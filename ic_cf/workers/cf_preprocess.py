from workers.cf_base import cf_base
import json

from ic_shared.configuration.defines import ENTER, EXIT, ERROR, FAIL
from ic_shared.configuration.defines import PREPROCESS_STATUS
from ic_shared.database.connection import execute_sql

from ic_cf.incoive_llm_prediction.document_classifier import DocumentClassifier

class cf_preprocess(cf_base):
    """Cloud Function entry point for preprocessing worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_preprocess")
    
    def execute(self):
        """Execute the preprocessing worker logic."""
        ENTER_STATUS = PREPROCESS_STATUS[ENTER]
        EXIT_STATUS = PREPROCESS_STATUS[EXIT]

        self._update_document_status(ENTER_STATUS)

        try:
            document = self._fetch_document()
            # Add document_id for classifier to use when saving rendered images
            document['id'] = str(self.document_id)
            
            # Classify document using LLM (best-effort approach)
            classifier = DocumentClassifier()
            classification = classifier.classify(document)

            print("*****************************************")
            print("Classification result:", classification) 
            print("*****************************************")
            
            # Update document metadata in DB
            self._update_document_classification(classification)
            
            self._update_document_status(EXIT_STATUS)
            
        except Exception as e:
            self.logger.error(f"Preprocessing failed: {str(e)}")
            raise
        
        self._publish_to_topic()
    
    def _update_document_classification(self, classification: dict):
        """Update document with classification metadata"""
        # Extract processed_image_filename if present (from scanned PDFs)
        processed_image_filename = classification.pop('processed_image_filename', None)
        # Remove 'processed/' prefix if present (keep just the filename)
        if processed_image_filename and processed_image_filename.startswith('processed/'):
            processed_image_filename = processed_image_filename.replace('processed/', '')
        
        sql = """
            UPDATE documents 
            SET content_type = %s, processed_image_filename = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        classification_json = json.dumps(classification)
        results, success = execute_sql(sql, (classification_json, processed_image_filename, str(self.document_id)))
        
        if success:
            self.logger.success(f"Classification stored: {classification['document_classification']}")
            if processed_image_filename:
                self.logger.info(f"Processed image saved: {processed_image_filename}")
        else:
            self.logger.error("Failed to update document classification")

