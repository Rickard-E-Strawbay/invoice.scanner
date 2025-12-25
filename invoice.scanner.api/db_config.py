"""
Database configuration for Invoice Scanner API
"""
import os
from urllib.parse import quote_plus

# Database connection settings - support both naming conventions
# Cloud Run uses DATABASE_* prefix, local dev uses DB_* prefix
DB_HOST = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DATABASE_USER') or os.getenv('DB_USER', 'scanner')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD', 'scanner')
DB_NAME = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME', 'invoice_scanner')

print(f"[db_config] Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# SQLAlchemy connection string
DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# For psycopg2 direct connection - use DB_NAME from environment
DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME
}

# ODBC connection string (for direct ODBC usage)
ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DB_HOST};Port={DB_PORT};Database={DB_NAME};Uid={DB_USER};Pwd={DB_PASSWORD};"
