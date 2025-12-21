#!/usr/bin/env python3
"""Create a test user for login testing."""

from werkzeug.security import generate_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

def create_test_user():
    password = "Test123!"
    hashed = generate_password_hash(password)
    print(f"Password hash: {hashed}")
    
    # When running in Docker, use 'db' as hostname
    # When running locally, use 'localhost'
    try:
        conn = psycopg2.connect(
            host="db",
            port=5432,
            user="scanner",
            password="scanner",
            database="invoice_scanner"
        )
    except:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="scanner",
            password="scanner",
            database="invoice_scanner"
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # First, check if test company exists
            cursor.execute("SELECT id FROM users_company WHERE company_name = %s", ('Test Company',))
            company = cursor.fetchone()
            
            if not company:
                # Create a test company
                cursor.execute("""
                    INSERT INTO users_company (company_name, company_email, organization_id, price_plan_key, company_enabled)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, ('Test Company', 'company@test.com', 'test-org-001', 10, True))
                company_id = cursor.fetchone()['id']
                print(f"Created company: Test Company with ID: {company_id}")
            else:
                company_id = company['id']
                print(f"Using existing company: Test Company with ID: {company_id}")
            
            # Delete old test user if exists
            cursor.execute("DELETE FROM users WHERE email = %s", ('admin@test.com',))
            
            # Insert new test user with role_key=1 (admin)
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role_key, company_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, ('admin@test.com', hashed, 'Test Admin', 1, company_id))
            
            user_id = cursor.fetchone()['id']
            conn.commit()
            print(f"✅ Created user: admin@test.com with ID: {user_id}")
            print(f"   Password: {password}")
            return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_test_user()
    sys.exit(0 if success else 1)
