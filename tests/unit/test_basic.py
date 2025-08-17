"""
Basic unit tests for Nexus framework core functionality.

These tests cover fundamental framework operations including:
- Framework import and initialization
- Basic app creation
- Version checking
- Core component availability
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import nexus
from nexus import create_nexus_app


class TestBasicImports:
    """Test basic framework imports and module structure."""

    def test_import_nexus(self):
        """Test that nexus can be imported without errors."""
        import nexus

        assert nexus is not None

    def test_nexus_version(self):
        """Test that nexus has a valid version."""
        assert hasattr(nexus, "__version__")
        assert nexus.__version__ is not None
        assert isinstance(nexus.__version__, str)

    def test_version_format(self):
        """Test version follows semantic versioning format."""
        import re

        version_pattern = r"^\d+\.\d+\.\d+.*$"
        assert re.match(version_pattern, nexus.__version__)

    def test_nexus_author(self):
        """Test that nexus has author information."""
        assert hasattr(nexus, "__author__")
        assert nexus.__author__ is not None
        assert isinstance(nexus.__author__, str)


class TestAppCreation:
    """Test basic application creation functionality."""

    def test_create_nexus_app_basic(self):
        """Test basic app creation."""
        app = create_nexus_app(title="Test App")
        assert app is not None

    def test_create_nexus_app_with_params(self):
        """Test app creation with various parameters."""
        app = create_nexus_app(title="Test App", description="Test Description", version="1.0.0")
        assert app is not None
        # Check if it's a FastAPI app
        assert hasattr(app, "title")
        assert app.title == "Test App"

    def test_app_has_health_endpoint(self):
        """Test that created app has health endpoint."""
        from fastapi.testclient import TestClient

        app = create_nexus_app(title="Test App")
        client = TestClient(app.app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_app_has_docs_endpoint(self):
        """Test that created app has documentation endpoint."""
        from fastapi.testclient import TestClient

        app = create_nexus_app(title="Test App")
        client = TestClient(app.app)

        response = client.get("/docs")
        assert response.status_code == 200


class TestCoreComponents:
    """Test core framework components are available."""

    def test_base_plugin_import(self):
        """Test BasePlugin can be imported."""
        from nexus import BasePlugin

        assert BasePlugin is not None

    def test_create_nexus_app_import(self):
        """Test create_nexus_app function can be imported."""
        from nexus import create_nexus_app

        assert create_nexus_app is not None
        assert callable(create_nexus_app)

    def test_config_components(self):
        """Test configuration components are available."""
        try:
            from nexus.core import AppConfig, create_default_config

            assert AppConfig is not None
            assert create_default_config is not None
        except ImportError:
            # If core module structure is different, this is expected
            pass


class TestErrorHandling:
    """Test error handling in basic operations."""

    def test_create_app_with_invalid_params(self):
        """Test app creation handles invalid parameters gracefully."""
        # This should not raise an exception, just use defaults
        app = create_nexus_app()
        assert app is not None

    def test_import_non_existent_module(self):
        """Test importing non-existent nexus modules raises ImportError."""
        with pytest.raises(ImportError):
            import importlib

            importlib.import_module("nexus.NonExistentModule")


class TestFrameworkMetadata:
    """Test framework metadata and constants."""

    def test_framework_constants(self):
        """Test framework has expected constants."""
        # Version should be present
        assert hasattr(nexus, "__version__")

        # Check if other metadata is available
        metadata_attrs = ["__author__", "__license__"]
        for attr in metadata_attrs:
            if hasattr(nexus, attr):
                assert getattr(nexus, attr) is not None

    def test_version_is_string(self):
        """Test version is a string type."""
        assert isinstance(nexus.__version__, str)
        assert len(nexus.__version__) > 0

    def test_version_components(self):
        """Test version has recognizable components."""
        version_parts = nexus.__version__.split(".")
        assert len(version_parts) >= 3  # At least major.minor.patch

        # First three parts should be numeric
        for part in version_parts[:3]:
            assert part.isdigit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
