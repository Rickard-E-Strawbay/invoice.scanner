"""
Shared logging utilities for Invoice Scanner services.

Provides unified ComponentLogger for consistent logging patterns.

Usage:
    from ic_shared.logging import ComponentLogger, get_component_logger
    
    # Method 1: Direct instantiation
    logger = ComponentLogger("OCRWorker")
    
    # Method 2: Factory function
    logger = get_component_logger("OCRWorker")
    
    # Logging with automatic emoji
    logger.info("Processing started")
    logger.error("Failed to process")
    logger.warning("Timeout detected")
    logger.success("Processing complete")
    
    # Custom emoji
    logger.info("Custom message", emoji="🚀")
    
    # Convenience methods for common patterns
    logger.task_start("document processing", "doc_123")
    logger.task_complete("document processing")
    logger.task_failed("document processing", "timeout")
    logger.retry_attempt(2, 3, "connection timeout")
    logger.service_unavailable("http://localhost:5000", "connection refused")
"""

from .logger import (
    ComponentLogger,
    get_component_logger,
    setup_logging,
)

# Auto-initialize logging on import
setup_logging()

__all__ = [
    'ComponentLogger',
    'get_component_logger',
    'setup_logging',
]