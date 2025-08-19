"""
Common Decorators for Nexus Plugins

This module provides shared decorators that can be used across all plugins
to add common functionality like logging, error handling, caching, and performance monitoring.
"""

import time
import logging
import asyncio
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simple in-memory cache for demonstration
_cache: Dict[str, Dict[str, Any]] = {}


def log_execution(
    log_args: bool = True, log_result: bool = False, log_duration: bool = True, level: str = "INFO"
):
    """
    Decorator to log function execution.

    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_duration: Whether to log execution duration
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"

            # Log function entry
            log_msg = f"Executing {func_name}"
            if log_args and (args or kwargs):
                log_msg += f" with args={args}, kwargs={kwargs}"

            getattr(logger, level.lower())(log_msg)

            try:
                result = await func(*args, **kwargs)

                # Log successful completion
                if log_duration:
                    duration = time.time() - start_time
                    logger.info(f"{func_name} completed in {duration:.3f}s")

                if log_result:
                    logger.debug(f"{func_name} result: {result}")

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func_name} failed after {duration:.3f}s: {str(e)}", exc_info=True)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"

            # Log function entry
            log_msg = f"Executing {func_name}"
            if log_args and (args or kwargs):
                log_msg += f" with args={args}, kwargs={kwargs}"

            getattr(logger, level.lower())(log_msg)

            try:
                result = func(*args, **kwargs)

                # Log successful completion
                if log_duration:
                    duration = time.time() - start_time
                    logger.info(f"{func_name} completed in {duration:.3f}s")

                if log_result:
                    logger.debug(f"{func_name} result: {result}")

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func_name} failed after {duration:.3f}s: {str(e)}", exc_info=True)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def handle_errors(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = True,
    error_message: Optional[str] = None,
):
    """
    Decorator to handle errors gracefully.

    Args:
        default_return: Value to return if error occurs and reraise=False
        log_errors: Whether to log errors
        reraise: Whether to re-raise the exception
        error_message: Custom error message to log
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    msg = error_message or f"Error in {func.__name__}: {str(e)}"
                    logger.error(msg, exc_info=True)

                if reraise:
                    raise
                else:
                    return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    msg = error_message or f"Error in {func.__name__}: {str(e)}"
                    logger.error(msg, exc_info=True)

                if reraise:
                    raise
                else:
                    return default_return

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def cache_result(
    ttl_seconds: int = 300, key_func: Optional[Callable] = None, use_args: bool = True
):
    """
    Decorator to cache function results.

    Args:
        ttl_seconds: Time-to-live for cached results in seconds
        key_func: Function to generate cache key from args/kwargs
        use_args: Whether to include function arguments in cache key
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__qualname__}"
                if use_args:
                    cache_key = f"{func_name}:{hash((args, tuple(sorted(kwargs.items()))))}"
                else:
                    cache_key = func_name

            # Check cache
            if cache_key in _cache:
                cached_data = _cache[cache_key]
                if datetime.now() < cached_data["expires"]:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data["result"]
                else:
                    # Cache expired
                    del _cache[cache_key]
                    logger.debug(f"Cache expired for {cache_key}")

            # Execute function and cache result
            result = await func(*args, **kwargs)

            _cache[cache_key] = {
                "result": result,
                "expires": datetime.now() + timedelta(seconds=ttl_seconds),
                "created": datetime.now(),
            }

            logger.debug(f"Cache stored for {cache_key}")
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__qualname__}"
                if use_args:
                    cache_key = f"{func_name}:{hash((args, tuple(sorted(kwargs.items()))))}"
                else:
                    cache_key = func_name

            # Check cache
            if cache_key in _cache:
                cached_data = _cache[cache_key]
                if datetime.now() < cached_data["expires"]:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data["result"]
                else:
                    # Cache expired
                    del _cache[cache_key]
                    logger.debug(f"Cache expired for {cache_key}")

            # Execute function and cache result
            result = func(*args, **kwargs)

            _cache[cache_key] = {
                "result": result,
                "expires": datetime.now() + timedelta(seconds=ttl_seconds),
                "created": datetime.now(),
            }

            logger.debug(f"Cache stored for {cache_key}")
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def rate_limit(max_calls: int = 100, window_seconds: int = 60):
    """
    Simple rate limiting decorator.

    Args:
        max_calls: Maximum number of calls allowed
        window_seconds: Time window in seconds
    """
    call_history: Dict[str, list] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            now = time.time()

            # Initialize or clean up call history
            if func_name not in call_history:
                call_history[func_name] = []

            # Remove old calls outside the window
            call_history[func_name] = [
                call_time
                for call_time in call_history[func_name]
                if now - call_time < window_seconds
            ]

            # Check rate limit
            if len(call_history[func_name]) >= max_calls:
                raise Exception(
                    f"Rate limit exceeded for {func_name}: "
                    f"{max_calls} calls per {window_seconds} seconds"
                )

            # Record this call
            call_history[func_name].append(now)

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            now = time.time()

            # Initialize or clean up call history
            if func_name not in call_history:
                call_history[func_name] = []

            # Remove old calls outside the window
            call_history[func_name] = [
                call_time
                for call_time in call_history[func_name]
                if now - call_time < window_seconds
            ]

            # Check rate limit
            if len(call_history[func_name]) >= max_calls:
                raise Exception(
                    f"Rate limit exceeded for {func_name}: "
                    f"{max_calls} calls per {window_seconds} seconds"
                )

            # Record this call
            call_history[func_name].append(now)

            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def measure_performance(include_memory: bool = False):
    """
    Decorator to measure function performance.

    Args:
        include_memory: Whether to measure memory usage (requires psutil)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import psutil
            import os

            start_time = time.time()
            start_memory = None
            process = None

            if include_memory:
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss

            try:
                result = await func(*args, **kwargs)

                # Calculate metrics
                duration = time.time() - start_time
                metrics = {
                    "function": f"{func.__module__}.{func.__qualname__}",
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat(),
                }

                if include_memory and start_memory and process:
                    end_memory = process.memory_info().rss
                    metrics["memory_delta_bytes"] = end_memory - start_memory
                    metrics["memory_usage_mb"] = end_memory / 1024 / 1024

                logger.info(f"Performance metrics: {metrics}")

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {str(e)}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None
            process = None

            if include_memory:
                try:
                    import psutil
                    import os

                    process = psutil.Process(os.getpid())
                    start_memory = process.memory_info().rss
                except ImportError:
                    logger.warning("psutil not available for memory monitoring")

            try:
                result = func(*args, **kwargs)

                # Calculate metrics
                duration = time.time() - start_time
                metrics = {
                    "function": f"{func.__module__}.{func.__qualname__}",
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat(),
                }

                if include_memory and start_memory and process:
                    end_memory = process.memory_info().rss
                    metrics["memory_delta_bytes"] = end_memory - start_memory
                    metrics["memory_usage_mb"] = end_memory / 1024 / 1024

                logger.info(f"Performance metrics: {metrics}")

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {str(e)}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff_multiplier: float = 2.0):
    """
    Decorator to retry function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_multiplier: Multiplier for delay on each retry
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise e

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}, "
                        f"retrying in {delay:.1f}s"
                    )

                    await asyncio.sleep(delay)
                    delay *= backoff_multiplier

            # Should never reach here, but just in case
            raise last_exception or RuntimeError(
                f"Function {func.__name__} failed after {max_attempts} attempts"
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise e

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}, "
                        f"retrying in {delay:.1f}s"
                    )

                    time.sleep(delay)
                    delay *= backoff_multiplier

            # Should never reach here, but just in case
            raise last_exception or RuntimeError(
                f"Function {func.__name__} failed after {max_attempts} attempts"
            )

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def clear_cache():
    """Clear the global cache."""
    global _cache
    _cache.clear()
    logger.info("Cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    now = datetime.now()
    active_entries = 0
    expired_entries = 0

    for key, data in _cache.items():
        if now < data["expires"]:
            active_entries += 1
        else:
            expired_entries += 1

    return {
        "total_entries": len(_cache),
        "active_entries": active_entries,
        "expired_entries": expired_entries,
        "cache_keys": list(_cache.keys()),
    }
