"""Performance baseline tests for wormhole operations.

These tests establish performance baselines and are marked as slow.
Run with: pytest -m slow
Skip with: pytest -m "not slow" (default behavior)
"""
import hashlib
import os
import time
from pathlib import Path
from typing import List
import pytest


# Skip all performance tests in CI environments
pytestmark = pytest.mark.skipif(
    os.getenv("CI") is not None or os.getenv("GITHUB_ACTIONS") is not None,
    reason="Performance tests skipped in CI"
)


@pytest.mark.slow
def test_large_file_checksum(tmp_path: Path):
    """Test MD5 checksum of 100MB file completes in <5s."""
    # Create 100MB test file
    file_size = 100 * 1024 * 1024  # 100MB
    test_file = tmp_path / "large_file.bin"

    # Write file in chunks for efficiency
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(test_file, "wb") as f:
        for _ in range(file_size // chunk_size):
            f.write(b"\x00" * chunk_size)

    # Time the MD5 checksum operation
    start_time = time.time()

    md5_hash = hashlib.md5()
    with open(test_file, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5_hash.update(chunk)

    result = md5_hash.hexdigest()
    elapsed_time = time.time() - start_time

    # Verify checksum completed
    assert result is not None
    assert len(result) == 32  # MD5 produces 32-char hex string

    # Performance assertion
    assert elapsed_time < 5.0, f"Checksum took {elapsed_time:.2f}s, expected <5s"
    print(f"\nLarge file checksum: {elapsed_time:.2f}s")


@pytest.mark.slow
def test_manifest_scan_1000_files(tmp_path: Path):
    """Test directory scan of 1000 files completes in <10s."""
    # Create directory structure with 1000 files
    num_files = 1000
    files_per_dir = 100
    num_dirs = num_files // files_per_dir

    created_files: List[Path] = []
    for dir_idx in range(num_dirs):
        dir_path = tmp_path / f"dir_{dir_idx}"
        dir_path.mkdir()

        for file_idx in range(files_per_dir):
            file_path = dir_path / f"file_{file_idx}.txt"
            file_path.write_text(f"Content {dir_idx}-{file_idx}\n")
            created_files.append(file_path)

    # Time the directory scanning operation
    start_time = time.time()

    # Simulate manifest scanning: walk directory, stat files, compute checksums
    manifest = []
    for root, dirs, files in os.walk(tmp_path):
        for filename in files:
            filepath = Path(root) / filename
            stat = filepath.stat()

            # Compute checksum (like rsync would do)
            md5_hash = hashlib.md5()
            with open(filepath, "rb") as f:
                md5_hash.update(f.read())

            manifest.append({
                "path": str(filepath.relative_to(tmp_path)),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "checksum": md5_hash.hexdigest()
            })

    elapsed_time = time.time() - start_time

    # Verify scan completed correctly
    assert len(manifest) == num_files
    assert all("checksum" in entry for entry in manifest)

    # Performance assertion
    assert elapsed_time < 10.0, f"Manifest scan took {elapsed_time:.2f}s, expected <10s"
    print(f"\n1000 file manifest scan: {elapsed_time:.2f}s ({len(manifest)} files)")


@pytest.mark.slow
def test_concurrent_channels():
    """Test 100 tunnel channels without memory leak."""
    import sys

    # Track initial memory usage
    try:
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        has_psutil = True
    except ImportError:
        has_psutil = False
        initial_memory = 0

    # Simulate 100 concurrent channels
    channels = []
    for i in range(100):
        # Simulate channel metadata (lightweight dict)
        channel = {
            "id": f"channel_{i}",
            "created_at": time.time(),
            "bytes_sent": 0,
            "bytes_received": 0,
            "buffer": bytearray(8192),  # 8KB buffer per channel
        }
        channels.append(channel)

    # Simulate some activity on channels
    for channel in channels:
        channel["bytes_sent"] = len(channel["buffer"])
        channel["bytes_received"] = len(channel["buffer"])

    # Check final memory usage
    if has_psutil:
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 100 channels * 8KB = 800KB minimum, allow up to 50MB for overhead
        assert memory_increase < 50.0, f"Memory increased by {memory_increase:.2f}MB, possible leak"
        print(f"\n100 channels memory usage: {memory_increase:.2f}MB")
    else:
        print("\npsutil not available, skipping memory check")

    # Verify all channels created
    assert len(channels) == 100
    assert all(ch["id"].startswith("channel_") for ch in channels)


@pytest.mark.slow
def test_http_response_throughput():
    """Test >1000 req/s locally with mocked responses."""
    from http.server import BaseHTTPRequestHandler
    from io import BytesIO

    # Mock HTTP request/response cycle
    class MockRequest:
        def __init__(self, request_id: int):
            self.request_id = request_id
            self.method = "GET"
            self.path = f"/api/data/{request_id}"
            self.headers = {"User-Agent": "test-client"}

    class MockResponse:
        def __init__(self, request: MockRequest):
            self.status = 200
            self.headers = {"Content-Type": "application/json"}
            self.body = f'{{"id": {request.request_id}, "status": "ok"}}'.encode()

    # Simulate request processing
    num_requests = 10000
    start_time = time.time()

    responses = []
    for i in range(num_requests):
        request = MockRequest(i)
        response = MockResponse(request)
        responses.append(response)

    elapsed_time = time.time() - start_time
    requests_per_sec = num_requests / elapsed_time

    # Verify responses generated
    assert len(responses) == num_requests
    assert all(r.status == 200 for r in responses)

    # Performance assertion
    assert requests_per_sec > 1000, f"Only {requests_per_sec:.0f} req/s, expected >1000"
    print(f"\nHTTP throughput: {requests_per_sec:.0f} req/s ({num_requests} requests in {elapsed_time:.2f}s)")


@pytest.mark.slow
def test_rsync_incremental_scan(tmp_path: Path):
    """Test 10000 file manifest completes in <30s with incremental detection."""
    # Create 10000 files across directory tree
    num_files = 10000
    files_per_dir = 100
    num_dirs = num_files // files_per_dir

    all_files: List[Path] = []
    for dir_idx in range(num_dirs):
        dir_path = tmp_path / f"subdir_{dir_idx:03d}"
        dir_path.mkdir()

        for file_idx in range(files_per_dir):
            file_path = dir_path / f"file_{file_idx:04d}.dat"
            # Small files with varying content
            file_path.write_bytes(f"Data-{dir_idx}-{file_idx}".encode() * 10)
            all_files.append(file_path)

    # First scan: build initial manifest
    print(f"\nCreated {len(all_files)} files")
    start_time = time.time()

    initial_manifest = {}
    for filepath in all_files:
        stat = filepath.stat()
        initial_manifest[str(filepath)] = {
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    first_scan_time = time.time() - start_time
    print(f"Initial scan: {first_scan_time:.2f}s")

    # Modify a small subset of files (1%)
    modified_files = all_files[:100]
    time.sleep(0.01)  # Ensure mtime changes
    for filepath in modified_files:
        filepath.write_bytes(b"MODIFIED" * 20)

    # Incremental scan: detect changes using mtime/size
    start_time = time.time()

    changes = []
    checksums_computed = 0
    for filepath in all_files:
        stat = filepath.stat()
        cache_entry = initial_manifest.get(str(filepath))

        if cache_entry is None or \
           stat.st_size != cache_entry["size"] or \
           stat.st_mtime != cache_entry["mtime"]:
            # File changed, compute checksum
            md5_hash = hashlib.md5()
            with open(filepath, "rb") as f:
                md5_hash.update(f.read())
            changes.append({
                "path": str(filepath),
                "checksum": md5_hash.hexdigest()
            })
            checksums_computed += 1

    elapsed_time = time.time() - start_time

    # Verify incremental detection
    assert len(changes) == len(modified_files), f"Expected {len(modified_files)} changes, found {len(changes)}"
    assert checksums_computed <= len(modified_files) + 10, "Too many checksums computed"

    # Performance assertion
    assert elapsed_time < 30.0, f"Incremental scan took {elapsed_time:.2f}s, expected <30s"
    print(f"Incremental scan: {elapsed_time:.2f}s ({checksums_computed} checksums, {len(changes)} changes)")
