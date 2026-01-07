"""
WormholeSSHServer - SSH server that accepts connections over wormhole.

Runs on the server side of `wh listen --ssh` to accept SSH connections
from `wh ssh` clients.
"""

from typing import Optional, Dict, Any
import asyncio
import os
import pty
import subprocess
import pwd

import asyncssh


class WormholeSSHServer(asyncssh.SSHServer):
    """SSH server for wormhole connections."""

    def __init__(
        self,
        authorized_keys: Optional[str] = None,
        passwords: Optional[Dict[str, str]] = None,
    ):
        self.authorized_keys_path = authorized_keys
        self._passwords = passwords or {}
        self._conn = None

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        self._conn = conn

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        if username in self._passwords:
            return self._passwords[username] == password
        return True  # Accept any password for dev

    def public_key_auth_supported(self) -> bool:
        return self.authorized_keys_path is not None

    def validate_public_key(self, username: str, key: asyncssh.SSHKey) -> bool:
        if not self.authorized_keys_path:
            return False
        try:
            authorized_keys = asyncssh.read_authorized_keys(self.authorized_keys_path)
            return authorized_keys.validate(key, username)
        except Exception:
            return False


class SSHServerHandler:
    """Handler that runs an SSH server over wormhole."""

    def __init__(
        self,
        wormhole_manager: Any,
        host_keys: Optional[list] = None,
        authorized_keys: Optional[str] = None,
        passwords: Optional[Dict[str, str]] = None,
    ):
        self.manager = wormhole_manager
        self.host_keys = host_keys or []
        self.authorized_keys = authorized_keys
        self.passwords = passwords
        self._server_key = None
        self._local_server = None
        self._local_port = None

        if not self.host_keys:
            self._generate_host_keys()

    def _generate_host_keys(self) -> None:
        """Generate temporary host keys."""
        self._server_key = asyncssh.generate_private_key(
            'ssh-rsa', comment='wh-host-key', key_size=2048
        )

    async def run(self) -> None:
        """Start accepting SSH connections via wormhole."""
        # Start local SSH server on random port
        server_host_keys = [self._server_key] if self._server_key else self.host_keys

        self._local_server = await asyncssh.create_server(
            lambda: WormholeSSHServer(
                authorized_keys=self.authorized_keys,
                passwords=self.passwords,
            ),
            '127.0.0.1', 0,  # Bind to random available port on localhost
            server_host_keys=server_host_keys,
            process_factory=self._handle_process,
            sftp_factory=True,  # Enable SFTP subsystem with default handler
        )

        # Get the assigned port
        self._local_port = self._local_server.sockets[0].getsockname()[1]

        # Listen on wormhole and forward to local SSH server
        endpoint = self.manager.listener_for("wh-ssh")

        from twisted.internet.protocol import Factory, Protocol

        handler = self
        loop = asyncio.get_event_loop()

        class ForwardProtocol(Protocol):
            """Forward wormhole traffic to local SSH server."""

            def __init__(self):
                self._local_reader = None
                self._local_writer = None
                self._forward_task = None
                self._pending_data = []  # Buffer for data before local connection

            def connectionMade(self):
                asyncio.ensure_future(self._connect_local())

            async def _connect_local(self):
                """Connect to local SSH server and start forwarding."""
                try:
                    self._local_reader, self._local_writer = await asyncio.open_connection(
                        '127.0.0.1', handler._local_port
                    )

                    # Flush any pending data that arrived before connection
                    if self._pending_data:
                        for data in self._pending_data:
                            self._local_writer.write(data)
                        await self._local_writer.drain()
                        self._pending_data = []

                    # Start forwarding from local to wormhole
                    self._forward_task = asyncio.ensure_future(self._forward_local_to_wormhole())
                except Exception:
                    self.transport.loseConnection()

            def dataReceived(self, data: bytes):
                """Forward data from wormhole to local SSH."""
                if self._local_writer and not self._local_writer.is_closing():
                    self._local_writer.write(data)
                    asyncio.ensure_future(self._drain_local())
                else:
                    # Buffer data until local connection is ready
                    self._pending_data.append(data)

            async def _drain_local(self):
                try:
                    await self._local_writer.drain()
                except:
                    pass

            async def _forward_local_to_wormhole(self):
                """Forward data from local SSH to wormhole."""
                try:
                    while True:
                        data = await self._local_reader.read(65536)
                        if not data:
                            break
                        self.transport.write(data)
                except Exception:
                    pass
                finally:
                    self.transport.loseConnection()

            def connectionLost(self, reason=None):
                if self._forward_task:
                    self._forward_task.cancel()
                if self._local_writer:
                    self._local_writer.close()

        class ForwardFactory(Factory):
            def buildProtocol(self, addr):
                return ForwardProtocol()

        # Start listening on wormhole
        d = endpoint.listen(ForwardFactory())

        future = loop.create_future()
        d.addCallback(lambda port: future.set_result(port) if not future.done() else None)
        d.addErrback(lambda f: future.set_exception(f.value) if not future.done() else None)

        await future

        # Keep running
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            if self._local_server:
                self._local_server.close()
                await self._local_server.wait_closed()

    def _handle_process(self, process: asyncssh.SSHServerProcess) -> None:
        """Handle an SSH process."""
        asyncio.ensure_future(self._run_process(process))

    async def _run_process(self, process: asyncssh.SSHServerProcess) -> None:
        """Run a shell or command."""
        command = process.command

        if command:
            await self._run_command(process, command)
        else:
            await self._run_shell(process)

    async def _run_command(self, process: asyncssh.SSHServerProcess, command: str) -> None:
        """Run a command with streaming stdin/stdout for interactive commands like SCP."""
        try:
            # Use async subprocess to allow interactive I/O (needed for scp)
            proc = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def forward_stdin():
                """Forward SSH stdin to process stdin."""
                try:
                    while not process.stdin.at_eof():
                        data = await process.stdin.read(65536)
                        if not data:
                            break
                        # Convert to bytes if needed
                        if isinstance(data, str):
                            data = data.encode('latin-1')  # Use latin-1 to preserve byte values
                        proc.stdin.write(data)
                        await proc.stdin.drain()
                except Exception:
                    pass
                finally:
                    try:
                        proc.stdin.close()
                    except:
                        pass

            async def forward_stdout():
                """Forward process stdout to SSH stdout (binary)."""
                try:
                    while True:
                        data = await proc.stdout.read(65536)
                        if not data:
                            break
                        # Decode bytes to string using latin-1 (preserves all byte values)
                        process.stdout.write(data.decode('latin-1'))
                except Exception:
                    pass

            async def forward_stderr():
                """Forward process stderr to SSH stderr."""
                try:
                    while True:
                        data = await proc.stderr.read(4096)
                        if not data:
                            break
                        process.stderr.write(data.decode('latin-1'))
                except Exception:
                    pass

            # Start stdin forwarding (runs in background)
            stdin_task = asyncio.create_task(forward_stdin())

            # Run stdout/stderr forwarding concurrently and wait for process
            try:
                await asyncio.gather(
                    forward_stdout(),
                    forward_stderr(),
                    return_exceptions=True
                )
            finally:
                stdin_task.cancel()
                try:
                    await stdin_task
                except asyncio.CancelledError:
                    pass

            # Wait for process to complete
            returncode = await proc.wait()
            process.exit(returncode)

        except Exception as e:
            process.stderr.write(f"Error: {e}\n")
            process.exit(1)

    async def _run_shell(self, process: asyncssh.SSHServerProcess) -> None:
        """Run an interactive shell."""
        try:
            shell = pwd.getpwuid(os.getuid()).pw_shell
        except Exception:
            shell = '/bin/sh'

        master_fd, slave_fd = pty.openpty()

        try:
            shell_proc = subprocess.Popen(
                shell,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)

            loop = asyncio.get_event_loop()

            async def read_master():
                while True:
                    try:
                        data = await loop.run_in_executor(
                            None, lambda: os.read(master_fd, 4096)
                        )
                        if not data:
                            break
                        process.stdout.write(data.decode('utf-8', errors='replace'))
                        await process.stdout.drain()
                    except:
                        break

            async def write_master():
                try:
                    while True:
                        data = await process.stdin.read(4096)
                        if not data:
                            break
                        os.write(master_fd, data)
                except:
                    pass

            await asyncio.gather(read_master(), write_master(), return_exceptions=True)
            process.exit(shell_proc.wait())

        finally:
            try:
                os.close(master_fd)
            except:
                pass
