"""
Basic integration tests for Nexus framework.

These tests verify that different components of the framework work together
correctly in an integrated environment.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from nexus import BasePlugin, create_nexus_app
from nexus.config import create_default_config
from nexus.core import EventBus, PluginManager, ServiceRegistry


class TestIntegration:
    """Test basic integration scenarios."""

    def test_app_startup_and_health_check(self):
        """Test that app starts up correctly and health endpoint works."""
        config = create_default_config()
        config.plugins.auto_load = False  # Disable plugin auto-loading for test

        app = create_nexus_app(title="Integration Test App", version="1.0.0-test", config=config)

        client = TestClient(app.app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "app" in health_data
        assert "plugins" in health_data

    def test_system_info_endpoint(self):
        """Test system info endpoint returns expected data."""
        app = create_nexus_app(title="Test App")
        client = TestClient(app.app)

        response = client.get("/api/system/info")
        assert response.status_code == 200

        info_data = response.json()
        assert "app" in info_data
        assert "framework" in info_data
        assert "plugins" in info_data
        assert "services" in info_data

    def test_plugins_list_endpoint(self):
        """Test plugins list endpoint."""
        app = create_nexus_app(title="Test App")
        client = TestClient(app.app)

        response = client.get("/api/plugins")
        assert response.status_code == 200

        plugins_data = response.json()
        assert isinstance(plugins_data, dict)
        assert "plugins" in plugins_data
        assert isinstance(plugins_data["plugins"], list)

    def test_app_configuration_loading(self):
        """Test that app configuration loads correctly."""
        config_dict = {
            "app": {"name": "Custom Test App", "debug": True},
            "cors": {"enabled": True, "origins": ["http://localhost:3000"]},
        }

        app = create_nexus_app(title="Config Test App", config=config_dict)

        assert app.config.app.name == "Custom Test App"
        assert app.config.app.debug == True
        assert app.config.cors.enabled == True
        assert "http://localhost:3000" in app.config.cors.origins


class TestEventSystem:
    """Test event system integration."""

    @pytest.mark.asyncio
    async def test_event_bus_basic_functionality(self):
        """Test basic event bus publish/subscribe functionality."""
        event_bus = EventBus()
        received_events = []

        def event_handler(event):
            received_events.append(event)

        # Subscribe to event
        event_bus.subscribe("test.event", event_handler)

        # Start the event bus processor
        processor_task = asyncio.create_task(event_bus.process_events())

        # Publish event
        await event_bus.publish("test.event", {"message": "test"})

        # Give some time for event processing
        await asyncio.sleep(0.1)

        # Check that event was received
        assert len(received_events) == 1
        assert received_events[0].name == "test.event"
        assert received_events[0].data["message"] == "test"

        # Clean up
        processor_task.cancel()
        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        await event_bus.shutdown()

    @pytest.mark.asyncio
    async def test_service_registry_integration(self):
        """Test service registry functionality."""
        registry = ServiceRegistry()

        # Register a service
        test_service = {"name": "test_service", "value": 42}
        registry.register("test_service", test_service)

        # Retrieve the service
        retrieved_service = registry.get("test_service")
        assert retrieved_service == test_service

        # Check service exists
        assert registry.has_service("test_service")

        # List services
        services = registry.list_services()
        assert "test_service" in services


class TestPluginSystem:
    """Test plugin system integration."""

    def test_plugin_manager_creation(self):
        """Test plugin manager can be created with dependencies."""
        event_bus = EventBus()
        service_registry = ServiceRegistry()

        plugin_manager = PluginManager(event_bus, service_registry)

        assert plugin_manager.event_bus == event_bus
        assert plugin_manager.service_registry == service_registry
        assert isinstance(plugin_manager._plugins, dict)
        assert isinstance(plugin_manager._plugin_info, dict)

    def test_plugin_base_class_instantiation(self):
        """Test that BasePlugin can be instantiated correctly."""

        class TestPluginImpl(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = "test_plugin"
                self.version = "1.0.0"
                self.description = "Test plugin"
                self.author = "Test Author"
                self.category = "test"

            async def initialize(self):
                pass

            async def shutdown(self):
                pass

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        plugin = TestPluginImpl()

        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.description == "Test plugin"
        assert plugin.enabled == True

    @pytest.mark.asyncio
    async def test_plugin_lifecycle_methods(self):
        """Test plugin lifecycle methods work correctly."""

        class TestPluginImpl(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = "lifecycle_test_plugin"
                self.version = "1.0.0"
                self.description = "Test plugin for lifecycle"
                self.author = "Test Author"
                self.category = "test"
                self.initialized = False
                self.shutdown_called = False

            async def initialize(self):
                self.initialized = True

            async def shutdown(self):
                self.shutdown_called = True

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        plugin = TestPluginImpl()

        # Test initialization
        await plugin.initialize()
        assert plugin.initialized == True

        # Test health check
        health = await plugin.health_check()
        # Health check returns a HealthStatus object, not dict
        assert hasattr(health, "healthy")
        assert hasattr(health, "message")

        # Test shutdown
        await plugin.shutdown()
        assert plugin.shutdown_called == True


class TestAppWithComponents:
    """Test app integration with various components."""

    def test_app_with_event_bus(self):
        """Test that app correctly initializes with event bus."""
        app = create_nexus_app(title="Event Bus Test")

        assert app.event_bus is not None
        assert hasattr(app.event_bus, "publish")
        assert hasattr(app.event_bus, "subscribe")

    def test_app_with_service_registry(self):
        """Test that app correctly initializes with service registry."""
        app = create_nexus_app(title="Service Registry Test")

        assert app.service_registry is not None
        assert hasattr(app.service_registry, "register")
        assert hasattr(app.service_registry, "get")

    def test_app_with_plugin_manager(self):
        """Test that app correctly initializes with plugin manager."""
        app = create_nexus_app(title="Plugin Manager Test")

        assert app.plugin_manager is not None
        assert hasattr(app.plugin_manager, "load_plugin")
        assert hasattr(app.plugin_manager, "get_loaded_plugins")

    @pytest.mark.asyncio
    async def test_app_event_emission(self):
        """Test that app can emit events correctly."""
        app = create_nexus_app(title="Event Emission Test")

        received_events = []

        def event_handler(event):
            received_events.append(event)

        # Subscribe to app events
        app.event_bus.subscribe("test.app.event", event_handler)

        # Start the event bus processor
        processor_task = asyncio.create_task(app.event_bus.process_events())

        # Emit event through app
        await app.emit_event("test.app.event", {"test": "data"})

        # Give some time for event processing
        await asyncio.sleep(0.1)

        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].name == "test.app.event"
        assert received_events[0].data["test"] == "data"

        # Clean up
        processor_task.cancel()
        try:
            await processor_task
        except asyncio.CancelledError:
            pass


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_app_handles_invalid_config_gracefully(self):
        """Test app handles invalid configuration gracefully."""
        # This should not raise an exception
        app = create_nexus_app(
            title="Error Test App", config={}  # Empty config should use defaults
        )

        assert app is not None
        assert app.title == "Error Test App"

    def test_missing_endpoints_return_404(self):
        """Test that missing endpoints return proper 404."""
        app = create_nexus_app(title="404 Test App")
        client = TestClient(app.app)

        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404

    def test_health_endpoint_always_available(self):
        """Test that health endpoint is always available."""
        app = create_nexus_app(title="Health Test App")
        client = TestClient(app.app)

        # Health should work even with minimal config
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
