# Nexus Framework Documentation

[![PyPI version](https://badge.fury.io/py/nexus-framework.svg)](https://badge.fury.io/py/nexus-framework)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-nexus--framework.dev-blue.svg)](https://docs.nexus-framework.dev)

Welcome to the comprehensive documentation for **Nexus Framework** - The Ultimate Plugin-Based Application Platform.

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install nexus-framework

# Verify installation
nexus --version
nexus-admin --version
```

### Create Your First Application

```bash
# Create a new project
mkdir my-nexus-app
cd my-nexus-app
nexus init

# Start the application
python main.py
```

Your application will be running at:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Admin Interface**: Available via `nexus-admin` CLI

## 📚 Documentation Structure

### 🎯 Getting Started

| Document | Description |
|----------|-------------|
| **[Installation & Setup](INSTALLATION.md)** | Install Nexus Framework and set up your environment |
| **[Quick Start Tutorial](TUTORIAL.md)** | Build your first application step-by-step |
| **[Configuration Guide](CONFIGURATION.md)** | Configure your application and plugins |

### 🏗️ Development

| Document | Description |
|----------|-------------|
| **[Architecture Overview](ARCHITECTURE.md)** | Understand the framework architecture |
| **[Plugin Development Guide](PLUGIN_DEVELOPMENT.md)** | Create custom plugins |
| **[API Reference](API_REFERENCE.md)** | Complete API documentation |
| **[Testing Guide](TESTING.md)** | Write tests for your applications |
| **[Best Practices](BEST_PRACTICES.md)** | Follow development best practices |

### 🚀 Deployment & Operations

| Document | Description |
|----------|-------------|
| **[Deployment Guide](DEPLOYMENT.md)** | Deploy applications to production |
| **[Community Guidelines](COMMUNITY.md)** | Community resources and guidelines |
| **[Contributing Guide](CONTRIBUTING.md)** | Contribute to the framework |

### 🤖 AI & Automation

| Document | Description |
|----------|-------------|
| **[AI Agents Guide](AGENTS.md)** | Use AI to accelerate development |

### 📦 Package Information

| Document | Description |
|----------|-------------|
| **[Package Distribution Guide](PACKAGE_DISTRIBUTION.md)** | Build and distribute the framework |
| **[Package Status Report](PACKAGE_STATUS.md)** | Current package status and validation |
| **[Documentation Updates](DOCUMENTATION_UPDATES.md)** | Summary of documentation changes |

## 🎯 Installation & Setup

### System Requirements

- **Python**: 3.11 or higher
- **Operating System**: Linux, macOS, Windows
- **Memory**: 512MB minimum, 2GB recommended
- **Disk Space**: 100MB for framework, additional space for plugins

### Installation Methods

#### Method 1: PyPI Installation (Recommended)

```bash
# Install latest stable version
pip install nexus-framework

# Install specific version
pip install nexus-framework==2.0.0

# Install with development dependencies
pip install nexus-framework[dev]
```

#### Method 2: From Source

```bash
# Clone repository
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# Install in development mode
pip install -e .
```

#### Method 3: Docker

```bash
# Pull official image
docker pull nexusframework/nexus:latest

# Run container
docker run -p 8000:8000 nexusframework/nexus:latest
```

### Verification

```bash
# Check installation
nexus --version
nexus-admin --version

# Test import
python -c "import nexus; print(f'Nexus {nexus.__version__} installed successfully!')"

# Run health check
nexus health
```

## 🔧 CLI Tools

### Main CLI (`nexus`)

The primary command-line interface for development and application management:

```bash
# Project management
nexus init                              # Initialize new project
nexus run --host 0.0.0.0 --port 8000  # Run application server
nexus status                           # Show application status
nexus health                           # Run health checks
nexus validate                         # Validate configuration

# Plugin management
nexus plugin create <name>             # Create new plugin
nexus plugin list                      # List available plugins
nexus plugin info <name>               # Show plugin information
```

### Admin CLI (`nexus-admin`)

Administrative tools for system management:

```bash
# User management
nexus-admin user create <username>     # Create new user
nexus-admin user list                  # List all users
nexus-admin user delete <username>     # Delete user

# System administration
nexus-admin system info                # Show system information
nexus-admin system health              # Comprehensive health check
nexus-admin system logs                # View system logs

# Plugin administration
nexus-admin plugin status              # Show plugin status
nexus-admin plugin enable <name>       # Enable plugin
nexus-admin plugin disable <name>      # Disable plugin

# Backup and maintenance
nexus-admin backup create              # Create system backup
nexus-admin backup restore <file>      # Restore from backup
nexus-admin maintenance                 # Run maintenance tasks
```

## 📖 Framework Overview

### Core Features

- **🔌 Plugin Architecture**: Everything is a plugin for maximum modularity
- **🚀 FastAPI Integration**: Modern async web framework with auto-documentation
- **🔐 Built-in Authentication**: JWT-based auth with role-based access control
- **📊 Database Support**: SQLAlchemy integration with multiple databases
- **⚡ High Performance**: Async/await throughout with optimized request handling
- **📈 Monitoring**: Health checks, metrics collection, and observability
- **🛠️ CLI Tools**: Comprehensive command-line interface

### Architecture Components

```
Nexus Framework Architecture
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Plugin Manager  │  Event Bus   │  Service Registry        │
├─────────────────────────────────────────────────────────────┤
│     Authentication    │    API Gateway    │   Middleware    │
├─────────────────────────────────────────────────────────────┤
│  Database Adapter  │   Monitoring   │   Configuration      │
├─────────────────────────────────────────────────────────────┤
│                      FastAPI Core                          │
└─────────────────────────────────────────────────────────────┘
```

### Plugin Lifecycle

1. **Discovery**: Plugins are discovered in configured directories
2. **Loading**: Plugin manifest is read and validated
3. **Initialization**: Plugin `initialize()` method is called
4. **Registration**: Routes, services, and event handlers are registered
5. **Runtime**: Plugin handles requests and events
6. **Shutdown**: Plugin `shutdown()` method is called during cleanup

## 💡 Basic Usage Examples

### Simple Application

```python
from nexus import create_nexus_app

# Create application
app = create_nexus_app(
    title="My API",
    description="Built with Nexus Framework",
    version="1.0.0"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Basic Plugin

```python
from nexus import BasePlugin
from fastapi import APIRouter

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        self.version = "1.0.0"
    
    async def initialize(self) -> bool:
        self.logger.info("Plugin initialized!")
        return True
    
    def get_api_routes(self):
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
        self.logger.info("Plugin shutting down")

def create_plugin():
    return MyPlugin()
```

### Configuration

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
  url: "sqlite:///./app.db"
  # PostgreSQL: "postgresql://user:pass@localhost/dbname"
  # MySQL: "mysql://user:pass@localhost/dbname"

plugins:
  auto_load: true
  directories: ["plugins"]

monitoring:
  metrics_enabled: true
  health_check_interval: 30
```

## 🧪 Testing

### Plugin Testing

```python
import pytest
from nexus.testing import PluginTestCase

class TestMyPlugin(PluginTestCase):
    plugin_class = MyPlugin
    
    async def test_initialization(self):
        assert await self.plugin.initialize() is True
        assert self.plugin.name == "my_plugin"
    
    async def test_api_endpoint(self):
        response = await self.client.get("/my-plugin/")
        assert response.status_code == 200
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nexus

# Run specific test file
pytest tests/test_my_plugin.py
```

## 🚀 Deployment

### Production Deployment

```bash
# Using Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Using Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Using Docker
docker run -p 8000:8000 -v $(pwd):/app nexusframework/nexus
```

### Environment Variables

```bash
# Application settings
export NEXUS_HOST=0.0.0.0
export NEXUS_PORT=8000
export NEXUS_DEBUG=false

# Database
export DATABASE_URL=postgresql://user:pass@localhost/nexus

# Authentication
export SECRET_KEY=your-super-secret-key-here

# Plugins
export PLUGINS_AUTO_LOAD=true
export PLUGINS_DIRECTORIES=plugins,extensions
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed health report
curl http://localhost:8000/health/detailed

# CLI health check
nexus health --format json
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Application metrics
nexus-admin system info
```

### Logging

```bash
# View logs
nexus-admin system logs --lines 100

# Follow logs
nexus-admin system logs --follow

# Filter by level
nexus-admin system logs --level ERROR
```

## 🔒 Security

### Authentication

- **JWT Token Authentication**
- **Role-Based Access Control (RBAC)**
- **API Key Authentication**
- **OAuth2 Integration Ready**

### Security Best Practices

1. **Use strong secret keys**
2. **Enable HTTPS in production**
3. **Configure CORS properly**
4. **Enable rate limiting**
5. **Validate all inputs**
6. **Keep dependencies updated**

## 🤝 Community & Support

### Getting Help

- **Documentation**: https://docs.nexus-framework.dev
- **GitHub Issues**: https://github.com/nexus-framework/nexus/issues
- **Discord Community**: https://discord.gg/nexus-framework
- **Stack Overflow**: Tag questions with `nexus-framework`

### Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details on:

- Reporting bugs
- Suggesting features
- Contributing code
- Writing documentation
- Creating plugins

### Community Guidelines

Please read our [Community Guidelines](COMMUNITY.md) for information about:

- Code of conduct
- Communication standards
- Support channels
- Community resources

## 📚 Additional Resources

### Official Links

- **PyPI Package**: https://pypi.org/project/nexus-framework/
- **GitHub Repository**: https://github.com/nexus-framework/nexus
- **Documentation Site**: https://docs.nexus-framework.dev
- **Release Notes**: https://github.com/nexus-framework/nexus/releases

### Learning Materials

- **Tutorial Videos**: https://youtube.com/nexus-framework
- **Blog Posts**: https://blog.nexus-framework.dev
- **Example Projects**: https://github.com/nexus-framework/examples
- **Plugin Collection**: https://github.com/nexus-framework/plugins

### Tools & Extensions

- **IDE Extensions**: Available for VS Code, PyCharm
- **CI/CD Templates**: GitHub Actions, GitLab CI
- **Docker Images**: Official Docker images
- **Helm Charts**: Kubernetes deployment charts

## 📊 Package Information

### Current Version

- **Version**: 2.0.0
- **Release Date**: December 21, 2024
- **Python Support**: 3.11+
- **License**: MIT

### Installation Statistics

- **Downloads**: Updated daily on PyPI
- **GitHub Stars**: Check our repository
- **Community Size**: Growing daily

### Dependencies

Core dependencies automatically installed:

- `fastapi ^0.109.0` - Web framework
- `uvicorn[standard] ^0.27.0` - ASGI server
- `pydantic ^2.5.3` - Data validation
- `sqlalchemy ^2.0.25` - Database ORM
- `python-jose[cryptography] ^3.3.0` - JWT handling
- `click ^8.1.7` - CLI framework
- `psutil ^5.9.0` - System monitoring

## 🎯 What's Next?

### For New Users

1. **[Install the Framework](INSTALLATION.md)** - Complete installation guide
2. **[Follow the Tutorial](TUTORIAL.md)** - Build your first application
3. **[Read the Architecture Guide](ARCHITECTURE.md)** - Understand the framework
4. **[Create Your First Plugin](PLUGIN_DEVELOPMENT.md)** - Extend functionality
5. **[Join the Community](COMMUNITY.md)** - Connect with other developers

### For Experienced Users

1. **[Explore Advanced Features](BEST_PRACTICES.md)** - Optimize your applications
2. **[Deploy to Production](DEPLOYMENT.md)** - Production deployment guide
3. **[Contribute to the Project](CONTRIBUTING.md)** - Help improve the framework
4. **[Build Plugin Collections](PLUGIN_DEVELOPMENT.md)** - Share your plugins

### For Maintainers

1. **[Package Distribution Guide](PACKAGE_DISTRIBUTION.md)** - Build and distribute packages
2. **[Package Status Report](PACKAGE_STATUS.md)** - Current status and validation
3. **[Documentation Updates](DOCUMENTATION_UPDATES.md)** - Track documentation changes

## 📝 License

Nexus Framework is released under the MIT License. See [LICENSE](../LICENSE) for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [SQLAlchemy](https://www.sqlalchemy.org/)
- CLI built with [Click](https://click.palletsprojects.com/)
- Documentation generated with [MkDocs](https://www.mkdocs.org/)

---

**Made with ❤️ by the Nexus Framework Team**

*Ready to build something amazing? Start with `pip install nexus-framework` and check out our [Installation Guide](INSTALLATION.md)* 🚀