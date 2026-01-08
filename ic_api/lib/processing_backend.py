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
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json

from ic_shared.logging import ComponentLogger

logger = ComponentLogger("ProcessingBackend")


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
        
        WARNING: This is called during task execution, NOT at startup.
        Failures are logged as warnings, not errors.
        
        Returns:
            True if service is reachable, False otherwise
        """
        import requests
        
        try:
            response = requests.get(self.processing_url, timeout=2)
            logger.info(f"✅ Cloud Functions Framework is available")
            return True
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️  Cloud Functions Framework NOT available at {self.processing_url}")
            logger.warning(f"Document will be marked for retry or fallback")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Error checking service availability: {e}")
            return False
    
    def trigger_task(self, document_id: str, company_id: str) -> Dict[str, Any]:
        """
        HTTP POST to local Cloud Functions Framework.
        
        Attempts to send task immediately WITHOUT pre-flight health checks.
        If service unavailable, error is returned but doesn't block or retry.
        
        This is Option A: Lazy health checks - no blocking operations.
        """
        import requests
        import base64
        
        try:
            logger.debug(
                f"[LocalCloudFunctionsBackend] Triggering task: doc={document_id}, company={company_id}"
            )
            
            # Format as CloudEvents HTTP Structured Content Mode
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
                f"[LocalCloudFunctionsBackend] 📨 Sending CloudEvents HTTP to {self.processing_url}"
            )
            
            # Send immediately WITHOUT health check - just try to reach the service
            response = requests.post(
                f"{self.processing_url}/",
                json=cloud_event,
                headers={"Content-Type": "application/cloudevents+json"},
                timeout=5  # Reduced from 30 - fail fast if service unreachable
            )
            
            if response.status_code == 200 or response.status_code == 202:
                logger.info(
                    f"[LocalCloudFunctionsBackend] ✅ Task triggered successfully: doc={document_id}"
                )
                return {
                    'task_id': document_id,
                    'status': 'queued',
                    'backend': self.backend_type
                }
            else:
                error_msg = f"Cloud Functions returned {response.status_code}"
                logger.warning(f"⚠️  {error_msg}")
                return {
                    'task_id': None,
                    'status': 'service_error',
                    'backend': self.backend_type,
                    'error': error_msg
                }
        
        except requests.exceptions.Timeout:
            error_msg = f"Cloud Functions timeout at {self.processing_url}"
            logger.warning(f"⚠️  {error_msg}")
            return {
                'task_id': None,
                'status': 'service_unavailable',
                'backend': self.backend_type,
                'error': error_msg
            }
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to Cloud Functions at {self.processing_url}"
            logger.warning(f"⚠️  {error_msg}")
            return {
                'task_id': None,
                'status': 'service_unavailable',
                'backend': self.backend_type,
                'error': error_msg
            }
        except Exception as e:
            logger.warning(f"⚠️  Error triggering task: {e}")
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
        logger.info(f"Starting initialization...")
        
        try:
            logger.info(f"Attempting to import google-cloud-pubsub...")
            from google.cloud import pubsub_v1
            from google.oauth2 import service_account
            logger.success(f"✅ google-cloud-pubsub imported successfully")
        except ImportError as import_error:
            error_msg = (
                "google-cloud-pubsub required for Cloud Functions backend. "
                f"Install: pip install google-cloud-pubsub. Error: {import_error}"
            )
            logger.error(f"❌ {error_msg}")
            raise ImportError(error_msg)
        
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.topic_id = os.getenv('PUBSUB_TOPIC_ID', 'document-processing')
        
        logger.info(f"Environment: GCP_PROJECT_ID={self.project_id}, PUBSUB_TOPIC_ID={self.topic_id}")
        
        if not self.project_id:
            error_msg = (
                "GCP_PROJECT_ID environment variable not set. "
                "Required for Cloud Functions backend."
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        try:
            logger.info(f"Initializing Pub/Sub publisher...")
            # Initialize Pub/Sub publisher
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            logger.success(f"✅ Pub/Sub publisher initialized, topic_path={self.topic_path}")
        except Exception as pubsub_error:
            error_msg = f"Failed to initialize Pub/Sub publisher: {pubsub_error}"
            logger.error(f"❌ {error_msg}")
            raise
        
        logger.info(
            f"[CloudFunctionsBackend] ✅ Initialized for project={self.project_id}, "
            f"topic={self.topic_id}"
        )
        logger.success(f"✅ Initialization complete")
    
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
            logger.error(f"Error triggering task: {e}")
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
        logger.debug(f"Mock task queued: {task_id}")
        
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
    
    logger.info(f"Initializing backend: {backend_name}")
    
    if backend_name == 'local':
        return LocalCloudFunctionsBackend()
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
