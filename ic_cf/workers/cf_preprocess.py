from pickle import FALSE
from workers.cf_base import cf_base
import json

from ic_shared.configuration.defines import ENTER, EXIT, ERROR, FAIL
from ic_shared.configuration.defines import PREPROCESS_STATUS
from ic_shared.database.connection import execute_sql

from incoive_llm_prediction.document_classifier import DocumentClassifier

class cf_preprocess(cf_base):
    """Cloud Function entry point for preprocessing worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_preprocess")
    
    def execute(self):
        """Execute the preprocessing worker logic."""
        ENTER_STATUS = PREPROCESS_STATUS[ENTER]
        EXIT_STATUS = PREPROCESS_STATUS[EXIT]
        ERROR_STATUS = PREPROCESS_STATUS[ERROR]

        # Reset relevant fields on re-processing
        dict_additional_fields = {}
        dict_additional_fields["invoice_data_raw"] = "{}"
        dict_additional_fields["invoice_data_peppol"] = "{}"
        dict_additional_fields["invoice_data_peppol_final"] = "{}"
        dict_additional_fields["error_message"] = ""
        dict_additional_fields["predicted_accuracy"] = 0.0
        dict_additional_fields["is_training"] = False
        self._update_document_status(ENTER_STATUS,None, dict_additional_fields  )

        try:
            document = self._fetch_document()
            # Add document_id for classifier to use when saving rendered images
            document['id'] = str(self.document_id)
            
            # Classify document using LLM (best-effort approach)
            classifier = DocumentClassifier()
            classification = classifier.classify(document)

            processed_image_filename = classification.pop('processed_image_filename', None)
            if processed_image_filename and processed_image_filename.startswith('processed/'):
                processed_image_filename = processed_image_filename.replace('processed/', '')
            
            
            dict_update = {}
            dict_update["content_type"] = json.dumps(classification)
            dict_update["processed_image_filename"] = processed_image_filename

            self._update_document_status(EXIT_STATUS,None, dict_update  )
            self._publish_to_topic()
            
        except Exception as e:
            self.logger.error(f"Preprocessing failed: {str(e)}")
            self._update_document_status(ERROR_STATUS)
            raise
    

