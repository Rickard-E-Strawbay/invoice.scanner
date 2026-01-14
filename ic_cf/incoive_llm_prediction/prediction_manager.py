from ic_shared.configuration.config import OPENAI_API_KEY, OPENAI_MODEL_NAME
from ic_shared.logging import ComponentLogger
from ic_shared.utils.storage_service import get_storage_service
import openai
from pathlib import Path
import base64
import mimetypes
import json
import xml.etree.ElementTree as ET

logger = ComponentLogger("PredictionManager")


class PredictionManager:
    
    def __init__(self):
        self.prompt_templates = self._load_prompt_templates()
        self.xml_schema = self._load_xml_schema()
        self.json_schema = self._load_json_template()
    
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
    
    def _load_xml_schema(self) -> str:
        """Load PEPPOL XML schema with all field metadata via storage service."""
        try:
            storage = get_storage_service()
            # Try to load from storage (works in both local and Cloud Functions)
            xml_content = storage.get_schema("3_0_peppol.xml")
            if xml_content:
                logger.info("Loaded PEPPOL XML schema from storage")
                return xml_content
            else:
                logger.warning("PEPPOL XML schema not found in storage")
                return "<Invoice><!-- Schema not available --></Invoice>"
        except Exception as e:
            logger.error(f"Failed to load XML schema: {e}")
            return "<Invoice><!-- Schema not available --></Invoice>"
    
    def _load_json_template(self) -> dict:
        """Load invoice JSON template from storage service."""
        try:
            storage = get_storage_service()
            # Try to load from storage (works in both local and Cloud Functions)
            json_content = storage.get_schema("inovice_template.json")  # Note: filename has typo
            if json_content:
                logger.info("Loaded invoice JSON template from storage")
                return json.loads(json_content)
            else:
                logger.warning("Invoice JSON template not found in storage")
                return {}
        except Exception as e:
            logger.error(f"Failed to load JSON template: {e}")
            return {}
    
    # def _generate_json_schema(self) -> dict:
    #     """Generate JSON schema from XML with mapid references."""
    #     try:
    #         root = ET.fromstring(self.xml_schema)
    #         schema = {}
            
    #         # Extract all elements with mapid attribute
    #         for elem in root.iter():
    #             mapid = elem.get('mapid')
    #             if mapid:
    #                 display_name = elem.get('DisplayName', mapid)
    #                 description = elem.get('Description', '')
    #                 schema[mapid] = {
    #                     "type": "string",
    #                     "description": description or display_name
    #                 }
            
    #         return schema
    #     except Exception as e:
    #         logger.warning(f"Could not parse XML schema: {str(e)}")
    #         return {}
    
    # def _get_xml_schema_snippet(self) -> str:
    #     """Extract human-readable XML schema for LLM prompt."""
    #     try:
    #         root = ET.fromstring(self.xml_schema)
    #         lines = []
            
    #         # Build readable schema with mapid and DisplayName
    #         for elem in root.iter():
    #             if elem.tag.endswith('}') or elem.tag.startswith('cbc:') or elem.tag.startswith('cac:'):
    #                 mapid = elem.get('mapid')
    #                 display_name = elem.get('DisplayName')
                    
    #                 if mapid:
    #                     tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    #                     lines.append(f"  - mapid=\"{mapid}\": {display_name} ({tag_name})")
            
    #         return "\n".join(lines[:100])  # Limit to 100 items for prompt size
    #     except Exception as e:
    #         logger.warning(f"Could not generate schema snippet: {str(e)}")
    #         return "<!-- Schema not available -->"
    
    # def _get_json_schema_snippet(self) -> str:
    #     """Generate JSON output schema for LLM prompt."""
    #     # Create a sample JSON structure with mapid keys
    #     sample_json = {}
        
    #     # Group by context for readability
    #     contexts = {}
    #     for mapid in self.json_schema:
    #         context = mapid.split('.')[0]
    #         if context not in contexts:
    #             contexts[context] = []
    #         contexts[context].append(mapid)
        
    #     # Build sample JSON
    #     for context in sorted(contexts.keys()):
    #         for mapid in sorted(contexts[context])[:10]:  # Limit items
    #             sample_json[mapid] = ""
        
    #     # Return formatted JSON with comments
    #     return json.dumps(sample_json, indent=2)
    
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

            str_xml_blob  = str(self.xml_schema)
            str_json_blob = json.dumps(self.json_schema, indent=2)
            
            # Replace placeholders with actual schema data
            prompt = prompt.replace("{{xml_structure}}", str_xml_blob)
            prompt = prompt.replace("{{json_blob}}", str_json_blob)
            logger.info(f"Predicting invoice for {filename} (content_type={content_type})")

            print("************************************")
            print(prompt)
            print("************************************")
            
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
        num_pages = 0
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            text_content = ""
            for page in pdf.pages:
                num_pages += 1  
                text_content += page.extract_text() or ""
        
        # Truncate to avoid token limits (5000 chars ~= 1250 tokens)
        text_content_length = len(text_content)
        if text_content_length > 5000:
            logger.warning("Truncateing extracted text from {num_pages} pages from PDF to 5000 characters")
            text_content = text_content[:5000]
        else:
            logger.info(f"Extracted {text_content_length} characters of text from {num_pages} pages from PDF")       
        
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