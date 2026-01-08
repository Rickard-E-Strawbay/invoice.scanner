"""
Shared Database Module

EXPORTS (two levels of clarity):

LEVEL 1 - connection.py (internal implementation):
  - get_connection: Unified factory (auto-detects Cloud Run vs Local)
  - RealDictCursor: pg8000 wrapper for dict-like row access
  - execute_sql: Execute SQL with auto transaction management

LEVEL 2 - __init__.py (this file - re-exports everything):
  All of the above via single import point

USAGE:
  # These are equivalent:
  from ic_shared.configuration.config import get_connection, execute_sql, DB_CONFIG
  from ic_shared.database import get_connection, execute_sql
  from ic_shared.database.connection import get_connection, execute_sql
"""

from .connection import (
    get_connection,
    RealDictCursor,
    execute_sql,
)

__all__ = [
    # Connection functions (from connection.py)
    'get_connection',
    'RealDictCursor',
    'execute_sql',
    # Configuration (from config.py)
    'DB_CONFIG',
    'DATABASE_URL',
    'IS_CLOUD_RUN',
    'DATABASE_HOST',
    'DATABASE_PORT',
    'DATABASE_USER',
    'DATABASE_PASSWORD',
    'DATABASE_NAME',
    'INSTANCE_CONNECTION_NAME'
]

