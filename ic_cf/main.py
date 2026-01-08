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
         --entry-point cf_preprocess_document \
         --project=strawbayscannertest

    2. gcloud functions deploy cf_extract_ocr_text \
         --runtime python311 \
         --trigger-topic document-ocr \
         --entry-point cf_extract_ocr_text \
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
from google.cloud import pubsub_v1
from datetime import datetime
from typing import Dict, Any

# Import ComponentLogger instead of standard logging

try:
    from ic_shared.logging import ComponentLogger
    logger = ComponentLogger("CloudFunctions")
except ImportError as e:
    error_msg = f"FATAL: Cannot import shared.configuration.config: {e}"
    raise


# Import Cloud Functions configuration from shared
try:
    from ic_shared.configuration.config import (
        GCP_PROJECT_ID,
        PROCESSING_SLEEP_TIME,
    )
    PROJECT_ID = GCP_PROJECT_ID
    logger.info("✓ Loaded configuration from shared.configuration.config")
except ImportError as e:
    error_msg = f"FATAL: Cannot import shared.configuration.config: {e}"
    logger.error(error_msg)
    raise

# Import the unified database connection and operations from shared
try:
    from ic_shared.database import get_document_status, update_document_status
    HAS_SHARED_DB = True
except ImportError:
    HAS_SHARED_DB = False
    logger.warning("Could not import from shared.database")


# ===== LOCAL PUB/SUB SIMULATOR =====
# When running locally without GCP credentials, simulate Pub/Sub by directly calling functions


def simulate_pubsub_message(topic_name: str, message_data: Dict[str, Any]) -> None:
    """
    Simulate Pub/Sub message delivery by directly calling the appropriate Cloud Function.

    In GCP, Cloud Functions are triggered by Pub/Sub topics.
    Locally, we simulate this by directly invoking the next function.
    """
    logger.info(f"📨 Simulating Pub/Sub message to {topic_name}")

    # Create a mock CloudEvent object
    import base64
    from cloudevents.http import CloudEvent

    # Encode message as Pub/Sub would
    message_json = json.dumps(message_data).encode("utf-8")
    encoded_message = base64.b64encode(message_json).decode("utf-8")

    # Create CloudEvent in Pub/Sub format
    cloud_event = CloudEvent(
        {
            "specversion": "1.0",
            "type": "google.cloud.pubsub.topic.publish",
            "source": f"//pubsub.googleapis.com/projects/local/topics/{topic_name}",
            "id": f"local-{message_data.get('document_id', 'unknown')}",
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
        },
        data={
            "message": {
                "data": encoded_message,
                "attributes": {
                    "document_id": message_data.get("document_id", ""),
                    "company_id": message_data.get("company_id", ""),
                },
            }
        },
    )

    # Map topic names to functions and call them
    topic_to_function = {
        "document-ocr": "cf_extract_ocr_text",
        "document-llm": "cf_predict_invoice_data",
        "document-extraction": "cf_extract_structured_data",
        "document-evaluation": "cf_run_automated_evaluation",
    }

    if topic_name in topic_to_function:
        func_name = topic_to_function[topic_name]
        logger.info(f"🔗 Calling {func_name} directly (local mode)")

        # Get the function from globals and call it
        try:
            func = globals().get(func_name)
            if func:
                func(cloud_event)
                logger.info(f"✅ Successfully called {func_name}")
            else:
                logger.error(f"❌ Function {func_name} not found")
        except Exception as e:
            logger.error(f"❌ Error calling {func_name}: {e}")
            import traceback

            traceback.print_exc()
    else:
        logger.warning(f"⚠️  No function mapping for topic {topic_name}")

# ===== PUB/SUB ORCHESTRATION =====


def publish_to_topic(topic_name: str, message_data: Dict[str, Any]) -> bool:
    """Publish message to Pub/Sub topic to trigger next stage."""
    try:
        logger.info(f"� Publishing message to {topic_name}: {message_data}")
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, topic_name)
        message_json = json.dumps(message_data).encode("utf-8")

        future = publisher.publish(topic_path, message_json)
        message_id = future.result(timeout=5)
        logger.info(f"✓ Published with message_id: {message_id}")
        return True
    except Exception as e:
        if "DefaultCredentialsError" in type(e).__name__:
            logger.info("[Pub/Sub] 📨 [LOCAL] Simulating Pub/Sub message")
            simulate_pubsub_message(topic_name, message_data)
            return True
        else:
            logger.error(f"❌ Failed: {type(e).__name__}: {e}")
            return False


# ===== CLOUD FUNCTION 1: PREPROCESSING =====


@functions_framework.cloud_event
def cf_preprocess_document(cloud_event):
    """
    Cloud Function: Preprocess document image.
    Triggered by: Pub/Sub message on 'document-processing' topic with stage='preprocess'
    """
    try:
        from workers.cf_preprocess import cf_preprocess
        processor = cf_preprocess(cloud_event)
        processor.execute()
    except Exception as e:
        logger.error(f"❌ Error in cf_preprocess_document: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


# ===== CLOUD FUNCTION 2: OCR EXTRACTION =====


@functions_framework.cloud_event
def cf_extract_ocr_text(cloud_event):
    """
    Cloud Function: Extract text from document using OCR.
    Triggered by: Pub/Sub message on 'document-ocr' topic with stage='ocr'
    """
    try:
        from workers.cf_extract_ocr_text import cf_extract_ocr_text
        processor = cf_extract_ocr_text(cloud_event)
        processor.execute()
    except Exception as e:
        logger.error(f"❌ Error in cf_extract_ocr_text: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


# ===== CLOUD FUNCTION 3: LLM PREDICTION =====


@functions_framework.cloud_event
def cf_predict_invoice_data(cloud_event):
    """
    Cloud Function: Predict invoice data using LLM.
    Triggered by: Pub/Sub message on 'document-llm' topic with stage='llm'
    """
    try:
        from workers.cf_predict_invoice_data import cf_predict_invoice_data
        processor = cf_predict_invoice_data(cloud_event)
        processor.execute()
    except Exception as e:
        logger.error(f"❌ Error in cf_predict_invoice_data: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


# ===== CLOUD FUNCTION 4: DATA EXTRACTION =====


@functions_framework.cloud_event
def cf_extract_structured_data(cloud_event):
    """
    Cloud Function: Extract and structure invoice data.
    Triggered by: Pub/Sub message on 'document-extraction' topic with stage='extraction'
    """
    try:
        from workers.cf_extract_structured_data import cf_extract_structured_data
        processor = cf_extract_structured_data(cloud_event)
        processor.execute()
    except Exception as e:
        logger.error(f"❌ Error in cf_extract_structured_data: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


# ===== CLOUD FUNCTION 5: EVALUATION =====


@functions_framework.cloud_event
def cf_run_automated_evaluation(cloud_event):
    """
    Cloud Function: Run automated quality evaluation.
    Triggered by: Pub/Sub message on 'document-evaluation' topic with stage='evaluation'
    Final stage - marks document as 'completed' when done.
    """
    try:
        from workers.cf_run_automated_evaluation import cf_run_automated_evaluation
        processor = cf_run_automated_evaluation(cloud_event)
        processor.execute()
    except Exception as e:
        logger.error(f"❌ Error in cf_run_automated_evaluation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


# ===== CLEANUP ON EXIT =====
# Managed by shared.database.connection.close_connector()
# No need to manually manage cleanup here
