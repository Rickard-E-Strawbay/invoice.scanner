from ic_shared.configuration.config import OPENAI_API_KEY, OPENAI_MODEL_NAME
from ic_shared.logging import ComponentLogger
import openai
from pathlib import Path
import base64
import mimetypes
import json

logger = ComponentLogger("PredictionManager")


class PredictionManager:
    
    def __init__(self):
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self):
        # Load prompt templates from a file or database
        templates = {}
        # Use absolute path relative to this file
        current_dir = Path(__file__).parent
        file_path = current_dir / "predict_invoice.txt"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:    
                prompt = file.read()
                name = file_path.stem  # Get filename without extension
                templates[name] = prompt
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found: {file_path}")

        return templates
    
    def get_prompt(self, template_name: str) -> str:
        """Get prompt template by name."""
        prompt = self.prompt_templates.get(template_name)
        if not prompt:
            raise ValueError(f"Prompt template '{template_name}' not found.")
        
        return prompt
    
    def predict_invoice(self, document: dict, content_type: str) -> dict:
        """
        Predict invoice data from document based on content type.
        
        Args:
            document: Dict with keys 'id', 'filename', 'content' (raw file bytes), 'processed_image_filename'
            content_type: One of 'image', 'pdf_text', 'pdf_scanned'
        
        Returns:
            Dict with 'success' (bool), 'invoice_data' (JSON object or None), 'raw_response' (str)
        """
        try:
            filename = document.get('filename', 'unknown')
            file_content = document.get('content', b'')
            prompt = self.get_prompt("predict_invoice")
            
            logger.info(f"Predicting invoice for {filename} (content_type={content_type})")
            
            # Route based on content type
            if content_type == "image":
                llm_response = self._predict_from_image(file_content, filename, prompt)
            elif content_type == "pdf_text":
                llm_response = self._predict_from_text_pdf(file_content, prompt)
            elif content_type == "pdf_scanned":
                llm_response = self._predict_from_scanned_pdf(document, prompt)
            else:
                raise ValueError(f"Unknown content_type: {content_type}")
            
            # Parse JSON from response
            invoice_data = self._parse_invoice_json(llm_response)
            
            logger.success(f"Invoice prediction completed: {invoice_data is not None}")
            
            return {
                "success": True,
                "invoice_data": invoice_data,
                "raw_response": llm_response
            }
            
        except Exception as e:
            logger.error(f"Invoice prediction failed: {str(e)}")
            return {
                "success": False,
                "invoice_data": None,
                "raw_response": str(e),
                "error": str(e)
            }
    
    def _predict_from_image(self, file_content: bytes, filename: str, prompt: str) -> str:
        """Predict invoice from image using Vision API."""
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "image/jpeg"
        
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_content}"
                        }
                    }
                ]
            }
        ]
        
        logger.info(f"Sending image to Vision API ({len(file_content)} bytes)")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
        )
        
        return response.choices[0].message.content
    
    def _predict_from_text_pdf(self, file_content: bytes, prompt: str) -> str:
        """Predict invoice from text-based PDF using Text API."""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber required for text PDF extraction")
        
        # Extract text from PDF
        import io
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            text_content = ""
            for page in pdf.pages:
                text_content += page.extract_text() or ""
        
        # Truncate to avoid token limits (5000 chars ~= 1250 tokens)
        text_content = text_content[:5000]
        logger.info(f"Extracted {len(text_content)} chars from text PDF")
        
        messages = [
            {
                "role": "user",
                "content": f"{prompt}\n\n--- Document Content ---\n{text_content}"
            }
        ]
        
        logger.info("Sending text PDF to Text API")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
        )
        
        return response.choices[0].message.content
    
    def _predict_from_scanned_pdf(self, document: dict, prompt: str) -> str:
        """Predict invoice from scanned PDF using Vision API on rendered image."""
        # Get rendered image filename from preprocessing
        processed_image_filename = document.get('processed_image_filename')
        if not processed_image_filename:
            raise ValueError("Scanned PDF must have processed_image_filename from preprocessing")
        
        # Fetch rendered image from storage
        from ic_shared.utils.storage_service import get_storage_service
        storage = get_storage_service()
        image_content = storage.get(processed_image_filename)
        
        if image_content is None:
            raise ValueError(f"Could not fetch rendered image: {processed_image_filename}")
        
        logger.info(f"Using rendered image: {processed_image_filename}")
        
        # Use Vision API on rendered image
        base64_content = base64.b64encode(image_content).decode('utf-8')
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_content}"
                        }
                    }
                ]
            }
        ]
        
        logger.info("Sending scanned PDF (rendered image) to Vision API")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
        )
        
        return response.choices[0].message.content
    
    def _parse_invoice_json(self, response_text: str) -> dict:
        """Parse JSON from LLM response with best-effort approach."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            logger.warning("Could not parse JSON from LLM response")
            return None