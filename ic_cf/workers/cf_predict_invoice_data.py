import os
import json
from ic_shared.database.document_operations import merge_peppol_json
from workers.cf_base import cf_base

from ic_shared.configuration.defines import ENTER, EXIT, ERROR
from ic_shared.configuration.defines import LLM_STATUS
from ic_shared.database.connection import execute_sql, fetch_all

from incoive_llm_prediction.prediction_manager import PredictionManager


class cf_predict_invoice_data(cf_base):
    """Cloud Function entry point for LLM prediction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_predict_invoice_data")
    
    def execute(self):
        """Execute the LLM prediction worker logic."""
        ENTER_STATUS = LLM_STATUS[ENTER]
        EXIT_STATUS = LLM_STATUS[EXIT]
        ERROR_STATUS = LLM_STATUS[ERROR]

        self._update_document_status(ENTER_STATUS)
        try:
            # Fetch document from storage with metadata
            document = self._fetch_document()
            
            # Get content_type from database
            content_type = self._get_content_type()    

            # Run LLM prediction with appropriate method based on content_type
            prediction_manager = PredictionManager()
            invoice_prediction_result = prediction_manager.predict_invoice(document, content_type)
            currency_prediction_result = prediction_manager.predict_currency(document, content_type)
            
            # Save result to database
            if invoice_prediction_result.get("success"):
                invoice_data = invoice_prediction_result.get("invoice_data")

                if currency_prediction_result.get("success"):
                    currency_data = currency_prediction_result.get("currency_data")
                    print("***************************************")
                    print(currency_data)
                    print("***************************************")
                    invoice_data = merge_peppol_json(invoice_data, currency_data)

                    # Verify the merge worked (TEMPORARY - development validation)
                    if self._verify_currency_merge(invoice_data, currency_data):
                        self.logger.info("✅ Currency data merged successfully and verified")
                    else:
                        self.logger.warning("⚠️  Currency merge verification failed - check data")

                dict_additional_fields = {}
               
                invoice_data_raw = json.dumps(invoice_data)

                dict_additional_fields["invoice_data_raw"] = invoice_data_raw

                self._update_document_status(EXIT_STATUS, None, dict_additional_fields)
                self._publish_to_topic()
                
            else:
                error_msg = invocie_prediction_result.get("error", "Unknown error")
                self.logger.error(f"Prediction failed: {error_msg}")
                self._update_document_status(ERROR_STATUS)    
            
        except Exception as e:
            self.logger.error(f"LLM prediction failed: {str(e)}")
            
            ERROR_STATUS = LLM_STATUS[ERROR]
            self._update_document_status(ERROR_STATUS)

    def _verify_currency_merge(self, invoice_data: dict, currency_data: dict) -> bool:
        """
        Verify that currency_data has been successfully merged into invoice_data.
        
        Checks that critical currency fields from currency_data exist in invoice_data
        with matching values.
        
        **TEMPORARY**: Used during development to validate merge operation.
        Remove this method once merge is validated in production.
        
        Args:
            invoice_data (dict): The merged invoice data
            currency_data (dict): The original currency prediction data
        
        Returns:
            bool: True if merge verification passed, False otherwise
        """
        try:
            if not currency_data:
                self.logger.warning("⚠️  Currency data is empty, skipping verification")
                return False
            
            if not invoice_data:
                self.logger.error("❌ Invoice data is empty after merge")
                return False
            
            # Extract critical field from currency_data
            currency_code = currency_data.get("meta", {}).get("currency_code", {}).get("v")
            
            if not currency_code:
                self.logger.warning("⚠️  No currency code found in currency_data")
                return False
            
            # Check if it exists in merged invoice_data
            merged_currency_code = invoice_data.get("meta", {}).get("currency_code", {}).get("v")
            
            # Verify they match
            if merged_currency_code == currency_code:
                self.logger.info(f"✅ Currency merge verified: {currency_code}")
                return True
            else:
                self.logger.error(
                    f"❌ Currency merge verification failed: "
                    f"expected '{currency_code}', got '{merged_currency_code}'"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Currency verification error: {str(e)}")
            return False
    

    def _get_content_type(self) -> str:
        """Fetch content_type from document database."""
        sql = "SELECT content_type FROM documents WHERE id = %s"
        results, success = fetch_all(sql, (str(self.document_id),))
        
        if not success or not results:
            raise ValueError(f"Could not fetch content_type for document {self.document_id}")
        
        content_type_json = results[0].get("content_type")        
        # Parse JSON if it's a string
        if isinstance(content_type_json, str):
            try:
                content_data = json.loads(content_type_json)
                content_type = content_data.get("content_classification")
                if not content_type:
                    content_type = "pdf_text"  # Safer fallback than "image"
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ JSON parse failed: {e}. Raw value: {content_type_json!r}")
                content_type = "pdf_text"  # Safer fallback than "image"
        elif isinstance(content_type_json, dict):
            # Already parsed (shouldn't happen but handle it)
            content_type = content_type_json.get("content_classification")
            if not content_type:
                self.logger.warning(f"⚠️  content_classification key missing in dict, using 'pdf_text' fallback")
                content_type = "pdf_text"
        else:
            self.logger.warning(f"⚠️  Unexpected content_type type: {type(content_type_json).__name__}, using 'pdf_text' fallback")
            content_type = "pdf_text"
        
        # Normalize content_type - LLM may return "text" instead of "pdf_text"
        content_type_mapping = {
            "text": "pdf_text",
            "image": "image",
            "pdf_text": "pdf_text",
            "pdf_scanned": "pdf_scanned"
        }
        normalized_type = content_type_mapping.get(content_type, "pdf_text")
        if normalized_type != content_type:
            self.logger.warning(f"⚠️  Normalized content_type: '{content_type}' → '{normalized_type}'")
        
        self.logger.info(f"✅ Final content_type: {normalized_type}")
        return normalized_type