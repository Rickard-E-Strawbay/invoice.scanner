"""
HTTP Service for Document Processing

Provides REST API endpoints to trigger and monitor Celery task processing.

ENDPOINTS:
    GET  /health                   - Service health check
    POST /api/tasks/orchestrate    - Queue a document for processing
    GET  /api/tasks/status/<id>    - Get task execution status

CONFIGURATION:
    Host: 0.0.0.0 (all interfaces)
    Port: 5002
    Debug: False (disabled in production)
"""

import logging
from typing import Dict, Any, Tuple, Optional

from flask import Flask, request, jsonify

from tasks.celery_app import app as celery_app
from tasks import document_tasks  # Ensure tasks are registered

from tasks.document_tasks import orchestrate_document_processing

# ===== LOGGING SETUP =====
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# ===== FLASK APP SETUP =====
app = Flask(__name__)


# ===== HELPER FUNCTIONS =====

def _validate_orchestrate_request(data: Optional[Dict]) -> Tuple[bool, Optional[str]]:
    """
    Validate request JSON for /api/tasks/orchestrate endpoint.

    Args:
        data: Request JSON data.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.
    """
    if not data:
        return False, "No JSON body provided"

    document_id = data.get('document_id')
    company_id = data.get('company_id')

    if not document_id:
        return False, "Missing required field: document_id"
    if not company_id:
        return False, "Missing required field: company_id"

    return True, None


def _create_error_response(
    error: str,
    status_code: int = 400
) -> Tuple[Dict[str, Any], int]:
    """
    Create standardized error response.

    Args:
        error: Error message.
        status_code: HTTP status code.

    Returns:
        Tuple of (response_dict, status_code).
    """
    return (
        {
            'status': 'error',
            'error': error,
            'code': status_code
        },
        status_code
    )


# ===== HEALTH CHECK =====

@app.route('/health', methods=['GET'])
def health() -> Tuple[Dict[str, Any], int]:
    """
    Health check endpoint.

    Returns:
        JSON with service status.
    """
    return (
        {
            'status': 'healthy',
            'service': 'processing-http'
        },
        200
    )


# ===== TASK ORCHESTRATION =====

@app.route('/api/tasks/orchestrate', methods=['POST'])
def trigger_orchestrate() -> Tuple[Dict[str, Any], int]:
    """
    Queue a document for processing.

    Starts the complete 5-stage processing pipeline:
    1. Preprocessing
    2. OCR
    3. LLM prediction
    4. Data extraction
    5. Quality evaluation

    Request JSON:
    {
        "document_id": "uuid-string",
        "company_id": "uuid-string"
    }

    Response (202 Accepted):
    {
        "status": "queued",
        "task_id": "celery-task-uuid",
        "document_id": "document-uuid",
        "message": "Document processing task queued successfully"
    }

    Errors:
        400 Bad Request: Invalid JSON or missing fields
        500 Internal Server Error: Task queueing failed

    Processing Time:
        ~25 seconds total (5 tasks × 5 seconds each, mocked)
        Real processing time depends on document size and server load

    Status Check:
        Use returned task_id with GET /api/tasks/status/<id>
        to monitor processing progress
    """
    try:
        data = request.get_json()

        # Validate request
        is_valid, error_msg = _validate_orchestrate_request(data)
        if not is_valid:
            return _create_error_response(error_msg, 400)

        document_id = data['document_id']
        company_id = data['company_id']

        # Log request
        logger.debug(
            f"[HTTP] Orchestrate request: doc={document_id}, company={company_id}"
        )

        # Queue the task
        try:
            task = orchestrate_document_processing.delay(
                document_id=document_id,
                company_id=company_id
            )

            logger.info(
                f"[HTTP] Task queued: {task.id} for document {document_id}"
            )

            return (
                {
                    'status': 'queued',
                    'task_id': task.id,
                    'document_id': document_id,
                    'message': 'Document processing task queued successfully'
                },
                202
            )

        except Exception as task_error:
            logger.error(
                f"[HTTP] Failed to queue task: {task_error}",
                exc_info=True
            )
            return _create_error_response(
                f"Failed to queue processing task: {str(task_error)}",
                500
            )

    except Exception as request_error:
        logger.error(
            f"[HTTP] Request processing error: {request_error}",
            exc_info=True
        )
        return _create_error_response(
            f"Internal server error: {str(request_error)}",
            500
        )


# ===== TASK STATUS =====

@app.route('/api/tasks/status/<task_id>', methods=['GET'])
def task_status(task_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get status and result of a Celery task.

    Returns the current execution status and result (if completed).

    Status Values:
        PENDING: Task not yet started
        STARTED: Task currently executing
        SUCCESS: Task completed successfully, result available
        FAILURE: Task failed with error
        RETRY: Task failed and is being retried

    Response:
    {
        "task_id": "celery-task-uuid",
        "status": "SUCCESS|FAILURE|PENDING|STARTED|RETRY",
        "result": {...}  # Only present if status is SUCCESS or FAILURE
    }

    Args:
        task_id: Celery task UUID from orchestrate endpoint.

    Returns:
        JSON with task status and optional result.
    """
    try:
        task_result = celery_app.AsyncResult(task_id)

        response = {
            'task_id': task_id,
            'status': task_result.status,
        }

        # Include result if task is complete
        if task_result.status in ['SUCCESS', 'FAILURE']:
            response['result'] = task_result.result

        logger.debug(f"[HTTP] Status check for {task_id}: {task_result.status}")

        return response, 200

    except Exception as e:
        logger.error(
            f"[HTTP] Error getting task status: {e}",
            exc_info=True
        )
        return _create_error_response(
            f"Failed to retrieve task status: {str(e)}",
            500
        )

# ===== MAIN =====

if __name__ == '__main__':
    import os
    
    # Get port from environment variable (Cloud Run sets PORT=8080)
    # For local development, default to 5002
    port = int(os.environ.get('PORT', 5002))
    
    logger.info(f"[HTTP] Starting processing HTTP service on port {port}")
    # Run Flask app on specified port
    # debug=False for production security
    app.run(host='0.0.0.0', port=port, debug=False)

