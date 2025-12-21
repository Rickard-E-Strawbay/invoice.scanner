"""
Celery Tasks Package

Defines all Celery tasks for the document processing pipeline.

MODULES:
    celery_app: Celery application instance and initialization
    document_tasks: Main orchestrator task
    preprocessing_tasks: Stage 1 - Image preprocessing
    ocr_tasks: Stage 2 - Text extraction via OCR
    llm_tasks: Stage 3 - Structured data prediction via LLM
    extraction_tasks: Stage 4 - Data validation and structuring
    evaluation_tasks: Stage 5 - Quality assessment
    callbacks: Completion and error callbacks

TYPICAL USAGE:
    from tasks.celery_app import app
    from tasks.preprocessing_tasks import preprocess_document

    # Queue a task
    result = preprocess_document.delay(document_id, company_id)

    # Check status
    print(result.status)

    # Get result
    output = result.get(timeout=30)
"""

__all__ = [
    'celery_app',
    'document_tasks',
    'preprocessing_tasks',
    'ocr_tasks',
    'llm_tasks',
    'extraction_tasks',
    'evaluation_tasks',
    'callbacks',
]
