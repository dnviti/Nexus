"""
Test configuration and shared fixtures for Nexus framework tests.

This file contains pytest fixtures and configuration that are shared
across all test modules in the test suite.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import nexus
from nexus import BasePlugin, create_nexus_app
from nexus.config import AppConfig, create_default_config
from nexus.core import EventBus, PluginManager, ServiceRegistry


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config() -> AppConfig:
    """Mock configuration for tests."""
    config = create_default_config()
    config.app.debug = True
    config.app.name = "Test Nexus App"
    config.auth.secret_key = "test-secret-key"
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

    async def initialize(self) -> None:
        """Initialize the test plugin."""
        self.initialized = True

    async def shutdown(self) -> None:
        """Shutdown the test plugin."""
        self.shutdown_called = True

    def get_api_routes(self):
        """Get API routes for this plugin."""
        return []

    def get_database_schema(self):
        """Get database schema for this plugin."""
        return {}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the test plugin."""
        return {
            "status": "healthy",
            "initialized": self.initialized,
            "details": "Test plugin is working correctly",
        }


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

# Configure pytest to handle async tests
pytest.mark.asyncio = pytest.mark.asyncio

# Test environment variables
import os

os.environ.setdefault("NEXUS_ENV", "testing")
os.environ.setdefault("NEXUS_DEBUG", "true")
