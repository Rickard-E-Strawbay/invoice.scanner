from flask_smorest import Api, Blueprint
from flask import request, jsonify, session
from ic_shared.database.connection import execute_sql, fetch_all
from ic_shared.logging import ComponentLogger
from lib.email_service import send_company_approved_email

blp_admin = Blueprint("admin", "admin", url_prefix="/admin", description="Admin endpoints")
logger = ComponentLogger("AdminAPI")


    
@blp_admin.route("/companies", methods=["GET"])
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
        results, success = fetch_all(sql, ())
        
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


@blp_admin.route("/companies", methods=["POST"])
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
        results, success = fetch_all(sql, (organization_id,))
        
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


@blp_admin.route("/companies/<company_id>", methods=["PUT"])
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
        results, success = fetch_all(sql, (company_id,))
        
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
            results, success = fetch_all(sql, (company_id,))
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

@blp_admin.route("/users", methods=["GET"])
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
            results, success = fetch_all(sql, (company_id,))
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
            results, success = fetch_all(sql, ())
        
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


@blp_admin.route("/users", methods=["POST"])
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
        results, success = fetch_all(sql, (company_id,))
        
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
        results, success = fetch_all(sql, (company_id,))
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


@blp_admin.route("/users/<user_id>", methods=["PUT"])
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
            results, success = fetch_all(sql, (user_id,))
            
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
            results, success = fetch_all(sql, (company_id,))
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
        results, success = fetch_all(sql, (user_id,))
        
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
            results, success = fetch_all(sql, (updated_user["company_id"],))
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
        results, success = fetch_all(sql, (updated_user["company_id"],))
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


@blp_admin.route("/users/<user_id>/send-password-reset", methods=["POST"])
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
        results, success = fetch_all(sql, (user_id,))
        
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
        sql = "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s RETURNING id"
        results, success = execute_sql(sql, (reset_token, reset_token_expires, user_id))
        
        if not success or not results:
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

@blp_admin.route("/users/<user_id>", methods=["DELETE"])
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
        results, success = fetch_all(sql, (user_id,))
        
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

@blp_admin.route("/companies/<company_id>", methods=["DELETE"])
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
        results, success = fetch_all(sql, (company_id,))
        
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
