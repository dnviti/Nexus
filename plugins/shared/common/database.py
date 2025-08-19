"""
Database Helper Utilities for Nexus Plugins

This module provides shared database utilities that can be used across all plugins
to maintain consistent database operations and connection management.
"""

import logging
import sqlite3
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database configuration
DEFAULT_DB_CONFIG = {
    "type": "sqlite",
    "path": "data/nexus.db",
    "timeout": 30,
    "check_same_thread": False,
}


class DatabaseError(Exception):
    """Custom database error."""

    def __init__(self, message: str, query: Optional[str] = None):
        self.message = message
        self.query = query
        super().__init__(message)


class DatabaseHelper:
    """Database helper class for common database operations."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database helper.

        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path or DEFAULT_DB_CONFIG["path"]
        self.timeout = DEFAULT_DB_CONFIG["timeout"]

        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database with common tables."""
        with self.get_connection() as conn:
            # Create plugin_data table for storing plugin-specific data
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plugin_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    data_type TEXT DEFAULT 'str',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(plugin_name, key)
                )
            """
            )

            # Create plugin_events table for event logging
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plugin_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create plugin_metrics table for performance tracking
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plugin_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metric_unit TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create plugin_config table for configuration storage
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plugin_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    config_value TEXT,
                    is_encrypted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(plugin_name, config_key)
                )
            """
            )

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()

    def execute_query(
        self, query: str, params: Optional[Union[tuple, dict]] = None, fetch: str = "none"
    ) -> Optional[Union[List[Dict], Dict]]:
        """
        Execute a database query.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Fetch mode - "none", "one", "all"

        Returns:
            Query results based on fetch mode
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch == "one":
                    row = cursor.fetchone()
                    return dict(row) if row else None
                elif fetch == "all":
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    conn.commit()
                    return None

        except sqlite3.Error as e:
            logger.error(f"Database query failed: {query}, Error: {str(e)}")
            raise DatabaseError(f"Query execution failed: {str(e)}", query)

    def store_plugin_data(
        self, plugin_name: str, key: str, value: Any, data_type: Optional[str] = None
    ) -> bool:
        """
        Store plugin-specific data.

        Args:
            plugin_name: Name of the plugin
            key: Data key
            value: Data value
            data_type: Type of data (str, int, float, json, bool)

        Returns:
            True if successful
        """
        # Determine data type if not provided
        if data_type is None:
            if isinstance(value, bool):
                data_type = "bool"
            elif isinstance(value, int):
                data_type = "int"
            elif isinstance(value, float):
                data_type = "float"
            elif isinstance(value, (dict, list)):
                data_type = "json"
            else:
                data_type = "str"

        # Serialize value based on type
        if data_type == "json":
            serialized_value = json.dumps(value)
        elif data_type == "bool":
            serialized_value = "1" if value else "0"
        else:
            serialized_value = str(value)

        query = """
            INSERT OR REPLACE INTO plugin_data
            (plugin_name, key, value, data_type, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        try:
            self.execute_query(query, (plugin_name, key, serialized_value, data_type))
            logger.debug(f"Stored data for {plugin_name}: {key} = {value}")
            return True
        except DatabaseError:
            logger.error(f"Failed to store data for {plugin_name}: {key}")
            return False

    def get_plugin_data(
        self, plugin_name: str, key: Optional[str] = None
    ) -> Optional[Union[Any, Dict[str, Any]]]:
        """
        Retrieve plugin-specific data.

        Args:
            plugin_name: Name of the plugin
            key: Data key (if None, returns all data for plugin)

        Returns:
            Retrieved data or None if not found
        """
        if key:
            query = "SELECT value, data_type FROM plugin_data WHERE plugin_name = ? AND key = ?"
            result = self.execute_query(query, (plugin_name, key), "one")

            if not result:
                return None

            return self._deserialize_value(result["value"], result["data_type"])
        else:
            query = "SELECT key, value, data_type FROM plugin_data WHERE plugin_name = ?"
            results = self.execute_query(query, (plugin_name,), "all")

            if not results:
                return {}

            data = {}
            for row in results:
                data[row["key"]] = self._deserialize_value(row["value"], row["data_type"])

            return data

    def delete_plugin_data(self, plugin_name: str, key: Optional[str] = None) -> bool:
        """
        Delete plugin-specific data.

        Args:
            plugin_name: Name of the plugin
            key: Data key (if None, deletes all data for plugin)

        Returns:
            True if successful
        """
        if key:
            query = "DELETE FROM plugin_data WHERE plugin_name = ? AND key = ?"
            params = (plugin_name, key)
        else:
            query = "DELETE FROM plugin_data WHERE plugin_name = ?"
            params = (plugin_name,)

        try:
            self.execute_query(query, params)
            logger.info(f"Deleted data for {plugin_name}" + (f": {key}" if key else " (all)"))
            return True
        except DatabaseError:
            logger.error(f"Failed to delete data for {plugin_name}" + (f": {key}" if key else ""))
            return False

    def log_plugin_event(
        self, plugin_name: str, event_type: str, event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a plugin event.

        Args:
            plugin_name: Name of the plugin
            event_type: Type of event
            event_data: Additional event data

        Returns:
            True if successful
        """
        serialized_data = json.dumps(event_data) if event_data else None

        query = """
            INSERT INTO plugin_events (plugin_name, event_type, event_data)
            VALUES (?, ?, ?)
        """

        try:
            self.execute_query(query, (plugin_name, event_type, serialized_data))
            return True
        except DatabaseError:
            logger.error(f"Failed to log event for {plugin_name}: {event_type}")
            return False

    def get_plugin_events(
        self, plugin_name: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get plugin events.

        Args:
            plugin_name: Filter by plugin name
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        query = "SELECT * FROM plugin_events WHERE 1=1"
        params = []

        if plugin_name:
            query += " AND plugin_name = ?"
            params.append(plugin_name)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = self.execute_query(query, params, "all")

        # Deserialize event data
        for result in results:
            if result["event_data"]:
                try:
                    result["event_data"] = json.loads(result["event_data"])
                except json.JSONDecodeError:
                    result["event_data"] = None

        return results

    def store_plugin_metric(
        self,
        plugin_name: str,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
    ) -> bool:
        """
        Store a plugin metric.

        Args:
            plugin_name: Name of the plugin
            metric_name: Name of the metric
            metric_value: Metric value
            metric_unit: Unit of measurement

        Returns:
            True if successful
        """
        query = """
            INSERT INTO plugin_metrics (plugin_name, metric_name, metric_value, metric_unit)
            VALUES (?, ?, ?, ?)
        """

        try:
            self.execute_query(query, (plugin_name, metric_name, metric_value, metric_unit))
            return True
        except DatabaseError:
            logger.error(f"Failed to store metric for {plugin_name}: {metric_name}")
            return False

    def get_plugin_metrics(
        self, plugin_name: Optional[str] = None, metric_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get plugin metrics.

        Args:
            plugin_name: Filter by plugin name
            metric_name: Filter by metric name
            limit: Maximum number of metrics to return

        Returns:
            List of metrics
        """
        query = "SELECT * FROM plugin_metrics WHERE 1=1"
        params = []

        if plugin_name:
            query += " AND plugin_name = ?"
            params.append(plugin_name)

        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return self.execute_query(query, params, "all")

    def _deserialize_value(self, value: str, data_type: str) -> Any:
        """Deserialize stored value based on data type."""
        if data_type == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        elif data_type == "int":
            try:
                return int(value)
            except ValueError:
                return value
        elif data_type == "float":
            try:
                return float(value)
            except ValueError:
                return value
        elif data_type == "bool":
            return value == "1"
        else:
            return value

    def cleanup_old_data(self, days_old: int = 30) -> bool:
        """
        Clean up old data from the database.

        Args:
            days_old: Delete data older than this many days

        Returns:
            True if successful
        """
        try:
            # Clean up old events
            self.execute_query(
                "DELETE FROM plugin_events WHERE created_at < datetime('now', '-{} days')".format(
                    days_old
                )
            )

            # Clean up old metrics
            self.execute_query(
                "DELETE FROM plugin_metrics WHERE created_at < datetime('now', '-{} days')".format(
                    days_old
                )
            )

            logger.info(f"Cleaned up database data older than {days_old} days")
            return True
        except DatabaseError:
            logger.error(f"Failed to cleanup old database data")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}

        try:
            # Count records in each table
            tables = ["plugin_data", "plugin_events", "plugin_metrics", "plugin_config"]

            for table in tables:
                result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch="one")
                stats[f"{table}_count"] = result["count"] if result else 0

            # Get database file size
            db_path = Path(self.db_path)
            if db_path.exists():
                stats["database_size_bytes"] = db_path.stat().st_size
                stats["database_size_mb"] = round(stats["database_size_bytes"] / 1024 / 1024, 2)

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {"error": str(e)}


# Global database helper instance
_db_helper: Optional[DatabaseHelper] = None


def get_db_connection() -> DatabaseHelper:
    """Get global database helper instance."""
    global _db_helper
    if _db_helper is None:
        _db_helper = DatabaseHelper()
    return _db_helper


def init_database(db_path: Optional[str] = None) -> DatabaseHelper:
    """Initialize database with custom path."""
    global _db_helper
    _db_helper = DatabaseHelper(db_path)
    return _db_helper
