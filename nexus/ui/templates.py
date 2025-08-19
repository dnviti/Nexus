"""
Nexus Framework UI Templates
Template loading and rendering utilities for the web interface
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Template loader for Nexus UI templates.

    Manages loading and caching of HTML templates from the file system.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            # Default to templates directory relative to this file
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = Path(template_dir)
        self._cache: Dict[str, str] = {}
        self._cache_enabled = True

    def load_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Load a template by name and render with context.

        Args:
            template_name: Name of the template file (without .html extension)
            context: Optional context variables for template rendering

        Returns:
            Rendered HTML string
        """
        # Check cache first
        cache_key = f"{template_name}_{hash(str(sorted((context or {}).items())))}"
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # Load template file
        template_path = self.template_dir / f"{template_name}.html"

        if not template_path.exists():
            logger.warning(f"Template not found: {template_path}")
            return self._get_fallback_template(template_name, context)

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Simple template variable substitution
            if context:
                template_content = self._render_template(template_content, context)

            # Cache the result
            if self._cache_enabled:
                self._cache[cache_key] = template_content

            return template_content

        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return self._get_fallback_template(template_name, context)

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Simple template rendering with variable substitution.

        Supports {{variable}} syntax for basic variable substitution.
        """
        import re

        def replace_var(match: Any) -> str:
            var_name = match.group(1).strip()
            return str(context.get(var_name, f"{{{{{var_name}}}}}"))

        # Replace {{variable}} patterns
        return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_var, template)

    def _get_fallback_template(self, template_name: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate a fallback template when the requested template is not found."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Template Not Found</title>
    <link rel="stylesheet" href="/static/css/nexus-ui.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Template Error</h1>
            <p>Template '{template_name}' could not be loaded</p>
        </div>
        <div class="content">
            <div class="section">
                <h2>Template Not Found</h2>
                <p>The requested template '<code>{template_name}</code>' was not found in the templates directory.</p>
                <p>Expected path: <code>{self.template_dir / template_name}</code></p>
            </div>
        </div>
    </div>
</body>
</html>
        """.strip()

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()

    def disable_cache(self) -> None:
        """Disable template caching (useful for development)."""
        self._cache_enabled = False
        self.clear_cache()

    def enable_cache(self) -> None:
        """Enable template caching."""
        self._cache_enabled = True


# Global template loader instance
_template_loader = TemplateLoader()


def get_debug_interface_template(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the main debug interface HTML template.

    Args:
        context: Optional context variables for the template

    Returns:
        Rendered HTML string for the debug interface
    """
    default_context = {
        "title": "Nexus Event Monitor",
        "description": "Real-time event monitoring and debugging interface",
        "version": "1.0.0",
        "api_base_url": "/api/v1",
    }

    if context:
        default_context.update(context)

    return _template_loader.load_template("debug_interface", default_context)


def get_simple_debug_template(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get a simple debug template for basic monitoring.

    Args:
        context: Optional context variables for the template

    Returns:
        Rendered HTML string for simple debug interface
    """
    # Fallback to embedded template for simple debug
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Debug Monitor</title>
    <link rel="stylesheet" href="/static/css/nexus-ui.css">
    <style>
        body {
            font-family: monospace;
            background: #1a1a1a;
            color: #00ff00;
            padding: 20px;
        }
        .debug-container {
            max-width: 800px;
            margin: 0 auto;
        }
        .debug-output {
            background: #000;
            padding: 20px;
            border-radius: 8px;
            height: 400px;
            overflow-y: auto;
            border: 1px solid #333;
        }
        .debug-controls {
            margin-bottom: 20px;
        }
        .debug-controls button {
            background: #333;
            color: #00ff00;
            border: 1px solid #555;
            padding: 10px 20px;
            margin-right: 10px;
            cursor: pointer;
        }
        .debug-controls button:hover {
            background: #555;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 2px 0;
        }
        .log-timestamp {
            color: #888;
        }
        .log-level-info { color: #00ff00; }
        .log-level-warn { color: #ffff00; }
        .log-level-error { color: #ff0000; }
    </style>
</head>
<body>
    <div class="debug-container">
        <h1>🔍 Simple Debug Monitor</h1>

        <div class="debug-controls">
            <button id="start-monitor">Start Monitor</button>
            <button id="stop-monitor">Stop Monitor</button>
            <button id="clear-output">Clear</button>
        </div>

        <div class="debug-output" id="debug-output">
            <div class="log-entry">
                <span class="log-timestamp">[--:--:--]</span>
                <span class="log-level-info">[INFO]</span>
                Debug monitor ready. Click "Start Monitor" to begin.
            </div>
        </div>
    </div>

    <script>
        let isMonitoring = false;
        let eventSource = null;

        document.getElementById('start-monitor').addEventListener('click', startMonitor);
        document.getElementById('stop-monitor').addEventListener('click', stopMonitor);
        document.getElementById('clear-output').addEventListener('click', clearOutput);

        function startMonitor() {
            if (isMonitoring) return;

            isMonitoring = true;
            addLogEntry('Starting event monitor...', 'info');

            eventSource = new EventSource('/api/v1/debug/events/stream');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addLogEntry(`Event: ${data.type} - ${JSON.stringify(data.data)}`, 'info');
            };

            eventSource.onerror = function(error) {
                addLogEntry('Event source error', 'error');
                stopMonitor();
            };
        }

        function stopMonitor() {
            if (!isMonitoring) return;

            isMonitoring = false;
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            addLogEntry('Event monitor stopped', 'warn');
        }

        function clearOutput() {
            document.getElementById('debug-output').innerHTML = '';
        }

        function addLogEntry(message, level = 'info') {
            const output = document.getElementById('debug-output');
            const timestamp = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `
                <span class="log-timestamp">[${timestamp}]</span>
                <span class="log-level-${level}">[${level.toUpperCase()}]</span>
                ${message}
            `;
            output.appendChild(entry);
            output.scrollTop = output.scrollHeight;
        }
    </script>
</body>
</html>
    """.strip()


def get_notifications_demo_template(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get a notifications demo template.

    Args:
        context: Optional context variables for the template

    Returns:
        Rendered HTML string for notifications demo
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Notifications Demo</title>
    <link rel="stylesheet" href="/static/css/nexus-ui.css">
    <style>
        .demo-container {
            max-width: 1000px;
            margin: 2rem auto;
            padding: 2rem;
        }
        .notification-types {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .notification-demo {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .notification-demo.success { border-left-color: #28a745; }
        .notification-demo.warning { border-left-color: #ffc107; }
        .notification-demo.error { border-left-color: #dc3545; }
        .notification-demo.info { border-left-color: #17a2b8; }

        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        .toast {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid #007bff;
            min-width: 300px;
            animation: slideIn 0.3s ease;
        }
        .toast.success { border-left-color: #28a745; }
        .toast.warning { border-left-color: #ffc107; }
        .toast.error { border-left-color: #dc3545; }
        .toast.info { border-left-color: #17a2b8; }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        .demo-button {
            background: #007bff;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            margin: 0.5rem;
        }
        .demo-button:hover { background: #0056b3; }
        .demo-button.success { background: #28a745; }
        .demo-button.success:hover { background: #1e7e34; }
        .demo-button.warning { background: #ffc107; color: #333; }
        .demo-button.warning:hover { background: #e0a800; }
        .demo-button.error { background: #dc3545; }
        .demo-button.error:hover { background: #c82333; }
    </style>
</head>
<body>
    <div class="demo-container">
        <h1>🔔 Nexus Notifications Demo</h1>
        <p>This page demonstrates various notification types and behaviors in the Nexus Framework.</p>

        <div class="section">
            <h2>Notification Types</h2>
            <div class="notification-types">
                <div class="notification-demo info">
                    <h4>ℹ️ Info</h4>
                    <p>General information messages</p>
                    <button class="demo-button" onclick="showToast('This is an info notification', 'info')">
                        Show Info
                    </button>
                </div>

                <div class="notification-demo success">
                    <h4>✅ Success</h4>
                    <p>Success confirmation messages</p>
                    <button class="demo-button success" onclick="showToast('Operation completed successfully!', 'success')">
                        Show Success
                    </button>
                </div>

                <div class="notification-demo warning">
                    <h4>⚠️ Warning</h4>
                    <p>Warning and caution messages</p>
                    <button class="demo-button warning" onclick="showToast('This is a warning message', 'warning')">
                        Show Warning
                    </button>
                </div>

                <div class="notification-demo error">
                    <h4>❌ Error</h4>
                    <p>Error and failure messages</p>
                    <button class="demo-button error" onclick="showToast('An error has occurred!', 'error')">
                        Show Error
                    </button>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Demo Actions</h2>
            <button class="demo-button" onclick="showRandomNotification()">Random Notification</button>
            <button class="demo-button" onclick="showMultipleNotifications()">Multiple Notifications</button>
            <button class="demo-button" onclick="clearAllToasts()">Clear All</button>
        </div>
    </div>

    <div class="toast-container" id="toast-container"></div>

    <script>
        function showToast(message, type = 'info', duration = 5000) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;

            const typeIcons = {
                info: 'ℹ️',
                success: '✅',
                warning: '⚠️',
                error: '❌'
            };

            toast.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>${typeIcons[type] || 'ℹ️'}</span>
                    <span>${message}</span>
                    <button onclick="this.parentElement.parentElement.remove()" style="margin-left: auto; background: none; border: none; font-size: 1.2rem; cursor: pointer;">×</button>
                </div>
            `;

            container.appendChild(toast);

            // Auto remove after duration
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, duration);
        }

        function showRandomNotification() {
            const types = ['info', 'success', 'warning', 'error'];
            const messages = [
                'This is a random notification',
                'Something interesting happened',
                'Plugin status updated',
                'System check completed',
                'New event received'
            ];

            const type = types[Math.floor(Math.random() * types.length)];
            const message = messages[Math.floor(Math.random() * messages.length)];

            showToast(message, type);
        }

        function showMultipleNotifications() {
            showToast('Starting batch operation...', 'info', 3000);
            setTimeout(() => showToast('Processing items...', 'warning', 3000), 500);
            setTimeout(() => showToast('Almost done...', 'info', 3000), 1000);
            setTimeout(() => showToast('All operations completed!', 'success', 5000), 1500);
        }

        function clearAllToasts() {
            const container = document.getElementById('toast-container');
            container.innerHTML = '';
        }

        // Demo auto-notifications
        setInterval(() => {
            if (Math.random() > 0.7) {
                showRandomNotification();
            }
        }, 10000);
    </script>
</body>
</html>
    """.strip()


def render_template(template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Generic template rendering function.

    Args:
        template_name: Name of the template to render
        context: Optional context variables

    Returns:
        Rendered HTML string
    """
    return _template_loader.load_template(template_name, context)


def set_template_directory(template_dir: Path) -> None:
    """
    Set the template directory for the global template loader.

    Args:
        template_dir: Path to the templates directory
    """
    global _template_loader
    _template_loader = TemplateLoader(template_dir)


def clear_template_cache() -> None:
    """Clear the global template cache."""
    _template_loader.clear_cache()


def disable_template_cache() -> None:
    """Disable template caching (useful for development)."""
    _template_loader.disable_cache()


def enable_template_cache() -> None:
    """Enable template caching."""
    _template_loader.enable_cache()
