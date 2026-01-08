from workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger
import time
from ic_shared.configuration.config import PROCESSING_SLEEP_TIME
from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import LLM_STATUS, LLM_ERROR
from ic_shared.configuration.defines import STAGE_EXTRACTION, TOPIC_NAME_EXTRACTION

logger = ComponentLogger("cf_predict_invoice_data")

class cf_predict_invoice_data(cf_base):
    """Cloud Function entry point for LLM prediction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_predict_invoice_data")
    
    def execute(self):
        """Execute the LLM prediction worker logic."""
        ENTER_STATUS = LLM_STATUS[ENTER]
        FAILED_STATUS = LLM_ERROR
        EXIT_STATUS = LLM_STATUS[EXIT]
        NEXT_TOPIC_NAME = TOPIC_NAME_EXTRACTION
        NEXT_STAGE = STAGE_EXTRACTION

        try:
            self._update_document_status(ENTER_STATUS)
            
            # TODO: Add actual LLM logic here
            # For now: mock delay to simulate processing
            time.sleep(PROCESSING_SLEEP_TIME)
            
            self._update_document_status(EXIT_STATUS)
            self._publish_to_topic(NEXT_TOPIC_NAME, NEXT_STAGE)
            
            logger.info(f"✓ Completed LLM prediction for document {self.document_id}")
        except Exception as e:
            logger.error(f"❌ Error during LLM prediction: {e}")
            self._handle_error("cf_predict_invoice_data", FAILED_STATUS, str(e))
