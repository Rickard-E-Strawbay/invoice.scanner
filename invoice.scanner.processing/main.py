"""
Invoice Scanner - Processing Worker Service

Pub/Sub-triggered document processing service with parallel worker pool.
Replaces Cloud Functions with stateful, timeout-unlimited worker service.

ARCHITECTURE:
    Pub/Sub Topics:
        ├─ document-processing → trigger cf_preprocess_document
        ├─ document-ocr → trigger cf_extract_ocr_text
        ├─ document-llm → trigger cf_predict_invoice_data
        ├─ document-extraction → trigger cf_extract_structured_data
        └─ document-evaluation → trigger cf_run_automated_evaluation

    Processing Service (Cloud Run):
        ├─ Pub/Sub Listener (async)
        │   └─ Subscribes to all 5 topics
        │
        ├─ Worker Coordinator
        │   ├─ PreprocessWorker (ThreadPool=2)
        │   ├─ OCRWorker (ThreadPool=5, parallel page processing)
        │   ├─ LLMWorker (ThreadPool=10, parallel item extraction)
        │   ├─ ExtractionWorker (ThreadPool=5)
        │   └─ EvaluationWorker (ThreadPool=20, confidence scoring)
        │
        ├─ Database Layer
        │   ├─ Document status updates
        │   ├─ Extracted data persistence
        │   └─ State management
        │
        └─ HTTP Endpoints
            ├─ POST /api/documents/{doc_id}/process
            ├─ GET /api/documents/{doc_id}/status
            └─ GET /health (Kubernetes liveness probe)

DEPLOYMENT:
    Local: docker-compose (with api, frontend, db)
    Cloud: Cloud Run (triggered by Pub/Sub subscriptions)

ENVIRONMENT VARIABLES:
    GCP_PROJECT_ID: GCP project (strawbayscannertest or strawbayscannerprod)
    DATABASE_*: DB connection (same as API)
    PROCESSING_BACKEND: 'worker_service' (used by API)
    WORKER_MAX_PROCESSES: Number of concurrent document processes (default: 5)
    WORKER_THREAD_POOL_SIZE: ThreadPool workers per stage (varies by stage)

"""

import os
import sys
import json
import logging
import base64
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time

from flask import Flask, jsonify, request
from google.cloud import pubsub_v1
import threading

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database config (unified from shared package) - SAME AS API
from shared.database.config import DB_CONFIG, get_connection, RealDictCursor
from shared.logging import ComponentLogger

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=os.getenv("PROCESSING_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = ComponentLogger("ProcessingService")

# ============================================================
# GLOBAL CONFIG
# ============================================================

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "strawbayscannertest")
PROCESSING_BACKEND = os.getenv("PROCESSING_BACKEND", "worker_service")
MAX_DOCUMENT_PROCESSES = int(os.getenv("WORKER_MAX_PROCESSES", "5"))

# Thread pool sizes per worker type
WORKER_THREAD_POOLS = {
    "preprocess": 2,      # Sequential PDF conversion
    "ocr": 2,             # Parallel page OCR
    "llm": 2,            # Parallel item extraction
    "extraction": 2,      # Parallel field extraction
    "evaluation": 2      # Parallel confidence scoring
}

PROCESSING_SLEEP_TIME = float(os.getenv("PROCESSING_SLEEP_TIME", "0.0"))

logger.info(f"Processing Service initialized [v2]")
logger.info(f"GCP_PROJECT_ID: {GCP_PROJECT_ID}")
logger.info(f"MAX_DOCUMENT_PROCESSES: {MAX_DOCUMENT_PROCESSES}")
logger.info(f"Worker thread pool config: {WORKER_THREAD_POOLS}")

# ============================================================
# FLASK APP SETUP
# ============================================================

app = Flask(__name__)

# ============================================================
# DATABASE LAYER
# ============================================================

def get_db_connection():
    """Get a database connection.
    
    Routes to appropriate connection method:
    - Cloud Run: Cloud SQL Connector (from get_connection in db_config)
    - Local: pg8000 TCP (from get_connection in db_config)
    """
    try:
        logger.info("[DB] Attempting to connect...")
        conn = get_connection(...)
        logger.info("[DB] Connection object returned")
  
        return conn
    except Exception as e:
        logger.database_error("connection", str(e))
        return None


def update_document_status(document_id: str, status: str, error_message: Optional[str] = None) -> bool:
    """Update document processing status in database.
    
    Uses explicit cursor handling (no context manager) to avoid pg8000 transaction deadlocks.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.database_error("connection", "Cannot connect to database")
            return False

        # Explicit cursor creation (NOT using context manager)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute query
        if error_message:
            cursor.execute(
                "UPDATE documents SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s",
                (status, error_message, document_id)
            )
        else:
            cursor.execute(
                "UPDATE documents SET status = %s, updated_at = NOW() WHERE id = %s",
                (status, document_id)
            )
        
        # EXPLICIT close BEFORE commit (critical for pg8000)
        cursor.close()
        cursor = None
        
        # Now commit
        conn.commit()
        logger.success(f"Document {document_id} status: {status}")
        return True
        
    except Exception as e:
        # Attempt rollback on error
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.debug(f"Rollback failed (may have been auto-rolled back): {rollback_error}")
        logger.database_error("update_status", str(e))
        return False
    finally:
        # Cleanup: close cursor if still open
        if cursor:
            try:
                cursor.close()
            except Exception as cursor_error:
                logger.debug(f"Cursor close error in finally: {cursor_error}")
        # Cleanup: close connection
        if conn:
            try:
                conn.close()
            except Exception as conn_error:
                logger.debug(f"Connection close error in finally: {conn_error}")


def get_document_details(document_id: str) -> Dict[str, Any]:
    """Get document details from database.
    
    Uses explicit cursor handling (no context manager) to avoid pg8000 transaction deadlocks.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {}

        # Explicit cursor creation with RealDictCursor factory
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute query
        cursor.execute(
            "SELECT * FROM documents WHERE id = %s",
            (document_id,)
        )
        result = cursor.fetchone()
        
        # EXPLICIT close (critical for pg8000)
        cursor.close()
        cursor = None
        conn.close()
        conn = None
        
        return dict(result) if result else {}
        
    except Exception as e:
        logger.database_error("fetch_document", str(e))
        return {}
    finally:
        # Cleanup: close cursor if still open
        if cursor:
            try:
                cursor.close()
            except Exception as cursor_error:
                logger.debug(f"Cursor close error in finally: {cursor_error}")
        # Cleanup: close connection if still open
        if conn:
            try:
                conn.close()
            except Exception as conn_error:
                logger.debug(f"Connection close error in finally: {conn_error}")


def save_extracted_text(document_id: str, extracted_text: str, ocr_data: Dict[str, Any] = None) -> bool:
    """Save extracted text and OCR data to database.
    
    Uses explicit cursor handling (no context manager) to avoid pg8000 transaction deadlocks.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False

        # Explicit cursor creation (NOT using context manager)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute query
        cursor.execute(
            """
            UPDATE documents 
            SET ocr_raw_text = %s, ocr_data = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (
                extracted_text,
                json.dumps(ocr_data or {}),
                document_id
            )
        )
        
        # EXPLICIT close BEFORE commit (critical for pg8000)
        cursor.close()
        cursor = None
        
        # Now commit
        conn.commit()
        logger.success(f"Saved OCR data for {document_id}")
        return True
        
    except Exception as e:
        # Attempt rollback on error
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.debug(f"Rollback failed (may have been auto-rolled back): {rollback_error}")
        logger.database_error("save_ocr_data", str(e))
        return False
    finally:
        # Cleanup: close cursor if still open
        if cursor:
            try:
                cursor.close()
            except Exception as cursor_error:
                logger.debug(f"Cursor close error in finally: {cursor_error}")
        # Cleanup: close connection
        if conn:
            try:
                conn.close()
            except Exception as conn_error:
                logger.debug(f"Connection close error in finally: {conn_error}")


def publish_to_topic(topic_name: str, message_data: Dict[str, Any]) -> bool:
    """
    Publish message to Pub/Sub topic to trigger next stage.
    
    In production (Cloud Run with credentials): Uses Pub/Sub
    In local dev (no credentials): Falls back to direct worker invocation
    """
    try:
        if not GCP_PROJECT_ID:
            logger.warning(f"GCP_PROJECT_ID not set, falling back to direct invocation")
            # Fallback: Invoke worker directly
            worker_thread = threading.Thread(
                target=process_document,
                args=(message_data,),
                daemon=True
            )
            worker_thread.start()
            return True

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(GCP_PROJECT_ID, topic_name)
        
        message_json = json.dumps(message_data)
        message_bytes = message_json.encode("utf-8")
        
        future = publisher.publish(topic_path, data=message_bytes)
        message_id = future.result()
        
        logger.success(f"Published to {topic_name}: {message_id}")
        return True
    except Exception as e:
        error_msg = str(e)
        # Check if this is expected credentials error (expected in local dev)
        if "credentials" in error_msg.lower() or "not found" in error_msg.lower():
            logger.info(f"Pub/Sub publishing not available (credentials): falling back to direct worker invocation")
        else:
            logger.error(f"Error publishing: {e}")
        logger.info(f"Falling back to direct worker invocation")
        
        # Fallback: Invoke worker directly in background thread
        try:
            worker_thread = threading.Thread(
                target=process_document,
                args=(message_data,),
                daemon=True
            )
            worker_thread.start()
            return True
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            return False

# ============================================================
# WORKER IMPLEMENTATIONS
# ============================================================

class BaseWorker:
    """Base class for all processing workers."""
    
    def __init__(self, document_id: str, company_id: str):
        self.document_id = document_id
        self.company_id = company_id
        self.stage_name = self.__class__.__name__.replace("Worker", "").lower()
    
    def execute(self):
        """Override in subclass."""
        raise NotImplementedError
    
    def _handle_error(self, error_msg: str):
        """Standard error handling."""
        logger.task_failed(self.stage_name, error_msg)
        update_document_status(self.document_id, f"{self.stage_name}_error", error_msg)


class PreprocessWorker(BaseWorker):
    """
    Stage 1: Preprocess document (PDF→PNG conversion)
    """
    
    def __init__(self, document_id: str, company_id: str, max_workers: int = 2):
        super().__init__(document_id, company_id)
        self.max_workers = max_workers
    
    def execute(self):
        logger.processing_stage("preprocess", self.document_id)
        logger.info(f"[PREPROCESS] Calling update_document_status: preprocessing")
        
        status_updated = update_document_status(self.document_id, "preprocessing")
        logger.info(f"[PREPROCESS] Status update returned: {status_updated}")
        
        # CRITICAL: If status update fails, document status is not saved in DB
        # We must abort processing to avoid orphaned documents in wrong state
        if not status_updated:
            logger.error(f"[PREPROCESS] ❌ FAILED to set preprocessing status - aborting")
            self._handle_error("Failed to update document status to 'preprocessing' in database")
            return
        
        try:
            # TODO: Implement actual preprocessing
            # - Get raw file from storage
            # - Convert PDF to PNG (600 DPI)
            # - Save to processed storage
            logger.info(f"[PREPROCESS] Starting preprocessing sleep for {self.document_id}")
            time.sleep(PROCESSING_SLEEP_TIME)
            logger.info(f"[PREPROCESS] Finished sleep, updating to preprocessed")
            
            status_updated = update_document_status(self.document_id, "preprocessed")
            logger.info(f"[PREPROCESS] Updated to preprocessed: {status_updated}")
            
            if not status_updated:
                logger.error(f"[PREPROCESS] ❌ Failed to update status to preprocessed")
                self._handle_error("Failed to update document status to 'preprocessed' in database")
                return
            
            # Trigger next stage
            logger.info(f"[PREPROCESS] Publishing to document-ocr topic")
            publish_result = publish_to_topic(
                "document-ocr",
                {"document_id": self.document_id, "company_id": self.company_id, "stage": "ocr"}
            )
            logger.info(f"[PREPROCESS] Publish to ocr topic returned: {publish_result}")
            
            logger.task_complete("preprocessing", f"doc={self.document_id}")
        except Exception as e:
            logger.error(f"[PREPROCESS] Exception in execute: {e}", exc_info=True)
            self._handle_error(str(e))


class OCRWorker(BaseWorker):
    """
    Stage 2: Extract text using OCR
    Supports parallel page processing for multi-page PDFs
    """
    
    def __init__(self, document_id: str, company_id: str, max_workers: int = 5):
        super().__init__(document_id, company_id)
        self.max_workers = max_workers
    
    def execute(self):
        logger.info(f"[OCR] Processing document {self.document_id}")
        status_updated = update_document_status(self.document_id, "ocr_extracting")
        
        if not status_updated:
            logger.error(f"[OCR] ❌ Failed to set ocr_extracting status - aborting")
            self._handle_error("Failed to update document status to 'ocr_extracting'")
            return
        
        try:
            # TODO: Implement actual OCR
            # - Get preprocessed PNG
            # - If multi-page:
            #   - Split into individual pages
            #   - Use ThreadPool to OCR pages in parallel
            # - Combine results
            # - Save to database
            time.sleep(PROCESSING_SLEEP_TIME)
            
            extracted_text = "Mock OCR text"
            # save_extracted_text(self.document_id, extracted_text)
            
            status_updated = update_document_status(self.document_id, "ocr_complete")
            if not status_updated:
                logger.error(f"[OCR] ❌ Failed to set ocr_complete status")
                self._handle_error("Failed to update document status to 'ocr_complete'")
                return
            
            # Trigger next stage
            publish_to_topic(
                "document-llm",
                {"document_id": self.document_id, "company_id": self.company_id, "stage": "llm"}
            )
            
            logger.info(f"[OCR] ✓ Completed for {self.document_id}")
        except Exception as e:
            self._handle_error(str(e))


class LLMWorker(BaseWorker):
    """
    Stage 3: Extract structured data using LLM
    Supports parallel item extraction (ThreadPool for API calls)
    """
    
    def __init__(self, document_id: str, company_id: str, max_workers: int = 10):
        super().__init__(document_id, company_id)
        self.max_workers = max_workers
    
    def execute(self):
        logger.info(f"[LLM] Processing document {self.document_id}")
        status_updated = update_document_status(self.document_id, "llm_predicting")
        
        if not status_updated:
            logger.error(f"[LLM] ❌ Failed to set llm_predicting status - aborting")
            self._handle_error("Failed to update document status to 'llm_predicting'")
            return
        
        try:
            # TODO: Implement actual LLM processing
            # - Get OCR text from database
            # - Parse into line items
            # - Use ThreadPool to call LLM in parallel for each item
            # - Combine results
            time.sleep(PROCESSING_SLEEP_TIME)
            
            status_updated = update_document_status(self.document_id, "llm_complete")
            if not status_updated:
                logger.error(f"[LLM] ❌ Failed to set llm_complete status")
                self._handle_error("Failed to update document status to 'llm_complete'")
                return
            
            # Trigger next stage
            publish_to_topic(
                "document-extraction",
                {"document_id": self.document_id, "company_id": self.company_id, "stage": "extraction"}
            )
            
            logger.info(f"[LLM] ✓ Completed for {self.document_id}")
        except Exception as e:
            self._handle_error(str(e))


class ExtractionWorker(BaseWorker):
    """
    Stage 4: Extract and structure final data
    """
    
    def __init__(self, document_id: str, company_id: str, max_workers: int = 5):
        super().__init__(document_id, company_id)
        self.max_workers = max_workers
    
    def execute(self):
        logger.info(f"[EXTRACTION] Processing document {self.document_id}")
        status_updated = update_document_status(self.document_id, "extraction")
        
        if not status_updated:
            logger.error(f"[EXTRACTION] ❌ Failed to set extraction status - aborting")
            self._handle_error("Failed to update document status to 'extraction'")
            return
        
        try:
            # TODO: Implement actual extraction
            # - Parse LLM output
            # - Normalize field values
            # - Validate data types
            time.sleep(PROCESSING_SLEEP_TIME)
            
            status_updated = update_document_status(self.document_id, "extraction_complete")
            if not status_updated:
                logger.error(f"[EXTRACTION] ❌ Failed to set extraction_complete status")
                self._handle_error("Failed to update document status to 'extraction_complete'")
                return
            
            # Trigger next stage
            publish_to_topic(
                "document-evaluation",
                {"document_id": self.document_id, "company_id": self.company_id, "stage": "evaluation"}
            )
            
            logger.info(f"[EXTRACTION] ✓ Completed for {self.document_id}")
        except Exception as e:
            self._handle_error(str(e))


class EvaluationWorker(BaseWorker):
    """
    Stage 5: Quality evaluation and confidence scoring
    Supports parallel confidence calculation (ThreadPool for all fields)
    """
    
    def __init__(self, document_id: str, company_id: str, max_workers: int = 20):
        super().__init__(document_id, company_id)
        self.max_workers = max_workers
    
    def execute(self):
        logger.info(f"[EVALUATION] Processing document {self.document_id}")
        status_updated = update_document_status(self.document_id, "automated_evaluation")
        
        if not status_updated:
            logger.error(f"[EVALUATION] ❌ Failed to set automated_evaluation status - aborting")
            self._handle_error("Failed to update document status to 'automated_evaluation'")
            return
        
        try:
            # TODO: Implement actual evaluation
            # - Get extracted data from database
            # - Use ThreadPool to calculate confidence for each field in parallel
            # - Generate quality score
            time.sleep(PROCESSING_SLEEP_TIME)
            
            status_updated = update_document_status(self.document_id, "evaluation_complete")
            if not status_updated:
                logger.error(f"[EVALUATION] ❌ Failed to set evaluation_complete status")
                self._handle_error("Failed to update document status to 'evaluation_complete'")
                return
            
            logger.info(f"[EVALUATION] ✓ Completed for {self.document_id}")
        except Exception as e:
            self._handle_error(str(e))


# ============================================================
# WORKER COORDINATOR
# ============================================================

def process_document(message_data: Dict[str, Any]):
    """
    Coordinate document processing through pipeline stages.
    Routes to appropriate worker based on stage.
    """
    logger.info(f"[COORDINATOR] Starting process_document")
    document_id = message_data.get("document_id")
    company_id = message_data.get("company_id")
    stage = message_data.get("stage", "preprocess")
    
    logger.info(f"[COORDINATOR] Processing {document_id} at stage: {stage}")
    
    # Route to appropriate worker
    workers = {
        "preprocess": PreprocessWorker,
        "ocr": OCRWorker,
        "llm": LLMWorker,
        "extraction": ExtractionWorker,
        "evaluation": EvaluationWorker,
    }
    
    worker_class = workers.get(stage)
    if not worker_class:
        logger.warning(f"[COORDINATOR] Unknown stage: {stage}")
        return
    
    try:
        logger.info(f"[COORDINATOR] Got worker: {worker_class.__name__}")
        # Instantiate worker with appropriate thread pool size
        if stage in WORKER_THREAD_POOLS:
            worker = worker_class(
                document_id,
                company_id,
                max_workers=WORKER_THREAD_POOLS[stage]
            )
        else:
            worker = worker_class(document_id, company_id)
        
        logger.info(f"[COORDINATOR] Executing worker")
        # Execute worker
        worker.execute()
        logger.success(f"[COORDINATOR] Worker completed")
    except Exception as e:
        logger.error(f"[COORDINATOR] Exception: {type(e).__name__}: {e}", exc_info=True)
        update_document_status(document_id, "error", str(e))

# ============================================================
# PUB/SUB LISTENER
# ============================================================

class PubSubListener:
    """Listen to Pub/Sub topics and route messages to worker pool."""
    
    def __init__(self, project_id: str, max_processes: int = 5):
        self.project_id = project_id
        self.max_processes = max_processes
        self.subscriber = pubsub_v1.SubscriberClient()
        self.process_pool = ThreadPoolExecutor(max_workers=max_processes)
        self.futures = []
    
    def start(self):
        """Start listening to all processing topics."""
        topics = ["document-processing", "document-ocr", "document-llm", "document-extraction", "document-evaluation"]
        
        for topic_name in topics:
            subscription_name = f"{topic_name}-subscription"
            subscription_path = self.subscriber.subscription_path(self.project_id, subscription_name)
            
            try:
                # Subscribe with callback
                future = self.subscriber.subscribe(subscription_path, callback=self.on_message)
                self.futures.append(future)
                logger.info(f"[PUBSUB] Listening to {topic_name}")
            except Exception as e:
                logger.warning(f"[PUBSUB] Could not subscribe to {topic_name}: {e}")
    
    def on_message(self, message):
        """Callback when Pub/Sub message arrives."""
        try:
            # message.data is already bytes from Pub/Sub, just decode and parse JSON
            message_data = json.loads(message.data.decode('utf-8'))
            logger.info(f"[PUBSUB] Received message: {message_data}")
            
            # Submit to worker pool
            self.process_pool.submit(process_document, message_data)
            
            # Acknowledge message
            message.ack()
        except Exception as e:
            logger.error(f"[PUBSUB] Error processing message: {e}")
            message.ack()  # Still ack to avoid redelivery
    
    def wait(self):
        """Wait for all futures (blocking)."""
        for future in self.futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"[PUBSUB] Future error: {e}")

# ============================================================
# HTTP ENDPOINTS
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Kubernetes."""
    return jsonify({"status": "healthy", "service": "invoice.scanner.processing"}), 200


@app.route("/api/documents/<doc_id>/process", methods=["POST"])
def trigger_document_process(doc_id):
    """
    Manually trigger document processing.
    Used by API when document is uploaded.
    
    In production (Cloud Run): Uses Pub/Sub messaging
    In local dev (docker-compose): Falls back to direct worker invocation
    """
    try:
        data = request.get_json() or {}
        company_id = data.get("company_id")
        
        if not company_id:
            return jsonify({"error": "company_id required"}), 400
        
        message_data = {
            "document_id": doc_id,
            "company_id": company_id,
            "stage": "preprocess"
        }
        
        # Try to publish to Pub/Sub (production mode)
        pubsub_success = publish_to_topic("document-processing", message_data)
        
        # Fallback: If Pub/Sub fails (local mode without GCP credentials),
        # invoke the worker directly in a background thread
        if not pubsub_success:
            logger.info(f"[HTTP] Pub/Sub unavailable, falling back to direct worker invocation")
            worker_thread = threading.Thread(
                target=process_document,
                args=(message_data,),
                daemon=True
            )
            worker_thread.start()
        
        return jsonify({
            "status": "queued",
            "document_id": doc_id,
            "message": "Document queued for processing",
            "mode": "pubsub" if pubsub_success else "direct"
        }), 202
    except Exception as e:
        logger.error(f"[HTTP] Error triggering process: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents/<doc_id>/status", methods=["GET"])
def get_document_status(doc_id):
    """Get document processing status."""
    try:
        doc_details = get_document_details(doc_id)
        if not doc_details:
            return jsonify({"error": "Document not found"}), 404
        
        return jsonify({
            "document_id": doc_id,
            "status": doc_details.get("status"),
            "updated_at": doc_details.get("updated_at"),
            "error_message": doc_details.get("error_message")
        }), 200
    except Exception as e:
        logger.error(f"[HTTP] Error fetching status: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# MAIN ENTRY POINT
# ============================================================

# Start Pub/Sub listener in background thread when app starts
def start_pubsub_listener():
    """Start Pub/Sub listener in background thread."""
    try:
        listener = PubSubListener(GCP_PROJECT_ID, MAX_DOCUMENT_PROCESSES)
        listener_thread = threading.Thread(target=listener.start, daemon=True)
        listener_thread.start()
        logger.info(f"[PUBSUB] Listener started in background thread")
    except Exception as e:
        logger.warning(f"[PUBSUB] Could not start listener: {e}")
        logger.warning(f"[PUBSUB] Service will work with HTTP endpoints, manual Pub/Sub trigger will fail")

# Start listener when Flask app context is ready
@app.before_request
def startup():
    """Initialize on first request."""
    if not hasattr(app, '_pubsub_started'):
        start_pubsub_listener()
        app.config['_pubsub_started'] = True

if __name__ == "__main__":
    # Cloud Run sets PORT environment variable (default 8080)
    # For local dev: PORT defaults to 8000
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"[MAIN] Starting Processing Service on port {port}")
    
    # Start Flask app (Flask development server)
    app.run(host="0.0.0.0", port=port, debug=False)
