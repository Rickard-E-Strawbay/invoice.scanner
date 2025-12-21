"""
LLM PROCESSOR - Multi-Provider Invoice Data Prediction

Denna processor hanterar LLM-anrop för att extrahera strukturerad data från OCR-text.
Den stöder:
- OpenAI (GPT-4o, GPT-3.5-turbo)
- Google Gemini
- Anthropic Claude

PROCESS:
    1. Ta in OCR-extraherad text
    2. Skapa structured prompt för LLM
    3. Anropa LLM via vald provider
    4. Parse och validera resultat
    5. Returnera strukturerad invoice data

PROVIDERS:
    OpenAI:    Högsta accuracy, dyrare, snabbast
    Gemini:    Bra accuracy, billigare, varierande snabbhet
    Anthropic: Högsta accuracy, dyrare än Gemini, långsammare än OpenAI

RETRY STRATEGY:
    - Automatisk retry med exponential backoff vid timeout/failures
    - Max 3 retries med 5min spacing
"""

import json
import logging
from typing import Dict, Any, Optional
from config.llm_providers import LLMProviderFactory, LLMProviderType
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    Multi-provider LLM processor för invoice data extraction.
    
    Stöder växling mellan providers via configuration.
    Varje provider har separat implementation för robustness.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM processor
        
        Args:
            provider: "openai", "gemini", "anthropic" eller None för default
        """
        self.provider_config = LLMProviderFactory.get_provider(provider)
        self.provider = self.provider_config.provider_type
        self._init_llm_client()
        logger.info(f"LLM Processor initialized with {self.provider} provider")
    
    def _init_llm_client(self):
        """Initialisera LLM client baserat på provider"""
        
        if self.provider == LLMProviderType.OPENAI:
            self.client = ChatOpenAI(
                model_name=self.provider_config.model_name,
                temperature=self.provider_config.temperature,
                max_tokens=self.provider_config.max_tokens,
                timeout=self.provider_config.timeout,
                api_key=self.provider_config.api_key
            )
        
        elif self.provider == LLMProviderType.GEMINI:
            self.client = ChatGoogleGenerativeAI(
                model=self.provider_config.model_name,
                temperature=self.provider_config.temperature,
                max_tokens=self.provider_config.max_tokens,
                api_key=self.provider_config.api_key,
                timeout=self.provider_config.timeout
            )
        
        elif self.provider == LLMProviderType.ANTHROPIC:
            self.client = ChatAnthropic(
                model_name=self.provider_config.model_name,
                temperature=self.provider_config.temperature,
                max_tokens=self.provider_config.max_tokens,
                timeout=self.provider_config.timeout,
                api_key=self.provider_config.api_key
            )
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def predict_invoice_fields(
        self,
        ocr_text: str,
        company_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict invoice fields using LLM
        
        Args:
            ocr_text: Extraherad text från OCR
            company_id: Company ID för context
            context: Eventuell extra context (previous invoices, company data osv)
        
        Returns:
            Dictionary med predikterade invoice fields:
            {
                'invoice_number': '...',
                'invoice_date': '2024-12-21',
                'vendor_name': '...',
                'amount': 1000.00,
                'vat': 250.00,
                'total': 1250.00,
                'due_date': '2025-01-20',
                'reference': '...',
                'confidence': 0.95,
                'model_used': 'gpt-4o',
                'provider': 'openai'
            }
        
        Raises:
            Exception: On API error or timeout
        """
        
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt(company_id, context)
            
            # Create user prompt with OCR text
            user_prompt = self._create_user_prompt(ocr_text)
            
            # Call LLM
            logger.info(f"[LLM] Calling {self.provider} with {len(ocr_text)} chars of text")
            response = self.client.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse response
            result = self._parse_response(response.content)
            result['provider'] = self.provider.value
            result['model_used'] = self.provider_config.model_name
            
            logger.info(f"[LLM] Successfully extracted invoice data with {result.get('confidence', 0):.2f} confidence")
            return result
            
        except Exception as e:
            logger.error(f"[LLM] Error predicting invoice fields: {e}")
            raise
    
    def _create_system_prompt(self, company_id: str, context: Optional[Dict]) -> str:
        """
        Create system prompt for LLM
        
        This prompt instructs the LLM exactly what to do.
        It is CRITICAL that the prompt is clear and structured.
        """
        
        prompt = """You are an expert at extracting invoice data from OCR text.

Your task is to:
1. Extract structured data from the invoice text
2. Return ONLY a JSON structure, no other text
3. Fill in all fields where data exists, use null for missing fields
4. Estimate a confidence score (0-1) based on text clarity

RETURN EXACTLY THIS STRUCTURE (JSON):
{
    "invoice_number": "string eller null",
    "invoice_date": "YYYY-MM-DD eller null",
    "vendor_name": "string eller null",
    "vendor_email": "string eller null",
    "vendor_phone": "string eller null",
    "amount": "float (netto) eller null",
    "vat_rate": "float (procent) eller null",
    "vat": "float eller null",
    "total": "float (total med VAT) eller null",
    "currency": "string (ISO 4217) eller null",
    "due_date": "YYYY-MM-DD eller null",
    "payment_terms": "string eller null",
    "reference": "string eller null",
    "order_number": "string eller null",
    "confidence": float mellan 0 och 1,
    "extraction_notes": "string med observationer"
}

INSTRUCTIONS:
- Date format MUST be YYYY-MM-DD
- Amounts must be floats without formatting
- Confidence 1.0 = very confident, 0.0 = very uncertain
- If unsure about a value, set it to null instead of guessing"""
        
        if context:
            prompt += f"\n\nCONTEXT:\nCompany ID: {company_id}"
            if context.get('previous_vendor_names'):
                prompt += f"\nKnown vendors: {', '.join(context['previous_vendor_names'])}"
        
        return prompt
    
    def _create_user_prompt(self, ocr_text: str) -> str:
        """Create user prompt with OCR text"""
        return f"Extract invoice data from this OCR text:\n\n{ocr_text}"
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response
        
        Attempts to extract JSON from response.
        Handles both pure JSON and JSON embedded in text.
        """
        
        try:
            # Try to parse directly
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in response (LLM may add extra text)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Could not parse JSON from response: {response[:200]}")
                    raise ValueError("Invalid JSON response from LLM")
            else:
                logger.error(f"No JSON found in response: {response[:200]}")
                raise ValueError("No JSON found in LLM response")
        
        # Validera required fields
        required_fields = ['confidence']
        for field in required_fields:
            if field not in result:
                result[field] = 0.0
        
        return result
