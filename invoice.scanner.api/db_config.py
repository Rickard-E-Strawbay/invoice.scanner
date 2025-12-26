"""
Database configuration for Invoice Scanner API
Uses DATABASE_* naming convention for all environments (Cloud Run + Docker Compose)

Connection modes:
- Unix socket (Cloud Run): DATABASE_HOST=/cloudsql/project:region:instance (no port in connection string)
- TCP localhost (docker-compose): DATABASE_HOST=db, DATABASE_PORT=5432
"""
import os
from urllib.parse import quote_plus

# Database connection settings
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')

if not all([DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
    print("[db_config] ERROR: Missing database configuration")
    print(f"[db_config] DATABASE_HOST={DATABASE_HOST}")
    print(f"[db_config] DATABASE_USER={DATABASE_USER}")
    print(f"[db_config] DATABASE_PASSWORD={'***' if DATABASE_PASSWORD else 'not set'}")
    print(f"[db_config] DATABASE_NAME={DATABASE_NAME}")
    raise ValueError(
        "Missing required database environment variables:\n"
        "  - DATABASE_HOST\n"
        "  - DATABASE_USER\n"
        "  - DATABASE_PASSWORD\n"
        "  - DATABASE_NAME"
    )

# Determine connection mode: Unix socket vs TCP
IS_UNIX_SOCKET = DATABASE_HOST.startswith('/')

if IS_UNIX_SOCKET:
    # Cloud Run with Cloud SQL Proxy (Unix socket)
    # Extract socket directory (everything before the last slash doesn't contain filename)
    # Socket path format: /cloudsql/project:region:instance
    socket_dir = DATABASE_HOST  # The path itself IS the socket directory
    
    print(f"[db_config] Connecting via Unix socket: {DATABASE_USER}@{socket_dir}/{DATABASE_NAME}")
    
    # For psycopg2/SQLAlchemy: use unix_sock_dir parameter
    # Format: postgresql://user:password@/database?unix_sock_dir=/path/to/socket/dir
    DATABASE_URL = f"postgresql://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}@/{DATABASE_NAME}?unix_sock_dir={socket_dir}"
    
    # For psycopg2 direct connection with Unix socket
    DB_CONFIG = {
        'host': socket_dir,
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'database': DATABASE_NAME
    }
else:
    # Local docker-compose with TCP (standard TCP connection)
    print(f"[db_config] Connecting via TCP: {DATABASE_USER}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")
    DATABASE_URL = f"postgresql://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    DB_CONFIG = {
        'host': DATABASE_HOST,
        'port': DATABASE_PORT,
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'database': DATABASE_NAME
    }

# ODBC connection string (for direct ODBC usage - typically TCP only)
if not IS_UNIX_SOCKET:
    ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DATABASE_HOST};Port={DATABASE_PORT};Database={DATABASE_NAME};Uid={DATABASE_USER};Pwd={DATABASE_PASSWORD};"
else:
    ODBC_CONNECTION_STRING = None  # ODBC not typically used with Unix sockets
