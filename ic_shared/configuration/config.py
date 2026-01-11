# config.py
# Centralized settings and database configuration

import os
from urllib.parse import quote_plus

from ic_shared.logging import ComponentLogger

# Import local defaults
from .defines import (
    LOCAL_DATABASE_URL,
    LOCAL_DATABASE_HOST,
    LOCAL_DATABASE_PORT,
    LOCAL_DATABASE_USER,
    LOCAL_DATABASE_PASSWORD,
    LOCAL_DATABASE_NAME,
)

logger = ComponentLogger("Configuration")

# ===== DATABASE CONFIGURATION =====

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")  # local, test, prod
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None
IS_LOCAL = ENVIRONMENT == "local"

# Database connection settings
DATABASE_HOST = os.getenv('DATABASE_HOST', LOCAL_DATABASE_HOST)
DATABASE_PORT = os.getenv('DATABASE_PORT', LOCAL_DATABASE_PORT)
DATABASE_USER = os.getenv('DATABASE_USER', LOCAL_DATABASE_USER)
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', LOCAL_DATABASE_PASSWORD)
DATABASE_NAME = os.getenv('DATABASE_NAME', LOCAL_DATABASE_NAME)
INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')  # Cloud Run only

logger.info(f"Environment: {'Cloud Run' if IS_CLOUD_RUN else 'Local'}")
logger.info(f"Driver: pg8000 (Pure Python PostgreSQL)")

if IS_CLOUD_RUN:
    # ==========================================
    # Cloud Run mode: pg8000 via Cloud SQL Connector
    # ==========================================
    if not all([INSTANCE_CONNECTION_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        logger.error("[config] ERROR: Missing Cloud SQL Connector configuration for Cloud Run")
        logger.info(f"INSTANCE_CONNECTION_NAME={INSTANCE_CONNECTION_NAME}")
        logger.info(f"DATABASE_USER={DATABASE_USER}")
        logger.info(f"DATABASE_PASSWORD={'***' if DATABASE_PASSWORD else 'not set'}")
        logger.info(f"DATABASE_NAME={DATABASE_NAME}")
        raise ValueError(
            "Missing required Cloud SQL environment variables for Cloud Run:\n"
            "  - INSTANCE_CONNECTION_NAME\n"
            "  - DATABASE_USER\n"
            "  - DATABASE_PASSWORD\n"
            "  - DATABASE_NAME"
        )
    
    logger.info(f"Using Cloud SQL Connector with pg8000")
    logger.info(f"Instance: {INSTANCE_CONNECTION_NAME}")
    logger.info(f"User: {DATABASE_USER}")
    logger.info(f"Database: {DATABASE_NAME}")
    
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
        logger.error("[config] ERROR: Missing database configuration for local mode")
        logger.info(f"DATABASE_HOST={DATABASE_HOST}")
        logger.info(f"DATABASE_USER={DATABASE_USER}")
        logger.info(f"DATABASE_PASSWORD={'***' if DATABASE_PASSWORD else 'not set'}")
        logger.info(f"DATABASE_NAME={DATABASE_NAME}")
        raise ValueError(
            "Missing required database environment variables for local mode:\n"
            "  - DATABASE_HOST\n"
            "  - DATABASE_USER\n"
            "  - DATABASE_PASSWORD\n"
            "  - DATABASE_NAME"
        )
    
    logger.info(f"Using pg8000 TCP connection")
    logger.info(f"Host: {DATABASE_HOST}:{DATABASE_PORT}")
    logger.info(f"User: {DATABASE_USER}")
    logger.info(f"Database: {DATABASE_NAME}")
    
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

# ===== MODEL CONFIGURATION =====

GEMINI_MODEL_NAME = "gemini-pro"
OPENAI_MODEL_NAME = "gpt-4o"
ANTHROPIC_MODEL_NAME = "claude-3.5-sonnet"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")


# ===== CLOUD FUNCTIONS CONFIGURATION =====

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
CLOUD_SQL_CONN = os.getenv("CLOUD_SQL_CONN")  # Format: project:region:instance
PROCESSING_SLEEP_TIME = float(os.getenv("PROCESSING_SLEEP_TIME", "1.0"))  # seconds
FUNCTION_LOG_LEVEL = os.getenv("FUNCTION_LOG_LEVEL", "DEBUG")
SECRET_MANAGER_CACHE_SIZE = 1  # Cache size for secret manager

# ===== EXPORTS =====

__all__ = [
    # Database configuration
    'DB_CONFIG',
    'DATABASE_URL',
    'DATABASE_HOST',
    'DATABASE_PORT',
    'DATABASE_USER',
    'DATABASE_PASSWORD',
    'DATABASE_NAME',
    'INSTANCE_CONNECTION_NAME',
    'IS_CLOUD_RUN',
    'ODBC_CONNECTION_STRING',
    # Model configuration
    'GEMINI_MODEL_NAME',
    'OPENAI_MODEL_NAME',
    'ANTHROPIC_MODEL_NAME',
    'GOOGLE_SEARCH_API_KEY',
    'GOOGLE_SEARCH_ENGINE_ID',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    # Cloud Functions configuration
    'GCP_PROJECT_ID',
    'CLOUD_SQL_CONN',
    'PROCESSING_SLEEP_TIME',
    'FUNCTION_LOG_LEVEL',
    'SECRET_MANAGER_CACHE_SIZE',
]

