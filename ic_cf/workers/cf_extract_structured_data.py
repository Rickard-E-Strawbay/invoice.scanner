from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import EXTRACTION_STATUS

class cf_extract_structured_data(cf_base):
    """Cloud Function entry point for structured data extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_structured_data")
    
    def execute(self):
        """Execute the structured data extraction worker logic."""
        ENTER_STATUS = EXTRACTION_STATUS[ENTER]
        EXIT_STATUS = EXTRACTION_STATUS[EXIT]
        # ERROR_STATUS = EXTRACTION_STATUS[ERROR]
        # FAIL_STATUS = EXTRACTION_STATUS[FAIL]

        self._update_document_status(ENTER_STATUS)

        # TODO: Add actual extraction logic here

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic()
