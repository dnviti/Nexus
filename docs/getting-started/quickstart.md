# Quick Start Guide

Build your first Nexus application in 5 minutes! This guide walks you through creating a basic application and your first plugin.

## 🚀 Prerequisites

- Python 3.11 or higher installed
- Nexus Platform installed: `pip install nexus-platform`
- Basic understanding of Python and web APIs

## 📝 Step 1: Initialize Your Project

Use the Nexus CLI to create a new project:

```bash
# Create a new directory for your project
mkdir my-nexus-app
cd my-nexus-app

# Initialize the Nexus project
nexus init
```

This creates the complete project structure:

- `nexus_config.yaml` - Configuration file
- `main.py` - Application entry point
- `plugins/` - Plugin directory
- `config/`, `logs/`, `static/`, `templates/` - Supporting directories

Alternatively, create manually with `main.py`:

```python
#!/usr/bin/env python3
"""
My First Nexus Application
A simple example demonstrating the Nexus Platform basics.
"""

from nexus import create_nexus_app
import uvicorn

# Create the Nexus application
app = create_nexus_app(
    title="My First Nexus App",
    version="1.0.0",
    description="Learning Nexus Platform with a simple example"
)

if __name__ == "__main__":
    print("🚀 Starting Nexus application...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("❤️  Health Check: http://localhost:8000/health")

    # Run the application
    uvicorn.run(
        app.app,  # Note: use app.app to get the FastAPI instance
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
```

## 🏃‍♂️ Step 2: Run Your Application

If you used `nexus init`, your application is ready to run:

```bash
# Run your application (from the project directory)
python main.py

# Or use the CLI
nexus run
```

Your application is now running! Open your browser and visit:

- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **System Info**: http://localhost:8000/info

## 🔍 Step 3: Explore the Default Endpoints

Your Nexus application comes with several built-in endpoints:

### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
    "status": "healthy",
    "timestamp": "2024-01-20T10:30:00Z",
    "version": "1.0.0",
    "components": {
        "database": { "status": "healthy" },
        "plugins": { "status": "healthy", "loaded": 0 }
    }
}
```

### System Information

```bash
curl http://localhost:8000/info
```

### Plugin List

```bash
curl http://localhost:8000/plugins
```

## 🔌 Step 4: Create Your First Plugin

Use the CLI to create a new plugin:

```bash
# Create a new plugin (run from your project directory)
nexus plugin create my_first_plugin

# This creates the plugin structure in plugins/custom/my_first_plugin/
```

## 📁 Step 5: Understand the Plugin Structure

Your plugin was created in `plugins/custom/my_first_plugin/` with these files:

```
my-nexus-app/
├── plugins/custom/my_first_plugin/
│   ├── __init__.py          # Plugin package initialization
│   ├── plugin.py            # Main plugin implementation
│   ├── manifest.json        # Plugin metadata
│   └── requirements.txt     # Plugin dependencies
├── main.py                  # Your application entry point
├── nexus_config.yaml        # Configuration file
└── logs/                    # Application logs
```

## 🛠️ Step 6: Customize Your Plugin

Edit `plugins/custom/my_first_plugin/plugin.py`:

```python
"""
My First Plugin - A simple example plugin
"""

from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel

from nexus.plugins import BasePlugin


class GreetingResponse(BaseModel):
    """Response model for greeting endpoint."""
    message: str
    timestamp: datetime
    plugin_version: str


class MyFirstPlugin(BasePlugin):
    """My first Nexus plugin - demonstrates basic functionality."""

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()

        # Plugin metadata
        self.name = "my_first_plugin"
        self.version = "1.0.0"
        self.description = "My first Nexus plugin"
        self.author = "Your Name"

        # Plugin state
        self.greeting_count = 0

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info(f"Initializing {self.name} plugin")

            # Load any saved state
            self.greeting_count = await self.get_config("greeting_count", 0)

            # Subscribe to events
            await self.subscribe_to_event("user.created", self._handle_user_created)

            self.initialized = True
            self.logger.info(f"{self.name} plugin initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            return False

    async def shutdown(self) -> None:
        """Clean up plugin resources."""
        # Save state
        await self.set_config("greeting_count", self.greeting_count)
        self.logger.info(f"{self.name} plugin shut down")

    def get_api_routes(self) -> List[APIRouter]:
        """Return API routes for this plugin."""
        router = APIRouter(tags=["My First Plugin"])

        @router.get("/greet/{name}", response_model=GreetingResponse)
        async def greet_user(name: str):
            """Greet a user by name."""
            self.greeting_count += 1

            # Publish an event
            await self.publish_event(
                "my_first_plugin.greeting",
                {"name": name, "count": self.greeting_count}
            )

            return GreetingResponse(
                message=f"Hello, {name}! This is greeting #{self.greeting_count}",
                timestamp=datetime.utcnow(),
                plugin_version=self.version
            )

        @router.get("/stats")
        async def get_stats():
            """Get plugin statistics."""
            return {
                "plugin": self.name,
                "version": self.version,
                "greeting_count": self.greeting_count,
                "initialized": self.initialized
            }

        return [router]

    async def _handle_user_created(self, event):
        """Handle user creation events."""
        username = event.data.get("username", "Unknown")
        self.logger.info(f"New user created: {username}")


def create_plugin():
    """Create and return the plugin instance."""
    return MyFirstPlugin()
```

## 🔄 Step 7: Restart and Test Your Plugin

1. **Stop your application** (Ctrl+C in terminal)
2. **Restart it**:
    ```bash
    python main.py
    ```
3. **Test your plugin**:

    ```bash
    # Test the greeting endpoint
    curl http://localhost:8000/greet/World

    # Check plugin stats
    curl http://localhost:8000/stats
    ```

## 📊 Step 8: View Your Plugin in Action

Visit the API documentation at http://localhost:8000/docs and you'll see:

- Your plugin's endpoints listed
- Interactive API testing interface
- Automatic request/response schema documentation

Try the endpoints:

- `GET /greet/{name}` - Greet someone
- `GET /stats` - View plugin statistics

## 🎯 Step 9: Add Configuration

If you used `nexus init`, you already have a `nexus_config.yaml` file. Update it with plugin-specific settings:

```yaml
app:
    title: "My First Nexus App"
    version: "1.0.0"
    description: "Learning Nexus Platform"
    debug: true

server:
    host: "0.0.0.0"
    port: 8000

database:
    type: sqlite
    connection:
        path: "./my_app.db"

plugins:
    enabled:
        - "my_first_plugin"
    directories:
        - "./plugins"

logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

Now you can run with the CLI:

```bash
nexus run
```

## 🔍 Step 10: Monitor Your Application

Use the CLI tools to monitor your application:

```bash
# Check application status
nexus status

# Check health
nexus health

# List plugins
nexus plugin list

# Get plugin info
nexus plugin info my_first_plugin

# View system information
nexus-admin system info
```

## 🎉 Congratulations!

You've successfully created your first Nexus application with a custom plugin! Here's what you've learned:

✅ **Application Creation**: Built a Nexus app with `create_nexus_app`
✅ **Plugin Development**: Created a custom plugin with API endpoints
✅ **Event System**: Used events for loose coupling
✅ **Configuration**: Set up application configuration
✅ **CLI Tools**: Used Nexus CLI for management
✅ **API Documentation**: Explored automatic API docs

## 🚀 Next Steps

Now that you have a basic understanding, explore more advanced features:

### Learn More About Plugins

- **[Plugin Basics](../plugins/basics.md)** - Deep dive into plugin development
- **[API Routes](../plugins/api-routes.md)** - Advanced API endpoint patterns
- **[Database Integration](../plugins/database.md)** - Persistent data storage
- **[Event System](../plugins/events.md)** - Advanced event handling

### Explore Architecture

- **[Core Components](../architecture/core-components.md)** - Understanding the framework
- **[Event Bus](../architecture/events.md)** - Event-driven architecture
- **[Core Components](../architecture/core-components.md)** - Service registry and dependency injection

### Production Deployment

- **[Docker Deployment](../deployment/docker.md)** - Containerize your app
- **[Configuration](configuration.md)** - Environment configs and deployment settings
- **[Monitoring](../deployment/monitoring.md)** - Health checks and metrics

## 💡 Tips for Success

1. **Start Small**: Begin with simple plugins and gradually add complexity
2. **Use Events**: Leverage the event system for loose coupling between plugins
3. **Log Everything**: Use the built-in logging for debugging and monitoring
4. **Test Regularly**: Test your plugins individually and as part of the whole system
5. **Read the Docs**: Explore the comprehensive documentation for advanced features

## 🆘 Need Help?

- **Documentation**: Browse the complete [documentation](../index.md)
- **GitHub Issues**: [Report bugs or ask questions](https://github.com/dnviti/nexus-platform/issues)
- **Discussions**: [Community discussions](https://github.com/dnviti/nexus-platform/discussions)

---

**Ready to build something amazing?** Continue with [Your First Plugin](first-plugin.md) for more advanced plugin development!
