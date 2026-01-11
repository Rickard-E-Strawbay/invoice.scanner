import os
import json
from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT, ERROR
from ic_shared.configuration.defines import LLM_STATUS
from ic_shared.database.connection import execute_sql

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
            # Fetch document from storage with metadata
            document = self._fetch_document()
            
            # Get content_type from database
            content_type = self._get_content_type()
            self.logger.info(f"Document content_type: {content_type}")
            
            # Run LLM prediction with appropriate method based on content_type
            prediction_manager = PredictionManager()
            result = prediction_manager.predict_invoice(document, content_type)
            
            # Save result to database
            if result.get("success"):
                invoice_data = result.get("invoice_data")
                self._save_invoice_data(invoice_data, result.get("raw_response"))
                self.logger.success(f"Invoice data extracted successfully")
            else:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"Prediction failed: {error_msg}")
                self._save_invoice_data(None, result.get("raw_response", error_msg))
            
            # Update status and publish to next stage
            self._update_document_status(EXIT_STATUS)
            self._publish_to_topic()
            
        except Exception as e:
            self.logger.error(f"LLM prediction failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            ERROR_STATUS = LLM_STATUS[ERROR]
            self._update_document_status(ERROR_STATUS)
    
    def _get_content_type(self) -> str:
        """Fetch content_type from document database."""
        sql = "SELECT content_type FROM documents WHERE id = %s"
        results, success = execute_sql(sql, (str(self.document_id),))
        
        if not success or not results:
            raise ValueError(f"Could not fetch content_type for document {self.document_id}")
        
        content_type_json = results[0].get("content_type")
        
        # Parse JSON if it's a string
        if isinstance(content_type_json, str):
            try:
                content_data = json.loads(content_type_json)
                content_type = content_data.get("content_classification", "image")
            except json.JSONDecodeError:
                # Fallback if JSON parse fails
                content_type = "image"
        else:
            content_type = content_type_json.get("content_classification", "image") if content_type_json else "image"
        
        return content_type
    
    def _save_invoice_data(self, invoice_data: dict, raw_response: str):
        """Save extracted invoice data to database."""
        try:
            # Prepare invoice_data JSON
            if invoice_data:
                invoice_json = json.dumps(invoice_data)
            else:
                # Save raw response for review if JSON parsing failed
                invoice_json = json.dumps({"raw_response": raw_response, "parse_error": True})
            
            # Update document with invoice_data
            sql = "UPDATE documents SET invoice_data = %s WHERE id = %s"
            results, success = execute_sql(sql, (invoice_json, str(self.document_id)))
            
            if success:
                self.logger.info(f"Invoice data saved to database")
            else:
                self.logger.error(f"Failed to save invoice data")
                
        except Exception as e:
            self.logger.error(f"Error saving invoice data: {str(e)}")   


            
