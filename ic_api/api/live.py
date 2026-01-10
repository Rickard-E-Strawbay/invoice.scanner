from flask_smorest import Api, Blueprint
from flask import request, jsonify, session
from lib.email_service import send_plan_change_email
from werkzeug.security import generate_password_hash, check_password_hash
from ic_shared.database.connection import execute_sql, fetch_all
from ic_shared.logging import ComponentLogger, logger
from api.helpers import refresh_user_session

blp_live = Blueprint("live", "live", url_prefix="/live", description="Live endpoints")

logger = ComponentLogger("LiveAPI")

@blp_live.route("/me", methods=["GET"])
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


@blp_live.route("/profile", methods=["PUT"])
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
        
        # Add user_id for WHERE clause (after SET fields)
        user_id_str = str(user_id) if not isinstance(user_id, str) else user_id
        update_values.append(user_id_str)
        
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
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500


@blp_live.route("/change-password", methods=["PUT"])
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
        results, success = fetch_all(sql, (user_id,))
        
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
    
@blp_live.route("/search-companies", methods=["GET"])
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
        results, success = fetch_all(sql, (f"%{query}%",))
        
        if not success:
            logger.error(f"Database error")
            return jsonify({"error": "Search failed"}), 500
        
        companies = results if results else []
        logger.info(f"Found {len(companies)} companies: {companies}")
        return jsonify({"companies": [dict(company) for company in companies]}), 200
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return jsonify({"error": "Search failed"}), 500
    
@blp_live.route("/plans", methods=["GET"])
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
        results, success = fetch_all(sql, ())
        
        if not success:
            return jsonify({"error": "Failed to fetch plans"}), 500
        
        plans = results if results else []
        
        # Get current company plan
        sql = "SELECT price_plan_key FROM users_company WHERE id = %s"
        results, success = fetch_all(sql, (company_id,))
        
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

@blp_live.route("/features", methods=["GET"])
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

@blp_live.route("/roles", methods=["GET"])
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
        results, success = fetch_all(sql, ())
        
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

@blp_live.route("/payment-methods", methods=["GET"])
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


@blp_live.route("/billing-details", methods=["GET"])
def get_billing_details():
    """Get company billing details."""
    try:
        if "company_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        
        sql = "SELECT * FROM users_company_billing WHERE company_id = %s"
        results, success = fetch_all(sql, (company_id,))
        
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

@blp_live.route("/billing-details", methods=["POST"])
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
        results, success = fetch_all(sql, (company_id,))
        
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

@blp_live.route("/company-info", methods=["GET"])
def get_company_info():
    """Get the current user's company information."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"error": "User has no company"}), 400
    
    try:
        sql = """
            SELECT id, company_name, company_email, organization_id
            FROM users_company
            WHERE id = %s
        """
        results, success = fetch_all(sql, (company_id,))
        
        if not success or not results:
            return jsonify({"error": "Company not found"}), 404
        
        company = results[0]
        return jsonify({
            "id": str(company["id"]),
            "company_name": company["company_name"],
            "company_email": company["company_email"],
            "organization_id": company["organization_id"]
        }), 200
    except Exception as e:
        logger.info(f"Error fetching company info: {e}")
        return jsonify({"error": "Failed to fetch company information"}), 500

@blp_live.route("/company-info", methods=["POST"])
def save_company_info():
    """Update the current user's company information."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"error": "User has no company"}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    company_name = data.get("company_name", "").strip()
    company_email = data.get("company_email", "").strip()
    
    if not company_name:
        return jsonify({"error": "Company name is required"}), 400
    if not company_email:
        return jsonify({"error": "Company email is required"}), 400
    
    try:
        # Update company information
        sql = """
            UPDATE users_company
            SET company_name = %s, company_email = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_name, company_email, organization_id
        """
        results, success = execute_sql(sql, (company_name, company_email, company_id))
        
        if not success or not results:
            return jsonify({"error": "Failed to update company"}), 500
        
        company = results[0]
        
        # Update session with new company info
        session["company_name"] = company_name
        
        logger.info(f"Company info updated for company {company_id}")
        return jsonify({
            "message": "Company information updated successfully",
            "company": {
                "id": str(company["id"]),
                "company_name": company["company_name"],
                "company_email": company["company_email"],
                "organization_id": company["organization_id"]
            }
        }), 200
    except Exception as e:
        logger.info(f"Error saving company info: {e}")
        return jsonify({"error": "Failed to save company information"}), 500    

@blp_live.route("/verify-reset-token/<token>", methods=["GET"])
def verify_reset_token(token):
    """Verify if a reset token is valid and not expired."""
    try:
        # Find user with this reset token
        sql = "SELECT id, email, name, reset_token_expires FROM users WHERE reset_token = %s"
        results, success = fetch_all(sql, (token,))
        
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

@blp_live.route("/reset-password/<token>", methods=["POST"])
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
        results, success = fetch_all(sql, (token,))
        
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
    
@blp_live.route("/change-plan", methods=["POST"])
def change_plan():
    """Change the company's pricing plan."""
    logger.info(f"Request received")
    
    if "user_id" not in session:
        logger.info(f"User not authenticated")
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session.get("user_id")
    company_id = session.get("company_id")
    
    if not company_id:
        logger.info(f"User has no company")
        return jsonify({"error": "User has no company"}), 400
    
    data = request.get_json()
    logger.info(f"Request data: {data}")
    price_plan_key = data.get("price_plan_key")
    
    if not price_plan_key:
        logger.info(f"price_plan_key not provided in request")
        return jsonify({"error": "price_plan_key required"}), 400
    
    try:
        price_plan_key = int(price_plan_key)
    except (ValueError, TypeError) as e:
        logger.info(f"Invalid price_plan_key: {price_plan_key}, error: {e}")
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


