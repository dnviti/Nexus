"""
Comprehensive unit tests for the Nexus plugins module.

Tests cover BasePlugin, plugin decorators, plugin types, validation, and all plugin-related functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus.plugins import (
    AnalyticsPlugin,
    BasePlugin,
    BusinessPlugin,
    HealthStatus,
    IntegrationPlugin,
    NotificationPlugin,
    PluginConfigSchema,
    PluginConfigurationError,
    PluginContext,
    PluginDependency,
    PluginDependencyError,
    PluginError,
    PluginHook,
    PluginInitializationError,
    PluginLifecycle,
    PluginMetadata,
    PluginPermission,
    PluginValidator,
    SecurityPlugin,
    StoragePlugin,
    UIPlugin,
    WorkflowPlugin,
    plugin_hook,
    requires_dependency,
    requires_permission,
)


class TestPluginMetadata:
    """Test PluginMetadata class."""

    def test_plugin_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            license="MIT",
            category="test",
            tags=["testing", "example"],
            homepage="https://example.com",
            repository="https://github.com/example/plugin",
            documentation="https://docs.example.com",
            dependencies=["dep1", "dep2"],
            permissions=["read", "write"],
            config_schema={"type": "object"},
            min_nexus_version="2.0.0",
            max_nexus_version="3.0.0",
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A test plugin"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.category == "test"
        assert metadata.tags == ["testing", "example"]
        assert metadata.homepage == "https://example.com"
        assert metadata.repository == "https://github.com/example/plugin"
        assert metadata.documentation == "https://docs.example.com"
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.permissions == ["read", "write"]
        assert metadata.config_schema == {"type": "object"}
        assert metadata.min_nexus_version == "2.0.0"
        assert metadata.max_nexus_version == "3.0.0"

    def test_plugin_metadata_defaults(self):
        """Test plugin metadata with default values."""
        metadata = PluginMetadata(name="simple_plugin", version="1.0.0", author="Author")

        assert metadata.name == "simple_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Author"
        assert metadata.description == ""
        assert metadata.license == "MIT"
        assert metadata.category == "general"
        assert metadata.tags == []
        assert metadata.dependencies == []
        assert metadata.permissions == []
        assert metadata.config_schema == {}


class TestPluginLifecycle:
    """Test PluginLifecycle enum."""

    def test_plugin_lifecycle_values(self):
        """Test plugin lifecycle enum values."""
        assert PluginLifecycle.INITIALIZING.value == "initializing"
        assert PluginLifecycle.RUNNING.value == "running"
        assert PluginLifecycle.STOPPING.value == "stopping"
        assert PluginLifecycle.STOPPED.value == "stopped"
        assert PluginLifecycle.ERROR.value == "error"


class TestPluginContext:
    """Test PluginContext class."""

    def test_plugin_context_creation(self):
        """Test creating plugin context."""
        app_config = {"test": "config"}
        service_registry = MagicMock()
        event_bus = MagicMock()

        context = PluginContext(app_config, service_registry, event_bus)

        assert context.app_config == app_config
        assert context.service_registry == service_registry
        assert context.event_bus == event_bus

    def test_plugin_context_get_service(self):
        """Test getting service from context."""
        service_registry = MagicMock()
        test_service = {"name": "test"}
        service_registry.get.return_value = test_service

        context = PluginContext({}, service_registry, MagicMock())

        result = context.get_service("test_service")
        assert result == test_service
        service_registry.get.assert_called_once_with("test_service")

    def test_plugin_context_get_config(self):
        """Test getting plugin config from context."""
        app_config = {"plugins": {"test_plugin": {"setting": "value"}}}
        context = PluginContext(app_config, MagicMock(), MagicMock())

        config = context.get_config("test_plugin")
        assert config == {"setting": "value"}

    def test_plugin_context_get_config_with_default(self):
        """Test getting plugin config with default value."""
        app_config = {"plugins": {}}
        context = PluginContext(app_config, MagicMock(), MagicMock())

        default_config = {"default": "value"}
        config = context.get_config("nonexistent_plugin", default_config)
        assert config == default_config


class TestPluginDependency:
    """Test PluginDependency class."""

    def test_plugin_dependency_creation(self):
        """Test creating plugin dependency."""
        dep = PluginDependency(name="required_plugin", version=">=1.0.0", optional=False)

        assert dep.name == "required_plugin"
        assert dep.version == ">=1.0.0"
        assert dep.optional == False

    def test_plugin_dependency_defaults(self):
        """Test plugin dependency with defaults."""
        dep = PluginDependency(name="some_plugin")

        assert dep.name == "some_plugin"
        assert dep.version == "*"
        assert dep.optional == False


class TestPluginPermission:
    """Test PluginPermission class."""

    def test_plugin_permission_creation(self):
        """Test creating plugin permission."""
        perm = PluginPermission(name="read_data", description="Read application data")

        assert perm.name == "read_data"
        assert perm.description == "Read application data"

    def test_plugin_permission_defaults(self):
        """Test plugin permission with defaults."""
        perm = PluginPermission(name="some_permission")

        assert perm.name == "some_permission"
        assert perm.description == ""


class TestPluginHook:
    """Test PluginHook class."""

    def test_plugin_hook_creation(self):
        """Test creating plugin hook."""
        hook = PluginHook(name="data_processed", priority=10)

        assert hook.name == "data_processed"
        assert hook.priority == 10

    def test_plugin_hook_defaults(self):
        """Test plugin hook with defaults."""
        hook = PluginHook(name="some_hook")

        assert hook.name == "some_hook"
        assert hook.priority == 0


class TestPluginConfigSchema:
    """Test PluginConfigSchema class."""

    def test_plugin_config_schema_creation(self):
        """Test creating plugin config schema."""
        schema = PluginConfigSchema(
            config_schema={"type": "object", "properties": {"setting": {"type": "string"}}},
            required=["setting"],
        )

        assert schema.config_schema == {
            "type": "object",
            "properties": {"setting": {"type": "string"}},
        }
        assert schema.required == ["setting"]

    def test_plugin_config_schema_defaults(self):
        """Test plugin config schema with defaults."""
        schema = PluginConfigSchema()

        assert schema.config_schema == {}
        assert schema.required == []


class TestPluginDecorators:
    """Test plugin decorators."""

    def test_plugin_hook_decorator(self):
        """Test plugin_hook decorator."""

        @plugin_hook("test_event")
        def test_handler():
            return "handled"

        # Decorator should add metadata to function
        assert hasattr(test_handler, "_nexus_hook")
        assert test_handler._nexus_hook == "test_event"  # type: ignore

    def test_plugin_hook_decorator_with_priority(self):
        """Test plugin_hook decorator with priority."""

        @plugin_hook("priority_event", priority=5)
        def priority_handler():
            return "priority_handled"

        assert hasattr(priority_handler, "_nexus_hook")
        assert hasattr(priority_handler, "_nexus_priority")
        assert priority_handler._nexus_hook == "priority_event"  # type: ignore
        assert priority_handler._nexus_priority == 5  # type: ignore

    def test_requires_permission_decorator(self):
        """Test requires_permission decorator."""

        @requires_permission("admin")
        def admin_function():
            return "admin_action"

        assert hasattr(admin_function, "_required_permission")
        assert admin_function._required_permission == "admin"  # type: ignore

    def test_requires_dependency_decorator(self):
        """Test requires_dependency decorator."""

        @requires_dependency("database")
        def db_function():
            return "db_action"

        assert hasattr(db_function, "_required_dependency")
        assert db_function._required_dependency == "database"  # type: ignore

    def test_requires_dependency_decorator_with_version(self):
        """Test requires_dependency decorator with version."""

        @requires_dependency("cache", version=">=2.0.0")
        def cache_function():
            return "cache_action"

        assert hasattr(cache_function, "_required_dependency")
        assert hasattr(cache_function, "_dependency_version")
        assert cache_function._required_dependency == "cache"  # type: ignore
        assert cache_function._dependency_version == ">=2.0.0"  # type: ignore


class TestHealthStatus:
    """Test HealthStatus class."""

    def test_health_status_creation(self):
        """Test creating health status."""
        components = {"database": {"status": "healthy"}}
        metrics = {"cpu": 50.0}

        status = HealthStatus(
            healthy=True, message="All systems operational", components=components, metrics=metrics
        )

        assert status.healthy == True
        assert status.message == "All systems operational"
        assert status.components == components
        assert status.metrics == metrics
        assert isinstance(status.timestamp, datetime)

    def test_health_status_defaults(self):
        """Test health status with defaults."""
        status = HealthStatus()

        assert status.healthy == True
        assert status.message == "Plugin is running"
        assert status.components == {}
        assert status.metrics == {}


class TestPluginExceptions:
    """Test plugin exception classes."""

    def test_plugin_error(self):
        """Test PluginError exception."""
        error = PluginError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    def test_plugin_initialization_error(self):
        """Test PluginInitializationError exception."""
        error = PluginInitializationError("Initialization failed")
        assert str(error) == "Initialization failed"
        assert isinstance(error, PluginError)

    def test_plugin_configuration_error(self):
        """Test PluginConfigurationError exception."""
        error = PluginConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert isinstance(error, PluginError)

    def test_plugin_dependency_error(self):
        """Test PluginDependencyError exception."""
        error = PluginDependencyError("Missing dependency")
        assert str(error) == "Missing dependency"
        assert isinstance(error, PluginError)


class TestBasePlugin:
    """Test BasePlugin abstract class."""

    def create_test_plugin(self):
        """Create a concrete test plugin implementation."""

        class TestPluginImpl(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = "test_plugin"
                self.version = "1.0.0"
                self.category = "test"

            async def initialize(self):
                self.initialized = True
                return True

            async def shutdown(self):
                pass

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        return TestPluginImpl()

    def test_base_plugin_creation(self):
        """Test creating base plugin."""
        plugin = self.create_test_plugin()

        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.category == "test"
        assert plugin.enabled == True
        assert plugin.initialized == False
        assert isinstance(plugin.config, dict)

    @pytest.mark.asyncio
    async def test_base_plugin_initialize(self):
        """Test plugin initialization."""
        plugin = self.create_test_plugin()

        await plugin.initialize()
        assert plugin.initialized == True

    @pytest.mark.asyncio
    async def test_base_plugin_health_check(self):
        """Test plugin health check."""
        plugin = self.create_test_plugin()
        await plugin.initialize()

        health = await plugin.health_check()
        assert isinstance(health, HealthStatus)
        assert health.healthy == True

    def test_base_plugin_validate_config(self):
        """Test plugin config validation."""
        plugin = self.create_test_plugin()

        # Should not raise error with valid config
        result = plugin.validate_config({"valid": "config"})
        assert result == True

    def test_base_plugin_get_info(self):
        """Test getting plugin info."""
        plugin = self.create_test_plugin()

        info = plugin.get_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "status" in info

    def test_base_plugin_get_metrics(self):
        """Test getting plugin metrics."""
        plugin = self.create_test_plugin()

        metrics = plugin.get_metrics()
        assert isinstance(metrics, dict)
        assert "uptime" in metrics
        assert "memory_usage" in metrics

    @pytest.mark.asyncio
    async def test_base_plugin_publish_event(self):
        """Test publishing events from plugin."""
        plugin = self.create_test_plugin()
        mock_event_bus = AsyncMock()
        plugin.event_bus = mock_event_bus

        await plugin.publish_event("test.event", {"data": "test"})

        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_base_plugin_subscribe_to_event(self):
        """Test subscribing to events."""
        plugin = self.create_test_plugin()
        mock_event_bus = MagicMock()
        plugin.event_bus = mock_event_bus

        def handler(event):
            pass

        await plugin.subscribe_to_event("test.event", handler)

        mock_event_bus.subscribe.assert_called_once_with("test.event", handler)

    @pytest.mark.asyncio
    async def test_base_plugin_unsubscribe_from_event(self):
        """Test unsubscribing from events."""
        plugin = self.create_test_plugin()
        mock_event_bus = MagicMock()
        plugin.event_bus = mock_event_bus

        def handler(event):
            pass

        await plugin.unsubscribe_from_event("test.event", handler)

        mock_event_bus.unsubscribe.assert_called_once_with("test.event", handler)

    def test_base_plugin_register_service(self):
        """Test registering services."""
        plugin = self.create_test_plugin()
        mock_registry = MagicMock()
        plugin.service_registry = mock_registry

        service = {"name": "test_service"}
        plugin.register_service("test", service)

        mock_registry.register.assert_called_once_with("test", service)

    def test_base_plugin_get_service(self):
        """Test getting services."""
        plugin = self.create_test_plugin()
        mock_registry = MagicMock()
        test_service = {"name": "test"}
        mock_registry.get.return_value = test_service
        plugin.service_registry = mock_registry

        result = plugin.get_service("test")

        assert result == test_service
        mock_registry.get.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_base_plugin_get_config(self):
        """Test getting plugin configuration."""
        plugin = self.create_test_plugin()
        mock_adapter = AsyncMock()
        mock_adapter.get.return_value = '{"setting": "value"}'
        plugin.db_adapter = mock_adapter

        config = await plugin.get_config("test_key")

        assert config == {"setting": "value"}

    @pytest.mark.asyncio
    async def test_base_plugin_set_config(self):
        """Test setting plugin configuration."""
        plugin = self.create_test_plugin()
        mock_adapter = AsyncMock()
        plugin.db_adapter = mock_adapter

        config_data = {"setting": "new_value"}
        await plugin.set_config("test_key", config_data)

        mock_adapter.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_base_plugin_get_data(self):
        """Test getting plugin data."""
        plugin = self.create_test_plugin()
        mock_adapter = AsyncMock()
        mock_adapter.get.return_value = "test_data"
        plugin.db_adapter = mock_adapter

        data = await plugin.get_data("data_key")

        assert data == "test_data"
        mock_adapter.get.assert_called_once_with("plugin:test_plugin:data_key")

    @pytest.mark.asyncio
    async def test_base_plugin_set_data(self):
        """Test setting plugin data."""
        plugin = self.create_test_plugin()
        mock_adapter = AsyncMock()
        plugin.db_adapter = mock_adapter

        await plugin.set_data("data_key", "test_value")

        mock_adapter.set.assert_called_once_with("plugin:test_plugin:data_key", "test_value")


class TestSpecializedPlugins:
    """Test specialized plugin classes."""

    def test_business_plugin(self):
        """Test BusinessPlugin class."""
        plugin = BusinessPlugin()
        assert plugin.category == "business"

    def test_integration_plugin(self):
        """Test IntegrationPlugin class."""
        plugin = IntegrationPlugin()
        assert plugin.category == "integration"

    @pytest.mark.asyncio
    async def test_integration_plugin_test_connection(self):
        """Test IntegrationPlugin connection test."""
        plugin = IntegrationPlugin()
        # Should return False by default (not implemented)
        result = await plugin.test_connection()
        assert result == False

    def test_analytics_plugin(self):
        """Test AnalyticsPlugin class."""
        plugin = AnalyticsPlugin()
        assert plugin.category == "analytics"

    @pytest.mark.asyncio
    async def test_analytics_plugin_collect_metrics(self):
        """Test AnalyticsPlugin metrics collection."""
        plugin = AnalyticsPlugin()
        # Should return empty dict by default
        metrics = await plugin.collect_metrics()
        assert metrics == {}

    @pytest.mark.asyncio
    async def test_analytics_plugin_generate_report(self):
        """Test AnalyticsPlugin report generation."""
        plugin = AnalyticsPlugin()
        # Should return empty dict by default
        report = await plugin.generate_report()
        assert report == {}

    def test_security_plugin(self):
        """Test SecurityPlugin class."""
        plugin = SecurityPlugin()
        assert plugin.category == "security"

    @pytest.mark.asyncio
    async def test_security_plugin_validate_request(self):
        """Test SecurityPlugin request validation."""
        plugin = SecurityPlugin()
        # Should return True by default (allow all)
        result = await plugin.validate_request({})
        assert result == True

    @pytest.mark.asyncio
    async def test_security_plugin_audit_log(self):
        """Test SecurityPlugin audit logging."""
        plugin = SecurityPlugin()
        # Should not raise error
        await plugin.audit_log("test_action", {"user": "test"})

    def test_ui_plugin(self):
        """Test UIPlugin class."""
        plugin = UIPlugin()
        assert plugin.category == "ui"

    def test_ui_plugin_get_ui_components(self):
        """Test UIPlugin UI components."""
        plugin = UIPlugin()
        # Should return empty list by default
        components = plugin.get_ui_components()
        assert components == []

    def test_ui_plugin_get_menu_items(self):
        """Test UIPlugin menu items."""
        plugin = UIPlugin()
        # Should return empty list by default
        items = plugin.get_menu_items()
        assert items == []

    def test_notification_plugin(self):
        """Test NotificationPlugin class."""
        plugin = NotificationPlugin()
        assert plugin.category == "notification"

    @pytest.mark.asyncio
    async def test_notification_plugin_send_notification(self):
        """Test NotificationPlugin notification sending."""
        plugin = NotificationPlugin()
        # Should not raise error
        await plugin.send_notification("user", "Test Subject", "Test message")

    def test_storage_plugin(self):
        """Test StoragePlugin class."""
        plugin = StoragePlugin()
        assert plugin.category == "storage"

    @pytest.mark.asyncio
    async def test_storage_plugin_store(self):
        """Test StoragePlugin data storage."""
        plugin = StoragePlugin()
        # Should not raise error
        await plugin.store("key", b"data")

    @pytest.mark.asyncio
    async def test_storage_plugin_retrieve(self):
        """Test StoragePlugin data retrieval."""
        plugin = StoragePlugin()
        # Should return None by default
        result = await plugin.retrieve("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_storage_plugin_delete(self):
        """Test StoragePlugin data deletion."""
        plugin = StoragePlugin()
        # Should not raise error
        await plugin.delete("key")

    def test_workflow_plugin(self):
        """Test WorkflowPlugin class."""
        plugin = WorkflowPlugin()
        assert plugin.category == "workflow"

    @pytest.mark.asyncio
    async def test_workflow_plugin_execute_workflow(self):
        """Test WorkflowPlugin workflow execution."""
        plugin = WorkflowPlugin()
        # Should not raise error
        result = await plugin.execute_workflow("test_workflow", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_workflow_plugin_get_workflow_status(self):
        """Test WorkflowPlugin workflow status."""
        plugin = WorkflowPlugin()
        # Should return unknown by default
        status = await plugin.get_workflow_status("workflow_id")
        assert status == "unknown"


class TestPluginValidator:
    """Test PluginValidator class."""

    def test_plugin_validator_creation(self):
        """Test creating plugin validator."""
        validator = PluginValidator()
        assert validator is not None

    def test_validate_plugin_valid(self):
        """Test validating a valid plugin."""
        validator = PluginValidator()

        # Create a mock valid plugin
        class ValidPlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = "valid_plugin"
                self.version = "1.0.0"

            async def initialize(self):
                return True

            async def shutdown(self):
                pass

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        plugin = ValidPlugin()
        result = validator.validate_plugin(plugin)

        assert result == True

    def test_validate_plugin_invalid_name(self):
        """Test validating plugin with invalid name."""
        validator = PluginValidator()

        # Create a mock plugin with invalid name
        class InvalidPlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = ""  # Invalid empty name

            async def initialize(self):
                return True

            async def shutdown(self):
                pass

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        plugin = InvalidPlugin()
        result = validator.validate_plugin(plugin)

        assert result == False

    def test_validate_manifest_valid(self):
        """Test validating valid manifest."""
        validator = PluginValidator()

        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "category": "test",
        }

        result = validator.validate_manifest(manifest)
        assert result == True

    def test_validate_manifest_missing_required_fields(self):
        """Test validating manifest with missing required fields."""
        validator = PluginValidator()

        # Missing required fields
        manifest = {"description": "A test plugin"}

        result = validator.validate_manifest(manifest)
        assert result == False

    def test_validate_manifest_invalid_version(self):
        """Test validating manifest with invalid version."""
        validator = PluginValidator()

        manifest = {
            "name": "test_plugin",
            "version": "invalid_version",  # Invalid version format
            "author": "Test Author",
            "category": "test",
        }

        result = validator.validate_manifest(manifest)
        assert result == False


class TestSpecializedPluginMethods:
    """Test specialized plugin methods for coverage."""

    @pytest.mark.asyncio
    async def test_business_plugin_methods(self):
        """Test BusinessPlugin methods."""
        plugin = BusinessPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_integration_plugin_methods(self):
        """Test IntegrationPlugin methods."""
        plugin = IntegrationPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_analytics_plugin_methods(self):
        """Test AnalyticsPlugin methods."""
        plugin = AnalyticsPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_security_plugin_methods(self):
        """Test SecurityPlugin methods."""
        plugin = SecurityPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_ui_plugin_methods(self):
        """Test UIPlugin methods."""
        plugin = UIPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_notification_plugin_methods(self):
        """Test NotificationPlugin methods."""
        plugin = NotificationPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_storage_plugin_methods(self):
        """Test StoragePlugin methods."""
        plugin = StoragePlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}

    @pytest.mark.asyncio
    async def test_workflow_plugin_methods(self):
        """Test WorkflowPlugin methods."""
        plugin = WorkflowPlugin()

        # Test initialize
        result = await plugin.initialize()
        assert result == True

        # Test shutdown
        await plugin.shutdown()  # Should not raise error

        # Test get_api_routes
        routes = plugin.get_api_routes()
        assert routes == []

        # Test get_database_schema
        schema = plugin.get_database_schema()
        assert schema == {}


class TestPluginValidatorErrorPaths:
    """Test plugin validator error paths for coverage."""

    def test_validate_plugin_missing_method(self):
        """Test validating plugin with missing required method."""
        validator = PluginValidator()

        # Create a complete plugin but test validation logic directly
        class CompletePlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.name = "complete_plugin"

            async def initialize(self):
                return True

            async def shutdown(self):
                pass

            def get_api_routes(self):
                return []

            def get_database_schema(self):
                return {}

        plugin = CompletePlugin()

        # Mock hasattr to simulate missing method for validation test
        with patch("builtins.hasattr") as mock_hasattr:
            # Return False for get_database_schema to simulate missing method
            mock_hasattr.side_effect = lambda obj, attr: attr != "get_database_schema"
            result = validator.validate_plugin(plugin)
            assert result == False

    def test_validate_manifest_invalid_category(self):
        """Test validating manifest with invalid category."""
        validator = PluginValidator()

        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "category": "invalid_category",  # Invalid category
        }

        result = validator.validate_manifest(manifest)
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
