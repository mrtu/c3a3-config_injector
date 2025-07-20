# Configuration Wrapping Framework Documentation

Welcome to the comprehensive documentation for the Configuration Wrapping Framework. This framework provides a declarative YAML approach to wrapping executables with configuration injection from multiple sources.

## Quick Navigation

- **[Usage Guide](USAGE.md)** - Complete guide to using the framework
- **[Configuration Providers](PROVIDERS.md)** - Detailed provider documentation
- **[Configuration Injectors](INJECTORS.md)** - Complete injector reference
- **[Token System](TOKENS.md)** - Token expansion and syntax
- **[Command Line Interface](CLI.md)** - CLI usage and commands
- **[Examples](EXAMPLES.md)** - Real-world examples and use cases

## What is the Configuration Wrapping Framework?

The Configuration Wrapping Framework is a powerful tool that allows you to:

- **Gather configuration** from multiple sources (environment variables, .env files, secrets vaults)
- **Inject resolved values** as environment variables, CLI parameters, or file inputs
- **Control execution context** and output redirection
- **Provide reproducible, testable runs** across environments

## Key Features

### 🔧 Configuration Providers
- **Environment Variables** - Read from host environment
- **Dotenv Files** - Hierarchical .env file loading
- **Bitwarden Secrets** - Secure secrets management
- **Filtering** - Include/exclude patterns for data control

### 💉 Configuration Injectors
- **Environment Variables** - Inject as process environment
- **Named Arguments** - Inject as CLI flags (--flag=value)
- **Positional Arguments** - Inject as command arguments
- **File Injection** - Create temporary files with content
- **Stdin Fragments** - Aggregate content for stdin

### 🔑 Token System
- **Dynamic Values** - `${ENV:VAR}`, `${PROVIDER:id:key}`
- **System Tokens** - `${HOME}`, `${PID}`, `${DATE:format}`
- **Fallback Values** - `${ENV:VAR|default}`
- **Type Coercion** - Automatic type conversion

### 🛡️ Security Features
- **Masking** - Hide sensitive data in logs
- **Conditional Injection** - `when` expressions
- **Required Validation** - Fail fast on missing values
- **Strict Mode** - Enhanced validation

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd c3a3-config_injector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# For Bitwarden Secrets integration
pip install -e ".[bws]"
```

### Basic Example

Create a simple specification file (`my-app.yaml`):

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

Run the framework:

```bash
# Dry run to see what would be executed
python -m config_injector.cli run my-app.yaml --dry-run

# Execute the specification
python -m config_injector.cli run my-app.yaml

# Validate the specification
python -m config_injector.cli validate my-app.yaml
```

## Documentation Structure

### [Usage Guide](USAGE.md)
The main usage guide covers:
- Quick start and installation
- Core concepts and architecture
- Configuration providers and injectors
- Token system and CLI interface
- Advanced features and best practices

### [Configuration Providers](PROVIDERS.md)
Detailed documentation for all provider types:
- Environment Provider
- Dotenv Provider (with hierarchical loading)
- Bitwarden Secrets Provider
- Filtering and masking options

### [Configuration Injectors](INJECTORS.md)
Complete reference for all injector types:
- Environment Variable Injector
- Named Argument Injector
- Positional Argument Injector
- File Injector
- Stdin Fragment Injector
- Type coercion and conditional injection

### [Token System](TOKENS.md)
Comprehensive token documentation:
- Token syntax and types
- Environment and provider tokens
- System tokens (HOME, PID, DATE, TIME)
- Dynamic tokens (SEQ, UUID)
- Fallback values and expansion

### [Command Line Interface](CLI.md)
CLI usage and commands:
- Run command with dry-run support
- Validate command with strict mode
- Explain command for understanding specs
- Print schema for tooling integration
- Error handling and debugging

### [Examples](EXAMPLES.md)
Real-world examples and use cases:
- Basic examples for getting started
- Web application configurations
- Database and microservices examples
- Development vs production setups
- Security-focused configurations
- Complex multi-service scenarios

## Architecture Overview

The framework follows a clean architecture with these components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YAML Spec     │───▶│  Pydantic       │───▶│  Runtime        │
│   Loader        │    │  Models         │    │  Context        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Providers     │◀───│  Token Engine   │───▶│  Injectors      │
│   (env/dotenv)  │    │  (${...} exp)   │    │  (env/argv)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Execution     │
                       │   Engine        │
                       └─────────────────┘
```

## Key Components

1. **Configuration Providers** - Sources of configuration data
2. **Configuration Injectors** - Define how values are injected
3. **Token Engine** - Expands `${...}` tokens in configuration
4. **Runtime Context** - Builds execution context
5. **Execution Engine** - Runs the target process

## Getting Help

### Common Tasks

- **Getting Started**: See [Usage Guide](USAGE.md#quick-start)
- **Understanding Tokens**: See [Token System](TOKENS.md)
- **CLI Commands**: See [Command Line Interface](CLI.md)
- **Real Examples**: See [Examples](EXAMPLES.md)

### Validation and Debugging

```bash
# Validate a specification
python -m config_injector.cli validate spec.yaml --strict

# Explain what a specification does
python -m config_injector.cli explain spec.yaml

# Dry run to preview execution
python -m config_injector.cli run spec.yaml --dry-run --verbose

# Get JSON schema for tooling
python -m config_injector.cli print-schema
```

### Best Practices

1. **Always validate** specifications before running
2. **Use dry-run** during development
3. **Provide fallback values** for tokens
4. **Mark sensitive data** for masking
5. **Use profiles** for environment-specific settings

## Contributing

For development and contribution guidelines, see the main project README and development documentation.

---

**Need help?** Start with the [Usage Guide](USAGE.md) for a comprehensive introduction to the framework. 