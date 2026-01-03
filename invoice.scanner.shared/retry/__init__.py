"""
Retry Utility Module

Provides unified retry logic and configurations for all services.
"""

from .decorators import (
    RetryConfig,
    retry_with_config,
    retry_simple,
    retry_exponential,
)

# Predefined configurations for different use cases
import requests

# For Health Checks (fast, linear retry)
HEALTH_CHECK_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=1.0,  # Linear: 1s, 1s, 1s
    exceptions=(
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )
)

# For Service Calls (gradual exponential backoff)
SERVICE_CALL_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,  # Exponential: 1s, 2s, 4s
    exceptions=(
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )
)

# For Database Operations (slower backoff with higher max)
DATABASE_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    backoff_factor=2.0,  # Exponential: 0.5s, 1s, 2s, 4s, 8s
    max_delay=30.0
)

__all__ = [
    'RetryConfig',
    'retry_with_config',
    'retry_simple',
    'retry_exponential',
    'HEALTH_CHECK_CONFIG',
    'SERVICE_CALL_CONFIG',
    'DATABASE_CONFIG',
]
