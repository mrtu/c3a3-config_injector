# Examples

This document provides real-world examples of how to use the Configuration Wrapping Framework for various use cases.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Web Applications](#web-applications)
- [Database Applications](#database-applications)
- [Microservices](#microservices)
- [Development vs Production](#development-vs-production)
- [Security Examples](#security-examples)
- [Complex Scenarios](#complex-scenarios)

## Basic Examples

### Simple Environment Variable Injection

A basic example that sets environment variables for a simple application.

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
    sources:
      - ${ENV:APP_ENV}
      - development

  - name: debug_mode
    kind: env_var
    aliases: [DEBUG]
    sources:
      - ${ENV:DEBUG|false}

target:
  working_dir: "/tmp"
  command: ["echo", "Running in ${APP_ENV} mode with DEBUG=${DEBUG}"]
```

**Usage:**
```bash
# Run with default values
python -m config_injector.cli run basic.yaml

# Run with custom environment
APP_ENV=production DEBUG=true python -m config_injector.cli run basic.yaml
```

### Named Arguments Example

Example showing how to inject named command-line arguments.

```yaml
version: "0.1"
env_passthrough: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

configuration_injectors:
  - name: config_file
    kind: named
    aliases: [--config, -c]
    connector: "="
    sources:
      - ${ENV:CONFIG_FILE}
      - config.yaml

  - name: verbose
    kind: named
    aliases: [--verbose, -v]
    connector: "space"
    sources:
      - ${ENV:VERBOSE|false}

  - name: port
    kind: named
    aliases: [--port, -p]
    connector: "="
    type: int
    sources:
      - ${ENV:PORT|8080}

target:
  working_dir: "/app"
  command: ["python", "app.py"]
```

**Usage:**
```bash
# Run with defaults
python -m config_injector.cli run named_args.yaml

# Run with custom values
CONFIG_FILE=prod.yaml VERBOSE=true PORT=9000 python -m config_injector.cli run named_args.yaml
```

## Web Applications

### Flask Application

A complete example for a Flask web application with database connectivity.

```yaml
version: "0.1"
env_passthrough: true
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

  - type: dotenv
    id: dotenv
    name: Application Config
    hierarchical: true
    filename: .env
    precedence: deep-first

  - type: bws
    id: bws
    name: Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: flask_env
    kind: env_var
    aliases: [FLASK_ENV]
    sources:
      - ${ENV:FLASK_ENV}
      - ${PROVIDER:dotenv:FLASK_ENV}
      - development

  - name: secret_key
    kind: env_var
    aliases: [SECRET_KEY]
    sources:
      - ${PROVIDER:bws:flask-secret-key}
    sensitive: true

  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:dotenv:DATABASE_URL}
      - ${PROVIDER:bws:database-url-secret}
    required: true
    sensitive: true

  - name: redis_url
    kind: env_var
    aliases: [REDIS_URL]
    sources:
      - ${ENV:REDIS_URL}
      - ${PROVIDER:dotenv:REDIS_URL}
      - redis://localhost:6379

  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources:
      - ${ENV:PORT}
      - ${PROVIDER:dotenv:PORT}
      - 5000

  - name: workers
    kind: named
    aliases: [--workers, -w]
    connector: "="
    type: int
    sources:
      - ${ENV:WORKERS}
      - ${PROVIDER:dotenv:WORKERS}
      - 4

  - name: bind_address
    kind: named
    aliases: [--bind]
    connector: "="
    sources:
      - ${ENV:BIND_ADDRESS}
      - 0.0.0.0

target:
  working_dir: "/app"
  command: ["gunicorn", "app:app"]
  stdout:
    path: "~/logs/flask_${DATE:YYYY-MM-DD}.log"
    tee_terminal: true
    append: true
    format: text
  stderr:
    path: "~/logs/flask_${DATE:YYYY-MM-DD}_error.log"
    tee_terminal: true
    append: true
    format: text
```

**Usage:**
```bash
# Development
python -m config_injector.cli run flask_app.yaml

# Production
FLASK_ENV=production python -m config_injector.cli run flask_app.yaml

# With custom port
PORT=8000 python -m config_injector.cli run flask_app.yaml
```

### Django Application

Example for a Django application with comprehensive configuration.

```yaml
version: "0.1"
env_passthrough: true
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

  - type: dotenv
    id: dotenv
    name: Django Config
    hierarchical: true
    filename: .env
    precedence: deep-first

  - type: bws
    id: bws
    name: Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: django_settings
    kind: env_var
    aliases: [DJANGO_SETTINGS_MODULE]
    sources:
      - ${ENV:DJANGO_SETTINGS_MODULE}
      - ${PROVIDER:dotenv:DJANGO_SETTINGS_MODULE}
      - config.settings.production

  - name: secret_key
    kind: env_var
    aliases: [SECRET_KEY]
    sources:
      - ${PROVIDER:bws:django-secret-key}
    sensitive: true

  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:dotenv:DATABASE_URL}
      - ${PROVIDER:bws:database-url-secret}
    required: true
    sensitive: true

  - name: allowed_hosts
    kind: env_var
    aliases: [ALLOWED_HOSTS]
    type: list
    sources:
      - ${ENV:ALLOWED_HOSTS}
      - ${PROVIDER:dotenv:ALLOWED_HOSTS}
      - localhost,127.0.0.1

  - name: debug
    kind: env_var
    aliases: [DEBUG]
    type: bool
    sources:
      - ${ENV:DEBUG}
      - ${PROVIDER:dotenv:DEBUG}
      - false

  - name: static_root
    kind: env_var
    aliases: [STATIC_ROOT]
    sources:
      - ${ENV:STATIC_ROOT}
      - ${PROVIDER:dotenv:STATIC_ROOT}
      - /app/staticfiles

  - name: media_root
    kind: env_var
    aliases: [MEDIA_ROOT]
    sources:
      - ${ENV:MEDIA_ROOT}
      - ${PROVIDER:dotenv:MEDIA_ROOT}
      - /app/media

  - name: port
    kind: named
    aliases: [--port]
    connector: "="
    type: int
    sources:
      - ${ENV:PORT|8000}

  - name: host
    kind: named
    aliases: [--host]
    connector: "="
    sources:
      - ${ENV:HOST|0.0.0.0}

target:
  working_dir: "/app"
  command: ["python", "manage.py", "runserver"]
  stdout:
    path: "~/logs/django_${DATE:YYYY-MM-DD}.log"
    tee_terminal: true
    append: true
    format: text
```

## Database Applications

### PostgreSQL Application

Example for a PostgreSQL application with connection pooling.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Database Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: db_host
    kind: env_var
    aliases: [DB_HOST]
    sources:
      - ${ENV:DB_HOST}
      - ${PROVIDER:bws:db-host-secret}
      - localhost

  - name: db_port
    kind: env_var
    aliases: [DB_PORT]
    type: int
    sources:
      - ${ENV:DB_PORT}
      - ${PROVIDER:bws:db-port-secret}
      - 5432

  - name: db_name
    kind: env_var
    aliases: [DB_NAME]
    sources:
      - ${ENV:DB_NAME}
      - ${PROVIDER:bws:db-name-secret}
      - myapp

  - name: db_user
    kind: env_var
    aliases: [DB_USER]
    sources:
      - ${ENV:DB_USER}
      - ${PROVIDER:bws:db-user-secret}
    required: true
    sensitive: true

  - name: db_password
    kind: env_var
    aliases: [DB_PASSWORD]
    sources:
      - ${PROVIDER:bws:db-password-secret}
    required: true
    sensitive: true

  - name: pool_size
    kind: env_var
    aliases: [POOL_SIZE]
    type: int
    sources:
      - ${ENV:POOL_SIZE|10}

  - name: max_overflow
    kind: env_var
    aliases: [MAX_OVERFLOW]
    type: int
    sources:
      - ${ENV:MAX_OVERFLOW|20}

  - name: ssl_mode
    kind: env_var
    aliases: [SSL_MODE]
    sources:
      - ${ENV:SSL_MODE|require}

  - name: ssl_cert
    kind: file
    aliases: [--ssl-cert]
    sources:
      - ${PROVIDER:bws:ssl-cert-secret}
    sensitive: true

target:
  working_dir: "/app"
  command: ["python", "database_app.py"]
  stdout:
    path: "~/logs/db_${DATE:YYYY-MM-DD}_${TIME:HHmmssSSS}.log"
    tee_terminal: true
    append: false
    format: text
```

### Redis Application

Example for a Redis application with clustering support.

```yaml
version: "0.1"
env_passthrough: true
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

  - type: bws
    id: bws
    name: Redis Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: redis_hosts
    kind: env_var
    aliases: [REDIS_HOSTS]
    type: list
    sources:
      - ${ENV:REDIS_HOSTS}
      - ${PROVIDER:bws:redis-hosts-secret}
      - localhost:6379

  - name: redis_password
    kind: env_var
    aliases: [REDIS_PASSWORD]
    sources:
      - ${PROVIDER:bws:redis-password-secret}
    sensitive: true

  - name: redis_db
    kind: env_var
    aliases: [REDIS_DB]
    type: int
    sources:
      - ${ENV:REDIS_DB|0}

  - name: redis_ssl
    kind: env_var
    aliases: [REDIS_SSL]
    type: bool
    sources:
      - ${ENV:REDIS_SSL|false}

  - name: redis_timeout
    kind: env_var
    aliases: [REDIS_TIMEOUT]
    type: int
    sources:
      - ${ENV:REDIS_TIMEOUT|5}

  - name: redis_retry_on_timeout
    kind: env_var
    aliases: [REDIS_RETRY_ON_TIMEOUT]
    type: bool
    sources:
      - ${ENV:REDIS_RETRY_ON_TIMEOUT|true}

  - name: cluster_mode
    kind: named
    aliases: [--cluster]
    connector: "space"
    sources:
      - ${ENV:CLUSTER_MODE|false}

target:
  working_dir: "/app"
  command: ["python", "redis_app.py"]
```

## Microservices

### API Service

Example for a microservice API with authentication and rate limiting.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: API Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: service_name
    kind: env_var
    aliases: [SERVICE_NAME]
    sources:
      - ${ENV:SERVICE_NAME}
      - api-service

  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:api-key-secret}
    required: true
    sensitive: true

  - name: jwt_secret
    kind: env_var
    aliases: [JWT_SECRET]
    sources:
      - ${PROVIDER:bws:jwt-secret}
    required: true
    sensitive: true

  - name: rate_limit
    kind: env_var
    aliases: [RATE_LIMIT]
    type: int
    sources:
      - ${ENV:RATE_LIMIT|100}

  - name: rate_limit_window
    kind: env_var
    aliases: [RATE_LIMIT_WINDOW]
    type: int
    sources:
      - ${ENV:RATE_LIMIT_WINDOW|3600}

  - name: cors_origins
    kind: env_var
    aliases: [CORS_ORIGINS]
    type: list
    sources:
      - ${ENV:CORS_ORIGINS}
      - http://localhost:3000,https://app.example.com

  - name: log_level
    kind: env_var
    aliases: [LOG_LEVEL]
    sources:
      - ${ENV:LOG_LEVEL|info}

  - name: port
    kind: named
    aliases: [--port, -p]
    connector: "="
    type: int
    sources:
      - ${ENV:PORT|8000}

  - name: host
    kind: named
    aliases: [--host]
    connector: "="
    sources:
      - ${ENV:HOST|0.0.0.0}

  - name: workers
    kind: named
    aliases: [--workers, -w]
    connector: "="
    type: int
    sources:
      - ${ENV:WORKERS|4}

target:
  working_dir: "/app"
  command: ["uvicorn", "main:app"]
  stdout:
    path: "~/logs/api_${DATE:YYYY-MM-DD}.log"
    tee_terminal: true
    append: true
    format: json
  stderr:
    path: "~/logs/api_${DATE:YYYY-MM-DD}_error.log"
    tee_terminal: true
    append: true
    format: json
```

### Background Worker

Example for a background worker service with queue configuration.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Worker Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: worker_id
    kind: env_var
    aliases: [WORKER_ID]
    sources:
      - worker_${PID}

  - name: queue_url
    kind: env_var
    aliases: [QUEUE_URL]
    sources:
      - ${ENV:QUEUE_URL}
      - ${PROVIDER:bws:queue-url-secret}
    required: true
    sensitive: true

  - name: queue_credentials
    kind: env_var
    aliases: [QUEUE_CREDENTIALS]
    sources:
      - ${PROVIDER:bws:queue-credentials-secret}
    required: true
    sensitive: true

  - name: batch_size
    kind: env_var
    aliases: [BATCH_SIZE]
    type: int
    sources:
      - ${ENV:BATCH_SIZE|10}

  - name: poll_interval
    kind: env_var
    aliases: [POLL_INTERVAL]
    type: int
    sources:
      - ${ENV:POLL_INTERVAL|5}

  - name: max_retries
    kind: env_var
    aliases: [MAX_RETRIES]
    type: int
    sources:
      - ${ENV:MAX_RETRIES|3}

  - name: dead_letter_queue
    kind: env_var
    aliases: [DEAD_LETTER_QUEUE]
    sources:
      - ${ENV:DEAD_LETTER_QUEUE}
      - ${PROVIDER:bws:dlq-url-secret}

  - name: log_level
    kind: env_var
    aliases: [LOG_LEVEL]
    sources:
      - ${ENV:LOG_LEVEL|info}

  - name: queue_name
    kind: positional
    order: 1
    sources:
      - ${ENV:QUEUE_NAME}
      - default-queue

target:
  working_dir: "/app"
  command: ["python", "worker.py"]
  stdout:
    path: "~/logs/worker_${DATE:YYYY-MM-DD}_${PID}.log"
    tee_terminal: true
    append: true
    format: json
```

## Development vs Production

### Environment-Specific Configuration

Example showing how to use profiles for different environments.

```yaml
version: "0.1"
env_passthrough: true
mask_defaults: false

profiles:
  development:
    env_passthrough: true
    mask_defaults: false
    configuration_injectors:
      - name: debug
        kind: env_var
        aliases: [DEBUG]
        sources: ["true"]
      
      - name: log_level
        kind: env_var
        aliases: [LOG_LEVEL]
        sources: ["debug"]

  production:
    env_passthrough: false
    mask_defaults: true
    configuration_injectors:
      - name: debug
        kind: env_var
        aliases: [DEBUG]
        sources: ["false"]
      
      - name: log_level
        kind: env_var
        aliases: [LOG_LEVEL]
        sources: ["info"]

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: true

  - type: dotenv
    id: dotenv
    name: Environment Config
    hierarchical: true
    filename: .env.${ENV:ENVIRONMENT|development}
    precedence: deep-first

  - type: bws
    id: bws
    name: Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: environment
    kind: env_var
    aliases: [ENVIRONMENT]
    sources:
      - ${ENV:ENVIRONMENT}
      - development

  - name: database_url
    kind: env_var
    aliases: [DATABASE_URL]
    sources:
      - ${ENV:DATABASE_URL}
      - ${PROVIDER:dotenv:DATABASE_URL}
      - ${PROVIDER:bws:database-url-secret}
    required: true
    sensitive: true

  - name: api_key
    kind: env_var
    aliases: [API_KEY]
    sources:
      - ${PROVIDER:bws:api-key-secret}
    sensitive: true

  - name: port
    kind: env_var
    aliases: [PORT]
    type: int
    sources:
      - ${ENV:PORT|8000}

target:
  working_dir: "/app"
  command: ["python", "app.py"]
  stdout:
    path: "~/logs/app_${DATE:YYYY-MM-DD}.log"
    tee_terminal: true
    append: true
    format: text
```

**Usage:**
```bash
# Development
python -m config_injector.cli run app.yaml --profile development

# Production
python -m config_injector.cli run app.yaml --profile production

# With environment variable
ENVIRONMENT=staging python -m config_injector.cli run app.yaml --profile staging
```

## Security Examples

### Secure Application with Secrets

Example demonstrating secure handling of sensitive data.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Application Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: app_secret
    kind: env_var
    aliases: [APP_SECRET]
    sources:
      - ${PROVIDER:bws:app-secret}
    required: true
    sensitive: true

  - name: database_password
    kind: env_var
    aliases: [DB_PASSWORD]
    sources:
      - ${PROVIDER:bws:db-password}
    required: true
    sensitive: true

  - name: ssl_cert
    kind: file
    aliases: [--ssl-cert]
    sources:
      - ${PROVIDER:bws:ssl-cert}
    sensitive: true

  - name: ssl_key
    kind: file
    aliases: [--ssl-key]
    sources:
      - ${PROVIDER:bws:ssl-key}
    sensitive: true

  - name: jwt_secret
    kind: env_var
    aliases: [JWT_SECRET]
    sources:
      - ${PROVIDER:bws:jwt-secret}
    required: true
    sensitive: true

  - name: encryption_key
    kind: env_var
    aliases: [ENCRYPTION_KEY]
    sources:
      - ${PROVIDER:bws:encryption-key}
    required: true
    sensitive: true

  - name: allowed_ips
    kind: env_var
    aliases: [ALLOWED_IPS]
    type: list
    sources:
      - ${ENV:ALLOWED_IPS}
      - 127.0.0.1,::1

target:
  working_dir: "/app"
  command: ["python", "secure_app.py"]
  stdout:
    path: "~/logs/secure_${DATE:YYYY-MM-DD}.log"
    tee_terminal: false
    append: true
    format: json
  stderr:
    path: "~/logs/secure_${DATE:YYYY-MM-DD}_error.log"
    tee_terminal: false
    append: true
    format: json
```

### Multi-Tenant Application

Example for a multi-tenant application with tenant-specific configuration.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Tenant Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: tenant_id
    kind: env_var
    aliases: [TENANT_ID]
    sources:
      - ${ENV:TENANT_ID}
    required: true

  - name: tenant_config
    kind: file
    aliases: [--config]
    sources:
      - |
        tenant: ${TENANT_ID}
        database:
          url: ${PROVIDER:bws:tenant-${TENANT_ID}-db-url}
        api:
          key: ${PROVIDER:bws:tenant-${TENANT_ID}-api-key}
        storage:
          bucket: ${PROVIDER:bws:tenant-${TENANT_ID}-bucket}
    sensitive: true

  - name: tenant_secret
    kind: env_var
    aliases: [TENANT_SECRET]
    sources:
      - ${PROVIDER:bws:tenant-${TENANT_ID}-secret}
    required: true
    sensitive: true

  - name: tenant_domain
    kind: env_var
    aliases: [TENANT_DOMAIN]
    sources:
      - ${PROVIDER:bws:tenant-${TENANT_ID}-domain}
    required: true

target:
  working_dir: "/app"
  command: ["python", "tenant_app.py"]
```

## Complex Scenarios

### Load Balancer Configuration

Example for configuring a load balancer with health checks and SSL termination.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Load Balancer Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: lb_config
    kind: file
    aliases: [--config]
    sources:
      - |
        global:
          daemon: off
          maxconn: 4096
          log: /dev/log local0
          log: /dev/log local1 notice
          chroot: /var/lib/haproxy
          stats: socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
          stats: timeout 30s
          user: haproxy
          group: haproxy

        defaults:
          log: global
          mode: http
          option: httplog
          option: dontlognull
          timeout: connect 5000
          timeout: client 50000
          timeout: server 50000

        frontend http_front
          bind *:80
          bind *:443 ssl crt /etc/ssl/certs/combined.pem
          http-request redirect scheme https unless { ssl_fc }
          default_backend http_back

        backend http_back
          balance roundrobin
          server app1 ${PROVIDER:bws:app1-host}:${PROVIDER:bws:app1-port} check
          server app2 ${PROVIDER:bws:app2-host}:${PROVIDER:bws:app2-port} check
          server app3 ${PROVIDER:bws:app3-host}:${PROVIDER:bws:app3-port} check

        listen stats
          bind *:8404
          stats enable
          stats uri /stats
          stats refresh 10s
          stats auth ${PROVIDER:bws:stats-user}:${PROVIDER:bws:stats-password}
    sensitive: true

  - name: ssl_cert
    kind: file
    aliases: [--ssl-cert]
    sources:
      - ${PROVIDER:bws:ssl-cert}
    sensitive: true

  - name: ssl_key
    kind: file
    aliases: [--ssl-key]
    sources:
      - ${PROVIDER:bws:ssl-key}
    sensitive: true

  - name: stats_user
    kind: env_var
    aliases: [STATS_USER]
    sources:
      - ${PROVIDER:bws:stats-user}
    sensitive: true

  - name: stats_password
    kind: env_var
    aliases: [STATS_PASSWORD]
    sources:
      - ${PROVIDER:bws:stats-password}
    sensitive: true

target:
  working_dir: "/etc/haproxy"
  command: ["haproxy", "-f", "haproxy.cfg"]
  stdout:
    path: "~/logs/haproxy_${DATE:YYYY-MM-DD}.log"
    tee_terminal: true
    append: true
    format: text
```

### Data Pipeline Configuration

Example for a data processing pipeline with multiple stages.

```yaml
version: "0.1"
env_passthrough: false
mask_defaults: true

configuration_providers:
  - type: env
    id: env
    name: Host Environment
    passthrough: false

  - type: bws
    id: bws
    name: Pipeline Secrets
    vault_url: ${ENV:BWS_VAULT_URL}
    access_token: ${ENV:BWS_ACCESS_TOKEN}
    mask: true

configuration_injectors:
  - name: pipeline_id
    kind: env_var
    aliases: [PIPELINE_ID]
    sources:
      - pipeline_${DATE:YYYYMMDD}_${TIME:HHmmssSSS}

  - name: input_config
    kind: file
    aliases: [--input-config]
    sources:
      - |
        {
          "source": {
            "type": "kafka",
            "bootstrap_servers": "${PROVIDER:bws:kafka-servers}",
            "topic": "${ENV:INPUT_TOPIC}",
            "group_id": "${PIPELINE_ID}",
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "sasl_username": "${PROVIDER:bws:kafka-username}",
            "sasl_password": "${PROVIDER:bws:kafka-password}"
          },
          "format": "json",
          "batch_size": ${ENV:BATCH_SIZE|1000},
          "batch_timeout": ${ENV:BATCH_TIMEOUT|30}
        }
    sensitive: true

  - name: output_config
    kind: file
    aliases: [--output-config]
    sources:
      - |
        {
          "destination": {
            "type": "elasticsearch",
            "hosts": "${PROVIDER:bws:es-hosts}",
            "index": "${ENV:OUTPUT_INDEX}",
            "username": "${PROVIDER:bws:es-username}",
            "password": "${PROVIDER:bws:es-password}"
          },
          "format": "json",
          "bulk_size": ${ENV:BULK_SIZE|1000}
        }
    sensitive: true

  - name: transform_config
    kind: file
    aliases: [--transform-config]
    sources:
      - |
        {
          "filters": [
            {
              "type": "field_filter",
              "include": ["id", "timestamp", "data", "metadata"]
            },
            {
              "type": "timestamp_filter",
              "field": "timestamp",
              "format": "iso8601"
            }
          ],
          "transformations": [
            {
              "type": "field_mapping",
              "mappings": {
                "id": "document_id",
                "timestamp": "created_at",
                "data": "content"
              }
            }
          ]
        }

  - name: monitoring_config
    kind: file
    aliases: [--monitoring-config]
    sources:
      - |
        {
          "metrics": {
            "enabled": true,
            "endpoint": "${PROVIDER:bws:metrics-endpoint}",
            "interval": ${ENV:METRICS_INTERVAL|60}
          },
          "logging": {
            "level": "${ENV:LOG_LEVEL|info}",
            "format": "json"
          },
          "health_check": {
            "enabled": true,
            "port": ${ENV:HEALTH_PORT|8080}
          }
        }

target:
  working_dir: "/app"
  command: ["python", "pipeline.py"]
  stdout:
    path: "~/logs/pipeline_${PIPELINE_ID}.log"
    tee_terminal: true
    append: true
    format: json
  stderr:
    path: "~/logs/pipeline_${PIPELINE_ID}_error.log"
    tee_terminal: true
    append: true
    format: json
```

## Usage Patterns

### Development Workflow

1. **Start with a simple configuration**:
   ```bash
   python -m config_injector.cli run basic.yaml --dry-run
   ```

2. **Add environment-specific settings**:
   ```bash
   python -m config_injector.cli run app.yaml --profile development
   ```

3. **Test with different configurations**:
   ```bash
   python -m config_injector.cli run app.yaml --profile staging
   python -m config_injector.cli run app.yaml --profile production
   ```

### Production Deployment

1. **Validate configuration**:
   ```bash
   python -m config_injector.cli validate app.yaml --strict
   ```

2. **Dry run to preview**:
   ```bash
   python -m config_injector.cli run app.yaml --dry-run --json
   ```

3. **Execute with production settings**:
   ```bash
   python -m config_injector.cli run app.yaml --profile production --quiet
   ```

### Debugging

1. **Use explain to understand configuration**:
   ```bash
   python -m config_injector.cli explain app.yaml --verbose
   ```

2. **Use dry-run to see resolved values**:
   ```bash
   python -m config_injector.cli run app.yaml --dry-run --verbose
   ```

3. **Check for validation errors**:
   ```bash
   python -m config_injector.cli validate app.yaml --strict --verbose
   ``` 
These examples demonstrate the flexibility and power of the Configuration Wrapping Framework for various real-world scenarios. Each example can be customized and extended based on specific requirements. 