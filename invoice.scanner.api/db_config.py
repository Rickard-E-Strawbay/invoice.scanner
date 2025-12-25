"""
Database configuration for Invoice Scanner API
Expects DATABASE_* environment variables (set by GCP Cloud Run)
"""
import os
from urllib.parse import quote_plus

# Database connection settings - GCP Cloud Run naming convention
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = os.getenv('DATABASE_PORT', '5432')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
DB_NAME = os.getenv('DATABASE_NAME')

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Missing required database environment variables: DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME")

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
