# Nexus Framework Configuration Guide

## Table of Contents
- [Overview](#overview)
- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Core Configuration](#core-configuration)
- [Database Configuration](#database-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Plugin Configuration](#plugin-configuration)
- [Security Settings](#security-settings)
- [Performance Tuning](#performance-tuning)
- [Logging Configuration](#logging-configuration)
- [Cache Configuration](#cache-configuration)
- [API Configuration](#api-configuration)
- [WebSocket Configuration](#websocket-configuration)
- [Email Configuration](#email-configuration)
- [Storage Configuration](#storage-configuration)
- [Environment-Specific Configurations](#environment-specific-configurations)
- [Configuration Validation](#configuration-validation)
- [Best Practices](#best-practices)

## Overview

The Nexus Framework uses a hierarchical configuration system that supports multiple formats and sources. Configuration can be provided through:

1. **Configuration files** (YAML, JSON, TOML)
2. **Environment variables**
3. **Command-line arguments**
4. **Plugin configurations**
5. **Runtime configuration API**

Configuration priority (highest to lowest):
1. Command-line arguments
2. Environment variables
3. Configuration files
4. Default values

## Configuration Files

### File Locations

The framework searches for configuration files in the following order:

```
1. ./config.yaml (or .json, .toml)
2. ./config/config.yaml
3. /etc/nexus/config.yaml
4. ~/.nexus/config.yaml
5. $NEXUS_CONFIG_PATH (if set)
```

### Supported Formats

#### YAML Configuration (Recommended)
```yaml
# config.yaml
app:
  name: "My Nexus Application"
  version: "1.0.0"
  environment: "production"
  debug: false
  host: "0.0.0.0"
  port: 8000
  
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  name: "nexus_db"
  user: "nexus_user"
  password: "${DB_PASSWORD}"  # Environment variable substitution
  
auth:
  jwt_secret: "${JWT_SECRET}"
  token_expiry: 3600
  refresh_token_expiry: 604800
  
plugins:
  directory: "./plugins"
  auto_load: true
  hot_reload: true
```

#### JSON Configuration
```json
{
  "app": {
    "name": "My Nexus Application",
    "version": "1.0.0",
    "environment": "production",
    "debug": false,
    "host": "0.0.0.0",
    "port": 8000
  },
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "name": "nexus_db",
    "user": "nexus_user",
    "password": "${DB_PASSWORD}"
  }
}
```

#### TOML Configuration
```toml
[app]
name = "My Nexus Application"
version = "1.0.0"
environment = "production"
debug = false
host = "0.0.0.0"
port = 8000

[database]
type = "postgresql"
host = "localhost"
port = 5432
name = "nexus_db"
user = "nexus_user"
password = "${DB_PASSWORD}"
```

## Environment Variables

### System Environment Variables

All configuration options can be set via environment variables using the prefix `NEXUS_`:

```bash
# Application settings
export NEXUS_APP_NAME="My Nexus App"
export NEXUS_APP_ENVIRONMENT="production"
export NEXUS_APP_DEBUG="false"
export NEXUS_APP_HOST="0.0.0.0"
export NEXUS_APP_PORT="8000"

# Database settings
export NEXUS_DATABASE_TYPE="postgresql"
export NEXUS_DATABASE_HOST="localhost"
export NEXUS_DATABASE_PORT="5432"
export NEXUS_DATABASE_NAME="nexus_db"
export NEXUS_DATABASE_USER="nexus_user"
export NEXUS_DATABASE_PASSWORD="secure_password"

# Authentication settings
export NEXUS_AUTH_JWT_SECRET="your-secret-key"
export NEXUS_AUTH_TOKEN_EXPIRY="3600"
```

### .env File Support

Create a `.env` file in your project root:

```bash
# .env
NEXUS_APP_NAME=My Nexus App
NEXUS_APP_ENVIRONMENT=development
NEXUS_APP_DEBUG=true

# Database
NEXUS_DATABASE_TYPE=postgresql
NEXUS_DATABASE_HOST=localhost
NEXUS_DATABASE_PORT=5432
NEXUS_DATABASE_NAME=nexus_dev
NEXUS_DATABASE_USER=developer
NEXUS_DATABASE_PASSWORD=dev_password

# Authentication
NEXUS_AUTH_JWT_SECRET=development-secret-key
NEXUS_AUTH_TOKEN_EXPIRY=7200

# Redis Cache
NEXUS_CACHE_TYPE=redis
NEXUS_CACHE_REDIS_HOST=localhost
NEXUS_CACHE_REDIS_PORT=6379

# Email
NEXUS_EMAIL_SMTP_HOST=smtp.gmail.com
NEXUS_EMAIL_SMTP_PORT=587
NEXUS_EMAIL_USERNAME=your-email@gmail.com
NEXUS_EMAIL_PASSWORD=your-app-password
```

## Core Configuration

### Application Settings

```yaml
app:
  # Application name
  name: "Nexus Application"
  
  # Application version
  version: "1.0.0"
  
  # Environment (development, staging, production)
  environment: "production"
  
  # Enable debug mode
  debug: false
  
  # Server host
  host: "0.0.0.0"
  
  # Server port
  port: 8000
  
  # Worker processes (0 = auto-detect CPU cores)
  workers: 0
  
  # Request timeout (seconds)
  timeout: 30
  
  # Maximum request size (bytes)
  max_request_size: 10485760  # 10MB
  
  # CORS settings
  cors:
    enabled: true
    origins: ["*"]
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    headers: ["*"]
    credentials: true
  
  # Static files
  static:
    enabled: true
    directory: "./static"
    url_path: "/static"
  
  # API prefix
  api_prefix: "/api"
  
  # Timezone
  timezone: "UTC"
  
  # Locale
  locale: "en_US"
```

### Server Configuration

```yaml
server:
  # Uvicorn settings
  uvicorn:
    reload: false
    log_level: "info"
    access_log: true
    use_colors: true
    
  # Gunicorn settings (production)
  gunicorn:
    workers: 4
    worker_class: "uvicorn.workers.UvicornWorker"
    worker_connections: 1000
    max_requests: 1000
    max_requests_jitter: 50
    timeout: 30
    keepalive: 2
    
  # SSL/TLS
  ssl:
    enabled: false
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
    
  # HTTP/2
  http2:
    enabled: true
    
  # Compression
  compression:
    enabled: true
    level: 6
    min_size: 1000
```

## Database Configuration

### PostgreSQL Configuration

```yaml
database:
  type: "postgresql"
  
  # Connection settings
  connection:
    host: "localhost"
    port: 5432
    database: "nexus_db"
    user: "nexus_user"
    password: "${DB_PASSWORD}"
    
  # Connection pool
  pool:
    min_size: 10
    max_size: 20
    max_overflow: 10
    pool_timeout: 30
    pool_recycle: 3600
    pool_pre_ping: true
    
  # Query settings
  query:
    echo: false
    echo_pool: false
    execution_options:
      isolation_level: "READ_COMMITTED"
      
  # Migrations
  migrations:
    enabled: true
    directory: "./migrations"
    auto_upgrade: false
```

### MongoDB Configuration

```yaml
database:
  type: "mongodb"
  
  # Connection settings
  connection:
    uri: "mongodb://localhost:27017/nexus_db"
    # Or use individual settings:
    host: "localhost"
    port: 27017
    database: "nexus_db"
    username: "nexus_user"
    password: "${MONGO_PASSWORD}"
    auth_source: "admin"
    
  # Connection pool
  pool:
    max_pool_size: 100
    min_pool_size: 10
    max_idle_time_ms: 300000
    wait_queue_timeout_ms: 30000
    
  # Options
  options:
    server_selection_timeout_ms: 30000
    connect_timeout_ms: 20000
    socket_timeout_ms: 20000
    
  # Indexes
  indexes:
    auto_create: true
    background: true
```

### MySQL Configuration

```yaml
database:
  type: "mysql"
  
  connection:
    host: "localhost"
    port: 3306
    database: "nexus_db"
    user: "nexus_user"
    password: "${MYSQL_PASSWORD}"
    charset: "utf8mb4"
    
  pool:
    pool_size: 10
    max_overflow: 20
    pool_timeout: 30
    pool_recycle: 3600
```

### SQLite Configuration

```yaml
database:
  type: "sqlite"
  
  connection:
    path: "./data/nexus.db"
    # For in-memory database:
    # path: ":memory:"
    
  options:
    check_same_thread: false
    timeout: 10
    isolation_level: "DEFERRED"
```

## Authentication Configuration

```yaml
auth:
  # JWT Configuration
  jwt:
    secret: "${JWT_SECRET}"  # Required: Set via environment variable
    algorithm: "HS256"
    token_expiry: 3600  # 1 hour
    refresh_token_expiry: 604800  # 7 days
    issuer: "nexus-framework"
    audience: "nexus-api"
    
  # Session Configuration
  session:
    enabled: true
    secret: "${SESSION_SECRET}"
    max_age: 86400  # 24 hours
    same_site: "lax"
    http_only: true
    secure: true  # Set to true in production with HTTPS
    
  # OAuth2 Providers
  oauth2:
    enabled: true
    providers:
      google:
        client_id: "${GOOGLE_CLIENT_ID}"
        client_secret: "${GOOGLE_CLIENT_SECRET}"
        redirect_uri: "http://localhost:8000/api/auth/google/callback"
        scopes: ["openid", "email", "profile"]
        
      github:
        client_id: "${GITHUB_CLIENT_ID}"
        client_secret: "${GITHUB_CLIENT_SECRET}"
        redirect_uri: "http://localhost:8000/api/auth/github/callback"
        scopes: ["user:email"]
        
  # API Key Configuration
  api_keys:
    enabled: true
    header_name: "X-API-Key"
    query_param: "api_key"
    
  # Multi-Factor Authentication
  mfa:
    enabled: false
    issuer: "Nexus Framework"
    totp:
      digits: 6
      period: 30
      algorithm: "SHA1"
      
  # Password Policy
  password_policy:
    min_length: 8
    require_uppercase: true
    require_lowercase: true
    require_digits: true
    require_special: true
    special_chars: "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
  # Account Security
  security:
    max_login_attempts: 5
    lockout_duration: 900  # 15 minutes
    password_reset_expiry: 3600  # 1 hour
    email_verification_required: true
    email_verification_expiry: 86400  # 24 hours
```

## Plugin Configuration

```yaml
plugins:
  # Plugin directories
  directories:
    - "./plugins"
    - "/usr/share/nexus/plugins"
    
  # Plugin loading
  loading:
    auto_load: true
    hot_reload: true
    lazy_load: false
    parallel_load: true
    load_timeout: 30
    
  # Plugin discovery
  discovery:
    enabled: true
    scan_interval: 60  # seconds
    file_patterns:
      - "*.py"
      - "plugin.yaml"
      - "manifest.json"
      
  # Plugin management
  management:
    allow_install: true
    allow_uninstall: true
    allow_update: true
    require_signature: false
    
  # Plugin registry
  registry:
    enabled: true
    url: "https://plugins.nexus-framework.dev"
    cache_ttl: 3600
    
  # Plugin sandbox
  sandbox:
    enabled: false
    memory_limit: "512MB"
    cpu_limit: 1.0
    timeout: 30
    
  # Plugin-specific configurations
  configs:
    analytics_dashboard:
      api_key: "${ANALYTICS_API_KEY}"
      refresh_interval: 60
      cache_results: true
      
    email_sender:
      provider: "smtp"
      from_address: "noreply@example.com"
      from_name: "Nexus Framework"
```

## Security Settings

```yaml
security:
  # HTTPS/TLS
  https:
    enabled: true
    redirect_http: true
    hsts:
      enabled: true
      max_age: 31536000
      include_subdomains: true
      preload: true
      
  # Content Security Policy
  csp:
    enabled: true
    directives:
      default_src: ["'self'"]
      script_src: ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"]
      style_src: ["'self'", "'unsafe-inline'", "fonts.googleapis.com"]
      font_src: ["'self'", "fonts.gstatic.com"]
      img_src: ["'self'", "data:", "https:"]
      
  # Rate Limiting
  rate_limiting:
    enabled: true
    default:
      requests: 1000
      window: 3600  # 1 hour
    endpoints:
      "/api/auth/login":
        requests: 10
        window: 900  # 15 minutes
      "/api/auth/register":
        requests: 5
        window: 3600
        
  # IP Filtering
  ip_filtering:
    enabled: false
    whitelist:
      - "192.168.1.0/24"
      - "10.0.0.0/8"
    blacklist:
      - "192.168.100.50"
      
  # Request Validation
  validation:
    max_request_size: 10485760  # 10MB
    max_json_depth: 10
    max_array_length: 1000
    max_string_length: 10000
    
  # XSS Protection
  xss_protection:
    enabled: true
    mode: "block"
    
  # CSRF Protection
  csrf:
    enabled: true
    token_length: 32
    cookie_name: "csrf_token"
    header_name: "X-CSRF-Token"
    
  # Security Headers
  headers:
    x_frame_options: "DENY"
    x_content_type_options: "nosniff"
    x_xss_protection: "1; mode=block"
    referrer_policy: "strict-origin-when-cross-origin"
    permissions_policy: "geolocation=(), microphone=(), camera=()"
```

## Performance Tuning

```yaml
performance:
  # Caching
  cache:
    type: "redis"  # redis, memcached, memory
    redis:
      host: "localhost"
      port: 6379
      db: 0
      password: "${REDIS_PASSWORD}"
      max_connections: 50
      socket_timeout: 5
      socket_connect_timeout: 5
      
    default_ttl: 300
    max_entries: 10000
    
  # Database Optimization
  database:
    query_cache:
      enabled: true
      size: 1000
      ttl: 60
      
    connection_pool:
      min_size: 10
      max_size: 100
      timeout: 30
      recycle: 3600
      
    query_optimization:
      explain_slow_queries: true
      slow_query_threshold: 1000  # milliseconds
      
  # Request Processing
  request:
    max_workers: 0  # 0 = auto
    worker_timeout: 30
    keepalive_timeout: 5
    request_queue_size: 100
    
  # Response Optimization
  response:
    compression:
      enabled: true
      level: 6
      min_size: 1000
      types:
        - "application/json"
        - "text/html"
        - "text/css"
        - "application/javascript"
        
    etag:
      enabled: true
      weak: false
      
  # Static Files
  static:
    cache_control: "public, max-age=31536000"
    use_x_sendfile: false
    use_x_accel: false
    
  # Background Tasks
  tasks:
    type: "celery"  # celery, rq, arq
    broker_url: "redis://localhost:6379/0"
    result_backend: "redis://localhost:6379/1"
    max_workers: 4
    task_timeout: 300
```

## Logging Configuration

```yaml
logging:
  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  level: "INFO"
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"
  
  # Console logging
  console:
    enabled: true
    level: "INFO"
    colorize: true
    
  # File logging
  file:
    enabled: true
    level: "DEBUG"
    path: "./logs/nexus.log"
    max_size: 10485760  # 10MB
    backup_count: 5
    encoding: "utf-8"
    
  # Structured logging
  structured:
    enabled: false
    format: "json"
    include_context: true
    
  # Syslog
  syslog:
    enabled: false
    host: "localhost"
    port: 514
    facility: "local0"
    
  # External services
  external:
    sentry:
      enabled: false
      dsn: "${SENTRY_DSN}"
      environment: "production"
      traces_sample_rate: 0.1
      
    elasticsearch:
      enabled: false
      hosts:
        - "http://localhost:9200"
      index: "nexus-logs"
      
  # Log filtering
  filters:
    - name: "sqlalchemy.engine"
      level: "WARNING"
    - name: "urllib3.connectionpool"
      level: "WARNING"
```

## Cache Configuration

```yaml
cache:
  # Cache backend
  backend: "redis"  # redis, memcached, memory, dynamodb
  
  # Redis configuration
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: "${REDIS_PASSWORD}"
    ssl: false
    ssl_cert_reqs: "required"
    max_connections: 50
    
    # Cluster mode
    cluster:
      enabled: false
      nodes:
        - "redis://node1:6379"
        - "redis://node2:6379"
        - "redis://node3:6379"
        
    # Sentinel mode
    sentinel:
      enabled: false
      master_name: "mymaster"
      sentinels:
        - ["localhost", 26379]
        - ["localhost", 26380]
        
  # Memcached configuration
  memcached:
    servers:
      - "localhost:11211"
    username: null
    password: null
    
  # Cache settings
  settings:
    default_timeout: 300
    key_prefix: "nexus:"
    version: 1
    key_function: null
    
  # Cache policies
  policies:
    eviction: "lru"  # lru, lfu, ttl
    max_entries: 10000
    max_memory: "256MB"
    
  # Cache warming
  warming:
    enabled: false
    on_startup: true
    schedule: "0 * * * *"  # Hourly
    keys:
      - "config:*"
      - "user:*:profile"
```

## API Configuration

```yaml
api:
  # API versioning
  versioning:
    enabled: true
    default_version: "v1"
    header_name: "X-API-Version"
    query_param: "version"
    
  # Documentation
  documentation:
    enabled: true
    title: "Nexus API"
    description: "Nexus Framework API Documentation"
    version: "1.0.0"
    terms_of_service: "https://example.com/terms"
    contact:
      name: "API Support"
      email: "api@example.com"
      url: "https://example.com/support"
    license:
      name: "MIT"
      url: "https://opensource.org/licenses/MIT"
      
  # OpenAPI/Swagger
  openapi:
    enabled: true
    url: "/openapi.json"
    swagger_ui_url: "/docs"
    redoc_url: "/redoc"
    
  # GraphQL
  graphql:
    enabled: false
    path: "/graphql"
    playground: true
    introspection: true
    
  # Response formatting
  response:
    envelope: true
    envelope_format:
      data: "data"
      error: "error"
      meta: "meta"
    pretty_print: false
    
  # Pagination
  pagination:
    default_page_size: 20
    max_page_size: 100
    page_query_param: "page"
    size_query_param: "limit"
```

## WebSocket Configuration

```yaml
websocket:
  enabled: true
  path: "/ws"
  
  # Connection settings
  connection:
    ping_interval: 20
    ping_timeout: 10
    max_connections: 1000
    max_message_size: 65536  # 64KB
    
  # Authentication
  auth:
    required: true
    token_header: "Authorization"
    token_query_param: "token"
    
  # Channels
  channels:
    max_channels_per_connection: 10
    default_channels:
      - "system"
      - "notifications"
      
  # Broadcasting
  broadcast:
    backend: "redis"  # redis, memory, rabbitmq
    redis:
      url: "redis://localhost:6379/2"
      
  # Rate limiting
  rate_limit:
    messages_per_second: 10
    connections_per_ip: 5
```

## Email Configuration

```yaml
email:
  # Email backend
  backend: "smtp"  # smtp, sendgrid, ses, mailgun
  
  # SMTP settings
  smtp:
    host: "smtp.gmail.com"
    port: 587
    username: "${EMAIL_USERNAME}"
    password: "${EMAIL_PASSWORD}"
    use_tls: true
    use_ssl: false
    timeout: 10
    
  # SendGrid settings
  sendgrid:
    api_key: "${SENDGRID_API_KEY}"
    
  # AWS SES settings
  ses:
    aws_access_key_id: "${AWS_ACCESS_KEY_ID}"
    aws_secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
    region: "us-east-1"
    
  # Mailgun settings
  mailgun:
    api_key: "${MAILGUN_API_KEY}"
    domain: "mg.example.com"
    
  # Default settings
  defaults:
    from_email: "noreply@example.com"
    from_name: "Nexus Framework"
    reply_to: "support@example.com"
    
  # Templates
  templates:
    directory: "./templates/email"
    engine: "jinja2"
    
  # Queue settings
  queue:
    enabled: true
    backend: "celery"
    max_retries: 3
    retry_delay: 60
```

## Storage Configuration

```yaml
storage:
  # Default storage backend
  default: "local"
  
  # Storage backends
  backends:
    local:
      type: "filesystem"
      root_path: "./data/uploads"
      base_url: "/uploads"
      
    s3:
      type: "s3"
      aws_access_key_id: "${AWS_ACCESS_KEY_ID}"
      aws_secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
      bucket_name: "nexus-uploads"
      region: "us-east-1"
      base_url: "https://nexus-uploads.s3.amazonaws.com"
      
    gcs:
      type: "gcs"
      credentials_path: "./credentials/gcs.json"
      bucket_name: "nexus-uploads"
      base_url: "https://storage.googleapis.com/nexus-uploads"
      
    azure:
      type: "azure"
      account_name: "${AZURE_ACCOUNT_NAME}"
      account_key: "${AZURE_ACCOUNT_KEY}"
      container_name: "nexus-uploads"
      base_url: "https://nexus.blob.core.windows.net"
      
  # Upload settings
  upload:
    max_file_size: 10485760  # 10MB
    allowed_extensions:
      - ".jpg"
      - ".jpeg"
      - ".png"
      - ".gif"
      - ".pdf"
      - ".doc"
      - ".docx"
    chunk_size: 4096
    
  # CDN settings
  cdn:
    enabled: false
    url: "https://cdn.example.com"
    
  # Image processing
  images:
    process_on_upload: true
    formats:
      thumbnail:
        width: 150
        height: 150
        quality: 85
      medium:
        width: 800
        height: 600
        quality: 90
      large:
        width: 1920
        height: 1080
        quality: 95
```

## Environment-Specific Configurations

### Development Configuration

```yaml
# config.development.yaml
app:
  environment: "development"
  debug: true
  
server:
  uvicorn:
    reload: true
    log_level: "debug"
    
database:
  connection:
    echo: true
    
cache:
  backend: "memory"
  
security:
  https:
    enabled: false
  rate_limiting:
    enabled: false
    
logging:
  level: "DEBUG"
  console:
    level: "DEBUG"
```

### Production Configuration

```yaml
# config.production.yaml
app:
  environment: "production"
  debug: false
  
server:
  gunicorn:
    workers: 4
    
database:
  pool:
    min_size: 20
    max_size: 100
    
cache:
  backend: "redis"
  redis:
    cluster:
      enabled: true
      
security:
  https:
    enabled: true
    redirect_http: true
  rate_limiting:
    enabled: true
    
logging:
  level: "WARNING"
  external:
    sentry:
      enabled: true
```

### Staging Configuration

```yaml
# config.staging.yaml
app:
  environment: "staging"
  debug: false
  
server:
  workers: 2
  
database:
  pool:
    min_size: 10
    max_size: 50
    
security:
  https:
    enabled: true
  rate_limiting:
    enabled: true
    default:
      requests: 5000
      window: 3600
```

## Configuration Validation

### Schema Validation

```python
# config_schema.py
from pydantic import BaseSettings, Field, validator
from typing import Optional, List, Dict

class DatabaseConfig(BaseSettings):
    type: str = Field(..., regex="^(postgresql|mysql|mongodb|sqlite)$")
    host: str = "localhost"
    port: int = Field(5432, ge=1, le=65535)
    database: str
    user: Optional[str]
    password: Optional[str]
    
    @validator("password")
    def validate_password(cls, v, values):
        if values.get("type") != "sqlite" and not v:
            raise ValueError("Password required for database type")
        return v

class AppConfig(BaseSettings):
    name: str = "Nexus Application"
    version: str = "1.0.0"
    environment: str = Field("development", regex="^(development|staging|production)$")
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = Field(8000, ge=1, le=65535)
    
class NexusConfig(BaseSettings):
    app: AppConfig
    database: DatabaseConfig
    
    class Config:
        env_prefix = "NEXUS_"
        env_nested_delimiter = "__"
```

### Validation on Startup

```python
# validate_config.py
from nexus.config import load_config, validate_config

def startup_validation():
    """Validate configuration on application startup."""
    config = load_config()
    
    # Validate required fields
    required_fields = [
        "app.name",
        "database.type",
        "auth.jwt.secret"
    ]
    
    for field in required_fields:
        if not config.get_nested(field):
            raise ValueError(f"Required configuration field missing: {field}")
    
    # Validate database connection
    if not test_database_connection(config.database):
        raise ConnectionError("Failed to connect to database")
    
    # Validate plugin directory exists
    if not os.path.exists(config.plugins.directory):
        os.makedirs(config.plugins.directory)
    
    return config
```

## Best Practices

### 1. Security Best Practices

- **Never commit secrets** to version control
- **Use environment variables** for sensitive data
- **Rotate secrets regularly**
- **Use strong encryption** for passwords
- **Enable HTTPS** in production
- **Implement rate limiting**
- **Use secure defaults**

### 2. Configuration Management

- **Use configuration profiles** for different environments
- **Validate configuration** on startup
- **Document all configuration options**
- **Provide sensible defaults**
- **Use configuration schemas**
- **Implement configuration hot-reload** where appropriate

### 3. Environment Variables

```bash
# Use a .env file for local development
cp .env.example .env

# Use secrets management in production
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
# - Azure Key Vault
```

### 4. Configuration Hierarchy

```yaml
# 1. Base configuration (config.yaml)
# 2