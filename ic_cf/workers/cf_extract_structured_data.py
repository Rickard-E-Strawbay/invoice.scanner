from workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger
import time
from ic_shared.configuration.config import PROCESSING_SLEEP_TIME
from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import EXTRACTION_STATUS, EXTRACTION_ERROR
from ic_shared.configuration.defines import STAGE_EVALUATION, TOPIC_NAME_EVALUATION

logger = ComponentLogger("cf_extract_structured_data")

class cf_extract_structured_data(cf_base):
    """Cloud Function entry point for structured data extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_structured_data")
    
    def execute(self):
        """Execute the structured data extraction worker logic."""
        ENTER_STATUS = EXTRACTION_STATUS[ENTER]
        FAILED_STATUS = EXTRACTION_ERROR
        EXIT_STATUS = EXTRACTION_STATUS[EXIT]
        NEXT_TOPIC_NAME = TOPIC_NAME_EVALUATION
        NEXT_STAGE = STAGE_EVALUATION

        try:
            self._update_document_status(ENTER_STATUS)
            
            # TODO: Add actual extraction logic here
            # For now: mock delay to simulate processing
            time.sleep(PROCESSING_SLEEP_TIME)
            
            self._update_document_status(EXIT_STATUS)
            self._publish_to_topic(NEXT_TOPIC_NAME, NEXT_STAGE)
            
            logger.info(f"✓ Completed data extraction for document {self.document_id}")
        except Exception as e:
            logger.error(f"❌ Error during data extraction: {e}")
            self._handle_error("cf_extract_structured_data", FAILED_STATUS, str(e))
