"""
PostgreSQL Connection Wrapper - pg8000 + Cloud SQL Connector

- Lokal TCP (docker-compose) eller Cloud Run via Cloud SQL Connector
- RealDictCursor-stöd för befintlig kod
- Thread-safe och context manager-kompatibel
"""

import os
import threading
import logging
import atexit
from typing import Optional, Tuple, List, Dict, Any

try:
    import pg8000
    HAS_PG8000 = True
except ImportError:
    HAS_PG8000 = False

logger = logging.getLogger(__name__)

# -------------------------------
# RealDictCursor Wrapper
# -------------------------------

class PG8000DictRow:
    def __init__(self, columns: List[str], values: Tuple):
        self._row_dict = dict(zip(columns, values))

    def __getitem__(self, key): return self._row_dict[key]
    def __setitem__(self, key, value): self._row_dict[key] = value
    def __contains__(self, key): return key in self._row_dict
    def get(self, key, default=None): return self._row_dict.get(key, default)
    def keys(self): return self._row_dict.keys()
    def values(self): return self._row_dict.values()
    def items(self): return self._row_dict.items()
    def to_dict(self): return self._row_dict.copy()
    def __repr__(self): return repr(self._row_dict)

class PG8000DictCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self._columns = None

    def execute(self, query: str, params: Tuple = None):
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        if self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None: return None
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        return PG8000DictRow(self._columns, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows: return []
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        return [PG8000DictRow(self._columns, row) for row in rows]

    def fetchmany(self, size: int = 1):
        rows = self._cursor.fetchmany(size)
        if not rows: return []
        if self._columns is None and self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        return [PG8000DictRow(self._columns, row) for row in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()

    def __iter__(self):
        for row in self._cursor.fetchall():
            if self._columns is None and self._cursor.description:
                self._columns = [desc[0] for desc in self._cursor.description]
            yield PG8000DictRow(self._columns, row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

def RealDictCursor(cursor):  # kompatibilitet med befintlig kod
    return PG8000DictCursor(cursor)

# -------------------------------
# Connection Wrapper
# -------------------------------

class PG8000Connection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, cursor_factory=None):
        cur = self._conn.cursor()
        if cursor_factory:
            return PG8000DictCursor(cur)
        return PG8000DictCursor(cur)

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): self._conn.close()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        else: self.commit()
        self.close()

# -------------------------------
# Cloud SQL Connector (lazy, thread-safe)
# -------------------------------

_connector_lock = threading.Lock()
_cloud_sql_connector = None

def _cleanup_connector():
    """Close Cloud SQL Connector on program exit"""
    global _cloud_sql_connector
    if _cloud_sql_connector:
        try:
            _cloud_sql_connector.close()
            logger.info("[DB] Cloud SQL Connector closed")
        except Exception as e:
            logger.error(f"[DB] Error closing Cloud SQL Connector: {e}")

atexit.register(_cleanup_connector)

def get_cloud_sql_connector():
    global _cloud_sql_connector
    if _cloud_sql_connector is None:
        with _connector_lock:
            if _cloud_sql_connector is None:
                try:
                    from google.cloud.sql.connector import Connector
                    _cloud_sql_connector = Connector()
                    logger.info("[DB] Cloud SQL Connector initialized")
                except Exception as e:
                    logger.error(f"[DB] Failed to init Cloud SQL Connector: {e}")
                    return None
    return _cloud_sql_connector

# -------------------------------
# Connection Factories
# -------------------------------

def get_connection_pg8000(host, database, user, password, port=5432) -> Optional[PG8000Connection]:
    if not HAS_PG8000:
        logger.error("[DB] pg8000 not installed")
        return None
    try:
        conn = pg8000.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            timeout=5,
            ssl_context=None
        )
        logger.info(f"[DB] Connected via TCP: {database}@{host}:{port}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"[DB] TCP connection failed: {e}")
        return None

def get_connection_pg8000_connector(instance_connection_name, database, user, password) -> Optional[PG8000Connection]:
    connector = get_cloud_sql_connector()
    if not connector:
        logger.error("[DB] No Cloud SQL Connector available")
        return None
    try:
        from google.cloud.sql.connector import IPTypes
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=user,
            password=password,
            db=database,
            ip_type=IPTypes.PRIVATE
        )
        logger.info(f"[DB] Connected via Cloud SQL Connector: {database}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"[DB] Cloud SQL Connector connection failed: {e}")
        return None

# -------------------------------
# Unified get_connection
# -------------------------------

def get_connection(
    host=None, port=None, database=None, user=None, password=None,
    use_connector: bool = False, instance_connection_name=None
) -> Optional[PG8000Connection]:
    host = host or os.getenv("DATABASE_HOST", "localhost")
    port = port or int(os.getenv("DATABASE_PORT", 5432))
    database = database or os.getenv("DATABASE_NAME", "invoice_scanner")
    user = user or os.getenv("DATABASE_USER", "scanner")
    password = password or os.getenv("DATABASE_PASSWORD", "password")

    is_cloud_run = os.getenv("K_SERVICE") is not None

    if use_connector or is_cloud_run:
        instance_connection_name = instance_connection_name or os.getenv("CLOUD_SQL_INSTANCE")
        if not instance_connection_name:
            logger.error("[DB] Connector requested but CLOUD_SQL_INSTANCE not set")
            return None
        return get_connection_pg8000_connector(instance_connection_name, database, user, password)
    else:
        return get_connection_pg8000(host, database, user, password, port)

# Export public API
__all__ = [
    'PG8000DictRow',
    'PG8000DictCursor',
    'PG8000Connection',
    'RealDictCursor',
    'get_connection',
    'get_connection_pg8000',
    'get_connection_pg8000_connector',
    'get_cloud_sql_connector',
]
