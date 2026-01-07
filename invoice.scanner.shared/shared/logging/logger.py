"""
Unified Logging for Invoice Scanner Services

Provides consistent logging patterns across all services with:
- Standardized component prefixes
- Emoji indicators for different log levels
- Structured logging format
- Easy component identification in logs
"""

import logging
from typing import Optional


class ComponentLogger:
    """
    Unified logger for a specific component/service.
    
    Provides consistent formatting with component prefix and emoji indicators.
    
    Usage:
        from shared.logging import ComponentLogger
        
        logger = ComponentLogger("OCRWorker")
        logger.info("Processing started")
        logger.error("Failed to process")
        logger.warning("Timeout detected")
    
    Output:
        [OCRWorker] ℹ️  Processing started
        [OCRWorker] ❌ Failed to process
        [OCRWorker] ⚠️  Timeout detected
    """
    
    # Log level emoji mapping
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🔴',
        'SUCCESS': '✅',
    }
    
    def __init__(self, component_name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize component logger.
        
        Args:
            component_name: Name of component (e.g., "OCRWorker", "API", "Processing")
            logger: Optional existing logger (defaults to root logger)
        """
        self.component_name = component_name
        self.logger = logger or logging.getLogger(component_name)
    
    def _format_message(self, message: str, emoji: Optional[str] = None) -> str:
        """
        Format message with component prefix and emoji.
        
        Args:
            message: Message to format
            emoji: Optional emoji (if not provided, defaults to level emoji)
        
        Returns:
            Formatted message string
        """
        prefix = f"[{self.component_name}]"
        if emoji:
            return f"{prefix} {emoji} {message}"
        return f"{prefix} {message}"
    
    def debug(self, message: str, emoji: Optional[str] = None, **kwargs):
        """Log debug message"""
        if emoji is None:
            emoji = self.EMOJIS['DEBUG']
        self.logger.debug(self._format_message(message, emoji), **kwargs)
    
    def info(self, message: str, emoji: Optional[str] = None, **kwargs):
        """Log info message"""
        if emoji is None:
            emoji = self.EMOJIS['INFO']
        self.logger.info(self._format_message(message, emoji), **kwargs)
    
    def warning(self, message: str, emoji: Optional[str] = None, **kwargs):
        """Log warning message"""
        if emoji is None:
            emoji = self.EMOJIS['WARNING']
        self.logger.warning(self._format_message(message, emoji), **kwargs)
    
    def error(self, message: str, emoji: Optional[str] = None, **kwargs):
        """Log error message"""
        if emoji is None:
            emoji = self.EMOJIS['ERROR']
        self.logger.error(self._format_message(message, emoji), **kwargs)
    
    def critical(self, message: str, emoji: Optional[str] = None, **kwargs):
        """Log critical message"""
        if emoji is None:
            emoji = self.EMOJIS['CRITICAL']
        self.logger.critical(self._format_message(message, emoji), **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message with green checkmark"""
        self.logger.info(self._format_message(message, self.EMOJIS['SUCCESS']), **kwargs)
    
    def task_start(self, task_name: str, details: Optional[str] = None):
        """Log task start"""
        msg = f"Starting {task_name}"
        if details:
            msg += f": {details}"
        self.info(msg, emoji="▶️ ")
    
    def task_complete(self, task_name: str, details: Optional[str] = None):
        """Log task completion"""
        msg = f"Completed {task_name}"
        if details:
            msg += f": {details}"
        self.success(msg)
    
    def task_failed(self, task_name: str, reason: Optional[str] = None):
        """Log task failure"""
        msg = f"Failed {task_name}"
        if reason:
            msg += f": {reason}"
        self.error(msg)
    
    def retry_attempt(self, attempt: int, max_attempts: int, reason: Optional[str] = None):
        """Log retry attempt"""
        msg = f"Retry attempt {attempt}/{max_attempts}"
        if reason:
            msg += f" ({reason})"
        self.warning(msg, emoji="🔄")
    
    def service_unavailable(self, service_url: str, reason: Optional[str] = None):
        """Log service unavailable"""
        msg = f"Service unavailable: {service_url}"
        if reason:
            msg += f" - {reason}"
        self.error(msg)
    
    def service_available(self, service_url: str):
        """Log service available"""
        self.success(f"Service available: {service_url}")
    
    def database_error(self, operation: str, error: Optional[str] = None):
        """Log database error"""
        msg = f"Database error during {operation}"
        if error:
            msg += f": {error}"
        self.error(msg)
    
    def processing_stage(self, stage: str, document_id: str):
        """Log processing stage start"""
        self.info(f"Processing stage '{stage}' for document {document_id}", emoji="📊")
    
    def processing_complete(self, stage: str, document_id: str):
        """Log processing stage completion"""
        self.success(f"Completed stage '{stage}' for document {document_id}")


# Convenience factory function
def get_component_logger(component_name: str) -> ComponentLogger:
    """
    Get a ComponentLogger for a specific component.
    
    Usage:
        logger = get_component_logger("OCRWorker")
        logger.info("Starting OCR")
    """
    return ComponentLogger(component_name)


def setup_logging(environment: str = None, log_level: str = None):
    """
    Configure logging based on environment.
    
    LOCAL: Simple console output with component prefixes
    CLOUD (GCP/Cloud Run): Structured JSON logging
    
    Args:
        environment: 'local', 'test', 'production', or None (auto-detect)
        log_level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' (or None from env var LOGGING_LEVEL)
    """
    import os
    import sys
    import json
    
    # Auto-detect environment if not provided
    if environment is None:
        # Cloud Run sets K_SERVICE env var
        if os.getenv('K_SERVICE'):
            environment = 'cloud'
        elif os.getenv('FLASK_ENV') == 'production':
            environment = 'production'
        else:
            environment = 'local'
    
    # Get log level from parameter, env var, or default
    if log_level is None:
        log_level = os.getenv('LOGGING_LEVEL', 'INFO').upper()
    else:
        log_level = log_level.upper()
    
    # Map string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    if environment == 'local':
        # LOCAL: Simple console with component prefixes
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        # Format already includes component prefix + emoji from ComponentLogger
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
    else:
        # CLOUD/PRODUCTION: JSON structured logging for Google Cloud Logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        
        class JSONFormatter(logging.Formatter):
            """Format logs as JSON for Cloud Logging"""
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'logger': record.name,
                }
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_entry)
        
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


__all__ = [
    'ComponentLogger',
    'get_component_logger',
    'setup_logging',
]