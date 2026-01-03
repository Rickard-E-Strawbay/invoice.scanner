"""
Unified Database Configuration for Invoice Scanner

Connection modes (shared across all services):
- Cloud Run: pg8000 via Cloud SQL Connector (Private IP, IAM auth)
- Local docker-compose: pg8000 TCP to db service

Uses pg8000 (Pure Python PostgreSQL driver) for both environments:
- Works with Cloud SQL Connector (only supports: pymysql, pg8000, pytds)
- Works with local TCP connections
- Provides RealDictCursor compatibility layer for existing code

Used by:
- invoice.scanner.api (Flask REST API)
- invoice.scanner.processing (Worker Service)
- invoice.scanner.cloud.functions (Cloud Functions - deprecated)
"""
import os
from urllib.parse import quote_plus

from .connection import (
    get_connection as get_pg8000_connection,
    RealDictCursor
)

# Environment detection
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None

# Database connection settings
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')
INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')  # Cloud Run only

print(f"[db_config] Environment: {'Cloud Run' if IS_CLOUD_RUN else 'Local'}")
print(f"[db_config] Driver: pg8000 (Pure Python PostgreSQL)")

if IS_CLOUD_RUN:
    # ==========================================
    # Cloud Run mode: pg8000 via Cloud SQL Connector
    # ==========================================
    if not all([INSTANCE_CONNECTION_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        print("[db_config] ERROR: Missing Cloud SQL Connector configuration for Cloud Run")
        print(f"[db_config] INSTANCE_CONNECTION_NAME={INSTANCE_CONNECTION_NAME}")
        print(f"[db_config] DATABASE_USER={DATABASE_USER}")
        print(f"[db_config] DATABASE_PASSWORD={'***' if DATABASE_PASSWORD else 'not set'}")
        print(f"[db_config] DATABASE_NAME={DATABASE_NAME}")
        raise ValueError(
            "Missing required Cloud SQL environment variables for Cloud Run:\n"
            "  - INSTANCE_CONNECTION_NAME\n"
            "  - DATABASE_USER\n"
            "  - DATABASE_PASSWORD\n"
            "  - DATABASE_NAME"
        )
    
    print(f"[db_config] Using Cloud SQL Connector with pg8000")
    print(f"[db_config] Instance: {INSTANCE_CONNECTION_NAME}")
    print(f"[db_config] User: {DATABASE_USER}")
    print(f"[db_config] Database: {DATABASE_NAME}")
    
    def get_connection():
        """Get database connection via Cloud SQL Connector (pg8000)"""
        return get_pg8000_connection(
            use_connector=True,
            instance_connection_name=INSTANCE_CONNECTION_NAME,
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD
        )
    
    # For compatibility
    DB_CONFIG = {
        'instance_connection_name': INSTANCE_CONNECTION_NAME,
        'driver': 'pg8000',
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'database': DATABASE_NAME
    }
    DATABASE_URL = None
    ODBC_CONNECTION_STRING = None

else:
    # ==========================================
    # Local mode: pg8000 TCP
    # ==========================================
    if not all([DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        print("[db_config] ERROR: Missing database configuration for local mode")
        print(f"[db_config] DATABASE_HOST={DATABASE_HOST}")
        print(f"[db_config] DATABASE_USER={DATABASE_USER}")
        print(f"[db_config] DATABASE_PASSWORD={'***' if DATABASE_PASSWORD else 'not set'}")
        print(f"[db_config] DATABASE_NAME={DATABASE_NAME}")
        raise ValueError(
            "Missing required database environment variables for local mode:\n"
            "  - DATABASE_HOST\n"
            "  - DATABASE_USER\n"
            "  - DATABASE_PASSWORD\n"
            "  - DATABASE_NAME"
        )
    
    print(f"[db_config] Using pg8000 TCP connection")
    print(f"[db_config] Host: {DATABASE_HOST}:{DATABASE_PORT}")
    print(f"[db_config] User: {DATABASE_USER}")
    print(f"[db_config] Database: {DATABASE_NAME}")
    
    # pg8000 configuration for local docker-compose
    DATABASE_URL = f"postgresql+pg8000://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    DB_CONFIG = {
        'host': DATABASE_HOST,
        'port': int(DATABASE_PORT),
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'database': DATABASE_NAME
    }
    
    ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DATABASE_HOST};Port={DATABASE_PORT};Database={DATABASE_NAME};Uid={DATABASE_USER};Pwd={DATABASE_PASSWORD};"    
    
    def get_connection():
        """Get database connection via pg8000 TCP (Local)"""
        return get_pg8000_connection(
            host=DATABASE_HOST,
            port=int(DATABASE_PORT),
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD
        )


__all__ = [
    'get_connection',
    'RealDictCursor',
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
