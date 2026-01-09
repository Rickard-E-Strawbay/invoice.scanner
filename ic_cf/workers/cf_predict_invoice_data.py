from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import LLM_STATUS

class cf_predict_invoice_data(cf_base):
    """Cloud Function entry point for LLM prediction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_predict_invoice_data")
    
    def execute(self):
        """Execute the LLM prediction worker logic."""
        ENTER_STATUS = LLM_STATUS[ENTER]
        EXIT_STATUS = LLM_STATUS[EXIT]
        # ERROR_STATUS = LLM_STATUS[ERROR]
        # FAIL_STATUS = LLM_STATUS[FAIL]

        self._update_document_status(ENTER_STATUS)

        # TODO: Add actual LLM logic here

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic()
