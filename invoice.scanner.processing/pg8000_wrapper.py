"""
PostgreSQL pg8000 Wrapper with RealDictCursor Compatibility

Provides a unified database interface that:
- Works with pg8000 (Pure Python PostgreSQL driver)
- Supports local TCP connections (docker-compose)
- Supports future Cloud SQL Connector (Cloud Run)
- Implements RealDictCursor-like interface for backward compatibility

Migration from psycopg2:
- Existing code using RealDictCursor continues to work
- Same dict-like row access patterns preserved
- Connection pooling for efficiency
"""

import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager

try:
    import pg8000.native
    HAS_PG8000 = True
except ImportError:
    HAS_PG8000 = False

logger = logging.getLogger(__name__)


class PG8000DictRow:
    """
    Dictionary-like wrapper for pg8000 rows.
    
    Provides psycopg2.RealDictCursor-compatible interface.
    Allows: row['column_name'] access and row.get('column_name', default)
    """
    
    def __init__(self, columns: List[str], values: Tuple):
        """
        Initialize row wrapper.
        
        Args:
            columns: List of column names from cursor description
            values: Tuple of row values
        """
        self._row_dict = dict(zip(columns, values))
    
    def __getitem__(self, key):
        return self._row_dict[key]
    
    def __setitem__(self, key, value):
        self._row_dict[key] = value
    
    def __contains__(self, key):
        return key in self._row_dict
    
    def __repr__(self):
        return repr(self._row_dict)
    
    def __str__(self):
        return str(self._row_dict)
    
    def get(self, key, default=None):
        """Get value with default fallback (dict-like)"""
        return self._row_dict.get(key, default)
    
    def keys(self):
        """Return column names (dict-like)"""
        return self._row_dict.keys()
    
    def values(self):
        """Return column values (dict-like)"""
        return self._row_dict.values()
    
    def items(self):
        """Return (key, value) tuples (dict-like)"""
        return self._row_dict.items()
    
    def to_dict(self):
        """Explicit conversion to dict"""
        return self._row_dict.copy()


class PG8000DictCursor:
    """
    Dictionary-like cursor for pg8000.
    
    Provides psycopg2.RealDictCursor-compatible interface.
    Rows are accessible as dictionaries: cursor.fetchone()['column_name']
    """
    
    def __init__(self, pg8000_cursor):
        """
        Initialize wrapper cursor.
        
        Args:
            pg8000_cursor: pg8000 cursor object from connection.cursor()
        """
        self._cursor = pg8000_cursor
        self._columns = None
    
    def execute(self, query: str, params: Tuple = None) -> 'PG8000DictCursor':
        """
        Execute query.
        
        Args:
            query: SQL query string
            params: Query parameters (tuple)
        
        Returns:
            Self for chaining
        """
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        
        # Cache column names from cursor description
        if self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        
        return self
    
    def fetchone(self) -> Optional[PG8000DictRow]:
        """
        Fetch one row as dictionary.
        
        Returns:
            PG8000DictRow (dict-like) or None if no more rows
        """
        row = self._cursor.fetchone()
        if row is None:
            return None
        
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        
        return PG8000DictRow(self._columns or [], row)
    
    def fetchall(self) -> List[PG8000DictRow]:
        """
        Fetch all rows as dictionaries.
        
        Returns:
            List of PG8000DictRow objects
        """
        rows = self._cursor.fetchall()
        
        if not rows:
            return []
        
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        
        return [PG8000DictRow(self._columns or [], row) for row in rows]
    
    def fetchmany(self, size: int = 1) -> List[PG8000DictRow]:
        """
        Fetch multiple rows as dictionaries.
        
        Args:
            size: Number of rows to fetch
        
        Returns:
            List of PG8000DictRow objects
        """
        rows = self._cursor.fetchmany(size)
        
        if not rows:
            return []
        
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        
        return [PG8000DictRow(self._columns or [], row) for row in rows]
    
    @property
    def rowcount(self) -> int:
        """Number of rows affected by last operation"""
        return self._cursor.rowcount
    
    @property
    def description(self):
        """Cursor description (column metadata)"""
        return self._cursor.description
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close cursor"""
        if self._cursor:
            self._cursor.close()
    
    def __iter__(self):
        """Iterate over rows as dictionaries"""
        for row in self._cursor.fetchall():
            if self._columns is None and self._cursor.description:
                self._columns = [desc[0] for desc in self._cursor.description]
            yield PG8000DictRow(self._columns or [], row)


class PG8000Connection:
    """
    Wrapper for pg8000 connection.
    
    Provides psycopg2-compatible interface:
    - cursor(cursor_factory=RealDictCursor) support
    - commit() and rollback()
    - Context manager support
    """
    
    def __init__(self, pg8000_conn):
        """
        Initialize connection wrapper.
        
        Args:
            pg8000_conn: pg8000.native.Connection object
        """
        self._conn = pg8000_conn
    
    def cursor(self, cursor_factory=None):
        """
        Get cursor, optionally with custom factory.
        
        Args:
            cursor_factory: Optional cursor class (e.g., RealDictCursor)
                          For compatibility, we return PG8000DictCursor if provided
        
        Returns:
            PG8000DictCursor if cursor_factory provided, else standard cursor
        """
        base_cursor = self._conn.cursor()
        
        if cursor_factory is not None:
            # Support both RealDictCursor class and string name
            if cursor_factory == RealDictCursor or (
                hasattr(cursor_factory, '__name__') and 
                cursor_factory.__name__ == 'RealDictCursor'
            ):
                return PG8000DictCursor(base_cursor)
        
        # Return wrapped cursor by default for consistency
        return PG8000DictCursor(base_cursor)
    
    def commit(self):
        """Commit transaction"""
        self._conn.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self._conn.rollback()
    
    def close(self):
        """Close connection"""
        self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def RealDictCursor(cursor):
    """
    Compatibility function for psycopg2-style cursor creation.
    
    Used as: cursor_factory=RealDictCursor in cursor() calls
    """
    return PG8000DictCursor(cursor)


def get_connection_pg8000(
    host: str,
    database: str,
    user: str,
    password: str,
    port: int = 5432
) -> Optional[PG8000Connection]:
    """
    Create pg8000 database connection.
    
    Args:
        host: Database host
        database: Database name
        user: Username
        password: Password
        port: Port (default 5432)
    
    Returns:
        PG8000Connection wrapper or None if connection fails
    """
    if not HAS_PG8000:
        logger.error("[DB] pg8000 not installed. Run: pip install pg8000")
        return None
    
    try:
        conn = pg8000.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            ssl_context=None  # SSL disabled for local docker-compose
        )
        logger.info(f"[DB] Connected via pg8000 TCP: {database}@{host}:{port}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"[DB] pg8000 connection failed: {e}", exc_info=True)
        return None


def get_connection_pg8000_connector(
    instance_connection_name: str,
    database: str,
    user: str,
    password: str
) -> Optional[PG8000Connection]:
    """
    Create pg8000 connection via Cloud SQL Connector (Cloud Run).
    
    Args:
        instance_connection_name: Cloud SQL instance connection name
                                 (project:region:instance)
        database: Database name
        user: Username
        password: Password
    
    Returns:
        PG8000Connection wrapper or None if connection fails
    """
    if not HAS_PG8000:
        logger.error("[DB] pg8000 not installed. Run: pip install pg8000")
        return None
    
    try:
        from google.cloud.sql.connector import Connector
        
        connector = Connector()
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=user,
            password=password,
            db=database
        )
        logger.info(f"[DB] Connected via Cloud SQL Connector: {database}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"[DB] Cloud SQL Connector connection failed: {e}", exc_info=True)
        return None


# Connection pooling (simple, non-pooling version for compatibility)
_connection_cache = None


def get_connection(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None,
    use_connector: bool = False,
    instance_connection_name: str = None
) -> Optional[PG8000Connection]:
    """
    Get or create database connection (with optional caching).
    
    Args:
        host: Database host (read from DATABASE_HOST env if not provided)
        port: Database port (read from DATABASE_PORT env if not provided)
        database: Database name (read from DATABASE_NAME env if not provided)
        user: Username (read from DATABASE_USER env if not provided)
        password: Password (read from DATABASE_PASSWORD env if not provided)
        use_connector: Use Cloud SQL Connector instead of direct TCP
        instance_connection_name: Cloud SQL instance name for Connector
    
    Returns:
        PG8000Connection or None if connection fails
    """
    # Read from environment if not provided
    host = host or os.getenv('DATABASE_HOST', 'localhost')
    port = port or int(os.getenv('DATABASE_PORT', 5432))
    database = database or os.getenv('DATABASE_NAME', 'invoice_scanner')
    user = user or os.getenv('DATABASE_USER', 'scanner')
    password = password or os.getenv('DATABASE_PASSWORD', 'password')
    
    if use_connector:
        if not instance_connection_name:
            instance_connection_name = os.getenv('CLOUD_SQL_INSTANCE')
        
        if not instance_connection_name:
            logger.error("[DB] Connector mode requested but CLOUD_SQL_INSTANCE not set")
            return None
        
        return get_connection_pg8000_connector(
            instance_connection_name,
            database,
            user,
            password
        )
    else:
        return get_connection_pg8000(
            host,
            database,
            user,
            password,
            port
        )


__all__ = [
    'PG8000DictRow',
    'PG8000DictCursor',
    'PG8000Connection',
    'RealDictCursor',
    'get_connection',
    'get_connection_pg8000',
    'get_connection_pg8000_connector',
]
