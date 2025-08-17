"""
Nexus Framework Test Suite

This package contains all tests for the Nexus framework, including:
- Unit tests for individual components
- Integration tests for system interactions
- Plugin tests for plugin functionality
- Performance tests for benchmarking

Test Structure:
- tests/unit/ - Unit tests for core components
- tests/integration/ - Integration tests with external services
- tests/plugins/ - Plugin-specific tests
- tests/fixtures/ - Shared test fixtures and utilities
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path for testing
test_dir = Path(__file__).parent
project_root = test_dir.parent
src_dir = project_root / "src"

if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Add the project root to the path
sys.path.insert(0, str(project_root))

__version__ = "2.0.0"
__author__ = "Nexus Team"
