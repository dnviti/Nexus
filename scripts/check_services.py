#!/usr/bin/env python3
"""
Service Connectivity Checker for Nexus CI/CD Pipeline

This script checks if required services (PostgreSQL, Redis, MySQL) are available
and ready to accept connections. It's designed to replace redis-cli and other
command-line tools that might not be available in CI environments.
"""

import sys
import time
import socket
import subprocess
from typing import Dict, Optional


def check_tcp_connection(host: str, port: int, timeout: int = 5) -> bool:
    """Check if a TCP connection can be established to the given host and port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, socket.timeout):
        return False


def check_redis(host: str = "localhost", port: int = 6379, timeout: int = 5) -> bool:
    """Check Redis connectivity using Python redis library."""
    try:
        import redis
        r = redis.Redis(host=host, port=port, socket_connect_timeout=timeout)
        r.ping()
        return True
    except Exception:
        # Fallback to TCP connection check
        return check_tcp_connection(host, port, timeout)


def check_postgres(host: str = "localhost", port: int = 5432, timeout: int = 5) -> bool:
    """Check PostgreSQL connectivity."""
    # Try pg_isready first (if available)
    try:
        result = subprocess.run(
            ['pg_isready', '-h', host, '-p', str(port)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try with psycopg2 if available
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            user="postgres",
            password="postgres",
            database="postgres",
            connect_timeout=timeout
        )
        conn.close()
        return True
    except Exception:
        pass

    # Fallback to TCP connection check
    return check_tcp_connection(host, port, timeout)


def check_mysql(host: str = "localhost", port: int = 3306, timeout: int = 5) -> bool:
    """Check MySQL connectivity."""
    # Try mysqladmin ping first (if available)
    try:
        result = subprocess.run(
            ['mysqladmin', 'ping', f'-h{host}', f'-P{port}', '-uroot', '-proot', '--silent'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try with pymysql if available
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user="root",
            password="root",
            connect_timeout=timeout
        )
        conn.close()
        return True
    except Exception:
        pass

    # Fallback to TCP connection check
    return check_tcp_connection(host, port, timeout)


def wait_for_service(
    service_name: str,
    check_func,
    max_attempts: int = 30,
    interval: int = 2,
    **kwargs
) -> bool:
    """Wait for a service to become available."""
    print(f"Waiting for {service_name}...")

    for attempt in range(max_attempts):
        if check_func(**kwargs):
            print(f"✅ {service_name} is ready")
            return True

        if attempt < max_attempts - 1:
            print(f"⏳ {service_name} not ready yet (attempt {attempt + 1}/{max_attempts})")
            time.sleep(interval)

    print(f"❌ {service_name} failed to become ready after {max_attempts} attempts")
    return False


def wait_for_services(services: Dict[str, Dict]) -> bool:
    """Wait for multiple services to become available."""
    all_ready = True

    for service_name, config in services.items():
        check_func = config.pop('check_func')
        if not wait_for_service(service_name, check_func, **config):
            all_ready = False

    return all_ready


def main():
    """Main function to check service availability."""
    import argparse

    parser = argparse.ArgumentParser(description="Check service connectivity")
    parser.add_argument(
        '--services',
        nargs='+',
        choices=['redis', 'postgres', 'mysql', 'all'],
        default=['all'],
        help='Services to check'
    )
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=30,
        help='Maximum number of connection attempts'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Interval between attempts in seconds'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=5,
        help='Connection timeout in seconds'
    )

    args = parser.parse_args()

    # Define available services
    available_services = {
        'redis': {
            'check_func': check_redis,
            'timeout': args.timeout
        },
        'postgres': {
            'check_func': check_postgres,
            'timeout': args.timeout
        },
        'mysql': {
            'check_func': check_mysql,
            'timeout': args.timeout
        }
    }

    # Determine which services to check
    if 'all' in args.services:
        services_to_check = available_services
    else:
        services_to_check = {
            name: config for name, config in available_services.items()
            if name in args.services
        }

    # Add common parameters
    for config in services_to_check.values():
        config['max_attempts'] = args.max_attempts
        config['interval'] = args.interval

    print("🔍 Starting service connectivity checks...")
    print(f"Services to check: {list(services_to_check.keys())}")
    print(f"Max attempts: {args.max_attempts}, Interval: {args.interval}s, Timeout: {args.timeout}s")
    print("-" * 50)

    # Wait for all services
    if wait_for_services(services_to_check):
        print("-" * 50)
        print("🎉 All services are ready!")
        return 0
    else:
        print("-" * 50)
        print("❌ Some services failed to become ready")
        return 1


if __name__ == "__main__":
    sys.exit(main())
