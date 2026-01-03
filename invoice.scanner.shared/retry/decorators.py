"""
Unified Retry Logic for Invoice Scanner Services

Provides consistent retry behavior across all services via decorators.
Supports exponential backoff, configurable delays, and exception handling.
"""

import time
import logging
from functools import wraps
from typing import Callable, Any, Tuple, Type, Optional

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = False,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap in seconds (default: 30.0)
            backoff_factor: Exponential backoff multiplier (default: 2.0 = exponential)
            jitter: Add random jitter to delays (default: False)
            exceptions: Tuple of exceptions to retry on (default: all)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for this attempt with optional exponential backoff.
        
        Args:
            attempt: Attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * random.random()
        
        return delay


def retry_with_config(
    config: RetryConfig = None,
    **kwargs  # Alternative: pass RetryConfig params directly
) -> Callable:
    """
    Decorator for retrying functions with configurable strategy.
    
    Usage:
        # Option 1: Pass RetryConfig object
        @retry_with_config(config=RetryConfig(max_attempts=5, base_delay=0.5))
        def my_function():
            ...
        
        # Option 2: Pass parameters directly
        @retry_with_config(max_attempts=5, base_delay=0.5)
        def my_function():
            ...
    """
    # Handle both config object and kwargs
    if config is None:
        config = RetryConfig(**kwargs)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **func_kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **func_kwargs)
                
                except config.exceptions as e:
                    last_exception = e
                    is_last_attempt = (attempt == config.max_attempts - 1)
                    
                    if is_last_attempt:
                        logger.error(
                            f"[{func.__name__}] ❌ Failed after {config.max_attempts} attempts",
                            exc_info=True
                        )
                        raise
                    
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"[{func.__name__}] ⚠️  Attempt {attempt+1}/{config.max_attempts} failed: {e}"
                    )
                    logger.info(
                        f"[{func.__name__}] Retrying in {delay:.1f}s... (attempt {attempt+2}/{config.max_attempts})"
                    )
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    return decorator


def retry_simple(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """
    Simple decorator for basic retry needs (no backoff).
    
    Usage:
        @retry_simple(max_attempts=3, delay=1.0)
        def my_function():
            ...
    """
    config = RetryConfig(max_attempts=max_attempts, base_delay=delay, backoff_factor=1.0)
    return retry_with_config(config=config)


def retry_exponential(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Callable:
    """
    Decorator with exponential backoff.
    
    Attempts:    1       2        3        4        5
    Delay:       1s  →   2s   →   4s   →   8s   →   16s
    
    Usage:
        @retry_exponential(max_attempts=5, base_delay=1.0, backoff_factor=2.0)
        def my_function():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_factor=backoff_factor
    )
    return retry_with_config(config=config)


__all__ = [
    'RetryConfig',
    'retry_with_config',
    'retry_simple',
    'retry_exponential',
]
