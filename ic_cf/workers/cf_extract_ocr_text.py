from workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger
import time
from ic_shared.configuration.config import PROCESSING_SLEEP_TIME
from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import OCR_STATUS, OCR_ERROR
from ic_shared.configuration.defines import STAGE_LLM, TOPIC_NAME_LLM

logger = ComponentLogger("cf_extract_ocr_text")

class cf_extract_ocr_text(cf_base):
    """Cloud Function entry point for OCR text extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_ocr_text")
    
    def execute(self):
        """Execute the OCR extraction worker logic."""
        ENTER_STATUS = OCR_STATUS[ENTER]
        FAILED_STATUS = OCR_ERROR
        EXIT_STATUS = OCR_STATUS[EXIT]
        NEXT_TOPIC_NAME = TOPIC_NAME_LLM
        NEXT_STAGE = STAGE_LLM

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
