"""
PostgreSQL Connection Wrapper - pg8000 + Cloud SQL Connector

- Lokal TCP (docker-compose) eller Cloud Run via Cloud SQL Connector
- RealDictCursor-stöd för befintlig kod
- Thread-safe och context manager-kompatibel
"""

import os
import threading
import atexit
from typing import Optional, Tuple, List, Dict, Any

from ic_shared.logging import ComponentLogger
from ic_shared.configuration.config import (
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_NAME,
    DATABASE_USER,
    DATABASE_PASSWORD,
    INSTANCE_CONNECTION_NAME,
    IS_CLOUD_RUN,
    IS_LOCAL,
)

try:
    import pg8000
    HAS_PG8000 = True
except ImportError:
    HAS_PG8000 = False

logger = ComponentLogger("DatabaseConnection")

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
        except Exception as e:
            logger.error(f"✗ Error closing Cloud SQL Connector: {e}")
    else:
        logger.debug("[DB.Cleanup] Cloud SQL Connector was not initialized, nothing to close")

atexit.register(_cleanup_connector)

def get_cloud_sql_connector():
    global _cloud_sql_connector
    if _cloud_sql_connector is None:
        with _connector_lock:
            if _cloud_sql_connector is None:
                try:
                    from google.cloud.sql.connector import Connector
                    _cloud_sql_connector = Connector()
                except Exception as e:
                    logger.error(f"Error initializing Cloud SQL Connector: {e}")
                    return None
    return _cloud_sql_connector

# -------------------------------
# Connection Factories
# -------------------------------

def get_connection_pg8000(host, database, user, password, port=5432) -> Optional[PG8000Connection]:
    if not HAS_PG8000:
        logger.error("[DB.TCP] ✗ pg8000 not installed")
        return None
    try:
        # logger.debug(f"Attempting TCP connection to {user}@{host}:{port}/{database}...")
        conn = pg8000.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            timeout=5,
            ssl_context=None
        )
        # logger.info(f"✓ Connected via TCP: {database}@{host}:{port}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"✗ TCP connection failed: {e}")
        return None

def get_connection_pg8000_connector(instance_connection_name, database, user, password) -> Optional[PG8000Connection]:
    connector = get_cloud_sql_connector()
    if not connector:
        logger.error("[DB] No Cloud SQL Connector available")
        return None
    try:
        from google.cloud.sql.connector import IPTypes
        logger.debug(f"Attempting connection to {instance_connection_name}...")
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=user,
            password=password,
            timeout=15,  # Increased from 5s to allow connector initialization time
            db=database,
            ip_type=IPTypes.PRIVATE
        )
        logger.debug(f"✓ Connection established to {instance_connection_name}")
        return PG8000Connection(conn)
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return None

# -------------------------------
# Unified get_connection
# -------------------------------

def get_connection(
    host=None, port=None, database=None, user=None, password=None,
    use_connector: bool = False, instance_connection_name=None
) -> Optional[PG8000Connection]:

    # Use provided parameters or fall back to config values (no os.getenv duplicates)
    host = host or DATABASE_HOST
    port = port or DATABASE_PORT
    database = database or DATABASE_NAME
    user = user or DATABASE_USER
    password = password or DATABASE_PASSWORD
    
    # Detect connection mode
    is_local = IS_LOCAL  # From ENVIRONMENT=local
    is_cloud_run = IS_CLOUD_RUN
    is_cloud_function = os.getenv("FUNCTION_TARGET") is not None or os.getenv("FUNCTION_SIGNATURE_TYPE") is not None
    has_instance_connection = INSTANCE_CONNECTION_NAME is not None

    # logger.debug(f"[DB] Connection mode: is_local={is_local}, is_cloud_run={is_cloud_run}, is_cloud_function={is_cloud_function}, has_instance_connection={has_instance_connection}")
    
    # Connection priority:
    # 1) LOCAL: Always use TCP if ENVIRONMENT=local (docker-compose or local functions-framework)
    # 2) CLOUD: Use Cloud SQL Connector if INSTANCE_CONNECTION_NAME is set
    # 3) REMOTE: Use TCP to remote host
    
    if is_local:
        # Local environment - always use TCP connection
        # logger.debug(f"[DB.Local] Using TCP connection: {user}@{host}:{port}/{database}")
        conn = get_connection_pg8000(host, database, user, password, port)
    elif use_connector or (is_cloud_run or is_cloud_function) and has_instance_connection:
        # Cloud environment with Cloud SQL Connector
        instance_conn_name = instance_connection_name or INSTANCE_CONNECTION_NAME
        
        if not instance_conn_name:
            logger.error("[DB] ✗ get_connection() FAILURE - INSTANCE_CONNECTION_NAME not set in Cloud environment")
            return None
        # logger.debug(f"[DB.Cloud] Using Cloud SQL Connector: {instance_conn_name}")
        conn = get_connection_pg8000_connector(instance_conn_name, database, user, password)
    else:
        # Remote TCP connection
        # logger.debug(f"[DB.Remote] Using TCP connection: {user}@{host}:{port}/{database}")
        conn = get_connection_pg8000(host, database, user, password, port)
    if not conn:
        logger.error("[DB] ✗ get_connection() FAILURE - Connection is None")
    
    return conn

# -----------------------------------------------
# Utility Functions for Direct SQL Execution
# -----------------------------------------------

def fetch_all(sql: str, params: Tuple = None) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Execute a SELECT query and return all results as list of dicts.
    
    Args:
        sql: SQL SELECT query to execute
        params: Optional tuple of query parameters for parameterized queries
    
    Returns:
        Tuple of (results, success)
        - results: List of dicts if successful, empty list if failed
        - success: Boolean indicating if query executed successfully
    
    Example:
        results, success = fetch_all("SELECT * FROM users WHERE id = %s", (user_id,))
        if success:
            logger.info(f"Found {len(results)} users")
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.error("[fetch_all] 🔴 get_connection() returned None")
            return [], False
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        results = cursor.fetchall()
        cursor.close()
        
        return [dict(row) for row in results], True
    
    except Exception as e:
        logger.error(f"🔴 fetch_all failed: {e}")
        return [], False
    
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def execute_sql(sql: str, params: Tuple = None) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Execute UPDATE/INSERT/DELETE query and return results.
    
    Args:
        sql: SQL UPDATE/INSERT/DELETE query to execute
        params: Optional tuple of query parameters for parameterized queries
    
    Returns:
        Tuple of (results, success)
        - results: List of dicts if RETURNING clause used, else [{"affected_rows": count}]
        - success: Boolean indicating if query executed successfully
    
    Example:
        results, success = execute_sql(
            "UPDATE users SET name = %s WHERE id = %s RETURNING id",
            ("John", user_id)
        )
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.error("[execute_sql] 🔴 get_connection() returned None")
            return [], False
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        # For statements with RETURNING, fetch results
        # For statements without RETURNING, just commit (pg8000 doesn't support rowcount without results)
        has_returning = 'RETURNING' in sql.upper()
        
        if has_returning:
            results = cursor.fetchall()
            cursor.close()
        else:
            # No RETURNING - no result set to fetch
            # pg8000 doesn't support rowcount without fetchall(), so just close
            results = []
            cursor.close()
        
        # Commit transaction
        conn.commit()
        
        if results:
            # RETURNING clause was used
            return [dict(row) for row in results], True
        else:
            # No RETURNING clause - assume success if no exception was raised
            # (pg8000 doesn't provide rowcount without a result set)
            return [{"affected_rows": 1}], True
    
    except Exception as e:
        logger.error(f"🔴 execute_sql failed: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return [], False
    
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# Export public API
# Only exports what's used outside this module
__all__ = [
    'get_connection',          # Unified connection factory (TCP or Cloud SQL Connector)
    'RealDictCursor',          # pg8000 cursor wrapper (dict-like rows)
    'fetch_all',               # Execute SELECT queries and return list of dicts
    'execute_sql',             # Execute UPDATE/INSERT/DELETE with automatic transaction management
]
