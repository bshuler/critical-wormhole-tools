"""
wh mount - Mount remote filesystem via wormhole.

Provides FUSE-based filesystem mounting through wormhole using SFTP.
"""

import asyncio
import click
import os
import sys
import stat
import errno
import struct
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# Mount protocol messages
MSG_GETATTR = 0x01
MSG_READDIR = 0x02
MSG_READ = 0x03
MSG_WRITE = 0x04
MSG_CREATE = 0x05
MSG_MKDIR = 0x06
MSG_UNLINK = 0x07
MSG_RMDIR = 0x08
MSG_RENAME = 0x09
MSG_TRUNCATE = 0x0A
MSG_CHMOD = 0x0B
MSG_RESPONSE = 0x10
MSG_ERROR = 0x11


@dataclass
class FileAttr:
    """File attributes."""
    mode: int
    size: int
    atime: float
    mtime: float
    ctime: float
    uid: int = 0
    gid: int = 0
    nlink: int = 1


class MountProtocol:
    """
    Filesystem protocol over wormhole.

    Provides remote filesystem operations for mounting.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        is_server: bool = False,
        root_dir: Optional[str] = None,
    ):
        self.on_status = on_status
        self.is_server = is_server
        self.root_dir = root_dir or os.path.expanduser("~")

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()

        # Request handling
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, request_id: int, data: bytes = b"") -> None:
        """Send a message."""
        if not self._protocol:
            return
        header = struct.pack(">BII", msg_type, request_id, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages."""
        while len(self._buffer) >= 9:  # type + request_id + length
            msg_type, request_id, data_len = struct.unpack(">BII", self._buffer[:9])

            if len(self._buffer) < 9 + data_len:
                break

            payload = self._buffer[9:9 + data_len]
            self._buffer = self._buffer[9 + data_len:]

            if msg_type in (MSG_RESPONSE, MSG_ERROR):
                self._handle_response(msg_type, request_id, payload)
            else:
                asyncio.create_task(self._handle_request(msg_type, request_id, payload))

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to root directory."""
        # Remove leading slash and normalize
        path = path.lstrip("/")
        if not path:
            return self.root_dir

        resolved = os.path.normpath(os.path.join(self.root_dir, path))

        # Security: ensure path is within root
        if not resolved.startswith(self.root_dir):
            raise PermissionError("Access denied: path outside root directory")

        return resolved

    async def _handle_request(self, msg_type: int, request_id: int, payload: bytes) -> None:
        """Handle filesystem request (server side)."""
        try:
            request = json.loads(payload.decode()) if payload else {}
            path = request.get("path", "/")
            resolved = self._resolve_path(path)

            if msg_type == MSG_GETATTR:
                await self._handle_getattr(request_id, resolved)
            elif msg_type == MSG_READDIR:
                await self._handle_readdir(request_id, resolved)
            elif msg_type == MSG_READ:
                await self._handle_read(request_id, resolved, request)
            elif msg_type == MSG_WRITE:
                await self._handle_write(request_id, resolved, request)
            elif msg_type == MSG_CREATE:
                await self._handle_create(request_id, resolved, request)
            elif msg_type == MSG_MKDIR:
                await self._handle_mkdir(request_id, resolved, request)
            elif msg_type == MSG_UNLINK:
                await self._handle_unlink(request_id, resolved)
            elif msg_type == MSG_RMDIR:
                await self._handle_rmdir(request_id, resolved)
            elif msg_type == MSG_RENAME:
                await self._handle_rename(request_id, resolved, request)
            elif msg_type == MSG_TRUNCATE:
                await self._handle_truncate(request_id, resolved, request)
            elif msg_type == MSG_CHMOD:
                await self._handle_chmod(request_id, resolved, request)
            else:
                self._send_error(request_id, errno.ENOSYS, "Not implemented")

        except PermissionError as e:
            self._send_error(request_id, errno.EACCES, str(e))
        except FileNotFoundError as e:
            self._send_error(request_id, errno.ENOENT, str(e))
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_getattr(self, request_id: int, path: str) -> None:
        """Handle getattr request."""
        try:
            st = os.stat(path)
            response = {
                "mode": st.st_mode,
                "size": st.st_size,
                "atime": st.st_atime,
                "mtime": st.st_mtime,
                "ctime": st.st_ctime,
                "uid": st.st_uid,
                "gid": st.st_gid,
                "nlink": st.st_nlink,
            }
            self._send_response(request_id, response)
        except FileNotFoundError:
            self._send_error(request_id, errno.ENOENT, "File not found")

    async def _handle_readdir(self, request_id: int, path: str) -> None:
        """Handle readdir request."""
        try:
            entries = [".", ".."]
            entries.extend(os.listdir(path))
            self._send_response(request_id, {"entries": entries})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_read(self, request_id: int, path: str, request: dict) -> None:
        """Handle read request."""
        offset = request.get("offset", 0)
        size = request.get("size", 4096)

        try:
            with open(path, "rb") as f:
                f.seek(offset)
                data = f.read(size)
            # Send data as base64
            import base64
            self._send_response(request_id, {"data": base64.b64encode(data).decode()})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_write(self, request_id: int, path: str, request: dict) -> None:
        """Handle write request."""
        offset = request.get("offset", 0)
        import base64
        data = base64.b64decode(request.get("data", ""))

        try:
            with open(path, "r+b") as f:
                f.seek(offset)
                written = f.write(data)
            self._send_response(request_id, {"written": written})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_create(self, request_id: int, path: str, request: dict) -> None:
        """Handle create request."""
        mode = request.get("mode", 0o644)

        try:
            fd = os.open(path, os.O_CREAT | os.O_WRONLY, mode)
            os.close(fd)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_mkdir(self, request_id: int, path: str, request: dict) -> None:
        """Handle mkdir request."""
        mode = request.get("mode", 0o755)

        try:
            os.mkdir(path, mode)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_unlink(self, request_id: int, path: str) -> None:
        """Handle unlink request."""
        try:
            os.unlink(path)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_rmdir(self, request_id: int, path: str) -> None:
        """Handle rmdir request."""
        try:
            os.rmdir(path)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_rename(self, request_id: int, path: str, request: dict) -> None:
        """Handle rename request."""
        new_path = self._resolve_path(request.get("new_path", ""))

        try:
            os.rename(path, new_path)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_truncate(self, request_id: int, path: str, request: dict) -> None:
        """Handle truncate request."""
        length = request.get("length", 0)

        try:
            with open(path, "r+b") as f:
                f.truncate(length)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    async def _handle_chmod(self, request_id: int, path: str, request: dict) -> None:
        """Handle chmod request."""
        mode = request.get("mode", 0o644)

        try:
            os.chmod(path, mode)
            self._send_response(request_id, {"success": True})
        except Exception as e:
            self._send_error(request_id, errno.EIO, str(e))

    def _send_response(self, request_id: int, data: dict) -> None:
        """Send success response."""
        self._send_message(MSG_RESPONSE, request_id, json.dumps(data).encode())

    def _send_error(self, request_id: int, code: int, message: str) -> None:
        """Send error response."""
        data = {"error": code, "message": message}
        self._send_message(MSG_ERROR, request_id, json.dumps(data).encode())

    def _handle_response(self, msg_type: int, request_id: int, payload: bytes) -> None:
        """Handle response (client side)."""
        if request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.done():
                try:
                    data = json.loads(payload.decode()) if payload else {}
                    if msg_type == MSG_ERROR:
                        future.set_exception(OSError(data.get("error", errno.EIO), data.get("message", "Error")))
                    else:
                        future.set_result(data)
                except Exception as e:
                    future.set_exception(e)

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(Exception("Connection lost"))

    async def _send_request(self, msg_type: int, data: dict) -> dict:
        """Send request and wait for response (client side)."""
        self._request_id += 1
        request_id = self._request_id

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        self._send_message(msg_type, request_id, json.dumps(data).encode())

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise OSError(errno.ETIMEDOUT, "Request timed out")

    # Client-side filesystem operations
    async def getattr(self, path: str) -> FileAttr:
        """Get file attributes."""
        result = await self._send_request(MSG_GETATTR, {"path": path})
        return FileAttr(
            mode=result["mode"],
            size=result["size"],
            atime=result["atime"],
            mtime=result["mtime"],
            ctime=result["ctime"],
            uid=result.get("uid", 0),
            gid=result.get("gid", 0),
            nlink=result.get("nlink", 1),
        )

    async def readdir(self, path: str) -> List[str]:
        """Read directory contents."""
        result = await self._send_request(MSG_READDIR, {"path": path})
        return result["entries"]

    async def read(self, path: str, offset: int, size: int) -> bytes:
        """Read file data."""
        result = await self._send_request(MSG_READ, {"path": path, "offset": offset, "size": size})
        import base64
        return base64.b64decode(result["data"])

    async def write(self, path: str, offset: int, data: bytes) -> int:
        """Write file data."""
        import base64
        result = await self._send_request(MSG_WRITE, {
            "path": path,
            "offset": offset,
            "data": base64.b64encode(data).decode()
        })
        return result["written"]

    async def create(self, path: str, mode: int = 0o644) -> None:
        """Create file."""
        await self._send_request(MSG_CREATE, {"path": path, "mode": mode})

    async def mkdir(self, path: str, mode: int = 0o755) -> None:
        """Create directory."""
        await self._send_request(MSG_MKDIR, {"path": path, "mode": mode})

    async def unlink(self, path: str) -> None:
        """Remove file."""
        await self._send_request(MSG_UNLINK, {"path": path})

    async def rmdir(self, path: str) -> None:
        """Remove directory."""
        await self._send_request(MSG_RMDIR, {"path": path})

    async def rename(self, old_path: str, new_path: str) -> None:
        """Rename file/directory."""
        await self._send_request(MSG_RENAME, {"path": old_path, "new_path": new_path})

    async def truncate(self, path: str, length: int) -> None:
        """Truncate file."""
        await self._send_request(MSG_TRUNCATE, {"path": path, "length": length})

    async def chmod(self, path: str, mode: int) -> None:
        """Change file mode."""
        await self._send_request(MSG_CHMOD, {"path": path, "mode": mode})

    async def run_server(self, manager: WormholeManager) -> None:
        """Run as mount server."""
        endpoint = manager.listener_for("wh-mount")

        connected = asyncio.Event()

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        d = endpoint.listen(factory)
        future = asyncio.get_event_loop().create_future()

        def callback(port):
            future.set_result(port)

        def errback(failure):
            future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future
        self._status("Mount server ready...")

        await connected.wait()
        self._status("Client connected")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager) -> "MountProtocol":
        """Run as mount client."""
        endpoint = manager.connector_for("wh-mount")

        connected = asyncio.Event()

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        d = endpoint.connect(factory)
        future = asyncio.get_event_loop().create_future()

        def callback(protocol):
            self._protocol = protocol
            future.set_result(protocol)

        def errback(failure):
            future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future
        await connected.wait()

        return self


def check_fuse_available() -> bool:
    """Check if FUSE is available."""
    try:
        import fuse
        return True
    except ImportError:
        return False


@click.command("mount")
@click.argument("target", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run mount server)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-d", "--directory", default=None, help="Directory to share (server mode)")
@click.option("-o", "--options", default="", help="Mount options")
@click.option("-f", "--foreground", is_flag=True, help="Run in foreground")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def mount(
    ctx: click.Context,
    target: Optional[str],
    listen: bool,
    code: Optional[str],
    directory: Optional[str],
    options: str,
    foreground: bool,
    verbose: bool,
) -> None:
    """
    Mount remote filesystem via wormhole.

    Mounts a remote directory through wormhole using a FUSE filesystem.
    Requires fusepy (pip install fusepy) on the client side.

    \b
    Examples:
        # Remote: Start mount server
        wh mount -l -d /path/to/share

        # Local: Mount remote filesystem
        wh mount -c 7-guitar-sunset /mnt/remote

        # Mount with options
        wh mount -c CODE -o ro,noexec /mnt/remote

        # Foreground mode (for debugging)
        wh mount -c CODE -f /mnt/remote

    Note: Without FUSE support, this command provides a file browser interface.
    """
    if listen:
        pass
    elif not code:
        raise click.UsageError("CODE is required when not in listen mode (use -c/--code)")
    elif not target:
        raise click.UsageError("MOUNTPOINT is required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[mount] {msg}", err=True)

    async def run_mount():
        manager = WormholeManager(
            relay_url=relay_url,
            transit_relay=transit_relay,
            code_length=code_length,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode
                    await manager.create_and_allocate_code()
                    click.echo(f"Mount server listening on code: {manager.code}", err=True)

                    root_dir = directory or os.getcwd()
                    root_dir = os.path.abspath(root_dir)
                    click.echo(f"Sharing directory: {root_dir}", err=True)

                    await manager.establish()

                    mount_proto = MountProtocol(
                        on_status=status,
                        is_server=True,
                        root_dir=root_dir,
                    )
                    await mount_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    mount_proto = MountProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    await mount_proto.run_client(manager)

                    # Check if FUSE is available
                    if check_fuse_available():
                        click.echo(f"Mounting remote filesystem on {target}", err=True)
                        click.echo("FUSE mount support coming soon...", err=True)
                        click.echo("For now, use the file browser mode:", err=True)

                    # Fall back to interactive file browser
                    click.echo("Connected to remote filesystem", err=True)
                    click.echo("Type 'help' for available commands", err=True)
                    click.echo("")

                    cwd = "/"

                    while not mount_proto._done.is_set():
                        try:
                            line = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: input(f"wh:{cwd}> ")
                            )
                        except EOFError:
                            break

                        line = line.strip()
                        if not line:
                            continue

                        parts = line.split(maxsplit=1)
                        cmd = parts[0].lower()
                        args = parts[1] if len(parts) > 1 else ""

                        try:
                            if cmd == "help":
                                click.echo("Available commands:")
                                click.echo("  ls [path]      - List directory")
                                click.echo("  cd <path>      - Change directory")
                                click.echo("  pwd            - Print current directory")
                                click.echo("  cat <file>     - Display file contents")
                                click.echo("  get <file>     - Download file")
                                click.echo("  put <file>     - Upload file")
                                click.echo("  mkdir <dir>    - Create directory")
                                click.echo("  rm <file>      - Remove file")
                                click.echo("  rmdir <dir>    - Remove directory")
                                click.echo("  stat <path>    - Show file info")
                                click.echo("  quit           - Exit")

                            elif cmd == "ls":
                                path = args if args else cwd
                                if not path.startswith("/"):
                                    path = os.path.join(cwd, path)
                                entries = await mount_proto.readdir(path)
                                for entry in entries:
                                    if entry not in (".", ".."):
                                        click.echo(entry)

                            elif cmd == "cd":
                                if not args:
                                    cwd = "/"
                                elif args.startswith("/"):
                                    cwd = args
                                else:
                                    cwd = os.path.normpath(os.path.join(cwd, args))

                            elif cmd == "pwd":
                                click.echo(cwd)

                            elif cmd == "cat":
                                if not args:
                                    click.echo("Usage: cat <file>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    data = await mount_proto.read(path, 0, 1024 * 1024)  # 1MB max
                                    sys.stdout.buffer.write(data)
                                    if not data.endswith(b"\n"):
                                        click.echo("")

                            elif cmd == "get":
                                if not args:
                                    click.echo("Usage: get <file>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    local_file = os.path.basename(args)
                                    attr = await mount_proto.getattr(path)
                                    data = await mount_proto.read(path, 0, attr.size)
                                    with open(local_file, "wb") as f:
                                        f.write(data)
                                    click.echo(f"Downloaded {len(data)} bytes to {local_file}")

                            elif cmd == "put":
                                if not args:
                                    click.echo("Usage: put <file>")
                                else:
                                    local_file = args
                                    remote_file = os.path.join(cwd, os.path.basename(args))
                                    with open(local_file, "rb") as f:
                                        data = f.read()
                                    await mount_proto.create(remote_file)
                                    await mount_proto.write(remote_file, 0, data)
                                    click.echo(f"Uploaded {len(data)} bytes to {remote_file}")

                            elif cmd == "mkdir":
                                if not args:
                                    click.echo("Usage: mkdir <dir>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    await mount_proto.mkdir(path)
                                    click.echo(f"Created directory: {path}")

                            elif cmd == "rm":
                                if not args:
                                    click.echo("Usage: rm <file>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    await mount_proto.unlink(path)
                                    click.echo(f"Removed: {path}")

                            elif cmd == "rmdir":
                                if not args:
                                    click.echo("Usage: rmdir <dir>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    await mount_proto.rmdir(path)
                                    click.echo(f"Removed directory: {path}")

                            elif cmd == "stat":
                                if not args:
                                    click.echo("Usage: stat <path>")
                                else:
                                    path = args if args.startswith("/") else os.path.join(cwd, args)
                                    attr = await mount_proto.getattr(path)
                                    click.echo(f"  Size: {attr.size}")
                                    click.echo(f"  Mode: {oct(attr.mode)}")
                                    click.echo(f"  Modified: {datetime.fromtimestamp(attr.mtime)}")

                            elif cmd in ("quit", "exit"):
                                break

                            else:
                                click.echo(f"Unknown command: {cmd}. Type 'help' for commands.")

                        except OSError as e:
                            click.echo(f"Error: {e}", err=True)
                        except Exception as e:
                            click.echo(f"Error: {e}", err=True)

        except KeyboardInterrupt:
            click.echo("\n--- mount closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_mount())
