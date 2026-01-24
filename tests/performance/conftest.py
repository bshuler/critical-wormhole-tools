"""Shared fixtures for performance tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
import time


@pytest.fixture
def performance_metrics():
    """
    Fixture to collect and report performance metrics.

    Usage:
        metrics = performance_metrics
        metrics.start('operation_name')
        # ... perform operation ...
        metrics.end('operation_name')

        # Get results
        duration = metrics.get_duration('operation_name')
        stats = metrics.get_stats('operation_name')
    """
    class PerformanceMetrics:
        def __init__(self):
            self.timings: Dict[str, List[float]] = {}
            self.start_times: Dict[str, float] = {}

        def start(self, operation: str) -> None:
            """Start timing an operation."""
            self.start_times[operation] = time.perf_counter()

        def end(self, operation: str) -> float:
            """End timing an operation and return duration."""
            if operation not in self.start_times:
                raise ValueError(f"No start time recorded for {operation}")

            duration = time.perf_counter() - self.start_times[operation]

            if operation not in self.timings:
                self.timings[operation] = []
            self.timings[operation].append(duration)

            del self.start_times[operation]
            return duration

        def get_duration(self, operation: str, iteration: int = -1) -> float:
            """Get duration for a specific operation iteration."""
            if operation not in self.timings:
                raise ValueError(f"No timings recorded for {operation}")
            return self.timings[operation][iteration]

        def get_stats(self, operation: str) -> Dict[str, float]:
            """Get statistical summary of operation timings."""
            if operation not in self.timings or not self.timings[operation]:
                raise ValueError(f"No timings recorded for {operation}")

            timings = self.timings[operation]
            return {
                'count': len(timings),
                'mean': sum(timings) / len(timings),
                'min': min(timings),
                'max': max(timings),
                'median': sorted(timings)[len(timings) // 2],
            }

        def report(self) -> str:
            """Generate a formatted report of all metrics."""
            lines = ["Performance Metrics:"]
            for operation in self.timings:
                stats = self.get_stats(operation)
                lines.append(f"\n{operation}:")
                lines.append(f"  Count:  {stats['count']}")
                lines.append(f"  Mean:   {stats['mean']:.4f}s")
                lines.append(f"  Median: {stats['median']:.4f}s")
                lines.append(f"  Min:    {stats['min']:.4f}s")
                lines.append(f"  Max:    {stats['max']:.4f}s")
            return "\n".join(lines)

    return PerformanceMetrics()


@pytest.fixture
def temp_test_dir():
    """
    Create a temporary directory for performance tests.

    Automatically cleaned up after test completes.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="wormhole_perf_test_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def wormhole_pair():
    """
    Create a pre-configured sender/receiver wormhole pair.

    Returns a tuple of (sender_manager, receiver_manager, code).

    TODO: Implement this fixture when needed for performance tests.
    This should create two WormholeManager instances and establish
    a connection between them for testing.
    """
    # Placeholder fixture - returns mock objects for tests that don't actually use it
    # Tests that use wormhole_pair need to implement actual WormholeManager usage
    yield (None, None, None)

    # TODO: Implementation should:
    # 1. Create sender WormholeManager instance
    # 2. Create receiver WormholeManager instance
    # 3. Generate/share wormhole code
    # 4. Establish connection
    # 5. Yield the pair
    # 6. Clean up connections in finally block

    # Example structure:
    # sender = WormholeManager(...)
    # receiver = WormholeManager(...)
    # try:
    #     code = await sender.allocate_code()
    #     await asyncio.gather(
    #         sender.connect(code),
    #         receiver.connect(code)
    #     )
    #     yield (sender, receiver, code)
    # finally:
    #     await sender.close()
    #     await receiver.close()


@pytest.fixture
def large_test_file(temp_test_dir):
    """
    Create a large test file for file transfer performance tests.

    Returns path to a file with random data.
    Default size: 100MB

    TODO: Make size configurable via pytest.ini or environment variable.
    """
    file_path = temp_test_dir / "large_test_file.bin"
    size_mb = 100

    # Generate file with random data
    # Using urandom for better performance than alternatives
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(file_path, 'wb') as f:
        for _ in range(size_mb):
            f.write(b'\x00' * chunk_size)  # TODO: Use os.urandom() for realistic data

    return file_path


@pytest.fixture(autouse=True)
def performance_test_marker(request):
    """
    Performance tests are marked with @pytest.mark.performance.

    They can be run with: pytest -m performance
    Or included in regular runs without filtering.
    """
    # This fixture allows performance tests to run normally
    # Tests are no longer auto-skipped
    pass
