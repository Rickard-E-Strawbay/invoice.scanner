"""
Invoice Scanner - Processing Worker Service Package

Pub/Sub-triggered document processing service with parallel workers.
Replaces Cloud Functions with stateful, timeout-unlimited service.

Architecture:
    - Listens to 5 Pub/Sub topics (document-processing, ocr, llm, extraction, evaluation)
    - Coordinates 5-stage pipeline with parallel ThreadPool workers
    - Maintains database state for each document
    - Provides HTTP endpoints for status and manual triggering

Environment:
    - Local: docker-compose with mock Pub/Sub
    - Cloud: Google Cloud Run with real Pub/Sub subscriptions
"""

__version__ = "1.0.0"
__author__ = "Invoice Scanner Team"

# Main Flask app is in main.py
# Database config in db_config.py
# Worker classes defined in main.py
