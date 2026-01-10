from flask_smorest import Api, Blueprint
from flask import jsonify
from ic_shared.logging import ComponentLogger
from ic_shared.database.connection import fetch_all
from datetime import datetime
logger = ComponentLogger("APIBase")

blp_base = Blueprint("base", "base", url_prefix="/", description="Base endpoints")

@blp_base.route("/", methods=["GET"])
@blp_base.response(200)
def home():
    """Basic health check route."""
    return jsonify({"message": "Invoice Scanner API is running"})

@blp_base.route("/health", methods=["GET"])
@blp_base.response(200)
def health():
    """Health check endpoint for Cloud Run and load balancers."""
    try:
        # Verify database connection
        logger.info("[HEALTH] Starting health check...")
        results, success = fetch_all("SELECT 1 AS health_check")
        
        if not success:
            logger.error("[HEALTH] ❌ Database connectivity check failed")
            return jsonify({
                "status": "unhealthy",
                "service": "ic_api",
                "database": "disconnected",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        logger.success("[HEALTH] ✅ Health check passed - database connected")
        return jsonify({
            "status": "healthy",
            "service": "ic_api",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"[HEALTH] ❌ Exception during health check: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "unhealthy",
            "service": "ic_api",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503