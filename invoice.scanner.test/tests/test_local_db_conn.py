#!/usr/bin/env python3
"""
Simple database connection tester
# Tests connectivity to PostgreSQL database using
# configured environment variables
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get DB config from environment
db_host = os.getenv('DATABASE_HOST') or 'db'
db_port = os.getenv('DATABASE_PORT') or '5432'
db_name = os.getenv('DATABASE_NAME') or 'invoice_scanner'
db_user = os.getenv('DATABASE_USER') or 'scanner_local'
db_pass = os.getenv('DATABASE_PASSWORD') or 'scanner_local'

logger.info(f"Testing database connection to \
            {db_user}@{db_host}:{db_port}/{db_name}")

# Try with pg8000
try:
    import pg8000
    logger.info("Attempting connection with pg8000...")
    conn = pg8000.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_pass,
        database=db_name,
    )
    logger.info("✓ Successfully connected with pg8000!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    logger.info(f"✓ Database version: {version}")
    cursor.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    logger.error(f"✗ pg8000 connection failed: {e}")

# Try with psycopg2
try:
    import psycopg2
    logger.info("Attempting connection with psycopg2...")
    conn = psycopg2.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_pass,
        database=db_name,
        connect_timeout=5
    )
    logger.info("✓ Successfully connected with psycopg2!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    logger.info(f"✓ Database version: {version}")
    cursor.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    logger.error(f"✗ psycopg2 connection failed: {e}")

# Try with socket connection test
try:
    import socket
    logger.info(f"Testing socket connection to {db_host}:{db_port}...")
    sock = socket.create_connection((db_host, int(db_port)), timeout=5)
    logger.info("✓ Socket connection successful!")
    sock.close()
except Exception as e:
    logger.error(f"✗ Socket connection failed: {e}")
    logger.info(f"   Make sure the database service is \
                running at {db_host}:{db_port}")

logger.error("✗ Could not connect to database. Check:")
logger.error(f"   - DATABASE_HOST={db_host}")
logger.error(f"   - DATABASE_PORT={db_port}")
logger.error(f"   - DATABASE_NAME={db_name}")
logger.error(f"   - DATABASE_USER={db_user}")
logger.error("   - Is the database service running?")
sys.exit(1)
