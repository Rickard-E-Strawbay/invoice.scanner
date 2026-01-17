"""Company settings management for the Invoice Scanner API."""

import json
from ic_shared.database.connection import execute_sql, fetch_all
from ic_shared.configuration.defines import COMPANY_SETTINGS_DEFAULTS
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("CompanySettingsManager")


def get_company_settings(company_id):
    """
    Fetch company settings from database.
    If settings are empty or null, return COMPANY_SETTINGS_DEFAULTS.
    
    Args:
        company_id: UUID of the company
        
    Returns:
        dict: Company settings merged with defaults
    """
    try:
        # Convert to string if necessary
        company_id_str = str(company_id) if not isinstance(company_id, str) else company_id
        
        # Fetch company_settings from database
        query = "SELECT company_settings FROM users_company WHERE id = %s"
        results, success = fetch_all(query, (company_id_str,))
        
        if not success or not results:
            logger.warning(f"Company not found: {company_id_str}")
            return COMPANY_SETTINGS_DEFAULTS.copy()
        
        company_row = results[0]
        company_settings = company_row.get("company_settings")  # JSONB column from DB
        
        # If company_settings is None or empty, return defaults
        if not company_settings:
            logger.info(f"No company settings for {company_id_str}, returning defaults")
            return COMPANY_SETTINGS_DEFAULTS.copy()
        
        # If company_settings is a string (JSON from JSONB), parse it
        if isinstance(company_settings, str):
            try:
                company_settings = json.loads(company_settings)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse company_settings JSON for {company_id_str}")
                return COMPANY_SETTINGS_DEFAULTS.copy()
        
        # If it's an empty dict, return defaults
        if not company_settings or not isinstance(company_settings, dict):
            logger.info(f"Empty company settings for {company_id_str}, returning defaults")
            return COMPANY_SETTINGS_DEFAULTS.copy()
        
        # Merge with defaults (company settings override defaults)
        merged_settings = COMPANY_SETTINGS_DEFAULTS.copy()
        merged_settings.update(company_settings)
        
        logger.success(f"✅ Retrieved company settings for {company_id_str}")
        return merged_settings
        
    except Exception as e:
        logger.error(f"Error fetching company settings: {str(e)}")
        return COMPANY_SETTINGS_DEFAULTS.copy()


def update_company_settings(company_id, settings):
    """
    Update company settings in database.
    
    Args:
        company_id: UUID of the company
        settings: dict of settings to update
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        company_id_str = str(company_id) if not isinstance(company_id, str) else company_id
        settings_json = json.dumps(settings)
        
        query = """
            UPDATE users_company
            SET company_settings = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_settings
        """
        
        results, success = execute_sql(query, [settings_json, company_id_str])
        
        if not success or not results:
            logger.error(f"Failed to update company settings for {company_id_str}")
            return False, "Failed to update company settings"
        
        logger.success(f"✅ Updated company settings for {company_id_str}")
        return True, "Company settings updated successfully"
        
    except Exception as e:
        logger.error(f"Error updating company settings: {str(e)}")
        return False, str(e)
