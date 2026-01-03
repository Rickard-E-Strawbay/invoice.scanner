"""
Shared Database Module

Provides unified database abstractions for all services:
- connection: PostgreSQL driver wrapper with RealDictCursor compatibility
- config: Unified database configuration for Cloud Run and Local modes
"""

from .connection import (
    PG8000DictRow,
    PG8000DictCursor,
    PG8000Connection,
    RealDictCursor,
    get_connection,
    get_connection_pg8000,
    get_connection_pg8000_connector,
)

from .config import (
    DB_CONFIG,
    DATABASE_URL,
    IS_CLOUD_RUN,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
    INSTANCE_CONNECTION_NAME,
)

__all__ = [
    # Connection classes and functions
    'PG8000DictRow',
    'PG8000DictCursor', 
    'PG8000Connection',
    'RealDictCursor',
    'get_connection',
    'get_connection_pg8000',
    'get_connection_pg8000_connector',
    # Config exports
    'DB_CONFIG',
    'DATABASE_URL',
    'IS_CLOUD_RUN',
    'DATABASE_HOST',
    'DATABASE_PORT',
    'DATABASE_USER',
    'DATABASE_PASSWORD',
    'DATABASE_NAME',
    'INSTANCE_CONNECTION_NAME',
]

