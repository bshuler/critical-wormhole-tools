"""
WormholeSCP - SCP file transfer over wormhole.

Provides secure copy functionality using AsyncSSH's SCP implementation
tunneled through the wormhole connection.
"""

from typing import Optional, Any, Callable
from pathlib import Path

import asyncssh

from wh.ssh.client import WormholeSSHClient


class WormholeSCP:
    """
    SCP file transfer over wormhole.

    Example:
        manager = WormholeManager()
        await manager.create_and_set_code("7-guitar-sunset")
        await manager.dilate()

        scp = WormholeSCP(manager, username="user", password="pass")

        # Download
        await scp.download("/remote/file.txt", "./local/")

        # Upload
        await scp.upload("./local/file.txt", "/remote/")
    """

    def __init__(
        self,
        wormhole_manager: Any,
        username: str,
        password: Optional[str] = None,
        client_keys: Optional[list] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ):
        """
        Initialize SCP client.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
            username: SSH username.
            password: SSH password.
            client_keys: List of paths to private key files.
            on_progress: Progress callback(filename, bytes_done, total_bytes).
        """
        self.manager = wormhole_manager
        self.username = username
        self.password = password
        self.client_keys = client_keys or []
        self.on_progress = on_progress
        self._ssh_client: Optional[WormholeSSHClient] = None

    async def _ensure_connected(self) -> None:
        """Ensure SSH connection is established."""
        if not self._ssh_client:
            self._ssh_client = WormholeSSHClient(
                wormhole_manager=self.manager,
                username=self.username,
                password=self.password,
                client_keys=self.client_keys,
            )
            await self._ssh_client.connect()

    async def download(
        self,
        remote_path: str,
        local_path: str,
        recursive: bool = False,
        preserve: bool = False,
    ) -> None:
        """
        Download file(s) from remote via SCP.

        Args:
            remote_path: Path on remote machine.
            local_path: Local destination path.
            recursive: Copy directories recursively.
            preserve: Preserve file permissions and times.
        """
        await self._ensure_connected()

        # Use AsyncSSH's scp function
        await asyncssh.scp(
            (self._ssh_client._conn, remote_path),
            local_path,
            recurse=recursive,
            preserve=preserve,
            block_size=65536,
        )

    async def upload(
        self,
        local_path: str,
        remote_path: str,
        recursive: bool = False,
        preserve: bool = False,
    ) -> None:
        """
        Upload file(s) to remote via SCP.

        Args:
            local_path: Local source path.
            remote_path: Path on remote machine.
            recursive: Copy directories recursively.
            preserve: Preserve file permissions and times.
        """
        await self._ensure_connected()

        # Use AsyncSSH's scp function
        await asyncssh.scp(
            local_path,
            (self._ssh_client._conn, remote_path),
            recurse=recursive,
            preserve=preserve,
            block_size=65536,
        )

    async def close(self) -> None:
        """Close the SSH connection."""
        if self._ssh_client:
            await self._ssh_client.close()
            self._ssh_client = None

    async def __aenter__(self) -> "WormholeSCP":
        """Async context manager entry."""
        await self._ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
