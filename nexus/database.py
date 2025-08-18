"""
Nexus Framework Database Module

Comprehensive database support using ORM:
- SQLAlchemy for SQL databases (SQLite, PostgreSQL, MariaDB/MySQL)
- Motor/Beanie for MongoDB
- SQLite as default with automatic setup
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

# Optional MongoDB dependencies
try:
    from motor.motor_asyncio import AsyncIOMotorClient

    HAS_MONGODB = True
except ImportError:
    AsyncIOMotorClient = None
    HAS_MONGODB = False

try:
    import pymongo

    HAS_PYMONGO = True
except ImportError:
    pymongo = None
    HAS_PYMONGO = False

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class KeyValueStore(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for key-value storage."""

    __tablename__ = "nexus_kv_store"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseConfig(BaseModel):
    """Database configuration model."""

    type: str = Field(
        default="sqlite", description="Database type: sqlite, postgresql, mariadb, mongodb"
    )
    url: Optional[str] = Field(default=None, description="Database connection URL")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="nexus", description="Database name")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[str] = Field(default=None, description="Database password")

    # SQLite specific
    path: str = Field(default="./nexus.db", description="SQLite database file path")

    # Connection pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max connection overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")

    # MongoDB specific
    replica_set: Optional[str] = Field(default=None, description="MongoDB replica set")
    auth_source: str = Field(default="admin", description="MongoDB auth source")

    # SSL/TLS settings
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca_path: Optional[str] = Field(default=None, description="SSL CA path")


class DatabaseAdapter(ABC):
    """Abstract database adapter interface."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database."""
        pass

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        """Set a value for a key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        pass

    @abstractmethod
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all data."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        pass


class SQLAlchemyAdapter(DatabaseAdapter):
    """SQLAlchemy-based database adapter for SQL databases."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.engine: Optional[Any] = None
        self.async_session: Optional[Any] = None
        self.session_factory: Optional[Any] = None

    async def connect(self) -> None:
        """Connect to the SQL database."""
        try:
            connection_url = self._build_connection_url()

            # Create async engine
            self.engine = create_async_engine(
                connection_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                echo=False,  # Set to True for SQL debugging
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.connected = True
            logger.info(f"Connected to {self.config.type} database")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.engine:
            await self.engine.dispose()
            self.connected = False
            logger.info("Disconnected from database")

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            result = await session.get(KeyValueStore, key)
            if result:
                try:
                    return json.loads(result.value)
                except json.JSONDecodeError:
                    return result.value
            return default

    async def set(self, key: str, value: Any) -> None:
        """Set a value for a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        # Serialize value
        if isinstance(value, (dict, list, tuple)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            # Check if key exists
            existing = await session.get(KeyValueStore, key)

            if existing:
                existing.value = value_str
                existing.updated_at = datetime.utcnow()
            else:
                kv_entry = KeyValueStore(key=key, value=value_str)
                session.add(kv_entry)

            await session.commit()

    async def delete(self, key: str) -> None:
        """Delete a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            result = await session.get(KeyValueStore, key)
            if result:
                await session.delete(result)
                await session.commit()

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            result = await session.get(KeyValueStore, key)
            return result is not None

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            if pattern == "*":
                result = await session.execute(text("SELECT key FROM nexus_kv_store"))
            else:
                # Convert shell pattern to SQL LIKE pattern
                sql_pattern = pattern.replace("*", "%").replace("?", "_")
                result = await session.execute(
                    text("SELECT key FROM nexus_kv_store WHERE key LIKE :pattern"),
                    {"pattern": sql_pattern},
                )

            return [row[0] for row in result.fetchall()]

    async def clear(self) -> None:
        """Clear all data."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.session_factory is None:
            raise RuntimeError("Database not connected")
        async with self.session_factory() as session:
            await session.execute(text("DELETE FROM nexus_kv_store"))
            await session.commit()

    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            if not self.connected:
                return {"status": "disconnected", "error": "Not connected to database"}

            if self.session_factory is None:
                raise RuntimeError("Database not connected")
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))

                # Get connection info
                result = await session.execute(text("SELECT COUNT(*) FROM nexus_kv_store"))
                count = result.scalar()

                return {
                    "status": "healthy",
                    "type": self.config.type,
                    "connected": True,
                    "total_keys": count,
                    "connection_pool_size": self.config.pool_size,
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "connected": False}

    def _build_connection_url(self) -> str:
        """Build database connection URL."""
        if self.config.url:
            return self.config.url

        if self.config.type == "sqlite":
            return f"sqlite+aiosqlite:///{self.config.path}"
        elif self.config.type == "postgresql":
            if self.config.username and self.config.password:
                return f"postgresql+asyncpg://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            else:
                return f"postgresql+asyncpg://{self.config.host}:{self.config.port}/{self.config.database}"
        elif self.config.type in ["mariadb", "mysql"]:
            if self.config.username and self.config.password:
                return f"mysql+aiomysql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            else:
                return (
                    f"mysql+aiomysql://{self.config.host}:{self.config.port}/{self.config.database}"
                )
        else:
            raise ValueError(f"Unsupported database type: {self.config.type}")


class MongoDBAdapter(DatabaseAdapter):
    """MongoDB adapter using Motor and Beanie."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.client: Optional[Any] = None
        self.database: Optional[Any] = None
        self.collection: Optional[Any] = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            if not HAS_MONGODB:
                raise ImportError(
                    "motor package is required for MongoDB support. Install with: pip install motor"
                )

            if not HAS_PYMONGO:
                raise ImportError(
                    "pymongo package is required for MongoDB support. Install with: pip install pymongo"
                )

            connection_url = self._build_connection_url()

            # Ensure AsyncIOMotorClient is available
            if AsyncIOMotorClient is None:
                raise ImportError(
                    "motor package could not be imported properly. "
                    "Ensure that motor is installed and importable."
                )

            # Create async client
            self.client = AsyncIOMotorClient(connection_url)

            # Test connection
            if self.client is None:
                raise RuntimeError("Failed to instantiate MongoDB client")
            try:
                await self.client.admin.command("ping")
            except Exception as e:
                raise RuntimeError(f"Failed to connect to MongoDB: {e}")

            self.database = self.client[self.config.database]
            if self.database is None:
                raise RuntimeError("Failed to access database")
            self.collection = self.database.nexus_kv_store

            # Create indexes
            if self.collection is None:
                raise RuntimeError("Failed to access collection")
            await self.collection.create_index("key", unique=True)
            await self.collection.create_index("created_at")

            self.connected = True
            logger.info("Connected to MongoDB database")

        except ImportError as ie:
            raise ImportError(
                "motor and pymongo are required for MongoDB support. Install with: pip install motor pymongo"
            ) from ie
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from MongoDB")

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.collection is None:
            raise RuntimeError("Database not connected")
        document = await self.collection.find_one({"key": key})
        if document:
            return document.get("value", default)
        return default

    async def set(self, key: str, value: Any) -> None:
        """Set a value for a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        document = {"key": key, "value": value, "updated_at": datetime.utcnow()}

        if self.collection is None:
            raise RuntimeError("Database not connected")
        await self.collection.update_one(
            {"key": key},
            {"$set": document, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

    async def delete(self, key: str) -> None:
        """Delete a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.collection is None:
            raise RuntimeError("Database not connected")
        await self.collection.delete_one({"key": key})

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.collection is None:
            raise RuntimeError("Database not connected")
        count = await self.collection.count_documents({"key": key})
        return bool(count > 0)

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if pattern == "*":
            if self.collection is None:
                raise RuntimeError("Database not connected")
            cursor = self.collection.find({}, {"key": 1})
        else:
            # Convert shell pattern to MongoDB regex
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            if self.collection is None:
                raise RuntimeError("Database not connected")
            cursor = self.collection.find({"key": {"$regex": f"^{regex_pattern}$"}}, {"key": 1})

        documents = await cursor.to_list(length=None)
        return [doc["key"] for doc in documents]

    async def clear(self) -> None:
        """Clear all data."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        if self.collection is None:
            raise RuntimeError("Database not connected")
        await self.collection.delete_many({})

    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            if not self.connected:
                return {"status": "disconnected", "error": "Not connected to database"}

            # Ping the database
            if self.client is None:
                raise RuntimeError("Database not connected")
            await self.client.admin.command("ping")

            # Get collection stats
            if self.collection is None:
                raise RuntimeError("Database not connected")
            count = await self.collection.count_documents({})

            return {
                "status": "healthy",
                "type": "mongodb",
                "connected": True,
                "total_keys": count,
                "database": self.config.database,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "connected": False}

    def _build_connection_url(self) -> str:
        """Build MongoDB connection URL."""
        if self.config.url:
            return self.config.url

        # Build connection string
        if self.config.username and self.config.password:
            auth_part = f"{self.config.username}:{self.config.password}@"
        else:
            auth_part = ""

        ssl_part = ""
        if self.config.ssl_enabled:
            ssl_part = "?ssl=true"
            if self.config.ssl_cert_path:
                ssl_part += f"&ssl_certfile={self.config.ssl_cert_path}"
            if self.config.ssl_key_path:
                ssl_part += f"&ssl_keyfile={self.config.ssl_key_path}"
            if self.config.ssl_ca_path:
                ssl_part += f"&ssl_ca_certs={self.config.ssl_ca_path}"

        replica_set_part = ""
        if self.config.replica_set:
            replica_set_part = f"&replicaSet={self.config.replica_set}"

        return f"mongodb://{auth_part}{self.config.host}:{self.config.port}/{self.config.database}{ssl_part}{replica_set_part}"


class MemoryAdapter(DatabaseAdapter):
    """In-memory database adapter for testing and development."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        super().__init__(config or DatabaseConfig(type="memory"))
        self.data: Dict[str, Any] = {}

    async def connect(self) -> None:
        """Connect to the in-memory database."""
        self.connected = True
        logger.info("Connected to in-memory database")

    async def disconnect(self) -> None:
        """Disconnect from the in-memory database."""
        self.connected = False
        self.data.clear()
        logger.info("Disconnected from in-memory database")

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        return self.data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Set a value for a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        self.data[key] = value

    async def delete(self, key: str) -> None:
        """Delete a key."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        self.data.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        return key in self.data

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        import fnmatch

        if pattern == "*":
            return list(self.data.keys())
        return [key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)]

    async def clear(self) -> None:
        """Clear all data."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        self.data.clear()

    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        return {
            "status": "healthy" if self.connected else "disconnected",
            "type": "memory",
            "connected": self.connected,
            "total_keys": len(self.data) if self.connected else 0,
        }


# Database Factory
def create_database_adapter(config: DatabaseConfig) -> DatabaseAdapter:
    """Create database adapter based on configuration."""
    if config.type == "sqlite":
        return SQLAlchemyAdapter(config)
    elif config.type == "postgresql":
        return SQLAlchemyAdapter(config)
    elif config.type in ["mariadb", "mysql"]:
        return SQLAlchemyAdapter(config)
    elif config.type == "mongodb":
        return MongoDBAdapter(config)
    elif config.type == "memory":
        return MemoryAdapter(config)
    else:
        raise ValueError(f"Unsupported database type: {config.type}")


# Transaction Context Manager
class TransactionContext:
    """Database transaction context manager."""

    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter
        self._operations: List[Dict[str, Any]] = []
        self._committed = False

    async def __aenter__(self) -> "TransactionContext":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None and not self._committed:
            await self.commit()
        elif not self._committed:
            await self.rollback()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value within the transaction."""
        # Check pending operations first
        for op in reversed(self._operations):
            if op["type"] == "set" and op["key"] == key:
                return op["value"]
            elif op["type"] == "delete" and op["key"] == key:
                return default

        return await self.adapter.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Set a value within the transaction."""
        self._operations.append({"type": "set", "key": key, "value": value})

    async def delete(self, key: str) -> None:
        """Delete a key within the transaction."""
        self._operations.append({"type": "delete", "key": key})

    async def commit(self) -> None:
        """Commit the transaction."""
        if self._committed:
            return

        for op in self._operations:
            if op["type"] == "set":
                await self.adapter.set(op["key"], op["value"])
            elif op["type"] == "delete":
                await self.adapter.delete(op["key"])

        self._operations.clear()
        self._committed = True

    async def rollback(self) -> None:
        """Rollback the transaction."""
        self._operations.clear()
        self._committed = True


# Default database configuration
def create_default_database_config() -> DatabaseConfig:
    """Create default database configuration (SQLite)."""
    return DatabaseConfig(type="sqlite", path="./nexus.db")


# Database connection examples
DATABASE_URL_EXAMPLES = {
    "sqlite": "sqlite+aiosqlite:///./nexus.db",
    "postgresql": "postgresql+asyncpg://user:password@localhost:5432/nexus",
    "mariadb": "mysql+aiomysql://user:password@localhost:3306/nexus",
    "mongodb": "mongodb://user:password@localhost:27017/nexus",
}


__all__ = [
    "DatabaseAdapter",
    "SQLAlchemyAdapter",
    "MongoDBAdapter",
    "MemoryAdapter",
    "DatabaseConfig",
    "TransactionContext",
    "create_database_adapter",
    "create_default_database_config",
    "DATABASE_URL_EXAMPLES",
]
