"""
wh rsync - Incremental file synchronization through wormhole.

Synchronizes files between local and remote, only transferring changed files.
"""

import asyncio
import click
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Optional, List, Dict, Any

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol


# Protocol messages
MSG_MANIFEST = 0x01      # File manifest (JSON list of files)
MSG_REQUEST = 0x02       # Request files (JSON list of paths)
MSG_FILE_START = 0x03    # Start file: path_len + path + size
MSG_FILE_DATA = 0x04     # File data chunk
MSG_FILE_END = 0x05      # End of file
MSG_DELETE = 0x06        # Delete files (JSON list)
MSG_DONE = 0x07          # Sync complete


def file_checksum(path: Path, block_size: int = 65536) -> str:
    """Calculate MD5 checksum of a file."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()


def scan_directory(path: Path, base: Path) -> List[Dict[str, Any]]:
    """
    Scan directory and return file manifest.

    Returns list of dicts with: path, size, mtime, checksum
    """
    files = []
    for item in path.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(base)
            stat = item.stat()
            files.append({
                "path": str(rel_path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "checksum": file_checksum(item),
            })
    return files


class RsyncProtocol:
    """
    Protocol for rsync-style file synchronization.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        on_progress: Optional[callable] = None,
    ):
        self.on_status = on_status
        self.on_progress = on_progress
        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()

        # File transfer state
        self._current_file: Optional[Path] = None
        self._current_file_handle = None
        self._current_file_size = 0
        self._current_file_received = 0
        self._files_transferred = 0
        self._bytes_transferred = 0

        # Pending operations
        self._manifest_future: Optional[asyncio.Future] = None
        self._request_future: Optional[asyncio.Future] = None

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _progress(self, filename: str, current: int, total: int) -> None:
        if self.on_progress:
            self.on_progress(filename, current, total)

    def _send_message(self, msg_type: int, data: bytes = b"") -> None:
        """Send a message."""
        if not self._protocol:
            return
        header = struct.pack(">BI", msg_type, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages."""
        while len(self._buffer) >= 5:
            msg_type, data_len = struct.unpack(">BI", self._buffer[:5])

            if len(self._buffer) < 5 + data_len:
                break

            payload = self._buffer[5:5 + data_len]
            self._buffer = self._buffer[5 + data_len:]

            if msg_type == MSG_MANIFEST:
                self._handle_manifest(payload)
            elif msg_type == MSG_REQUEST:
                self._handle_request(payload)
            elif msg_type == MSG_FILE_START:
                self._handle_file_start(payload)
            elif msg_type == MSG_FILE_DATA:
                self._handle_file_data(payload)
            elif msg_type == MSG_FILE_END:
                self._handle_file_end()
            elif msg_type == MSG_DELETE:
                self._handle_delete(payload)
            elif msg_type == MSG_DONE:
                self._handle_done()

    def _handle_manifest(self, payload: bytes) -> None:
        """Handle incoming manifest."""
        if self._manifest_future:
            manifest = json.loads(payload.decode())
            self._manifest_future.set_result(manifest)

    def _handle_request(self, payload: bytes) -> None:
        """Handle file request."""
        if self._request_future:
            request = json.loads(payload.decode())
            self._request_future.set_result(request)

    def _handle_file_start(self, payload: bytes) -> None:
        """Handle start of file transfer."""
        path_len = struct.unpack(">H", payload[:2])[0]
        path = payload[2:2 + path_len].decode()
        size = struct.unpack(">Q", payload[2 + path_len:10 + path_len])[0]

        self._current_file = Path(path)
        self._current_file_size = size
        self._current_file_received = 0

        # Create parent directories
        self._current_file.parent.mkdir(parents=True, exist_ok=True)

        # Open file for writing
        self._current_file_handle = open(self._current_file, "wb")
        self._status(f"Receiving: {path} ({size} bytes)")

    def _handle_file_data(self, payload: bytes) -> None:
        """Handle file data chunk."""
        if self._current_file_handle:
            self._current_file_handle.write(payload)
            self._current_file_received += len(payload)
            self._bytes_transferred += len(payload)
            self._progress(
                str(self._current_file),
                self._current_file_received,
                self._current_file_size
            )

    def _handle_file_end(self) -> None:
        """Handle end of file transfer."""
        if self._current_file_handle:
            self._current_file_handle.close()
            self._current_file_handle = None
            self._files_transferred += 1
            self._status(f"Completed: {self._current_file}")
        self._current_file = None

    def _handle_delete(self, payload: bytes) -> None:
        """Handle delete request."""
        files = json.loads(payload.decode())
        for path in files:
            p = Path(path)
            if p.exists():
                p.unlink()
                self._status(f"Deleted: {path}")

    def _handle_done(self) -> None:
        """Handle sync complete."""
        self._done.set()

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()

    async def send_manifest(self, manifest: List[Dict]) -> None:
        """Send file manifest to remote."""
        data = json.dumps(manifest).encode()
        self._send_message(MSG_MANIFEST, data)

    async def receive_manifest(self) -> List[Dict]:
        """Wait for manifest from remote."""
        self._manifest_future = asyncio.get_event_loop().create_future()
        manifest = await self._manifest_future
        self._manifest_future = None
        return manifest

    async def send_request(self, files: List[str]) -> None:
        """Send file request to remote."""
        data = json.dumps(files).encode()
        self._send_message(MSG_REQUEST, data)

    async def receive_request(self) -> List[str]:
        """Wait for file request from remote."""
        self._request_future = asyncio.get_event_loop().create_future()
        request = await self._request_future
        self._request_future = None
        return request

    async def send_file(self, path: Path, rel_path: str) -> None:
        """Send a file."""
        size = path.stat().st_size
        path_bytes = rel_path.encode()

        # Send file start
        header = struct.pack(">H", len(path_bytes)) + path_bytes + struct.pack(">Q", size)
        self._send_message(MSG_FILE_START, header)

        # Send file data in chunks
        with open(path, "rb") as f:
            while True:
                chunk = f.read(32768)
                if not chunk:
                    break
                self._send_message(MSG_FILE_DATA, chunk)
                self._bytes_transferred += len(chunk)

        # Send file end
        self._send_message(MSG_FILE_END)
        self._files_transferred += 1

    async def send_delete(self, files: List[str]) -> None:
        """Send delete request."""
        data = json.dumps(files).encode()
        self._send_message(MSG_DELETE, data)

    async def send_done(self) -> None:
        """Signal sync complete."""
        self._send_message(MSG_DONE)


def compare_manifests(
    local: List[Dict],
    remote: List[Dict],
    delete: bool = False,
) -> tuple:
    """
    Compare manifests and return files to transfer and delete.

    Returns: (files_to_send, files_to_delete)
    """
    local_dict = {f["path"]: f for f in local}
    remote_dict = {f["path"]: f for f in remote}

    to_send = []
    to_delete = []

    # Files to send: new or changed
    for path, info in local_dict.items():
        if path not in remote_dict:
            to_send.append(path)
        elif remote_dict[path]["checksum"] != info["checksum"]:
            to_send.append(path)

    # Files to delete: exist on remote but not local
    if delete:
        for path in remote_dict:
            if path not in local_dict:
                to_delete.append(path)

    return to_send, to_delete


@click.command("rsync")
@click.argument("source")
@click.argument("dest")
@click.option("-l", "--listen", is_flag=True, help="Listen mode (receive files)")
@click.option("-r", "--recursive", is_flag=True, help="Recurse into directories")
@click.option("--delete", is_flag=True, help="Delete files on dest that don't exist on source")
@click.option("-n", "--dry-run", is_flag=True, help="Show what would be transferred")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--progress", is_flag=True, help="Show progress")
@click.pass_context
def rsync(
    ctx: click.Context,
    source: str,
    dest: str,
    listen: bool,
    recursive: bool,
    delete: bool,
    dry_run: bool,
    verbose: bool,
    progress: bool,
) -> None:
    """
    Incremental file synchronization through wormhole.

    Synchronizes files between local and remote, only transferring files that
    have changed (based on checksum comparison).

    \b
    SOURCE and DEST can be:
      - Local path: /path/to/dir or ./dir
      - Remote path: CODE:/path or wh://addr.wns:/path

    \b
    Examples:
        # Remote: Listen to receive files
        wh rsync -l ./dest

        # Local: Sync directory to remote
        wh rsync -r ./src 7-guitar-sunset:./dest

        # Sync with delete (remove files not in source)
        wh rsync -r --delete ./src 7-guitar-sunset:./dest

        # Sync to WNS address
        wh rsync -r ./src wh://server.wns:./dest

        # Dry run (show what would transfer)
        wh rsync -r -n ./src 7-guitar-sunset:./dest
    """
    relay_url = ctx.obj.get("relay") if ctx.obj else None

    def status(msg: str) -> None:
        if verbose:
            click.echo(msg, err=True)

    def show_progress(filename: str, current: int, total: int) -> None:
        if progress:
            pct = (current / total * 100) if total > 0 else 100
            click.echo(f"\r{filename}: {pct:.1f}%", nl=False, err=True)
            if current >= total:
                click.echo("", err=True)

    async def run_rsync():
        manager = WormholeManager(
            relay_url=relay_url,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode - receive files
                    dest_path = Path(source)  # In listen mode, "source" is dest
                    if not dest_path.exists():
                        dest_path.mkdir(parents=True)

                    await manager.create_and_allocate_code()
                    click.echo(f"Rsync listening on code: {manager.code}", err=True)
                    click.echo(f"Destination: {dest_path}", err=True)

                    await manager.establish()

                    # Set up protocol
                    rsync_proto = RsyncProtocol(
                        on_status=status,
                        on_progress=show_progress if progress else None,
                    )
                    endpoint = manager.listener_for("wh-rsync")

                    from twisted.internet.protocol import Factory

                    connected = asyncio.Event()

                    class RsyncServerProtocol(StreamingProtocol):
                        def __init__(self, proto):
                            super().__init__()
                            self.rsync = proto

                        def connectionMade(self):
                            super().connectionMade()
                            self.rsync._protocol = self
                            connected.set()

                        def dataReceived(self, data):
                            self.rsync._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.rsync._on_connection_lost(None)

                    class RsyncFactory(Factory):
                        def buildProtocol(self, addr):
                            return RsyncServerProtocol(rsync_proto)

                    d = endpoint.listen(RsyncFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future

                    await connected.wait()
                    status("Peer connected")

                    # Scan local directory
                    local_manifest = scan_directory(dest_path, dest_path) if dest_path.exists() else []
                    status(f"Local files: {len(local_manifest)}")

                    # Send our manifest
                    await rsync_proto.send_manifest(local_manifest)

                    # Receive remote manifest
                    remote_manifest = await rsync_proto.receive_manifest()
                    status(f"Remote files: {len(remote_manifest)}")

                    # Determine what we need
                    to_receive, to_delete = compare_manifests(
                        remote_manifest, local_manifest, delete=delete
                    )
                    status(f"Files to receive: {len(to_receive)}")

                    # Request files
                    await rsync_proto.send_request(to_receive)

                    # Wait for transfer to complete
                    await rsync_proto._done.wait()

                    click.echo(
                        f"Received {rsync_proto._files_transferred} files, "
                        f"{rsync_proto._bytes_transferred} bytes",
                        err=True
                    )

                else:
                    # Client mode - send files
                    # Parse source and dest
                    if ":" in dest:
                        code, remote_path = dest.split(":", 1)
                    else:
                        raise click.UsageError("DEST must include CODE: for remote path")

                    source_path = Path(source)
                    if not source_path.exists():
                        raise click.ClickException(f"Source not found: {source}")

                    await manager.create_and_set_code(code)
                    click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    # Set up protocol
                    rsync_proto = RsyncProtocol(
                        on_status=status,
                        on_progress=show_progress if progress else None,
                    )
                    endpoint = manager.connector_for("wh-rsync")

                    from twisted.internet.protocol import Factory

                    connected = asyncio.Event()

                    class RsyncClientProtocol(StreamingProtocol):
                        def __init__(self, proto):
                            super().__init__()
                            self.rsync = proto

                        def connectionMade(self):
                            super().connectionMade()
                            self.rsync._protocol = self
                            connected.set()

                        def dataReceived(self, data):
                            self.rsync._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.rsync._on_connection_lost(None)

                    class RsyncFactory(Factory):
                        def buildProtocol(self, addr):
                            return RsyncClientProtocol(rsync_proto)

                    d = endpoint.connect(RsyncFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future
                    await connected.wait()

                    # Scan source directory
                    if source_path.is_dir():
                        local_manifest = scan_directory(source_path, source_path)
                    else:
                        local_manifest = [{
                            "path": source_path.name,
                            "size": source_path.stat().st_size,
                            "mtime": source_path.stat().st_mtime,
                            "checksum": file_checksum(source_path),
                        }]

                    status(f"Local files: {len(local_manifest)}")

                    # Receive remote manifest
                    remote_manifest = await rsync_proto.receive_manifest()
                    status(f"Remote files: {len(remote_manifest)}")

                    # Determine what to send
                    to_send, to_delete_remote = compare_manifests(
                        local_manifest, remote_manifest, delete=delete
                    )

                    if dry_run:
                        click.echo("Would transfer:", err=True)
                        for f in to_send:
                            click.echo(f"  {f}", err=True)
                        if to_delete_remote:
                            click.echo("Would delete:", err=True)
                            for f in to_delete_remote:
                                click.echo(f"  {f}", err=True)
                        return

                    status(f"Files to send: {len(to_send)}")

                    # Send our manifest
                    await rsync_proto.send_manifest(local_manifest)

                    # Wait for request
                    requested = await rsync_proto.receive_request()
                    status(f"Remote requested: {len(requested)} files")

                    # Send requested files
                    for rel_path in requested:
                        if source_path.is_dir():
                            full_path = source_path / rel_path
                        else:
                            full_path = source_path
                        if full_path.exists():
                            status(f"Sending: {rel_path}")
                            await rsync_proto.send_file(full_path, rel_path)

                    # Send deletes if requested
                    if delete and to_delete_remote:
                        await rsync_proto.send_delete(to_delete_remote)

                    # Signal done
                    await rsync_proto.send_done()

                    click.echo(
                        f"Sent {rsync_proto._files_transferred} files, "
                        f"{rsync_proto._bytes_transferred} bytes",
                        err=True
                    )

        except KeyboardInterrupt:
            click.echo("\n--- rsync interrupted ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_rsync())
