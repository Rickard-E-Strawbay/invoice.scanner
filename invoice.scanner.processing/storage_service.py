"""
Storage Service Abstraction Layer
Handles both local file storage and Google Cloud Storage

Supports:
- LOCAL: Development/testing with Docker volumes
- GCS: Production with Google Cloud Storage
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, BinaryIO
from datetime import datetime

logger = logging.getLogger(__name__)


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
        except ImportError:
            raise ImportError("google-cloud-storage is required for GCSStorageService. Install with: pip install google-cloud-storage")
        
        self.bucket_name = bucket_name
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID')
        
        try:
            # Initialize GCS client (uses Application Default Credentials)
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise ValueError(f"GCS bucket '{bucket_name}' does not exist")
            
            logger.info(f"GCSStorageService initialized with bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error initializing GCSStorageService: {e}")
            raise
    
    def save(self, file_path: str, file_content: BinaryIO) -> str:
        """Save file to GCS"""
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_file(file_content)
            gcs_path = f"gs://{self.bucket_name}/{file_path}"
            logger.info(f"File saved to GCS: {gcs_path}")
            return gcs_path
        except Exception as e:
            logger.error(f"Error saving file to GCS: {e}")
            raise
    
    def get(self, file_path: str) -> Optional[bytes]:
        """Retrieve file from GCS"""
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                return blob.download_as_bytes()
            logger.warning(f"File not found in GCS: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving file from GCS: {e}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """Delete file from GCS"""
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.delete()
                logger.info(f"File deleted from GCS: {file_path}")
                return True
            logger.warning(f"File not found for deletion in GCS: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {e}")
            raise
    
    def list(self, directory: str) -> List[str]:
        """List files in GCS directory"""
        try:
            # Ensure directory ends with /
            if directory and not directory.endswith('/'):
                directory += '/'
            
            blobs = self.client.list_blobs(
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
            logger.error(f"Error listing files in GCS: {e}")
            raise
    
    def exists(self, file_path: str) -> bool:
        """Check if file exists in GCS"""
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence in GCS: {e}")
            raise


def get_storage_service() -> StorageService:
    """
    Factory function to get appropriate storage service based on environment
    
    Environment variables:
    - STORAGE_TYPE: 'local' (default) or 'gcs'
    
    For GCS:
    - GCS_BUCKET: Bucket name (required)
    - GCP_PROJECT_ID: GCP project ID (optional, uses ADC)
    
    Returns:
        StorageService: LocalStorageService or GCSStorageService
    """
    storage_type = os.environ.get('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 'gcs':
        bucket_name = os.environ.get('GCS_BUCKET')
        if not bucket_name:
            raise ValueError("GCS_BUCKET environment variable is required when STORAGE_TYPE=gcs")
        
        project_id = os.environ.get('GCP_PROJECT_ID')
        logger.info(f"Using GCSStorageService with bucket: {bucket_name}")
        return GCSStorageService(bucket_name=bucket_name, project_id=project_id)
    
    else:
        logger.info("Using LocalStorageService")
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
