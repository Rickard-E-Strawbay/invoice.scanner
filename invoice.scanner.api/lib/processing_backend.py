"""
Processing Backend Abstraction Layer

Provides environment-aware document processing backend selection.
Supports both local (Cloud Functions Framework) and cloud (Cloud Functions + Pub/Sub) deployments.

ARCHITECTURE:
    API (same code for local and cloud)
         ↓
    ProcessingBackend (abstract interface)
         ↓
    ┌──────────────────────────────┬─────────────────────┐
    │                              │                     │
    LOCAL                          CLOUD                 MOCK
    └──────────────────────────────┴─────────────────────┘
         │                              │                 │
    functions-framework         Cloud Functions       Testing
    (:9000)                     Pub/Sub Topic      Offline mode

ENVIRONMENT VARIABLES:
    PROCESSING_BACKEND: 'local' | 'cloud_functions' | 'mock'
    
    For local:
        PROCESSING_SERVICE_URL: HTTP endpoint (default: http://localhost:9000)
    
    For cloud_functions:
        GCP_PROJECT_ID: GCP project ID
        PUBSUB_TOPIC_ID: Pub/Sub topic name (default: 'document-processing')
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON

USAGE:
    from lib.processing_backend import get_processing_backend
    
    backend = get_processing_backend()
    result = backend.trigger_task(document_id, company_id)
    # Returns: {'task_id': 'xxx', 'status': 'queued' | 'submitted'}
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import requests

from shared.retry import (
    retry_with_config,
    HEALTH_CHECK_CONFIG,
    SERVICE_CALL_CONFIG,
)
from shared.logging import ComponentLogger

logger = ComponentLogger("LocalCloudFunctionsBackend")


# ===== ABSTRACT BASE CLASS =====

class ProcessingBackend(ABC):
    """
    Abstract interface for document processing.
    
    All backend implementations must provide:
    1. trigger_task(): Queue document for async processing
    2. get_task_status(): Get current processing status
    3. backend_type: String identifier ('local', 'cloud_functions', 'mock')
    """
    
    backend_type: str = "unknown"
    
    @abstractmethod
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """
        Trigger document processing asynchronously.
        
        Args:
            document_id: UUID of document to process
            company_id: UUID of company owning document
            
        Returns:
            {
                'task_id': str,           # Backend-specific task ID
                'status': 'queued' | 'submitted',
                'backend': str            # e.g. 'local', 'cloud_functions'
            }
            
        Raises:
            Exception: If task queueing fails (caller should handle gracefully)
        """
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get current processing status.
        
        Args:
            task_id: Task ID returned by trigger_task()
            
        Returns:
            {
                'status': 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE',
                'result': {...}   # Only if completed
            }
        """
        pass


# ===== LOCAL CLOUD FUNCTIONS BACKEND =====

class LocalCloudFunctionsBackend(ProcessingBackend):
    """
    Local Cloud Functions Framework backend for docker-compose development.
    
    Uses HTTP CloudEvents to trigger functions on local Cloud Functions Framework.
    Suitable for development, testing, and small deployments.
    """
    
    backend_type = "local"
    
    def __init__(self, processing_service_url: Optional[str] = None):
        """
        Initialize local Cloud Functions Framework backend.
        
        Args:
            processing_service_url: HTTP URL to processing service
                (default: from PROCESSING_SERVICE_URL env var or http://localhost:9000)
        """
        self.processing_url = processing_service_url or os.getenv(
            'PROCESSING_SERVICE_URL',
            'http://host.docker.internal:9000'
        )
        logger.info(f"Initialized with URL: {self.processing_url}")
    
    def _check_service_available(self) -> bool:
        """
        Check if Cloud Functions Framework is running and accessible.
        
        Returns:
            True if service is reachable, False otherwise
        """
        import requests
        
        try:
            response = requests.get(self.processing_url, timeout=2)
            logger.success("Cloud Functions Framework is available")
            return True
        except requests.exceptions.ConnectionError:
            logger.service_unavailable(
                self.processing_url,
                "Cloud Functions Framework not running. Start with: cd invoice.scanner.cloud.functions && ./local_server.sh"
            )
            return False
        except Exception as e:
            logger.error(f"Error checking service availability: {e}")
            return False
    
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """
        HTTP POST to local Cloud Functions Framework.
        
        First checks if Cloud Functions Framework is available.
        If not available, returns error status that indicates failed_preprocessing.
        
        Flow:
            API → Check service available
                  → If available: HTTP POST → Cloud Functions Framework → Processing
                  → If not available: Return error with status='service_unavailable'
        """
        import requests
        import base64
        
        # First check if Cloud Functions Framework is running
        if not self._check_service_available():
            logger.task_failed(
                "document processing",
                f"Cloud Functions Framework not running (doc={document_id})"
            )
            return {
                'task_id': None,
                'status': 'service_unavailable',
                'backend': self.backend_type,
                'error': 'Cloud Functions Framework not running. Start with: cd invoice.scanner.cloud.functions && ./local_server.sh'
            }
        
        try:
            logger.debug(
                f"Triggering task: doc={document_id}, company={company_id}"
            )
            
            # Format as CloudEvents HTTP Structured Content Mode
            # This is what Cloud Functions Framework expects locally
            pubsub_message = {
                'document_id': document_id,
                'company_id': company_id,
                'stage': 'preprocess'
            }
            
            # Encode as base64 like Pub/Sub does
            message_json = json.dumps(pubsub_message).encode('utf-8')
            encoded_message = base64.b64encode(message_json).decode('utf-8')
            
            # Format as CloudEvents HTTP Structured Content Mode
            cloud_event = {
                "specversion": "1.0",
                "type": "google.cloud.pubsub.topic.publish",
                "source": "//pubsub.googleapis.com/projects/local/topics/document-processing",
                "id": f"local-{document_id}",
                "time": "2025-12-27T00:00:00Z",
                "datacontenttype": "application/json",
                "data": {
                    "message": {
                        "data": encoded_message,
                        "attributes": {
                            "document_id": document_id,
                            "company_id": company_id
                        }
                    }
                }
            }
            
            logger.info(
                f"Sending CloudEvents HTTP to {self.processing_url}",
                emoji="📨"
            )
            
            response = requests.post(
                f"{self.processing_url}/",
                json=cloud_event,
                headers={"Content-Type": "application/cloudevents+json"},
                timeout=30
            )
            
            if response.status_code == 200 or response.status_code == 202:
                logger.task_complete(
                    "document processing",
                    f"doc={document_id}"
                )
                return {
                    'task_id': document_id,  # Use document_id as task_id for local
                    'status': 'queued',
                    'backend': self.backend_type
                }
            else:
                error_msg = f"Cloud Functions returned {response.status_code}"
                logger.error(f"{error_msg}")
                logger.error(f"Response: {response.text}")
                return {
                    'task_id': None,
                    'status': 'service_error',
                    'backend': self.backend_type,
                    'error': error_msg
                }
        
        except requests.exceptions.Timeout:
            error_msg = f"Cloud Functions Framework timeout at {self.processing_url}"
            logger.error(f"{error_msg}")
            return {
                'task_id': None,
                'status': 'service_unavailable',
                'backend': self.backend_type,
                'error': error_msg
            }
        except Exception as e:
            logger.error(f"Error triggering task: {e}")
            import traceback
            traceback.print_exc()
            return {
                'task_id': None,
                'status': 'service_error',
                'backend': self.backend_type,
                'error': str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Poll task status from local Celery backend.
        
        Queries the /api/tasks/status endpoint on processing service.
        """
        import requests
        
        try:
            response = requests.get(
                f"{self.processing_url}/api/tasks/status/{task_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Status endpoint returned {response.status_code}")
                return {
                    'task_id': task_id,
                    'status': 'UNKNOWN'
                }
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {
                'task_id': task_id,
                'status': 'UNKNOWN',
                'error': str(e)
            }


# ===== CLOUD FUNCTIONS BACKEND =====

class CloudFunctionsBackend(ProcessingBackend):
    """
    Google Cloud Functions backend for GCP deployments.
    
    Uses Cloud Tasks + Pub/Sub to trigger Cloud Functions.
    Provides auto-scaling, managed infrastructure, and production-grade processing.
    
    ARCHITECTURE:
        API → Cloud Tasks/Pub/Sub → Cloud Functions (preprocessing)
                                          ↓
                                    Cloud Functions (OCR)
                                          ↓
                                    ... (4 more stages)
                                          ↓
                                    Database status update
    """
    
    backend_type = "cloud_functions"
    
    def __init__(self):
        """
        Initialize Cloud Functions backend.
        
        Reads configuration from environment:
            GCP_PROJECT_ID: Google Cloud project ID
            PUBSUB_TOPIC_ID: Pub/Sub topic name (default: 'document-processing')
            GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
        """
        print(f"[CloudFunctionsBackend] Starting initialization...")
        
        try:
            print(f"[CloudFunctionsBackend] Attempting to import google-cloud-pubsub...")
            from google.cloud import pubsub_v1
            from google.oauth2 import service_account
            print(f"[CloudFunctionsBackend] ✅ google-cloud-pubsub imported successfully")
        except ImportError as import_error:
            error_msg = (
                "google-cloud-pubsub required for Cloud Functions backend. "
                f"Install: pip install google-cloud-pubsub. Error: {import_error}"
            )
            print(f"[CloudFunctionsBackend] ❌ {error_msg}")
            raise ImportError(error_msg)
        
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.topic_id = os.getenv('PUBSUB_TOPIC_ID', 'document-processing')
        
        print(f"[CloudFunctionsBackend] Environment: GCP_PROJECT_ID={self.project_id}, PUBSUB_TOPIC_ID={self.topic_id}")
        
        if not self.project_id:
            error_msg = (
                "GCP_PROJECT_ID environment variable not set. "
                "Required for Cloud Functions backend."
            )
            print(f"[CloudFunctionsBackend] ❌ {error_msg}")
            raise ValueError(error_msg)
        
        try:
            print(f"[CloudFunctionsBackend] Initializing Pub/Sub publisher...")
            # Initialize Pub/Sub publisher
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            print(f"[CloudFunctionsBackend] ✅ Pub/Sub publisher initialized, topic_path={self.topic_path}")
        except Exception as pubsub_error:
            error_msg = f"Failed to initialize Pub/Sub publisher: {pubsub_error}"
            print(f"[CloudFunctionsBackend] ❌ {error_msg}")
            raise
        
        logger.info(
            f"[CloudFunctionsBackend] ✅ Initialized for project={self.project_id}, "
            f"topic={self.topic_id}"
        )
        print(f"[CloudFunctionsBackend] ✅ Initialization complete")
    
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """
        Publish message to Pub/Sub topic.
        
        This triggers a Cloud Function that will start the processing pipeline.
        
        Flow:
            API → Pub/Sub Message → Cloud Function Trigger → Cloud Function
        """
        try:
            logger.debug(
                f"[CloudFunctionsBackend] Triggering task: doc={document_id}, "
                f"company={company_id}"
            )
            
            # Create message payload
            message_data = json.dumps({
                'document_id': document_id,
                'company_id': company_id,
                'stage': 'preprocess'  # First stage
            }).encode('utf-8')
            
            # Publish to Pub/Sub (this is async - returns immediately)
            publish_future = self.publisher.publish(
                self.topic_path,
                message_data
            )
            
            # Get message ID (synchronously wait for publish)
            message_id = publish_future.result(timeout=5)
            
            logger.info(
                f"[CloudFunctionsBackend] Message published: {message_id} "
                f"for doc={document_id}"
            )
            
            return {
                'task_id': message_id,
                'status': 'submitted',
                'backend': self.backend_type
            }
        
        except Exception as e:
            logger.error(f"[CloudFunctionsBackend] Error triggering task: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status from Cloud Tasks/Datastore.
        
        Note: Cloud Functions don't have built-in task status tracking like Celery.
        Status is managed via document table in database.
        This method is for API compatibility.
        """
        # In GCP, we query database directly (via API's get_document_status)
        # Cloud Functions don't provide task status like Celery
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'note': 'Use GET /documents/{id}/status for actual status'
        }


# ===== WORKER SERVICE BACKEND =====

class WorkerServiceBackend(ProcessingBackend):
    """
    Processing Worker Service backend (Cloud Run + Pub/Sub).
    
    Replaces serverless Cloud Functions with stateful Worker Service on Cloud Run.
    Provides:
    - Unlimited timeout for processing
    - Parallel workers (ThreadPool per stage)
    - Persistent state and intermediate result caching
    - Better scalability and resource efficiency
    
    ARCHITECTURE:
        API → HTTP POST → Worker Service
                             ↓
                        Pub/Sub Listener
                             ↓
                        Worker Coordinator
                             ├─ PreprocessWorker
                             ├─ OCRWorker (with ThreadPool)
                             ├─ LLMWorker (with ThreadPool)
                             ├─ ExtractionWorker
                             └─ EvaluationWorker (with ThreadPool)
    """
    
    backend_type = "worker_service"
    
    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize Worker Service backend.
        
        Args:
            service_url: HTTP URL to processing service
                (default: from PROCESSING_SERVICE_URL env var or http://processing:8000)
        """
        self.service_url = service_url or os.getenv(
            'PROCESSING_SERVICE_URL',
            'http://processing:8000'
        )
        logger.info(f"[WorkerServiceBackend] Initialized with URL: {self.service_url}")
    
    def _check_service_available(self) -> bool:
        """Check if Worker Service is running and accessible."""
        try:
            self._health_check_with_retry()
            logger.info(f"[WorkerServiceBackend] ✅ Worker Service is available")
            return True
        except Exception as e:
            logger.error(f"[WorkerServiceBackend] ❌ Health check failed: {e}")
            logger.error(f"[WorkerServiceBackend] ⚠️  Ensure Worker Service is running:")
            logger.error(f"[WorkerServiceBackend]    docker-compose up -d processing")
            return False
    
    @retry_with_config(config=HEALTH_CHECK_CONFIG)
    def _health_check_with_retry(self) -> None:
        """Perform health check with automatic retry (via decorator)"""
        response = requests.get(
            f"{self.service_url}/health",
            timeout=5
        )
        if response.status_code != 200:
            raise requests.exceptions.ConnectionError(
                f"Health check returned {response.status_code}"
            )
    
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """
        Trigger document processing via HTTP POST to Worker Service.
        
        Posts to /api/documents/{doc_id}/process endpoint with automatic retry.
        """
        try:
            # Ensure service is available before attempting POST
            if not self._check_service_available():
                return {
                    'task_id': None,
                    'status': 'service_unavailable',
                    'backend': self.backend_type,
                    'error': f'Worker Service not available at {self.service_url}'
                }
            
            # POST to worker service with automatic retry
            response = self._post_to_service_with_retry(document_id, company_id)
            
            if response.status_code == 202:  # Accepted
                logger.info(f"[WorkerServiceBackend] ✅ Document queued: {document_id}")
                return {
                    'task_id': document_id,
                    'status': 'queued',
                    'backend': self.backend_type
                }
            else:
                error_msg = f"Worker Service returned {response.status_code}"
                logger.error(f"[WorkerServiceBackend] ❌ {error_msg}")
                logger.error(f"[WorkerServiceBackend] Response: {response.text}")
                return {
                    'task_id': None,
                    'status': 'service_error',
                    'backend': self.backend_type,
                    'error': error_msg
                }
        
        except requests.exceptions.Timeout:
            error_msg = f"Worker Service timeout at {self.service_url}"
            logger.error(f"[WorkerServiceBackend] ❌ {error_msg}")
            return {
                'task_id': None,
                'status': 'service_unavailable',
                'backend': self.backend_type,
                'error': error_msg
            }
        except Exception as e:
            logger.error(f"[WorkerServiceBackend] Error triggering task: {e}", exc_info=True)
            return {
                'task_id': None,
                'status': 'service_error',
                'backend': self.backend_type,
                'error': str(e)
            }
    
    @retry_with_config(config=SERVICE_CALL_CONFIG)
    def _post_to_service_with_retry(self, document_id: str, company_id: str) -> requests.Response:
        """
        POST to worker service with automatic retry (via decorator).
        
        Retries with exponential backoff: 1s → 2s → 4s
        """
        logger.debug(f"[WorkerServiceBackend] Triggering task: doc={document_id}, company={company_id}")
        
        return requests.post(
            f"{self.service_url}/api/documents/{document_id}/process",
            json={'company_id': company_id},
            timeout=10
        )
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get document processing status from Worker Service.
        
        Queries /api/documents/{task_id}/status endpoint.
        """
        import requests
        
        try:
            response = requests.get(
                f"{self.service_url}/api/documents/{task_id}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'task_id': task_id,
                    'status': data.get('status', 'UNKNOWN'),
                    'document_id': data.get('document_id'),
                    'updated_at': data.get('updated_at'),
                    'error_message': data.get('error_message')
                }
            else:
                logger.warning(f"[WorkerServiceBackend] Status endpoint returned {response.status_code}")
                return {
                    'task_id': task_id,
                    'status': 'UNKNOWN'
                }
        except Exception as e:
            logger.error(f"[WorkerServiceBackend] Error getting task status: {e}")
            return {
                'task_id': task_id,
                'status': 'UNKNOWN',
                'error': str(e)
            }


# ===== MOCK BACKEND (FOR TESTING) =====

class MockBackend(ProcessingBackend):
    """
    Mock backend for testing without external dependencies.
    
    Useful for:
    - Unit tests
    - Development without Celery/GCP
    - CI/CD pipelines
    """
    
    backend_type = "mock"
    
    def __init__(self):
        logger.info("[MockBackend] Initialized")
    
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """Return mock task ID immediately (no actual processing)."""
        import uuid
        
        task_id = f"mock-{uuid.uuid4()}"
        logger.debug(f"[MockBackend] Mock task queued: {task_id}")
        
        return {
            'task_id': task_id,
            'status': 'queued',
            'backend': self.backend_type
        }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Return mock status."""
        return {
            'task_id': task_id,
            'status': 'SUCCESS',
            'backend': self.backend_type
        }


# ===== FACTORY FUNCTION =====

def get_processing_backend() -> ProcessingBackend:
    """
    Factory function to get environment-appropriate processing backend.
    
    Backend selection priority:
        1. PROCESSING_BACKEND env var (if explicitly set)
        2. GCP_PROJECT_ID env var (auto-detect cloud deployment)
        3. Default to 'local' (docker-compose)
    
    Supported backends:
        - 'local': Local Cloud Functions Framework (http://localhost:9000)
        - 'worker_service': Processing Worker Service (http://processing:8000 or custom URL)
        - 'cloud_functions': Cloud Functions + Pub/Sub (GCP production)
        - 'mock': Mock backend for testing
    
    Returns:
        Initialized ProcessingBackend instance
        
    Raises:
        ValueError: If backend cannot be initialized
        ImportError: If required dependencies missing
    """
    backend_name = os.getenv('PROCESSING_BACKEND', '').lower()
    
    # Auto-detect Cloud deployment if GCP_PROJECT_ID set
    if not backend_name and os.getenv('GCP_PROJECT_ID'):
        backend_name = 'cloud_functions'
    
    # Default to local
    if not backend_name:
        backend_name = 'local'
    
    logger.info(f"[ProcessingBackend] Initializing backend: {backend_name}")
    
    if backend_name == 'local':
        return LocalCloudFunctionsBackend()
    elif backend_name == 'worker_service':
        return WorkerServiceBackend()
    elif backend_name == 'cloud_functions':
        return CloudFunctionsBackend()
    elif backend_name == 'mock':
        return MockBackend()
    else:
        raise ValueError(f"Unknown processing backend: {backend_name}")


# ===== SINGLETON PATTERN (OPTIONAL) =====
# Initialize once and reuse

_backend_instance: Optional[ProcessingBackend] = None


def init_processing_backend() -> ProcessingBackend:
    """
    Initialize singleton processing backend instance.
    
    Call this once at application startup.
    """
    global _backend_instance
    
    if _backend_instance is None:
        _backend_instance = get_processing_backend()
    
    return _backend_instance


def get_backend() -> ProcessingBackend:
    """Get singleton backend instance."""
    return init_processing_backend()
