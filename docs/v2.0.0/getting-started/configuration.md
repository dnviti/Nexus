# Configuration Guide

Configure your Nexus application for different environments and use cases.

## 🎯 Configuration Overview

Nexus uses a hierarchical configuration system that loads settings from multiple sources:

```mermaid
graph LR
    A[Default Values] --> B[Config Files]
    B --> C[Environment Variables]
    C --> D[CLI Arguments]
    D --> E[Final Config]
    
    subgraph "Priority (Low to High)"
        F[defaults.yaml]
        G[nexus_config.yaml]
        H[ENV vars]
        I[--flags]
    end
```

## 📋 Prerequisites

- [First Plugin completed](first-plugin.md)
- Working Nexus application with plugins
- Basic understanding of YAML format

## 🔧 Configuration Structure

### Basic Configuration File

Create `nexus_config.yaml`:

```yaml
# Application settings
app:
  name: "My Nexus App"
  description: "A powerful modular application"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 1

# Authentication settings
auth:
  secret_key: "your-secret-key-change-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7
  create_default_admin: true
  default_admin_email: "admin@nexus.local"
  default_admin_password: "admin"

# Database configuration
database:
  url: "sqlite:///./nexus.db"
  # url: "postgresql://user:password@localhost/nexus"
  # url: "mysql://user:password@localhost/nexus"
  pool_size: 5
  max_overflow: 10
  echo: false

# Security settings
security:
  cors_enabled: true
  cors_origins: ["*"]
  trusted_hosts: []
  rate_limiting_enabled: true
  rate_limit_requests: 100
  rate_limit_period: 60
  api_key_header: "X-API-Key"

# Performance settings
performance:
  compression_enabled: true
  cache_enabled: true
  cache_ttl: 300
  connection_pool_size: 100
  request_timeout: 30

# Monitoring settings
monitoring:
  metrics_enabled: true
  health_check_interval: 30
  log_requests: true
  log_responses: false
  tracing_enabled: false

# Logging configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "nexus.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5
  access_log: true

# Plugin settings
plugins_dir: "plugins"
data_dir: "data"
```

## 🌍 Environment-Specific Configurations

### Development Environment

Create `config/development.yaml`:

```yaml
app:
  debug: true
  workers: 1

database:
  url: "sqlite:///./dev_nexus.db"
  echo: true

logging:
  level: "DEBUG"
  log_requests: true
  log_responses: true

security:
  cors_origins: ["http://localhost:3000", "http://127.0.0.1:3000"]

monitoring:
  tracing_enabled: true
```

### Production Environment

Create `config/production.yaml`:

```yaml
app:
  debug: false
  workers: 4

database:
  url: "${DATABASE_URL}"
  pool_size: 20
  max_overflow: 30

auth:
  secret_key: "${NEXUS_SECRET_KEY}"

security:
  cors_origins: ["https://yourdomain.com"]
  trusted_hosts: ["yourdomain.com"]
  rate_limit_requests: 1000

logging:
  level: "INFO"
  file: "/var/log/nexus/nexus.log"
  log_requests: false

monitoring:
  metrics_enabled: true
  tracing_enabled: false
```

### Testing Environment

Create `config/testing.yaml`:

```yaml
app:
  debug: true

database:
  url: "sqlite:///:memory:"

auth:
  secret_key: "test-secret-key"
  create_default_admin: false

logging:
  level: "WARNING"
  file: null

monitoring:
  metrics_enabled: false
```

## 🔐 Environment Variables

### Required Variables

```bash
# Production secrets (required)
export NEXUS_SECRET_KEY="your-super-secret-key-256-bits-long"
export DATABASE_URL="postgresql://user:pass@localhost/nexus"

# Optional overrides
export NEXUS_DEBUG="false"
export NEXUS_LOG_LEVEL="INFO"
export NEXUS_HOST="0.0.0.0"
export NEXUS_PORT="8000"
```

### Environment Variable Mapping

```yaml
# In config file, use ${VAR_NAME} syntax
auth:
  secret_key: "${NEXUS_SECRET_KEY}"
  
database:
  url: "${DATABASE_URL}"
  
app:
  host: "${NEXUS_HOST:0.0.0.0}"  # Default value after colon
  port: "${NEXUS_PORT:8000}"
  debug: "${NEXUS_DEBUG:false}"
```

## 🎛️ Loading Configuration

### Method 1: File-based Loading

```python
from nexus import create_nexus_app, load_config

# Load specific config file
config = load_config("config/production.yaml")

app = create_nexus_app(config=config)
```

### Method 2: Environment-based Loading

```python
import os
from nexus import create_nexus_app, load_config

# Load config based on environment
env = os.getenv("NEXUS_ENV", "development")
config_file = f"config/{env}.yaml"

config = load_config(config_file)
app = create_nexus_app(config=config)
```

### Method 3: Programmatic Configuration

```python
from nexus import create_nexus_app, AppConfig

# Create config programmatically
config = AppConfig()
config.app.name = "My App"
config.app.debug = True
config.database.url = "sqlite:///./app.db"

app = create_nexus_app(config=config)
```

## 🔧 Plugin Configuration

### Plugin-Specific Settings

Add plugin configurations to your main config:

```yaml
# Plugin configurations
plugins:
  user_manager:
    max_users: 1000
    enable_registration: true
    require_email_verification: false
    
  file_upload:
    max_file_size: 10485760  # 10MB
    allowed_extensions: [".jpg", ".png", ".pdf"]
    storage_path: "./uploads"
    
  email_service:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "${EMAIL_USERNAME}"
    smtp_password: "${EMAIL_PASSWORD}"
```

### Plugin Configuration Schema

Define configuration schema in plugin manifest:

```json
{
  "name": "user_manager",
  "configuration_schema": {
    "max_users": {
      "type": "integer",
      "default": 1000,
      "minimum": 1,
      "description": "Maximum number of users allowed"
    },
    "enable_registration": {
      "type": "boolean",
      "default": true,
      "description": "Allow new user registration"
    },
    "admin_emails": {
      "type": "array",
      "items": {"type": "string", "format": "email"},
      "default": [],
      "description": "List of admin email addresses"
    }
  }
}
```

### Accessing Plugin Configuration

```python
class UserManagerPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        # Access plugin-specific config
        self.max_users = self.config.get('max_users', 1000)
        self.enable_registration = self.config.get('enable_registration', True)
    
    async def initialize(self):
        # Validate configuration
        if self.max_users < 1:
            raise ValueError("max_users must be at least 1")
        
        self.logger.info(f"User manager configured for max {self.max_users} users")
        return True
```

## 🗂️ Configuration Validation

### CLI Validation

```bash
# Validate configuration file
nexus validate config/production.yaml

# Check specific section
nexus validate --section database

# Validate all environment configs
nexus validate config/*.yaml
```

### Programmatic Validation

```python
from nexus import validate_config, ConfigValidationError

try:
    config = validate_config("nexus_config.yaml")
    print("✓ Configuration is valid")
except ConfigValidationError as e:
    print(f"✗ Configuration error: {e}")
```

### Custom Validation

```python
from nexus import BasePlugin, ConfigValidationError

class MyPlugin(BasePlugin):
    def validate_config(self, config):
        """Custom configuration validation"""
        if config.get('api_key') is None:
            raise ConfigValidationError("api_key is required")
        
        if config.get('timeout', 0) < 1:
            raise ConfigValidationError("timeout must be positive")
        
        return True
```

## 🔄 Runtime Configuration

### Dynamic Updates

```python
from nexus import get_config, update_config

# Get current configuration
current_config = get_config()

# Update configuration at runtime
update_config({
    "logging.level": "DEBUG",
    "monitoring.metrics_enabled": True
})
```

### Configuration Reloading

```python
class ConfigurablePlugin(BasePlugin):
    async def on_config_change(self, changes):
        """Handle configuration changes"""
        if 'max_connections' in changes:
            await self.update_connection_pool(changes['max_connections'])
        
        if 'log_level' in changes:
            self.logger.setLevel(changes['log_level'])
```

## 🏗️ Configuration Patterns

### Database Configuration

```yaml
# SQLite (development)
database:
  url: "sqlite:///./nexus.db"

# PostgreSQL (production)
database:
  url: "postgresql://user:pass@localhost:5432/nexus"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600

# MySQL
database:
  url: "mysql://user:pass@localhost:3306/nexus"
  charset: "utf8mb4"
```

### Caching Configuration

```yaml
cache:
  backend: "redis"  # redis, memory, memcached
  url: "redis://localhost:6379/0"
  default_ttl: 300
  key_prefix: "nexus:"
  
  # Memory cache settings
  memory:
    max_size: 1000
    
  # Redis settings
  redis:
    max_connections: 20
    retry_on_timeout: true
```

### Logging Configuration

```yaml
logging:
  version: 1
  formatters:
    standard:
      format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    json:
      format: '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
  
  handlers:
    console:
      class: "logging.StreamHandler"
      level: "INFO"
      formatter: "standard"
    
    file:
      class: "logging.handlers.RotatingFileHandler"
      level: "DEBUG"
      formatter: "json"
      filename: "nexus.log"
      maxBytes: 10485760
      backupCount: 5
  
  loggers:
    nexus:
      level: "DEBUG"
      handlers: ["console", "file"]
    
    uvicorn:
      level: "INFO"
      handlers: ["console"]
```

## 🔧 Advanced Configuration

### Configuration Inheritance

```yaml
# base.yaml
defaults: &defaults
  app:
    host: "0.0.0.0"
    port: 8000
  
  logging:
    level: "INFO"

# development.yaml
<<: *defaults
app:
  debug: true
  port: 8001

logging:
  level: "DEBUG"
```

### Conditional Configuration

```yaml
app:
  name: "My App"
  debug: ${NEXUS_DEBUG:false}
  
# Use different database based on environment
database:
  url: >-
    ${NEXUS_ENV:development} == "production" 
    ? "${DATABASE_URL}" 
    : "sqlite:///./dev.db"
```

### Configuration Templates

```yaml
# templates/base.yaml
app:
  name: "${APP_NAME:Nexus App}"
  version: "${APP_VERSION:1.0.0}"

database:
  url: "${DATABASE_URL:sqlite:///./nexus.db}"

auth:
  secret_key: "${SECRET_KEY:change-me-in-production}"
```

## 🎯 Configuration Best Practices

### Security

1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive data
3. **Validate all inputs** before using
4. **Use strong default values** where possible

### Organization

1. **Group related settings** into sections
2. **Use descriptive names** for configuration keys
3. **Document complex settings** with comments
4. **Keep environment configs minimal** (only differences)

### Performance

1. **Load configuration once** at startup
2. **Cache frequently accessed values**
3. **Use lazy loading** for expensive operations
4. **Validate early** to fail fast

## ✅ Configuration Checklist

- [ ] Created environment-specific config files
- [ ] Set up environment variables for secrets
- [ ] Configured database connection
- [ ] Set up logging and monitoring
- [ ] Validated configuration files
- [ ] Tested configuration loading
- [ ] Documented custom settings

## 🚀 Next Steps

Now that your application is properly configured:

1. **[Plugin Development](../plugins/basics.md)** - Build advanced plugins
2. **[Database Integration](../plugins/database.md)** - Persistent data storage
3. **[API Reference](../api/core.md)** - Complete framework reference
4. **[Deployment](../deployment/docker.md)** - Deploy to production

---

**🎉 Configuration complete!** Your Nexus application is now ready for advanced development and deployment.