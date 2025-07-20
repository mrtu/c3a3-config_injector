# Token System

The Configuration Wrapping Framework uses a powerful token system for dynamic configuration values. This document covers all supported token types and their usage.

## Table of Contents

- [Overview](#overview)
- [Token Syntax](#token-syntax)
- [Environment Tokens](#environment-tokens)
- [Provider Tokens](#provider-tokens)
- [System Tokens](#system-tokens)
- [Date and Time Tokens](#date-and-time-tokens)
- [Dynamic Tokens](#dynamic-tokens)
- [Fallback Values](#fallback-values)
- [Token Expansion Contexts](#token-expansion-contexts)
- [Best Practices](#best-practices)

## Overview

Tokens use the `${...}` syntax to dynamically resolve values at runtime. They can reference environment variables, provider values, system information, and more.

### Key Features

- **Dynamic Resolution**: Values are resolved at runtime
- **Fallback Support**: Provide default values when tokens fail
- **Nested Expansion**: Tokens can reference other tokens
- **Context-Aware**: Different contexts provide different token types

## Token Syntax

### Basic Syntax

```yaml
# Basic token
${TOKEN_TYPE:value}

# Token with fallback
${TOKEN_TYPE:value|fallback}

# Complex token
${TOKEN_TYPE:value:subvalue|fallback}
```

### Token Components

1. **Token Type**: Identifies the token category (`ENV`, `PROVIDER`, `DATE`, etc.)
2. **Value**: Token-specific value or identifier
3. **Fallback**: Optional default value if token resolution fails

### Examples

```yaml
sources:
  - ${ENV:APP_ENV}                    # Environment variable
  - ${PROVIDER:bws:secret-id}         # Provider value
  - ${DATE:YYYY-MM-DD}                # Date token
  - ${ENV:PORT|8080}                  # With fallback
  - ${PROVIDER:dotenv:DB_HOST|localhost}  # Provider with fallback
```

## Environment Tokens

Access environment variables from the host system.

### Syntax

```yaml
${ENV:VARIABLE_NAME}
${ENV:VARIABLE_NAME|fallback}
```

### Examples

#### Basic Environment Variables

```yaml
configuration_injectors:
  - name: app_environment
    kind: env_var
    aliases: [APP_ENV]
    sources:
      - ${ENV:APP_ENV}
      - development

  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    sources:
      - ${ENV:DATABASE_URL}
```

#### Environment Variables with Fallbacks

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    sources:
      - ${ENV:PORT|8080}

  - name: debug
    kind: env_var
    aliases: [DEBUG]
    sources:
      - ${ENV:DEBUG|false}

  - name: log_level
    kind: env_var
    aliases: [LOG_LEVEL]
    sources:
      - ${ENV:LOG_LEVEL|info}
```

#### Multiple Environment Variables

```yaml
configuration_injectors:
  - name: database_config
    kind: env_var
    aliases: [DB_CONFIG]
    sources:
      - ${ENV:DATABASE_URL}
      - ${ENV:DB_CONNECTION_STRING}
      - ${ENV:DB_URI}
      - "postgresql://localhost/mydb"
```

### Environment Token Behavior

- **Case Sensitivity**: Environment variable names are case-sensitive
- **Empty Values**: Empty environment variables are treated as unresolved
- **Missing Variables**: Missing variables trigger fallback or error
- **Special Characters**: Variable names can contain letters, numbers, and underscores

## Provider Tokens

Access values from configuration providers.

### Syntax

```yaml
${PROVIDER:provider_id:key_name}
${PROVIDER:provider_id:key_name|fallback}
```

### Provider ID Reference

The `provider_id` must match the `id` field of a configured provider:

```yaml
configuration_providers:
  - type: env
    id: env                    # Referenced as ${PROVIDER:env:KEY}
    name: Host Environment

  - type: dotenv
    id: dotenv_hier           # Referenced as ${PROVIDER:dotenv_hier:KEY}
    name: Hierarchical .env

  - type: bws
    id: bws                   # Referenced as ${PROVIDER:bws:secret-id}
    name: Bitwarden Secrets
```

### Examples

#### Environment Provider

```yaml
configuration_injectors:
  - name: app_env
    kind: env_var
    aliases: [APP_ENV]
    sources:
      - ${PROVIDER:env:APP_ENV}
      - development
```

#### Dotenv Provider

```yaml
configuration_injectors:
  - name: database_host
    kind: env_var
    aliases: [DB_HOST]
    sources:
      - ${PROVIDER:dotenv_hier:DB_HOST}
      - localhost

  - name: database_port
    kind: env_var
    aliases: [DB_PORT]
    sources:
      - ${PROVIDER:dotenv_hier:DB_PORT|5432}
```

#### Bitwarden Secrets Provider

```yaml
configuration_injectors:
  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:f68a9321-8a60-4ec3-ae59-b31c0155e387}
    sensitive: true

  - name: database_password
    kind: env_var
    aliases: [DB_PASSWORD]
    sources:
      - ${PROVIDER:bws:db-password-secret-id}
      - ${PROVIDER:bws:db-password-alt-id}
    sensitive: true
```

#### Provider with Fallback

```yaml
configuration_injectors:
  - name: config_value
    kind: env_var
    aliases: [CONFIG_VALUE]
    sources:
      - ${PROVIDER:dotenv:CONFIG_VALUE|default_value}
      - ${PROVIDER:env:CONFIG_VALUE|default_value}
```

### Provider Token Behavior

- **Provider Resolution**: Values are resolved from the specified provider
- **Key Lookup**: Keys are looked up in the provider's value map
- **Missing Keys**: Missing keys trigger fallback or error
- **Provider Order**: Provider tokens are resolved in the order they appear in sources

## System Tokens

Access system information and dynamic values.

### Available System Tokens

| Token | Description | Example |
|-------|-------------|---------|
| `${HOME}` | User home directory | `/home/user` |
| `${PID}` | Current process ID | `12345` |
| `${UUID}` | Random UUID | `f68a9321-8a60-4ec3-ae59-b31c0155e387` |
| `${SEQ}` | Sequence number | `0001` |

### Examples

#### Home Directory

```yaml
configuration_injectors:
  - name: config_dir
    kind: env_var
    aliases: [CONFIG_DIR]
    sources:
      - ${HOME}/.config/myapp

  - name: log_file
    kind: named
    aliases: [--log-file]
    sources:
      - ${HOME}/logs/app.log
```

#### Process ID

```yaml
configuration_injectors:
  - name: pid_file
    kind: named
    aliases: [--pid-file]
    sources:
      - /tmp/app_${PID}.pid

  - name: temp_dir
    kind: env_var
    aliases: [TEMP_DIR]
    sources:
      - /tmp/app_${PID}
```

#### UUID Generation

```yaml
configuration_injectors:
  - name: session_id
    kind: env_var
    aliases: [SESSION_ID]
    sources:
      - ${UUID}

  - name: request_id
    kind: env_var
    aliases: [REQUEST_ID]
    sources:
      - req_${UUID}
```

#### Sequence Numbers

```yaml
configuration_injectors:
  - name: instance_id
    kind: env_var
    aliases: [INSTANCE_ID]
    sources:
      - instance_${SEQ}

  - name: backup_name
    kind: named
    aliases: [--backup-name]
    sources:
      - backup_${DATE:YYYY-MM-DD}_${SEQ}
```

### System Token Behavior

- **Dynamic Values**: Values are generated at runtime
- **Unique Values**: Each token expansion generates a unique value
- **No Fallbacks**: System tokens don't support fallback values
- **Context Independent**: System tokens work in any context

## Date and Time Tokens

Generate formatted date and time values.

### Syntax

```yaml
${DATE:format_string}
${TIME:format_string}
```

### Format Strings

Date and time tokens use Python's `strftime` format strings:

| Format | Description | Example |
|--------|-------------|---------|
| `YYYY` | 4-digit year | `2024` |
| `MM` | 2-digit month | `01` |
| `DD` | 2-digit day | `15` |
| `HH` | 2-digit hour (24-hour) | `14` |
| `mm` | 2-digit minute | `30` |
| `ss` | 2-digit second | `45` |
| `SSS` | 3-digit millisecond | `123` |

### Date Token Examples

#### Basic Date Formats

```yaml
configuration_injectors:
  - name: date_today
    kind: env_var
    aliases: [DATE_TODAY]
    sources:
      - ${DATE:YYYY-MM-DD}        # 2024-01-15

  - name: date_short
    kind: env_var
    aliases: [DATE_SHORT]
    sources:
      - ${DATE:MM/DD/YYYY}        # 01/15/2024

  - name: date_long
    kind: env_var
    aliases: [DATE_LONG]
    sources:
      - ${DATE:YYYY-MM-DD HH:mm:ss}  # 2024-01-15 14:30:45
```

#### Date in File Paths

```yaml
configuration_injectors:
  - name: log_file
    kind: named
    aliases: [--log-file]
    sources:
      - ~/logs/app_${DATE:YYYY-MM-DD}.log

  - name: backup_dir
    kind: env_var
    aliases: [BACKUP_DIR]
    sources:
      - /backups/${DATE:YYYY}/${DATE:MM}
```

### Time Token Examples

#### Basic Time Formats

```yaml
configuration_injectors:
  - name: time_now
    kind: env_var
    aliases: [TIME_NOW]
    sources:
      - ${TIME:HH:mm:ss}          # 14:30:45

  - name: time_stamp
    kind: env_var
    aliases: [TIME_STAMP]
    sources:
      - ${TIME:HHmmssSSS}         # 143045123

  - name: time_iso
    kind: env_var
    aliases: [TIME_ISO]
    sources:
      - ${TIME:HH:mm:ss.SSS}      # 14:30:45.123
```

#### Time in File Names

```yaml
configuration_injectors:
  - name: output_file
    kind: named
    aliases: [--output]
    sources:
      - output_${DATE:YYYY-MM-DD}_${TIME:HHmmss}.json

  - name: temp_file
    kind: env_var
    aliases: [TEMP_FILE]
    sources:
      - /tmp/data_${TIME:HHmmssSSS}.tmp
```

### Combined Date and Time

```yaml
configuration_injectors:
  - name: timestamp
    kind: env_var
    aliases: [TIMESTAMP]
    sources:
      - ${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}

  - name: log_file
    kind: named
    aliases: [--log-file]
    sources:
      - ~/logs/app_${DATE:YYYY-MM-DD}_${TIME:HHmmss}.log
```

### Date/Time Token Behavior

- **Runtime Generation**: Values are generated at runtime
- **Format Validation**: Invalid format strings cause errors
- **Timezone**: Uses system timezone
- **No Fallbacks**: Date/time tokens don't support fallback values

## Dynamic Tokens

Generate dynamic values that change with each execution.

### UUID Token

Generate random UUIDs:

```yaml
configuration_injectors:
  - name: session_id
    kind: env_var
    aliases: [SESSION_ID]
    sources:
      - ${UUID}

  - name: request_id
    kind: env_var
    aliases: [REQUEST_ID]
    sources:
      - req_${UUID}

  - name: temp_file
    kind: named
    aliases: [--temp-file]
    sources:
      - /tmp/data_${UUID}.json
```

### Sequence Token

Generate sequential numbers:

```yaml
configuration_injectors:
  - name: instance_id
    kind: env_var
    aliases: [INSTANCE_ID]
    sources:
      - instance_${SEQ}

  - name: backup_name
    kind: named
    aliases: [--backup-name]
    sources:
      - backup_${SEQ:04d}

  - name: log_file
    kind: env_var
    aliases: [LOG_FILE]
    sources:
      - ~/logs/app_${SEQ:06d}.log
```

### Dynamic Token Behavior

- **Unique Values**: Each expansion generates a unique value
- **No Persistence**: Values don't persist between executions
- **No Fallbacks**: Dynamic tokens don't support fallback values
- **Format Support**: Some tokens support format specifiers

## Fallback Values

Provide default values when token resolution fails.

### Fallback Syntax

```yaml
${TOKEN_TYPE:value|fallback}
```

### Fallback Examples

#### Environment Variables with Fallbacks

```yaml
configuration_injectors:
  - name: port
    kind: env_var
    aliases: [PORT]
    sources:
      - ${ENV:PORT|8080}

  - name: debug
    kind: env_var
    aliases: [DEBUG]
    sources:
      - ${ENV:DEBUG|false}

  - name: log_level
    kind: env_var
    aliases: [LOG_LEVEL]
    sources:
      - ${ENV:LOG_LEVEL|info}
```

#### Provider Values with Fallbacks

```yaml
configuration_injectors:
  - name: database_host
    kind: env_var
    aliases: [DB_HOST]
    sources:
      - ${PROVIDER:dotenv:DB_HOST|localhost}

  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:api-key-secret|default-key}
```

#### Complex Fallbacks

```yaml
configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config]
    sources:
      - ${ENV:CONFIG_FILE|${HOME}/.config/app.yaml}

  - name: log_file
    kind: env_var
    aliases: [LOG_FILE]
    sources:
      - ${ENV:LOG_FILE|~/logs/app_${DATE:YYYY-MM-DD}.log}
```

### Fallback Behavior

- **Empty Values**: Empty strings trigger fallback
- **Missing Values**: Missing values trigger fallback
- **Nested Tokens**: Fallbacks can contain other tokens
- **Multiple Fallbacks**: Only one fallback per token

## Token Expansion Contexts

Tokens are expanded in different contexts with different available values.

### Provider Context

When expanding tokens in provider configurations:

```yaml
configuration_providers:
  - type: bws
    id: bws
    vault_url: ${ENV:BWS_VAULT_URL}        # Environment token
    access_token: ${ENV:BWS_ACCESS_TOKEN}  # Environment token
```

### Injector Context

When expanding tokens in injector sources:

```yaml
configuration_injectors:
  - name: config_value
    kind: env_var
    aliases: [CONFIG_VALUE]
    sources:
      - ${ENV:CONFIG_VALUE}                    # Environment token
      - ${PROVIDER:dotenv:CONFIG_VALUE}        # Provider token
      - ${DATE:YYYY-MM-DD}                     # Date token
      - ${HOME}/config_${PID}.yaml             # System tokens
```

### Target Context

When expanding tokens in target configuration:

```yaml
target:
  working_dir: "/tmp"
  stdout:
    path: "~/logs/${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}_${PID}.log"
  stderr:
    path: "~/logs/${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}_${PID}_err.log"
```

### Context-Specific Tokens

| Context | Available Tokens |
|---------|------------------|
| Provider | `ENV`, `HOME`, `PID` |
| Injector | `ENV`, `PROVIDER`, `DATE`, `TIME`, `HOME`, `PID`, `UUID`, `SEQ` |
| Target | `ENV`, `DATE`, `TIME`, `HOME`, `PID` |

## Best Practices

### Token Usage

1. **Use descriptive fallbacks**:
   ```yaml
   sources:
     - ${ENV:PORT|8080}
     - ${ENV:DEBUG|false}
   ```

2. **Order sources by preference**:
   ```yaml
   sources:
     - ${ENV:DATABASE_URL}           # Environment first
     - ${PROVIDER:dotenv:DB_URL}     # Then dotenv
     - ${PROVIDER:bws:db-secret}     # Then secrets
     - "postgresql://localhost/db"   # Finally literal
   ```

3. **Use system tokens for uniqueness**:
   ```yaml
   sources:
     - ~/logs/app_${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}_${PID}.log
   ```

### Security

1. **Avoid sensitive data in fallbacks**:
   ```yaml
   # Good
   sources:
     - ${PROVIDER:bws:api-key|}
   
   # Bad
   sources:
     - ${PROVIDER:bws:api-key|secret-key}
   ```

2. **Use provider tokens for secrets**:
   ```yaml
   sources:
     - ${PROVIDER:bws:secret-id}
   ```

3. **Validate token expansion**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

### Performance

1. **Minimize token lookups**:
   ```yaml
   # Good - single lookup
   sources:
     - ${ENV:CONFIG_VALUE|default}
   
   # Bad - multiple lookups
   sources:
     - ${ENV:CONFIG_VALUE}
     - default
   ```

2. **Use efficient token types**:
   ```yaml
   # Environment tokens are fastest
   - ${ENV:VAR}
   
   # Provider tokens are slower
   - ${PROVIDER:bws:secret-id}
   ```

3. **Cache frequently used tokens**:
   ```yaml
   # Reuse expanded values
   sources:
     - ${ENV:BASE_URL}/api/v1
     - ${ENV:BASE_URL}/health
   ```

### Error Handling

1. **Provide sensible fallbacks**:
   ```yaml
   sources:
     - ${ENV:PORT|8080}
     - ${ENV:DEBUG|false}
     - ${ENV:LOG_LEVEL|info}
   ```

2. **Use required validation**:
   ```yaml
   - name: critical_config
     required: true
     sources:
       - ${ENV:CRITICAL_CONFIG}
   ```

3. **Test token expansion**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   ```

## Troubleshooting

### Common Issues

1. **Token not found**:
   - Check token syntax
   - Verify token type is supported
   - Check context availability

2. **Provider not found**:
   - Verify provider ID spelling
   - Check provider is enabled
   - Validate provider configuration

3. **Token expansion errors**:
   - Check format strings
   - Verify fallback syntax
   - Test token expansion

### Debugging

1. **Use dry-run to see token values**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

2. **Enable verbose mode**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

3. **Validate token syntax**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   ``` 