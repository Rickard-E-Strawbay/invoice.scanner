#!/usr/bin/env python3
"""Setup script for local Cloud Functions development.

Runs before the functions-framework starts to:
- Reset PEPPOL cache for fresh schema load
- Verify configuration
"""

import os
import sys

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from ic_shared.logging import ComponentLogger

logger = ComponentLogger("SetupEnvironment")


def reset_peppol_cache():
    """Reset PEPPOL manager cache to force fresh schema load."""
    try:
        # Import after path setup
        from ic_shared.utils.peppol_manager import PeppolManager
        
        # Reset cache
        PeppolManager.reset_cache()
        logger.success("✅ PEPPOL cache reset - will load fresh schema")
        
    except ImportError as e:
        logger.error(f"⚠️  Could not import PeppolManager: {e}")
    except Exception as e:
        logger.error(f"⚠️  Error resetting PEPPOL cache: {e}")


def verify_environment():
    """Verify critical environment variables and paths."""
    required_env = ["ENVIRONMENT", "DATABASE_HOST", "DATABASE_NAME"]
    
    for env_var in required_env:
        if os.getenv(env_var):
            logger.info(f"✓ {env_var} = {os.getenv(env_var)}")
        else:
            logger.warning(f"⚠️  {env_var} not set")


def main():
    """Run setup tasks."""
    logger.info("🔧 Initializing local development environment...")
    print()
    
    verify_environment()
    reset_peppol_cache()
    
    print()
    logger.success("✅ Environment setup complete")


if __name__ == "__main__":
    main()
