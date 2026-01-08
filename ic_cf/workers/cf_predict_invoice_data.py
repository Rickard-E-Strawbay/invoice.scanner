from ic_cf.workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger
import time
from ic_shared.configuration.config import PROCESSING_SLEEP_TIME

logger = ComponentLogger("cf_predict_invoice_data")

class cf_predict_invoice_data(cf_base):
    """Cloud Function entry point for LLM prediction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event)
    
    def execute(self):
        """Execute the LLM prediction worker logic."""
        ENTER_STATUS = "llm_predicting"
        FAILED_STATUS = "llm_error"
        EXIT_STATUS = "llm_complete"
        NEXT_TOPIC_NAME = "document-extraction"
        NEXT_STAGE = "extraction"

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
