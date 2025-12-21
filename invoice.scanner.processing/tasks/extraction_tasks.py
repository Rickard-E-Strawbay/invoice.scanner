"""
Data Extraction Tasks

Handles validation and structuring of extracted data:
- Schema validation
- Data normalization
- Format standardization
- Derived field calculation

These are MOCKED for testing with 5-second delays.
Replace time.sleep() with actual extraction logic for production.
"""

import logging
import time
from typing import Dict, Any
from celery.exceptions import SoftTimeLimitExceeded
from tasks.celery_app import app
from config.celery_config import CeleryConfig
from config.db_utils import update_document_status

logger = logging.getLogger(__name__)


# ===== DATA EXTRACTION TASK =====

@app.task(
    bind=True,
    name='tasks.extraction_tasks.extract_structured_data',
    max_retries=CeleryConfig.RETRY_STRATEGIES['extraction']['max_retries'],
    time_limit=300
)
def extract_structured_data(
    self,
    llm_prediction: Dict[str, Any],
    company_id: str,
    document_id: str
) -> Dict[str, Any]:
    """
    Extract and validate structured invoice data.

    Fourth stage of the processing pipeline.
    Validates predicted data against invoice schema,
    normalizes values, and structures for database storage.

    CURRENT STATE: MOCKED for testing (5-second delay with mock output).
    PRODUCTION: Replace time.sleep() with actual DataExtractor logic that
    performs schema validation, field normalization, and consistency checks.

    Args:
        llm_prediction: LLM output from previous task with predicted fields.
        company_id: UUID of company (for company-specific validation rules).
        document_id: UUID of document being processed (for status tracking).

    Returns:
        Dictionary with validated and structured data:
        {
            'validation_status': 'valid' | 'warnings' | 'errors',
            'validation_errors': [],  # Critical errors
            'validation_warnings': [],  # Non-critical issues
            'structured': {
                'invoice_id': 'INV-2025-12345',
                'invoice_date': '2025-12-21T00:00:00Z',  # ISO 8601
                'due_date': '2025-12-28T00:00:00Z',
                'total_amount': 1000.00,  # Normalized to float
                'currency': 'SEK',
                'vendor': {
                    'name': 'Vendor AB',
                    'email': 'vendor@example.com'
                },
                'items': [...],  # Structured line items
                'extracted_by': 'data_extractor_v1'
            }
        }

    Raises:
        Exception: On critical validation errors (with retry).

    Note:
        Even if 'validation_status' is 'warnings', structured data is returned.
        Warnings should be reviewed but don't prevent further processing.
    """
    
    try:
        logger.info(f"[EXTRACTION] Starting data extraction for document: {document_id}")

        # MOCK: Sleep for 5 seconds to simulate extraction processing
        time.sleep(5)

        # Mark completion and update database
        logger.info(f"[EXTRACTION] Completed data extraction for {document_id}")
        update_document_status(document_id, 'extraction')

        # Return mock structured data
        return {
            'validation_status': 'valid',
            'validation_errors': [],
            'validation_warnings': [],
            'structured': {
                'invoice_id': llm_prediction.get('invoice_number', 'INV-MOCK'),
                'invoice_date': llm_prediction.get('invoice_date', '2025-12-21'),
                'due_date': llm_prediction.get('due_date', '2025-12-28'),
                'total_amount': llm_prediction.get('invoice_amount', 0),
                'currency': llm_prediction.get('currency', 'SEK'),
                'vendor': {
                    'name': llm_prediction.get('vendor_name', 'Unknown'),
                    'email': llm_prediction.get('vendor_email', 'unknown@example.com')
                },
                'items': llm_prediction.get('line_items', []),
                'extracted_by': 'mock_extraction'
            }
        }

    except Exception as e:
        logger.error(f"[EXTRACTION] Error for {document_id}: {e}", exc_info=True)
        update_document_status(document_id, 'extraction_error', {'error': str(e)})
        self.retry(
            exc=e,
            countdown=CeleryConfig.RETRY_STRATEGIES['extraction']['countdown']
        )
