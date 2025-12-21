"""
CELERY TASKS - Main Document Processing Pipeline

Denna modul definierar all Celery tasks för dokumentprocessering.
Tasks körs async i separate workers och koordineras via Redis.

PROCESS FLOW:
    upload_document (API)
         ↓
    orchestrate_document_processing (main task)
         ↓
    [CHAIN OF TASKS]
    1. preprocessing_tasks.preprocess_document
    2. ocr_tasks.extract_ocr_text
    3. llm_tasks.predict_invoice_data
    4. extraction_tasks.extract_structured_data
    5. evaluation_tasks.run_automated_evaluation
         ↓
    callback: mark_processing_complete

RETRY STRATEGY:
    - Automatic retries med exponential backoff
    - Max 3 retries per task type
    - Failures loggat och notifieras

ERROR HANDLING:
    - Soft time limits (SoftTimeLimitExceeded)
    - Hard time limits (SIGTERM)
    - Error callbacks för status updates
"""

import logging
from typing import Dict, Any
from celery import chain
from celery.utils.nodenames import gethostname
from celery.exceptions import SoftTimeLimitExceeded
from tasks.celery_app import app
from config.celery_config import CeleryConfig
from config.db_utils import update_document_status

logger = logging.getLogger(__name__)

# ===== MAIN ORCHESTRATOR TASK =====

@app.task(bind=True, name='tasks.document_tasks.orchestrate_document_processing')
def orchestrate_document_processing(self, document_id: str, company_id: str) -> Dict[str, Any]:
    """
    Orchestrate complete document processing pipeline.

    This is the main entry point for document processing. It creates and executes
    a sequential chain of 5 tasks:
    1. Preprocess: Image normalization and quality enhancement
    2. OCR: Text extraction using OCR engine
    3. LLM: Structured data prediction using LLM
    4. Extraction: Data validation and structuring
    5. Evaluation: Quality assessment and recommendations

    Each task's output becomes the next task's input, ensuring data flows
    through the complete pipeline. document_id is injected into all tasks
    so they can update status in the database.

    Args:
        document_id: UUID of the document to process.
        company_id: UUID of the company owning the document.

    Returns:
        Dictionary with status, document_id, and task chain ID.
        {
            'status': 'Processing started',
            'document_id': '<uuid>',
            'task_id': '<celery-task-id>'
        }

    Raises:
        Logs errors and updates document status to 'error' on failure.

    Lifetime:
        - Initial status update: 'preprocessing'
        - Task chain execution: ~25 seconds (5 sec per task)
        - Final status: 'completed' or 'error' (set by final task)
    """
    
    try:
        logger.info(f"[ORCHESTRATOR] Starting document processing: {document_id} (company: {company_id})")
        
        # Update status to indicate processing started
        update_document_status(document_id, 'preprocessing')
        
        # Import tasks from their respective modules
        from tasks.preprocessing_tasks import preprocess_document
        from tasks.ocr_tasks import extract_ocr_text
        from tasks.llm_tasks import predict_invoice_data
        from tasks.extraction_tasks import extract_structured_data
        from tasks.evaluation_tasks import run_automated_evaluation
        
        # Create task chain with document_id injected into all tasks
        # 
        # CHAIN FLOW:
        # preprocess_document(document_id, company_id)
        #   → returns preprocessed_image_path
        # extract_ocr_text(preprocessed_image_path, document_id)
        #   → returns ocr_result
        # predict_invoice_data(ocr_result, company_id, document_id)
        #   → returns llm_prediction
        # extract_structured_data(llm_prediction, company_id, document_id)
        #   → returns structured_data
        # run_automated_evaluation(structured_data, document_id)
        #   → returns final_evaluation
        #
        # Note: In Celery chain, previous task result becomes first arg
        # of next task, so we add document_id as additional arg after that.
        
        workflow = chain(
            # Task 1: Preprocess - takes document_id and company_id
            preprocess_document.s(document_id, company_id),
            
            # Task 2: OCR - receives preprocessed_image_path from task1, also needs document_id
            extract_ocr_text.s(document_id),
            
            # Task 3: LLM - receives ocr_result from task2, needs company_id and document_id
            predict_invoice_data.s(company_id, document_id),
            
            # Task 4: Extraction - receives llm_prediction from task3, needs company_id and document_id
            extract_structured_data.s(company_id, document_id),
            
            # Task 5: Evaluation - receives structured_data from task4, needs document_id
            run_automated_evaluation.s(document_id),
        )
        
        # Apply and execute with proper queue routing
        # The chain will execute tasks in order, routing each to its specific queue
        result = workflow.apply_async(
            queue='preprocessing',  # Start with preprocessing queue
            task_id=None,  # Let Celery generate task ID
            retry=True,
            retry_policy={
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        )
        
        logger.info(f"[ORCHESTRATOR] Task chain started with ID: {result.id}")
        
        return {
            'status': 'Processing started',
            'document_id': document_id,
            'task_id': result.id
        }
        
    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Error: {e}", exc_info=True)
        update_document_status(document_id, 'error', {'error': str(e)})
        raise

