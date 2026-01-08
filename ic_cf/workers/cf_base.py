from typing import Optional
import json
import base64

from ic_shared.logging import ComponentLogger
from ic_shared.database import get_document_status, update_document_status

PUBSUB_MESSAGE_TEMPLATE = {
    "document_id": None,
    "company_id": None,
    "stage": None
}

class cf_base:
    """Base class for all processing workers."""
    
    def __init__(self, cloud_event ):
        data = self._read_cloud_event_data(cloud_event)
        self.document_id = data.get("document_id")
        self.company_id = data.get("company_id")
        self.stage_name = data.get("stage")
    
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
    
    def _update_document_status(self, document_status: str, error_message: Optional[str] = None):
        """Update document status in the database."""
        return update_document_status(self.document_id, document_status)
    
    def _publish_to_topic(self, next_topic_name: str, next_stage_name: str):
        """Publish message to the specified topic for the next stage."""

        from main import publish_to_topic
        message_data = PUBSUB_MESSAGE_TEMPLATE.copy()
        message_data["document_id"] = self.document_id
        message_data["company_id"] = self.company_id
        message_data["stage"] = next_stage_name
        publish_to_topic(next_topic_name, message_data)
    
    def _handle_error(self, prefix: str,failed_status: str, error_msg: str):
        """Handle preprocessing errors."""
        logger = ComponentLogger(prefix)
        logger.error(f"Error: {error_msg}")
        try:
            update_document_status(self.document_id, failed_status)
        except Exception as e:
            logger.error(f"Could not update status: {e}")