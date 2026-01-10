from flask_smorest import Api, Blueprint
from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from ic_shared.database.connection import execute_sql, fetch_all
from ic_shared.logging import ComponentLogger
from lib.email_service import (
    send_password_reset_email,
    send_company_registration_pending_email,
    send_user_registration_pending_email,
)
from lib.password_validator import validate_password_strength
from api.helpers import refresh_user_session
import uuid
import re   


blp_auth = Blueprint("auth", "auth", url_prefix="/auth", description="Authentication endpoints")

logger = ComponentLogger("AuthAPI")


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
        results, success = fetch_all(sql, (email,))
        
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
        results, success = fetch_all(sql, (email,))
        if success and results:
            return jsonify({"error": "User already exists"}), 409
        
        # Check if organization exists in users_company
        sql = "SELECT id, company_name, company_email, company_enabled FROM users_company WHERE organization_id = %s"
        results, success = fetch_all(sql, (organization_id,))
        
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
        results, success = fetch_all(sql, (company_id,))
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
            results, success = fetch_all(sql, (company_id,))
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
        results, success = fetch_all(sql, (company_id,))
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
    results, success = fetch_all(sql, (email,))
    
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