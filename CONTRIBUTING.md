# Contributing to Critical Wormhole Tools

Thank you for your interest in contributing to Critical Wormhole Tools! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include:**
   - Python version (`python --version`)
   - OS and version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and stack traces

### Suggesting Features

1. **Check the [ROADMAP.md](ROADMAP.md)** to see if it's already planned
2. **Open a discussion** first for large features
3. **Use the feature request template**
4. **Explain the use case** - why is this needed?

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Add tests** for new functionality
5. **Run tests**: `pytest`
6. **Run linting**: `ruff check src tests`
7. **Commit with descriptive message**
8. **Push and create PR**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cwt.git
cd cwt

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
```

## Code Style

- **Python 3.10+** features are welcome
- **Type hints** are required for all public APIs
- **Docstrings** in Google style for all public functions/classes
- **Line length**: 88 characters (Black-compatible)
- **Linting**: We use `ruff` for linting

### Example Code Style

```python
async def transfer_file(
    source: str,
    destination: str,
    *,
    recursive: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
) -> TransferResult:
    """
    Transfer a file through the wormhole connection.

    Args:
        source: Source file path.
        destination: Destination file path.
        recursive: If True, transfer directories recursively.
        progress: Optional callback for progress updates (bytes_sent, total_bytes).

    Returns:
        TransferResult containing transfer statistics.

    Raises:
        ConnectionError: If wormhole connection is lost.
        FileNotFoundError: If source file doesn't exist.
    """
    ...
```

## Testing

### Test Structure

```
tests/
├── unit/           # Fast, isolated unit tests
├── functional/     # Tests with mocked dependencies
└── integration/    # Tests against real wormhole relay
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit

# With coverage
pytest --cov=wh --cov-report=html

# Specific test file
pytest tests/unit/test_wormhole_manager.py

# Specific test
pytest tests/unit/test_wormhole_manager.py::TestWormholeManager::test_init_defaults
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestMyFeature:
    """Tests for MyFeature class."""

    def test_basic_functionality(self):
        """Test that basic functionality works."""
        result = my_function(input_value)
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        result = await my_async_function()
        assert result is not None

    def test_error_handling(self):
        """Test that errors are handled correctly."""
        with pytest.raises(ValueError, match="Invalid input"):
            my_function(invalid_input)
```

## Commit Messages

We follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(ssh): add support for key-based authentication
fix(scp): handle binary files correctly
docs(readme): add installation instructions for Windows
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create PR with version bump
4. After merge, create GitHub release
5. GitHub Actions will publish to PyPI

## Questions?

- **GitHub Discussions**: For questions and ideas
- **GitHub Issues**: For bugs and feature requests

Thank you for contributing!
