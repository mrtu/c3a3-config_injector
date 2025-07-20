# Testing Guide

This document provides comprehensive instructions for running tests in the Configuration Wrapping Framework project.

## Overview

The project uses pytest as the primary testing framework with comprehensive test coverage across all components. Tests are organized by functionality and include unit tests, integration tests, and end-to-end scenarios.

## Prerequisites

### Development Environment Setup

1. **Clone and set up the project**:
   ```bash
   git clone <repository-url>
   cd config_injector
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install the project with development dependencies**:
   ```bash
   pip install -e .
   pip install -e ".[dev]"
   ```

   This installs all testing dependencies including:
   - pytest>=7.0.0
   - pytest-cov>=4.0.0
   - pytest-approvaltests>=0.2.4
   - black, ruff, mypy (for code quality)

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest

# Run tests with verbose output
python -m pytest -v

# Run tests in the tests/ directory explicitly
python -m pytest tests/
```

### Coverage Reports

The project is configured to automatically generate coverage reports:

```bash
# Run tests with coverage (default configuration)
python -m pytest

# Generate coverage report in terminal
python -m pytest --cov=src/config_injector --cov-report=term-missing

# Generate HTML coverage report
python -m pytest --cov=src/config_injector --cov-report=html

# Generate both terminal and HTML reports
python -m pytest --cov=src/config_injector --cov-report=term-missing --cov-report=html
```

The HTML coverage report will be generated in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view detailed coverage information.

### Running Specific Tests

```bash
# Run a specific test file
python -m pytest tests/test_basic.py

# Run a specific test function
python -m pytest tests/test_basic.py::test_token_expansion

# Run tests matching a pattern
python -m pytest -k "token"

# Run tests for a specific component
python -m pytest tests/test_providers.py tests/test_injectors.py
```

### Test Categories

The test suite is organized into several categories:

#### Core Functionality Tests
```bash
# Basic framework functionality
python -m pytest tests/test_basic.py

# Core runtime and context
python -m pytest tests/test_execution.py

# Validation and error handling
python -m pytest tests/test_validation.py
```

#### Provider Tests
```bash
# Environment provider
python -m pytest tests/test_env_passthrough.py

# Dotenv provider with hierarchical loading
python -m pytest tests/test_dotenv_hierarchical.py

# Bitwarden Secrets provider
python -m pytest tests/test_bws_provider.py
```

#### Injector Tests
```bash
# All injector types (env_var, named, positional, etc.)
python -m pytest tests/test_injectors.py
```

#### Integration Tests
```bash
# Basic integration scenarios
python -m pytest tests/test_integration.py

# Comprehensive end-to-end tests
python -m pytest tests/test_integration_comprehensive.py
```

#### Feature-Specific Tests
```bash
# Dry run functionality
python -m pytest tests/test_dry_run.py

# Stream management and logging
python -m pytest tests/test_streams.py

# Sensitive data masking
python -m pytest tests/test_masking.py

# CLI interface
python -m pytest tests/test_cli_flags.py

# Sequence counter functionality
python -m pytest tests/test_sequence_counter.py
```

## Test Configuration

The project uses pytest configuration defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src/config_injector --cov-report=term-missing --cov-report=html"
```

### Customizing Test Runs

You can override the default configuration:

```bash
# Run without coverage
python -m pytest --no-cov

# Change coverage output format
python -m pytest --cov-report=xml

# Run with different verbosity
python -m pytest -vv  # Very verbose
python -m pytest -q   # Quiet mode

# Stop on first failure
python -m pytest -x

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
python -m pytest -n auto
```

## Debugging Tests

### Running Tests with Debug Output

```bash
# Show print statements and debug output
python -m pytest -s

# Show local variables on failures
python -m pytest --tb=long

# Drop into debugger on failures
python -m pytest --pdb

# Show the slowest tests
python -m pytest --durations=10
```

### Debug Logging in Tests

The framework supports debug logging in tests. Add debug messages with the `[DEBUG_LOG]` prefix:

```python
def test_example():
    print("[DEBUG_LOG] Starting test execution")
    # Your test code here
    print(f"[DEBUG_LOG] Variable value: {some_variable}")
```

## Writing New Tests

### Test Structure

Follow these conventions when writing new tests:

1. **File naming**: `test_<component>.py`
2. **Function naming**: `test_<functionality>`
3. **Use descriptive docstrings**
4. **Follow the existing patterns**

### Example Test Template

```python
"""Tests for [component name]."""

import pytest
from pathlib import Path

from config_injector.models import Spec, Target
from config_injector.core import build_runtime_context


def test_example_functionality():
    """Test description of what this test verifies."""
    # Arrange
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Act
    context = build_runtime_context(spec)

    # Assert
    assert context.pid > 0
    assert context.home is not None


def test_error_handling():
    """Test error conditions and edge cases."""
    with pytest.raises(ValueError, match="Expected error message"):
        # Code that should raise an error
        pass
```

### Testing Best Practices

1. **Test both success and failure cases**
2. **Use temporary files/directories for file system tests**
3. **Mock external dependencies when appropriate**
4. **Test edge cases and boundary conditions**
5. **Keep tests focused and independent**
6. **Use descriptive assertion messages**

### Fixtures and Utilities

Common test utilities and fixtures:

```python
import tempfile
from pathlib import Path

# Temporary directory fixture
@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

# Environment variable fixture
@pytest.fixture
def test_env(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "test_value")
    yield
```

## Continuous Integration

The test suite is designed to run in CI environments. Key considerations:

- Tests should be deterministic and not depend on external services
- Use appropriate timeouts for integration tests
- Mock external dependencies
- Ensure tests clean up after themselves

## Performance Testing

For performance-sensitive components:

```bash
# Run tests with timing information
python -m pytest --durations=0

# Profile test execution (requires pytest-profiling)
pip install pytest-profiling
python -m pytest --profile
```

## Test Coverage Goals

The project aims for high test coverage:

- **Minimum**: 80% overall coverage
- **Target**: 90%+ coverage for core components
- **Critical paths**: 100% coverage for security-sensitive code

Check current coverage:

```bash
python -m pytest --cov=src/config_injector --cov-report=term-missing
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure the project is installed in development mode (`pip install -e .`)
2. **Missing dependencies**: Install dev dependencies (`pip install -e ".[dev]"`)
3. **Path issues**: Run tests from the project root directory
4. **Environment conflicts**: Use a clean virtual environment

### Getting Help

- Check the test output for detailed error messages
- Use `pytest --tb=long` for full tracebacks
- Review the existing tests for patterns and examples
- Consult the main README.md for project setup instructions

## Integration with Development Workflow

### Pre-commit Testing

Run tests before committing:

```bash
# Quick test run
python -m pytest tests/test_basic.py

# Full test suite
python -m pytest

# With coverage check
python -m pytest --cov=src/config_injector --cov-fail-under=80
```

### Code Quality Checks

The project includes additional quality tools:

```bash
# Type checking
mypy src/config_injector/

# Code formatting
black src/ tests/

# Linting
ruff check src/ tests/
```

Run all quality checks:

```bash
# Format code
black src/ tests/

# Check types
mypy src/config_injector/

# Lint code
ruff check src/ tests/

# Run tests with coverage
python -m pytest
```
