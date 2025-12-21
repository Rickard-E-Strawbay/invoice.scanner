"""
LLM Prediction Tasks

Handles LLM-based invoice data prediction:
- Structured data extraction from OCR text
- Multi-provider support (OpenAI, Gemini, Anthropic)
- Confidence scoring and validation

These are MOCKED for testing with 5-second delays.
Replace time.sleep() with actual LLM processor calls for production.
"""

import logging
import time
from typing import Dict, Any
from celery.exceptions import SoftTimeLimitExceeded
from tasks.celery_app import app
from config.celery_config import CeleryConfig
from config.db_utils import update_document_status

logger = logging.getLogger(__name__)


# ===== LLM PREDICTION TASK =====

@app.task(
    bind=True,
    name='tasks.llm_tasks.predict_invoice_data',
    max_retries=CeleryConfig.RETRY_STRATEGIES['llm']['max_retries'],
    time_limit=600
)
def predict_invoice_data(
    self,
    ocr_result: Dict[str, Any],
    company_id: str,
    document_id: str
) -> Dict[str, Any]:
    """
    Predict structured invoice data using LLM.

    Third stage of the processing pipeline.
    Uses an LLM to extract and structure invoice data from OCR text,
    including amounts, dates, vendor info, and line items.

    CURRENT STATE: MOCKED for testing (5-second delay with mock output).
    PRODUCTION: Replace time.sleep() with actual LLMProcessor logic that
    calls OpenAI, Gemini, Anthropic, or other LLM providers.

    Args:
        ocr_result: OCR output from previous task.
            {
                'text': '...',
                'overall_confidence': 0.95,
                'lines': [...]
            }
        company_id: UUID of company (for context and validation rules).
        document_id: UUID of document being processed (for status tracking).

    Returns:
        Dictionary with predicted invoice data:
        {
            'confidence': 0.92,
            'invoice_number': 'INV-2025-12345',
            'invoice_date': '2025-12-21',
            'due_date': '2025-12-28',
            'invoice_amount': 1000.00,
            'currency': 'SEK',
            'vendor_name': 'Vendor AB',
            'vendor_email': 'vendor@example.com',
            'line_items': [
                {'description': '...', 'quantity': 1, 'unit_price': 500, 'amount': 500},
                ...
            ],
            'notes': 'Additional context...'
        }

    Raises:
        SoftTimeLimitExceeded: If API call exceeds 10-minute soft limit.
        Will retry up to 3 times with 300-second backoff.

    Note:
        LLM calls can be slow and unreliable. Generous timeouts and
        retry strategy are crucial for production reliability.
    """
    
    try:
        logger.info(f"[LLM] Starting LLM prediction for document: {document_id}, company: {company_id}")

        # MOCK: Sleep for 5 seconds to simulate LLM API call
        time.sleep(5)

        # Mark completion and update database
        logger.info(f"[LLM] Completed with mock LLM predictions for {document_id}")
        update_document_status(document_id, 'predicting')

        # Return mock LLM result
        return {
            'confidence': 0.92,
            'invoice_number': 'INV-2025-12345',
            'invoice_date': '2025-12-21',
            'due_date': '2025-12-28',
            'invoice_amount': 1000.00,
            'currency': 'SEK',
            'vendor_name': 'Mock Vendor AB',
            'vendor_email': 'vendor@mock.se',
            'line_items': [
                {'description': 'Service 1', 'quantity': 1, 'unit_price': 500, 'amount': 500},
                {'description': 'Service 2', 'quantity': 1, 'unit_price': 500, 'amount': 500}
            ],
            'notes': 'Mock invoice data for testing'
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"[LLM] Timeout exceeded for {document_id}, scheduling retry")
        self.retry(countdown=300)
    except Exception as e:
        logger.error(f"[LLM] Error for {document_id}: {e}", exc_info=True)
        update_document_status(document_id, 'llm_error', {'error': str(e)})
        self.retry(
            exc=e,
            countdown=CeleryConfig.RETRY_STRATEGIES['llm']['countdown']
        )
