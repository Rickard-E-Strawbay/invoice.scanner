# ===================
# Imports and Globals
# ===================
# API Version: 2026-01-07-CLEAN (Force rebuild to deploy clean code without cached images)
from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

import secrets
import os
from datetime import datetime
from ic_shared.logging import ComponentLogger
from api.helpers import warm_up
from api.helpers import get_cors_origins_regex
from ic_shared.configuration.config import IS_CLOUD_RUN, ENVIRONMENT

from api.auth import blp_auth
from api.admin import blp_admin
from api.live import blp_live
from api.base import blp_base
from api.documents import blp_documents

logger = ComponentLogger("APIMain")

warm_up()
# refresh_user_session()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.getenv('SECRET_KEY', secrets.token_hex(32)))
app.config['SESSION_COOKIE_HTTPONLY'] = True

if IS_CLOUD_RUN:
    # Cloud Run: HTTPS environment
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    logger.info("Session cookies: SECURE=True, SAMESITE=None (Cloud Run HTTPS)")
else:
    # Local development: HTTP environment
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    logger.info("Session cookies: SECURE=False, SAMESITE=Lax (Local HTTP)")

app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Configure CORS - dynamically based on ENVIRONMENT variable
if IS_CLOUD_RUN:
    # Cloud Run: use environment-specific origins
    if ENVIRONMENT in ["test", "staging"]:
        cors_origins = [
            "https://invoice-scanner-frontend-test-wcpzrlxtjq-ew.a.run.app",
            "https://invoice-scanner-frontend-test.run.app"
        ]
    else:  # prod or other
        cors_origins = [
            "https://invoice-scanner-frontend-prod.run.app",
            "https://invoice-scanner-frontend-prod-wcpzrlxtjq-ew.a.run.app"
        ]
    logger.info(f"CORS configured for '{ENVIRONMENT}' environment: {cors_origins}")
    
    CORS(app, 
         supports_credentials=True,
         origins=cors_origins,
         allow_headers=['Content-Type', 'Authorization', 'Cache-Control', 'Pragma', 'Expires', '*'],
         expose_headers=['Content-Type', 'Authorization', 'Cache-Control'])
else:
    # Development: allow localhost and all origins for testing
    CORS(app,
         supports_credentials=True,
         origins=["http://localhost:8080", "http://localhost:8081", "http://127.0.0.1:8080", "http://127.0.0.1:8081"],
         allow_headers=['Content-Type', 'Authorization', 'Cache-Control', 'Pragma', 'Expires', '*'],
         expose_headers=['Content-Type', 'Authorization', 'Cache-Control'])

# Flask-smorest + Swagger configuration
app.config["API_TITLE"] = "Example API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/"              # Base URL for API
app.config["OPENAPI_JSON_PATH"] = "/openapi.json"   # OpenAPI spec path
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/docs"    # Swagger UI path
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["OPENAPI_SWAGGER_UI_CONFIG"] = {
    "validatorUrl": None,                          # Disable online validator
    "oauth2RedirectUrl": None
}
app.config["API_SPEC_OPTIONS"] = {
    "swagger_ui": True
}

api = Api(app)


# Register blueprints
api.register_blueprint(blp_auth)
api.register_blueprint(blp_base)
api.register_blueprint(blp_live)
api.register_blueprint(blp_admin)
api.register_blueprint(blp_documents)   

# =====================
# App Entrypoint
# =====================
if __name__ == "__main__" or __name__ == "main":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")

    # Cloud Run sets PORT environment variable, default to 8080 for Cloud Run compatibility
    # If PORT env var is set, use it; otherwise use --port arg or default 5000 for local dev
    
    default_port = int(os.environ.get("PORT", 5000))
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args()
    
    # Determine debug mode: True for local dev, False for production
    is_production = os.environ.get("FLASK_ENV") == "production"
    debug_mode = not is_production
    
    logger.info(f"Starting Flask app on {args.host}:{args.port}")
    logger.info(f"PORT env var: {os.environ.get('PORT', 'not set')}")
    logger.info(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}")
    logger.info(f"Debug mode: {debug_mode}")
    app.run(host=args.host, port=args.port, debug=debug_mode)

