# Configuration Wrapping Framework - Usage Guide

The Configuration Wrapping Framework is a declarative YAML framework for wrapping executables with configuration injection from multiple sources. This guide covers all features and how to use them effectively.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Configuration Providers](#configuration-providers)
- [Configuration Injectors](#configuration-injectors)
- [Token System](#token-system)
- [Command Line Interface](#command-line-interface)
- [Advanced Features](#advanced-features)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Basic Installation

```bash
# Clone the repository
git clone <repository-url>
cd c3a3-config_injector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Optional Dependencies

```bash
# For development with testing tools
pip install -e ".[dev]"

# For Bitwarden Secrets integration
pip install -e ".[bws]"
```

## Quick Start

### 1. Create a Basic Specification

Create a file named `example.yaml`:

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

### 2. Run the Framework

```bash
# Dry run to see what would be executed
python -m config_injector.cli run example.yaml --dry-run

# Execute the specification
python -m config_injector.cli run example.yaml

# Validate the specification
python -m config_injector.cli validate example.yaml
```

## Core Concepts

### Configuration Providers

Configuration providers are sources of configuration data. The framework supports:

- **Environment Variables**: Read from the host environment
- **Dotenv Files**: Load from `.env` files with hierarchical support
- **Bitwarden Secrets**: Fetch secrets from Bitwarden Secrets Manager
- **Custom Providers**: Extensible provider system

### Configuration Injectors

Configuration injectors define how values are injected into the target process:

- **Environment Variables**: Set environment variables
- **Named Arguments**: Add named CLI arguments (e.g., `--param=value`)
- **Positional Arguments**: Add positional CLI arguments
- **Files**: Write values to temporary files
- **Stdin Fragments**: Append to stdin

### Token System

The framework supports token expansion with syntax like `${ENV:VAR}`, `${PROVIDER:id:key}`, `${DATE:format}`, etc. Tokens can include fallback values using the `|` syntax.

### Runtime Context

The framework builds a runtime context that includes:
- Environment variables
- Provider values
- System information (PID, home directory, etc.)
- Dynamic values (UUIDs, timestamps, sequence numbers)

## Configuration Providers

### Environment Provider

Reads configuration from environment variables:

```yaml
configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true
    filter_chain:
      - include: '^APP_'
      - exclude: '^APP_DEBUG'
```

**Options:**
- `passthrough`: Whether to pass through all environment variables
- `filter_chain`: List of include/exclude patterns (regex)

### Dotenv Provider

Loads configuration from `.env` files:

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv_hier
    name: Hierarchical .env
    hierarchical: true
    filename: .env
    precedence: deep-first
    filter_chain:
      - exclude: '^OS_'
    mask: false
```

**Options:**
- `hierarchical`: Enable hierarchical loading (walks up directory tree)
- `filename`: Name of the dotenv file (default: `.env`)
- `precedence`: Merge strategy (`deep-first` or `shallow-first`)
- `filter_chain`: Include/exclude patterns
- `mask`: Whether to mask sensitive values

### Bitwarden Secrets Provider

Fetches secrets from Bitwarden Secrets Manager:

```yaml
configuration_providers:
  - type: bws
    id: bws
    name: Bitwarden Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true
```

**Requirements:**
- Bitwarden Secrets SDK installed (`pip install config-injector[bws]`)
- Valid vault URL and access token

## Configuration Injectors

### Environment Variable Injector

Sets environment variables for the target process:

```yaml
configuration_injectors:
  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL, DB_URL]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:bws:db-secret-id}
    required: true
    sensitive: true
```

### Named Argument Injector

Adds named CLI arguments:

```yaml
configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config, -c]
    connector: "="
    sources:
      - ${ENV:CONFIG_FILE}
      - "config.yaml"
```

**Connector Options:**
- `=`: `--param=value`
- `space`: `--param value`
- `repeat`: `--param value` (same as space)

### Positional Argument Injector

Adds positional CLI arguments:

```yaml
configuration_injectors:
  - name: input_file
    kind: positional
    order: 1
    sources:
      - ${ENV:INPUT_FILE}
      - "input.txt"
```

### File Injector

Writes values to temporary files:

```yaml
configuration_injectors:
  - name: config_json
    kind: file
    aliases: [--config-file]
    sources:
      - ${PROVIDER:bws:config-secret}
    type: json
```

### Stdin Fragment Injector

Appends content to stdin:

```yaml
configuration_injectors:
  - name: stdin_data
    kind: stdin_fragment
    sources:
      - "additional input data"
```

## Token System

### Basic Token Syntax

Tokens use the `${...}` syntax:

```yaml
sources:
  - ${ENV:APP_ENV}
  - ${PROVIDER:bws:secret-id}
  - ${DATE:YYYY-MM-DD}
  - ${UUID}
```

### Environment Tokens

```yaml
# Basic environment variable
- ${ENV:VAR_NAME}

# With fallback
- ${ENV:VAR_NAME|default_value}
```

### Provider Tokens

```yaml
# Provider value
- ${PROVIDER:provider_id:key_name}

# With fallback
- ${PROVIDER:bws:secret-id|default_value}
```

### System Tokens

```yaml
# User home directory
- ${HOME}

# Process ID
- ${PID}

# UUID
- ${UUID}

# Sequence number
- ${SEQ}
```

### Date and Time Tokens

```yaml
# Date with format
- ${DATE:YYYY-MM-DD}

# Time with format
- ${TIME:HH:mm:ss}

# Combined
- ${DATE:YYYY-MM-DD}_${TIME:HHmmss}
```

### Fallback Values

All tokens support fallback values using the `|` syntax:

```yaml
sources:
  - ${ENV:DEBUG|false}
  - ${PROVIDER:bws:api-key|default-key}
  - ${ENV:PORT|8080}
```

## Command Line Interface

### Basic Commands

```bash
# Run a specification
python -m config_injector.cli run spec.yaml

# Validate a specification
python -m config_injector.cli validate spec.yaml

# Explain a specification
python -m config_injector.cli explain spec.yaml

# Print JSON schema
python -m config_injector.cli print-schema
```

### Run Command Options

```bash
python -m config_injector.cli run spec.yaml \
  --dry-run \
  --profile production \
  --verbose \
  --strict \
  --env-passthrough \
  --mask-defaults
```

**Options:**
- `--dry-run`: Show what would be executed without running
- `--json`: Output in JSON format (with --dry-run)
- `--profile`: Use a specific profile
- `--verbose/-v`: Enable verbose output
- `--quiet/-q`: Enable quiet mode
- `--strict`: Enable strict validation
- `--env-passthrough/--no-env-passthrough`: Override env_passthrough setting
- `--mask-defaults/--no-mask-defaults`: Override mask_defaults setting

### Validate Command Options

```bash
python -m config_injector.cli validate spec.yaml \
  --strict \
  --verbose
```

### Explain Command Options

```bash
python -m config_injector.cli explain spec.yaml \
  --verbose \
  --quiet
```

## Advanced Features

### Type Coercion

Injectors support automatic type conversion:

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources: ["${ENV:PORT|8080}"]

  - name: debug
    kind: env_var
    aliases: [DEBUG]
    type: bool
    sources: ["${ENV:DEBUG|false}"]

  - name: config
    kind: file
    type: json
    sources: ["${PROVIDER:bws:config-secret}"]
```

**Supported Types:**
- `string`: String (default)
- `int`: Integer
- `bool`: Boolean
- `path`: File path
- `list`: Comma-separated list
- `json`: JSON object

### Conditional Injection

Use `when` expressions to conditionally inject values:

```yaml
configuration_injectors:
  - name: debug_mode
    kind: env_var
    aliases: [DEBUG]
    when: "${ENV:ENVIRONMENT} == 'development'"
    sources: ["true"]

  - name: production_config
    kind: env_var
    aliases: [CONFIG]
    when: "${ENV:ENVIRONMENT} == 'production'"
    sources: ["${PROVIDER:bws:prod-config}"]
```

### Profiles

Use profiles for environment-specific configurations:

```yaml
profiles:
  development:
    env_passthrough: true
    mask_defaults: false
    configuration_injectors:
      - name: debug
        kind: env_var
        aliases: [DEBUG]
        sources: ["true"]

  production:
    env_passthrough: false
    mask_defaults: true
    configuration_injectors:
      - name: debug
        kind: env_var
        aliases: [DEBUG]
        sources: ["false"]
```

### Output Stream Management

Configure stdout and stderr handling:

```yaml
target:
  stdout:
    path: "~/logs/${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}_${PID}.log"
    tee_terminal: true
    append: false
    format: text
  stderr:
    path: "~/logs/${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}_${PID}_err.log"
    tee_terminal: true
    append: false
    format: json
```

**Stream Options:**
- `path`: File path for output (supports tokens)
- `tee_terminal`: Whether to also output to terminal
- `append`: Whether to append to existing file
- `format`: Output format (`text` or `json`)

### Masking Sensitive Data

Protect sensitive information in logs:

```yaml
# Global masking
mask_defaults: true

configuration_providers:
  - type: bws
    id: bws
    mask: true

configuration_injectors:
  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sensitive: true
    sources: ["${PROVIDER:bws:api-key}"]
```

## Examples

### Basic Web Application

```yaml
version: "0.1"
env_passthrough: true

configuration_providers:
  - type: env
    id: env
    passthrough: true

  - type: dotenv
    id: dotenv
    filename: .env

configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources: ["${ENV:PORT|8080}"]

  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:dotenv:DATABASE_URL}
    required: true
    sensitive: true

  - name: config_file
    kind: named
    aliases: [--config]
    connector: "="
    sources: ["${ENV:CONFIG_FILE|config.yaml}"]

target:
  working_dir: "/app"
  command: ["python", "app.py"]
```

### Database Application with Secrets

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: bws
    id: bws
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: db_host
    kind: env_var
    aliases: [DB_HOST]
    sources: ["${PROVIDER:bws:db-host-secret}"]

  - name: db_password
    kind: env_var
    aliases: [DB_PASSWORD]
    sources: ["${PROVIDER:bws:db-password-secret}"]
    sensitive: true

  - name: ssl_cert
    kind: file
    aliases: [--ssl-cert]
    sources: ["${PROVIDER:bws:ssl-cert-secret}"]

target:
  working_dir: "/app"
  command: ["python", "database_tool.py"]
```

### Microservice with Conditional Configuration

```yaml
version: "0.1"

configuration_providers:
  - type: env
    id: env
    passthrough: true

configuration_injectors:
  - name: service_name
    kind: env_var
    aliases: [SERVICE_NAME]
    sources: ["${ENV:SERVICE_NAME}"]

  - name: debug_mode
    kind: env_var
    aliases: [DEBUG]
    type: bool
    when: "${ENV:ENVIRONMENT} == 'development'"
    sources: ["true"]

  - name: log_level
    kind: env_var
    aliases: [LOG_LEVEL]
    when: "${ENV:ENVIRONMENT} == 'production'"
    sources: ["INFO"]

  - name: metrics_port
    kind: named
    aliases: [--metrics-port]
    when: "${ENV:ENABLE_METRICS} == 'true'"
    sources: ["${ENV:METRICS_PORT|9090}"]

target:
  working_dir: "/app"
  command: ["python", "service.py"]
```

## Best Practices

### Security

1. **Use masking for sensitive data**:
   ```yaml
   mask_defaults: true
   configuration_injectors:
     - name: api_key
       sensitive: true
   ```

2. **Validate required values**:
   ```yaml
   configuration_injectors:
     - name: database_url
       required: true
   ```

3. **Use environment-specific profiles**:
   ```yaml
   profiles:
     production:
       mask_defaults: true
   ```

### Configuration Management

1. **Use hierarchical dotenv for local development**:
   ```yaml
   configuration_providers:
     - type: dotenv
       hierarchical: true
       precedence: deep-first
   ```

2. **Provide sensible defaults**:
   ```yaml
   sources:
     - ${ENV:PORT|8080}
     - ${ENV:DEBUG|false}
   ```

3. **Use conditional injection for environment-specific behavior**:
   ```yaml
   when: "${ENV:ENVIRONMENT} == 'development'"
   ```

### Error Handling

1. **Use dry-run for validation**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

2. **Enable strict validation**:
   ```bash
   python -m config_injector.cli validate spec.yaml --strict
   ```

3. **Check for required values**:
   ```yaml
   configuration_injectors:
     - name: critical_config
       required: true
   ```

### Performance

1. **Use appropriate provider filtering**:
   ```yaml
   filter_chain:
     - include: '^APP_'
     - exclude: '^APP_DEBUG'
   ```

2. **Minimize provider calls**:
   - Cache provider values when possible
   - Use efficient provider implementations

3. **Optimize token expansion**:
   - Use fallback values to avoid unnecessary lookups
   - Cache frequently used tokens

## Troubleshooting

### Common Issues

1. **Token expansion failures**:
   - Check token syntax
   - Verify provider IDs and keys
   - Use fallback values

2. **Missing required values**:
   - Check source configuration
   - Verify environment variables
   - Review provider setup

3. **Permission errors**:
   - Check file permissions
   - Verify working directory access
   - Review Bitwarden credentials

### Debugging

1. **Use verbose mode**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

2. **Enable dry-run**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

3. **Validate specification**:
   ```bash
   python -m config_injector.cli validate spec.yaml --strict
   ```

4. **Explain configuration**:
   ```bash
   python -m config_injector.cli explain spec.yaml
   ```

For more detailed information about specific features, see the individual documentation files in the `docs/` directory. 