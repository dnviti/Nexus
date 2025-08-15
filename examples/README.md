# Nexus Framework Examples

Welcome to the Nexus Framework examples! This directory contains comprehensive examples demonstrating the power and flexibility of the Nexus Framework for building modular, plugin-based applications.

## 📚 Available Examples

### 1. Complete Application (`complete_app.py`)
A full-featured application showcasing all major Nexus Framework capabilities:
- **Task Management System** - Complete CRUD operations for tasks
- **Advanced Authentication** - JWT, MFA, OAuth2, API keys
- **Real-time Notifications** - WebSocket-based push notifications
- **Analytics Dashboard** - Usage tracking and reporting
- **File Storage** - Upload, download, and manage files
- **Background Jobs** - Automated tasks and cleanup
- **API Documentation** - Auto-generated Swagger/ReDoc docs

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip package manager
- Git (for cloning the repository)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/nexus-framework/nexus.git
cd nexus
```

2. **Create a virtual environment:**
```bash
python -m venv venv

# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the Complete Example

1. **Navigate to the examples directory:**
```bash
cd examples
```

2. **Run the application:**
```bash
python complete_app.py
```

3. **Access the application:**
- **Home Page**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🎯 Example Features Walkthrough

### 1. User Registration and Authentication

**Register a new user:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

**Login and get access token:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=SecurePass123!"
```

**Use the token for authenticated requests:**
```bash
TOKEN="your-access-token-here"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me
```

### 2. Task Management

**Create a task:**
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete documentation",
    "description": "Write comprehensive docs for the project",
    "priority": "high",
    "category": "documentation",
    "due_date": "2024-12-31T23:59:59"
  }'
```

**Get all tasks:**
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tasks
```

**Update task status:**
```bash
curl -X PUT http://localhost:8000/api/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

### 3. Real-time Notifications (WebSocket)

**Connect to WebSocket using JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications/user123');

ws.onopen = () => {
    console.log('Connected to notifications');
};

ws.onmessage = (event) => {
    const notification = JSON.parse(event.data);
    console.log('Received:', notification);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

**Using Python WebSocket client:**
```python
import asyncio
import websockets
import json

async def listen_notifications():
    uri = "ws://localhost:8000/ws/notifications/user123"
    async with websockets.connect(uri) as websocket:
        print("Connected to notifications")
        while True:
            notification = await websocket.recv()
            print(f"Received: {json.loads(notification)}")

asyncio.run(listen_notifications())
```

### 4. File Upload and Management

**Upload a file:**
```bash
curl -X POST http://localhost:8000/api/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/file.pdf" \
  -F "category=documents"
```

**List files in a category:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/files/list/documents
```

**Download a file:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/files/documents/filename.pdf \
  -o downloaded_file.pdf
```

### 5. Analytics Dashboard

**Get analytics data:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/dashboard
```

**Track custom event:**
```bash
curl -X POST http://localhost:8000/api/analytics/track/event \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "button_clicked",
    "properties": {
      "button_id": "submit_form",
      "page": "home"
    }
  }'
```

## 🔌 Plugin System

### Available Plugins in the Example

1. **Task Manager Plugin** (`/app/plugins/task_manager/`)
   - Complete task CRUD operations
   - Task assignment and tracking
   - Priority and status management
   - Due date reminders
   - Statistics and reporting

2. **Advanced Authentication Plugin** (`/app/plugins/auth_advanced/`)
   - User registration and login
   - JWT token management
   - Multi-factor authentication (MFA)
   - OAuth2 integration
   - API key management
   - Session management

3. **Notification Plugin** (in `complete_app.py`)
   - Real-time WebSocket notifications
   - Event-driven messaging
   - User-to-user messaging
   - Broadcast capabilities

4. **Analytics Plugin** (in `complete_app.py`)
   - Usage tracking
   - Custom event tracking
   - Periodic reporting
   - Dashboard metrics

5. **File Storage Plugin** (in `complete_app.py`)
   - File upload/download
   - Category-based organization
   - File listing and management
   - Automatic cleanup of temp files

### Creating Your Own Plugin

1. **Create plugin directory:**
```bash
mkdir -p plugins/my_plugin
```

2. **Create plugin manifest (`plugins/my_plugin/manifest.json`):**
```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "author": "Your Name",
  "category": "custom",
  "dependencies": [],
  "permissions": ["read", "write"]
}
```

3. **Create plugin class (`plugins/my_plugin/plugin.py`):**
```python
from nexus.plugins import BasePlugin, PluginMetadata
from fastapi import APIRouter

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My custom plugin"
        )
    
    async def initialize(self, context) -> bool:
        # Plugin initialization logic
        return True
    
    def get_api_routes(self):
        router = APIRouter(prefix="/api/my_plugin")
        
        @router.get("/")
        async def get_info():
            return {"plugin": "my_plugin", "status": "active"}
        
        return [router]
```

## 📊 Testing the Examples

### Unit Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nexus --cov-report=html

# Run specific test file
pytest tests/test_complete_app.py
```

### Load Testing with Locust
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Access Locust UI at http://localhost:8089
```

### API Testing with HTTPie
```bash
# Install HTTPie
pip install httpie

# Test endpoints
http POST localhost:8000/api/auth/register \
  username=testuser email=test@example.com password=SecurePass123!

http POST localhost:8000/api/auth/login \
  username=testuser password=SecurePass123!

# Use token
http GET localhost:8000/api/tasks \
  "Authorization: Bearer $TOKEN"
```

## 🐳 Docker Deployment

### Build and run with Docker:
```bash
# Build image
docker build -t nexus-example .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/nexus.db \
  -e JWT_SECRET=your-secret-key \
  -v $(pwd)/data:/app/data \
  nexus-example
```

### Using Docker Compose:
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📁 Project Structure

```
examples/
├── complete_app.py          # Main example application
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── config/
│   └── example.yaml       # Configuration example
├── plugins/               # Example plugins
│   ├── task_manager/      # Task management plugin
│   ├── auth_advanced/     # Authentication plugin
│   └── ...               # Other plugins
├── static/               # Static files
├── templates/            # HTML templates
├── uploads/              # File uploads directory
└── logs/                 # Application logs
```

## 🔧 Configuration

The example uses configuration from multiple sources:

1. **Configuration file** (`config/example.yaml`)
2. **Environment variables** (`.env` file)
3. **Command-line arguments**
4. **Default values** in code

### Key Configuration Options

```yaml
# Basic settings
app:
  name: "Nexus Example"
  environment: "development"
  debug: true

# Database
database:
  type: "sqlite"  # or postgresql, mysql, mongodb
  connection:
    path: "./data/nexus.db"

# Authentication
auth:
  jwt_secret: "your-secret-key"
  token_expiry: 3600

# Plugins
plugins:
  directory: "./plugins"
  auto_load: true
  hot_reload: true
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill the process or use a different port
   python complete_app.py --port 8001
   ```

2. **Database connection error:**
   - Check database credentials in `.env`
   - Ensure database service is running
   - Verify connection string format

3. **Plugin not loading:**
   - Check plugin manifest file
   - Verify dependencies are installed
   - Review logs for error messages

4. **WebSocket connection failed:**
   - Ensure WebSocket support in reverse proxy
   - Check firewall settings
   - Verify correct WebSocket URL

## 📚 Learn More

- **[Main Documentation](../docs/README.md)** - Complete framework documentation
- **[API Reference](../docs/API_REFERENCE.md)** - Detailed API documentation
- **[Plugin Development](../docs/PLUGIN_DEVELOPMENT.md)** - Create custom plugins
- **[Deployment Guide](../docs/DEPLOYMENT.md)** - Production deployment
- **[Best Practices](../docs/BEST_PRACTICES.md)** - Development guidelines

## 🤝 Contributing

We welcome contributions to the examples! Please:

1. Fork the repository
2. Create a feature branch
3. Add your example with documentation
4. Submit a pull request

See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for detailed guidelines.

## 📄 License

The Nexus Framework and examples are released under the MIT License.

## 🆘 Support

- **Discord**: [Join our community](https://discord.gg/nexus-framework)
- **GitHub Issues**: [Report bugs](https://github.com/nexus-framework/nexus/issues)
- **Forum**: [Ask questions](https://community.nexus-framework.dev)
- **Email**: support@nexus-framework.dev

---

Happy coding with Nexus Framework! 🚀