from typing import Optional
import json
import base64
import os

from ic_shared.configuration.defines import STAGES
from ic_shared.logging import ComponentLogger
from ic_shared.database import update_document_status
from ic_shared.database.connection import fetch_all
from ic_shared.utils.storage_service import get_storage_service


PUBSUB_MESSAGE_TEMPLATE = {
    "document_id": None,
    "company_id": None,
    "stage": None
}

class cf_base:
    """Base class for all processing workers."""
    
    def __init__(self, cloud_event, logger_name):
        data = self._read_cloud_event_data(cloud_event)
        self.logger = ComponentLogger(logger_name)
        self.document_id = data.get("document_id")
        self.company_id = data.get("company_id")
        self.stage_name = data.get("stage")
        self.logger.info(f"INIT {self.document_id}, company {self.company_id}, stage {self.stage_name}")
    
    def execute(self):
        """Override in subclass."""
        raise NotImplementedError
    
    def _read_cloud_event_data(self, cloud_event) -> dict:
        """Extract data from Cloud Event."""
        
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message = json.loads(pubsub_message)

        document_id = message.get("document_id")
        company_id = message.get("company_id")
        stage = message.get("stage")

        return {
            "document_id": document_id,
            "company_id": company_id,
            "stage": stage
        }   
    
    def _fetch_document(self):
        """Fetch document metadata and raw file content from storage."""
        
        # 1. Get document metadata from database
        sql = "SELECT raw_format FROM documents WHERE id = %s"
        results, success = fetch_all(sql, (str(self.document_id),))
        
        if not success or not results:
            raise ValueError(f"Document not found: {self.document_id}")
        
        doc = results[0]
        
        # 2. Get raw file from storage using format: raw/{id}.{raw_format}
        raw_format = doc["raw_format"]
        file_path = f"raw/{self.document_id}.{raw_format}"
        
        storage = get_storage_service()
        file_content = storage.get(file_path)
        
        if file_content is None:
            raise ValueError(f"Document file not found in storage: {file_path}")
        
        return {
            "id": self.document_id,
            "raw_format": raw_format,
            "content": file_content
        }
    
    def _update_document_status(self, document_status: str, error_message: Optional[str] = None):
        """Update document status in the database."""
        self.logger.info(f"NEW STATUS {document_status} for document {self.document_id}")
        return update_document_status(self.document_id, document_status)
    
    def __find_next_stage(self) -> Optional[str]:
        try:
            current_index = STAGES.index(self.stage_name)
            # Get next topic if it exists
            if current_index + 1 < len(STAGES):
                next_stage = STAGES[current_index + 1]
               
                return next_stage
        except (ValueError, IndexError):
            pass
        return None
        
    
    def _publish_to_topic(self, stage: Optional[str] = None):
        """Publish message to the specified topic for the next stage."""
        # Use provided stage or auto-detect next stage from pipeline
        if stage:
            next_stage_name = stage
        else:
            next_stage_name = self.__find_next_stage()

        next_topic_name = "document-" + next_stage_name if next_stage_name else None

        from main import publish_to_topic
        message_data = PUBSUB_MESSAGE_TEMPLATE.copy()
        message_data["document_id"] = self.document_id
        message_data["company_id"] = self.company_id
        message_data["stage"] = next_stage_name

        print(f"PUBLISH {self.document_id} to topic {next_topic_name} for stage {next_stage_name}")
        publish_to_topic(next_topic_name, message_data)
    
    def _handle_error(self,failed_status: str, error_msg: str):
        """Handle preprocessing errors."""
        self.logger.error(f"Error: {error_msg}")
        try:
            update_document_status(self.document_id, failed_status)
        except Exception as e:
            self.logger.error(f"Could not update status: {e}")