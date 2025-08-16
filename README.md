# Nexus

[![PyPI version](https://badge.fury.io/py/nexus-framework.svg)](https://badge.fury.io/py/nexus-framework)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**The Ultimate Plugin-Based Application Platform** - Build modular, scalable applications with ease.

Nexus is a next-generation application development platform that revolutionizes how we build software by making **everything a plugin**. Instead of monolithic applications, Nexus enables you to create applications as a collection of focused, reusable plugins that work together seamlessly.

## ✨ Key Features

- **🔌 Pure Plugin Architecture** - Every feature is a plugin, ensuring complete modularity
- **🔥 Hot-Reload Support** - Add, update, or remove plugins without restarting
- **🎯 FastAPI Integration** - Modern async web framework with automatic OpenAPI docs
- **🛡️ Built-in Authentication** - JWT-based auth with role-based access control
- **📊 Multi-Database Support** - SQLAlchemy integration with PostgreSQL, MySQL, SQLite
- **🌐 API-First Design** - Automatic REST API generation with Swagger UI
- **⚡ High Performance** - Async/await throughout with optimized request handling
- **🧪 Testing Framework** - Comprehensive testing utilities for plugins
- **📈 Monitoring & Metrics** - Health checks, metrics collection, and observability
- **🔧 CLI Tools** - Powerful command-line interface for development and deployment

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install nexus-framework

# Verify installation
nexus --version
```

### Create Your First Application

```bash
# Create a new project directory
mkdir my-nexus-app
cd my-nexus-app

# Initialize Nexus project
nexus init

# Start the application
python main.py
```

Your application will be running at `http://localhost:8000` with:
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Admin Interface**: Available via `nexus-admin` CLI

### Create Your First Plugin

```bash
# Generate a new plugin
nexus plugin create my_awesome_plugin

# Plugin structure created at:
# plugins/my_awesome_plugin/
# ├── __init__.py
# ├── plugin.py          # Main plugin code
# └── manifest.json       # Plugin metadata
```

## 📖 Usage Examples

### Basic Application

```python
from nexus import create_nexus_app

# Create application with default configuration
app = create_nexus_app(
    title="My API",
    description="Built with Nexus",
    version="1.0.0"
)

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Custom Plugin Development

```python
from nexus import BasePlugin
from fastapi import APIRouter

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        self.version = "1.0.0"
        self.description = "My awesome plugin"
    
    async def initialize(self) -> bool:
        """Initialize plugin resources"""
        self.logger.info("Plugin initialized!")
        return True
    
    def get_api_routes(self):
        """Define API routes"""
        router = APIRouter(prefix="/my-plugin", tags=["my-plugin"])
        
        @router.get("/")
        async def get_info():
            return {
                "plugin": self.name,
                "version": self.version,
                "status": "active"
            }
        
        return [router]
    
    async def shutdown(self):
        """Cleanup resources"""
        self.logger.info("Plugin shutting down")

# Plugin factory function
def create_plugin():
    return MyPlugin()
```

### Advanced Configuration

```yaml
# nexus_config.yaml
app:
  name: "My Nexus Application"
  debug: false
  host: "0.0.0.0"
  port: 8000

auth:
  secret_key: "your-secret-key-here"
  access_token_expire_minutes: 30

database:
  url: "postgresql://user:pass@localhost/mydb"
  # or: "sqlite:///./app.db"

plugins:
  auto_load: true
  directories: ["plugins", "extensions"]

monitoring:
  metrics_enabled: true
  health_check_interval: 30
```

## 🔧 CLI Tools

### Main CLI (`nexus`)

```bash
# Application management
nexus run --host 0.0.0.0 --port 8000    # Run application server
nexus init                                # Initialize new project
nexus status                             # Show application status
nexus health                             # Run health checks

# Plugin management
nexus plugin create <name>               # Create new plugin
nexus plugin list                        # List available plugins
nexus plugin info <name>                 # Show plugin information

# Configuration
nexus validate                           # Validate configuration
```

### Admin CLI (`nexus-admin`)

```bash
# User management
nexus-admin user create <username>       # Create new user
nexus-admin user list                    # List all users
nexus-admin user delete <username>       # Delete user

# System administration
nexus-admin system info                  # Show system information
nexus-admin system health                # Comprehensive health check
nexus-admin system logs                  # View system logs

# Plugin administration
nexus-admin plugin status                # Show plugin status
nexus-admin plugin enable <name>         # Enable plugin
nexus-admin plugin disable <name>        # Disable plugin

# Backup and maintenance
nexus-admin backup create                # Create system backup
nexus-admin backup restore <file>        # Restore from backup
nexus-admin maintenance                   # Run maintenance tasks
```

## 📁 Project Structure

When you run `nexus init`, you get a complete project structure:

```
my-nexus-app/
├── main.py                    # Application entry point
├── nexus_config.yaml          # Configuration file
├── nexus/                     # Nexus framework core
│   ├── __init__.py
│   ├── core.py               # Core framework components
│   ├── api.py                # API utilities
│   ├── auth.py               # Authentication system
│   ├── cli.py                # Command-line interface
│   ├── admin.py              # Admin utilities
│   ├── config.py             # Configuration management
│   ├── middleware.py         # Middleware components
│   ├── monitoring.py         # Health checks and metrics
│   ├── plugins.py            # Plugin management
│   └── utils.py              # Utility functions
├── plugins/                   # Plugin directory
│   └── example/              # Example plugins
│       └── hello_world/
│           ├── __init__.py
│           └── plugin.py
├── plugin_template/           # Plugin development template
│   ├── README.md
│   ├── manifest.json
│   ├── plugin.py
│   └── pyproject.toml
├── config/                    # Additional configuration files
│   └── example.yaml
├── logs/                      # Application logs
├── static/                    # Static assets
└── templates/                 # Template files
```

## 🏗️ Architecture

### Core Components

- **Plugin Manager**: Handles plugin lifecycle, loading, and dependency management
- **Service Registry**: Dependency injection container for services
- **Event Bus**: Async event system for plugin communication
- **Database Adapter**: Multi-database support with SQLAlchemy
- **Authentication Manager**: JWT-based authentication and authorization
- **Monitoring System**: Health checks, metrics, and observability
- **API Gateway**: Request routing and middleware processing

### Plugin Lifecycle

1. **Discovery**: Plugins are discovered in configured directories
2. **Loading**: Plugin manifest is read and validated
3. **Initialization**: Plugin `initialize()` method is called
4. **Registration**: Routes, services, and event handlers are registered
5. **Runtime**: Plugin handles requests and events
6. **Shutdown**: Plugin `shutdown()` method is called during cleanup

## 🌟 Advanced Features

### Event-Driven Architecture

```python
# In your plugin
class MyPlugin(BasePlugin):
    async def initialize(self):
        # Subscribe to events
        self.event_bus.subscribe("user.created", self.on_user_created)
        
        # Emit events
        await self.event_bus.emit("plugin.initialized", {
            "plugin": self.name,
            "timestamp": datetime.utcnow()
        })
    
    async def on_user_created(self, event_data):
        """Handle user creation event"""
        user_id = event_data.get("user_id")
        self.logger.info(f"New user created: {user_id}")
```

### Service Registry

```python
# Register a service
self.service_registry.register("email_service", EmailService())

# Use a service in another plugin
email_service = self.service_registry.get("email_service")
await email_service.send_email(to="user@example.com", subject="Welcome!")
```

### Database Integration

```python
from nexus.database import get_session
from sqlalchemy.orm import Session

class UserPlugin(BasePlugin):
    def get_api_routes(self):
        router = APIRouter()
        
        @router.get("/users")
        async def get_users(db: Session = Depends(get_session)):
            return db.query(User).all()
        
        return [router]
```

## 🧪 Testing

### Plugin Testing

```python
import pytest
from nexus.testing import PluginTestCase

class TestMyPlugin(PluginTestCase):
    plugin_class = MyPlugin
    
    async def test_plugin_initialization(self):
        """Test plugin initializes correctly"""
        assert await self.plugin.initialize() is True
        assert self.plugin.name == "my_plugin"
    
    async def test_api_endpoints(self):
        """Test plugin API endpoints"""
        response = await self.client.get("/my-plugin/")
        assert response.status_code == 200
        assert response.json()["plugin"] == "my_plugin"
```

### Application Testing

```bash
# Run tests with coverage
nexus test --coverage

# Run specific test file
nexus test tests/test_my_plugin.py

# Run with verbose output
nexus test --verbose
```

## 📊 Monitoring and Observability

### Built-in Health Checks

- **Database connectivity**
- **Memory usage**
- **Disk space**
- **Plugin status**
- **External service availability**

### Metrics Collection

```python
from nexus.monitoring import metrics

# Custom metrics in your plugin
@metrics.timer("api.request_duration")
async def my_endpoint():
    metrics.counter("api.requests").increment()
    return {"status": "success"}
```

### Health Check Endpoints

- `GET /health` - Basic health status
- `GET /health/detailed` - Comprehensive health report
- `GET /metrics` - Prometheus-compatible metrics

## 🔒 Security Features

### Authentication

- **JWT Token Authentication**
- **Role-Based Access Control (RBAC)**
- **API Key Authentication**
- **OAuth2 Integration Ready**

### Security Middleware

- **CORS Protection**
- **Rate Limiting**
- **Request Validation**
- **Security Headers**
- **SQL Injection Prevention**

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
poetry install

# Run tests
python -m pytest

# Start development server
python main.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/nexus-framework/
- **GitHub Repository**: https://github.com/nexus-framework/nexus
- **Issue Tracker**: https://github.com/nexus-framework/nexus/issues
- **Discord Community**: https://discord.gg/nexus-framework
- **Twitter**: [@nexus_framework](https://twitter.com/nexus_framework)

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [SQLAlchemy](https://www.sqlalchemy.org/)
- CLI built with [Click](https://click.palletsprojects.com/)
- Async support via [asyncio](https://docs.python.org/3/library/asyncio.html)

---

**Made with ❤️ by the Nexus Team**

*Start building your next great application with Nexus today!*