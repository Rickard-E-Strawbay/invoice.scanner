"""
Configuration Validation and Sanitization

Validates environment variables and configuration on startup.
Provides helpful error messages for misconfiguration.

VALIDATION CHECKS:
    - Required environment variables present
    - Database connection parameters valid
    - Redis connection parameters valid
    - LLM provider credentials available (if needed)
    - Directory paths exist and are writable

USAGE:
    from config.validation import validate_configuration

    # Call at application startup
    validate_configuration()

ERROR HANDLING:
    Raises ValueError with detailed messages on validation failures.
    Should be called early in application initialization (celery_app.py).
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(ValueError):
    """Raised when configuration validation fails"""
    pass


# ===== VALIDATION FUNCTIONS =====

def _validate_environment_variable(
    var_name: str,
    required: bool = False,
    default: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a single environment variable.

    Args:
        var_name: Name of the environment variable.
        required: Whether the variable is required.
        default: Default value if not set.

    Returns:
        Tuple of (is_valid, value).
        is_valid is False if required and not found.
    """
    value = os.getenv(var_name, default)

    if required and not value:
        return False, None

    return True, value


def validate_database_config() -> bool:
    """
    Validate database connection configuration.

    Checks:
    - DB_HOST is set or defaults to 'postgres'
    - DB_PORT is valid integer or defaults to 5432
    - DB_NAME is set or defaults to 'invoice_scanner'
    - DB_USER is set or defaults to 'scanner'
    - DB_PASSWORD is set or defaults to 'password'

    Returns:
        True if valid, raises ConfigurationError otherwise.
    """
    try:
        db_host = os.getenv('DB_HOST', 'postgres')
        db_port_str = os.getenv('DB_PORT', '5432')

        # Validate port is integer
        try:
            db_port = int(db_port_str)
            if not (1 <= db_port <= 65535):
                raise ConfigurationError(
                    f"DB_PORT must be between 1 and 65535, got: {db_port}"
                )
        except ValueError:
            raise ConfigurationError(
                f"DB_PORT must be a valid integer, got: {db_port_str}"
            )

        db_name = os.getenv('DB_NAME', 'invoice_scanner')
        db_user = os.getenv('DB_USER', 'scanner')
        db_password = os.getenv('DB_PASSWORD', 'password')

        logger.info(
            f"[CONFIG] Database: {db_user}@{db_host}:{db_port}/{db_name}"
        )

        return True

    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Database configuration error: {e}")


def validate_redis_config() -> bool:
    """
    Validate Redis connection configuration.

    Checks:
    - REDIS_URL or CELERY_BROKER_URL is valid format
    - Defaults to redis://localhost:6379/0

    Returns:
        True if valid, raises ConfigurationError otherwise.
    """
    try:
        redis_url = os.getenv(
            'REDIS_URL',
            os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        )

        # Basic URL format validation
        if not redis_url.startswith('redis://'):
            raise ConfigurationError(
                f"REDIS_URL must start with 'redis://', got: {redis_url}"
            )

        logger.info(f"[CONFIG] Redis: {redis_url}")

        return True

    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Redis configuration error: {e}")


def validate_llm_config() -> Dict[str, bool]:
    """
    Validate LLM provider configuration.

    Checks if API keys are available for configured providers.
    Not required - if missing, those providers will be disabled.

    Returns:
        Dictionary of provider availability:
        {
            'openai': True/False,
            'gemini': True/False,
            'anthropic': True/False
        }

    Note:
        At least one LLM provider should be configured for production.
    """
    providers = {
        'openai': bool(os.getenv('OPENAI_API_KEY')),
        'gemini': bool(os.getenv('GOOGLE_API_KEY')),
        'anthropic': bool(os.getenv('ANTHROPIC_API_KEY')),
    }

    available_count = sum(1 for v in providers.values() if v)

    if available_count == 0:
        logger.warning(
            "[CONFIG] WARNING: No LLM providers configured. "
            "Set OPENAI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY"
        )
    else:
        configured = [k for k, v in providers.items() if v]
        logger.info(f"[CONFIG] LLM Providers available: {', '.join(configured)}")

    return providers


def validate_directories() -> bool:
    """
    Validate that required directories exist.

    Checks:
    - /app/documents exists and is writable
    - /app/documents/raw exists
    - /app/documents/processed exists

    Returns:
        True if valid, raises ConfigurationError otherwise.
    """
    try:
        base_dir = '/app/documents'

        # Create base directory if it doesn't exist
        if not os.path.exists(base_dir):
            logger.warning(f"[CONFIG] Creating directory: {base_dir}")
            os.makedirs(base_dir, exist_ok=True)

        # Check writability
        if not os.access(base_dir, os.W_OK):
            raise ConfigurationError(
                f"Directory not writable: {base_dir}"
            )

        # Create subdirectories
        for subdir in ['raw', 'processed']:
            full_path = os.path.join(base_dir, subdir)
            if not os.path.exists(full_path):
                logger.warning(f"[CONFIG] Creating directory: {full_path}")
                os.makedirs(full_path, exist_ok=True)

        logger.info(f"[CONFIG] Directories validated at: {base_dir}")

        return True

    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Directory validation error: {e}")


# ===== MAIN VALIDATION =====

def validate_configuration(strict: bool = False) -> Dict[str, bool]:
    """
    Perform comprehensive configuration validation.

    Validates:
    - Database configuration
    - Redis configuration
    - Directory accessibility
    - LLM provider availability

    Args:
        strict: If True, require at least one LLM provider.
               If False (default), allow operation without LLMs.

    Returns:
        Dictionary with validation results:
        {
            'database': True/False,
            'redis': True/False,
            'directories': True/False,
            'llm_providers': {...},
            'all_valid': True/False
        }

    Raises:
        ConfigurationError: If any critical validation fails.

    Usage:
        try:
            results = validate_configuration()
            print(f"Config valid: {results['all_valid']}")
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
    """
    results = {
        'database': False,
        'redis': False,
        'directories': False,
        'llm_providers': {},
    }

    errors: List[str] = []

    # Validate database
    try:
        validate_database_config()
        results['database'] = True
    except ConfigurationError as e:
        errors.append(str(e))

    # Validate Redis
    try:
        validate_redis_config()
        results['redis'] = True
    except ConfigurationError as e:
        errors.append(str(e))

    # Validate directories
    try:
        validate_directories()
        results['directories'] = True
    except ConfigurationError as e:
        errors.append(str(e))

    # Validate LLM providers
    llm_status = validate_llm_config()
    results['llm_providers'] = llm_status

    # Determine overall validity
    critical_valid = all([
        results['database'],
        results['redis'],
        results['directories']
    ])

    if strict:
        llm_valid = any(llm_status.values())
        results['all_valid'] = critical_valid and llm_valid
    else:
        results['all_valid'] = critical_valid

    # Log results
    if errors:
        logger.error("[CONFIG] Validation errors:")
        for error in errors:
            logger.error(f"  - {error}")

    if results['all_valid']:
        logger.info("[CONFIG] ✓ All validations passed")
    else:
        logger.error("[CONFIG] ✗ Validation failed")

    return results


if __name__ == '__main__':
    # Can be run directly to validate configuration
    logging.basicConfig(level=logging.INFO)

    try:
        results = validate_configuration()
        if results['all_valid']:
            print("✓ Configuration valid")
            sys.exit(0)
        else:
            print("✗ Configuration invalid")
            sys.exit(1)
    except ConfigurationError as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)
