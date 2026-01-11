"""
Document Classification using LLM
Classifies documents with best-effort approach - returns sensible defaults on failure
"""

import openai
import json
from pathlib import Path
from ic_shared.configuration.config import OPENAI_API_KEY, OPENAI_MODEL_NAME
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("DocumentClassifier")


class DocumentClassifier:
    """Classifies documents using LLM vision/text capabilities"""
    
    CLASSIFICATION_PROMPT = """Analyze this document and classify it.

IMPORTANT: An "invoice" contains:
- An invoice number or reference
- A seller/vendor information
- A buyer/customer information  
- Line items with amounts
- Total amount
- Payment terms or due date
- Tax information (if applicable)

If most of these elements are present, it's an "invoice".
If it's just a receipt, bill, quote, or other document type, classify as "not_invoice".

Return ONLY a JSON object with these fields (no other text):
{
    "content_classification": "image" | "pdf_text" | "pdf_scanned",
    "document_classification": "invoice" | "not_invoice",
    "original_company": "Company Name or 'Unknown'",
    "country": "Country code (SE, US, DE, etc) or 'Unknown'",
    "currency": "Currency code (SEK, USD, EUR, etc) or 'Unknown'",
    "date_format": "Date format (YYYY-MM-DD, DD/MM/YYYY, etc) or 'Unknown'"
}"""
    
    DEFAULT_CLASSIFICATION = {
        "content_classification": "image",
        "document_classification": "not_invoice",
        "original_company": "Unknown",
        "country": "Unknown",
        "currency": "Unknown",
        "date_format": "Unknown"
    }
    
    def classify(self, document: dict) -> dict:
        """
        Classify document with best-effort approach.
        
        Args:
            document: Dict with 'id', 'filename', 'content' (bytes)
        
        Returns:
            Classification dict (with defaults on failure)
            - Adds 'processed_image_filename' for scanned PDFs
        """
        try:
            document_id = document.get('id', 'unknown')
            filename = document.get('filename', 'unknown')
            file_content = document.get('content', b'')
            
            logger.info(f"Classifying document: {filename}")
            
            # Get MIME type
            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            
            # Prepare message for LLM
            if mime_type and mime_type.startswith('image/'):
                classification = self._classify_image(file_content, mime_type)
            else:
                classification = self._classify_text_or_pdf(file_content, filename, document_id)
            
            logger.success(f"Classification: {classification['document_classification']}")
            return classification
            
        except Exception as e:
            logger.warning(f"Classification failed, using defaults: {str(e)}")
            return self.DEFAULT_CLASSIFICATION.copy()
    
    def _classify_image(self, file_content: bytes, mime_type: str) -> dict:
        """Classify image using vision API"""
        import base64
        
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.CLASSIFICATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_content}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.3,  # Low temperature for consistent classification
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    def _classify_text_or_pdf(self, file_content: bytes, filename: str, document_id: str) -> dict:
        """Classify text/PDF using text API or Vision API for scanned PDFs"""
        import io
        
        text_content = None
        content_classification = "unknown"
        
        # Try to extract text from PDF
        if filename.lower().endswith('.pdf'):
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    # Extract text from first 2 pages (fast)
                    text_parts = []
                    for i, page in enumerate(pdf.pages[:2]):
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    
                    text_content = "\n".join(text_parts)[:2000]
                    
                    # If we got substantial text, it's a text PDF
                    if text_content and len(text_content) > 200:
                        content_classification = "pdf_text"
                    else:
                        content_classification = "pdf_scanned"
                        text_content = None  # Will use Vision API
            except Exception as e:
                logger.warning(f"PDF extraction failed: {str(e)}, treating as scanned")
                content_classification = "pdf_scanned"
                text_content = None
        else:
            # Not a PDF, try to decode as text
            try:
                text_content = file_content.decode('utf-8', errors='ignore')[:2000]
                if text_content:
                    content_classification = "pdf_text"  # Treat as text content
            except Exception:
                content_classification = "image"  # Fallback to image classification
                text_content = None
        
        # If we have text content, classify via text API
        if text_content:
            return self._classify_via_text(text_content, content_classification)
        
        # Otherwise, treat as image/scanned and use Vision API
        else:
            logger.info(f"Using Vision API for scanned PDF classification")
            return self._classify_scanned_pdf(file_content, document_id)
    
    def _classify_via_text(self, text_content: str, content_type: str) -> dict:
        """Classify document via extracted text"""
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": f"{self.CLASSIFICATION_PROMPT}\n\nDocument content:\n{text_content}"
                }
            ],
            temperature=0.3,
        )
        
        classification = self._parse_json_response(response.choices[0].message.content)
        # Override content_classification with detected type
        classification["content_classification"] = content_type
        return classification
    
    def _classify_scanned_pdf(self, file_content: bytes, document_id: str) -> dict:
        """Classify scanned PDF by rendering first page and using Vision API"""
        import base64
        import io
        
        try:
            import fitz  # PyMuPDF
            from ic_shared.utils.storage_service import get_storage_service
            
            # Open PDF from bytes
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            # Get first page
            first_page = pdf_document[0]
            
            # Render page to image (2x zoom for better quality)
            pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pix.tobytes("png")
            
            pdf_document.close()
            
            # Save rendered PNG to storage
            processed_filename = f"processed/{document_id}.png"
            storage = get_storage_service()
            import io
            storage.save(processed_filename, io.BytesIO(image_bytes))
            logger.info(f"Rendered scanned PDF saved: {processed_filename}")
            
            # Convert to base64
            base64_content = base64.b64encode(image_bytes).decode('utf-8')
            
            # Classify image using Vision API
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.CLASSIFICATION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_content}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
            )
            
            classification = self._parse_json_response(response.choices[0].message.content)
            # Override content_classification to pdf_scanned
            classification["content_classification"] = "pdf_scanned"
            # Add processed_image_filename for database storage
            classification["processed_image_filename"] = processed_filename
            
            logger.success(f"Scanned PDF classified via Vision API")
            return classification
            
        except Exception as e:
            logger.warning(f"Scanned PDF classification failed: {str(e)}, using defaults")
            classification = self.DEFAULT_CLASSIFICATION.copy()
            classification["content_classification"] = "pdf_scanned"
            return classification
    
    def _parse_json_response(self, response_text: str) -> dict:
        """Parse LLM response as JSON"""
        try:
            # Extract JSON from response (may have surrounding text)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Validate required fields
                required_fields = [
                    "content_classification",
                    "document_classification",
                    "original_company",
                    "country",
                    "currency",
                    "date_format"
                ]
                
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = "Unknown"
                
                return parsed
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
        
        return self.DEFAULT_CLASSIFICATION.copy()
