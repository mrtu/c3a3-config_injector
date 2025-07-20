# Command Line Interface

The Configuration Wrapping Framework provides a comprehensive command-line interface for managing and executing configuration specifications.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Basic Commands](#basic-commands)
- [Run Command](#run-command)
- [Validate Command](#validate-command)
- [Explain Command](#explain-command)
- [Print Schema Command](#print-schema-command)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Overview

The CLI is built using Typer and provides a user-friendly interface for:

- Running configuration specifications
- Validating configuration files
- Explaining configuration behavior
- Generating JSON schemas
- Debugging configuration issues

### Command Structure

```bash
python -m config_injector.cli <command> [options] <spec-file>
```

## Installation

### Development Installation

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

### Global Installation

```bash
# Install globally (if available)
pip install config-injector

# Use the wrapper command
wrapper run spec.yaml
```

## Basic Commands

### Help

Get help for the CLI:

```bash
# General help
python -m config_injector.cli --help

# Command-specific help
python -m config_injector.cli run --help
python -m config_injector.cli validate --help
python -m config_injector.cli explain --help
```

### Available Commands

| Command | Description |
|---------|-------------|
| `run` | Execute a configuration specification |
| `validate` | Validate a configuration specification |
| `explain` | Explain what a configuration does |
| `print-schema` | Print the JSON schema |

## Run Command

Execute a configuration specification.

### Basic Usage

```bash
python -m config_injector.cli run spec.yaml
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | false | Show what would be executed without running |
| `--json` | flag | false | Output in JSON format (only with --dry-run) |
| `--profile` | string | null | Profile to use |
| `--verbose, -v` | flag | false | Enable verbose output |
| `--quiet, -q` | flag | false | Enable quiet mode (minimal output) |
| `--strict` | flag | false | Enable strict validation |
| `--env-passthrough/--no-env-passthrough` | flag | null | Override env_passthrough setting |
| `--mask-defaults/--no-mask-defaults` | flag | null | Override mask_defaults setting |

### Examples

#### Basic Execution

```bash
# Run a specification
python -m config_injector.cli run example.yaml

# Run with verbose output
python -m config_injector.cli run example.yaml --verbose

# Run with quiet mode
python -m config_injector.cli run example.yaml --quiet
```

#### Dry Run

```bash
# Preview execution without running
python -m config_injector.cli run example.yaml --dry-run

# Dry run with JSON output
python -m config_injector.cli run example.yaml --dry-run --json

# Dry run with verbose output
python -m config_injector.cli run example.yaml --dry-run --verbose
```

#### Profile Usage

```bash
# Run with development profile
python -m config_injector.cli run example.yaml --profile development

# Run with production profile
python -m config_injector.cli run example.yaml --profile production
```

#### Override Settings

```bash
# Override environment passthrough
python -m config_injector.cli run example.yaml --env-passthrough

# Disable environment passthrough
python -m config_injector.cli run example.yaml --no-env-passthrough

# Enable masking
python -m config_injector.cli run example.yaml --mask-defaults

# Disable masking
python -m config_injector.cli run example.yaml --no-mask-defaults
```

#### Strict Validation

```bash
# Run with strict validation
python -m config_injector.cli run example.yaml --strict

# Dry run with strict validation
python -m config_injector.cli run example.yaml --dry-run --strict
```

### Dry Run Output

When using `--dry-run`, the CLI shows:

1. **Configuration Summary**: What providers and injectors are configured
2. **Resolved Values**: The actual values that would be injected
3. **Command Preview**: The exact command that would be executed
4. **Environment Variables**: Environment variables that would be set
5. **Files Created**: Temporary files that would be created
6. **Errors**: Any configuration errors or warnings

#### Text Output Example

```
┌─ Dry Run Report ──────────────────────────────────────────────────────────┐
│                                                                           │
│ Configuration:                                                            │
│   Providers: 3 (env, dotenv_hier, bws)                                   │
│   Injectors: 5                                                            │
│   Target: echo "Hello from Configuration Wrapping Framework!"             │
│                                                                           │
│ Environment Variables:                                                    │
│   APP_ENV=development                                                     │
│   DATABASE_URL=<masked>                                                   │
│   PORT=8080                                                               │
│                                                                           │
│ Command Arguments:                                                        │
│   --config=config.yaml                                                    │
│   --verbose                                                               │
│                                                                           │
│ Working Directory: /tmp                                                   │
│                                                                           │
│ Output Streams:                                                           │
│   stdout: ~/logs/2024-01-15_143025123_12345.log                          │
│   stderr: ~/logs/2024-01-15_143025123_12345_err.log                      │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

#### JSON Output Example

```bash
python -m config_injector.cli run example.yaml --dry-run --json
```

```json
{
  "spec": {
    "version": "0.1",
    "providers": 3,
    "injectors": 5
  },
  "environment": {
    "APP_ENV": "development",
    "DATABASE_URL": "<masked>",
    "PORT": "8080"
  },
  "arguments": [
    "--config=config.yaml",
    "--verbose"
  ],
  "target": {
    "working_dir": "/tmp",
    "command": ["echo", "Hello from Configuration Wrapping Framework!"]
  },
  "streams": {
    "stdout": "~/logs/2024-01-15_143025123_12345.log",
    "stderr": "~/logs/2024-01-15_143025123_12345_err.log"
  },
  "errors": [],
  "warnings": []
}
```

## Validate Command

Validate a configuration specification.

### Basic Usage

```bash
python -m config_injector.cli validate spec.yaml
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--strict` | flag | false | Enable strict validation |
| `--verbose, -v` | flag | false | Enable verbose output |
| `--quiet, -q` | flag | false | Enable quiet mode (minimal output) |

### Examples

#### Basic Validation

```bash
# Validate a specification
python -m config_injector.cli validate example.yaml

# Validate with verbose output
python -m config_injector.cli validate example.yaml --verbose

# Validate with quiet mode
python -m config_injector.cli validate example.yaml --quiet
```

#### Strict Validation

```bash
# Validate with strict mode
python -m config_injector.cli validate example.yaml --strict

# Strict validation with verbose output
python -m config_injector.cli validate example.yaml --strict --verbose
```

### Validation Types

The validate command performs several types of validation:

1. **Schema Validation**: Ensures the YAML structure matches the expected schema
2. **Semantic Validation**: Checks for logical errors and inconsistencies
3. **Runtime Validation**: Performs a dry run to catch runtime issues
4. **Strict Validation**: Additional checks for best practices and security

### Validation Output

#### Success Example

```bash
$ python -m config_injector.cli validate example.yaml
✓ Specification is valid
```

#### Error Example

```bash
$ python -m config_injector.cli validate example.yaml
Validation failed:
  • Provider 'bws' requires access_token
  • Injector 'database_url' is required but no value found
  • Invalid token syntax: ${INVALID:TOKEN}
```

#### Verbose Output

```bash
$ python -m config_injector.cli validate example.yaml --verbose
Loaded specification from example.yaml
Version: 0.1
Providers: 3
Injectors: 5
Performing dry run validation...
Performing semantic validation...
✓ Specification is valid
```

## Explain Command

Explain what a configuration specification does.

### Basic Usage

```bash
python -m config_injector.cli explain spec.yaml
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verbose, -v` | flag | false | Enable verbose output |
| `--quiet, -q` | flag | false | Enable quiet mode (minimal output) |

### Examples

#### Basic Explanation

```bash
# Explain a specification
python -m config_injector.cli explain example.yaml

# Explain with verbose output
python -m config_injector.cli explain example.yaml --verbose

# Explain with quiet mode
python -m config_injector.cli explain example.yaml --quiet
```

### Explanation Output

The explain command provides a detailed breakdown of:

1. **Configuration Overview**: What the specification does
2. **Providers**: What data sources are configured
3. **Injectors**: How values are injected
4. **Target**: What command is executed
5. **Token Resolution**: How tokens are expanded
6. **Security**: What data is masked

#### Example Output

```
Configuration Explanation
========================

Overview:
  This specification runs a web application with database connectivity
  and logging configuration.

Providers:
  • env: Host environment variables (passthrough enabled)
  • dotenv_hier: Hierarchical .env files (deep-first precedence)
  • bws: Bitwarden Secrets (masked)

Injectors:
  • app_environment: Sets APP_ENV environment variable
    - Sources: ${ENV:APP_ENV}, development
    - Resolved: development
  
  • database_url: Sets DATABASE_URL environment variable
    - Sources: ${ENV:DATABASE_URL}, ${PROVIDER:bws:db-secret}
    - Resolved: <masked>
  
  • port: Sets PORT environment variable
    - Sources: ${ENV:PORT|8080}
    - Resolved: 8080

Target:
  • Working Directory: /tmp
  • Command: python app.py
  • Output: ~/logs/2024-01-15_143025123_12345.log

Security:
  • 2 values masked
  • 1 sensitive injector
```

## Print Schema Command

Print the JSON schema for configuration specifications.

### Basic Usage

```bash
python -m config_injector.cli print-schema
```

### Examples

#### Print Schema

```bash
# Print the complete schema
python -m config_injector.cli print-schema

# Save schema to file
python -m config_injector.cli print-schema > schema.json
```

### Schema Output

The schema defines the structure and validation rules for configuration files:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Configuration Wrapping Framework Specification",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "description": "Specification version"
    },
    "env_passthrough": {
      "type": "boolean",
      "default": false,
      "description": "Whether to pass through environment variables"
    },
    "configuration_providers": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Provider"
      }
    },
    "configuration_injectors": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Injector"
      }
    },
    "target": {
      "$ref": "#/definitions/Target"
    }
  },
  "required": ["version", "configuration_providers", "configuration_injectors", "target"]
}
```

## Error Handling

### Common Error Types

1. **File Not Found**
   ```bash
   Error: File 'nonexistent.yaml' not found
   ```

2. **Invalid YAML**
   ```bash
   Error: Invalid YAML syntax at line 5, column 10
   ```

3. **Schema Validation**
   ```bash
   Error: Invalid configuration:
     • 'version' is required
     • 'configuration_providers' must be an array
   ```

4. **Runtime Errors**
   ```bash
   Error: Provider 'bws' failed to load:
     • Invalid access token
   ```

5. **Token Expansion Errors**
   ```bash
   Error: Token expansion failed:
     • Unknown token: ${INVALID:TOKEN}
     • Provider 'nonexistent' not found
   ```

### Error Recovery

1. **Use dry-run to catch errors early**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

2. **Validate before running**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   ```

3. **Use verbose mode for details**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

4. **Check configuration step by step**:
   ```bash
   python -m config_injector.cli explain spec.yaml
   ```

## Best Practices

### Command Usage

1. **Always validate before running**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   python -m config_injector.cli run spec.yaml
   ```

2. **Use dry-run for testing**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

3. **Use profiles for different environments**:
   ```bash
   python -m config_injector.cli run spec.yaml --profile development
   python -m config_injector.cli run spec.yaml --profile production
   ```

4. **Enable strict validation in production**:
   ```bash
   python -m config_injector.cli run spec.yaml --strict
   ```

### Debugging

1. **Use verbose mode for troubleshooting**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

2. **Use explain to understand configuration**:
   ```bash
   python -m config_injector.cli explain spec.yaml
   ```

3. **Use JSON output for programmatic access**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run --json
   ```

4. **Check for specific issues**:
   ```bash
   python -m config_injector.cli validate spec.yaml --strict
   ```

### Security

1. **Use masking for sensitive data**:
   ```bash
   python -m config_injector.cli run spec.yaml --mask-defaults
   ```

2. **Validate in strict mode**:
   ```bash
   python -m config_injector.cli validate spec.yaml --strict
   ```

3. **Use dry-run to preview sensitive operations**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

### Automation

1. **Use quiet mode in scripts**:
   ```bash
   python -m config_injector.cli run spec.yaml --quiet
   ```

2. **Use JSON output for parsing**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run --json
   ```

3. **Check exit codes**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   if [ $? -eq 0 ]; then
     python -m config_injector.cli run spec.yaml
   fi
   ```

### Integration

1. **Use in CI/CD pipelines**:
   ```yaml
   - name: Validate Configuration
     run: python -m config_injector.cli validate spec.yaml --strict
   
   - name: Run Application
     run: python -m config_injector.cli run spec.yaml
   ```

2. **Use in Docker containers**:
   ```dockerfile
   COPY spec.yaml /app/
   RUN python -m config_injector.cli validate spec.yaml
   CMD ["python", "-m", "config_injector.cli", "run", "spec.yaml"]
   ```

3. **Use in Kubernetes**:
   ```yaml
   command: ["python", "-m", "config_injector.cli", "run", "spec.yaml"]
   ```

## Troubleshooting

### Common Issues

1. **Command not found**:
   ```bash
   # Ensure the package is installed
   pip install -e .
   
   # Use the correct module path
   python -m config_injector.cli --help
   ```

2. **Permission errors**:
   ```bash
   # Check file permissions
   ls -la spec.yaml
   
   # Check working directory permissions
   ls -la /tmp
   ```

3. **Import errors**:
   ```bash
   # Check Python environment
   python --version
   pip list | grep config_injector
   
   # Reinstall if needed
   pip install -e . --force-reinstall
   ```

### Debugging Commands

1. **Check CLI version**:
   ```bash
   python -m config_injector.cli --version
   ```

2. **Check available commands**:
   ```bash
   python -m config_injector.cli --help
   ```

3. **Check command options**:
   ```bash
   python -m config_injector.cli run --help
   ```

4. **Test with minimal configuration**:
   ```bash
   echo 'version: "0.1"
   configuration_providers: []
   configuration_injectors: []
   target:
     working_dir: "/tmp"
     command: ["echo", "test"]' > test.yaml
   
   python -m config_injector.cli run test.yaml
   ``` 