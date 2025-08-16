# Nexus Framework Examples

Welcome to the Nexus Framework examples! These examples demonstrate how to build powerful, modular applications using the Nexus Framework pip package.

## 📦 Installation

Before running these examples, install the Nexus Framework:

```bash
pip install nexus-framework
```

Verify the installation:

```bash
nexus --version
nexus-admin --version
```

## 🚀 Quick Start Example

### 1. Simple Application

Create a basic Nexus application:

```python
from nexus import create_nexus_app

# Create application
app = create_nexus_app(
    title="My First Nexus App",
    description="Built with Nexus Framework",
    version="1.0.0"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. Using CLI to Generate Project

```bash
# Create new project
mkdir my-nexus-app
cd my-nexus-app
nexus init

# Start the application
python main.py
```

## 📂 Available Examples

### 1. Complete Application (`complete_app.py`)

A comprehensive example demonstrating:

- ✅ Task management system
- ✅ User authentication with JWT
- ✅ Real-time notifications
- ✅ Analytics dashboard
- ✅ File storage capabilities
- ✅ Email notifications
- ✅ WebSocket support
- ✅ Background job processing

**Run the example:**

```bash
python complete_app.py
```

**Features:**
- Full REST API with OpenAPI documentation
- User registration and authentication
- Task CRUD operations with status tracking
- Real-time updates via WebSocket
- Email notifications for task updates
- File upload and management
- Analytics and reporting
- Admin dashboard

**API Endpoints:**
- `GET /docs` - Interactive API documentation
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `GET /tasks` - List tasks
- `POST /tasks` - Create new task
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task
- `POST /files/upload` - Upload files
- `GET /analytics/dashboard` - Analytics data

### 2. Plugin Development Examples

#### Basic Plugin Structure

```python
from nexus import BasePlugin
from fastapi import APIRouter

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        self.version = "1.0.0"
        self.description = "Example plugin"

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

        @router.post("/action")
        async def perform_action(data: dict):
            # Plugin-specific logic here
            return {"result": "success", "data": data}

        return [router]

    async def shutdown(self):
        """Cleanup resources"""
        self.logger.info("Plugin shutting down")

def create_plugin():
    return MyPlugin()
```

#### Advanced Plugin with Database

```python
from nexus import BasePlugin
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from fastapi import APIRouter, Depends
from datetime import datetime

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabasePlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "database_plugin"
        self.version = "1.0.0"

    async def initialize(self) -> bool:
        # Create database tables
        from nexus.database import get_engine
        Base.metadata.create_all(bind=get_engine())
        return True

    def get_api_routes(self):
        router = APIRouter(prefix="/items", tags=["items"])

        @router.get("/")
        async def get_items(db=Depends(get_db_session)):
            return db.query(Item).all()

        @router.post("/")
        async def create_item(item_data: dict, db=Depends(get_db_session)):
            item = Item(**item_data)
            db.add(item)
            db.commit()
            return item

        return [router]
```

## 🎯 Getting Started with Examples

### 1. Basic Setup

```bash
# Create a new directory for your project
mkdir nexus-examples
cd nexus-examples

# Install Nexus Framework
pip install nexus-framework

# Initialize a new project
nexus init

# Your project structure:
# ├── main.py                 # Application entry point
# ├── nexus_config.yaml       # Configuration
# ├── plugins/                # Plugin directory
# ├── config/                 # Additional configs
# ├── logs/                   # Application logs
# ├── static/                 # Static files
# └── templates/              # Templates
```

### 2. Create Your First Plugin

```bash
# Generate a new plugin
nexus plugin create hello_world

# Edit the generated plugin
# plugins/hello_world/plugin.py
```

### 3. Run Your Application

```bash
# Start the development server
python main.py

# Or use the CLI
nexus run --reload

# Or with custom host/port
nexus run --host 0.0.0.0 --port 8080
```

### 4. Access Your Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Your Plugin**: http://localhost:8000/hello-world/

## 🔧 Configuration Examples

### Basic Configuration (`nexus_config.yaml`)

```yaml
app:
  name: "My Nexus Application"
  debug: true
  host: "0.0.0.0"
  port: 8000

auth:
  secret_key: "your-secret-key-change-in-production"
  access_token_expire_minutes: 30

database:
  url: "sqlite:///./app.db"
  # For PostgreSQL: "postgresql://user:pass@localhost/dbname"
  # For MySQL: "mysql://user:pass@localhost/dbname"

plugins:
  auto_load: true
  directories: ["plugins"]

security:
  cors_enabled: true
  cors_origins: ["*"]
  rate_limiting_enabled: true
  rate_limit_requests: 100
  rate_limit_period: 60

monitoring:
  metrics_enabled: true
  health_check_interval: 30
```

### Production Configuration

```yaml
app:
  name: "Production Nexus App"
  debug: false
  workers: 4

auth:
  secret_key: "${SECRET_KEY}"
  access_token_expire_minutes: 15

database:
  url: "${DATABASE_URL}"
  pool_size: 20
  max_overflow: 30

security:
  cors_origins: ["https://yourdomain.com"]
  trusted_hosts: ["yourdomain.com"]

logging:
  level: "INFO"
  file: "/var/log/nexus/app.log"
```

## 🧪 Testing Examples

### Plugin Testing

```python
import pytest
from nexus.testing import PluginTestCase
from my_plugin import MyPlugin

class TestMyPlugin(PluginTestCase):
    plugin_class = MyPlugin

    async def test_initialization(self):
        """Test plugin initializes correctly"""
        assert await self.plugin.initialize() is True
        assert self.plugin.name == "my_plugin"

    async def test_api_endpoint(self):
        """Test plugin API endpoint"""
        response = await self.client.get("/my-plugin/")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin"] == "my_plugin"

    async def test_action_endpoint(self):
        """Test plugin action endpoint"""
        test_data = {"key": "value"}
        response = await self.client.post("/my-plugin/action", json=test_data)
        assert response.status_code == 200
        result = response.json()
        assert result["result"] == "success"
```

### Application Testing

```python
import pytest
from nexus import create_nexus_app
from httpx import AsyncClient

@pytest.fixture
async def app():
    return create_nexus_app(title="Test App")

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

## 🚀 Deployment Examples

### Using Uvicorn

```bash
# Basic deployment
uvicorn main:app --host 0.0.0.0 --port 8000

# Production with multiple workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL
uvicorn main:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nexus
      - SECRET_KEY=your-secret-key
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=nexus
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 🛠️ CLI Examples

### Project Management

```bash
# Create new project
nexus init

# Create with custom template
nexus init --template advanced

# Validate configuration
nexus validate

# Check application status
nexus status

# Run health checks
nexus health --format json
```

### Plugin Management

```bash
# List available plugins
nexus plugin list

# Create new plugin
nexus plugin create user_management

# Show plugin information
nexus plugin info user_management

# Test plugin
nexus plugin test user_management
```

### User Management

```bash
# Create admin user
nexus-admin user create admin --email admin@example.com --admin

# List all users
nexus-admin user list

# Delete user
nexus-admin user delete testuser
```

### System Administration

```bash
# System information
nexus-admin system info --format json

# View logs
nexus-admin system logs --lines 100 --follow

# Create backup
nexus-admin backup create --output backup.tar.gz

# Restore from backup
nexus-admin backup restore backup.tar.gz

# Run maintenance
nexus-admin maintenance --dry-run
```

## 📚 Learning Resources

### Documentation Links

- **Official Documentation**: https://docs.nexus-framework.dev
- **API Reference**: https://docs.nexus-framework.dev/api/
- **Plugin Development Guide**: https://docs.nexus-framework.dev/plugins/
- **Configuration Reference**: https://docs.nexus-framework.dev/configuration/

### Community

- **GitHub Repository**: https://github.com/nexus-framework/nexus
- **Issue Tracker**: https://github.com/nexus-framework/nexus/issues
- **Discord Community**: https://discord.gg/nexus-framework
- **Stack Overflow**: Tag questions with `nexus-framework`

### Additional Examples

Check out more documentation and guides:
- **[Installation Guide](../docs/INSTALLATION.md)** - Complete installation instructions
- **[Tutorial](../docs/TUTORIAL.md)** - Step-by-step learning guide
- **[Architecture Guide](../docs/ARCHITECTURE.md)** - Framework design principles
- **[Testing Guide](../docs/TESTING.md)** - Comprehensive testing documentation
- **[Deployment Guide](../docs/DEPLOYMENT.md)** - Production deployment strategies
- **[Best Practices](../docs/BEST_PRACTICES.md)** - Development guidelines

## 🤝 Contributing

Want to contribute more examples? Check our [Contributing Guide](../docs/CONTRIBUTING.md).

### Example Contribution

1. Fork the repository
2. Create your example in the `examples/` directory
3. Add documentation
4. Submit a pull request

## 📄 License

These examples are part of the Nexus Framework and are licensed under the MIT License.

---

**Happy coding with Nexus Framework!** 🚀

For questions or support, reach out to our community or check the documentation.