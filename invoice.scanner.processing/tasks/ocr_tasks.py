"""
OCR Extraction Tasks

Handles optical character recognition (OCR):
- Text extraction from preprocessed images
- Confidence scoring
- Line-level detail extraction

These are MOCKED for testing with 5-second delays.
Replace time.sleep() with actual OCR processor calls for production.
"""

import logging
import time
from typing import Dict, Any
from celery.exceptions import SoftTimeLimitExceeded
from tasks.celery_app import app
from config.celery_config import CeleryConfig
from config.db_utils import update_document_status

logger = logging.getLogger(__name__)


# ===== OCR TASK =====

@app.task(
    bind=True,
    name='tasks.ocr_tasks.extract_ocr_text',
    max_retries=CeleryConfig.RETRY_STRATEGIES['ocr']['max_retries'],
    time_limit=600
)
def extract_ocr_text(self, preprocessed_image_path: str, document_id: str) -> Dict[str, Any]:
    """
    Extract text from preprocessed image using OCR.

    Second stage of the processing pipeline.
    Performs optical character recognition on the preprocessed image
    and returns structured text with confidence scores.

    CURRENT STATE: MOCKED for testing (5-second delay with mock output).
    PRODUCTION: Replace time.sleep() with actual OCR processor logic
    (Tesseract, PaddleOCR, or similar).

    Args:
        preprocessed_image_path: Path to preprocessed image from previous task.
            Example: '/app/documents/processed/98416a06-3a8_preprocessed.jpg'
        document_id: UUID of document being processed (for status tracking).

    Returns:
        Dictionary with OCR results:
        {
            'text': 'Full extracted text...',
            'overall_confidence': 0.95,  # Confidence 0-1
            'lines': [
                {'text': 'Line 1', 'confidence': 0.98},
                {'text': 'Line 2', 'confidence': 0.96},
                ...
            ]
        }

    Raises:
        SoftTimeLimitExceeded: If processing exceeds 10-minute soft limit.
        Will retry up to 3 times with 120-second backoff.

    Note:
        The output of this task is passed directly to the LLM task.
        Ensure the returned dictionary matches the expected structure.
    """
    
    try:
        logger.info(f"[OCR] Starting text extraction for document: {document_id}")

        # MOCK: Sleep for 5 seconds to simulate OCR processing
        time.sleep(5)

        # Mark completion and update database
        logger.info(f"[OCR] Completed with mock OCR text for {document_id}")
        update_document_status(document_id, 'ocr_extracting')

        # Return mock OCR result
        return {
            'text': 'MOCK OCR TEXT: Invoice #12345 Date: 2025-12-21 Amount: 1000 SEK',
            'overall_confidence': 0.95,
            'lines': [
                {'text': 'MOCK OCR TEXT', 'confidence': 0.98},
                {'text': 'Invoice #12345', 'confidence': 0.96},
                {'text': 'Amount: 1000 SEK', 'confidence': 0.92}
            ]
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"[OCR] Timeout exceeded for {document_id}, scheduling retry")
        self.retry(countdown=120)
    except Exception as e:
        logger.error(f"[OCR] Error for {document_id}: {e}", exc_info=True)
        update_document_status(document_id, 'ocr_error', {'error': str(e)})
        self.retry(
            exc=e,
            countdown=CeleryConfig.RETRY_STRATEGIES['ocr']['countdown']
        )
