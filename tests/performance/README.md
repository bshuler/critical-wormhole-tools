# Performance Tests

This directory contains performance benchmarking tests for wormhole operations.

## Overview

These tests measure the performance characteristics of various wormhole operations:
- Message throughput
- File transfer speed
- Connection latency
- Dilation setup time
- Concurrent connection handling

## Running Performance Tests

Performance tests are marked with `@pytest.mark.performance` and `@pytest.mark.slow` and are skipped by default.

### Run all performance tests

```bash
pytest tests/performance/ -m performance
```

### Run specific performance test categories

```bash
# Throughput tests only
pytest tests/performance/test_throughput_scaffold.py -m performance

# Latency tests only
pytest tests/performance/test_latency_scaffold.py -m performance
```

### Run with verbose output

```bash
pytest tests/performance/ -m performance -v
```

### Run without skipping (when tests are implemented)

```bash
pytest tests/performance/ -m performance --run-performance
```

## Test Categories

### Throughput Tests (`test_throughput_scaffold.py`)
Measures data transfer rates:
- Messages per second through WormholeManager
- Bytes per second for file transfers
- Sustained throughput under load

### Latency Tests (`test_latency_scaffold.py`)
Measures timing characteristics:
- Connection establishment time
- Dilation setup latency
- Round-trip message latency
- Concurrent connection overhead

## Writing Performance Tests

When implementing performance tests:

1. **Use appropriate markers**:
   ```python
   @pytest.mark.performance
   @pytest.mark.slow
   @pytest.mark.asyncio
   ```

2. **Include statistical analysis**:
   - Run multiple iterations
   - Calculate mean, median, std dev
   - Set threshold assertions

3. **Document expected performance**:
   - Add docstrings with baseline expectations
   - Note hardware/network assumptions
   - Document test methodology

4. **Clean up resources**:
   - Use fixtures for setup/teardown
   - Ensure connections are closed
   - Clean up temporary files

## Fixtures

See `conftest.py` for shared fixtures:
- `performance_metrics`: Collect and report performance data
- `temp_test_dir`: Temporary directory for file operations
- `wormhole_pair`: Pre-configured sender/receiver pair

## Interpreting Results

Performance test results should be compared against baselines and trended over time.

Typical expectations (baseline hardware):
- Message throughput: 1000+ messages/sec (small messages)
- File transfer: 50+ MB/sec (local network)
- Connection latency: <500ms (internet), <100ms (local)
- Dilation setup: <2 seconds

Results will vary significantly based on:
- Network conditions (bandwidth, latency, packet loss)
- Hardware (CPU, memory, disk I/O)
- System load
- Python implementation and version

## TODO

- [ ] Implement throughput test scenarios
- [ ] Implement latency test scenarios
- [ ] Add statistical analysis utilities
- [ ] Create baseline performance database
- [ ] Add CI integration for performance regression detection
- [ ] Add memory usage profiling
- [ ] Add CPU usage profiling
