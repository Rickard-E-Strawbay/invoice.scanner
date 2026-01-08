"""
Document operations - generic database functions for document management.

These functions are shared across API, Cloud Functions, and other services.
All operations use execute_sql() for unified connection handling.
"""

from ic_shared.logging import ComponentLogger
from ic_shared.database.connection import execute_sql

logger = ComponentLogger("DocumentOperations")


def get_document_status(document_id: str) -> str:
    """
    Retrieve the current status of a document from the database.
    Uses shared execute_sql() for database access.

    Args:
        document_id (str): The unique identifier of the document.

    Returns:
        str: The status of the document if found, otherwise 'NOT_FOUND' or 'ERROR'.
    """
    logger.info(f"Getting status for document {document_id}")

    try:
        results, success = execute_sql(
            """
            SELECT status
            FROM documents
            WHERE id = %s
            """,
            (document_id,)
        )
        
        if not success:
            logger.error("Failed to query document status")
            return "ERROR"
        
        if results:
            status = results[0].get("status") or results[0][0]
            logger.info(f"✓ Document {document_id} status: {status}")
            return status
        else:
            logger.warning(f"⚠️  Document {document_id} not found")
            return "NOT_FOUND"
    except Exception as e:
        logger.error(f"✗ Error querying document status: {e}")
        return "ERROR"


def update_document_status(document_id: str, status: str) -> bool:
    """
    Update document status in database using shared execute_sql().

    NOTE: This is a best-effort operation. If Cloud SQL connection fails,
    we log the error but continue processing. The API layer handles
    initial status updates (e.g., 'preprocessing' when document uploaded).
    This status update is for visibility only.

    Args:
        document_id (str): The unique identifier of the document.
        status (str): The new status to set.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    logger.info(f"[DB] Updating document {document_id} to status '{status}'")

    try:
        results, success = execute_sql(
            """
            UPDATE documents
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (status, document_id)
        )
        
        if success:
            logger.info(f"✓ Document {document_id} status updated -> {status}")
            return True
        else:
            logger.warning(f"[DB] ⚠️  Could not update status (non-critical, continuing)")
            return False
    except Exception as e:
        logger.error(f"❌ Error updating status: {type(e).__name__}: {e}")
        return False
