# Configuration Providers

Configuration providers are sources of configuration data that the framework can use to inject values into target processes. This document covers all supported provider types and their configuration options.

## Table of Contents

- [Overview](#overview)
- [Environment Provider](#environment-provider)
- [Dotenv Provider](#dotenv-provider)
- [Bitwarden Secrets Provider](#bitwarden-secrets-provider)
- [Provider Filtering](#provider-filtering)
- [Provider Masking](#provider-masking)
- [Provider Precedence](#provider-precedence)

## Overview

Configuration providers define where configuration values come from. Each provider has:

- **Type**: The provider implementation (`env`, `dotenv`, `bws`, `custom`)
- **ID**: Unique identifier for referencing in tokens
- **Name**: Human-readable description
- **Filter Chain**: Optional filtering rules
- **Masking**: Whether to mask sensitive values

## Environment Provider

The environment provider reads configuration from the host environment variables.

### Basic Configuration

```yaml
configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true
    filter_chain: []
    mask: false
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | required | Must be `env` |
| `id` | string | required | Unique provider identifier |
| `name` | string | optional | Human-readable name |
| `passthrough` | boolean | false | Whether to pass through all environment variables |
| `filter_chain` | array | `[]` | List of filtering rules |
| `mask` | boolean | false | Whether to mask values in logs |

### Examples

#### Basic Environment Provider

```yaml
configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true
```

#### Filtered Environment Provider

```yaml
configuration_providers:
  - type: env
    id: env
    name: Application Environment
    passthrough: false
    filter_chain:
      - include: '^APP_'
      - exclude: '^APP_DEBUG'
    mask: false
```

#### Masked Environment Provider

```yaml
configuration_providers:
  - type: env
    id: env
    name: Sensitive Environment
    passthrough: true
    mask: true
```

## Dotenv Provider

The dotenv provider loads configuration from `.env` files with support for hierarchical loading.

### Basic Configuration

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv
    name: Application Config
    hierarchical: false
    filename: .env
    precedence: deep-first
    filter_chain: []
    mask: false
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | required | Must be `dotenv` |
| `id` | string | required | Unique provider identifier |
| `name` | string | optional | Human-readable name |
| `hierarchical` | boolean | false | Enable hierarchical file loading |
| `filename` | string | `.env` | Name of the dotenv file |
| `path` | string | optional | Direct path to dotenv file |
| `precedence` | string | `deep-first` | Merge strategy for hierarchical files |
| `filter_chain` | array | `[]` | List of filtering rules |
| `mask` | boolean | false | Whether to mask values |

### Hierarchical Loading

When `hierarchical: true`, the provider walks up the directory tree from the working directory, finding all `.env` files and merging them according to the precedence strategy.

#### Deep-First Precedence

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv_hier
    name: Hierarchical .env
    hierarchical: true
    filename: .env
    precedence: deep-first
```

**Behavior**: Closest to working directory wins (child overrides parent)

**Example Directory Structure**:
```
/home/user/project/
├── .env                    # Base configuration
├── subdir/
│   ├── .env               # Overrides base
│   └── deepdir/
│       └── .env           # Overrides both above
```

#### Shallow-First Precedence

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv_hier
    name: Hierarchical .env
    hierarchical: true
    filename: .env
    precedence: shallow-first
```

**Behavior**: Root wins (parent overrides child)

### Examples

#### Single Dotenv File

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv
    name: Application Config
    hierarchical: false
    filename: .env
```

#### Hierarchical Dotenv with Filtering

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv_hier
    name: Hierarchical .env
    hierarchical: true
    filename: .env
    precedence: deep-first
    filter_chain:
      - include: '^APP_'
      - exclude: '^APP_DEBUG'
    mask: false
```

#### Direct Path Configuration

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv
    name: Custom Config
    hierarchical: false
    path: /etc/myapp/config.env
```

## Bitwarden Secrets Provider

The Bitwarden Secrets provider fetches secrets from Bitwarden Secrets Manager using the official SDK.

### Prerequisites

1. Install with Bitwarden support:
   ```bash
   pip install -e ".[bws]"
   ```

2. Set up Bitwarden credentials:
   ```bash
   export BWS_VAULT_URL="https://api.bitwarden.com"
   export BWS_ACCESS_TOKEN="your-access-token"
   ```

### Basic Configuration

```yaml
configuration_providers:
  - type: bws
    id: bws
    name: Bitwarden Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true
    filter_chain: []
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | required | Must be `bws` |
| `id` | string | required | Unique provider identifier |
| `name` | string | optional | Human-readable name |
| `vault_url` | string | optional | Bitwarden vault URL |
| `access_token` | string | required | Bitwarden access token |
| `filter_chain` | array | `[]` | List of filtering rules |
| `mask` | boolean | true | Whether to mask values (recommended) |

### Secret Access

Secrets are accessed by their secret ID in tokens:

```yaml
configuration_injectors:
  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:f68a9321-8a60-4ec3-ae59-b31c0155e387}
```

### Examples

#### Basic Bitwarden Provider

```yaml
configuration_providers:
  - type: bws
    id: bws
    name: Bitwarden Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true
```

#### Filtered Bitwarden Provider

```yaml
configuration_providers:
  - type: bws
    id: bws
    name: Filtered Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true
    filter_chain:
      - include: '^[0-9a-f-]{36}$'  # Only UUID patterns
```

## Provider Filtering

All providers support filtering through the `filter_chain` option. Filters are applied in order and can include or exclude keys based on regex patterns.

### Filter Rule Syntax

```yaml
filter_chain:
  - include: '^APP_'      # Include keys starting with APP_
  - exclude: '^APP_DEBUG' # Exclude APP_DEBUG specifically
  - include: '^DB_'       # Include keys starting with DB_
```

### Filter Options

| Option | Type | Description |
|--------|------|-------------|
| `include` | string | Regex pattern for keys to include |
| `exclude` | string | Regex pattern for keys to exclude |

### Filter Behavior

1. **Include Rules**: Add matching keys to the result set
2. **Exclude Rules**: Remove matching keys from the result set
3. **Order Matters**: Filters are applied in the order specified
4. **Regex Support**: Uses Python's `re` module for pattern matching

### Examples

#### Environment Variable Filtering

```yaml
configuration_providers:
  - type: env
    id: env
    name: Filtered Environment
    passthrough: false
    filter_chain:
      - include: '^APP_'
      - exclude: '^APP_DEBUG'
      - include: '^DB_'
```

#### Dotenv Filtering

```yaml
configuration_providers:
  - type: dotenv
    id: dotenv
    name: Filtered .env
    hierarchical: true
    filename: .env
    filter_chain:
      - exclude: '^OS_'
      - exclude: '^PATH'
      - include: '^APP_'
```

## Provider Masking

Providers can mask sensitive values in logs and dry-run output to protect sensitive information.

### Global Masking

Set `mask_defaults: true` in the specification to enable global masking:

```yaml
version: "0.1"
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    mask: true  # Will be masked
```

### Per-Provider Masking

Override masking per provider:

```yaml
configuration_providers:
  - type: env
    id: env
    mask: false  # Not masked

  - type: bws
    id: bws
    mask: true   # Always masked
```

### Masking Behavior

- Masked values appear as `<masked>` in logs and dry-run output
- Provider-level masking overrides global settings
- Sensitive injectors are automatically masked regardless of provider settings

## Provider Precedence

When multiple providers contain the same key, the framework uses a precedence system to determine which value to use.

### Default Precedence

1. **Environment Provider**: Highest precedence (if `passthrough: true`)
2. **Dotenv Provider**: Medium precedence
3. **Bitwarden Provider**: Lower precedence

### Overriding Precedence

Use the `precedence` option in injectors to control value resolution:

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
      - "default-url"                 # Finally fallback
```

### Precedence Strategies

| Strategy | Description |
|----------|-------------|
| `first_non_empty` | Use the first non-empty value found |
| `last_non_empty` | Use the last non-empty value found |
| `first` | Use the first value regardless of emptiness |
| `last` | Use the last value regardless of emptiness |

## Best Practices

### Security

1. **Always mask Bitwarden providers**:
   ```yaml
   - type: bws
     id: bws
     mask: true
   ```

2. **Use filtering to limit exposure**:
   ```yaml
   filter_chain:
     - include: '^APP_'
     - exclude: '^APP_DEBUG'
   ```

3. **Avoid passthrough for sensitive environments**:
   ```yaml
   - type: env
     id: env
     passthrough: false
   ```

### Performance

1. **Use appropriate filtering**:
   - Include only necessary keys
   - Exclude system variables when possible

2. **Cache provider values**:
   - Provider values are cached during execution
   - Minimize provider calls in tokens

3. **Use hierarchical dotenv efficiently**:
   - Limit the number of `.env` files
   - Use appropriate precedence strategy

### Configuration Management

1. **Use hierarchical dotenv for development**:
   ```yaml
   - type: dotenv
     hierarchical: true
     precedence: deep-first
   ```

2. **Use Bitwarden for production secrets**:
   ```yaml
   - type: bws
     id: bws
     mask: true
   ```

3. **Provide sensible defaults**:
   ```yaml
   sources:
     - ${PROVIDER:dotenv:PORT|8080}
   ```

## Troubleshooting

### Common Issues

1. **Provider not found**:
   - Check provider ID spelling
   - Verify provider is enabled
   - Check provider configuration

2. **Filter not working**:
   - Verify regex syntax
   - Check filter order
   - Test regex patterns separately

3. **Bitwarden connection issues**:
   - Verify credentials
   - Check network connectivity
   - Validate secret IDs

### Debugging

1. **Use dry-run to see provider values**:
   ```bash
   python -m config_injector.cli run spec.yaml --dry-run
   ```

2. **Enable verbose mode**:
   ```bash
   python -m config_injector.cli run spec.yaml --verbose
   ```

3. **Validate provider configuration**:
   ```bash
   python -m config_injector.cli validate spec.yaml
   ``` 