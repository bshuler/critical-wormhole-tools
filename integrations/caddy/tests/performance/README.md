# Performance Tests

Baseline performance tests for wormhole operations. These tests are marked as `slow` and are not run in CI by default.

## Running the Tests

```bash
# Run all performance tests
pytest -m slow tests/performance/

# Run with verbose output showing timings
pytest -m slow -s tests/performance/

# Run specific test
pytest -m slow tests/performance/test_performance.py::test_large_file_checksum

# Skip performance tests (default in CI)
pytest -m "not slow"
```

## Test Cases

1. **test_large_file_checksum** - MD5 of 100MB file completes in <5s
2. **test_manifest_scan_1000_files** - Directory scan of 1000 files completes in <10s
3. **test_concurrent_channels** - 100 tunnel channels without memory leak
4. **test_http_response_throughput** - >1000 req/s locally (mocked)
5. **test_rsync_incremental_scan** - 10000 file manifest completes in <30s

## CI Behavior

Performance tests are automatically skipped in CI environments (when `CI` or `GITHUB_ACTIONS` environment variables are set).

## Requirements

- pytest
- psutil (optional, for memory leak detection in test_concurrent_channels)
