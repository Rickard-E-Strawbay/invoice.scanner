#!/usr/bin/env python3
"""Test script to verify settings are saved correctly in database."""

import json
from ic_shared.database.connection import execute_sql
from ic_shared.configuration.defines import COMPANY_SETTINGS_DEFAULTS
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("TestSettings")

# Get first company ID from database
query = "SELECT id, company_name FROM users_company LIMIT 1"
results, success = execute_sql(query, [])

if success and results:
    company_id = results[0]["id"]
    company_name = results[0]["company_name"]
    print(f"✅ Found company: {company_name} (ID: {company_id})")
    
    # Fetch current settings
    query = "SELECT company_settings FROM users_company WHERE id = %s"
    results, success = execute_sql(query, [str(company_id)])
    
    if success and results:
        current_settings = results[0]["company_settings"]
        print(f"\n📊 Current settings in DB:")
        if current_settings:
            if isinstance(current_settings, dict):
                print(json.dumps(current_settings, indent=2))
            else:
                print(current_settings)
        else:
            print("NULL - will use defaults")
        
        # Show defaults structure
        print(f"\n🔧 Default settings structure:")
        print(json.dumps(COMPANY_SETTINGS_DEFAULTS, indent=2))
        
        # Test update
        test_settings = {
            "scanner_settings": {
                "name": "Scanner Configuration",
                "parameters": [
                    {"name": "Enabled", "key": "enabled", "type": "boolean", "default": True, "description": "Enable document scanner"},
                    {"name": "Confidence Threshold", "key": "confidence_threshold", "type": "float", "default": 0.75, "description": "Minimum confidence score"},
                    {"name": "Max Pages", "key": "max_pages", "type": "integer", "default": 500, "description": "Max pages per document"},
                    {"name": "API Key", "key": "api_key", "type": "text", "default": "", "description": "External API key"}
                ]
            }
        }
        
        print(f"\n📝 Attempting to save test settings...")
        update_query = """
            UPDATE users_company
            SET company_settings = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_settings
        """
        
        test_json = json.dumps(test_settings)
        results, success = execute_sql(update_query, [test_json, str(company_id)])
        
        if success and results:
            print(f"✅ Settings saved successfully!")
            saved_settings = results[0][1]
            print(f"\n🔍 Verification - Settings now in DB:")
            if isinstance(saved_settings, dict):
                print(json.dumps(saved_settings, indent=2))
            else:
                print(json.dumps(json.loads(saved_settings), indent=2))
        else:
            print(f"❌ Failed to save settings")
    else:
        print("❌ Failed to fetch current settings")
else:
    print("❌ No companies found in database")
