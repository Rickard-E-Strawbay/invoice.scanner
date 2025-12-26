"""
Google Cloud Functions for Document Processing

This module provides Cloud Functions that handle each stage of document processing
on Google Cloud Platform.

DEPLOYMENT:
    Each function is deployed as a separate Cloud Function triggered by Pub/Sub messages.

ARCHITECTURE:
    Pub/Sub Topic: document-processing
         ↓
    Subscription 1: triggers cf-preprocess
    Subscription 2: triggers cf-ocr (after preprocess completes)
    ... (continue for each stage)

MESSAGE FORMAT:
    {
        'document_id': 'uuid',
        'company_id': 'uuid',
        'stage': 'preprocess|ocr|llm|extraction|evaluation'
    }

DEPLOYMENT STEPS:
    1. gcloud functions deploy cf_preprocess_document \
         --runtime python311 \
         --trigger-topic document-processing \
         --entry-point process_preprocess \
         --project=strawbayscannertest

    2. gcloud functions deploy cf_extract_ocr_text \
         --runtime python311 \
         --trigger-topic document-ocr \
         --entry-point process_ocr \
         --project=strawbayscannertest

    ... (continue for each stage)

NOTES:
    - Each Cloud Function is stateless and idempotent
    - Database is the source of truth for state
    - Pub/Sub ensures at-least-once delivery
    - Update document status in database as each stage completes
    - Publish to next-stage topic when current stage done
"""

import functions_framework
import json
import logging
import os
from google.cloud import pubsub_v1
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Get configuration from environment
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
DATABASE_HOST = os.getenv('DATABASE_HOST', 'localhost')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'invoice_scanner')
DATABASE_USER = os.getenv('DATABASE_USER', 'scanner')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', 'password')
DATABASE_PORT = int(os.getenv('DATABASE_PORT', 5432))


def get_db_connection():
    """Get PostgreSQL connection using Cloud SQL Proxy (Cloud Run)."""
    try:
        import pg8000
        
        conn = pg8000.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            timeout=10
        )
        return conn
    except Exception as e:
        logger.error(f"[DB] Connection failed: {e}")
        return None


def update_document_status(document_id: str, status: str, error: str = None) -> bool:
    """Update document status in database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET status = %s, error = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (status, error, document_id)
            )
            conn.commit()
            logger.info(f"[DB] Document {document_id} status -> {status}")
            return True
    except Exception as e:
        logger.error(f"[DB] Error updating status: {e}")
        return False
    finally:
        conn.close()


def publish_to_topic(topic_name: str, message_data: Dict[str, Any]) -> bool:
    """Publish message to Pub/Sub topic to trigger next stage."""
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, topic_name)
        
        message_json = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, message_json)
        message_id = future.result(timeout=5)
        
        logger.info(f"[Pub/Sub] Published to {topic_name}: {message_id}")
        return True
    except Exception as e:
        logger.error(f"[Pub/Sub] Failed to publish: {e}")
        return False


# ===== CLOUD FUNCTION 1: PREPROCESSING =====

@functions_framework.cloud_event
def cf_preprocess_document(cloud_event):
    """
    Cloud Function: Preprocess document image.
    
    Triggered by: Pub/Sub message on 'document-processing' topic with stage='preprocess'
    
    Process:
        1. Get document from storage
        2. Preprocess image
        3. Save preprocessed version
        4. Update status to 'preprocessed'
        5. Publish to 'document-ocr' topic to trigger next stage
    """
    try:
        # Decode Pub/Sub message
        import base64
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)
        
        document_id = message.get('document_id')
        company_id = message.get('company_id')
        stage = message.get('stage')
        
        if stage != 'preprocess':
            logger.info(f"[CF-PREPROCESS] Skipping message with stage={stage}")
            return
        
        logger.info(f"[CF-PREPROCESS] Processing document {document_id}")
        
        # Update status
        update_document_status(document_id, 'preprocessing')
        
        # TODO: Add actual preprocessing logic here
        # For now: mock delay to simulate processing
        import time
        time.sleep(5)
        
        # Mark complete
        update_document_status(document_id, 'preprocessed')
        
        # Publish to next stage
        publish_to_topic('document-ocr', {
            'document_id': document_id,
            'company_id': company_id,
            'stage': 'ocr'
        })
        
        logger.info(f"[CF-PREPROCESS] Completed for {document_id}")
    
    except Exception as e:
        logger.error(f"[CF-PREPROCESS] Error: {e}", exc_info=True)
        document_id = message.get('document_id') if 'message' in locals() else 'unknown'
        update_document_status(document_id, 'error', str(e))


# ===== CLOUD FUNCTION 2: OCR EXTRACTION =====

@functions_framework.cloud_event
def cf_extract_ocr_text(cloud_event):
    """
    Cloud Function: Extract text from document using OCR.
    
    Triggered by: Pub/Sub message on 'document-ocr' topic with stage='ocr'
    """
    try:
        import base64
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)
        
        document_id = message.get('document_id')
        company_id = message.get('company_id')
        stage = message.get('stage')
        
        if stage != 'ocr':
            return
        
        logger.info(f"[CF-OCR] Processing document {document_id}")
        
        update_document_status(document_id, 'ocr_extracting')
        
        # TODO: Add actual OCR logic here
        import time
        time.sleep(5)
        
        update_document_status(document_id, 'ocr_complete')
        
        # Publish to next stage
        publish_to_topic('document-llm', {
            'document_id': document_id,
            'company_id': company_id,
            'stage': 'llm'
        })
        
        logger.info(f"[CF-OCR] Completed for {document_id}")
    
    except Exception as e:
        logger.error(f"[CF-OCR] Error: {e}")
        document_id = message.get('document_id') if 'message' in locals() else 'unknown'
        update_document_status(document_id, 'error', str(e))


# ===== CLOUD FUNCTION 3: LLM PREDICTION =====

@functions_framework.cloud_event
def cf_predict_invoice_data(cloud_event):
    """
    Cloud Function: Predict invoice data using LLM.
    
    Triggered by: Pub/Sub message on 'document-llm' topic with stage='llm'
    """
    try:
        import base64
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)
        
        document_id = message.get('document_id')
        company_id = message.get('company_id')
        stage = message.get('stage')
        
        if stage != 'llm':
            return
        
        logger.info(f"[CF-LLM] Processing document {document_id}")
        
        update_document_status(document_id, 'llm_predicting')
        
        # TODO: Add actual LLM logic here
        import time
        time.sleep(5)
        
        update_document_status(document_id, 'llm_complete')
        
        # Publish to next stage
        publish_to_topic('document-extraction', {
            'document_id': document_id,
            'company_id': company_id,
            'stage': 'extraction'
        })
        
        logger.info(f"[CF-LLM] Completed for {document_id}")
    
    except Exception as e:
        logger.error(f"[CF-LLM] Error: {e}")
        document_id = message.get('document_id') if 'message' in locals() else 'unknown'
        update_document_status(document_id, 'error', str(e))


# ===== CLOUD FUNCTION 4: DATA EXTRACTION =====

@functions_framework.cloud_event
def cf_extract_structured_data(cloud_event):
    """
    Cloud Function: Extract and structure invoice data.
    
    Triggered by: Pub/Sub message on 'document-extraction' topic with stage='extraction'
    """
    try:
        import base64
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)
        
        document_id = message.get('document_id')
        company_id = message.get('company_id')
        stage = message.get('stage')
        
        if stage != 'extraction':
            return
        
        logger.info(f"[CF-EXTRACTION] Processing document {document_id}")
        
        update_document_status(document_id, 'extraction')
        
        # TODO: Add actual extraction logic here
        import time
        time.sleep(5)
        
        update_document_status(document_id, 'extraction_complete')
        
        # Publish to next stage
        publish_to_topic('document-evaluation', {
            'document_id': document_id,
            'company_id': company_id,
            'stage': 'evaluation'
        })
        
        logger.info(f"[CF-EXTRACTION] Completed for {document_id}")
    
    except Exception as e:
        logger.error(f"[CF-EXTRACTION] Error: {e}")
        document_id = message.get('document_id') if 'message' in locals() else 'unknown'
        update_document_status(document_id, 'error', str(e))


# ===== CLOUD FUNCTION 5: EVALUATION =====

@functions_framework.cloud_event
def cf_run_automated_evaluation(cloud_event):
    """
    Cloud Function: Run automated quality evaluation.
    
    Triggered by: Pub/Sub message on 'document-evaluation' topic with stage='evaluation'
    
    Final stage - marks document as 'completed' when done.
    """
    try:
        import base64
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)
        
        document_id = message.get('document_id')
        company_id = message.get('company_id')
        stage = message.get('stage')
        
        if stage != 'evaluation':
            return
        
        logger.info(f"[CF-EVALUATION] Processing document {document_id}")
        
        update_document_status(document_id, 'evaluation')
        
        # TODO: Add actual evaluation logic here
        import time
        time.sleep(5)
        
        # Final stage - mark as completed
        update_document_status(document_id, 'completed')
        
        logger.info(f"[CF-EVALUATION] Completed for {document_id}")
    
    except Exception as e:
        logger.error(f"[CF-EVALUATION] Error: {e}")
        document_id = message.get('document_id') if 'message' in locals() else 'unknown'
        update_document_status(document_id, 'error', str(e))
