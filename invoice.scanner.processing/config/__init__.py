"""
Configuration Module

Central configuration management for the processing service.

MODULES:
    celery_config: Celery task queue configuration
    llm_providers: LLM provider initialization and configuration
    db_utils: Database connection and utility functions
    constants: Global constants and defaults
    validation: Configuration validation and startup checks

USAGE:
    from config.celery_config import CeleryConfig
    from config.db_utils import update_document_status
    from config.llm_providers import LLMProviderFactory
    from config.constants import STATUS_PREPROCESSING, LOG_PREFIX_OCR
    from config.validation import validate_configuration

STARTUP:
    # Validate config at application initialization
    from config.validation import validate_configuration
    results = validate_configuration()
    if not results['all_valid']:
        sys.exit(1)
"""

__all__ = [
    'celery_config',
    'llm_providers',
    'db_utils',
    'constants',
    'validation',
]
