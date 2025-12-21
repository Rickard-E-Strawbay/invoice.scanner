"""
LLM PROVIDERS CONFIGURATION

This file handles configuration for all LLM providers:
- OpenAI (GPT-4o, GPT-3.5-turbo)
- Google Gemini
- Anthropic Claude

Each provider has its own class to keep configuration separate
and make it easy to switch providers.

USAGE:
    from config.llm_providers import OpenAIProvider, GeminiProvider, AnthropicProvider
    
    provider = OpenAIProvider()
    response = provider.predict(prompt, temperature=0.7)
"""

import os
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class LLMProviderType(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


@dataclass
class LLMProviderConfig:
    """
    Base configuration class for LLM providers.
    Contains common settings for all providers.
    """
    provider_type: LLMProviderType
    api_key: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 300  # 5 minute timeout for API calls
    
    def validate(self) -> bool:
        """Validate that all required fields are set"""
        if not self.api_key:
            raise ValueError(f"{self.provider_type} API key is missing")
        if not self.model_name:
            raise ValueError(f"{self.provider_type} model name is missing")
        return True


class OpenAIConfig(LLMProviderConfig):
    """
    Configuration for OpenAI (GPT-4o, GPT-3.5-turbo)
    
    Environment variables:
    - OPENAI_API_KEY: Your OpenAI API key
    - OPENAI_MODEL: Which model to use (default: gpt-4o)
    - OPENAI_TEMPERATURE: Temperature 0-2 (default: 0.7)
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "")
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        super().__init__(
            provider_type=LLMProviderType.OPENAI,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
        self.validate()


class GeminiConfig(LLMProviderConfig):
    """
    Configuration for Google Gemini
    
    Environment variables:
    - GOOGLE_API_KEY: Your Google Cloud API key
    - GEMINI_MODEL: Which model to use (default: gemini-2.0-flash)
    - GEMINI_TEMPERATURE: Temperature 0-2 (default: 0.7)
    """
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
        
        super().__init__(
            provider_type=LLMProviderType.GEMINI,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
        self.validate()


class AnthropicConfig(LLMProviderConfig):
    """
    Configuration for Anthropic Claude
    
    Environment variables:
    - ANTHROPIC_API_KEY: Your Anthropic API key
    - ANTHROPIC_MODEL: Which model to use (default: claude-3-5-sonnet-20241022)
    - ANTHROPIC_TEMPERATURE: Temperature 0-1 (default: 0.7)
    """
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
        
        super().__init__(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
        self.validate()


class LLMProviderFactory:
    """
    Factory class for creating LLM provider instances.
    
    Use this to easily switch between providers:
    
    EXAMPLE:
        # Automatic from environment variable
        provider = LLMProviderFactory.get_provider()
        
        # Or explicitly choose provider
        provider = LLMProviderFactory.get_provider("openai")
    """
    
    _providers: Dict[str, LLMProviderConfig] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize all providers from environment variables"""
        try:
            cls._providers[LLMProviderType.OPENAI] = OpenAIConfig()
            print("✓ OpenAI provider initialized")
        except ValueError as e:
            print(f"✗ OpenAI provider not configured: {e}")
        
        try:
            cls._providers[LLMProviderType.GEMINI] = GeminiConfig()
            print("✓ Gemini provider initialized")
        except ValueError as e:
            print(f"✗ Gemini provider not configured: {e}")
        
        try:
            cls._providers[LLMProviderType.ANTHROPIC] = AnthropicConfig()
            print("✓ Anthropic provider initialized")
        except ValueError as e:
            print(f"✗ Anthropic provider not configured: {e}")
    
    @classmethod
    def get_provider(cls, provider_type: Optional[str] = None) -> LLMProviderConfig:
        """
        Get LLM provider configuration
        
        Args:
            provider_type: "openai", "gemini", "anthropic" 
                          If None, use default from environment
        
        Returns:
            LLMProviderConfig instance
        
        Raises:
            ValueError: If provider is not configured
        """
        if not cls._providers:
            cls.initialize()
        
        # If no provider specified, use first available
        if provider_type is None:
            if LLMProviderType.OPENAI in cls._providers:
                return cls._providers[LLMProviderType.OPENAI]
            elif LLMProviderType.ANTHROPIC in cls._providers:
                return cls._providers[LLMProviderType.ANTHROPIC]
            elif LLMProviderType.GEMINI in cls._providers:
                return cls._providers[LLMProviderType.GEMINI]
            else:
                raise ValueError("No LLM provider configured")
        
        # Convert string to enum
        if isinstance(provider_type, str):
            provider_type = LLMProviderType(provider_type.lower())
        
        if provider_type not in cls._providers:
            raise ValueError(f"LLM provider not configured: {provider_type}")
        
        return cls._providers[provider_type]
    
    @classmethod
    def list_available_providers(cls) -> list:
        """Lista alla tillgängliga providers"""
        if not cls._providers:
            cls.initialize()
        return list(cls._providers.keys())
