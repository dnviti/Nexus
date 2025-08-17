"""
Hello World Plugin for Nexus Framework

A simple example plugin demonstrating the basics of plugin development.
This plugin provides greeting functionality in multiple languages and a simple message board.
"""

from .plugin import HelloWorldPlugin, create_plugin

__all__ = ["HelloWorldPlugin", "create_plugin"]
__version__ = "1.0.0"
__author__ = "Nexus Team"
