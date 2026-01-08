from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import PREPROCESS_STATUS, PREPROCESS_ERROR
from ic_shared.configuration.defines import STAGE_OCR, TOPIC_NAME_OCR

class cf_preprocess(cf_base):
    """Cloud Function entry point for preprocessing worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_preprocess")
    
    def execute(self):
        """Execute the preprocessing worker logic."""
        ENTER_STATUS = PREPROCESS_STATUS[ENTER]
        EXIT_STATUS = PREPROCESS_STATUS[EXIT]
        NEXT_TOPIC_NAME = TOPIC_NAME_OCR
        NEXT_STAGE = STAGE_OCR

        self._update_document_status(ENTER_STATUS)

        # self._update_document_status(PREPROCESS_ERROR)

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic(NEXT_TOPIC_NAME, NEXT_STAGE)
