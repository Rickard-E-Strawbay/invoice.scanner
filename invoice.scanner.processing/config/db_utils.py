"""
Database Utilities

Centralized database connection and utility functions.
Used by all tasks for consistent database access.

FUNCTIONS:
    get_db_connection(): PostgreSQL connection
    update_document_status(): Update document processing status
    get_document_status(): Retrieve current document status
"""

import logging
import os
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Establish PostgreSQL database connection.

    Reads connection parameters from environment variables:
    - DB_HOST: Database hostname (default: 'postgres')
    - DB_NAME: Database name (default: 'invoice_scanner')
    - DB_USER: Database user (default: 'scanner')
    - DB_PASSWORD: Database password (default: 'password')
    - DB_PORT: Database port (default: 5432)

    Returns:
        psycopg2 connection object or None if connection fails.

    Raises:
        Logs errors but does not raise - calling code must handle None.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            database=os.getenv('DB_NAME', 'invoice_scanner'),
            user=os.getenv('DB_USER', 'scanner'),
            password=os.getenv('DB_PASSWORD', 'password'),
            port=int(os.getenv('DB_PORT', 5432))
        )
        return conn
    except Exception as e:
        logger.error(f"[DB] Connection failed: {e}", exc_info=True)
        return None


def update_document_status(
    document_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update document processing status in database.

    This is used throughout the processing pipeline to track document state:
    - 'preprocessing': Initial preprocessing stage
    - 'preprocessed': Preprocessing complete
    - 'ocr': OCR extraction stage
    - 'llm_extraction': LLM processing stage
    - 'extraction': Data extraction stage
    - 'evaluation': Quality evaluation stage
    - 'completed': Processing complete
    - 'error': Processing failed
    - 'preprocess_error', 'ocr_error', etc.: Stage-specific errors

    Args:
        document_id: Document UUID.
        status: New status string.
        details: Optional dictionary of additional metadata.

    Returns:
        True if update succeeded, False otherwise.
    """
    conn = get_db_connection()
    if not conn:
        logger.error(f"[DB] Cannot update status for doc {document_id}: no connection")
        return False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (status, document_id)
            )
            conn.commit()
            logger.info(f"[DB] Document {document_id} status -> {status}")
            return True
    except Exception as e:
        logger.error(
            f"[DB] Error updating document {document_id}: {e}",
            exc_info=True
        )
        return False
    finally:
        conn.close()


def get_document_status(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve current document status and metadata.

    Args:
        document_id: Document UUID.

    Returns:
        Dictionary with document data or None if not found/error.
    """
    conn = get_db_connection()
    if not conn:
        logger.error(f"[DB] Cannot retrieve status for doc {document_id}: no connection")
        return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM documents WHERE id = %s",
                (document_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(
            f"[DB] Error retrieving document {document_id}: {e}",
            exc_info=True
        )
        return None
    finally:
        conn.close()
