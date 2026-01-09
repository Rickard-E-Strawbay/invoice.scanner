from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import OCR_STATUS

class cf_extract_ocr_text(cf_base):
    """Cloud Function entry point for OCR text extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_ocr_text")
    
    def execute(self):
        """Execute the OCR extraction worker logic."""
        ENTER_STATUS = OCR_STATUS[ENTER]
        EXIT_STATUS = OCR_STATUS[EXIT]
        # ERROR_STATUS = OCR_STATUS[ERROR]
        # FAIL_STATUS = OCR_STATUS[FAIL]

        self._update_document_status(ENTER_STATUS)

        # TODO: Add actual OCR logic here

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic()
