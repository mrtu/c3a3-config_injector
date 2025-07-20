# Configuration Injectors

Configuration injectors define how values are injected into the target process. This document covers all supported injector types and their configuration options.

## Table of Contents

- [Overview](#overview)
- [Environment Variable Injector](#environment-variable-injector)
- [Named Argument Injector](#named-argument-injector)
- [Positional Argument Injector](#positional-argument-injector)
- [File Injector](#file-injector)
- [Stdin Fragment Injector](#stdin-fragment-injector)
- [Type Coercion](#type-coercion)
- [Conditional Injection](#conditional-injection)
- [Precedence and Resolution](#precedence-and-resolution)
- [Sensitive Data Handling](#sensitive-data-handling)

## Overview

Configuration injectors define how resolved values are injected into the target process. Each injector has:

- **Name**: Unique identifier for the injector
- **Kind**: Injection method (`env_var`, `named`, `positional`, `file`, `stdin_fragment`)
- **Sources**: List of value sources (tokens, literals)
- **Precedence**: Resolution strategy for multiple sources
- **Type**: Optional type coercion
- **Conditional**: Optional `when` expression

## Environment Variable Injector

Sets environment variables for the target process.

### Basic Configuration

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

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Unique injector identifier |
| `kind` | string | required | Must be `env_var` |
| `aliases` | array | `[]` | List of environment variable names |
| `sources` | array | `[]` | List of value sources |
| `precedence` | string | `first_non_empty` | Resolution strategy |
| `required` | boolean | false | Whether the injector is required |
| `default` | any | null | Default value if no source resolves |
| `type` | string | `string` | Type coercion |
| `sensitive` | boolean | false | Whether to mask the value |
| `when` | string | null | Conditional expression |

### Examples

#### Basic Environment Variable

```yaml
configuration_injectors:
  - name: app_environment
    kind: env_var
    aliases: [APP_ENV]
    sources:
      - ${ENV:APP_ENV}
      - development
```

#### Multiple Aliases

```yaml
configuration_injectors:
  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL, DB_URL, DATABASE_CONNECTION_STRING]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:dotenv:DB_URL}
```

#### Required with Fallback

```yaml
configuration_injectors:
  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${ENV:API_KEY}
      - ${PROVIDER:bws:api-key-secret}
    required: true
    sensitive: true
```

#### Type Coercion

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources:
      - ${ENV:PORT|8080}
```

## Named Argument Injector

Adds named CLI arguments to the target command.

### Basic Configuration

```yaml
configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config, -c]
    connector: "="
    sources:
      - ${ENV:CONFIG_FILE}
      - config.yaml
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Unique injector identifier |
| `kind` | string | required | Must be `named` |
| `aliases` | array | `[]` | List of argument names |
| `connector` | string | `=` | How to connect value to argument |
| `sources` | array | `[]` | List of value sources |
| `precedence` | string | `first_non_empty` | Resolution strategy |
| `required` | boolean | false | Whether the injector is required |
| `default` | any | null | Default value if no source resolves |
| `type` | string | `string` | Type coercion |
| `sensitive` | boolean | false | Whether to mask the value |
| `when` | string | null | Conditional expression |

### Connector Types

| Connector | Example | Description |
|-----------|---------|-------------|
| `=` | `--param=value` | Value connected with equals sign |
| `space` | `--param value` | Value as separate argument |
| `repeat` | `--param value` | Same as space (for compatibility) |

### Examples

#### Basic Named Argument

```yaml
configuration_injectors:
  - name: verbose
    kind: named
    aliases: [--verbose, -v]
    connector: "space"
    sources: ["true"]
```

#### Multiple Aliases

```yaml
configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config, --config-file, -c]
    connector: "="
    sources:
      - ${ENV:CONFIG_FILE}
      - config.yaml
```

#### Conditional Named Argument

```yaml
configuration_injectors:
  - name: debug
    kind: named
    aliases: [--debug]
    connector: "space"
    when: "${ENV:ENVIRONMENT} == 'development'"
    sources: ["true"]
```

#### Type Coercion

```yaml
configuration_injectors:
  - name: workers
    kind: named
    aliases: [--workers, -w]
    connector: "="
    type: int
    sources:
      - ${ENV:WORKERS|4}
```

## Positional Argument Injector

Adds positional CLI arguments to the target command.

### Basic Configuration

```yaml
configuration_injectors:
  - name: input_file
    kind: positional
    order: 1
    sources:
      - ${ENV:INPUT_FILE}
      - input.txt
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Unique injector identifier |
| `kind` | string | required | Must be `positional` |
| `order` | integer | null | Position in argument list |
| `sources` | array | `[]` | List of value sources |
| `precedence` | string | `first_non_empty` | Resolution strategy |
| `required` | boolean | false | Whether the injector is required |
| `default` | any | null | Default value if no source resolves |
| `type` | string | `string` | Type coercion |
| `sensitive` | boolean | false | Whether to mask the value |
| `when` | string | null | Conditional expression |

### Ordering

Positional arguments are ordered by their `order` field (lower numbers come first). If no order is specified, they are added in the order they appear in the configuration.

### Examples

#### Basic Positional Argument

```yaml
configuration_injectors:
  - name: input_file
    kind: positional
    sources:
      - ${ENV:INPUT_FILE}
      - input.txt
```

#### Ordered Positional Arguments

```yaml
configuration_injectors:
  - name: command
    kind: positional
    order: 1
    sources: ["process"]

  - name: subcommand
    kind: positional
    order: 2
    sources: ["start"]

  - name: target
    kind: positional
    order: 3
    sources:
      - ${ENV:TARGET}
      - default-target
```

#### Required Positional Argument

```yaml
configuration_injectors:
  - name: config_file
    kind: positional
    order: 1
    required: true
    sources:
      - ${ENV:CONFIG_FILE}
```

## File Injector

Creates temporary files with content and injects the file path.

### Basic Configuration

```yaml
configuration_injectors:
  - name: config_json
    kind: file
    aliases: [--config-file]
    sources:
      - ${PROVIDER:bws:config-secret}
    type: json
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Unique injector identifier |
| `kind` | string | required | Must be `file` |
| `aliases` | array | `[]` | Argument names for file path |
| `connector` | string | `=` | How to connect file path |
| `sources` | array | `[]` | File content (supports tokens) |
| `precedence` | string | `first_non_empty` | Resolution strategy |
| `required` | boolean | false | Whether the injector is required |
| `default` | any | null | Default content if no source resolves |
| `type` | string | `string` | Type coercion for content |
| `sensitive` | boolean | false | Whether to mask the content |
| `when` | string | null | Conditional expression |

### Behavior

1. **File Creation**: Creates a temporary file with resolved content
2. **Path Injection**: Injects the file path as a named argument or environment variable
3. **Cleanup**: Automatically cleans up the file after execution
4. **Token Support**: File content supports token expansion

### Examples

#### Basic File Injection

```yaml
configuration_injectors:
  - name: config_file
    kind: file
    aliases: [--config]
    connector: "="
    sources:
      - |
        database:
          host: ${PROVIDER:dotenv:DB_HOST}
          port: ${PROVIDER:dotenv:DB_PORT}
        logging:
          level: ${ENV:LOG_LEVEL|info}
```

#### JSON Configuration File

```yaml
configuration_injectors:
  - name: config_json
    kind: file
    aliases: [--config-file]
    type: json
    sources:
      - |
        {
          "database": {
            "host": "${PROVIDER:dotenv:DB_HOST}",
            "port": "${PROVIDER:dotenv:DB_PORT}"
          },
          "logging": {
            "level": "${ENV:LOG_LEVEL|info}"
          }
        }
```

#### SSL Certificate File

```yaml
configuration_injectors:
  - name: ssl_cert
    kind: file
    aliases: [--ssl-cert]
    sources:
      - ${PROVIDER:bws:ssl-cert-secret}
    sensitive: true
```

#### Environment Variable Path

```yaml
configuration_injectors:
  - name: temp_config
    kind: file
    sources:
      - |
        # Temporary configuration
        setting1: value1
        setting2: ${ENV:SETTING2}
```

## Stdin Fragment Injector

Appends content to the target process's stdin.

### Basic Configuration

```yaml
configuration_injectors:
  - name: stdin_data
    kind: stdin_fragment
    sources:
      - "additional input data"
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Unique injector identifier |
| `kind` | string | required | Must be `stdin_fragment` |
| `sources` | array | `[]` | Content to append to stdin |
| `precedence` | string | `first_non_empty` | Resolution strategy |
| `required` | boolean | false | Whether the injector is required |
| `default` | any | null | Default content if no source resolves |
| `type` | string | `string` | Type coercion |
| `sensitive` | boolean | false | Whether to mask the content |
| `when` | string | null | Conditional expression |

### Behavior

1. **Aggregation**: Content from multiple `stdin_fragment` injectors is aggregated
2. **Appending**: Combined content is sent to the target process's stdin
3. **Token Support**: Content supports token expansion
4. **Ordering**: Fragments are appended in the order they appear in configuration

### Examples

#### Basic Stdin Fragment

```yaml
configuration_injectors:
  - name: stdin_data
    kind: stdin_fragment
    sources:
      - "additional input data"
```

#### Multiple Fragments

```yaml
configuration_injectors:
  - name: header
    kind: stdin_fragment
    sources:
      - "=== Configuration Data ==="

  - name: config_data
    kind: stdin_fragment
    sources:
      - |
        setting1: ${ENV:SETTING1}
        setting2: ${PROVIDER:dotenv:SETTING2}

  - name: footer
    kind: stdin_fragment
    sources:
      - "=== End Configuration ==="
```

#### Sensitive Stdin Data

```yaml
configuration_injectors:
  - name: api_key
    kind: stdin_fragment
    sources:
      - ${PROVIDER:bws:api-key-secret}
    sensitive: true
```

## Type Coercion

Injectors support automatic type conversion for their values.

### Supported Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | String (default) | `"hello"` |
| `int` | Integer | `123` |
| `bool` | Boolean | `true`, `false`, `1`, `0` |
| `path` | File path | `/path/to/file` |
| `list` | Comma-separated list | `"a,b,c"` → `["a", "b", "c"]` |
| `json` | JSON object | `'{"key": "value"}'` |

### Type Coercion Examples

#### Integer Coercion

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources:
      - ${ENV:PORT|8080}
```

#### Boolean Coercion

```yaml
configuration_injectors:
  - name: debug
    kind: env_var
    aliases: [DEBUG]
    type: bool
    sources:
      - ${ENV:DEBUG|false}
```

#### List Coercion

```yaml
configuration_injectors:
  - name: items
    kind: env_var
    aliases: [ITEMS]
    type: list
    delimiter: ","
    sources:
      - "item1,item2,item3"
```

#### JSON Coercion

```yaml
configuration_injectors:
  - name: config
    kind: file
    type: json
    sources:
      - |
        {
          "database": {
            "host": "${PROVIDER:dotenv:DB_HOST}",
            "port": "${PROVIDER:dotenv:DB_PORT}"
          }
        }
```

## Conditional Injection

Use `when` expressions to conditionally inject values.

### Expression Syntax

- **Simple comparisons**: `==`, `!=`, `>`, `<`, `>=`, `<=`
- **Logical operators**: `and`, `or`, `not`
- **String literals**: Must be quoted (`'value'`)
- **Environment variables**: `${ENV:VAR}`
- **Provider values**: `${PROVIDER:id:key}`

### Conditional Examples

#### Environment-Based Injection

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

#### Complex Conditions

```yaml
configuration_injectors:
  - name: verbose_logging
    kind: named
    aliases: [--verbose]
    when: "${ENV:DEBUG} == 'true' and ${ENV:ENVIRONMENT} == 'development'"
    sources: ["true"]

  - name: quiet_mode
    kind: named
    aliases: [--quiet]
    when: "${ENV:ENVIRONMENT} == 'production' or ${ENV:QUIET} == 'true'"
    sources: ["true"]
```

#### Feature Flags

```yaml
configuration_injectors:
  - name: metrics_port
    kind: named
    aliases: [--metrics-port]
    when: "${ENV:ENABLE_METRICS} == 'true'"
    sources: ["${ENV:METRICS_PORT|9090}"]

  - name: health_check
    kind: named
    aliases: [--health-check]
    when: "${ENV:ENABLE_HEALTH_CHECK} == 'true'"
    sources: ["true"]
```

## Precedence and Resolution

Injectors use precedence strategies to resolve values from multiple sources.

### Precedence Strategies

| Strategy | Description |
|----------|-------------|
| `first_non_empty` | Use the first non-empty value found |
| `last_non_empty` | Use the last non-empty value found |
| `first` | Use the first value regardless of emptiness |
| `last` | Use the last value regardless of emptiness |

### Resolution Examples

#### First Non-Empty (Default)

```yaml
configuration_injectors:
  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    precedence: first_non_empty
    sources:
      - ${ENV:DATABASE_URL}           # Try environment first
      - ${PROVIDER:dotenv:DB_URL}     # Then dotenv
      - ${PROVIDER:bws:db-secret-id}  # Then Bitwarden
      - "postgresql://localhost/db"   # Finally fallback
```

#### Last Non-Empty

```yaml
configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config]
    precedence: last_non_empty
    sources:
      - "default.yaml"                # Start with default
      - ${ENV:CONFIG_FILE}            # Override with environment
      - ${PROVIDER:dotenv:CONFIG}     # Override with dotenv
```

#### With Default Values

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    precedence: first_non_empty
    sources:
      - ${ENV:PORT}
      - ${PROVIDER:dotenv:PORT}
    default: 8080
```

## Sensitive Data Handling

Protect sensitive information by marking injectors as sensitive.

### Sensitive Injectors

```yaml
configuration_injectors:
  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:api-key-secret}
    sensitive: true

  - name: password
    kind: named
    aliases: [--password]
    sources:
      - ${PROVIDER:bws:password-secret}
    sensitive: true
```

### Masking Behavior

- **Sensitive injectors**: Always masked regardless of provider settings
- **Provider masking**: Controlled by provider `mask` setting
- **Global masking**: Controlled by `mask_defaults` setting
- **Masked output**: Appears as `<masked>` in logs and dry-run output

### Security Best Practices

1. **Mark secrets as sensitive**:
   ```yaml
   - name: secret_key
     sensitive: true
   ```

2. **Use Bitwarden for secrets**:
   ```yaml
   sources:
     - ${PROVIDER:bws:secret-id}
   ```

3. **Enable global masking in production**:
   ```yaml
   mask_defaults: true
   ```

## Best Practices

### Security

1. **Mark sensitive injectors**:
   ```yaml
   - name: api_key
     sensitive: true
   ```

2. **Use appropriate sources**:
   ```yaml
   sources:
     - ${PROVIDER:bws:secret-id}  # For secrets
     - ${ENV:CONFIG}              # For configuration
   ```

3. **Validate required values**:
   ```yaml
   - name: critical_config
     required: true
   ```

### Configuration Management

1. **Provide sensible defaults**:
   ```yaml
   sources:
     - ${ENV:PORT|8080}
     - ${ENV:DEBUG|false}
   ```

2. **Use conditional injection**:
   ```yaml
   when: "${ENV:ENVIRONMENT} == 'development'"
   ```

3. **Order positional arguments**:
   ```yaml
   - name: command
     order: 1
   - name: subcommand
     order: 2
   ```

### Performance

1. **Use appropriate precedence**:
   ```yaml
   precedence: first_non_empty  # Stop at first valid value
   ```

2. **Minimize source lookups**:
   ```yaml
   sources:
     - ${ENV:VAR}              # Fast lookup
     - ${PROVIDER:bws:secret}  # Slower lookup
   ```

3. **Use conditional injection for optional features**:
   ```yaml
   when: "${ENV:FEATURE_FLAG} == 'true'"
   ```

## Troubleshooting

### Common Issues

1. **Injector not applied**:
   - Check conditional expressions
   - Verify source values are not empty
   - Check injector configuration

2. **Type coercion errors**:
   - Verify source values match expected type
   - Check type configuration
   - Use appropriate fallback values

3. **File injection issues**:
   - Check file content format
   - Verify token expansion
   - Check file permissions

### Debugging

1. **Use dry-run to see injector values**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

2. **Enable verbose mode**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

3. **Validate injector configuration**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   ``` 