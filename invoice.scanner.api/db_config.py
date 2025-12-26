"""
Database configuration for Invoice Scanner API
Uses DATABASE_* naming convention for all environments (Cloud Run + Docker Compose)
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

print(f"[db_config] Connecting to {DATABASE_USER}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")

# SQLAlchemy connection string
DATABASE_URL = f"postgresql://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

# For psycopg2 direct connection
DB_CONFIG = {
    'host': DATABASE_HOST,
    'port': DATABASE_PORT,
    'user': DATABASE_USER,
    'password': DATABASE_PASSWORD,
    'database': DATABASE_NAME
}

# ODBC connection string (for direct ODBC usage)
ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DATABASE_HOST};Port={DATABASE_PORT};Database={DATABASE_NAME};Uid={DATABASE_USER};Pwd={DATABASE_PASSWORD};"
