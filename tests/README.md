# Test Suite Documentation

## Overview
This directory contains the test suite for Critical Wormhole Tools.

## Test Pyramid

| Tier | Directory | Description | Run Command |
|------|-----------|-------------|-------------|
| Unit | tests/unit/ | Fast, isolated tests | `pytest tests/unit/` |
| Functional | tests/functional/ | Component tests | `pytest tests/functional/` |
| Integration | tests/integration/ | Network tests | `pytest tests/integration/` |
| Performance | tests/performance/ | Benchmark tests | `pytest tests/performance/` |

## Running Tests

### All Tests
```bash
make test
# or
pytest
```

### By Category
```bash
pytest tests/unit/           # Unit tests only
pytest tests/functional/     # Functional tests only
pytest tests/integration/    # Integration tests only
pytest tests/performance/    # Performance tests only
```

### With Coverage
```bash
make test-coverage
# or
pytest --cov=wh --cov-report=html
```

## Test Markers

- `@pytest.mark.slow` - Tests that take >1s
- `@pytest.mark.network` - Tests requiring network
- `@pytest.mark.optional` - Tests for optional dependencies

## Writing New Tests

1. **Unit tests first** - When fixing a bug, write a unit test that reproduces it
2. **Isolation** - Unit tests should not require network or external services
3. **Naming** - Use `test_<module>_<function>_<scenario>.py` format
4. **Fixtures** - Prefer fixtures over setUp/tearDown

## Test Counts

- Total: 1338 tests
- Unit: ~800 tests
- Functional: ~200 tests
- Integration: ~250 tests
- Performance: ~50 tests
