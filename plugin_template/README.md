# Nexus Framework Plugin Template

This template provides the standard structure for creating Nexus Framework plugins with proper dependency management.

## Plugin Structure

```
my_plugin/
├── __init__.py              # Plugin package initialization
├── plugin.py                # Main plugin class (required)
├── manifest.json            # Plugin metadata and configuration (required)
├── pyproject.toml          # Plugin dependencies and project config (required)
├── README.md               # Plugin documentation
├── LICENSE                 # Plugin license file
├── .gitignore             # Git ignore rules
├── models/                # Data models
│   ├── __init__.py
│   └── entities.py
├── services/              # Business logic services
│   ├── __init__.py
│   └── core_service.py
├── api/                   # API endpoints and routes
│   ├── __init__.py
│   ├── routes.py
│   └── schemas.py
├── repositories/          # Data access layer
│   ├── __init__.py
│   └── repository.py
├── events/                # Event handlers
│   ├── __init__.py
│   └── handlers.py
├── config/                # Plugin configuration
│   ├── __init__.py
│   └── settings.py
├── utils/                 # Utility functions
│   ├── __init__.py
│   └── helpers.py
├── static/                # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── img/
├── templates/             # HTML/Email templates
│   └── email/
├── migrations/            # Database migrations
│   └── versions/
├── tests/                 # Plugin tests
│   ├── __init__.py
│   ├── test_plugin.py
│   ├── test_services.py
│   └── test_api.py
├── scripts/               # Installation and maintenance scripts
│   ├── install.py
│   ├── uninstall.py
│   ├── update.py
│   └── health.py
└── docs/                  # Plugin documentation
    ├── api.md
    ├── configuration.md
    └── examples.md
```

## Required Files

### 1. `plugin.py` - Main Plugin Class

```python
"""
My Plugin for Nexus Framework

Description of what your plugin does.
"""

from nexus.plugins import BasePlugin, PluginMetadata
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)


class MyPlugin(BasePlugin):
    """Main plugin class."""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="Description of my plugin",
            author="Your Name",
            category="category_name",
            tags=["tag1", "tag2"],
            dependencies=["required_plugin_1"],
            permissions=["permission.read", "permission.write"]
        )

    async def initialize(self, context) -> bool:
        """Initialize the plugin."""
        try:
            logger.info(f"Initializing {self.metadata.name} v{self.metadata.version}")

            # Get services from context
            self.db = context.get_service("database")
            self.event_bus = context.get_service("event_bus")

            # Load configuration
            self.config = context.get_config(self.metadata.name, {})

            # Initialize your plugin components here

            logger.info(f"{self.metadata.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.metadata.name}: {e}")
            return False

    async def cleanup(self):
        """Clean up plugin resources."""
        logger.info(f"Cleaning up {self.metadata.name}")
        # Cleanup code here

    def get_api_routes(self):
        """Return API routes for the plugin."""
        router = APIRouter(prefix=f"/api/{self.metadata.name}", tags=[self.metadata.name])

        @router.get("/")
        async def get_info():
            """Get plugin information."""
            return {
                "plugin": self.metadata.name,
                "version": self.metadata.version,
                "status": "active"
            }

        # Add more routes here

        return [router]
```

### 2. `manifest.json` - Plugin Metadata

```json
{
  "name": "my_plugin",
  "display_name": "My Plugin",
  "version": "1.0.0",
  "description": "A brief description of what your plugin does",
  "author": "Your Name",
  "license": "MIT",
  "category": "utility",
  "tags": ["tag1", "tag2", "tag3"],
  "repository": "https://github.com/yourusername/my-plugin",
  "homepage": "https://your-plugin-website.com",
  "dependencies": {
    "nexus_framework": ">=0.1.0",
    "plugins": [],
    "python": ">=3.11",
    "packages": ["package1>=1.0.0", "package2>=2.0.0"]
  },
  "permissions": [
    "database.read",
    "database.write",
    "events.publish",
    "api.register_routes"
  ],
  "api": {
    "prefix": "/api/my_plugin",
    "version": "v1",
    "endpoints": [
      {
        "path": "/",
        "methods": ["GET"],
        "description": "Get plugin information"
      }
    ]
  },
  "events": {
    "publishes": ["my_plugin.event1", "my_plugin.event2"],
    "subscribes": ["system.startup", "user.created"]
  },
  "configuration": {
    "schema": {
      "setting1": {
        "type": "string",
        "default": "default_value",
        "description": "Description of setting1"
      },
      "setting2": {
        "type": "integer",
        "default": 100,
        "min": 1,
        "max": 1000,
        "description": "Description of setting2"
      }
    }
  },
  "compatibility": {
    "min_framework_version": "0.1.0",
    "max_framework_version": null,
    "tested_versions": ["0.1.0"]
  }
}
```

### 3. `pyproject.toml` - Plugin Dependencies and Configuration

```txt
# My Plugin Requirements
# Dependencies specific to this plugin
# The Nexus Framework core dependencies are already available

# Add your plugin-specific dependencies here
# Example:
# requests>=2.31.0
# redis>=5.0.1
# numpy>=1.26.2

# Database drivers (uncomment if needed)
# asyncpg>=0.29.0         # PostgreSQL async driver
# aiomysql>=0.2.0         # MySQL async driver
# motor>=3.3.2            # MongoDB async driver

# Optional features (uncomment if needed)
# pillow>=10.1.0          # Image processing
# pandas>=2.1.4           # Data analysis
# jinja2>=3.1.3           # Template engine
```

## Creating a New Plugin

### Step 1: Copy the Template

```bash
# Copy the template to create your plugin
cp -r plugin_template plugins/my_new_plugin
cd plugins/my_new_plugin
```

### Step 2: Update Plugin Information

1. Edit `manifest.json` with your plugin details
2. Rename and modify the main plugin class in `plugin.py`
3. Update `pyproject.toml` with your dependencies
4. Update `README.md` with documentation

### Step 3: Install Dependencies

```bash
# Install plugin dependencies with Poetry
poetry install
```

### Step 4: Implement Plugin Logic

1. Add your models in `models/`
2. Implement services in `services/`
3. Create API routes in `api/`
4. Add event handlers in `events/`
5. Write tests in `tests/`

### Step 5: Test Your Plugin

```bash
# Run plugin tests
pytest tests/

# Test with the framework
cd ../../
python -c "
from nexus import create_nexus_app
app = create_nexus_app()
# Your plugin should auto-load if in the plugins directory
"
```

## Best Practices

### 1. Dependency Management

- **Keep dependencies minimal** - Only include what's necessary
- **Version pin carefully** - Use >= for flexibility, == for stability
- **Document optional dependencies** - Comment out optional packages
- **Test with minimal deps** - Ensure plugin works with core dependencies

### 2. Plugin Structure

- **Follow the structure** - Maintain consistent organization
- **Separate concerns** - Use models, services, repositories pattern
- **Document everything** - Include docstrings and comments
- **Write tests** - Aim for >80% code coverage

### 3. Configuration

- **Use manifest.json** - Define all metadata and configuration
- **Validate config** - Use schema validation in manifest
- **Provide defaults** - Always have sensible defaults
- **Document settings** - Explain each configuration option

### 4. Error Handling

```python
async def initialize(self, context) -> bool:
    """Initialize with proper error handling."""
    try:
        # Initialization code
        return True
    except SpecificError as e:
        logger.error(f"Specific error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False
```

### 5. Event Communication

```python
# Publishing events
await self.event_bus.publish(Event(
    type="my_plugin.something_happened",
    data={"key": "value"},
    priority=EventPriority.NORMAL
))

# Subscribing to events
self.event_bus.subscribe("other_plugin.event", self.handle_event)

async def handle_event(self, event: Event):
    """Handle incoming event."""
    # Process event
    pass
```

## Example Plugins

### Minimal Plugin

```python
from nexus.plugins import BasePlugin, PluginMetadata

class MinimalPlugin(BasePlugin):
    """A minimal plugin example."""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="minimal",
            version="1.0.0",
            description="A minimal plugin"
        )

    async def initialize(self, context) -> bool:
        return True
```

### Database Plugin

```python
from nexus.plugins import BasePlugin, PluginMetadata
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String(36), primary_key=True)
    name = Column(String(100))
    created_at = Column(DateTime)

class DatabasePlugin(BasePlugin):
    """Plugin with database operations."""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="database_plugin",
            version="1.0.0",
            description="Plugin with database"
        )

    async def initialize(self, context) -> bool:
        self.db = context.get_service("database")
        # Create tables
        # Base.metadata.create_all(self.db.engine)
        return True
```

## Testing

### Unit Test Example

```python
# tests/test_plugin.py
import pytest
from ..plugin import MyPlugin

@pytest.fixture
async def plugin():
    plugin = MyPlugin()
    yield plugin
    await plugin.cleanup()

@pytest.mark.asyncio
async def test_plugin_initialization(plugin):
    """Test plugin initializes correctly."""
    context = MockContext()
    result = await plugin.initialize(context)
    assert result is True
    assert plugin.metadata.name == "my_plugin"
```

## Distribution

### Publishing Your Plugin

1. **Package your plugin:**

```bash
python setup.py sdist bdist_wheel
```

2. **Upload to PyPI:**

```bash
pip install twine
twine upload dist/*
```

3. **Or share via Git:**

```bash
git init
git add .
git commit -m "Initial plugin release"
git remote add origin https://github.com/yourusername/nexus-plugin-name
git push -u origin main
```

### Installing Published Plugins

```bash
# From PyPI
pip install nexus-platform-plugin-name

# From Git
pip install git+https://github.com/username/nexus-plugin-name.git

# From local directory
pip install -e ./path/to/plugin
```

## Support

- **Documentation**: https://docs.nexus-framework.dev/plugin-development
- **Examples**: https://github.com/nexus-framework/plugin-examples
- **Community**: https://discord.gg/nexus-framework
- **Issues**: https://github.com/nexus-framework/nexus/issues
