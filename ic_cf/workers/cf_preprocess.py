from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT, ERROR, FAIL
from ic_shared.configuration.defines import PREPROCESS_STATUS

class cf_preprocess(cf_base):
    """Cloud Function entry point for preprocessing worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_preprocess")
    
    def execute(self):
        """Execute the preprocessing worker logic."""
        ENTER_STATUS = PREPROCESS_STATUS[ENTER]
        EXIT_STATUS = PREPROCESS_STATUS[EXIT]
        # ERROR_STATUS = PREPROCESS_STATUS[ERROR]
        # FAIL_STATUS = PREPROCESS_STATUS[FAIL]


        self._update_document_status(ENTER_STATUS)

        # self._update_document_status(ERROR_STATUS)
        # self._update_document_status(FAIL_STATUS)

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic()
