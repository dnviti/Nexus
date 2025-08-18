# Your First Plugin

Learn how to create powerful, modular plugins for your Nexus application. This guide walks you through building a complete plugin from scratch.

## 🎯 What You'll Build

A **Task Manager Plugin** with:

- RESTful API for managing tasks
- Database persistence
- Event publishing and handling
- Configuration management
- Health monitoring
- Complete CRUD operations

## 📋 Prerequisites

- [Nexus Platform installed](installation.md)
- [Quick Start completed](quickstart.md)
- Understanding of Python classes and async/await
- Basic knowledge of REST APIs

## 🚀 Step 1: Create Plugin Structure

Use the Nexus CLI to create a new plugin:

```bash
# Create a new plugin called "task_manager"
nexus plugin create task_manager

# This creates the plugin in plugins/custom/task_manager/
```

The CLI creates this structure:

```
plugins/custom/task_manager/
├── __init__.py          # Plugin package initialization
├── plugin.py            # Main plugin implementation
├── manifest.json        # Plugin metadata
└── requirements.txt     # Plugin dependencies (if any)
```

## 📝 Step 2: Understand the Plugin Template

Let's examine the generated `plugin.py` file. The CLI creates a basic template that follows Nexus best practices:

```python
"""
Task Manager Plugin Template
"""

from nexus.plugins import BasePlugin

class TaskManagerPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "task_manager"
        self.version = "1.0.0"
        self.description = "A task management plugin"

    async def initialize(self) -> bool:
        # Plugin initialization logic
        return True

    async def shutdown(self) -> None:
        # Plugin cleanup logic
        pass

def create_plugin():
    return TaskManagerPlugin()
```

## 🛠️ Step 3: Build the Complete Plugin

Replace the contents of `plugins/custom/task_manager/plugin.py` with this complete implementation:

```python
"""
Task Manager Plugin for Nexus Platform

A comprehensive example demonstrating:
- CRUD API endpoints
- Database integration
- Event handling
- Configuration management
- Health monitoring
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from nexus.plugins import BasePlugin, HealthStatus


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskCreate(BaseModel):
    """Schema for creating a task."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[str] = Field(None, regex="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    completed: Optional[bool] = None


class Task(BaseModel):
    """Complete task schema."""
    id: str
    title: str
    description: Optional[str]
    priority: str
    due_date: Optional[datetime]
    tags: List[str]
    completed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskStats(BaseModel):
    """Task statistics."""
    total: int
    completed: int
    pending: int
    overdue: int
    by_priority: Dict[str, int]


# ============================================================================
# Main Plugin Class
# ============================================================================

class TaskManagerPlugin(BasePlugin):
    """
    Task Manager Plugin - A comprehensive example plugin.

    Features:
    - Complete CRUD operations for tasks
    - Task filtering and search
    - Statistics and reporting
    - Event publishing for task changes
    - Configuration for default settings
    - Health monitoring
    """

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()

        # Plugin metadata
        self.name = "task_manager"
        self.version = "1.0.0"
        self.description = "A comprehensive task management plugin"
        self.author = "Nexus Team"
        self.category = "productivity"

        # In-memory storage (in production, use database)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_counter = 0

    # ========================================================================
    # Plugin Lifecycle
    # ========================================================================

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info(f"Initializing {self.name} plugin v{self.version}")

            # Load configuration
            await self._load_configuration()

            # Initialize data
            await self._initialize_data()

            # Subscribe to events
            await self._setup_event_handlers()

            # Register services
            self.register_service(f"{self.name}.api", self)

            self.initialized = True
            self.logger.info(f"{self.name} plugin initialized successfully")

            # Publish initialization event
            await self.publish_event(
                f"{self.name}.initialized",
                {"version": self.version, "task_count": len(self.tasks)}
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            return False

    async def shutdown(self) -> None:
        """Clean up plugin resources."""
        self.logger.info(f"Shutting down {self.name} plugin")

        # Save current state
        await self._save_state()

        # Publish shutdown event
        await self.publish_event(
            f"{self.name}.shutdown",
            {"task_count": len(self.tasks)}
        )

        self.logger.info(f"{self.name} plugin shut down successfully")

    # ========================================================================
    # API Routes
    # ========================================================================

    def get_api_routes(self) -> List[APIRouter]:
        """Define API routes for task management."""
        router = APIRouter(tags=["Task Manager"])

        @router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
        async def create_task(task_data: TaskCreate):
            """Create a new task."""
            task_id = str(uuid4())
            now = datetime.utcnow()

            task = {
                "id": task_id,
                "title": task_data.title,
                "description": task_data.description,
                "priority": task_data.priority,
                "due_date": task_data.due_date,
                "tags": task_data.tags,
                "completed": False,
                "created_at": now,
                "updated_at": now,
                "completed_at": None
            }

            # Store task
            self.tasks[task_id] = task
            self.task_counter += 1

            # Publish event
            await self.publish_event(
                f"{self.name}.task_created",
                {"task_id": task_id, "title": task_data.title, "priority": task_data.priority}
            )

            self.logger.info(f"Created task: {task_data.title}")
            return Task(**task)

        @router.get("/tasks", response_model=List[Task])
        async def list_tasks(
            completed: Optional[bool] = None,
            priority: Optional[str] = Query(None, regex="^(low|medium|high|urgent)$"),
            tag: Optional[str] = None,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """List tasks with optional filtering."""
            filtered_tasks = list(self.tasks.values())

            # Apply filters
            if completed is not None:
                filtered_tasks = [t for t in filtered_tasks if t["completed"] == completed]

            if priority:
                filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority]

            if tag:
                filtered_tasks = [t for t in filtered_tasks if tag in t.get("tags", [])]

            # Sort by created_at (newest first)
            filtered_tasks.sort(key=lambda t: t["created_at"], reverse=True)

            # Apply pagination
            paginated_tasks = filtered_tasks[skip:skip + limit]

            return [Task(**task) for task in paginated_tasks]

        @router.get("/tasks/{task_id}", response_model=Task)
        async def get_task(task_id: str):
            """Get a specific task by ID."""
            if task_id not in self.tasks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )

            return Task(**self.tasks[task_id])

        @router.put("/tasks/{task_id}", response_model=Task)
        async def update_task(task_id: str, task_update: TaskUpdate):
            """Update an existing task."""
            if task_id not in self.tasks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )

            task = self.tasks[task_id]
            update_data = task_update.dict(exclude_unset=True)

            # Track if completion status changed
            was_completed = task["completed"]

            # Update fields
            for field, value in update_data.items():
                task[field] = value

            task["updated_at"] = datetime.utcnow()

            # Set completed_at if task was just completed
            if not was_completed and task.get("completed", False):
                task["completed_at"] = datetime.utcnow()
            elif was_completed and not task.get("completed", True):
                task["completed_at"] = None

            # Publish event
            event_data = {"task_id": task_id, "changes": update_data}
            if "completed" in update_data:
                event_type = "task_completed" if update_data["completed"] else "task_reopened"
                await self.publish_event(f"{self.name}.{event_type}", event_data)
            else:
                await self.publish_event(f"{self.name}.task_updated", event_data)

            return Task(**task)

        @router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_task(task_id: str):
            """Delete a task."""
            if task_id not in self.tasks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )

            task_title = self.tasks[task_id]["title"]
            del self.tasks[task_id]

            # Publish event
            await self.publish_event(
                f"{self.name}.task_deleted",
                {"task_id": task_id, "title": task_title}
            )

            return None

        @router.get("/tasks/stats", response_model=TaskStats)
        async def get_task_statistics():
            """Get task statistics."""
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks.values() if t["completed"])
            pending = total - completed

            # Count overdue tasks
            now = datetime.utcnow()
            overdue = sum(
                1 for t in self.tasks.values()
                if not t["completed"] and t.get("due_date") and t["due_date"] < now
            )

            # Count by priority
            by_priority = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
            for task in self.tasks.values():
                by_priority[task["priority"]] += 1

            return TaskStats(
                total=total,
                completed=completed,
                pending=pending,
                overdue=overdue,
                by_priority=by_priority
            )

        @router.post("/tasks/{task_id}/complete", response_model=Task)
        async def complete_task(task_id: str):
            """Mark a task as completed."""
            if task_id not in self.tasks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )

            task = self.tasks[task_id]
            if task["completed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Task is already completed"
                )

            task["completed"] = True
            task["completed_at"] = datetime.utcnow()
            task["updated_at"] = datetime.utcnow()

            # Publish event
            await self.publish_event(
                f"{self.name}.task_completed",
                {"task_id": task_id, "title": task["title"]}
            )

            return Task(**task)

        @router.get("/health")
        async def health_check():
            """Plugin health check endpoint."""
            health_status = await self.health_check()
            return health_status.dict()

        return [router]

    # ========================================================================
    # Database Schema
    # ========================================================================

    def get_database_schema(self) -> Dict[str, Any]:
        """Define database schema for task storage."""
        return {
            "collections": {
                "tasks": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "completed"},
                        {"field": "priority"},
                        {"field": "due_date"},
                        {"field": "created_at"},
                        {"field": "tags", "type": "multikey"}
                    ]
                }
            },
            "initial_data": {
                "config": {
                    "default_priority": "medium",
                    "max_tasks_per_user": 1000,
                    "enable_notifications": True
                }
            }
        }

    # ========================================================================
    # Health Monitoring
    # ========================================================================

    async def health_check(self) -> HealthStatus:
        """Check plugin health status."""
        health = await super().health_check()

        # Add custom health checks
        try:
            total_tasks = len(self.tasks)
            completed_tasks = sum(1 for t in self.tasks.values() if t["completed"])

            health.components["tasks"] = {
                "status": "healthy",
                "total": total_tasks,
                "completed": completed_tasks,
                "pending": total_tasks - completed_tasks
            }

            # Check for any concerning conditions
            if total_tasks > 10000:  # Large number of tasks
                health.components["tasks"]["warning"] = "High task count detected"

        except Exception as e:
            health.components["tasks"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health.healthy = False

        # Update metrics
        health.metrics.update({
            "total_tasks": float(len(self.tasks)),
            "completed_tasks": float(sum(1 for t in self.tasks.values() if t["completed"])),
            "task_creation_rate": float(self.task_counter)
        })

        return health

    # ========================================================================
    # Configuration Management
    # ========================================================================

    async def _load_configuration(self) -> None:
        """Load plugin configuration."""
        # Set default configuration
        self.config = {
            "default_priority": await self.get_config("default_priority", "medium"),
            "max_tasks": await self.get_config("max_tasks", 1000),
            "enable_notifications": await self.get_config("enable_notifications", True),
            "auto_archive_completed": await self.get_config("auto_archive_completed", False)
        }

        self.logger.debug(f"Loaded configuration: {self.config}")

    async def _initialize_data(self) -> None:
        """Initialize plugin data."""
        # Load existing tasks from storage
        stored_tasks = await self.get_data("tasks")
        if stored_tasks:
            self.tasks = stored_tasks
            self.task_counter = len(self.tasks)
        else:
            # Create a sample task for demonstration
            sample_task_id = str(uuid4())
            sample_task = {
                "id": sample_task_id,
                "title": "Welcome to Task Manager!",
                "description": "This is a sample task to get you started.",
                "priority": "medium",
                "due_date": None,
                "tags": ["sample", "welcome"],
                "completed": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "completed_at": None
            }
            self.tasks[sample_task_id] = sample_task
            self.task_counter = 1

    async def _save_state(self) -> None:
        """Save plugin state."""
        await self.set_data("tasks", self.tasks)
        await self.set_config("task_counter", self.task_counter)

    # ========================================================================
    # Event Handlers
    # ========================================================================

    async def _setup_event_handlers(self) -> None:
        """Set up event subscriptions."""
        # Subscribe to user events to create welcome tasks
        await self.subscribe_to_event("user.created", self._handle_user_created)

        # Subscribe to system events
        await self.subscribe_to_event("system.maintenance", self._handle_maintenance)

    async def _handle_user_created(self, event):
        """Handle new user creation by creating a welcome task."""
        username = event.data.get("username", "New User")

        welcome_task_id = str(uuid4())
        welcome_task = {
            "id": welcome_task_id,
            "title": f"Welcome to Task Manager, {username}!",
            "description": "Get started by exploring the task management features.",
            "priority": "medium",
            "due_date": None,
            "tags": ["welcome", "onboarding"],
            "completed": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }

        self.tasks[welcome_task_id] = welcome_task
        self.task_counter += 1

        self.logger.info(f"Created welcome task for new user: {username}")

    async def _handle_maintenance(self, event):
        """Handle system maintenance events."""
        self.logger.info("System maintenance event received, saving state...")
        await self._save_state()

    # ========================================================================
    # Public API Methods
    # ========================================================================

    async def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)

    async def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending (incomplete) tasks."""
        return [task for task in self.tasks.values() if not task["completed"]]

    async def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get all overdue tasks."""
        now = datetime.utcnow()
        return [
            task for task in self.tasks.values()
            if not task["completed"] and task.get("due_date") and task["due_date"] < now
        ]


# ============================================================================
# Plugin Factory
# ============================================================================

def create_plugin():
    """Create and return the plugin instance."""
    return TaskManagerPlugin()
```

## 📋 Step 4: Update Plugin Manifest

Edit `plugins/custom/task_manager/manifest.json`:

```json
{
    "name": "task_manager",
    "version": "1.0.0",
    "title": "Task Manager",
    "description": "A comprehensive task management plugin with CRUD operations, statistics, and event handling",
    "author": "Your Name",
    "license": "MIT",
    "category": "productivity",
    "tags": ["tasks", "productivity", "crud", "management"],
    "python_version": ">=3.11",
    "nexus_version": ">=0.1.0",
    "dependencies": [],
    "permissions": ["database.read", "database.write", "events.publish", "events.subscribe"],
    "configuration": {
        "default_priority": {
            "type": "string",
            "default": "medium",
            "description": "Default priority for new tasks"
        },
        "max_tasks": {
            "type": "integer",
            "default": 1000,
            "description": "Maximum number of tasks allowed"
        },
        "enable_notifications": {
            "type": "boolean",
            "default": true,
            "description": "Enable task notifications"
        }
    },
    "api_endpoints": [
        {
            "method": "POST",
            "path": "/tasks",
            "description": "Create a new task"
        },
        {
            "method": "GET",
            "path": "/tasks",
            "description": "List all tasks with filtering"
        },
        {
            "method": "GET",
            "path": "/tasks/{task_id}",
            "description": "Get a specific task"
        },
        {
            "method": "PUT",
            "path": "/tasks/{task_id}",
            "description": "Update a task"
        },
        {
            "method": "DELETE",
            "path": "/tasks/{task_id}",
            "description": "Delete a task"
        },
        {
            "method": "GET",
            "path": "/tasks/stats",
            "description": "Get task statistics"
        }
    ],
    "events": {
        "publishes": [
            "task_manager.task_created",
            "task_manager.task_updated",
            "task_manager.task_completed",
            "task_manager.task_deleted"
        ],
        "subscribes": ["user.created", "system.maintenance"]
    }
}
```

## 🚀 Step 5: Test Your Plugin

1. **Restart your Nexus application**:

    ```bash
    python main.py
    ```

2. **Verify plugin loaded**:

    ```bash
    # Check if plugin is loaded
    nexus plugin list

    # Get plugin information
    nexus plugin info task_manager
    ```

3. **Test the API endpoints**:

    ```bash
    # Create a task
    curl -X POST http://localhost:8000/tasks \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Learn Nexus Plugins",
        "description": "Complete the first plugin tutorial",
        "priority": "high",
        "tags": ["learning", "nexus"]
      }'

    # List tasks
    curl http://localhost:8000/tasks

    # Get task statistics
    curl http://localhost:8000/tasks/stats

    # Complete a task
    curl -X POST http://localhost:8000/tasks/{task_id}/complete
    ```

4. **View API documentation**:
    - Visit http://localhost:8000/docs
    - Find the "Task Manager" section
    - Try the interactive API endpoints

## 📊 Step 6: Monitor Plugin Health

Check your plugin's health status:

```bash
# Check plugin health via CLI
nexus plugin info task_manager

# Or via API
curl http://localhost:8000/health
```

The health check includes:

- Overall plugin status
- Task counts and statistics
- Component health
- Performance metrics

## 🎯 Step 7: Understand Key Concepts

### Plugin Lifecycle

Your plugin follows this lifecycle:

1. **Instantiation**: `__init__()` method called
2. **Initialization**: `initialize()` method called
3. **Runtime**: Plugin serves requests and handles events
4. **Shutdown**: `shutdown()` method called for cleanup

### API Route Registration

The `get_api_routes()` method returns FastAPI routers that are automatically registered with your application.

### Event System

Your plugin can:

- **Publish events** using `await self.publish_event()`
- **Subscribe to events** using `await self.subscribe_to_event()`

### Configuration Management

Use these methods for persistent configuration:

- `await self.get_config(key, default)` - Get configuration value
- `await self.set_config(key, value)` - Set configuration value

### Data Persistence

Use these methods for persistent data:

- `await self.get_data(key)` - Get stored data
- `await self.set_data(key, value)` - Store data

## 🔧 Step 8: Advanced Features

### Add Custom Configuration

Create `nexus_config.yaml` in your project root to configure your plugin:

```yaml
plugins:
    task_manager:
        default_priority: "high"
        max_tasks: 5000
        enable_notifications: true
        auto_archive_completed: true
```

### Add Database Integration

For production use, integrate with a database:

```python
def get_database_schema(self) -> Dict[str, Any]:
    """Define database tables for tasks."""
    return {
        "tables": {
            "tasks": {
                "columns": {
                    "id": {"type": "VARCHAR", "primary_key": True},
                    "title": {"type": "VARCHAR", "nullable": False},
                    "description": {"type": "TEXT", "nullable": True},
                    "priority": {"type": "VARCHAR", "default": "medium"},
                    "completed": {"type": "BOOLEAN", "default": False},
                    "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"},
                    "updated_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}
                },
                "indexes": [
                    {"columns": ["completed"]},
                    {"columns": ["priority"]},
                    {"columns": ["created_at"]}
                ]
            }
        }
    }
```

## 🧪 Step 9: Test Your Plugin

Create a simple test script to verify functionality:

```python
# test_plugin.py
import asyncio
import json
from plugins.custom.task_manager.plugin import create_plugin

async def test_plugin():
    """Test the task manager plugin."""
    plugin = create_plugin()

    # Initialize plugin
    success = await plugin.initialize()
    print(f"Plugin initialization: {'✓' if success else '✗'}")

    # Test plugin info
    info = plugin.get_info()
    print(f"Plugin name: {info['name']}")
    print(f"Plugin version: {info['version']}")

    # Test health check
    health = await plugin.health_check()
    print(f"Plugin health: {health.status}")

    # Cleanup
    await plugin.shutdown()

if __name__ == "__main__":
    asyncio.run(test_plugin())
```

Run the test:

```bash
python test_plugin.py
```

## 🎉 Congratulations!

You've successfully created a complete Nexus plugin with:

✅ **CRUD Operations** - Create, read, update, delete tasks
✅ **API Documentation** - Automatic OpenAPI/Swagger docs
✅ **Event System** - Publishing and subscribing to events
✅ **Configuration** - Persistent configuration management
✅ **Health Monitoring** - Built-in health checks
✅ **Data Persistence** - Storing and retrieving data
✅ **Error Handling** - Proper HTTP error responses

## 🚀 Next Steps

### Enhance Your Plugin

1. **Add Authentication**: Integrate with Nexus auth system
2. **Add Validation**: More sophisticated input validation
3. **Add Caching**: Cache frequently accessed data
4. **Add Notifications**: Send notifications on task completion
5. **Add Search**: Full-text search capabilities

### Learn More

- **[Plugin API Routes](../plugins/api-routes.md)** - Advanced API patterns
- **[Database Integration](../plugins/database.md)** - Working with databases
- **[Event System](../plugins/events.md)** - Advanced event handling
- **[Plugin Testing](../plugins/testing.md)** - Testing strategies
- **[Plugin Basics](../plugins/basics.md)** - Advanced configuration

### Share Your Plugin

1. **Package your plugin** for distribution
2. **Add comprehensive tests**
3. **Create documentation**
4. **Publish to a registry** (when available)

## 🆘 Troubleshooting

### Plugin Not Loading

```bash
# Check plugin directory structure
ls -la plugins/custom/task_manager/

# Check for syntax errors
python -m py_compile plugins/custom/task_manager/plugin.py

# Check plugin list
nexus plugin list
```

### API Endpoints Not Working

1. Verify `get_api_routes()` returns a list of routers
2. Check for proper FastAPI decorators
3. Ensure plugin is initialized successfully
4. Check application logs for errors

### Events Not Working

1. Verify event subscriptions in `_setup_event_handlers()`
2. Check event publishing with `await self.publish_event()`
3. Ensure event handlers are async functions
4. Check logs for event processing errors

---

**🎊 Great job!** You've mastered Nexus plugin development. Ready to build something amazing? Check out [Advanced Plugin Patterns](../plugins/advanced.md)!
