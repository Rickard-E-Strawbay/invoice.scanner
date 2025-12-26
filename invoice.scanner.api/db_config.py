"""
Database configuration for Invoice Scanner API

Connection modes:
- Cloud Run: Cloud SQL Connector + psycopg2 (Private IP, IAM auth)
- Local docker-compose: psycopg2 TCP to db service

K_SERVICE env var indicates Cloud Run environment.
INSTANCE_CONNECTION_NAME is set in Cloud Run for Connector.
"""
import os
from urllib.parse import quote_plus

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

if IS_CLOUD_RUN:
    # ==========================================
    # Cloud Run mode: Cloud SQL Connector
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
    
    print(f"[db_config] Using Cloud SQL Connector")
    print(f"[db_config] Instance: {INSTANCE_CONNECTION_NAME}")
    print(f"[db_config] User: {DATABASE_USER}")
    print(f"[db_config] Database: {DATABASE_NAME}")
    
    # Configuration for Cloud SQL Connector
    # Will be used in main.py with: connector.connect(**DB_CONFIG)
    DB_CONFIG = {
        'instance_connection_name': INSTANCE_CONNECTION_NAME,
        'driver': 'psycopg2',
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'db': DATABASE_NAME
    }
    
    DATABASE_URL = None  # Will use creator function with Connector
    ODBC_CONNECTION_STRING = None

else:
    # ==========================================
    # Local mode: psycopg2 TCP
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
    
    print(f"[db_config] Using psycopg2 TCP connection")
    print(f"[db_config] Host: {DATABASE_HOST}:{DATABASE_PORT}")
    print(f"[db_config] User: {DATABASE_USER}")
    print(f"[db_config] Database: {DATABASE_NAME}")
    
    # Standard psycopg2 configuration for local docker-compose
    DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    DB_CONFIG = {
        'host': DATABASE_HOST,
        'port': DATABASE_PORT,
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'database': DATABASE_NAME
    }
    
    ODBC_CONNECTION_STRING = f"Driver={{PostgreSQL Unicode}};Server={DATABASE_HOST};Port={DATABASE_PORT};Database={DATABASE_NAME};Uid={DATABASE_USER};Pwd={DATABASE_PASSWORD};"
