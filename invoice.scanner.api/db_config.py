"""
Database configuration for Invoice Scanner API
"""
import os
from urllib.parse import quote_plus

# Database connection settings
DB_HOST = os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'scanner')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'scanner')
DB_NAME = os.getenv('DB_NAME', 'invoice_scanner')

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
