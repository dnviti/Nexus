# Nexus Framework Testing Guide

## Table of Contents
- [Overview](#overview)
- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [End-to-End Testing](#end-to-end-testing)
- [Plugin Testing](#plugin-testing)
- [API Testing](#api-testing)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Database Testing](#database-testing)
- [Mock and Fixtures](#mock-and-fixtures)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)
- [Testing Tools](#testing-tools)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Nexus Framework provides comprehensive testing utilities and patterns to ensure your applications and plugins are robust, reliable, and maintainable. This guide covers all aspects of testing in the Nexus ecosystem.

### Testing Levels

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete user workflows
4. **Performance Tests** - Test system performance and scalability
5. **Security Tests** - Test security vulnerabilities

### Testing Stack

- **pytest** - Primary testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage
- **pytest-mock** - Mocking utilities
- **httpx** - API testing
- **factory_boy** - Test data generation
- **faker** - Fake data generation
- **locust** - Performance testing

## Testing Philosophy

### Core Principles

1. **Test Early, Test Often** - Write tests alongside code
2. **Test in Isolation** - Each test should be independent
3. **Test Behavior, Not Implementation** - Focus on what, not how
4. **Keep Tests Simple** - Tests should be easy to understand
5. **Fast Feedback** - Tests should run quickly
6. **Comprehensive Coverage** - Aim for high code coverage

## Test Structure

### Project Test Layout

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_repositories.py
│   └── test_utils.py
├── integration/            # Integration tests
│   ├── test_api.py
│   ├── test_database.py
│   ├── test_auth.py
│   └── test_plugins.py
├── e2e/                    # End-to-end tests
│   ├── test_user_flows.py
│   ├── test_admin_flows.py
│   └── test_plugin_flows.py
├── performance/            # Performance tests
│   ├── locustfile.py
│   └── stress_tests.py
├── security/               # Security tests
│   ├── test_auth_security.py
│   ├── test_input_validation.py
│   └── test_vulnerabilities.py
├── fixtures/               # Test data and fixtures
│   ├── users.json
│   ├── products.json
│   └── test_data.py
└── utils/                  # Test utilities
    ├── helpers.py
    ├── factories.py
    └── mocks.py
```

## Unit Testing

### Basic Unit Test

```python
# tests/unit/test_services.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services import UserService
from app.models import User
from app.exceptions import ValidationError

class TestUserService:
    """Test UserService functionality."""
    
    @pytest.fixture
    def user_service(self):
        """Create UserService instance with mocked dependencies."""
        repository = Mock()
        cache = Mock()
        event_bus = Mock()
        return UserService(repository, cache, event_bus)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id="123",
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )
    
    def test_create_user_success(self, user_service, sample_user):
        """Test successful user creation."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePass123!"
        }
        user_service.repository.create.return_value = sample_user
        user_service.repository.find_by_email.return_value = None
        
        # Act
        result = user_service.create_user(user_data)
        
        # Assert
        assert result.username == sample_user.username
        user_service.repository.create.assert_called_once()
        user_service.event_bus.publish.assert_called_with(
            "user.created", 
            {"user_id": sample_user.id}
        )
    
    def test_create_user_duplicate_email(self, user_service):
        """Test user creation with duplicate email."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "existing@example.com",
            "password": "SecurePass123!"
        }
        user_service.repository.find_by_email.return_value = Mock()
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            user_service.create_user(user_data)
        
        assert "Email already exists" in str(exc.value)
        user_service.repository.create.assert_not_called()
    
    @pytest.mark.parametrize("invalid_email", [
        "invalid",
        "@example.com",
        "user@",
        "user@.com",
        "",
        None
    ])
    def test_create_user_invalid_email(self, user_service, invalid_email):
        """Test user creation with invalid email formats."""
        user_data = {
            "username": "testuser",
            "email": invalid_email,
            "password": "SecurePass123!"
        }
        
        with pytest.raises(ValidationError):
            user_service.create_user(user_data)
```

### Async Unit Testing

```python
# tests/unit/test_async_services.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestAsyncService:
    """Test async service functionality."""
    
    @pytest.fixture
    async def async_service(self):
        """Create async service with mocked dependencies."""
        service = AsyncDataService()
        service.client = AsyncMock()
        service.cache = AsyncMock()
        return service
    
    async def test_fetch_data_with_cache_hit(self, async_service):
        """Test data fetching when cache hit occurs."""
        # Arrange
        cached_data = {"id": "123", "value": "cached"}
        async_service.cache.get.return_value = cached_data
        
        # Act
        result = await async_service.fetch_data("123")
        
        # Assert
        assert result == cached_data
        async_service.cache.get.assert_called_once_with("data:123")
        async_service.client.fetch.assert_not_called()
    
    async def test_fetch_data_with_cache_miss(self, async_service):
        """Test data fetching when cache miss occurs."""
        # Arrange
        fetched_data = {"id": "123", "value": "fresh"}
        async_service.cache.get.return_value = None
        async_service.client.fetch.return_value = fetched_data
        
        # Act
        result = await async_service.fetch_data("123")
        
        # Assert
        assert result == fetched_data
        async_service.cache.get.assert_called_once_with("data:123")
        async_service.client.fetch.assert_called_once_with("123")
        async_service.cache.set.assert_called_once_with(
            "data:123", 
            fetched_data, 
            ttl=300
        )
    
    async def test_concurrent_requests(self, async_service):
        """Test handling of concurrent requests."""
        # Arrange
        async_service.client.fetch.side_effect = [
            {"id": "1", "value": "one"},
            {"id": "2", "value": "two"},
            {"id": "3", "value": "three"}
        ]
        async_service.cache.get.return_value = None
        
        # Act
        results = await asyncio.gather(
            async_service.fetch_data("1"),
            async_service.fetch_data("2"),
            async_service.fetch_data("3")
        )
        
        # Assert
        assert len(results) == 3
        assert results[0]["value"] == "one"
        assert results[1]["value"] == "two"
        assert results[2]["value"] == "three"
```

## Integration Testing

### Database Integration Tests

```python
# tests/integration/test_database.py
import pytest
from nexus.database import DatabaseAdapter
from app.repositories import UserRepository
from app.models import User

@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration."""
    
    @pytest.fixture
    async def db_adapter(self, test_database_url):
        """Create database adapter for testing."""
        adapter = DatabaseAdapter(test_database_url)
        await adapter.connect()
        yield adapter
        await adapter.disconnect()
    
    @pytest.fixture
    async def user_repository(self, db_adapter):
        """Create user repository."""
        return UserRepository(db_adapter)
    
    async def test_user_crud_operations(self, user_repository):
        """Test complete CRUD operations for users."""
        # Create
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password"
        }
        created_user = await user_repository.create(user_data)
        assert created_user.id is not None
        assert created_user.username == "testuser"
        
        # Read
        fetched_user = await user_repository.get(created_user.id)
        assert fetched_user.email == "test@example.com"
        
        # Update
        updated_data = {"email": "updated@example.com"}
        updated_user = await user_repository.update(
            created_user.id, 
            updated_data
        )
        assert updated_user.email == "updated@example.com"
        
        # Delete
        deleted = await user_repository.delete(created_user.id)
        assert deleted is True
        
        # Verify deletion
        deleted_user = await user_repository.get(created_user.id)
        assert deleted_user is None
    
    async def test_transaction_rollback(self, db_adapter):
        """Test transaction rollback on error."""
        async with db_adapter.transaction() as tx:
            try:
                await tx.execute("INSERT INTO users (username) VALUES ('test')")
                # Force an error
                raise Exception("Simulated error")
            except Exception:
                await tx.rollback()
        
        # Verify rollback
        result = await db_adapter.fetch_one(
            "SELECT * FROM users WHERE username = 'test'"
        )
        assert result is None
    
    async def test_connection_pool(self, db_adapter):
        """Test database connection pooling."""
        tasks = []
        for i in range(20):
            tasks.append(
                db_adapter.fetch_one(f"SELECT {i} as num")
            )
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 20
        
        # Check pool statistics
        pool_stats = db_adapter.get_pool_stats()
        assert pool_stats["size"] <= pool_stats["max_size"]
```

### API Integration Tests

```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.integration
class TestAPIIntegration:
    """Test API endpoint integration."""
    
    @pytest.fixture
    async def client(self):
        """Create async HTTP client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    async def auth_headers(self, client):
        """Get authentication headers."""
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    async def test_complete_user_flow(self, client, auth_headers):
        """Test complete user registration and profile flow."""
        # Register new user
        register_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=register_data)
        assert response.status_code == 201
        user_id = response.json()["user"]["id"]
        
        # Login with new user
        login_response = await client.post(
            "/api/auth/login",
            json={
                "username": "newuser",
                "password": "SecurePass123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get user profile
        profile_response = await client.get(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == "newuser"
        
        # Update profile
        update_response = await client.put(
            f"/api/users/{user_id}",
            json={"bio": "Test bio"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["bio"] == "Test bio"
        
        # Delete account
        delete_response = await client.delete(
            f"/api/users/{user_id}",
            headers=auth_headers  # Admin required
        )
        assert delete_response.status_code == 204
```

## End-to-End Testing

### E2E Test with Selenium

```python
# tests/e2e/test_user_flows.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.mark.e2e
class TestUserFlows:
    """End-to-end user flow tests."""
    
    @pytest.fixture
    def driver(self):
        """Create Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_user_registration_flow(self, driver, base_url):
        """Test complete user registration flow."""
        # Navigate to registration page
        driver.get(f"{base_url}/register")
        
        # Fill registration form
        driver.find_element(By.ID, "username").send_keys("testuser")
        driver.find_element(By.ID, "email").send_keys("test@example.com")
        driver.find_element(By.ID, "password").send_keys("SecurePass123!")
        driver.find_element(By.ID, "confirm_password").send_keys("SecurePass123!")
        
        # Submit form
        driver.find_element(By.ID, "register_button").click()
        
        # Wait for redirect to login
        WebDriverWait(driver, 10).until(
            EC.url_contains("/login")
        )
        
        # Login with new account
        driver.find_element(By.ID, "username").send_keys("testuser")
        driver.find_element(By.ID, "password").send_keys("SecurePass123!")
        driver.find_element(By.ID, "login_button").click()
        
        # Verify dashboard access
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dashboard"))
        )
        
        # Verify username display
        username_element = driver.find_element(By.CLASS_NAME, "username")
        assert username_element.text == "testuser"
    
    def test_plugin_installation_flow(self, driver, base_url, admin_login):
        """Test plugin installation through UI."""
        # Login as admin
        admin_login(driver)
        
        # Navigate to plugin marketplace
        driver.get(f"{base_url}/admin/plugins")
        
        # Search for plugin
        search_box = driver.find_element(By.ID, "plugin_search")
        search_box.send_keys("analytics")
        search_box.submit()
        
        # Wait for results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "plugin-card"))
        )
        
        # Install first plugin
        install_button = driver.find_element(
            By.CSS_SELECTOR, 
            ".plugin-card:first-child .install-button"
        )
        install_button.click()
        
        # Confirm installation
        confirm_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "confirm_install"))
        )
        confirm_button.click()
        
        # Wait for installation to complete
        WebDriverWait(driver, 30).until(
            EC.text_to_be_present_in_element(
                (By.CLASS_NAME, "installation-status"),
                "Installed successfully"
            )
        )
```

## Plugin Testing

### Plugin Test Structure

```python
# plugins/my_plugin/tests/test_plugin.py
import pytest
from nexus.testing import PluginTestCase
from ..plugin import MyPlugin

class TestMyPlugin(PluginTestCase):
    """Test MyPlugin functionality."""
    
    @pytest.fixture
    async def plugin(self):
        """Create plugin instance for testing."""
        plugin = MyPlugin()
        await plugin.initialize()
        yield plugin
        await plugin.cleanup()
    
    async def test_plugin_initialization(self, plugin):
        """Test plugin initializes correctly."""
        assert plugin.initialized is True
        assert plugin.name == "my_plugin"
        assert plugin.version == "1.0.0"
    
    async def test_plugin_api_routes(self, plugin):
        """Test plugin registers API routes."""
        routes = plugin.get_api_routes()
        assert len(routes) > 0
        
        # Test route configuration
        first_route = routes[0]
        assert first_route.prefix == "/api/my_plugin"
        assert len(first_route.routes) > 0
    
    async def test_plugin_dependencies(self, plugin):
        """Test plugin dependencies are satisfied."""
        dependencies = plugin.get_dependencies()
        
        for dep in dependencies:
            assert await self.is_plugin_loaded(dep), f"Dependency {dep} not loaded"
    
    async def test_plugin_configuration(self, plugin):
        """Test plugin configuration loading."""
        config = plugin.get_configuration()
        
        assert config is not None
        assert "enabled" in config
        assert config["enabled"] is True
    
    async def test_plugin_event_handling(self, plugin):
        """Test plugin event handling."""
        # Emit test event
        await self.emit_event("test.event", {"data": "test"})
        
        # Wait for handler
        await asyncio.sleep(0.1)
        
        # Verify handler was called
        assert plugin.event_received is True
        assert plugin.last_event_data == {"data": "test"}
```

### Plugin Integration Testing

```python
# plugins/my_plugin/tests/test_integration.py
import pytest
from nexus.testing import create_test_app
from httpx import AsyncClient

@pytest.mark.integration
class TestPluginIntegration:
    """Test plugin integration with framework."""
    
    @pytest.fixture
    async def app(self):
        """Create test application with plugin."""
        app = await create_test_app(
            plugins=["my_plugin"],
            config={
                "database": {"type": "sqlite", "path": ":memory:"},
                "cache": {"type": "memory"}
            }
        )
        yield app
        await app.shutdown()
    
    @pytest.fixture
    async def client(self, app):
        """Create HTTP client for testing."""
        async with AsyncClient(app=app.fastapi_app, base_url="http://test") as client:
            yield client
    
    async def test_plugin_endpoints_available(self, client):
        """Test plugin endpoints are available."""
        response = await client.get("/api/my_plugin/status")
        assert response.status_code == 200
        assert response.json()["status"] == "active"
    
    async def test_plugin_database_operations(self, app):
        """Test plugin database operations."""
        plugin = app.get_plugin("my_plugin")
        
        # Create test data
        result = await plugin.create_entity({
            "name": "Test Entity",
            "value": 100
        })
        assert result["id"] is not None
        
        # Fetch data
        entity = await plugin.get_entity(result["id"])
        assert entity["name"] == "Test Entity"
    
    async def test_plugin_interaction(self, app):
        """Test interaction between plugins."""
        my_plugin = app.get_plugin("my_plugin")
        auth_plugin = app.get_plugin("auth")
        
        # Create user through auth plugin
        user = await auth_plugin.create_user({
            "username": "testuser",
            "password": "password123"
        })
        
        # Use user in my_plugin
        result = await my_plugin.process_user_data(user["id"])
        assert result["processed"] is True
```

## Performance Testing

### Locust Performance Tests

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random
import json

class NexusUser(HttpUser):
    """Simulated Nexus Framework user."""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login when user starts."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(3)
    def get_users(self):
        """Get users list."""
        self.client.get("/api/users", headers=self.headers)
    
    @task(2)
    def get_user_profile(self):
        """Get specific user profile."""
        user_id = random.randint(1, 100)
        self.client.get(f"/api/users/{user_id}", headers=self.headers)
    
    @task(1)
    def create_entity(self):
        """Create new entity."""
        data = {
            "name": f"Entity {random.randint(1, 1000)}",
            "value": random.randint(1, 100)
        }
        self.client.post(
            "/api/entities",
            json=data,
            headers=self.headers
        )
    
    @task(2)
    def search_entities(self):
        """Search entities."""
        query = random.choice(["test", "entity", "data"])
        self.client.get(
            f"/api/entities/search?q={query}",
            headers=self.headers
        )

class AdminUser(HttpUser):
    """Simulated admin user."""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login as admin."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(1)
    def manage_plugins(self):
        """Get plugin list."""
        self.client.get("/api/plugins", headers=self.headers)
    
    @task(1)
    def view_metrics(self):
        """View system metrics."""
        self.client.get("/api/admin/metrics", headers=self.headers)
```

### Load Testing Script

```python
# tests/performance/load_test.py
import asyncio
import aiohttp
import time
from typing import List, Dict, Any

class LoadTester:
    """Load testing utility."""
    
    def __init__(self, base_url: str, concurrent_users: int = 100):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.results = []
    
    async def make_request(self, session: aiohttp.ClientSession, 
                          endpoint: str, method: str = "GET", 
                          **kwargs) -> Dict[str, Any]:
        """Make single request and measure performance."""
        start_time = time.time()
        
        try:
            async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as response:
                await response.text()
                status = response.status
                error = None
        except Exception as e:
            status = 0
            error = str(e)
        
        elapsed = time.time() - start_time
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "elapsed": elapsed,
            "error": error
        }
    
    async def run_test(self, endpoints: List[Dict[str, Any]], 
                      duration: int = 60) -> Dict[str, Any]:
        """Run load test for specified duration."""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            tasks = []
            
            while time.time() - start_time < duration:
                for endpoint in endpoints:
                    task = self.make_request(
                        session,
                        endpoint["path"],
                        endpoint.get("method", "GET"),
                        json=endpoint.get("data"),
                        headers=endpoint.get("headers", {})
                    )
                    tasks.append(task)
                
                # Limit concurrent requests
                if len(tasks) >= self.concurrent_users:
                    results = await asyncio.gather(*tasks)
                    self.results.extend(results)
                    tasks = []
                
                await asyncio.sleep(0.1)
            
            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                self.results.extend(results)
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results."""
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if 200 <= r["status"] < 300)
        failed_requests = sum(1 for r in self.results if r["error"] or r["status"] >= 400)
        
        response_times = [r["elapsed"] for r in self.results if not r["error"]]
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests * 100,
            "average_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
            "requests_per_second": total_requests / 60
        }

# Usage example
async def main():
    tester = LoadTester("http://localhost:8000", concurrent_users=100)
    
    endpoints = [
        {"path": "/api/health", "method": "GET"},
        {"path": "/api/users", "method": "GET"},
        {"path": "/api/entities", "method": "POST", "data": {"name": "test"}}
    ]
    
    results = await tester.run_test(endpoints, duration=60)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## Mock and Fixtures

### Custom Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from nexus.testing import TestDatabase, TestCache
from app.main import create_app

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    db = TestDatabase("postgresql://test_user:test_pass@localhost/test_db")
    await db.create()
    yield db
    await db.destroy()

@pytest.fixture
async def db_session(test_db):
    """Create database session for test."""
    async with test_db.session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_cache():
    """Create test cache instance."""
    cache = TestCache()
    yield cache
    await cache.clear()

@pytest.fixture
async def app(test_db, test_cache):
    """Create test application."""
    app = create_app(
        database=test_db,
        cache=test_cache,
        config={
            "testing": True,
            "debug": True
        }
    )
    await app.startup()
    yield app
    await app.shutdown()

@pytest.fixture
def auth_token(app):
    """Generate auth token for testing."""
    from app.auth import generate_token
    return generate_token(user_id="test_user", roles=["user"])

@pytest.fixture
def admin_token(app):
    """Generate admin token for testing."""
    from app.auth import generate_token
    return generate_token(user_id="admin_user", roles=["admin"])
```

### Factory Pattern for Test Data

```python
# tests/utils/factories.py
import factory
from factory import fuzzy
from datetime import datetime, timedelta
from app.models import User, Product, Order

class UserFactory(factory.Factory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: f"user_{n}")
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.