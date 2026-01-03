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

# Import database config (unified from shared package)
from shared.database.config import get_connection, RealDictCursor
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

logger.info(f"Processing Service initialized")
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
    """
    Get database connection (same as API uses).
    Routes to Cloud SQL Connector (Cloud Run) or local TCP (docker-compose).
    """
    try:
        from shared.database.config import get_connection as get_db_conn
        conn = get_db_conn()
        return conn
    except Exception as e:
        logger.database_error("connection", str(e))
        return None


def update_document_status(document_id: str, status: str, error_message: Optional[str] = None) -> bool:
    """Update document processing status in database."""
    try:
        conn = get_db_connection()
        if not conn:
            logger.database_error("connection", "Cannot connect to database")
            return False

        try:
            cursor = conn.cursor()
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
            conn.commit()
            logger.success(f"Document {document_id} status: {status}")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.database_error("update_status", str(e))
        return False


def get_document_details(document_id: str) -> Dict[str, Any]:
    """Get document details from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM documents WHERE id = %s",
                (document_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else {}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.database_error("fetch_document", str(e))
        return {}


def save_extracted_text(document_id: str, extracted_text: str, ocr_data: Dict[str, Any] = None) -> bool:
    """Save extracted text and OCR data to database."""
    try:
        conn = get_db_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
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
            conn.commit()
            logger.success(f"Saved OCR data for {document_id}")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.database_error("save_ocr_data", str(e))
        return False


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
        update_document_status(self.document_id, "preprocessing")
        
        try:
            # TODO: Implement actual preprocessing
            # - Get raw file from storage
            # - Convert PDF to PNG (600 DPI)
            # - Save to processed storage
            time.sleep(PROCESSING_SLEEP_TIME)
            
            update_document_status(self.document_id, "preprocessed")
            
            # Trigger next stage
            publish_to_topic(
                "document-ocr",
                {"document_id": self.document_id, "company_id": self.company_id, "stage": "ocr"}
            )
            
            logger.task_complete("preprocessing", f"doc={self.document_id}")
        except Exception as e:
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
        update_document_status(self.document_id, "ocr_extracting")
        
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
            
            update_document_status(self.document_id, "ocr_complete")
            
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
        update_document_status(self.document_id, "llm_predicting")
        
        try:
            # TODO: Implement actual LLM processing
            # - Get OCR text from database
            # - Parse into line items
            # - Use ThreadPool to call LLM in parallel for each item
            # - Combine results
            time.sleep(PROCESSING_SLEEP_TIME)
            
            update_document_status(self.document_id, "llm_complete")
            
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
        update_document_status(self.document_id, "extraction")
        
        try:
            # TODO: Implement actual extraction
            # - Parse LLM output
            # - Normalize field values
            # - Validate data types
            time.sleep(PROCESSING_SLEEP_TIME)
            
            update_document_status(self.document_id, "extraction_complete")
            
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
        update_document_status(self.document_id, "automated_evaluation")
        
        try:
            # TODO: Implement actual evaluation
            # - Get extracted data from database
            # - Use ThreadPool to calculate confidence for each field in parallel
            # - Generate quality score
            time.sleep(PROCESSING_SLEEP_TIME)
            
            update_document_status(self.document_id, "evaluation_complete")
            
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
        # Instantiate worker with appropriate thread pool size
        if stage in WORKER_THREAD_POOLS:
            worker = worker_class(
                document_id,
                company_id,
                max_workers=WORKER_THREAD_POOLS[stage]
            )
        else:
            worker = worker_class(document_id, company_id)
        
        # Execute worker
        worker.execute()
    except Exception as e:
        logger.error(f"[COORDINATOR] Error processing {document_id}: {e}")
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
            message_data = json.loads(base64.b64decode(message.data).decode())
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
