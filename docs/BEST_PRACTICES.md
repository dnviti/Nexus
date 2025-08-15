# Nexus Framework Best Practices

## Table of Contents
- [Overview](#overview)
- [Plugin Development](#plugin-development)
- [Code Organization](#code-organization)
- [Architecture Patterns](#architecture-patterns)
- [Performance Optimization](#performance-optimization)
- [Security Best Practices](#security-best-practices)
- [API Design](#api-design)
- [Database Patterns](#database-patterns)
- [Error Handling](#error-handling)
- [Testing Strategies](#testing-strategies)
- [Logging and Monitoring](#logging-and-monitoring)
- [Deployment Practices](#deployment-practices)
- [Documentation Standards](#documentation-standards)
- [Team Collaboration](#team-collaboration)
- [Common Pitfalls](#common-pitfalls)

## Overview

This guide provides comprehensive best practices for developing applications with the Nexus Framework. Following these guidelines will help you build maintainable, scalable, and secure applications while avoiding common pitfalls.

### Core Principles

1. **Modularity First** - Everything should be a plugin when possible
2. **Clean Architecture** - Maintain clear separation of concerns
3. **Security by Default** - Always consider security implications
4. **Performance Matters** - Optimize for real-world usage patterns
5. **Developer Experience** - Make it easy for others to understand and contribute

## Plugin Development

### Plugin Structure

```
my_plugin/
├── __init__.py           # Plugin package initialization
├── plugin.py             # Main plugin class
├── manifest.json         # Plugin metadata
├── models/               # Data models
│   ├── __init__.py
│   └── entities.py
├── services/             # Business logic
│   ├── __init__.py
│   └── core_service.py
├── api/                  # API endpoints
│   ├── __init__.py
│   ├── routes.py
│   └── schemas.py
├── repositories/         # Data access layer
│   ├── __init__.py
│   └── data_repository.py
├── config/               # Configuration
│   ├── __init__.py
│   └── settings.py
├── utils/                # Utility functions
│   ├── __init__.py
│   └── helpers.py
├── tests/                # Plugin tests
│   ├── __init__.py
│   ├── test_services.py
│   └── test_api.py
├── docs/                 # Plugin documentation
│   └── README.md
└── requirements.txt      # Plugin dependencies
```

### Plugin Class Design

```python
# plugin.py
from nexus.plugins import BasePlugin
from nexus.core import inject
from typing import Optional, List, Dict, Any
import logging

class MyPlugin(BasePlugin):
    """
    A well-structured plugin following best practices.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        self.version = "1.0.0"
        self.category = "business"
        self.description = "A comprehensive plugin example"
        
        # Initialize plugin state
        self._initialized = False
        self._config = None
        self._services = {}
        
    async def initialize(self) -> bool:
        """Initialize plugin with proper error handling."""
        try:
            # Load configuration
            self._config = await self._load_configuration()
            
            # Initialize services
            await self._initialize_services()
            
            # Set up database connections
            await self._setup_database()
            
            # Register event handlers
            self._register_event_handlers()
            
            self._initialized = True
            self.logger.info(f"{self.name} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            await self.cleanup()
            return False
    
    async def cleanup(self):
        """Clean up resources on shutdown."""
        try:
            # Close database connections
            await self._close_database_connections()
            
            # Stop background tasks
            await self._stop_background_tasks()
            
            # Clear caches
            await self._clear_caches()
            
            self._initialized = False
            self.logger.info(f"{self.name} cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_api_routes(self):
        """Return API routes with proper versioning."""
        from .api import routes
        return routes.get_router(self._config)
    
    def get_dependencies(self) -> List[str]:
        """Declare plugin dependencies."""
        return ["core_auth", "database_adapter"]
    
    def get_permissions(self) -> List[str]:
        """Declare required permissions."""
        return ["data.read", "data.write", "api.access"]
```

### Service Layer Pattern

```python
# services/core_service.py
from typing import Optional, List, Dict, Any
from nexus.core import Service, inject, transactional
from ..repositories import DataRepository
from ..models import Entity
import asyncio

class CoreService(Service):
    """
    Service layer implementing business logic.
    """
    
    def __init__(self, repository: DataRepository):
        self.repository = repository
        self._cache = {}
        
    @transactional
    async def create_entity(self, data: Dict[str, Any]) -> Entity:
        """
        Create a new entity with validation and business rules.
        """
        # Validate input
        validated_data = await self._validate_create_data(data)
        
        # Apply business rules
        processed_data = await self._apply_business_rules(validated_data)
        
        # Check for duplicates
        if await self._check_duplicate(processed_data):
            raise ValueError("Duplicate entity detected")
        
        # Create entity
        entity = await self.repository.create(processed_data)
        
        # Trigger events
        await self._publish_event("entity.created", entity)
        
        # Invalidate cache
        await self._invalidate_cache()
        
        return entity
    
    async def get_entity(self, entity_id: str, use_cache: bool = True) -> Optional[Entity]:
        """
        Retrieve entity with caching support.
        """
        if use_cache and entity_id in self._cache:
            return self._cache[entity_id]
        
        entity = await self.repository.get(entity_id)
        
        if entity and use_cache:
            self._cache[entity_id] = entity
            
        return entity
    
    async def update_entity(self, entity_id: str, data: Dict[str, Any]) -> Entity:
        """
        Update entity with optimistic locking.
        """
        # Get current entity
        current = await self.get_entity(entity_id, use_cache=False)
        if not current:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Check version for optimistic locking
        if "version" in data and data["version"] != current.version:
            raise ValueError("Entity has been modified by another process")
        
        # Validate and update
        validated_data = await self._validate_update_data(data)
        updated = await self.repository.update(entity_id, validated_data)
        
        # Update cache
        self._cache[entity_id] = updated
        
        # Trigger events
        await self._publish_event("entity.updated", updated)
        
        return updated
```

### Repository Pattern

```python
# repositories/data_repository.py
from typing import Optional, List, Dict, Any
from nexus.database import Repository, Query
from ..models import Entity

class DataRepository(Repository):
    """
    Repository for data access with query optimization.
    """
    
    def __init__(self, db_adapter):
        super().__init__(db_adapter)
        self.collection = "entities"
        
    async def create(self, data: Dict[str, Any]) -> Entity:
        """Create entity with automatic timestamps."""
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        data["version"] = 1
        
        result = await self.db.insert(self.collection, data)
        return Entity(**result)
    
    async def get(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID with field projection."""
        result = await self.db.find_one(
            self.collection,
            {"_id": entity_id},
            projection=self._get_projection()
        )
        return Entity(**result) if result else None
    
    async def find(self, filters: Dict[str, Any], 
                   page: int = 1, 
                   limit: int = 20) -> List[Entity]:
        """
        Find entities with pagination and sorting.
        """
        query = Query(self.collection)\
            .filter(filters)\
            .sort([("created_at", -1)])\
            .skip((page - 1) * limit)\
            .limit(limit)
        
        results = await self.db.execute_query(query)
        return [Entity(**r) for r in results]
    
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Entity:
        """Update with version increment."""
        data["updated_at"] = datetime.utcnow()
        
        result = await self.db.update_one(
            self.collection,
            {"_id": entity_id},
            {
                "$set": data,
                "$inc": {"version": 1}
            }
        )
        
        return await self.get(entity_id)
    
    async def delete(self, entity_id: str) -> bool:
        """Soft delete with audit trail."""
        return await self.db.update_one(
            self.collection,
            {"_id": entity_id},
            {
                "$set": {
                    "deleted": True,
                    "deleted_at": datetime.utcnow()
                }
            }
        )
```

## Code Organization

### Project Structure

```
nexus-app/
├── app/                      # Application code
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   └── dependencies.py      # Dependency injection setup
├── plugins/                  # Plugin directory
│   ├── business/            # Business logic plugins
│   ├── integration/         # Integration plugins
│   └── utils/               # Utility plugins
├── core/                     # Core application logic
│   ├── __init__.py
│   ├── models/              # Shared models
│   ├── services/            # Shared services
│   └── utils/               # Shared utilities
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                  # Utility scripts
│   ├── migrate.py
│   ├── seed.py
│   └── deploy.sh
├── config/                   # Configuration files
│   ├── config.yaml
│   ├── config.dev.yaml
│   └── config.prod.yaml
├── docker/                   # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                     # Documentation
├── .env.example             # Environment variables example
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration
└── README.md               # Project documentation
```

### Import Organization

```python
# Standard library imports first
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party imports
import asyncio
import aiohttp
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

# Nexus framework imports
from nexus.core import Plugin, Service
from nexus.database import Repository
from nexus.auth import require_auth

# Local application imports
from ..models import User, Product
from ..services import UserService
from ..utils import helpers
```

## Architecture Patterns

### Dependency Injection

```python
# dependencies.py
from nexus.core import Container, Singleton, Scoped
from .services import UserService, ProductService
from .repositories import UserRepository, ProductRepository

def configure_dependencies(container: Container):
    """Configure dependency injection container."""
    
    # Register repositories
    container.register(UserRepository, lifetime=Singleton)
    container.register(ProductRepository, lifetime=Singleton)
    
    # Register services
    container.register(UserService, lifetime=Scoped)
    container.register(ProductService, lifetime=Scoped)
    
    # Register factories
    container.register_factory(
        "db_connection",
        lambda: create_database_connection(),
        lifetime=Singleton
    )
```

### Event-Driven Architecture

```python
# events/handlers.py
from nexus.events import EventHandler, subscribe
from typing import Dict, Any

class OrderEventHandler(EventHandler):
    """Handle order-related events."""
    
    @subscribe("order.created")
    async def on_order_created(self, event_data: Dict[str, Any]):
        """Process new order creation."""
        order_id = event_data["order_id"]
        
        # Send confirmation email
        await self.email_service.send_order_confirmation(order_id)
        
        # Update inventory
        await self.inventory_service.reserve_items(event_data["items"])
        
        # Trigger analytics
        await self.analytics_service.track_order(order_id)
    
    @subscribe("order.cancelled")
    async def on_order_cancelled(self, event_data: Dict[str, Any]):
        """Handle order cancellation."""
        order_id = event_data["order_id"]
        
        # Release inventory
        await self.inventory_service.release_items(order_id)
        
        # Process refund
        await self.payment_service.process_refund(order_id)
        
        # Notify customer
        await self.notification_service.send_cancellation_notice(order_id)
```

### CQRS Pattern

```python
# cqrs/commands.py
from nexus.cqrs import Command, CommandHandler
from pydantic import BaseModel

class CreateOrderCommand(BaseModel):
    """Command to create a new order."""
    customer_id: str
    items: List[Dict[str, Any]]
    shipping_address: Dict[str, str]

class CreateOrderHandler(CommandHandler):
    """Handle order creation command."""
    
    async def handle(self, command: CreateOrderCommand) -> str:
        """Execute order creation."""
        # Validate customer
        customer = await self.customer_service.get(command.customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        # Validate items
        await self.inventory_service.validate_availability(command.items)
        
        # Calculate pricing
        total = await self.pricing_service.calculate_total(command.items)
        
        # Create order
        order = await self.order_service.create({
            "customer_id": command.customer_id,
            "items": command.items,
            "total": total,
            "shipping_address": command.shipping_address
        })
        
        # Publish event
        await self.event_bus.publish("order.created", order.to_dict())
        
        return order.id

# cqrs/queries.py
from nexus.cqrs import Query, QueryHandler

class GetOrderDetailsQuery(BaseModel):
    """Query for order details."""
    order_id: str
    include_history: bool = False

class GetOrderDetailsHandler(QueryHandler):
    """Handle order details query."""
    
    async def handle(self, query: GetOrderDetailsQuery) -> Dict[str, Any]:
        """Retrieve order details."""
        # Get from read model (optimized for queries)
        order = await self.read_repository.get_order(query.order_id)
        
        if query.include_history:
            order["history"] = await self.read_repository.get_order_history(query.order_id)
        
        return order
```

## Performance Optimization

### Caching Strategies

```python
# caching/strategies.py
from nexus.cache import Cache, cache_key, cache_aside
from typing import Optional, Any
import hashlib
import json

class SmartCache:
    """Intelligent caching with multiple strategies."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
        self.default_ttl = 300  # 5 minutes
        
    @cache_aside(ttl=600)
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Cache-aside pattern for user profiles."""
        # This will only be called if not in cache
        return await self.user_repository.get_profile(user_id)
    
    async def get_with_refresh(self, key: str, 
                               fetch_func, 
                               ttl: int = None,
                               refresh_ttl: int = None) -> Any:
        """
        Get with background refresh strategy.
        """
        ttl = ttl or self.default_ttl
        refresh_ttl = refresh_ttl or (ttl * 0.8)
        
        # Try to get from cache
        cached = await self.cache.get(key)
        
        if cached:
            # Check if needs refresh
            remaining_ttl = await self.cache.ttl(key)
            if remaining_ttl < refresh_ttl:
                # Trigger background refresh
                asyncio.create_task(self._refresh_cache(key, fetch_func, ttl))
            return cached["data"]
        
        # Not in cache, fetch and store
        data = await fetch_func()
        await self.cache.set(key, {"data": data}, ttl=ttl)
        return data
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        keys = await self.cache.keys(pattern)
        if keys:
            await self.cache.delete_many(keys)
    
    def generate_cache_key(self, prefix: str, **params) -> str:
        """Generate consistent cache keys."""
        # Sort parameters for consistency
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        
        # Create hash for long keys
        if len(param_str) > 200:
            param_hash = hashlib.md5(param_str.encode()).hexdigest()
            return f"{prefix}:{param_hash}"
        
        return f"{prefix}:{param_str}"
```

### Database Query Optimization

```python
# optimization/database.py
from nexus.database import QueryOptimizer, Index
from typing import List, Dict, Any

class DatabaseOptimizer:
    """Database query optimization strategies."""
    
    async def optimize_query(self, collection: str, 
                            query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize query before execution."""
        # Analyze query
        analysis = await self.analyze_query(collection, query)
        
        # Suggest indexes
        if not analysis["uses_index"]:
            suggested_index = self.suggest_index(query)
            self.logger.warning(f"Query on {collection} could benefit from index: {suggested_index}")
        
        # Add query hints
        if analysis["estimated_docs"] > 10000:
            query["$hint"] = self.get_optimal_index(collection, query)
        
        return query
    
    async def batch_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Batch multiple operations for efficiency."""
        batches = []
        current_batch = []
        
        for op in operations:
            current_batch.append(op)
            
            # Execute batch when size limit reached
            if len(current_batch) >= 100:
                batches.append(current_batch)
                current_batch = []
        
        if current_batch:
            batches.append(current_batch)
        
        # Execute batches in parallel
        results = await asyncio.gather(*[
            self.execute_batch(batch) for batch in batches
        ])
        
        # Flatten results
        return [item for batch_result in results for item in batch_result]
    
    async def use_aggregation_pipeline(self, collection: str, 
                                      filters: Dict[str, Any],
                                      group_by: str) -> List[Dict[str, Any]]:
        """Use aggregation pipeline for complex queries."""
        pipeline = [
            {"$match": filters},
            {
                "$group": {
                    "_id": f"${group_by}",
                    "count": {"$sum": 1},
                    "avg_value": {"$avg": "$value"},
                    "max_value": {"$max": "$value"},
                    "min_value": {"$min": "$value"}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]
        
        return await self.db.aggregate(collection, pipeline)
```

### Async Processing

```python
# async/processing.py
from nexus.async_utils import RateLimiter, CircuitBreaker, retry
import asyncio
from typing import List, Any

class AsyncProcessor:
    """Efficient async processing patterns."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(calls=100, period=1)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
    async def process_parallel(self, items: List[Any], 
                              processor_func,
                              max_concurrent: int = 10) -> List[Any]:
        """Process items in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_limit(item):
            async with semaphore:
                return await processor_func(item)
        
        tasks = [process_with_limit(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    @retry(max_attempts=3, backoff_factor=2)
    async def process_with_retry(self, func, *args, **kwargs):
        """Process with automatic retry on failure."""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Processing failed: {e}, retrying...")
            raise
    
    async def process_stream(self, stream, processor_func, 
                           buffer_size: int = 100):
        """Process streaming data efficiently."""
        buffer = []
        
        async for item in stream:
            buffer.append(item)
            
            if len(buffer) >= buffer_size:
                # Process buffer
                await self.process_batch(buffer, processor_func)
                buffer = []
        
        # Process remaining items
        if buffer:
            await self.process_batch(buffer, processor_func)
    
    async def process_with_circuit_breaker(self, func, *args, **kwargs):
        """Use circuit breaker pattern for external calls."""
        return await self.circuit_breaker.call(func, *args, **kwargs)
```

## Security Best Practices

### Input Validation

```python
# security/validation.py
from pydantic import BaseModel, Field, validator
from typing import Optional
import re
import bleach

class SecureInputValidator:
    """Comprehensive input validation."""
    
    @staticmethod
    def sanitize_html(html: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        allowed_attributes = {}
        
        return bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    
    @staticmethod
    def validate_sql_input(value: str) -> str:
        """Validate input to prevent SQL injection."""
        # Use parameterized queries instead of this
        dangerous_patterns = [
            r"(;|--|\*|union|select|insert|update|delete|drop|create|alter)",
            r"(exec|execute|script|javascript|eval)"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous input detected")
        
        return value
    
    @staticmethod
    def validate_file_path(path: str) -> str:
        """Validate file paths to prevent directory traversal."""
        # Remove any directory traversal attempts
        cleaned = os.path.normpath(path)
        
        if ".." in cleaned or cleaned.startswith("/"):
            raise ValueError("Invalid file path")
        
        return cleaned

class SecureUserInput(BaseModel):
    """Secure user input model with validation."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8)
    age: Optional[int] = Field(None, ge=0, le=150)
    bio: Optional[str] = Field(None, max_length=500)
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username contains invalid characters")
        return v
    
    @validator("password")
    def validate_password(cls, v):
        """Enforce password complexity."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain special character")
        return v
    
    @validator("bio")
    def sanitize_bio(cls, v):
        """Sanitize bio HTML."""
        if v:
            return SecureInputValidator.sanitize_html(v)
        return v
```

### Authentication & Authorization

```python
# security/auth.py
from nexus.auth import Auth, Permission, Role
from typing import List, Optional
import jwt
import bcrypt

class SecureAuthService:
    """Secure authentication service."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.token_expiry = 3600  # 1 hour
        self.refresh_expiry = 604800  # 7 days
        
    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with rate limiting."""
        # Check rate limit
        if await self.is_rate_limited(username):
            raise ValueError("Too many login attempts")
        
        # Get user
        user = await self.user_repository.get_by_username(username)
        if not user:
            # Log failed attempt
            await self.log_failed_attempt(username)
            return None
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            await self.log_failed_attempt(username)
            return None
        
        # Check if account is locked
        if user.locked:
            raise ValueError("Account is locked")
        
        # Generate tokens
        access_token = self.generate_token(user.id, "access")
        refresh_token = self.generate_token(user.id, "refresh")
        
        # Log successful login
        await self.log_successful_login(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode(), hash.encode())
    
    def generate_token(self, user_id: str, token_type: str) -> str:
        """Generate JWT token."""
        expiry = self.token_expiry if token_type == "access" else self.refresh_expiry
        
        payload = {
            "sub": user_id,
            "type": token_type,
            "exp": datetime.utcnow() + timedelta(seconds=expiry),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # Unique token ID
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        user = await self.user_repository.get(user_id)
        if not user:
            return False
        
        # Check direct permissions
        if permission in user.permissions:
            return True
        
        # Check role permissions
        for role in user.roles:
            role_obj = await self.role_repository.get(role)
            if role_obj and permission in role_obj.permissions:
                return True
        
        return False
```

### Data Protection

```python
# security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class DataProtection:
    """Data encryption and protection."""
    
    def __init__(self, master_key: str):
        self.cipher = self._create_cipher(master_key)
        
    def _create_cipher(self, master_key: str) -> Fernet:
        """Create encryption cipher from master key."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stable_salt',  # Use proper salt management
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    def mask_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask personally identifiable information."""
        masked = data.copy()
        
        # Mask email
        if "email" in masked:
            email = masked["email"]
            parts = email.split("@")
            if len(parts) == 2:
                masked["email"] = f"{parts[0][:2]}***@{parts[1]}"
        
        # Mask phone
        if "phone" in masked:
            phone = masked["phone"]
            masked["phone"] = f"***-***-{phone[-4:]}"
        
        # Mask SSN
        if "ssn" in masked:
            ssn = masked["ssn"]
            masked["ssn"] = f"***