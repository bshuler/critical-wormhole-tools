"""
wh ftp - FTP client through wormhole.

Provides FTP client functionality for file transfers through wormhole.
"""

import asyncio
import click
import os
import struct
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# FTP protocol messages (over wormhole)
MSG_COMMAND = 0x01      # FTP command: command_len + command + args
MSG_RESPONSE = 0x02     # FTP response: code (2 bytes) + message
MSG_DATA_START = 0x03   # Start data transfer
MSG_DATA = 0x04         # Data chunk
MSG_DATA_END = 0x05     # End data transfer
MSG_ERROR = 0x06        # Error message


@dataclass
class FileInfo:
    """File information for directory listings."""
    name: str
    size: int
    is_dir: bool
    modified: str
    permissions: str = ""


class FTPProtocol:
    """
    FTP-like protocol over wormhole.

    Provides common FTP operations: list, get, put, cd, pwd, mkdir, rm, rmdir.
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
        self.cwd = self.root_dir

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()

        # Response handling
        self._response_future: Optional[asyncio.Future] = None
        self._data_buffer: bytes = b""
        self._receiving_data = False

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, data: bytes = b"") -> None:
        """Send a message."""
        if not self._protocol:
            return
        header = struct.pack(">BI", msg_type, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data from wormhole."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages from buffer."""
        while len(self._buffer) >= 5:
            msg_type, data_len = struct.unpack(">BI", self._buffer[:5])

            if len(self._buffer) < 5 + data_len:
                break

            payload = self._buffer[5:5 + data_len]
            self._buffer = self._buffer[5 + data_len:]

            if msg_type == MSG_COMMAND:
                asyncio.create_task(self._handle_command(payload))
            elif msg_type == MSG_RESPONSE:
                self._handle_response(payload)
            elif msg_type == MSG_DATA_START:
                self._receiving_data = True
                self._data_buffer = b""
            elif msg_type == MSG_DATA:
                if self._receiving_data:
                    self._data_buffer += payload
            elif msg_type == MSG_DATA_END:
                self._receiving_data = False
                self._handle_data_complete()
            elif msg_type == MSG_ERROR:
                self._handle_error(payload)

    async def _handle_command(self, payload: bytes) -> None:
        """Handle FTP command (server side)."""
        if len(payload) < 1:
            self._send_response(500, "Invalid command")
            return

        cmd_len = payload[0]
        if len(payload) < 1 + cmd_len:
            self._send_response(500, "Invalid command")
            return

        cmd = payload[1:1 + cmd_len].decode().upper()
        args = payload[1 + cmd_len:].decode() if len(payload) > 1 + cmd_len else ""

        self._status(f"Command: {cmd} {args}")

        try:
            if cmd == "PWD":
                await self._cmd_pwd()
            elif cmd == "CWD":
                await self._cmd_cwd(args)
            elif cmd == "LIST":
                await self._cmd_list(args)
            elif cmd == "RETR":
                await self._cmd_retr(args)
            elif cmd == "STOR":
                await self._cmd_stor(args)
            elif cmd == "MKD":
                await self._cmd_mkd(args)
            elif cmd == "RMD":
                await self._cmd_rmd(args)
            elif cmd == "DELE":
                await self._cmd_dele(args)
            elif cmd == "SIZE":
                await self._cmd_size(args)
            elif cmd == "QUIT":
                self._send_response(221, "Goodbye")
                self._done.set()
            else:
                self._send_response(502, f"Command not implemented: {cmd}")
        except Exception as e:
            self._send_response(550, str(e))

    def _send_response(self, code: int, message: str) -> None:
        """Send FTP response."""
        payload = struct.pack(">H", code) + message.encode()
        self._send_message(MSG_RESPONSE, payload)

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to current directory."""
        if os.path.isabs(path):
            resolved = os.path.normpath(path)
        else:
            resolved = os.path.normpath(os.path.join(self.cwd, path))

        # Security: ensure path is within root
        if not resolved.startswith(self.root_dir):
            raise PermissionError("Access denied: path outside root directory")

        return resolved

    async def _cmd_pwd(self) -> None:
        """Print working directory."""
        rel_path = os.path.relpath(self.cwd, self.root_dir)
        if rel_path == ".":
            rel_path = "/"
        else:
            rel_path = "/" + rel_path
        self._send_response(257, f'"{rel_path}" is current directory')

    async def _cmd_cwd(self, path: str) -> None:
        """Change working directory."""
        if path == "/":
            new_path = self.root_dir
        else:
            new_path = self._resolve_path(path)

        if not os.path.isdir(new_path):
            self._send_response(550, f"Directory not found: {path}")
            return

        self.cwd = new_path
        self._send_response(250, "Directory changed successfully")

    async def _cmd_list(self, path: str) -> None:
        """List directory contents."""
        target = self._resolve_path(path) if path else self.cwd

        if not os.path.isdir(target):
            self._send_response(550, f"Not a directory: {path}")
            return

        files: List[Dict[str, Any]] = []
        for name in os.listdir(target):
            full_path = os.path.join(target, name)
            try:
                stat = os.stat(full_path)
                files.append({
                    "name": name,
                    "size": stat.st_size,
                    "is_dir": os.path.isdir(full_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                })
            except OSError:
                continue

        # Send file list as JSON
        self._send_response(150, "Opening data connection")
        self._send_message(MSG_DATA_START)
        self._send_message(MSG_DATA, json.dumps(files).encode())
        self._send_message(MSG_DATA_END)
        self._send_response(226, "Transfer complete")

    async def _cmd_retr(self, path: str) -> None:
        """Retrieve (download) file."""
        target = self._resolve_path(path)

        if not os.path.isfile(target):
            self._send_response(550, f"File not found: {path}")
            return

        self._send_response(150, "Opening data connection")
        self._send_message(MSG_DATA_START)

        try:
            with open(target, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self._send_message(MSG_DATA, chunk)
        except Exception as e:
            self._send_message(MSG_ERROR, str(e).encode())
            return

        self._send_message(MSG_DATA_END)
        self._send_response(226, "Transfer complete")

    async def _cmd_stor(self, path: str) -> None:
        """Store (upload) file."""
        target = self._resolve_path(path)

        # Wait for data
        self._send_response(150, "Ready to receive data")
        self._receiving_data = True
        self._data_buffer = b""

        # Data will be collected in _process_buffer
        # and written when MSG_DATA_END is received
        # Store the target path for later
        self._stor_target = target

    async def _cmd_mkd(self, path: str) -> None:
        """Make directory."""
        target = self._resolve_path(path)

        try:
            os.makedirs(target, exist_ok=False)
            self._send_response(257, f'"{path}" directory created')
        except FileExistsError:
            self._send_response(550, f"Directory already exists: {path}")
        except Exception as e:
            self._send_response(550, str(e))

    async def _cmd_rmd(self, path: str) -> None:
        """Remove directory."""
        target = self._resolve_path(path)

        if not os.path.isdir(target):
            self._send_response(550, f"Not a directory: {path}")
            return

        try:
            os.rmdir(target)
            self._send_response(250, "Directory removed")
        except OSError as e:
            self._send_response(550, str(e))

    async def _cmd_dele(self, path: str) -> None:
        """Delete file."""
        target = self._resolve_path(path)

        if not os.path.isfile(target):
            self._send_response(550, f"File not found: {path}")
            return

        try:
            os.remove(target)
            self._send_response(250, "File deleted")
        except Exception as e:
            self._send_response(550, str(e))

    async def _cmd_size(self, path: str) -> None:
        """Get file size."""
        target = self._resolve_path(path)

        if not os.path.isfile(target):
            self._send_response(550, f"File not found: {path}")
            return

        size = os.path.getsize(target)
        self._send_response(213, str(size))

    def _handle_response(self, payload: bytes) -> None:
        """Handle FTP response (client side)."""
        if len(payload) < 2:
            return

        code = struct.unpack(">H", payload[:2])[0]
        message = payload[2:].decode()

        if self._response_future and not self._response_future.done():
            self._response_future.set_result((code, message))

    def _handle_data_complete(self) -> None:
        """Handle data transfer complete."""
        if self.is_server and hasattr(self, '_stor_target'):
            # Server: write uploaded data to file
            try:
                with open(self._stor_target, "wb") as f:
                    f.write(self._data_buffer)
                self._send_response(226, "Transfer complete")
            except Exception as e:
                self._send_response(550, str(e))
            finally:
                delattr(self, '_stor_target')
        elif self._response_future and not self._response_future.done():
            # Client: data received
            pass  # Data is in self._data_buffer

    def _handle_error(self, payload: bytes) -> None:
        """Handle error message."""
        error = payload.decode() if payload else "Unknown error"
        self._status(f"Error: {error}")
        if self._response_future and not self._response_future.done():
            self._response_future.set_exception(Exception(error))

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle wormhole disconnection."""
        self._done.set()
        if self._response_future and not self._response_future.done():
            self._response_future.set_exception(Exception("Connection lost"))

    async def send_command(self, cmd: str, args: str = "") -> tuple:
        """Send command and wait for response (client side)."""
        self._response_future = asyncio.get_event_loop().create_future()
        self._data_buffer = b""

        cmd_bytes = cmd.encode()
        payload = bytes([len(cmd_bytes)]) + cmd_bytes + args.encode()
        self._send_message(MSG_COMMAND, payload)

        try:
            result = await asyncio.wait_for(self._response_future, timeout=60.0)
            return result
        except asyncio.TimeoutError:
            return (421, "Request timed out")

    async def upload_file(self, local_path: str, remote_path: str) -> tuple:
        """Upload a file to the server."""
        if not os.path.isfile(local_path):
            return (550, f"Local file not found: {local_path}")

        # Send STOR command
        self._response_future = asyncio.get_event_loop().create_future()
        cmd_bytes = b"STOR"
        payload = bytes([len(cmd_bytes)]) + cmd_bytes + remote_path.encode()
        self._send_message(MSG_COMMAND, payload)

        # Wait for ready response
        try:
            code, msg = await asyncio.wait_for(self._response_future, timeout=10.0)
            if code != 150:
                return (code, msg)
        except asyncio.TimeoutError:
            return (421, "Request timed out")

        # Send file data
        self._send_message(MSG_DATA_START)
        try:
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self._send_message(MSG_DATA, chunk)
        except Exception as e:
            return (550, str(e))

        self._send_message(MSG_DATA_END)

        # Wait for completion response
        self._response_future = asyncio.get_event_loop().create_future()
        try:
            return await asyncio.wait_for(self._response_future, timeout=60.0)
        except asyncio.TimeoutError:
            return (421, "Transfer timed out")

    async def download_file(self, remote_path: str, local_path: str) -> tuple:
        """Download a file from the server."""
        self._response_future = asyncio.get_event_loop().create_future()
        self._data_buffer = b""

        cmd_bytes = b"RETR"
        payload = bytes([len(cmd_bytes)]) + cmd_bytes + remote_path.encode()
        self._send_message(MSG_COMMAND, payload)

        # Wait for data start
        try:
            code, msg = await asyncio.wait_for(self._response_future, timeout=10.0)
            if code != 150:
                return (code, msg)
        except asyncio.TimeoutError:
            return (421, "Request timed out")

        # Wait for data end
        self._response_future = asyncio.get_event_loop().create_future()
        try:
            code, msg = await asyncio.wait_for(self._response_future, timeout=120.0)
            if code != 226:
                return (code, msg)
        except asyncio.TimeoutError:
            return (421, "Transfer timed out")

        # Write data to file
        try:
            with open(local_path, "wb") as f:
                f.write(self._data_buffer)
            return (226, f"Downloaded {len(self._data_buffer)} bytes")
        except Exception as e:
            return (550, str(e))

    async def run_server(self, manager: WormholeManager) -> None:
        """Run as FTP server."""
        endpoint = manager.listener_for("wh-ftp")

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
        self._status("FTP server started, waiting for client...")

        await connected.wait()
        self._status("Client connected")

        # Send welcome message
        self._send_response(220, "wh-ftp server ready")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager) -> "FTPProtocol":
        """Run as FTP client and return the protocol for interaction."""
        endpoint = manager.connector_for("wh-ftp")

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

        # Wait for welcome message
        self._response_future = asyncio.get_event_loop().create_future()
        try:
            code, msg = await asyncio.wait_for(self._response_future, timeout=10.0)
            self._status(f"{code} {msg}")
        except asyncio.TimeoutError:
            raise Exception("No response from server")

        return self


@click.command("ftp")
@click.argument("code", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run FTP server)")
@click.option("-d", "--directory", default=None, help="Root directory for server mode")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def ftp(
    ctx: click.Context,
    code: Optional[str],
    listen: bool,
    directory: Optional[str],
    verbose: bool,
) -> None:
    """
    FTP client/server through wormhole.

    In listen mode, runs an FTP server that exposes a directory.
    In client mode, provides an interactive FTP session.

    \b
    Examples:
        # Remote: Start FTP server
        wh ftp -l -d /path/to/share

        # Local: Connect to FTP server
        wh ftp 7-guitar-sunset

        # Interactive FTP commands:
        ftp> ls
        ftp> cd subdir
        ftp> get file.txt
        ftp> put local.txt
        ftp> quit

        # Connect to WNS address
        wh ftp wh://abc123.wns
    """
    if not listen and not code:
        raise click.UsageError("CODE is required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[ftp] {msg}", err=True)

    async def run_ftp():
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
                    click.echo(f"FTP server listening on code: {manager.code}", err=True)

                    root_dir = directory or os.getcwd()
                    root_dir = os.path.abspath(root_dir)
                    click.echo(f"Serving directory: {root_dir}", err=True)

                    await manager.establish()

                    ftp_proto = FTPProtocol(
                        on_status=status,
                        is_server=True,
                        root_dir=root_dir,
                    )
                    await ftp_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    ftp_proto = FTPProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    await ftp_proto.run_client(manager)

                    click.echo("Connected to FTP server", err=True)
                    click.echo("Type 'help' for available commands", err=True)

                    # Interactive mode
                    local_cwd = os.getcwd()

                    while not ftp_proto._done.is_set():
                        try:
                            line = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: input("ftp> ")
                            )
                        except EOFError:
                            break

                        line = line.strip()
                        if not line:
                            continue

                        parts = line.split(maxsplit=1)
                        cmd = parts[0].lower()
                        args = parts[1] if len(parts) > 1 else ""

                        if cmd == "help":
                            click.echo("Available commands:")
                            click.echo("  ls [path]       - List directory")
                            click.echo("  cd <path>       - Change remote directory")
                            click.echo("  pwd             - Print remote directory")
                            click.echo("  lcd <path>      - Change local directory")
                            click.echo("  lpwd            - Print local directory")
                            click.echo("  get <file>      - Download file")
                            click.echo("  put <file>      - Upload file")
                            click.echo("  mkdir <dir>     - Create directory")
                            click.echo("  rmdir <dir>     - Remove directory")
                            click.echo("  rm <file>       - Delete file")
                            click.echo("  quit            - Exit")

                        elif cmd == "ls":
                            code_resp, msg = await ftp_proto.send_command("LIST", args)
                            if code_resp == 226:
                                try:
                                    files = json.loads(ftp_proto._data_buffer.decode())
                                    for f in files:
                                        ftype = "d" if f["is_dir"] else "-"
                                        size = f["size"] if not f["is_dir"] else ""
                                        click.echo(f"{ftype} {size:>10} {f['name']}")
                                except json.JSONDecodeError:
                                    click.echo(f"Error parsing directory listing")
                            else:
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "cd":
                            if not args:
                                click.echo("Usage: cd <path>")
                            else:
                                code_resp, msg = await ftp_proto.send_command("CWD", args)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "pwd":
                            code_resp, msg = await ftp_proto.send_command("PWD")
                            click.echo(f"{code_resp} {msg}")

                        elif cmd == "lcd":
                            if not args:
                                click.echo("Usage: lcd <path>")
                            else:
                                try:
                                    os.chdir(args)
                                    local_cwd = os.getcwd()
                                    click.echo(f"Local directory: {local_cwd}")
                                except Exception as e:
                                    click.echo(f"Error: {e}")

                        elif cmd == "lpwd":
                            click.echo(f"Local directory: {os.getcwd()}")

                        elif cmd == "get":
                            if not args:
                                click.echo("Usage: get <file>")
                            else:
                                local_file = os.path.basename(args)
                                code_resp, msg = await ftp_proto.download_file(args, local_file)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "put":
                            if not args:
                                click.echo("Usage: put <file>")
                            else:
                                remote_file = os.path.basename(args)
                                code_resp, msg = await ftp_proto.upload_file(args, remote_file)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "mkdir":
                            if not args:
                                click.echo("Usage: mkdir <dir>")
                            else:
                                code_resp, msg = await ftp_proto.send_command("MKD", args)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "rmdir":
                            if not args:
                                click.echo("Usage: rmdir <dir>")
                            else:
                                code_resp, msg = await ftp_proto.send_command("RMD", args)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "rm":
                            if not args:
                                click.echo("Usage: rm <file>")
                            else:
                                code_resp, msg = await ftp_proto.send_command("DELE", args)
                                click.echo(f"{code_resp} {msg}")

                        elif cmd == "quit" or cmd == "exit" or cmd == "bye":
                            await ftp_proto.send_command("QUIT")
                            break

                        else:
                            click.echo(f"Unknown command: {cmd}. Type 'help' for commands.")

        except KeyboardInterrupt:
            click.echo("\n--- ftp closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_ftp())
