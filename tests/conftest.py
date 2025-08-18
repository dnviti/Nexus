"""
Test configuration and shared fixtures for Nexus framework tests.

This file contains pytest fixtures and configuration that are shared
across all test modules in the test suite.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

# Configure logging for tests
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger("nexus.core").setLevel(logging.CRITICAL)

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# nexus import removed as unused
from nexus import BasePlugin, create_nexus_app
from nexus.config import AppConfig, create_default_config
from nexus.core import EventBus, PluginManager, ServiceRegistry


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        # Try to get existing loop first
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
    except RuntimeError:
        # Create new loop if none exists or current is closed
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)

    yield loop

    # Clean up
    try:
        # Cancel all running tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                task.cancel()
            # Wait for tasks to be cancelled
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass
    finally:
        if not loop.is_closed():
            loop.close()


@pytest.fixture
def mock_config() -> AppConfig:
    """Mock configuration for tests."""
    config = create_default_config()
    config.app.debug = True
    config.app.name = "Test Nexus App"
    config.auth.jwt_secret = "test-secret-key"
    config.database = None  # Disable database for basic tests
    return config


@pytest.fixture
def test_app_config() -> Dict[str, Any]:
    """Basic test application configuration as dictionary."""
    return {
        "app": {
            "name": "Test App",
            "debug": True,
        },
        "auth": {
            "secret_key": "test-secret-key-for-testing",
        },
        "cors": {
            "enabled": True,
            "origins": ["*"],
        },
        "plugins": {
            "directory": "./test_plugins",
            "auto_load": False,
        },
    }


@pytest.fixture
def nexus_app(mock_config):
    """Create a test Nexus application instance."""
    app = create_nexus_app(
        title="Test Nexus App",
        version="1.0.0-test",
        description="Test application for unit tests",
        config=mock_config,
    )
    return app


@pytest.fixture
def test_client(nexus_app):
    """Create a test client for the Nexus application."""
    return TestClient(nexus_app.app)


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    event_bus = EventBus()
    return event_bus


@pytest.fixture
def mock_service_registry():
    """Mock ServiceRegistry for testing."""
    return ServiceRegistry()


@pytest.fixture
def mock_plugin_manager(mock_event_bus, mock_service_registry):
    """Mock PluginManager for testing."""
    return PluginManager(mock_event_bus, mock_service_registry)


@pytest.fixture
def sample_plugin_metadata():
    """Sample plugin metadata for testing."""
    return {
        "name": "test_plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "Test Author",
        "category": "test",
        "dependencies": [],
        "permissions": [],
        "config_schema": {},
    }


class TestPlugin(BasePlugin):
    """Sample test plugin implementation."""

    def __init__(self, context=None):
        super().__init__()
        # Set metadata after initialization
        self.name = "test_plugin"
        self.version = "1.0.0"
        self.description = "A test plugin for unit tests"
        self.author = "Test Author"
        self.category = "test"
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self) -> bool:
        """Initialize the test plugin."""
        self.initialized = True
        return True

    async def shutdown(self) -> None:
        """Shutdown the test plugin."""
        self.shutdown_called = True

    def get_api_routes(self):
        """Get API routes for this plugin."""
        return []

    def get_database_schema(self):
        """Get database schema for this plugin."""
        return {}

    async def health_check(self):
        """Health check for the test plugin."""
        from nexus.plugins import HealthStatus

        return HealthStatus(healthy=True, message="Test plugin is working correctly")


@pytest.fixture
def test_plugin():
    """Create a test plugin instance."""
    return TestPlugin()


@pytest.fixture
def mock_database_adapter():
    """Mock database adapter for testing."""
    adapter = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.get = AsyncMock()
    adapter.set = AsyncMock()
    adapter.delete = AsyncMock()
    adapter.exists = AsyncMock(return_value=False)
    adapter.list_keys = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def temp_plugin_dir(tmp_path):
    """Create a temporary directory for plugin testing."""
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    # Create a sample plugin structure
    test_plugin_dir = plugin_dir / "test_category" / "test_plugin"
    test_plugin_dir.mkdir(parents=True)

    # Create manifest file
    manifest = test_plugin_dir / "manifest.yaml"
    manifest.write_text(
        """
name: test_plugin
version: 1.0.0
description: A test plugin for unit tests
author: Test Author
category: test_category
dependencies: []
permissions: []
config_schema: {}
"""
    )

    # Create plugin file
    plugin_file = test_plugin_dir / "__init__.py"
    plugin_file.write_text(
        """
from nexus import BasePlugin

class TestPluginImpl(BasePlugin):
    async def initialize(self):
        pass

    async def shutdown(self):
        pass
"""
    )

    return plugin_dir


# Test markers for different test categories
pytest_plugins = []

# Configure pytest to handle async tests automatically
# This ensures that pytest-asyncio is properly configured

# Test environment variables
import os

os.environ.setdefault("NEXUS_ENV", "testing")
os.environ.setdefault("NEXUS_DEBUG", "true")


# Ensure asyncio mode is configured for pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio settings."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    # Ensure asyncio mode is set to auto
    if not hasattr(config.option, "asyncio_mode"):
        config.option.asyncio_mode = "auto"


# Auto-apply asyncio marker to async test functions
def pytest_collection_modifyitems(config, items):
    """Automatically mark async test functions with asyncio marker."""
    for item in items:
        # Check if the test function is a coroutine function
        if hasattr(item, "function") and asyncio.iscoroutinefunction(item.function):
            # Add asyncio marker if not already present
            if not any(marker.name == "asyncio" for marker in item.iter_markers()):
                item.add_marker(pytest.mark.asyncio)

        # Also check for async methods in test classes
        if hasattr(item, "obj") and hasattr(item.obj, "__self__"):
            test_method = getattr(item.obj.__self__.__class__, item.obj.__name__, None)
            if test_method and asyncio.iscoroutinefunction(test_method):
                if not any(marker.name == "asyncio" for marker in item.iter_markers()):
                    item.add_marker(pytest.mark.asyncio)


# Pytest hook to ensure proper async test handling
def pytest_runtest_setup(item):
    """Setup hook for each test item to ensure proper async handling."""
    if any(marker.name == "asyncio" for marker in item.iter_markers()):
        # Ensure we have a proper event loop for async tests
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                # Create a new loop if the current one is closed
                policy = asyncio.get_event_loop_policy()
                loop = policy.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No loop exists, create one
            policy = asyncio.get_event_loop_policy()
            loop = policy.new_event_loop()
            asyncio.set_event_loop(loop)


# Debug fixture to help troubleshoot async issues
@pytest.fixture(autouse=True)
def debug_async_environment():
    """Debug fixture to log async environment state."""
    import logging

    logger = logging.getLogger("test.async")

    try:
        loop = asyncio.get_event_loop()
        logger.debug(
            f"Event loop: {loop}, running: {loop.is_running()}, closed: {loop.is_closed()}"
        )
    except RuntimeError as e:
        logger.debug(f"No event loop available: {e}")

    yield

    # Cleanup after test
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            # Cancel any remaining tasks
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending:
                for task in pending:
                    if not task.cancelled():
                        task.cancel()
    except Exception as e:
        logger.debug(f"Cleanup error: {e}")
