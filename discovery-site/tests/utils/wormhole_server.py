"""Wormhole server management for integration tests."""

import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional


class WormholeServer:
    """Context manager for running wh listen --serve.

    Starts a wormhole server serving files from a directory and extracts
    the generated wormhole code for test use.

    Usage:
        with WormholeServer(serve_dir) as server:
            print(f"Connect to: {server.code}")
            # ... run tests ...
    """

    # Pattern to extract wormhole code from server output
    CODE_PATTERN = re.compile(r"(?:code:|Listening on code:)\s*(\d+-\w+-\w+)", re.IGNORECASE)

    def __init__(self, serve_dir: Path, timeout: int = 60):
        """Initialize the wormhole server.

        Args:
            serve_dir: Directory to serve via wormhole
            timeout: Seconds to wait for server to start and emit code
        """
        self.serve_dir = Path(serve_dir)
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.code: Optional[str] = None
        self._output_lines: list[str] = []
        self._output_thread: Optional[threading.Thread] = None
        self._stop_output = False

    def start(self) -> str:
        """Start the wormhole server and return the code.

        Returns:
            The wormhole code (e.g., "7-guitar-sunset")

        Raises:
            RuntimeError: If server exits unexpectedly
            TimeoutError: If code not received within timeout
            FileNotFoundError: If serve_dir doesn't exist
        """
        if not self.serve_dir.exists():
            raise FileNotFoundError(f"Serve directory not found: {self.serve_dir}")

        # Use -v for verbose output to see what's happening
        # Browser now properly checks for WebRTC support and skips dilation
        # when peer only supports TCP-based dilation (direct-tcp-v1, relay-v1)
        cmd = [sys.executable, "-m", "wh.cli.main", "-v", "listen", "--serve", str(self.serve_dir)]

        env = os.environ.copy()
        # Ensure unbuffered output
        env["PYTHONUNBUFFERED"] = "1"

        print(f"[WormholeServer] Starting: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        start_time = time.time()

        while time.time() - start_time < self.timeout:
            if self.process.poll() is not None:
                # Process exited unexpectedly
                remaining = self.process.stdout.read() if self.process.stdout else ""
                self._output_lines.append(remaining)
                output = "".join(self._output_lines)
                raise RuntimeError(f"wh listen exited unexpectedly (code {self.process.returncode}):\n{output}")

            line = self.process.stdout.readline() if self.process.stdout else ""
            if line:
                self._output_lines.append(line)
                print(f"[wh listen] {line.rstrip()}")

                # Try to extract wormhole code
                match = self.CODE_PATTERN.search(line)
                if match:
                    self.code = match.group(1)
                    print(f"[WormholeServer] Got code: {self.code}")
                    # Start background thread to continue reading output
                    self._start_output_reader()
                    return self.code

            time.sleep(0.1)

        # Timeout - cleanup and raise
        self.stop()
        output = "".join(self._output_lines)
        raise TimeoutError(f"Timed out waiting for wormhole code after {self.timeout}s:\n{output}")

    def _start_output_reader(self):
        """Start a background thread to continue reading server output."""
        def read_output():
            while not self._stop_output and self.process and self.process.poll() is None:
                try:
                    line = self.process.stdout.readline() if self.process.stdout else ""
                    if line:
                        self._output_lines.append(line)
                        print(f"[wh listen] {line.rstrip()}")
                except Exception:
                    break
                time.sleep(0.01)

        self._output_thread = threading.Thread(target=read_output, daemon=True)
        self._output_thread.start()

    def stop(self):
        """Stop the wormhole server gracefully."""
        if self.process is None:
            return

        # Stop the output reader thread
        self._stop_output = True
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=1)

        print("[WormholeServer] Stopping server...")

        # Try SIGINT first (graceful shutdown)
        try:
            self.process.send_signal(signal.SIGINT)
            self.process.wait(timeout=5)
            print("[WormholeServer] Server stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            print("[WormholeServer] Force killing server...")
            self.process.kill()
            self.process.wait()
            print("[WormholeServer] Server killed")
        except Exception as e:
            print(f"[WormholeServer] Error stopping: {e}")
            try:
                self.process.kill()
            except Exception:
                pass
        finally:
            self.process = None

    def get_output(self) -> str:
        """Get all captured server output."""
        return "".join(self._output_lines)

    def __enter__(self) -> "WormholeServer":
        """Context manager entry - starts the server."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops the server."""
        self.stop()
        return False  # Don't suppress exceptions
