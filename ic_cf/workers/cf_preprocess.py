from ic_cf.workers.cf_base import cf_base
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("cf_preprocess")

class cf_preprocess(cf_base):
    """Cloud Function entry point for preprocessing worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event)
    
    def execute(self):
        """Execute the preprocessing worker logic."""
        ENTER_STATUS = "preprocessing"
        FAILED_STATUS = "preprocess_error"
        EXIT_STATUS = "preprocessed"
        NEXT_TOPIC_NAME = "document-ocr"
        NEXT_STAGE = "ocr"

        self._update_document_status(ENTER_STATUS)

        # self._update_document_status(FAILED_STATUS)

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic(NEXT_TOPIC_NAME, NEXT_STAGE)
