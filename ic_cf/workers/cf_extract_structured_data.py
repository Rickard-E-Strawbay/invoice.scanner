import json
import os
from workers.cf_base import cf_base
from workers.peppol_manager import PeppolManager

from ic_shared.configuration.defines import ENTER, EXIT
from ic_shared.configuration.defines import EXTRACTION_STATUS
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("cf_extract_structured_data")

class cf_extract_structured_data(cf_base):
    """Cloud Function entry point for structured data extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_structured_data")
        self._peppol_manager = PeppolManager()
    
    def execute(self):
        """Execute the structured data extraction worker logic."""
        ENTER_STATUS = EXTRACTION_STATUS[ENTER]
        EXIT_STATUS = EXTRACTION_STATUS[EXIT]
        # ERROR_STATUS = EXTRACTION_STATUS[ERROR]
        # FAIL_STATUS = EXTRACTION_STATUS[FAIL]

        self._update_document_status(ENTER_STATUS)

        # Get mandatory PEPPOL fields
        mandatory_fields = self._peppol_manager.get_mandatory_fields()
        self.logger.info(f"Using {len(mandatory_fields)} mandatory PEPPOL fields for extraction")

        

        # TODO: Add actual extraction logic here

        self._update_document_status(EXIT_STATUS)
        self._publish_to_topic()

