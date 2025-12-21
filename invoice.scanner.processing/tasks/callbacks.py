"""
Callback Tasks for Task Chain Events

Handles completion and error callbacks in the Celery task chain.
These tasks are called automatically when tasks succeed or fail.

CALLBACKS:
    mark_processing_complete: Executes after successful pipeline completion
    handle_processing_error: Executes if any task in the chain fails
"""

import logging
from typing import Any, Dict
from tasks.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name='tasks.callbacks.mark_processing_complete')
def mark_processing_complete(result: Any, document_id: str) -> Dict[str, Any]:
    """
    Mark document as successfully processed.

    Called automatically after the final task in the chain completes.
    Updates database status and logs completion.

    Args:
        result: Result from the final evaluation task.
        document_id: UUID of the processed document.

    Returns:
        Dictionary confirming completion with document_id and result.
    """
    logger.info(
        f"[CALLBACK] Document {document_id} processing completed successfully"
    )
    return {
        'status': 'completed',
        'document_id': document_id,
        'final_result': result
    }


@app.task(name='tasks.callbacks.handle_processing_error')
def handle_processing_error(
    uuid: str,
    document_id: str,
    einfo: str
) -> Dict[str, Any]:
    """
    Handle errors during document processing.

    Called automatically if any task in the chain fails.
    Logs error details and provides error summary.

    Args:
        uuid: Task UUID (for error tracking).
        document_id: UUID of the document that failed processing.
        einfo: Error information/traceback from the failed task.

    Returns:
        Dictionary with error information for logging/monitoring.
    """
    logger.error(
        f"[CALLBACK] Document {document_id} processing failed: {einfo}"
    )
    return {
        'status': 'error',
        'document_id': document_id,
        'task_uuid': uuid,
        'error': str(einfo)
    }

