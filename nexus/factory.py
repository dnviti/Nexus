"""
Nexus Framework Factory Functions
Factory functions for creating applications and plugins with proper configuration.
"""

import logging
from typing import Any, Dict, List, Optional, Type, Union

from .app import NexusApp
from .config import AppConfig, create_default_config, load_config
from .plugins import BasePlugin, PluginContext, PluginMetadata

logger = logging.getLogger(__name__)


def create_nexus_app(
    title: str = "Nexus Application",
    version: str = "1.0.0",
    description: str = "A Nexus Framework Application",
    config: Optional[Union[AppConfig, Dict[str, Any], str]] = None,
    **kwargs: Any,
) -> NexusApp:
    """
    Factory function to create a new Nexus application.

    This is the main entry point for creating Nexus applications. It handles
    configuration loading and provides sensible defaults for rapid development.

    Args:
        title: Application title
        version: Application version
        description: Application description
        config: Configuration (AppConfig object, dict, or path to config file)
        **kwargs: Additional FastAPI configuration options

    Returns:
        NexusApp: Configured application instance ready to run

    Examples:
        Basic usage:
        ```python
        app = create_nexus_app(
            title="My API Server",
            version="1.0.0"
        )
        app.run()
        ```

        With configuration file:
        ```python
        app = create_nexus_app(
            title="Production API",
            config="config.yaml"
        )
        ```

        With inline configuration:
        ```python
        app = create_nexus_app(
            title="Development API",
            config={
                "database": {"type": "postgresql", "host": "localhost"},
                "cors": {"enabled": True, "origins": ["http://localhost:3000"]}
            }
        )
        ```
    """
    # Handle different config types
    final_config: AppConfig

    if config is None:
        # Create default configuration
        final_config = create_default_config()
        logger.debug("Using default configuration")
    elif isinstance(config, str):
        # Load from configuration file
        try:
            final_config = load_config(config)
            logger.info(f"Loaded configuration from {config}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config}: {e}, using defaults")
            final_config = create_default_config()
    elif isinstance(config, dict):
        # Create from dictionary
        try:
            final_config = AppConfig(**config)
            logger.debug("Created configuration from dictionary")
        except Exception as e:
            logger.error(f"Invalid configuration dictionary: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    elif isinstance(config, AppConfig):
        # Use provided AppConfig instance
        final_config = config
        logger.debug("Using provided AppConfig instance")
    else:
        raise TypeError(
            f"Invalid config type: {type(config)}. "
            f"Expected AppConfig, dict, str (file path), or None"
        )

    # Create the application instance
    return NexusApp(
        title=title,
        version=version,
        description=description,
        config=final_config,
        **kwargs,
    )


def create_plugin(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    category: str = "general",
    dependencies: Optional[Dict[str, str]] = None,
    permissions: Optional[List[str]] = None,
    **metadata_kwargs: Any,
) -> Type[BasePlugin]:
    """
    Factory function to create a plugin class dynamically.

    This function creates a plugin class that can be subclassed to implement
    custom plugin functionality. It handles metadata setup and provides
    a clean API for plugin development.

    Args:
        name: Plugin name (should be unique)
        version: Plugin version (semantic versioning recommended)
        description: Plugin description
        author: Plugin author name/email
        category: Plugin category for organization
        dependencies: Dictionary of required dependencies {name: version}
        permissions: List of required permissions
        **metadata_kwargs: Additional metadata fields

    Returns:
        Type[BasePlugin]: Plugin class ready for implementation

    Examples:
        Basic plugin:
        ```python
        MyPlugin = create_plugin(
            name="hello_world",
            version="1.0.0",
            description="A simple hello world plugin",
            author="John Doe <john@example.com>"
        )

        class HelloWorldPlugin(MyPlugin):
            async def on_enable(self):
                self.logger.info("Hello, World!")

            async def on_disable(self):
                self.logger.info("Goodbye, World!")
        ```

        Plugin with dependencies:
        ```python
        DatabasePlugin = create_plugin(
            name="database_manager",
            version="2.1.0",
            description="Database connection manager",
            author="DB Team",
            category="database",
            dependencies={"psycopg2": ">=2.9.0", "sqlalchemy": ">=1.4.0"},
            permissions=["database.read", "database.write"]
        )
        ```
    """
    # Prepare metadata
    plugin_metadata = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "category": category,
        "dependencies": dependencies or {},
        "permissions": permissions or [],
        **metadata_kwargs,
    }

    class DynamicPlugin(BasePlugin):
        """Dynamically created plugin class."""

        def __init__(self) -> None:
            """Initialize the plugin with metadata."""
            super().__init__()

            # Set core metadata
            self.name = name
            self.version = version
            self.description = description
            self.author = author
            self.category = category

            # Set additional metadata
            for key, value in plugin_metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)

            # Set up logger with plugin name
            self.logger = logging.getLogger(f"nexus.plugin.{name}")

    # Set a more descriptive class name
    class_name = f"{name.title().replace('_', '')}Plugin"
    DynamicPlugin.__name__ = class_name
    DynamicPlugin.__qualname__ = class_name

    return DynamicPlugin


def create_plugin_context(
    app_config: Optional[Dict[str, Any]] = None,
    service_registry: Optional[Any] = None,
    event_bus: Optional[Any] = None,
) -> PluginContext:
    """
    Factory function to create a plugin context.

    Args:
        app_config: Application configuration dictionary
        service_registry: Service registry instance
        event_bus: Event bus instance

    Returns:
        PluginContext: Configured plugin context
    """
    return PluginContext(
        app_config=app_config or {},
        service_registry=service_registry,
        event_bus=event_bus,
    )


def create_plugin_metadata(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    **kwargs: Any,
) -> PluginMetadata:
    """
    Factory function to create plugin metadata.

    Args:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        **kwargs: Additional metadata fields

    Returns:
        PluginMetadata: Configured plugin metadata
    """
    return PluginMetadata(
        name=name,
        version=version,
        description=description,
        author=author,
        **kwargs,
    )


# Convenience aliases for common use cases
def create_api_app(title: str, version: str = "1.0.0", **kwargs: Any) -> NexusApp:
    """
    Create an API-focused Nexus application with optimized defaults.

    Args:
        title: API title
        version: API version
        **kwargs: Additional configuration

    Returns:
        NexusApp: Configured API application
    """
    return create_nexus_app(
        title=title,
        version=version,
        description=f"{title} - REST API built with Nexus Framework",
        **kwargs,
    )


def create_microservice(name: str, version: str = "1.0.0", **kwargs: Any) -> NexusApp:
    """
    Create a microservice with Nexus framework.

    Args:
        name: Microservice name
        version: Service version
        **kwargs: Additional configuration

    Returns:
        NexusApp: Configured microservice application
    """
    return create_nexus_app(
        title=f"{name.title()} Service",
        version=version,
        description=f"{name} microservice built with Nexus Framework",
        **kwargs,
    )


def create_web_app(title: str, version: str = "1.0.0", **kwargs: Any) -> NexusApp:
    """
    Create a web application with Nexus framework.

    Args:
        title: Web application title
        version: Application version
        **kwargs: Additional configuration

    Returns:
        NexusApp: Configured web application
    """
    return create_nexus_app(
        title=title,
        version=version,
        description=f"{title} - Web Application built with Nexus Framework",
        **kwargs,
    )
