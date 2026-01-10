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
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ic_shared.database.connection import execute_sql, fetch_all
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
            results, success = fetch_all("SELECT 1 AS warmup")
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


# =============
# CORS Configuration
# =============
import re


# =============
# CORS Configuration
# =============
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

# Configure CORS with regex pattern matching for Cloud Run
CORS(app, 
     supports_credentials=True, 
     origins_regex=get_cors_origins_regex(),
     allow_headers=['Content-Type', 'Authorization'])

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

@blp_live.route("/x")
def x():
    return jsonify({"status": "done"})

# ======================
# Authentication Routes
# ======================











# =====================
# Plans Endpoint
# =====================



# =====================
# Password Reset Endpoints (Public)
# =====================




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
        results, success = fetch_all(sql, (user_id,))
        requester = results[0] if success and results else None
        requester_name = requester["name"] if requester else "Administrator"
        requester_email = requester["email"] if requester else "unknown@strawbay.io"
        
        # Get current company info
        sql = "SELECT id, company_name, price_plan_key FROM users_company WHERE id = %s"
        results, success = fetch_all(sql, (company_id,))
        
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
        results, success = fetch_all(sql, (price_plan_key,))
        plan = results[0] if success and results else None
        new_plan_name = plan["plan_name"] if plan else "Unknown"
        
        # Get billing contact info
        sql = """
            SELECT billing_contact_name, billing_contact_email FROM users_company_billing
            WHERE company_id = %s LIMIT 1
        """
        results, success = fetch_all(sql, (company_id,))
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
        results, success = fetch_all(sql, (doc_id, company_id))
        
        if not success or not results:
            return jsonify({"error": "Document not found"}), 404
        
        document = results[0]
        
        # Get status description
        sql = "SELECT status_name, status_description FROM document_status WHERE status_key = %s"
        results, success = fetch_all(sql, (document['status'],))
        
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
        results, success = fetch_all(sql, (str(doc_uuid), str(company_id)))
        
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
        results, success = fetch_all(sql, (company_id,))
        
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
        results, success = fetch_all(sql, (str(doc_uuid), str(company_id)))
        
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
            dup_results, dup_success = fetch_all(dup_sql, (str(company_id), new_document_name, str(doc_uuid)))
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

