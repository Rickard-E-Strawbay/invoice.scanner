"""
Database configuration for Invoice Scanner API
Supports both GCP Cloud Run (DATABASE_*) and local dev (DB_*) naming conventions
"""
import os
from urllib.parse import quote_plus

# Database connection settings
# Priority: DATABASE_* (GCP Cloud Run) > DB_* (local docker-compose)
DB_HOST = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST')
DB_PORT = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DATABASE_USER') or os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME')

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    print("[db_config] ERROR: Missing database configuration")
    print(f"[db_config] DATABASE_HOST={os.getenv('DATABASE_HOST')}, DB_HOST={os.getenv('DB_HOST')}")
    print(f"[db_config] DATABASE_USER={os.getenv('DATABASE_USER')}, DB_USER={os.getenv('DB_USER')}")
    print(f"[db_config] DATABASE_PASSWORD={'***' if os.getenv('DATABASE_PASSWORD') else 'not set'}")
    print(f"[db_config] DATABASE_NAME={os.getenv('DATABASE_NAME')}, DB_NAME={os.getenv('DB_NAME')}")
    raise ValueError(
        "Missing required database environment variables.\n"
        "Set either:\n"
        "  - GCP style: DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME\n"
        "  - Local style: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    )

print(f"[db_config] Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# SQLAlchemy connection string
DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# For psycopg2 direct connection
DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME
}

# ODBC connection string (for direct ODBC usage)
ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DB_HOST};Port={DB_PORT};Database={DB_NAME};Uid={DB_USER};Pwd={DB_PASSWORD};"
