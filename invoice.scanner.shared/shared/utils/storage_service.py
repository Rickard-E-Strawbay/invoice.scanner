"""
Storage Service Abstraction Layer
Handles both local file storage and Google Cloud Storage

Supports:
- LOCAL: Development/testing with Docker volumes
- GCS: Production with Google Cloud Storage
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, BinaryIO
from datetime import datetime

from shared.logging import ComponentLogger

logger = ComponentLogger("StorageService")


class StorageService(ABC):
    """Abstract storage service interface"""
    
    @abstractmethod
    def save(self, file_path: str, file_content: BinaryIO) -> str:
        """Save file and return storage location"""
        pass
    
    @abstractmethod
    def get(self, file_path: str) -> Optional[bytes]:
        """Retrieve file content"""
        pass
    
    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file"""
        pass
    
    @abstractmethod
    def list(self, directory: str) -> List[str]:
        """List files in directory"""
        pass
    
    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage for development"""
    
    def __init__(self, base_path: str = "/app/documents"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageService initialized with base_path: {self.base_path}")
    
    def save(self, file_path: str, file_content: BinaryIO) -> str:
        """Save file to local filesystem"""
        full_path = self.base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, 'wb') as f:
                f.write(file_content.read())
            logger.info(f"File saved locally: {full_path}")
            return str(full_path)
        except Exception as e:
            logger.error(f"Error saving file locally: {e}")
            raise
    
    def get(self, file_path: str) -> Optional[bytes]:
        """Retrieve file from local filesystem"""
        full_path = self.base_path / file_path
        
        try:
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    return f.read()
            logger.warning(f"File not found locally: {full_path}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving file locally: {e}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        full_path = self.base_path / file_path
        
        try:
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted locally: {full_path}")
                return True
            logger.warning(f"File not found for deletion: {full_path}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file locally: {e}")
            raise
    
    def list(self, directory: str) -> List[str]:
        """List files in local directory"""
        full_path = self.base_path / directory
        
        try:
            if not full_path.exists():
                return []
            
            files = []
            for item in full_path.rglob('*'):
                if item.is_file():
                    # Return relative path from base_path
                    rel_path = item.relative_to(self.base_path)
                    files.append(str(rel_path))
            
            logger.info(f"Listed {len(files)} files in {directory}")
            return files
        except Exception as e:
            logger.error(f"Error listing files locally: {e}")
            raise
    
    def exists(self, file_path: str) -> bool:
        """Check if file exists locally"""
        full_path = self.base_path / file_path
        return full_path.exists()


class GCSStorageService(StorageService):
    """Google Cloud Storage implementation for production"""
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        try:
            from google.cloud import storage
            self.storage_module = storage
        except ImportError:
            raise ImportError("google-cloud-storage is required for GCSStorageService. Install with: pip install google-cloud-storage")
        
        self.bucket_name = bucket_name
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID')
        
        logger.info(f"GCSStorageService initialized for bucket: {bucket_name}, project: {self.project_id}")
        logger.info(f"Note: storage.Client() created per-request for connection pool stability")
    
    def _get_client(self):
        """Create a new storage client for this request (per-request pattern)
        
        This prevents connection pool exhaustion with high concurrency.
        Each request gets its own client and connection lifecycle.
        """
        try:
            client = self.storage_module.Client(project=self.project_id)
            return client
        except Exception as e:
            logger.error(f"Failed to create GCS client: {type(e).__name__}: {e}", exc_info=True)
            raise
    
    def _get_bucket(self, client):
        """Get bucket reference from client"""
        return client.bucket(self.bucket_name)
    
    def save(self, file_path: str, file_content: BinaryIO) -> str:
        """Save file to GCS (per-request client)"""
        client = None
        try:
            client = self._get_client()
            bucket = self._get_bucket(client)
            blob = bucket.blob(file_path)
            blob.upload_from_file(file_content)
            gcs_path = f"gs://{self.bucket_name}/{file_path}"
            logger.info(f"✅ File saved to GCS: {gcs_path}")
            return gcs_path
        except Exception as e:
            logger.error(f"❌ Error saving file to GCS: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Warning closing GCS client: {e}")
    
    def get(self, file_path: str) -> Optional[bytes]:
        """Retrieve file from GCS (per-request client)"""
        client = None
        try:
            client = self._get_client()
            bucket = self._get_bucket(client)
            blob = bucket.blob(file_path)
            
            logger.info(f"Downloading {file_path}...")
            content = blob.download_as_bytes()
            logger.info(f"✅ Successfully downloaded {file_path} ({len(content)} bytes)")
            return content
                
        except Exception as e:
            # If download fails, it means file doesn't exist or GCS error
            if "404" in str(e) or "Not Found" in str(e):
                logger.warning(f"File not found in GCS: {file_path}")
                return None
            else:
                logger.error(f"❌ Error retrieving file from GCS ({file_path}): {type(e).__name__}: {str(e)}", exc_info=True)
                raise
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Warning closing GCS client: {e}")
    
    def delete(self, file_path: str) -> bool:
        """Delete file from GCS (per-request client)"""
        client = None
        try:
            client = self._get_client()
            bucket = self._get_bucket(client)
            blob = bucket.blob(file_path)
            blob.delete()
            logger.info(f"✅ File deleted from GCS: {file_path}")
            return True
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                logger.warning(f"File not found for deletion in GCS: {file_path}")
                return False
            logger.error(f"❌ Error deleting file from GCS: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Warning closing GCS client: {e}")
    
    def list(self, directory: str) -> List[str]:
        """List files in GCS directory (per-request client)"""
        client = None
        try:
            client = self._get_client()
            # Ensure directory ends with /
            if directory and not directory.endswith('/'):
                directory += '/'
            
            blobs = client.list_blobs(
                self.bucket_name,
                prefix=directory,
                delimiter='/'
            )
            
            files = []
            for blob in blobs:
                files.append(blob.name)
            
            logger.info(f"Listed {len(files)} files in GCS directory: {directory}")
            return files
        except Exception as e:
            logger.error(f"❌ Error listing files in GCS: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Warning closing GCS client: {e}")
    
    def exists(self, file_path: str) -> bool:
        """Check if file exists in GCS (per-request client)
        
        Note: Uses download attempt instead of blob.exists() to avoid SSL timeout
        """
        client = None
        try:
            client = self._get_client()
            bucket = self._get_bucket(client)
            blob = bucket.blob(file_path)
            # Try to get blob metadata - if 404, file doesn't exist
            blob.reload()
            return True
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                return False
            logger.warning(f"Warning checking if file exists: {type(e).__name__}: {e}")
            return False
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Warning closing GCS client: {e}")


def get_storage_service() -> StorageService:
    """
    Factory function to get appropriate storage service based on environment
    
    Environment variables:
    - STORAGE_TYPE: 'local' (default) or 'gcs'
    - GCS_BUCKET: Bucket name (required for GCS)
    - GCP_PROJECT_ID: GCP project ID (optional, uses ADC)
    
    Returns:
        StorageService: LocalStorageService or GCSStorageService
    
    Logs all initialization steps for debugging timeout issues.
    """
    storage_type = os.environ.get('STORAGE_TYPE', 'local').lower()
    
    logger.info(f"STORAGE_TYPE={storage_type}")
    
    if storage_type == 'gcs':
        bucket_name = os.environ.get('GCS_BUCKET')
        if not bucket_name:
            error_msg = "GCS_BUCKET environment variable is required when STORAGE_TYPE=gcs"
            logger.error(f"{error_msg}")
            raise ValueError(error_msg)
        
        project_id = os.environ.get('GCP_PROJECT_ID')
        logger.info(f"Initializing GCS: bucket={bucket_name}, project={project_id}")
        
        try:
            service = GCSStorageService(bucket_name=bucket_name, project_id=project_id)
            logger.info(f"GCS initialization complete")
            return service
        except Exception as e:
            logger.error(f"Failed to initialize GCS: {str(e)}")
            raise
    
    else:
        logger.info("[get_storage_service] Using LocalStorageService")
        return LocalStorageService()


# Singleton instance (lazy loaded)
_storage_service: Optional[StorageService] = None


def init_storage_service() -> StorageService:
    """Initialize and cache storage service"""
    global _storage_service
    if _storage_service is None:
        _storage_service = get_storage_service()
    return _storage_service


def get_cached_storage_service() -> StorageService:
    """Get cached storage service instance"""
    if _storage_service is None:
        raise RuntimeError("Storage service not initialized. Call init_storage_service() first.")
    return _storage_service
