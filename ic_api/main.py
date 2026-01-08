# ===================
# Imports and Globals
# ===================
# API Version: 2026-01-07-CLEAN (Force rebuild to deploy clean code without cached images)
from flask import Flask, jsonify, request, session, make_response
from flask_cors import CORS
from flask_smorest import Api, Blueprint
from marshmallow import Schema, fields
import threading
import time
import uuid
import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ic_shared.database.connection import execute_sql
from ic_shared.logging import ComponentLogger
import os
from lib.storage_service import init_storage_service
from lib.processing_backend import init_processing_backend
from lib.email_service import (
    send_company_registration_pending_email,
    send_user_registration_pending_email,
    send_user_approved_email,
    send_company_approved_email,
    send_password_reset_email,
    send_plan_change_email
)
from lib.password_validator import validate_password_strength

logger = ComponentLogger("APIService")

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
            results, success = execute_sql("SELECT 1 AS warmup")
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

# =============
# Database Helper
# =============
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
    results, success = execute_sql(sql, (user_id,))
    
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


# =============
# CORS Configuration
# =============
def get_cors_origins():
    """Get allowed CORS origins based on environment.
    
    - Local dev: Always allow localhost:8080
    - Cloud Run: Allow dynamic FRONTEND_URL + all Cloud Run subdomains
    
    Environment variables:
    - FRONTEND_URL: Specific frontend URL (optional, will be added if set)
    - FLASK_ENV: development, test, production
    - K_SERVICE: Set automatically by Cloud Run (used to detect environment)
    """
    origins = [
        'http://localhost:8080',
        'https://localhost:8080'
    ]
    
    # Get frontend URL from environment variable if explicitly set
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        origins.append(frontend_url)
        logger.info(f"CORS: Added FRONTEND_URL from env: {frontend_url}")
    
    # In Cloud Run, allow all frontend services from the same region
    # This handles the dynamic hash in Cloud Run URLs
    is_cloud_run = os.getenv('K_SERVICE') is not None
    if is_cloud_run:
        # Cloud Run URLs format: name-hash.region.run.app
        # We allow any service from the same domain
        cloud_run_domain = os.getenv('GCP_REGION', 'europe-west1')
        wildcard_origin = f"https://invoice-scanner-frontend-*.{cloud_run_domain}.run.app"
        origins.append(wildcard_origin)
        logger.info(f"CORS: Added wildcard Cloud Run origin: {wildcard_origin}")
    
    logger.debug(f"CORS Allowed origins: {origins}")
    return origins

# =============
# App & Config
# =============
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.getenv('SECRET_KEY', secrets.token_hex(32)))
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Session cookie configuration - environment aware
# Cloud Run uses HTTPS, so we need Secure=True and SameSite=None
# Local development uses HTTP, so we need Secure=False and SameSite=Lax
IS_CLOUD_RUN = os.getenv('K_SERVICE') is not None
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

# CORS configuration using flask_cors
CORS(app, supports_credentials=True, origins=get_cors_origins())

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
blp_live = Blueprint("live", "live", url_prefix="/live", description="Live endpoints")
blp_auth = Blueprint("auth", "auth", url_prefix="/auth", description="Authentication endpoints")

@app.route("/")
def home():
    """Basic health check route."""
    return jsonify({"message": "Invoice Scanner API is running"})

@app.route("/health")
def health():
    """Health check endpoint for Cloud Run and load balancers."""
    try:
        # Verify database connection
        logger.info("[HEALTH] Starting health check...")
        results, success = execute_sql("SELECT 1 AS health_check")
        
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





    try:
        # Minimal health check - just verify the app is responding
        # Don't require DB to be up (DB connections are lazy-loaded on demand)
        return jsonify({
            "status": "healthy",
            "service": "ic_api",
            "version": "1.0"
        }), 200
    except Exception as e:
        logger.info(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@blp_live.route("/x")
def x():
    return jsonify({"status": "done"})

# ======================
# Authentication Routes
# ======================

@blp_auth.route("/request-password-reset", methods=["POST"])
def request_password_reset():
    """Request password reset email (public endpoint - no auth required)."""
    try:
        data = request.get_json()
        email = data.get("email", "").lower().strip()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Find user by email
        sql = "SELECT id, name, email FROM users WHERE email = %s"
        results, success = execute_sql(sql, (email,))
        
        if not success or not results:
            # For security, don't reveal if email exists
            return jsonify({
                "message": "If an account exists for this email, a password reset link has been sent"
            }), 200
        
        user = results[0]
        
        # Generate reset token
        import secrets
        from datetime import datetime, timedelta
        reset_token = secrets.token_urlsafe(32)
        reset_token_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Store reset token in database
        sql = "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s"
        _, success = execute_sql(sql, (reset_token, reset_token_expires, user["id"]))
        
        if not success:
            return jsonify({"error": "Failed to store reset token"}), 500
        
        reset_link = f"http://localhost:3000/reset-password/{reset_token}"
        
        # Send password reset email
        send_password_reset_email(
            to_email=user["email"],
            name=user["name"],
            reset_link=reset_link
        )
        
        logger.info(f"Password reset email sent to {user['email']}")
        
        return jsonify({
            "message": "If an account exists for this email, a password reset link has been sent"
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to process request"}), 500

@blp_auth.route("/signup", methods=["POST"])
def signup():
    """Register a new user and create company."""
    data = request.get_json()
    logger.info(f"Request received: {data}")
    
    if not data or not data.get("email") or not data.get("password"):
        logger.info(f"Missing email or password")
        return jsonify({"error": "Email and password required"}), 400
    
    if not data.get("company_name") or not data.get("organization_id"):
        logger.info(f"Missing company_name or organization_id")
        return jsonify({"error": "Company name and organization ID required"}), 400
    
    email = data.get("email")
    password = data.get("password")
    
    # Validate password strength
    password_validation = validate_password_strength(password)
    if not password_validation["is_valid"]:
        error_message = password_validation["errors"][0] if password_validation["errors"] else "Password does not meet requirements"
        logger.info(f"Password validation failed: {error_message}")
        return jsonify({"error": error_message}), 400
    
    name = data.get("name", email.split("@")[0])  # Default to email prefix if name not provided
    company_name = data.get("company_name")
    organization_id = data.get("organization_id")
    terms_version = data.get("terms_version", "1.0")
    terms_accepted = data.get("terms_accepted", False)
    
    try:
        # Check if user exists
        sql = "SELECT id FROM users WHERE email = %s"
        results, success = execute_sql(sql, (email,))
        if success and results:
            return jsonify({"error": "User already exists"}), 409
        
        # Check if organization exists in users_company
        sql = "SELECT id, company_name, company_email, company_enabled FROM users_company WHERE organization_id = %s"
        results, success = execute_sql(sql, (organization_id,))
        
        if success and results:
            company = results[0]
            company_id = company["id"]
            is_new_company = False
            company_name_final = company["company_name"]
            company_enabled = company["company_enabled"]
        else:
            # Create new company - disabled by default, waiting for admin approval
            company_id = str(uuid.uuid4())
            sql = "INSERT INTO users_company (id, company_name, company_email, organization_id, company_enabled) VALUES (%s, %s, %s, %s, %s)"
            _, success = execute_sql(sql, (company_id, company_name, email, organization_id, False))
            if not success:
                return jsonify({"error": "Failed to create company"}), 500
            logger.info(f"New company created (disabled): {company_id} - {company_name}")
            is_new_company = True
            company_name_final = company_name
            company_enabled = False
        
        # Check if this is the first user for the company
        sql = "SELECT COUNT(*) as user_count FROM users WHERE company_id = %s"
        results, success = execute_sql(sql, (company_id,))
        is_first_user = success and results and results[0]["user_count"] == 0
        
        # Set role_key to Company Admin (50) if first user, else User (10)
        role_key = 50 if is_first_user else 10
        
        # Create new user (always, regardless of company_enabled status)
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        sql = "INSERT INTO users (id, email, password_hash, name, company_id, role_key, terms_accepted, terms_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        _, success = execute_sql(sql, (user_id, email, password_hash, name, company_id, role_key, terms_accepted, terms_version))
        
        if not success:
            return jsonify({"error": "Failed to create user"}), 500
        
        logger.info(f"User created successfully: {user_id} - {email}")
        
        # If it's a new company, send pending approval email
        if is_new_company:
            send_company_registration_pending_email(
                to_email=email,
                name=name,
                company_name=company_name_final,
                organization_id=organization_id
            )
            return jsonify({
                "message": "Company created successfully",
                "is_new_company": True,
                "company_name": company_name_final,
                "email": email
            }), 201
        
        # If company is not enabled, show pending approval message
        if not company_enabled:
            logger.info(f"User added to disabled company: {company_id}")
            # Get the company admin info for the email
            sql = """
                SELECT u.name, u.email 
                FROM users u 
                WHERE u.company_id = %s AND u.role_key = 50 
                LIMIT 1
            """
            results, success = execute_sql(sql, (company_id,))
            admin_info = results[0] if success and results else None
            
            admin_name = admin_info["name"] if admin_info else "Company Administrator"
            admin_email = admin_info["email"] if admin_info else email
            
            send_user_registration_pending_email(
                to_email=email,
                name=name,
                company_name=company_name_final,
                admin_name=admin_name,
                admin_email=admin_email
            )
            
            return jsonify({
                "message": "User created successfully",
                "is_new_company": False,
                "company_enabled": False,
                "company_name": company_name_final,
                "email": email,
                "error_message": "Ditt företag avväntar godkännande. Så fort Strawbay godkänt kommer du att få en notifiering via epost."
            }), 201
        
        # If joining enabled company, send pending review email
        # Get the company admin info for the email
        sql = """
            SELECT u.name, u.email 
            FROM users u 
            WHERE u.company_id = %s AND u.role_key = 50 
            LIMIT 1
        """
        results, success = execute_sql(sql, (company_id,))
        admin_info = results[0] if success and results else None
        
        if admin_info:
            send_user_registration_pending_email(
                to_email=email,
                name=name,
                company_name=company_name_final,
                admin_name=admin_info["name"],
                admin_email=admin_info["email"]
            )
        
        # Refresh user session with fresh data from database
        user_data = refresh_user_session(user_id)
        if not user_data:
            return jsonify({"error": "User created but failed to load user data"}), 500
        
        return jsonify({
            "message": "User created successfully",
            "user": user_data,
            "is_new_company": False
        }), 201
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Signup failed"}), 500

@blp_auth.route("/login", methods=["POST"])
def login():
    """Authenticate user and create session."""
    data = request.get_json()
    logger.info(f"Request received for email: {data.get('email') if data else 'N/A'}")
    
    if not data or not data.get("email") or not data.get("password"):
        logger.info(f"Missing email or password")
        return jsonify({"error": "Email and password required"}), 400
    
    email = data.get("email")
    password = data.get("password")
    
    # Get user and check if company is enabled
    sql = """
        SELECT u.id, u.email, u.password_hash, u.company_id, u.user_enabled,
               uc.company_enabled, uc.company_name
        FROM users u
        LEFT JOIN users_company uc ON u.company_id = uc.id
        WHERE u.email = %s
    """
    results, success = execute_sql(sql, (email,))
    
    if not success or not results:
        logger.info(f"Invalid credentials for email: {email}")
        return jsonify({"error": "Invalid credentials"}), 401
    
    user = results[0]
    
    if not check_password_hash(user["password_hash"], password):
        logger.info(f"Invalid credentials for email: {email}")
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Check if user is enabled
    if not user["user_enabled"]:
        logger.info(f"User account not enabled for user: {email}")
        return jsonify({
            "error": "Account not enabled",
            "message": "Ditt konto är inte aktiverat. Kontakta administratör för att få tillgång."
        }), 403
    
    # Check if company is enabled
    if user["company_id"] and not user["company_enabled"]:
        logger.info(f"Company not enabled for user: {email}")
        return jsonify({
            "error": "Company not enabled",
            "message": "Ditt företag avväntar godkännande. Så fort Strawbay godkänt kommer du att få en notifiering via epost."
        }), 403
    
    user_id = user["id"]
    logger.info(f"Password verified for user: {user_id}")
    
    # Refresh user session with fresh data from database
    user_data = refresh_user_session(user_id)
    if not user_data:
        return jsonify({"error": "Failed to load user data"}), 500
    
    logger.info(f"Login successful for: {email}")
    return jsonify({
        "message": "Logged in successfully",
        "user": user_data
    }), 200

@blp_auth.route("/logout", methods=["POST"])
def logout():
    """End user session."""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@blp_auth.route("/me", methods=["GET"])
def get_current_user():
    """Get current logged-in user info."""
    logger.info(f"========== REQUEST RECEIVED ==========")
    logger.info(f"Session content: {dict(session)}")
    logger.info(f"Session keys: {list(session.keys())}")
    logger.info(f"Cookies received: {request.cookies}")
    
    if "user_id" not in session:
        logger.info(f"❌ NOT AUTHENTICATED - no user_id in session")
        logger.info(f"========== END REQUEST ==========")
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    logger.info(f"✅ Found user_id in session: {user_id}")
    logger.info(f"Calling refresh_user_session()...")
    
    # Refresh and fetch fresh user data from database
    user_data = refresh_user_session(user_id)
    if not user_data:
        logger.info(f"❌ refresh_user_session returned None")
        logger.info(f"========== END REQUEST ==========")
        return jsonify({"error": "Failed to fetch user information"}), 500
    
    logger.info(f"✅ Returning user data: {user_data}")
    logger.info(f"========== END REQUEST ==========")
    return jsonify(user_data), 200


@blp_auth.route("/profile", methods=["PUT"])
def update_profile():
    """Update current user's profile (name and notification preferences)."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract fields
    name = data.get("name")
    receive_notifications = data.get("receive_notifications")
    weekly_summary = data.get("weekly_summary")
    marketing_opt_in = data.get("marketing_opt_in")
    
    # At least name is required
    if not name or not name.strip():
        return jsonify({"error": "Name is required"}), 400
    
    try:
        # Build update query dynamically
        update_fields = ["name = %s"]
        update_values = [name.strip()]
        
        if receive_notifications is not None:
            update_fields.append("receive_notifications = %s")
            update_values.append(receive_notifications)
        
        if weekly_summary is not None:
            update_fields.append("weekly_summary = %s")
            update_values.append(weekly_summary)
        
        if marketing_opt_in is not None:
            update_fields.append("marketing_opt_in = %s")
            update_values.append(marketing_opt_in)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, email, name, role_key, company_id, receive_notifications, weekly_summary, marketing_opt_in
        """
        
        results, success = execute_sql(query, tuple(update_values))
        
        if not success or not results:
            return jsonify({"error": "User not found"}), 404
        
        updated_user = results[0]
        
        # Update session with new name
        session["name"] = updated_user["name"]
        
        logger.info(f"User {user_id} updated profile: name={updated_user['name']}")
        
        return jsonify({
            "message": "Profile updated successfully",
            "user": {
                "id": str(updated_user["id"]),
                "email": updated_user["email"],
                "name": updated_user["name"],
                "role_key": updated_user["role_key"],
                "receive_notifications": updated_user["receive_notifications"],
                "weekly_summary": updated_user["weekly_summary"],
                "marketing_opt_in": updated_user["marketing_opt_in"]
            }
        }), 200

    except Exception as e:
        logger.info(f"Error updating profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 500


@blp_auth.route("/change-password", methods=["PUT"])
def change_password():
    """Change current user's password."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    # Validate inputs
    if not old_password:
        return jsonify({"error": "Current password is required"}), 400
    
    if not new_password:
        return jsonify({"error": "New password is required"}), 400
    
    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400
    
    try:
        # Get current user's password hash
        sql = "SELECT password_hash FROM users WHERE id = %s"
        results, success = execute_sql(sql, (user_id,))
        
        if not success or not results:
            return jsonify({"error": "User not found"}), 404
        
        user = results[0]
        
        # Verify old password
        if not check_password_hash(user["password_hash"], old_password):
            logger.info(f"User {user_id} provided incorrect old password")
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Hash new password
        new_password_hash = generate_password_hash(new_password)
        
        # Update password
        sql = """
            UPDATE users
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, email
        """
        results, success = execute_sql(sql, (new_password_hash, user_id))
        
        if not success or not results:
            return jsonify({"error": "Failed to update password"}), 500
        
        updated_user = results[0]
        
        logger.info(f"User {user_id} ({updated_user['email']}) changed password")
        
        return jsonify({
            "message": "Password changed successfully",
            "user": {
                "id": str(updated_user["id"]),
                "email": updated_user["email"]
            }
        }), 200

    except Exception as e:
        logger.info(f"Error changing password: {e}")
        return jsonify({"error": "Failed to change password"}), 500


@blp_auth.route("/search-companies", methods=["GET"])
def search_companies():
    """Search for companies by name in users_company table."""
    query = request.args.get("q", "").strip()
    logger.info(f"Query received: '{query}'")
    
    if not query or len(query) < 2:
        logger.info(f"Query too short or empty, returning empty results")
        return jsonify({"companies": []}), 200
    
    try:
        # Search for companies matching the query (case-insensitive, partial match)
        logger.info(f"Executing database query for: {query}")
        sql = """
            SELECT DISTINCT company_name, organization_id
            FROM users_company
            WHERE LOWER(company_name) LIKE LOWER(%s)
            ORDER BY company_name
            LIMIT 10
        """
        results, success = execute_sql(sql, (f"%{query}%",))
        
        if not success:
            logger.error(f"Database error")
            return jsonify({"error": "Search failed"}), 500
        
        companies = results if results else []
        logger.info(f"Found {len(companies)} companies: {companies}")
        return jsonify({"companies": [dict(company) for company in companies]}), 200
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return jsonify({"error": "Search failed"}), 500


@blp_auth.route("/company-info", methods=["GET"])
def get_company_info():
    """Get company information for the current user."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    
    try:
        # Get user's company information
        sql = """
            SELECT uc.id, uc.company_name, uc.organization_id, uc.company_email
            FROM users u
            LEFT JOIN users_company uc ON u.company_id = uc.id
            WHERE u.id = %s
        """
        results, success = execute_sql(sql, (user_id,))
        
        if not success or not results:
            return jsonify({"error": "Company information not found"}), 404
        
        company = results[0]
        
        return jsonify({
            "id": company["id"],
            "company_name": company["company_name"],
            "organization_id": company["organization_id"],
            "company_email": company["company_email"]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching company info: {e}")
        return jsonify({"error": "Failed to fetch company information"}), 500


@blp_auth.route("/admin/companies", methods=["GET"])
def get_all_companies():
    """Get all companies from users_company table. Admin only."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Check if user is admin (role_key 1000 or 50)
    role_key = session.get("role_key", 10)
    if role_key not in [1000, 50]:
        logger.info(f"Unauthorized - user role_key: {role_key}")
        return jsonify({"error": "Unauthorized"}), 403
    
    logger.info(f"Fetching all companies for user with role_key: {role_key}")
    
    try:
        sql = """
            SELECT id, company_name, company_email, organization_id, 
                   company_enabled, price_plan_key, created_at, updated_at
            FROM users_company
            ORDER BY company_name ASC
        """
        results, success = execute_sql(sql, ())
        
        if not success:
            logger.info(f"Database error")
            return jsonify({"error": "Failed to fetch companies"}), 500
        
        companies = results if results else []
        logger.info(f"Found {len(companies)} companies")
        # Convert PG8000DictRow objects to dictionaries for JSON serialization
        companies_list = [dict(company) for company in companies]
        return jsonify({"companies": companies_list}), 200
    except Exception as e:
        logger.info(f"Error fetching companies: {e}")
        return jsonify({"error": "Failed to fetch companies"}), 500


@blp_auth.route("/admin/companies", methods=["POST"])
def add_company():
    """Add a new company. Strawbay Admin only."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Check if user is Strawbay Admin (role_key 1000)
    role_key = session.get("role_key", 10)
    if role_key != 1000:
        logger.info(f"Unauthorized - user role_key: {role_key}")
        return jsonify({"error": "Only Strawbay Admins can add companies"}), 403
    
    data = request.get_json()
    logger.info(f"Request received: {data}")
    
    # Validate input
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    company_name = data.get("company_name", "").strip()
    company_email = data.get("company_email", "").strip()
    organization_id = data.get("organization_id", "").strip()
    company_enabled = data.get("company_enabled", False)
    
    if not isinstance(company_enabled, bool):
        company_enabled = False
    
    if not company_name:
        return jsonify({"error": "Company name is required"}), 400
    if not company_email:
        return jsonify({"error": "Company email is required"}), 400
    if not organization_id:
        return jsonify({"error": "Organization ID is required"}), 400
    
    try:
        # Check for duplicate organization_id
        sql = "SELECT id FROM users_company WHERE organization_id = %s"
        results, success = execute_sql(sql, (organization_id,))
        
        if success and results:
            logger.info(f"Organization ID already exists: {organization_id}")
            return jsonify({"error": "Organization ID already exists"}), 409
        
        # Insert new company
        sql = """
            INSERT INTO users_company (company_name, company_email, organization_id, company_enabled, price_plan_key)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, company_name, company_email, organization_id, company_enabled, price_plan_key, created_at
        """
        results, success = execute_sql(sql, (company_name, company_email, organization_id, company_enabled, 10))
        
        if not success or not results:
            logger.info(f"Failed to insert company")
            return jsonify({"error": "Failed to add company"}), 500
        
        new_company = results[0]
        
        logger.info(f"Company added successfully: {new_company['company_name']}")
        return jsonify({
            "message": "Company added successfully",
            "company": {
                "id": new_company["id"],
                "company_name": new_company["company_name"],
                "company_email": new_company["company_email"],
                "organization_id": new_company["organization_id"],
                "company_enabled": new_company["company_enabled"],
                "price_plan_key": new_company["price_plan_key"],
                "created_at": new_company["created_at"]
            }
        }), 201
    except Exception as e:
        logger.info(f"Error adding company: {e}")
        return jsonify({"error": "Failed to add company"}), 500


@blp_auth.route("/admin/companies/<company_id>", methods=["PUT"])
def update_company_status(company_id):
    """Update company details. Only Strawbay Admin can do this."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    role_key = session.get("role_key")
    
    # Check if user is Strawbay Admin (role_key == 1000)
    if role_key != 1000:
        logger.info(f"User {user_id} tried to update company but is not admin (role_key: {role_key})")
        return jsonify({"error": "Only Strawbay Admins can update company"}), 403
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract fields - only company_enabled is required, others are optional
    company_enabled = data.get("company_enabled")
    company_name = data.get("company_name")
    company_email = data.get("company_email")
    organization_id = data.get("organization_id")
    price_plan_key = data.get("price_plan_key")
    
    # If company_enabled is provided, validate it's a boolean
    if company_enabled is not None and not isinstance(company_enabled, bool):
        return jsonify({"error": "company_enabled must be a boolean"}), 400
    
    # Validate price_plan_key if provided
    if price_plan_key is not None:
        try:
            price_plan_key = int(price_plan_key)
        except (ValueError, TypeError):
            return jsonify({"error": "price_plan_key must be a number"}), 400
    
    # Build update query dynamically based on provided fields
    update_fields = []
    update_values = []
    
    if company_name is not None:
        if not company_name.strip():
            return jsonify({"error": "Company name cannot be empty"}), 400
        update_fields.append("company_name = %s")
        update_values.append(company_name)
    
    if company_email is not None:
        if not company_email.strip():
            return jsonify({"error": "Company email cannot be empty"}), 400
        update_fields.append("company_email = %s")
        update_values.append(company_email)
    
    if organization_id is not None:
        if not organization_id.strip():
            return jsonify({"error": "Organization ID cannot be empty"}), 400
        update_fields.append("organization_id = %s")
        update_values.append(organization_id)
    
    if company_enabled is not None:
        update_fields.append("company_enabled = %s")
        update_values.append(company_enabled)
    
    if price_plan_key is not None:
        update_fields.append("price_plan_key = %s")
        update_values.append(price_plan_key)
    
    if not update_fields:
        return jsonify({"error": "No fields to update"}), 400
    
    try:
        # Check if company exists first and get current status
        sql = "SELECT id, company_enabled FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success or not results:
            logger.info(f"Company {company_id} not found")
            return jsonify({"error": "Company not found"}), 404
        
        company_check = results[0]
        was_enabled = company_check["company_enabled"]
        
        # Update company
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(company_id)
        
        query = f"""
            UPDATE users_company
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, company_name, company_email, organization_id, company_enabled, price_plan_key, created_at, updated_at
        """
        
        results, success = execute_sql(query, tuple(update_values))
        
        if not success or not results:
            logger.info(f"Failed to update company")
            return jsonify({"error": "Failed to update company"}), 500
        
        updated_company = results[0]
        
        # If company was just enabled, send approval email to all company admins
        if company_enabled is True and not was_enabled:
            logger.info(f"Company {company_id} was approved, sending emails to admins")
            # Get all Company Admins for this company
            sql = """
                SELECT u.email, u.name 
                FROM users u 
                WHERE u.company_id = %s AND u.role_key = 50
            """
            results, success = execute_sql(sql, (company_id,))
            admins = results if success and results else []
            
            # Send email to each admin
            for admin in admins:
                send_company_approved_email(
                    to_email=admin["email"],
                    name=admin["name"],
                    company_name=updated_company["company_name"],
                    organization_id=updated_company["organization_id"]
                )
                logger.info(f"Approval email sent to admin: {admin['email']}")
        
        logger.info(f"Company {company_id} updated by user {user_id}")
        
        return jsonify({
            "company": {
                "id": str(updated_company["id"]),
                "company_name": updated_company["company_name"],
                "company_email": updated_company["company_email"],
                "organization_id": updated_company["organization_id"],
                "company_enabled": updated_company["company_enabled"],
                "created_at": updated_company["created_at"],
                "updated_at": updated_company["updated_at"]
            }
        }), 200
    except Exception as e:
        logger.info(f"Error updating company: {e}")
        return jsonify({"error": "Failed to update company"}), 500


# =====================
# User Management Endpoints (Admin Only)
# =====================

@blp_auth.route("/admin/users", methods=["GET"])
def get_users():
    """Get users. Strawbay Admin sees all, Company Admin sees only their company's users."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    role_key = session.get("role_key")
    user_id = session.get("user_id")
    company_id = session.get("company_id")
    
    # Check if user is Strawbay Admin (role_key == 1000) or Company Admin (role_key == 50)
    if role_key not in [1000, 50]:
        return jsonify({"error": "Only Admins can view users"}), 403
    
    try:
        # If Company Admin, only fetch their company's users
        if role_key == 50:
            if not company_id:
                return jsonify({"error": "Company Admin must have a company_id"}), 400
            
            sql = """
                SELECT 
                    u.id, 
                    u.email, 
                    u.name, 
                    u.role_key,
                    u.user_enabled,
                    u.company_id,
                    u.created_at,
                    u.updated_at,
                    uc.company_name,
                    uc.company_enabled
                FROM users u
                LEFT JOIN users_company uc ON u.company_id = uc.id
                WHERE u.company_id = %s
                ORDER BY u.created_at DESC
            """
            results, success = execute_sql(sql, (company_id,))
        else:
            # Strawbay Admin sees all users
            sql = """
                SELECT 
                    u.id, 
                    u.email, 
                    u.name, 
                    u.role_key,
                    u.user_enabled,
                    u.company_id,
                    u.created_at,
                    u.updated_at,
                    uc.company_name,
                    uc.company_enabled
                FROM users u
                LEFT JOIN users_company uc ON u.company_id = uc.id
                ORDER BY u.created_at DESC
            """
            results, success = execute_sql(sql, ())
        
        if not success:
            return jsonify({"error": "Failed to fetch users"}), 500
        
        users = results if results else []
        
        return jsonify({
            "users": [
                {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "name": user["name"],
                    "role_key": user["role_key"],
                    "user_enabled": user["user_enabled"],
                    "company_id": user["company_id"],
                    "company_name": user["company_name"],
                    "company_enabled": user["company_enabled"] if user["company_enabled"] is not None else True,
                    "created_at": user["created_at"],
                    "updated_at": user["updated_at"]
                }
                for user in users
            ]
        }), 200
    except Exception as e:
        logger.info(f"Error fetching users: {e}")
        return jsonify({"error": "Failed to fetch users"}), 500


@blp_auth.route("/admin/users", methods=["POST"])
def create_user():
    """Create a new user. Only Strawbay Admin can do this."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    role_key = session.get("role_key")
    
    # Check if user is Strawbay Admin (role_key == 1000)
    if role_key != 1000:
        return jsonify({"error": "Only Strawbay Admins can create users"}), 403
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    email = data.get("email", "").strip()
    name = data.get("name", "").strip()
    role_key_new = data.get("role_key", 10)
    user_enabled = data.get("user_enabled", False)
    company_id = data.get("company_id")
    
    # Validate required fields
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not company_id:
        return jsonify({"error": "Company ID is required"}), 400
    
    # Validate email format
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format"}), 400
    
    try:
        # Check if company exists
        sql = "SELECT id FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success or not results:
            return jsonify({"error": "Company not found"}), 404
        
        # Create user with default password
        default_password_hash = "scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139"
        
        sql = """
            INSERT INTO users (email, password_hash, name, company_id, role_key, user_enabled, terms_accepted, terms_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, name, role_key, user_enabled, created_at, updated_at
        """
        results, success = execute_sql(sql, (email, default_password_hash, name, company_id, role_key_new, user_enabled, True, "1.0"))
        
        if not success or not results:
            if "duplicate" in str(success).lower():
                return jsonify({"error": "Email already exists"}), 409
            return jsonify({"error": "Failed to create user"}), 500
        
        new_user = results[0]
        
        # Get company_enabled status
        sql = "SELECT company_enabled FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        company = results[0] if success and results else None
        company_enabled = company["company_enabled"] if company else False
        
        logger.info(f"User {email} created by admin {user_id}")
        
        return jsonify({
            "user": {
                "id": str(new_user["id"]),
                "email": new_user["email"],
                "name": new_user["name"],
                "role_key": new_user["role_key"],
                "user_enabled": new_user["user_enabled"],
                "company_enabled": company_enabled,
                "created_at": new_user["created_at"],
                "updated_at": new_user["updated_at"]
            }
        }), 201
    except Exception as e:
        logger.info(f"Error creating user: {e}")
        if "duplicate key" in str(e).lower():
            return jsonify({"error": "Email already exists"}), 409
        return jsonify({"error": "Failed to create user"}), 500


@blp_auth.route("/admin/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user details. Strawbay Admin can update any user. Company Admin can update users in their company."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    admin_id = session.get("user_id")
    admin_role_key = session.get("role_key")
    admin_company_id = session.get("company_id")
    
    # Check if user is Strawbay Admin (role_key == 1000) or Company Admin (role_key == 50)
    if admin_role_key not in [1000, 50]:
        return jsonify({"error": "Only Admins can update users"}), 403
    
    # If Company Admin, verify they're updating a user in their own company
    if admin_role_key == 50:
        try:
            sql = "SELECT company_id FROM users WHERE id = %s"
            results, success = execute_sql(sql, (user_id,))
            
            if not success or not results:
                return jsonify({"error": "User not found"}), 404
            
            user_to_update = results[0]
            
            if user_to_update["company_id"] != admin_company_id:
                return jsonify({"error": "You can only update users in your own company"}), 403
        except Exception as e:
            logger.error(f"Error checking user company: {e}")
            return jsonify({"error": "Failed to verify user"}), 500
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract fields
    name = data.get("name")
    role_key_new = data.get("role_key")
    user_enabled = data.get("user_enabled")
    company_id = data.get("company_id")
    
    # Build update query dynamically
    update_fields = []
    update_values = []
    
    if name is not None:
        if not name.strip():
            return jsonify({"error": "Name cannot be empty"}), 400
        update_fields.append("name = %s")
        update_values.append(name)
    
    if role_key_new is not None:
        update_fields.append("role_key = %s")
        update_values.append(role_key_new)
    
    if user_enabled is not None:
        update_fields.append("user_enabled = %s")
        update_values.append(user_enabled)
    
    if company_id is not None:
        # Verify company exists
        try:
            sql = "SELECT id FROM users_company WHERE id = %s"
            results, success = execute_sql(sql, (company_id,))
            if not success or not results:
                return jsonify({"error": "Company not found"}), 404
        except Exception as e:
            logger.error(f"Error checking company: {e}")
            return jsonify({"error": "Failed to verify company"}), 500
        
        update_fields.append("company_id = %s")
        update_values.append(company_id)
    
    if not update_fields:
        return jsonify({"error": "No fields to update"}), 400
    
    try:
        # Check if user exists
        sql = "SELECT id FROM users WHERE id = %s"
        results, success = execute_sql(sql, (user_id,))
        
        if not success or not results:
            return jsonify({"error": "User not found"}), 404
        
        # Update user
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, email, name, role_key, user_enabled, created_at, updated_at, company_id
        """
        
        results, success = execute_sql(query, tuple(update_values))
        
        if not success or not results:
            return jsonify({"error": "Failed to update user"}), 500
        
        updated_user = results[0]
        
        # Get company name if company_id exists
        company_name = None
        if updated_user["company_id"]:
            sql = "SELECT company_name FROM users_company WHERE id = %s"
            results, success = execute_sql(sql, (updated_user["company_id"],))
            company = results[0] if success and results else None
            company_name = company["company_name"] if company else None
        
        # Get role name for user
        role_names = {50: "Company Admin", 10: "User", 1000: "Strawbay Admin"}
        role_name = role_names.get(updated_user["role_key"], "User")
        
        # If user was just approved (user_enabled set to True), send approval email
        if user_enabled is True:
            send_user_approved_email(
                to_email=updated_user["email"],
                name=updated_user["name"],
                company_name=company_name or "Your Company",
                role_name=role_name
            )
        
        logger.info(f"User {user_id} updated by admin {admin_id}")
        
        # Get company_enabled status
        sql = "SELECT company_enabled FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (updated_user["company_id"],))
        company = results[0] if success and results else None
        company_enabled = company["company_enabled"] if company else False
        
        return jsonify({
            "user": {
                "id": str(updated_user["id"]),
                "email": updated_user["email"],
                "name": updated_user["name"],
                "role_key": updated_user["role_key"],
                "user_enabled": updated_user["user_enabled"],
                "company_enabled": company_enabled,
                "company_name": company_name,
                "created_at": updated_user["created_at"],
                "updated_at": updated_user["updated_at"]
            }
        }), 200
    except Exception as e:
        logger.info(f"Error updating user: {e}")
        return jsonify({"error": "Failed to update user"}), 500


@blp_auth.route("/admin/users/<user_id>/send-password-reset", methods=["POST"])
def send_password_reset(user_id):
    """Send password reset email to user. Strawbay Admin can send to any user. Company Admin can send to users in their company."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    admin_id = session.get("user_id")
    admin_role_key = session.get("role_key")
    admin_company_id = session.get("company_id")
    
    # Check if user is Strawbay Admin (role_key == 1000) or Company Admin (role_key == 50)
    if admin_role_key not in [1000, 50]:
        return jsonify({"error": "Only Admins can send password reset emails"}), 403
    
    try:
        # Get user details
        sql = "SELECT id, email, name, company_id, user_enabled FROM users WHERE id = %s"
        results, success = execute_sql(sql, (user_id,))
        
        if not success or not results:
            return jsonify({"error": "User not found"}), 404
        
        user = results[0]
        
        # If Company Admin, verify they can send to this user
        if admin_role_key == 50 and user["company_id"] != admin_company_id:
            return jsonify({"error": "You can only send reset emails to users in your own company"}), 403
        
        # Generate temporary password reset token
        import secrets
        from datetime import datetime, timedelta
        reset_token = secrets.token_urlsafe(32)
        reset_token_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Store reset token in database
        sql = "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s"
        _, success = execute_sql(sql, (reset_token, reset_token_expires, user_id))
        
        if not success:
            return jsonify({"error": "Failed to generate reset token"}), 500
        
        reset_link = f"http://localhost:3000/reset-password/{reset_token}"
        
        # Send password reset email
        send_password_reset_email(
            to_email=user["email"],
            name=user["name"],
            reset_link=reset_link
        )
        
        logger.info(f"Password reset email sent to {user['email']} by admin {admin_id}")
        
        return jsonify({
            "message": f"Password reset email sent to {user['email']}",
            "user_email": user["email"]
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to send password reset email"}), 500


@blp_auth.route("/admin/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user. Only Strawbay Admin can do this."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    admin_id = session.get("user_id")
    role_key = session.get("role_key")
    
    # Check if user is Strawbay Admin (role_key == 1000)
    if role_key != 1000:
        return jsonify({"error": "Only Strawbay Admins can delete users"}), 403
    
    try:
        # Check if user exists and it's not the admin deleting themselves
        sql = "SELECT id, email FROM users WHERE id = %s"
        results, success = execute_sql(sql, (user_id,))
        
        if not success or not results:
            return jsonify({"error": "User not found"}), 404
        
        user = results[0]
        
        if str(user["id"]) == str(admin_id):
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        # Delete user
        sql = "DELETE FROM users WHERE id = %s"
        _, success = execute_sql(sql, (user_id,))
        
        if not success:
            return jsonify({"error": "Failed to delete user"}), 500
        
        logger.info(f"User {user['email']} deleted by admin {admin_id}")
        
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        logger.info(f"Error deleting user: {e}")
        return jsonify({"error": "Failed to delete user"}), 500


@blp_auth.route("/admin/companies/<company_id>", methods=["DELETE"])
def delete_company(company_id):
    """Delete a company. Only Strawbay Admin can do this."""
    # Check authentication
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    admin_id = session.get("user_id")
    role_key = session.get("role_key")
    
    # Check if user is Strawbay Admin (role_key == 1000)
    if role_key != 1000:
        return jsonify({"error": "Only Strawbay Admins can delete companies"}), 403
    
    try:
        # Check if company exists
        sql = "SELECT id, company_name FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success or not results:
            return jsonify({"error": "Company not found"}), 404
        
        company = results[0]
        
        # Delete all users associated with this company first
        sql = "DELETE FROM users WHERE company_id = %s"
        _, success = execute_sql(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to delete company users"}), 500
        
        # Delete company
        sql = "DELETE FROM users_company WHERE id = %s"
        _, success = execute_sql(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to delete company"}), 500
        
        logger.info(f"Company {company['company_name']} deleted by admin {admin_id}")
        
        return jsonify({"message": "Company deleted successfully"}), 200
    except Exception as e:
        logger.info(f"Error deleting company: {e}")
        return jsonify({"error": "Failed to delete company"}), 500


# =====================
# Plans Endpoint
# =====================

@blp_auth.route("/plans", methods=["GET"])
def get_plans():
    """Get all available plans and current company plan."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_id = session.get("user_id")
        company_id = session.get("company_id")
        
        # Get all plans
        sql = "SELECT * FROM price_plans ORDER BY price_plan_key DESC"
        results, success = execute_sql(sql, ())
        
        if not success:
            return jsonify({"error": "Failed to fetch plans"}), 500
        
        plans = results if results else []
        
        # Get current company plan
        sql = "SELECT price_plan_key FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        company = results[0] if success and results else None
        current_plan_key = company["price_plan_key"] if company else None
        
        # Convert plans to list of dicts
        plans_list = []
        for plan in plans:
            plans_list.append({
                "id": str(plan["id"]),
                "price_plan_key": plan["price_plan_key"],
                "plan_name": plan["plan_name"],
                "plan_description": plan["plan_description"],
                "price_per_month": float(plan["price_per_month"]) * 100,  # Convert to cents
                "features": plan["features"] or {}
            })
        
        return jsonify({
            "plans": plans_list,
            "current_plan_key": current_plan_key
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch plans"}), 500


@blp_auth.route("/features", methods=["GET"])
def get_features():
    """Get all available features with their descriptions."""
    try:
        import json
        from pathlib import Path
        
        features_dir = Path(__file__).parent / "features"
        features = []
        
        if features_dir.exists():
            for feature_file in sorted(features_dir.glob("*.json")):
                with open(feature_file, 'r') as f:
                    feature_data = json.load(f)
                    features.append(feature_data)
        
        return jsonify({"features": features}), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch features"}), 500


@blp_auth.route("/roles", methods=["GET"])
def get_roles():
    """Get all available user roles."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get all roles ordered by role_key
        sql = """
            SELECT role_key, role_name, role_description 
            FROM user_roles 
            ORDER BY role_key DESC
        """
        results, success = execute_sql(sql, ())
        
        if not success:
            return jsonify({"error": "Failed to fetch roles"}), 500
        
        roles = results if results else []
        
        # Convert to list of dicts
        roles_list = []
        for role in roles:
            roles_list.append({
                "key": role["role_key"],
                "name": role["role_name"],
                "description": role["role_description"]
            })
        
        return jsonify({"roles": roles_list}), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch roles"}), 500


@blp_auth.route("/payment-methods", methods=["GET"])
def get_payment_methods():
    """Get all available payment methods."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Payment methods can be hardcoded or fetched from config
        payment_methods = [
            {
                "key": "strawbay_invoice",
                "name": "Strawbay Invoice",
                "description": "Pay via Strawbay invoice",
                "enabled": True
            },
            {
                "key": "credit_card",
                "name": "Credit Card",
                "description": "Pay via credit card (Coming Soon)",
                "enabled": False
            }
        ]
        
        return jsonify({"payment_methods": payment_methods}), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch payment methods"}), 500


@blp_auth.route("/billing-details", methods=["GET"])
def get_billing_details():
    """Get company billing details."""
    try:
        if "company_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        
        sql = "SELECT * FROM users_company_billing WHERE company_id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to fetch billing details"}), 500
        
        if results:
            billing = results[0]
            return jsonify({
                "billing": {
                    "id": str(billing["id"]),
                    "billing_contact_name": billing["billing_contact_name"],
                    "billing_contact_email": billing["billing_contact_email"],
                    "country": billing["country"],
                    "city": billing["city"],
                    "postal_code": billing["postal_code"],
                    "street_address": billing["street_address"],
                    "vat_number": billing["vat_number"],
                    "payment_method": billing["payment_method"]
                }
            }), 200
        else:
            return jsonify({"billing": None}), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch billing details"}), 500


@blp_auth.route("/billing-details", methods=["POST"])
def save_billing_details():
    """Save or update company billing details."""
    try:
        if "company_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ["billing_contact_name", "billing_contact_email", "country", "city", "postal_code", "street_address"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Check if billing details already exist
        sql = "SELECT id FROM users_company_billing WHERE company_id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to check existing billing details"}), 500
        
        existing = results[0] if results else None
        
        if existing:
            # Update existing
            sql = """UPDATE users_company_billing 
                   SET billing_contact_name = %s, billing_contact_email = %s, 
                       country = %s, city = %s, postal_code = %s, street_address = %s,
                       vat_number = %s, payment_method = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE company_id = %s
                   RETURNING *"""
            results, success = execute_sql(sql, (data.get("billing_contact_name"), data.get("billing_contact_email"),
                 data.get("country"), data.get("city"), data.get("postal_code"),
                 data.get("street_address"), data.get("vat_number"), data.get("payment_method"),
                 company_id))
        else:
            # Insert new
            sql = """INSERT INTO users_company_billing 
                   (company_id, billing_contact_name, billing_contact_email, country, city, postal_code, street_address, vat_number, payment_method)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *"""
            results, success = execute_sql(sql, (company_id, data.get("billing_contact_name"), data.get("billing_contact_email"),
                 data.get("country"), data.get("city"), data.get("postal_code"),
                 data.get("street_address"), data.get("vat_number"), data.get("payment_method")))
        
        if not success or not results:
            return jsonify({"error": "Failed to save billing details"}), 500
        
        result = results[0]
        
        return jsonify({
            "message": "Billing details saved successfully",
            "billing": {
                "id": str(result["id"]),
                "billing_contact_name": result["billing_contact_name"],
                "billing_contact_email": result["billing_contact_email"],
                "country": result["country"],
                "city": result["city"],
                "postal_code": result["postal_code"],
                "street_address": result["street_address"],
                "vat_number": result["vat_number"],
                "payment_method": result["payment_method"]
            }
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to save billing details"}), 500


# =====================
# Password Reset Endpoints (Public)
# =====================

@blp_auth.route("/verify-reset-token/<token>", methods=["GET"])
def verify_reset_token(token):
    """Verify if a reset token is valid and not expired."""
    try:
        # Find user with this reset token
        sql = "SELECT id, email, name, reset_token_expires FROM users WHERE reset_token = %s"
        results, success = execute_sql(sql, (token,))
        
        if not success or not results:
            return jsonify({"error": "Invalid reset token"}), 404
        
        user = results[0]
        
        # Check if token is expired
        from datetime import datetime
        expires_at = user["reset_token_expires"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if datetime.utcnow() > expires_at:
            return jsonify({"error": "Reset token has expired"}), 400
        
        # Token is valid
        return jsonify({
            "valid": True,
            "email": user["email"],
            "name": user["name"]
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to verify token"}), 500


@blp_auth.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    """Reset user password using a valid reset token."""
    try:
        data = request.get_json()
        new_password = data.get("password")
        
        if not new_password:
            return jsonify({"error": "Password is required"}), 400
        
        # Validate password strength
        password_validation = validate_password_strength(new_password)
        if not password_validation["is_valid"]:
            error_message = password_validation["errors"][0] if password_validation["errors"] else "Password does not meet requirements"
            return jsonify({"error": error_message}), 400
        
        # Find user with this reset token
        sql = "SELECT id, email, reset_token_expires FROM users WHERE reset_token = %s"
        results, success = execute_sql(sql, (token,))
        
        if not success or not results:
            return jsonify({"error": "Invalid reset token"}), 404
        
        user = results[0]
        
        # Check if token is expired
        from datetime import datetime
        expires_at = user["reset_token_expires"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if datetime.utcnow() > expires_at:
            return jsonify({"error": "Reset token has expired"}), 400
        
        # Hash the new password
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(new_password)
        
        # Update password and clear the reset token
        sql = "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s"
        _, success = execute_sql(sql, (password_hash, user["id"]))
        
        if not success:
            return jsonify({"error": "Failed to reset password"}), 500
        
        logger.info(f"Password reset successful for user {user['email']}")
        
        return jsonify({
            "message": "Password reset successfully",
            "email": user["email"]
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to reset password"}), 500


@blp_auth.route("/change-plan", methods=["POST"])
def change_plan():
    """Change the company's pricing plan."""
    logger.info(f"Request received")
    
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    company_id = session.get("company_id")
    
    if not company_id:
        return jsonify({"error": "User has no company"}), 400
    
    data = request.get_json()
    price_plan_key = data.get("price_plan_key")
    
    if not price_plan_key:
        return jsonify({"error": "price_plan_key required"}), 400
    
    try:
        price_plan_key = int(price_plan_key)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid price_plan_key"}), 400
    
    try:
        # Get requester info (user who made the change)
        sql = "SELECT name, email FROM users WHERE id = %s"
        results, success = execute_sql(sql, (user_id,))
        requester = results[0] if success and results else None
        requester_name = requester["name"] if requester else "Administrator"
        requester_email = requester["email"] if requester else "unknown@strawbay.io"
        
        # Get current company info
        sql = "SELECT id, company_name, price_plan_key FROM users_company WHERE id = %s"
        results, success = execute_sql(sql, (company_id,))
        
        if not success or not results:
            return jsonify({"error": "Company not found"}), 404
        
        company = results[0]
        
        # Check if plan is different
        if company["price_plan_key"] == price_plan_key:
            return jsonify({"error": "Plan is already active"}), 400
        
        # Update company plan
        sql = """
            UPDATE users_company SET price_plan_key = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_name, price_plan_key
        """
        results, success = execute_sql(sql, (price_plan_key, company_id))
        
        if not success or not results:
            return jsonify({"error": "Failed to update plan"}), 500
        
        updated_company = results[0]
        
        # Get new plan name
        sql = "SELECT plan_name FROM price_plans WHERE price_plan_key = %s"
        results, success = execute_sql(sql, (price_plan_key,))
        plan = results[0] if success and results else None
        new_plan_name = plan["plan_name"] if plan else "Unknown"
        
        # Get billing contact info
        sql = """
            SELECT billing_contact_name, billing_contact_email FROM users_company_billing
            WHERE company_id = %s LIMIT 1
        """
        results, success = execute_sql(sql, (company_id,))
        billing = results[0] if success and results else None
        
        # Send confirmation email if billing contact exists
        if billing and billing["billing_contact_email"]:
            send_plan_change_email(
                to_email=billing["billing_contact_email"],
                billing_contact_name=billing["billing_contact_name"] or "Billing Contact",
                company_name=company["company_name"],
                new_plan_name=new_plan_name,
                requester_name=requester_name,
                requester_email=requester_email
            )
            logger.info(f"Confirmation email sent to {billing['billing_contact_email']}")
        
        # Update session with new plan
        session["price_plan_key"] = price_plan_key
        
        logger.info(f"Plan changed successfully for company {company_id}: {company['price_plan_key']} -> {price_plan_key}")
        
        return jsonify({
            "message": "Plan changed successfully",
            "company": {
                "id": updated_company["id"],
                "company_name": updated_company["company_name"],
                "price_plan_key": updated_company["price_plan_key"]
            }
        }), 200
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to change plan"}), 500


# =====================
# Document Upload Endpoint
# ========================
# 
# Denna endpoint hanterar filuppladdning och triggar
# async document processing via Celery.
#
# FLOW:
# 1. User uploade fil
# 2. Vi sparar fil och skapar DB record
# 3. Vi triggar async processing chain
# 4. Vi returnerar omedelbar (polling endpoint för status)

@blp_auth.route("/documents/upload", methods=["POST"])
def upload_document():
    """
    Upload a document and queue for async processing.
    
    Request: POST /documents/upload
        - file: Binary file (PDF/JPG/PNG)
        - Authentication: Required (via session)
    
    Response: 201 Created
        {
            "message": "Document uploaded and queued for processing",
            "document": {
                "id": "doc-uuid",
                "raw_filename": "invoice.pdf",
                "status": "preprocessing",
                "created_at": "2024-12-21T..."
            },
            "task_id": "celery-task-uuid"  # För polling
        }
    """
    try:
        from ic_shared.configuration import DOCUMENTS_RAW_DIR
        from werkzeug.utils import secure_filename
        
        # ========== AUTHENTICATION ==========
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_id = session.get("user_id")
        company_id = session.get("company_id")
        
        if not user_id or not company_id:
            return jsonify({"error": "User or company info not found in session"}), 400
        
        # ========== FILE VALIDATION ==========
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        
        allowed_extensions = {"pdf", "jpg", "jpeg", "png"}
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"}), 400
        
        # ========== SAVE FILE ==========
        doc_id = str(uuid.uuid4())
        unique_filename = f"{doc_id}.{file_ext}"
        
        # Use storage service (LOCAL or GCS)
        if not storage_service:
            return jsonify({"error": "Storage service not initialized"}), 500
        
        try:
            file_path = storage_service.save(f"raw/{unique_filename}", file)
            logger.info(f"File saved: {file_path}")
        except Exception as save_error:
            logger.info(f"Storage error: {save_error}")
            return jsonify({"error": "Failed to save file"}), 500
        
        # ========== CREATE DATABASE RECORD ==========
        # Extract filename without extension for document_name
        # Make it unique by appending timestamp to avoid duplicate key violations
        filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        import time
        unique_document_name = f"{filename_without_ext}_{int(time.time() * 1000)}"
        
        # Insert document record with status "preprocessing"
        # (actual processing starts after response)
        sql = """
            INSERT INTO documents 
            (id, company_id, uploaded_by, raw_format, raw_filename, document_name, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, company_id, uploaded_by, raw_format, raw_filename, document_name, status, created_at
        """
        results, success = execute_sql(sql, (doc_id, company_id, user_id, file_ext, filename, unique_document_name, "preprocessing"))
        
        if not success or not results:
            logger.info(f"Database error: Failed to create document record")
            return jsonify({"error": "Failed to create document record"}), 500
        
        document = results[0]
        logger.info(f"Document record created: {doc_id}")
        
        # ========== TRIGGER ASYNC PROCESSING ==========
        task_id = None
        processing_error = None
        try:
            if processing_backend:
                result = processing_backend.trigger_task(str(doc_id), str(company_id))
                task_id = result.get('task_id')
                backend_status = result.get('status')
                
                # Check if processing backend returned an error
                if backend_status in ['service_unavailable', 'service_error']:
                    processing_error = result.get('error', 'Unknown error')
                    logger.info(f"❌ PROCESSING ERROR: {processing_error}")
                    
                    # Update document status to failed_preprocessing
                    update_sql = "UPDATE documents SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                    execute_sql(update_sql, ('failed_preprocessing', doc_id))
                    logger.info(f"✅ Document status updated to failed_preprocessing")
                else:
                    logger.info(f"✅ Processing task queued via {processing_backend.backend_type}")
            else:
                logger.info(f"⚠️  Processing backend not initialized")
                task_id = None
        except Exception as task_error:
            logger.info(f"❌ Error triggering processing: {task_error}")
            processing_error = str(task_error)
            task_id = None
        
        return jsonify({
            "message": "Document uploaded" + (" and queued for processing" if not processing_error else " but processing unavailable"),
            "document": {
                "id": str(doc_id),
                "raw_filename": filename,
                "status": "failed_preprocessing" if processing_error else "preprocessing",
                "processing_error": processing_error if processing_error else None,
                "created_at": datetime.utcnow().isoformat()
            },
            "task_id": task_id,
            "processing_error": processing_error
        }), 201 if not processing_error else 202
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Upload failed"}), 500


# Document Processing Status Endpoint
# ===================================
# Polling endpoint för att checka processing status

@blp_auth.route("/documents/<doc_id>/status", methods=["GET"])
def get_document_processing_status(doc_id):
    """
    Get current processing status for a document.
    
    Used for real-time polling to track document through processing pipeline.
    
    Response:
    {
        "document_id": "doc-uuid",
        "status": "ocr_extracting",
        "status_description": "OCR extraction is in progress",
        "progress": {
            "current_step": 3,
            "total_steps": 6,
            "percentage": 50
        },
        "quality_score": null,  # Set after evaluation
        "created_at": "...",
        "last_update": "..."
    }
    """
    try:
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        
        # Get document
        sql = """
            SELECT d.id, d.status, d.created_at, d.updated_at, d.predicted_accuracy
            FROM documents d
            WHERE d.id = %s AND d.company_id = %s
        """
        results, success = execute_sql(sql, (doc_id, company_id))
        
        if not success or not results:
            return jsonify({"error": "Document not found"}), 404
        
        document = results[0]
        
        # Get status description
        sql = "SELECT status_name, status_description FROM document_status WHERE status_key = %s"
        results, success = execute_sql(sql, (document['status'],))
        
        status_info = results[0] if success and results else None
        status_name = status_info['status_name'] if status_info else document['status']
        status_desc = status_info['status_description'] if status_info else ""
        
        # Calculate progress
        status_steps = {
            'preprocessing': 1,
            'preprocessed': 1,
            'ocr_extracting': 2,
            'predicting': 3,
            'predicted': 3,
            'extraction': 4,
            'extraction_error': 4,
            'automated_evaluation': 5,
            'automated_evaluation_error': 5,
            'manual_review': 5,
            'approved': 6,
            'exported': 6,
        }
        
        current_step = status_steps.get(document['status'], 0)
        total_steps = 6
        
        return jsonify({
            "document_id": doc_id,
            "status": document['status'],
            "status_name": status_name,
            "status_description": status_desc,
            "progress": {
                "current_step": current_step,
                "total_steps": total_steps,
                "percentage": int((current_step / total_steps) * 100)
            },
            "quality_score": float(document['predicted_accuracy']) if document['predicted_accuracy'] else None,
            "created_at": document['created_at'].isoformat() if document['created_at'] else None,
            "last_update": document['updated_at'].isoformat() if document['updated_at'] else None
        }), 200

    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch status"}), 500


@blp_auth.route("/documents/<doc_id>/restart", methods=["POST"])
def restart_document(doc_id):
    """
    Restart document processing from the beginning.
    
    Request: POST /documents/<doc_id>/restart
        - Authentication: Required (via session)
    
    Response: 200 OK
        {
            "message": "Document processing restarted",
            "document": {
                "id": "doc-uuid",
                "status": "preprocessing",
                "created_at": "2024-12-21T..."
            },
            "task_id": "celery-task-uuid"
        }
    """
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # Verify document belongs to user's company
        sql = """
            SELECT id, raw_filename, status FROM documents
            WHERE id = %s AND company_id = %s
        """
        results, success = execute_sql(sql, (str(doc_uuid), str(company_id)))
        
        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        document = results[0]
        
        # Reset document status to preprocessing
        update_sql = """
            UPDATE documents
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, raw_filename, status, created_at, updated_at
        """
        update_results, update_success = execute_sql(update_sql, ("preprocessing", str(doc_uuid)))
        
        if not update_success or not update_results:
            logger.info(f"Error: Failed to reset document status")
            return jsonify({"error": "Failed to reset document status"}), 500
        
        updated_doc = update_results[0]
        logger.info(f"Document {doc_id} status reset to preprocessing")
        
        # ========== TRIGGER ASYNC PROCESSING ==========
        try:
            import requests
            
            # Call processing service via HTTP to trigger task
            processing_url = os.environ.get('PROCESSING_SERVICE_URL', 'http://localhost:5002')
            
            response = requests.post(
                f'{processing_url}/api/tasks/orchestrate',
                json={
                    'document_id': str(doc_uuid),
                    'company_id': str(company_id)
                },
                timeout=10
            )
            
            task_id = response.json().get('task_id', 'processing-queued')
            logger.info(f"Processing task queued: {task_id}")
            
            return jsonify({
                "message": "Document processing restarted",
                "document": {
                    "id": updated_doc["id"],
                    "status": updated_doc["status"],
                    "created_at": updated_doc["created_at"].isoformat() if updated_doc["created_at"] else None
                },
                "task_id": task_id
            }), 200
                
        except Exception as e:
            # Log error but still return success since status is reset
            logger.info(f"Warning: Failed to queue processing task: {str(e)}")
            return jsonify({
                "message": "Document status reset, processing will begin shortly",
                "document": {
                    "id": updated_doc["id"],
                    "status": updated_doc["status"],
                    "created_at": updated_doc["created_at"].isoformat() if updated_doc["created_at"] else None
                }
            }), 200
    
    except Exception as e:
        logger.info(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@blp_auth.route("/documents", methods=["GET"])
def get_documents():
    """Get all documents for the authenticated user's company."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        sql = """
            SELECT d.id, d.company_id, d.uploaded_by, d.raw_format, d.raw_filename, 
                   d.document_name, d.processed_image_filename, d.content_type, d.status, d.predicted_accuracy, 
                   d.is_training, d.created_at, d.updated_at,
                   ds.status_name
            FROM documents d
            LEFT JOIN document_status ds ON d.status = ds.status_key
            WHERE d.company_id = %s
            ORDER BY d.created_at DESC
        """
        results, success = execute_sql(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to fetch documents"}), 500
        
        documents = results if results else []
        return jsonify({
            "documents": [dict(doc) for doc in documents]
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch documents"}), 500


@blp_auth.route("/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    """Update a document's extracted invoice data."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # First, verify the document belongs to the user's company and get current name
        sql = """
            SELECT id, document_name FROM documents
            WHERE id = %s AND company_id = %s
        """
        results, success = execute_sql(sql, (str(doc_uuid), str(company_id)))
        
        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        existing_doc = results[0]
        
        # Extract allowed fields from request data
        allowed_fields = {
            "document_name": data.get("document_name"),
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "vendor_name": data.get("vendor_name"),
            "amount": data.get("amount"),
            "vat": data.get("vat"),
            "total": data.get("total"),
            "due_date": data.get("due_date"),
            "reference": data.get("reference"),
        }
        
        # Check if document_name is being changed and if it's unique within the company
        new_document_name = allowed_fields["document_name"]
        if new_document_name and new_document_name != existing_doc["document_name"]:
            # Check for duplicates (ignore NULL values)
            dup_sql = """
                SELECT id FROM documents
                WHERE company_id = %s AND document_name = %s AND id != %s
            """
            dup_results, dup_success = execute_sql(dup_sql, (str(company_id), new_document_name, str(doc_uuid)))
            if dup_success and dup_results:
                return jsonify({
                    "error": "A document with this name already exists in your company"
                }), 409
        
        # Update the document with document_name only
        # TODO: Create separate invoice_data table for extracted data
        update_sql = """
            UPDATE documents
            SET document_name = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_id, uploaded_by, raw_format, raw_filename, 
                      document_name, processed_image_filename, content_type, status, 
                      predicted_accuracy, is_training, created_at, updated_at
        """
        update_results, update_success = execute_sql(update_sql, (allowed_fields["document_name"], str(doc_uuid)))
        
        if not update_success or not update_results:
            logger.info(f"Error: Failed to update document")
            return jsonify({"error": "Failed to update document"}), 500
        
        updated_doc = update_results[0]
        
        return jsonify({
            "message": "Document updated successfully",
            "document": dict(updated_doc)
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to update document"}), 500


# =====================
# Preview Endpoint
# =====================
@blp_auth.route("/documents/<doc_id>/preview", methods=["GET"])
def get_document_preview(doc_id):
    """Get preview for a document. Returns file content if status allows preview."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # Get document details
        sql = """
            SELECT id, raw_filename, status FROM documents
            WHERE id = %s AND company_id = %s
        """
        results, success = execute_sql(sql, (str(doc_uuid), str(company_id)))
        
        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        doc = results[0]
        
        # Check if status allows preview
        allowed_statuses = ["uploaded", "preprocessing", "preprocess_error"]
        if doc["status"] not in allowed_statuses:
            return jsonify({
                "error": f"Preview not available for status: {doc['status']}"
            }), 400
        
        # Get file using storage service
        _, ext = os.path.splitext(doc["raw_filename"])
        file_storage_path = f"raw/{doc['id']}{ext}"
        
        if not storage_service:
            return jsonify({"error": "Storage service not initialized"}), 500
        
        file_content = storage_service.get(file_storage_path)
        if file_content is None:
            return jsonify({"error": "File not found in storage"}), 404
        
        # Read and serve the file
        from flask import send_file
        from io import BytesIO
        
        # Determine MIME type based on file extension
        mime_type = "application/octet-stream"
        if ext.lower() in [".pdf"]:
            mime_type = "application/pdf"
        elif ext.lower() in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext.lower() in [".png"]:
            mime_type = "image/png"
        elif ext.lower() in [".tiff", ".tif"]:
            mime_type = "image/tiff"
        
        return send_file(
            BytesIO(file_content),
            mimetype=mime_type,
            as_attachment=False,
            download_name=doc["raw_filename"]
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in get_document_preview: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

api.register_blueprint(blp_live)
api.register_blueprint(blp_auth)

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

