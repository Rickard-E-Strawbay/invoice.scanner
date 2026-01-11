
from ic_shared.utils.storage_service import init_storage_service
from lib.processing_backend import init_processing_backend
from ic_shared.logging import ComponentLogger
from ic_shared.database.connection import fetch_all
from flask import session
import os
import time

logger = ComponentLogger("API Helpers")


def warm_up():
   # Initialize storage service (LOCAL or GCS based on STORAGE_TYPE env var)
    try:
        storage_service = init_storage_service()
        logger.info(f"Storage service initialized: STORAGE_TYPE={os.environ.get('STORAGE_TYPE', 'local')}")
    except Exception as e:
        logger.error(f"Error initializing storage service: {e}")
        storage_service = None

    # Initialize Cloud SQL Connector early (pre-warm for health checks)
    # This ensures health checks don't timeout waiting for connector initialization
    logger.info("Pre-warming Cloud SQL Connector for health checks...")
    try:
        from ic_shared.database.connection import get_cloud_sql_connector
        connector = get_cloud_sql_connector()
        if connector:
            logger.success("Cloud SQL Connector pre-warmed")
            # Make an actual test connection to warm up the pool
            try:
                results, success = fetch_all("SELECT 1 AS warmup")
                time.sleep(1)  # Small delay to ensure connection is ready
                if success:
                    logger.success("✅ Cloud SQL Connector test query succeeded - health checks ready")
                else:
                    logger.error("❌ Cloud SQL Connector test query failed")
            except Exception as e:
                logger.error(f"❌ Cloud SQL Connector test connection failed: {e}")
        else:
            logger.warning("Cloud SQL Connector not available (running locally?)")
    except Exception as e:
        logger.warning(f"Could not pre-warm Cloud SQL Connector: {e}")

    # Initialize processing backend (LOCAL Celery or CLOUD Functions based on env)
    # NOTE: This is now lazy - no blocking health checks at startup
    logger.info(f"Attempting to initialize processing backend...")
    logger.info(f"PROCESSING_BACKEND env: {os.getenv('PROCESSING_BACKEND', 'not set')}")
    logger.info(f"GCP_PROJECT_ID env: {os.getenv('GCP_PROJECT_ID', 'not set')}")
    try:
        processing_backend = init_processing_backend()
        logger.success(f"Processing backend initialized: {processing_backend.backend_type}")
        logger.info(f"ℹ️  API will start regardless of processing service availability")
    except Exception as e:
        import traceback
        logger.error(f"Error initializing processing backend: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        processing_backend = None

def refresh_user_session(user_id):
    """Fetch fresh user data from database and update session."""
    logger.info(f"Refreshing session for user_id: {user_id}")
    
    sql = """
        SELECT u.id, u.email, u.name, u.role_key, u.company_id,
               u.receive_notifications, u.weekly_summary, u.marketing_opt_in,
               ur.role_name,
               uc.company_name, uc.organization_id, uc.price_plan_key
        FROM users u
        LEFT JOIN user_roles ur ON u.role_key = ur.role_key
        LEFT JOIN users_company uc ON u.company_id = uc.id
        WHERE u.id = %s
    """
    results, success = fetch_all(sql, (user_id,))
    
    if not success or not results:
        logger.warning(f"User not found: {user_id}")
        return None
    
    user = results[0]
    
    # Update session with fresh data
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    session["name"] = user["name"] or user["email"].split("@")[0]
    session["company_id"] = user["company_id"] or None
    session["company_name"] = user["company_name"] or ""
    session["organization_id"] = user["organization_id"] or ""
    session["price_plan_key"] = user["price_plan_key"] or 10
    session["role_key"] = user["role_key"] or 10
    session["role_name"] = user["role_name"] or "User"
    session["receive_notifications"] = user["receive_notifications"] if user["receive_notifications"] is not None else True
    session["weekly_summary"] = user["weekly_summary"] if user["weekly_summary"] is not None else True
    session["marketing_opt_in"] = user["marketing_opt_in"] if user["marketing_opt_in"] is not None else True
    
    logger.debug(f"Session refreshed with data: email={user['email']}, company={user['company_name']}, role={user['role_name']}, price_plan_key={user['price_plan_key']}")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"] or user["email"].split("@")[0],
        "company_id": user["company_id"],
        "company_name": user["company_name"] or "",
        "organization_id": user["organization_id"] or "",
        "price_plan_key": user["price_plan_key"] or 10,
        "role_key": user["role_key"] or 10,
        "role_name": user["role_name"] or "User",
        "receive_notifications": user["receive_notifications"] if user["receive_notifications"] is not None else True,
        "weekly_summary": user["weekly_summary"] if user["weekly_summary"] is not None else True,
        "marketing_opt_in": user["marketing_opt_in"] if user["marketing_opt_in"] is not None else True
    }

def get_cors_origins_regex():
    """Get CORS origins regex pattern for flask-cors"""
    env = os.getenv('FLASK_ENV', 'development')
    
    # Always allow localhost
    origins = ['http://localhost:8080', 'https://localhost:8080']
    
    # Add wildcard pattern for Cloud Run domains
    origins.append('https://.*\\.run\\.app')
    
    if env == 'production':
        # Production environment - also accept specific prod frontend URL as fallback
        origins.append('https://invoice-scanner-frontend-prod.*\\.run\\.app')
    else:
        # Development/Test environment
        origins.append('https://invoice-scanner-frontend-test.*\\.run\\.app')
    
    logger.debug(f"CORS origins regex patterns: {origins}")
    return '|'.join(origins)

def get_peppol_structured_data_fields():
    from ic_shared.utils.peppol_manager import PeppolManager

    peppol_manager = PeppolManager()
    scheme = peppol_manager.get_peppol_scheme()
    return scheme