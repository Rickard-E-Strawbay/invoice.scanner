"""
Preprocessing Tasks

Handles document image preprocessing:
- Quality normalization
- Format standardization
- Enhancement for OCR

These are MOCKED for testing with 5-second delays.
Replace time.sleep() with actual processing logic for production.
"""

import logging
import time
import os
from typing import Optional
from celery.exceptions import SoftTimeLimitExceeded
from tasks.celery_app import app
from config.celery_config import CeleryConfig
from config.db_utils import update_document_status

logger = logging.getLogger(__name__)


# ===== PREPROCESSING TASK =====

@app.task(
    bind=True,
    name='tasks.preprocessing_tasks.preprocess_document',
    max_retries=CeleryConfig.RETRY_STRATEGIES['preprocessing']['max_retries'],
    time_limit=300
)
def preprocess_document(self, document_id: str, company_id: str) -> str:
    """
    Preprocess document image for OCR.

    First stage of the processing pipeline.
    Normalizes image format, size, quality, and orientation
    to prepare for OCR extraction.

    CURRENT STATE: MOCKED for testing (5-second delay with mock output).
    PRODUCTION: Replace time.sleep() with actual image processing logic.

    Args:
        document_id: UUID of the document to preprocess.
        company_id: UUID of the company (for context/permissions).

    Returns:
        Path to preprocessed image file.
        Example: '/app/documents/processed/98416a06-3a8_preprocessed.jpg'

    Database Effects:
        Updates document status to 'preprocessed' on success.
        Updates to 'preprocess_error' if an exception occurs.

    Raises:
        SoftTimeLimitExceeded: If processing exceeds 5-minute soft limit.
        Will retry up to 3 times with 60-second backoff.
    """
    
    try:
        logger.info(f"[PREPROCESSING] Starting for document {document_id}")

        # Initialize storage service (LOCAL or GCS based on environment)
        try:
            from storage_service import init_storage_service
            storage_service = init_storage_service()
            logger.info(f"[PREPROCESSING] Storage service initialized: STORAGE_TYPE={os.environ.get('STORAGE_TYPE', 'local')}")
        except Exception as e:
            logger.error(f"[PREPROCESSING] Failed to initialize storage service: {e}")
            storage_service = None

        # MOCK: Sleep for 5 seconds to simulate processing
        time.sleep(5)

        # Mark completion and update database
        logger.info(f"[PREPROCESSING] Completed for document {document_id}")
        update_document_status(document_id, 'preprocessed')

        # Return mock preprocessed image path using storage service abstraction
        # For LOCAL: /app/documents/processed/...
        # For GCS: gs://bucket/processed/...
        if storage_service:
            output_path = f"processed/{document_id}_preprocessed.jpg"
            logger.info(f"[PREPROCESSING] Output path (abstract): {output_path}")
        else:
            # Fallback to local path if storage service not available
            output_path = f"/app/documents/processed/{document_id}_preprocessed.jpg"
            logger.warning(f"[PREPROCESSING] Storage service unavailable, using fallback path: {output_path}")
        
        return output_path

    except SoftTimeLimitExceeded:
        logger.warning(
            f"[PREPROCESSING] Timeout exceeded for {document_id}, scheduling retry"
        )
        self.retry(countdown=60)
    except Exception as e:
        logger.error(
            f"[PREPROCESSING] Error processing {document_id}: {e}",
            exc_info=True
        )
        update_document_status(document_id, 'preprocess_error', {'error': str(e)})
        self.retry(
            exc=e,
            countdown=CeleryConfig.RETRY_STRATEGIES['preprocessing']['countdown']
        )
