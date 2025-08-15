"""
Task Manager Plugin for Nexus Framework

A comprehensive task management plugin that demonstrates:
- Plugin architecture
- Database operations
- RESTful API endpoints
- Event-driven communication
- Authentication integration
- Service and repository patterns
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from nexus.plugins import BasePlugin, PluginMetadata, PluginLifecycle, plugin_hook
from nexus.core import Event, EventPriority
from nexus.auth import get_current_user, require_permission
from nexus.database import get_db

logger = logging.getLogger(__name__)

# Database Models
Base = declarative_base()


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task status values."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class TaskCategory(str, Enum):
    """Task categories."""
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    MAINTENANCE = "maintenance"
    OTHER = "other"


# SQLAlchemy Models
class TaskModel(Base):
    """Task database model."""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    category = Column(SQLEnum(TaskCategory), default=TaskCategory.OTHER)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    assigned_to = Column(String(36), nullable=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    metadata = Column(JSON, default=dict)

    # Task relationships
    parent_id = Column(String(36), nullable=True)  # For subtasks
    project_id = Column(String(36), nullable=True)

    # Time tracking
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)

    # Notifications
    reminder_sent = Column(Boolean, default=False)
    reminder_date = Column(DateTime, nullable=True)


# Pydantic Models
class TaskBase(BaseModel):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    category: TaskCategory = TaskCategory.OTHER
    due_date: Optional[datetime] = None
    tags: List[str] = []
    assigned_to: Optional[str] = None
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    estimated_hours: Optional[int] = Field(None, ge=0, le=1000)
    metadata: Dict[str, Any] = {}

    @validator('due_date')
    def validate_due_date(cls, v):
        """Ensure due date is in the future."""
        if v and v < datetime.utcnow():
            # Allow dates in the past for historical data
            logger.warning("Due date is in the past")
        return v


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    category: Optional[TaskCategory] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    estimated_hours: Optional[int] = Field(None, ge=0, le=1000)
    actual_hours: Optional[int] = Field(None, ge=0, le=1000)
    metadata: Optional[Dict[str, Any]] = None


class Task(TaskBase):
    """Complete task schema."""
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    actual_hours: Optional[int] = None
    is_deleted: bool = False
    reminder_sent: bool = False
    reminder_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class TaskFilter(BaseModel):
    """Task filtering options."""
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    category: Optional[TaskCategory] = None
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    project_id: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    include_deleted: bool = False


class TaskStatistics(BaseModel):
    """Task statistics."""
    total: int = 0
    by_status: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    overdue: int = 0
    completed_today: int = 0
    completed_this_week: int = 0
    completed_this_month: int = 0
    average_completion_time: Optional[float] = None
    assigned_to_me: int = 0
    created_by_me: int = 0


# Repository Layer
class TaskRepository:
    """Repository for task data operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, task_data: TaskCreate, user_id: str) -> TaskModel:
        """Create a new task."""
        task = TaskModel(
            **task_data.dict(),
            created_by=user_id
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get(self, task_id: str) -> Optional[TaskModel]:
        """Get task by ID."""
        return self.db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.is_deleted == False
        ).first()

    async def get_many(self, filters: TaskFilter, skip: int = 0, limit: int = 100) -> List[TaskModel]:
        """Get tasks with filtering."""
        query = self.db.query(TaskModel)

        # Apply filters
        if not filters.include_deleted:
            query = query.filter(TaskModel.is_deleted == False)

        if filters.status:
            query = query.filter(TaskModel.status == filters.status)

        if filters.priority:
            query = query.filter(TaskModel.priority == filters.priority)

        if filters.category:
            query = query.filter(TaskModel.category == filters.category)

        if filters.assigned_to:
            query = query.filter(TaskModel.assigned_to == filters.assigned_to)

        if filters.created_by:
            query = query.filter(TaskModel.created_by == filters.created_by)

        if filters.project_id:
            query = query.filter(TaskModel.project_id == filters.project_id)

        if filters.parent_id:
            query = query.filter(TaskModel.parent_id == filters.parent_id)

        if filters.tags:
            # Filter by any matching tag
            for tag in filters.tags:
                query = query.filter(TaskModel.tags.contains([tag]))

        if filters.due_before:
            query = query.filter(TaskModel.due_date < filters.due_before)

        if filters.due_after:
            query = query.filter(TaskModel.due_date >= filters.due_after)

        if filters.created_before:
            query = query.filter(TaskModel.created_at < filters.created_before)

        if filters.created_after:
            query = query.filter(TaskModel.created_at >= filters.created_after)

        # Order by due date, then priority
        query = query.order_by(TaskModel.due_date.asc().nullslast(), TaskModel.priority.desc())

        return query.offset(skip).limit(limit).all()

    async def update(self, task_id: str, task_update: TaskUpdate) -> Optional[TaskModel]:
        """Update a task."""
        task = await self.get(task_id)
        if not task:
            return None

        update_data = task_update.dict(exclude_unset=True)

        # Handle status change
        if 'status' in update_data:
            if update_data['status'] == TaskStatus.DONE and task.status != TaskStatus.DONE:
                update_data['completed_at'] = datetime.utcnow()
            elif update_data['status'] != TaskStatus.DONE and task.status == TaskStatus.DONE:
                update_data['completed_at'] = None

        for field, value in update_data.items():
            setattr(task, field, value)

        task.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: str, soft: bool = True) -> bool:
        """Delete a task (soft delete by default)."""
        task = await self.get(task_id)
        if not task:
            return False

        if soft:
            task.is_deleted = True
            task.updated_at = datetime.utcnow()
            await self.db.commit()
        else:
            self.db.delete(task)
            await self.db.commit()

        return True

    async def get_statistics(self, user_id: Optional[str] = None, project_id: Optional[str] = None) -> TaskStatistics:
        """Get task statistics."""
        query = self.db.query(TaskModel).filter(TaskModel.is_deleted == False)

        if user_id:
            # Get tasks related to user
            user_tasks = query.filter(
                (TaskModel.created_by == user_id) | (TaskModel.assigned_to == user_id)
            ).all()
        else:
            user_tasks = query.all()

        if project_id:
            user_tasks = [t for t in user_tasks if t.project_id == project_id]

        stats = TaskStatistics()
        stats.total = len(user_tasks)

        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        completion_times = []

        for task in user_tasks:
            # Count by status
            status = task.status.value if task.status else 'unknown'
            stats.by_status[status] = stats.by_status.get(status, 0) + 1

            # Count by priority
            priority = task.priority.value if task.priority else 'unknown'
            stats.by_priority[priority] = stats.by_priority.get(priority, 0) + 1

            # Count by category
            category = task.category.value if task.category else 'unknown'
            stats.by_category[category] = stats.by_category.get(category, 0) + 1

            # Count overdue
            if task.due_date and task.due_date < now and task.status not in [TaskStatus.DONE, TaskStatus.CANCELLED]:
                stats.overdue += 1

            # Count completed
            if task.completed_at:
                if task.completed_at.date() == today:
                    stats.completed_today += 1
                if task.completed_at >= week_ago:
                    stats.completed_this_week += 1
                if task.completed_at >= month_ago:
                    stats.completed_this_month += 1

                # Calculate completion time
                completion_time = (task.completed_at - task.created_at).total_seconds() / 3600  # in hours
                completion_times.append(completion_time)

            # Count user-specific
            if user_id:
                if task.assigned_to == user_id:
                    stats.assigned_to_me += 1
                if task.created_by == user_id:
                    stats.created_by_me += 1

        # Calculate average completion time
        if completion_times:
            stats.average_completion_time = sum(completion_times) / len(completion_times)

        return stats


# Service Layer
class TaskService:
    """Service layer for task operations."""

    def __init__(self, repository: TaskRepository, event_bus):
        self.repository = repository
        self.event_bus = event_bus

    async def create_task(self, task_data: TaskCreate, user_id: str) -> Task:
        """Create a new task with notifications."""
        # Validate parent task exists if specified
        if task_data.parent_id:
            parent = await self.repository.get(task_data.parent_id)
            if not parent:
                raise ValueError(f"Parent task {task_data.parent_id} not found")

        # Create task
        task_model = await self.repository.create(task_data, user_id)
        task = Task.from_orm(task_model)

        # Publish event
        await self.event_bus.publish(Event(
            type="task.created",
            data={
                "task_id": task.id,
                "title": task.title,
                "created_by": user_id,
                "assigned_to": task.assigned_to,
                "priority": task.priority.value
            },
            priority=EventPriority.NORMAL
        ))

        # Schedule reminder if due date is set
        if task.due_date:
            reminder_time = task.due_date - timedelta(hours=24)
            if reminder_time > datetime.utcnow():
                await self._schedule_reminder(task.id, reminder_time)

        logger.info(f"Task created: {task.id} by user {user_id}")
        return task

    async def get_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Get a task with permission check."""
        task_model = await self.repository.get(task_id)
        if not task_model:
            return None

        # Check permissions (user can see tasks they created or are assigned to)
        if task_model.created_by != user_id and task_model.assigned_to != user_id:
            # Check if user has admin permission
            # This would integrate with the auth system
            logger.warning(f"User {user_id} attempted to access task {task_id} without permission")
            return None

        return Task.from_orm(task_model)

    async def update_task(self, task_id: str, task_update: TaskUpdate, user_id: str) -> Optional[Task]:
        """Update a task with validation and notifications."""
        # Get existing task
        existing = await self.repository.get(task_id)
        if not existing:
            return None

        # Check permissions
        if existing.created_by != user_id and existing.assigned_to != user_id:
            logger.warning(f"User {user_id} attempted to update task {task_id} without permission")
            return None

        # Track changes for notifications
        old_status = existing.status
        old_assigned = existing.assigned_to

        # Update task
        task_model = await self.repository.update(task_id, task_update)
        if not task_model:
            return None

        task = Task.from_orm(task_model)

        # Publish update event
        changes = task_update.dict(exclude_unset=True)
        await self.event_bus.publish(Event(
            type="task.updated",
            data={
                "task_id": task.id,
                "updated_by": user_id,
                "changes": changes
            },
            priority=EventPriority.NORMAL
        ))

        # Send notifications for specific changes
        if 'status' in changes and changes['status'] != old_status:
            await self._notify_status_change(task, old_status, user_id)

        if 'assigned_to' in changes and changes['assigned_to'] != old_assigned:
            await self._notify_assignment_change(task, old_assigned, user_id)

        logger.info(f"Task updated: {task_id} by user {user_id}")
        return task

    async def delete_task(self, task_id: str, user_id: str, permanent: bool = False) -> bool:
        """Delete a task with cascade handling."""
        task = await self.repository.get(task_id)
        if not task:
            return False

        # Check permissions
        if task.created_by != user_id:
            logger.warning(f"User {user_id} attempted to delete task {task_id} without permission")
            return False

        # Check for subtasks
        subtasks = await self.repository.get_many(
            TaskFilter(parent_id=task_id, include_deleted=False),
            limit=1
        )
        if subtasks:
            raise ValueError(f"Cannot delete task {task_id} with active subtasks")

        # Delete task
        success = await self.repository.delete(task_id, soft=not permanent)

        if success:
            # Publish event
            await self.event_bus.publish(Event(
                type="task.deleted",
                data={
                    "task_id": task_id,
                    "deleted_by": user_id,
                    "permanent": permanent
                },
                priority=EventPriority.NORMAL
            ))

            logger.info(f"Task deleted: {task_id} by user {user_id} (permanent={permanent})")

        return success

    async def get_user_tasks(self, user_id: str, filters: TaskFilter) -> List[Task]:
        """Get all tasks for a user with filters."""
        # Set user filter
        filters.created_by = user_id
        # Could also filter by assigned_to based on requirements

        task_models = await self.repository.get_many(filters)
        return [Task.from_orm(tm) for tm in task_models]

    async def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard data for a user."""
        stats = await self.repository.get_statistics(user_id)

        # Get recent tasks
        recent_filter = TaskFilter(
            created_after=datetime.utcnow() - timedelta(days=7),
            created_by=user_id
        )
        recent_tasks = await self.repository.get_many(recent_filter, limit=10)

        # Get upcoming tasks
        upcoming_filter = TaskFilter(
            due_after=datetime.utcnow(),
            due_before=datetime.utcnow() + timedelta(days=7),
            status=TaskStatus.TODO
        )
        upcoming_tasks = await self.repository.get_many(upcoming_filter, limit=10)

        return {
            "statistics": stats.dict(),
            "recent_tasks": [Task.from_orm(t).dict() for t in recent_tasks],
            "upcoming_tasks": [Task.from_orm(t).dict() for t in upcoming_tasks],
            "timestamp": datetime.utcnow()
        }

    async def _schedule_reminder(self, task_id: str, reminder_time: datetime):
        """Schedule a task reminder."""
        await self.event_bus.publish(Event(
            type="task.reminder.schedule",
            data={
                "task_id": task_id,
                "reminder_time": reminder_time.isoformat()
            },
            priority=EventPriority.LOW
        ))

    async def _notify_status_change(self, task: Task, old_status: TaskStatus, user_id: str):
        """Send notification for status change."""
        await self.event_bus.publish(Event(
            type="task.status_changed",
            data={
                "task_id": task.id,
                "title": task.title,
                "old_status": old_status.value,
                "new_status": task.status.value,
                "changed_by": user_id,
                "assigned_to": task.assigned_to
            },
            priority=EventPriority.HIGH if task.priority == TaskPriority.URGENT else EventPriority.NORMAL
        ))

    async def _notify_assignment_change(self, task: Task, old_assigned: Optional[str], user_id: str):
        """Send notification for assignment change."""
        await self.event_bus.publish(Event(
            type="task.assigned",
            data={
                "task_id": task.id,
                "title": task.title,
                "old_assigned": old_assigned,
                "new_assigned": task.assigned_to,
                "assigned_by": user_id
            },
            priority=EventPriority.HIGH
        ))


# Main Plugin Class
class TaskManagerPlugin(BasePlugin):
    """
    Task Manager Plugin for Nexus Framework.

    Provides comprehensive task management functionality including:
    - Task CRUD operations
    - Task assignment and tracking
    - Priority and status management
    - Due date tracking and reminders
    - Statistics and dashboards
    - Event-driven notifications
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="task_manager",
            version="2.0.0",
            description="Comprehensive task management system",
            author="Nexus Team",
            category="productivity",
            tags=["tasks", "productivity", "project-management"],
            dependencies=["auth", "database"],
            permissions=["task.read", "task.write", "task.delete", "task.admin"],
            config_schema={
                "enable_reminders": {"type": "boolean", "default": True},
                "reminder_advance_hours": {"type": "integer", "default": 24},
                "max_tasks_per_user": {"type": "integer", "default": 1000},
                "enable_time_tracking": {"type": "boolean", "default": True},
                "default_task_priority": {"type": "string", "default": "medium"}
            }
        )

        self.repository = None
        self.service = None
        self.db = None
        self.event_bus = None
        self.config = {}

    async def initialize(self, context) -> bool:
        """Initialize the plugin."""
        try:
            logger.info(f"Initializing {self.metadata.name} plugin v{self.metadata.version}")

            # Get dependencies
            self.db = context.get_service("database")
            self.event_bus = context.get_service("event_bus")

            if not self.db or not self.event_bus:
                logger.error("Required services not available")
                return False

            # Load configuration
            self.config = context.get_config(self.metadata.name, {})

            # Create database tables
            await self._create_tables()

            # Initialize repository and service
            self.repository = TaskRepository(self.db)
            self.service = TaskService(self.repository, self.event_bus)

            # Register event handlers
            self._register_event_handlers()

            # Register services
            context.register_service(f"{self.metadata.name}.repository", self.repository)
            context.register_service(f"{self.metadata.name}.service", self.service)

            logger.info(f"{self.metadata.name} plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.metadata.name}: {e}", exc_info=True)
            return False

    async def _create_tables(self):
        """Create database tables."""
        # This would use the database adapter to create tables
        # For SQLAlchemy:
        # Base.metadata.create_all(bind=self.db.engine)
        pass

    def _register_event_handlers(self):
        """Register event handlers."""
        # Subscribe to relevant events
        self.event_bus.subscribe("user.deleted", self._handle_user_deleted)
        self.event_bus.subscribe("project.deleted", self._handle_project_deleted)

        if self.config.get("enable_reminders", True):
            self.event_bus.subscribe("task.reminder.trigger", self._send_reminder)

    async def _handle_user_deleted(self, event: Event):
        """Handle user deletion by reassigning tasks."""
        user_id = event.data.get("user_id")
        if not user_id:
            return

        # Reassign tasks to admin or mark as unassigned
        tasks = await self.repository.get_many(
            TaskFilter(assigned_to=user_id),
            limit=1000
        )

        for task in tasks:
            await self.repository.update(
                task.id,
                TaskUpdate(assigned_to=None)
            )

        logger.info(f"Reassigned {len(tasks)} tasks from deleted user {user_id}")

    async def _handle_project_deleted(self, event: Event):
        """Handle project deletion."""
        project_id = event.data.get("project_id")
        if not project_id:
            return

        # Archive all tasks in the project
        tasks = await self.repository.get_many(
            TaskFilter(project_id=project_id),
            limit=10000
        )

        for task in tasks:
            await self.repository.update(
                task.id,
                TaskUpdate(status=TaskStatus.ARCHIVED)
            )

        logger.info(f"Archived {len(tasks)} tasks from deleted project {project_id}")

    async def _send_reminder(self, event: Event):
        """Send task reminder notification."""
        task_id = event.data.get("task_id")
        if not task_id:
            return

        task = await self.repository.get(task_id)
        if not task or task.reminder_sent:
            return

        # Send reminder notification
        await self.event_bus.publish(Event(
            type="notification.send",
            data={
                "user_id": task.assigned_to or task.created_by,
                "type": "task_reminder",
                "title": f"Task Reminder: {task.title}",
                "message": f"Task '{task.title}' is due on {task.due_date}",
                "task_id": task_id
            },
            priority=EventPriority.HIGH
        ))

        # Mark reminder as sent
        await self.repository.update(
            task_id,
            TaskUpdate(metadata={"reminder_sent": True})
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Define API routes for the plugin."""
        router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

        # Dependency to get current user (simplified)
        async def get_current_user_id():
            # This would integrate with the auth system
            return "current_user_id"

        @router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
        async def create_task(
            task: TaskCreate,
            user_id: str = Depends(get_current_user_id),
            db: Session = Depends(get_db)
        ):
            """Create a new task."""
            try:
                repository = TaskRepository(db)
                service = TaskService(repository, self.event_bus)
                return await service.create_task(task, user_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.get("/", response_model=List[Task])
        async def get_tasks(
            status: Optional[TaskStatus] = None,
            priority: Optional[TaskPriority] = None,
            category: Optional[TaskCategory] = None,
            assigned_to: Optional[str] = None,
            project_id: Optional[str] = None,
            tags: Optional[List[str]] = Query(None),
            skip: int = 0,
            limit: int = Query(100, le=500),
            user_id: str = Depends(get_current_user_id),
            db: Session = Depends(get_db)
        ):
            """Get tasks with filtering."""
            filters = TaskFilter(
                status=status,
                priority=priority,
                category=category,
                assigned_to=assigned_to,
                project_id=project_id,
                tags=tags,
                created_by=user_id  # Filter by current user
            )
            repository = TaskRepository(db)
            task_models = await repository.get_many(filters, skip=skip, limit=limit)
            return [Task.from_orm(tm) for tm in task_models]

        @router.get("/statistics", response_model=TaskStatistics)
        async def get_statistics(
            project_id: Optional[str] = None,
            user_id: str = Depends(get_current_user_id),
            db: Session = Depends(get_db)
        ):
            """Get task statistics."""
            repository = TaskRepository(db)
            return await repository.get_statistics(user_id, project_id)

        @router.get("/dashboard")
        async def get_dashboard(
            user_id: str = Depends(get_current_user_id),
            db: Session = Depends(get_db)
        ):
            """Get dashboard data."""
            repository = TaskRepository(db)
            service = TaskService(repository, self.event_bus)
            return await service.get_dashboard_data(user_id)

        @router.get("/{task_id}", response_model=Task)
        async def get_task(
            task_id: str,
