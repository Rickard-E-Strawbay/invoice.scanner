import os
from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT, ERROR
from ic_shared.configuration.defines import LLM_STATUS


from incoive_llm_prediction.prediction_manager import PredictionManager

class cf_predict_invoice_data(cf_base):
    """Cloud Function entry point for LLM prediction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_predict_invoice_data")
    
    def execute(self):
        """Execute the LLM prediction worker logic."""
        ENTER_STATUS = LLM_STATUS[ENTER]
        EXIT_STATUS = LLM_STATUS[EXIT]
        
        self._update_document_status(ENTER_STATUS)

        try:
            # Fetch document from storage
            # prediction_manager = PredictionManager()
            # document = self._fetch_document()
            # llm_response_content = prediction_manager.predict_invoice(document)
            
            # self.logger.info(f"***************************************************")
            #self.logger.success(f"LLM prediction completed: {llm_response_content}")
            # self.logger.info(f"***************************************************")
            self._update_document_status(EXIT_STATUS)
            self._publish_to_topic()
            
        except Exception as e:
            self.logger.error(f"LLM prediction failed: {str(e)}")
            ERROR_STATUS = LLM_STATUS[ERROR]
            self._update_document_status(ERROR_STATUS)   


            
