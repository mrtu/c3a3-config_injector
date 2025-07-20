# Configuration Wrapping Framework

A declarative YAML framework for wrapping executables with configuration injection from multiple sources.

## Overview

The Configuration Wrapping Framework allows you to:

- Gather configuration from multiple sources (environment variables, dotenv files, secrets vaults)
- Inject resolved values as environment variables, CLI parameters, or file inputs
- Control execution context and output redirection
- Provide reproducible, testable runs across environments

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd c3a3-config_injector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# For development with testing tools
pip install -e ".[dev]"

# For Bitwarden Secrets integration
pip install -e ".[bws]"
```

## Quick Start

1. **Create a specification file** (`example.yaml`):

```yaml
version: "0.1"
env_passthrough: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

configuration_injectors:
  - name: app_environment
    kind: env_var
    aliases: [APP_ENV]
    sources: ["${ENV:APP_ENV}", "development"]

target:
  working_dir: "/tmp"
  command: ["echo", "Hello from Configuration Wrapping Framework!"]
```

2. **Run the framework**:

```bash
# Dry run to see what would be executed
python -m config_injector.cli run example.yaml --dry-run

# Execute the specification
python -m config_injector.cli run example.yaml

# Validate the specification
python -m config_injector.cli validate example.yaml
```

## Features

### ✅ Implemented (v0.1)

- **YAML Specification Loading**: Load and validate configuration specs
- **Environment Provider**: Read from host environment variables
- **Token Expansion**: Support for `${ENV:VAR}`, `${HOME}`, `${PID}`, etc.
- **Basic Injectors**: Environment variables and named parameters
- **Runtime Context**: Build execution context with environment snapshot
- **Dry Run Mode**: Preview what would be executed without running

### 🚧 In Progress

- **Dotenv Provider**: Load from .env files (hierarchical support)
- **BWS Provider**: Bitwarden Secrets integration (optional, requires `pip install config-injector[bws]`)
- **File Injectors**: Write values to temporary files
- **Stream Management**: Output redirection and logging
- **CLI Interface**: Full command-line interface

### 📋 Planned

- **Type Coercion**: Automatic type conversion (int, bool, json, etc.)
- **Conditional Injection**: `when` expressions
- **Masking**: Sensitive data protection
- **Profiles**: Environment-specific overrides
- **Cross-host Execution**: SSH, Docker, Kubernetes runners

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Documentation Index](docs/README.md)** - Overview and quick navigation
- **[Usage Guide](docs/USAGE.md)** - Complete guide to using the framework
- **[Configuration Providers](docs/PROVIDERS.md)** - Detailed provider documentation
- **[Configuration Injectors](docs/INJECTORS.md)** - Complete injector reference
- **[Token System](docs/TOKENS.md)** - Token expansion and syntax
- **[Command Line Interface](docs/CLI.md)** - CLI usage and commands
- **[Examples](docs/EXAMPLES.md)** - Real-world examples and use cases

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/
```

For detailed testing information, see [TESTING.md](TESTING.md).

### Project Structure

```
config_injector/
├── src/config_injector/
│   ├── __init__.py      # Package exports
│   ├── models.py        # Pydantic models
│   ├── core.py          # Core functionality
│   ├── providers.py     # Configuration providers
│   ├── token_engine.py  # Token expansion
│   ├── injectors.py     # Value injection
│   ├── streams.py       # Output management
│   ├── cli.py          # Command-line interface
│   └── types.py        # Type definitions
├── tests/              # Test suite
├── docs/               # Documentation
├── example.yaml        # Example specification
├── demo.py            # Basic demo script
└── pyproject.toml     # Project configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

For development roadmap and architecture details, see [TODO.md](TODO.md).

## License

SPDX-License-Identifier: Prosperity-3.0.0
© 2025 ã — see LICENSE.md for terms.
