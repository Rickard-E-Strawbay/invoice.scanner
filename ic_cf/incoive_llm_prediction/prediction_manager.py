from ic_shared.configuration.config import OPENAI_API_KEY, OPENAI_MODEL_NAME
import openai
from pathlib import Path
import base64
import mimetypes

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
        """Generate a prompt for the LLM based on the template and OCR text."""
        prompt = self.prompt_templates.get(template_name)
        if not prompt:
            raise ValueError(f"Prompt template '{template_name}' not found.")
        
        return prompt
    
    def predict_invoice(self, document):
        """
        Predict invoice data from document.
        
        Args:
            document: Dict with keys 'id', 'filename', 'content' (raw file bytes)
        
        Returns:
            LLM response content as string
        """
        filename = document.get('filename', 'unknown')
        file_content = document.get('content', b'')
        
        # Detect file type and prepare for LLM
        _, file_ext = Path(filename).name.rsplit('.', 1) if '.' in filename else ('', '')
        mime_type, _ = mimetypes.guess_type(filename)
        
        # Prepare message with document
        prompt = self.get_prompt("predict_invoice")
        
        # For images: use vision capability with base64
        if mime_type and mime_type.startswith('image/'):
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
        else:
            # For text or other formats: try to decode as text
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
            except Exception:
                text_content = f"[Binary file: {filename}]"
            
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n--- Document Content ---\n{text_content[:5000]}"
                }
            ]

        print("Sending messages to LLM:", messages) 
        print("***********§§***************     ***************")
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        llm_response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
        )
        print("Received response from LLM:", llm_response) 
        print("***********§§***************     ***************")
        
        return llm_response.choices[0].message.content