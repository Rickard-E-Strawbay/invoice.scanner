"""
Celery Application Instance and Configuration

This module initializes the Celery application instance,
applies configuration, and auto-discovers task modules.

ARCHITECTURE:
    Redis (Message Broker + Result Backend)
         ↓
    Celery App (manages tasks and workers)
         ↓
    Workers (preprocessing, ocr, llm, extraction, evaluation)

TASK REGISTRATION:
    All tasks are auto-discovered from specified modules.
    Task names follow pattern: tasks.<module>.<function>
    Example: tasks.preprocessing_tasks.preprocess_document

INITIALIZATION:
    1. Create Celery app instance
    2. Apply configuration from CeleryConfig
    3. Initialize LLM providers (lazy, on first use)
    4. Auto-discover all task modules

USAGE:
    from tasks.celery_app import app

    # Queue a task asynchronously
    result = some_task.delay(arg1, arg2)

    # Get result with timeout
    result.get(timeout=30)

    # Check task status
    task_result = app.AsyncResult(task_id)
    print(task_result.status)  # PENDING, STARTED, SUCCESS, FAILURE
"""

import os
from celery import Celery
from config.celery_config import CeleryConfig
from config.llm_providers import LLMProviderFactory

# ===== INITIALIZE CELERY APPLICATION =====
# Create Celery app instance with a descriptive name
app = Celery('invoice_scanner_processing')

# ===== APPLY CONFIGURATION =====
# Load all Celery configuration from CeleryConfig class
app.config_from_object(CeleryConfig)

# ===== INITIALIZE LLM PROVIDERS =====
# Initialize all configured LLM providers at startup
# This validates API keys and sets up clients
try:
    LLMProviderFactory.initialize()
except Exception as e:
    print(f"Warning: LLM provider initialization failed: {e}")

# ===== AUTO-DISCOVER TASK MODULES =====
# Celery automatically scans these modules and registers all @app.task functions
app.autodiscover_tasks([
    'tasks.document_tasks',       # Main orchestrator
    'tasks.preprocessing_tasks',  # Stage 1: Image preprocessing
    'tasks.ocr_tasks',           # Stage 2: Text extraction
    'tasks.llm_tasks',           # Stage 3: Data prediction
    'tasks.extraction_tasks',    # Stage 4: Data structuring
    'tasks.evaluation_tasks',    # Stage 5: Quality assessment
    'tasks.callbacks',           # Callback handlers
])

# ===== EXPLICIT TASK IMPORT =====
# Force import to ensure tasks are registered, even if autodiscover misses them
try:
    from tasks import document_tasks as _doc_tasks_module
except ImportError as e:
    print(f"Warning: Could not import document_tasks: {e}")


if __name__ == '__main__':
    app.start()

