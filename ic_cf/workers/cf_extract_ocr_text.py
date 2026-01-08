from ic_cf.workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger
import time
from ic_shared.configuration.config import PROCESSING_SLEEP_TIME

logger = ComponentLogger("cf_extract_ocr_text")

class cf_extract_ocr_text(cf_base):
    """Cloud Function entry point for OCR text extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event)
    
    def execute(self):
        """Execute the OCR extraction worker logic."""
        ENTER_STATUS = "ocr_extracting"
        FAILED_STATUS = "ocr_error"
        EXIT_STATUS = "ocr_complete"
        NEXT_TOPIC_NAME = "document-llm"
        NEXT_STAGE = "llm"

        try:
            self._update_document_status(ENTER_STATUS)
            
            # TODO: Add actual OCR logic here
            # For now: mock delay to simulate processing
            time.sleep(PROCESSING_SLEEP_TIME)
            
            self._update_document_status(EXIT_STATUS)
            self._publish_to_topic(NEXT_TOPIC_NAME, NEXT_STAGE)
            
            logger.info(f"✓ Completed OCR for document {self.document_id}")
        except Exception as e:
            logger.error(f"❌ Error during OCR extraction: {e}")
            self._handle_error("cf_extract_ocr_text", FAILED_STATUS, str(e))
