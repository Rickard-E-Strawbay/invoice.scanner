"""
Document operations - generic database functions for document management.

These functions are shared across API, Cloud Functions, and other services.
Uses fetch_all() for SELECT queries and execute_sql() for UPDATE/INSERT/DELETE.
"""

import sys
import os

# Debug: Add project root to path when running directly from VS Code
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, project_root)

from ic_shared.logging import ComponentLogger
from ic_shared.database.connection import execute_sql, fetch_all
import copy

logger = ComponentLogger("DocumentOperations")


def reshape_to_peppol_format(data: dict) -> dict:
    """
    Convert simple key-value pairs to PEPPOL format with confidence scores.
    {"field": "value"} → {"field": {"v": "value", "p": 1.0}}
    Works recursively for nested structures and arrays.
    """
    if not isinstance(data, dict):
        return data
    
    reshaped = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively reshape nested dicts
            reshaped[key] = reshape_to_peppol_format(value)
        elif isinstance(value, list):
            # Handle arrays (like line_items)
            reshaped[key] = [
                reshape_to_peppol_format(item) if isinstance(item, dict) else {"v": str(item), "p": 1.0}
                for item in value
            ]
        elif value is not None:
            # Convert to PEPPOL format: {"v": value, "p": 1.0}
            reshaped[key] = {"v": str(value), "p": 1.0}
        else:
            # Keep None values as-is
            reshaped[key] = value
    
    return reshaped


def get_document_status(document_id: str) -> str:
    """
    Retrieve the current status of a document from the database.
    Uses shared fetch_all() for database access.

    Args:
        document_id (str): The unique identifier of the document.

    Returns:
        str: The status of the document if found, otherwise 'NOT_FOUND' or 'ERROR'.
    """
    
    try:
        results, success = fetch_all(
            """
            SELECT status
            FROM documents
            WHERE id = %s
            """,
            (document_id,)
        )
        
        if not success:
            logger.error("Failed to query document status")
            return "ERROR"
        
        if results:
            status = results[0].get("status") or results[0][0]
            return status
        else:
            return "NOT_FOUND"
    except Exception as e:
        logger.error(f"✗ Error querying document status: {e}")
        return "ERROR"
    
def get_document_data(document_id: str) -> dict:
    """
    Retrieve the full document data from the database.
    Uses shared fetch_all() for database access.

    Args:
        document_id (str): The unique identifier of the document.  
    Returns:
        dict: The document data if found, otherwise empty dict.
    """
    try:
        results, success = fetch_all(
            """
            SELECT *
            FROM documents
            WHERE id = %s
            """,
            (document_id,)
        )
        
        if not success:
            logger.error("Failed to query document data")
            return {}
        
        if results:
            document_data = results[0]
            return document_data
        else:
            return {}
    except Exception as e:
        logger.error(f"✗ Error querying document data: {e}")
        return {}   


def update_document_status(document_id: str, status: str, dict_key_val:dict = None) -> bool:
    """
    Update document status in database using shared execute_sql().

    NOTE: This is a best-effort operation. If Cloud SQL connection fails,
    we log the error but continue processing. The API layer handles
    initial status updates (e.g., 'preprocessing' when document uploaded).
    This status update is for visibility only.

    Args:
        document_id (str): The unique identifier of the document.
        status (str): The new status to set.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    # logger.info(f"[DB] Updating document {document_id} to status '{status}'")

    sql = "UPDATE documents SET status = %s, updated_at = CURRENT_TIMESTAMP "
    params = [status]
    
    if dict_key_val:
        for key, val in dict_key_val.items():
            sql += ", {key} = %s ".format(key=key)
            params.append(val)
    
    sql += "WHERE id = %s"
    params.append(document_id)

    try:
        results, success = execute_sql(sql, params)
        
        if success:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"❌ Error updating status: {type(e).__name__}: {e}")
        return False
    



def merge_peppol_json(peppol_slave: dict, peppol_master: dict) -> dict:
    """
    Merge two Peppol JSON structures.
    
    Rules:
    1. No elements in original structures are modified
    2. Returns new merged structure
    3. Merged structure contains ALL elements from peppol_slave
    4. Merged structure contains ALL elements from peppol_master
    5. Where "v" or "p" differs, use master value (override)
    
    Logic:
    - Start with deep copy of slave (preserve all slave elements)
    - Recursively merge master into result
    - For shared keys: master overrides where both exist
    - For Peppol values {"v": ..., "p": ...}: replace entirely
    - For container dicts: merge recursively
    
    Args:
        peppol_slave (dict): Base document (all elements preserved)
        peppol_master (dict): Override document (overrides matching keys)
    
    Returns:
        dict: New merged document with all elements from both sources
    """
    try:
        result = copy.deepcopy(peppol_slave) if peppol_slave else {}
        
        if not peppol_master:
            return result
        
        def is_peppol_value(obj):
            """Check if object is a Peppol value dict {"v": ..., "p": ...}"""
            if isinstance(obj, dict):
                # Peppol values have only "v" and/or "p" keys
                return len(obj) <= 2 and all(k in ("v", "p") for k in obj.keys())
            return False
        
        def merge_recursive(target: dict, source: dict) -> dict:
            """
            Recursively merge source into target.
            - All target keys are preserved
            - Source keys are added or override target
            - For nested dicts: recurse if both are container dicts
            - For Peppol values: replace entirely (master wins)
            """
            for key, source_value in source.items():
                target_value = target.get(key)
                
                if isinstance(source_value, dict) and isinstance(target_value, dict):
                    # Check if these are Peppol values ({"v": ..., "p": ...})
                    if is_peppol_value(source_value) or is_peppol_value(target_value):
                        # It's a Peppol value - replace entirely with source (master wins)
                        target[key] = copy.deepcopy(source_value)
                    else:
                        # It's a container dict - merge recursively (both preserved)
                        merge_recursive(target[key], source_value)
                else:
                    # Simple value or source is dict but target isn't - use source
                    target[key] = copy.deepcopy(source_value)
            
            return target
        
        result = merge_recursive(result, peppol_master)
        logger.info(f"✅ Successfully merged Peppol JSON (all elements from both preserved)")
        return result
        
    except Exception as e:
        logger.error(f"✗ Error merging Peppol JSON: {type(e).__name__}: {e}")
        return copy.deepcopy(peppol_slave) if peppol_slave else {}
            


def apply_peppol_json_template(document: dict, template: dict) -> dict:
    """
    Apply PEPPOL template to document.
    
    Logic:
    1. Keep ALL fields from document
    2. Add/override with template values where template has keys
    3. Template values ALWAYS override document values
    4. For nested dicts: merge recursively
    5. For line_items: apply template to each item
    
    Args:
        document (dict): The base document (all fields preserved)
        template (dict): The template (overrides/adds where present)
    
    Returns:
        dict: Merged document with template applied
    """
    try:
        result = copy.deepcopy(document) if document else {}
        
        if not template:
            return result
        
        def merge_template(target: dict, template_dict: dict) -> dict:
            """
            Apply template to target.
            - All target keys are preserved
            - Template keys override/add to target
            """
            for key, template_value in template_dict.items():
                if key == "line_items" and isinstance(template_value, list):
                    # Special handling for line_items
                    # Apply template to each item in the list
                    if isinstance(target.get(key), list) and template_value and len(template_value) > 0:
                        line_template = template_value[0]
                        if isinstance(line_template, dict):
                            # Apply each template field to every line item (OVERRIDE)
                            for item in target[key]:
                                if isinstance(item, dict):
                                    for tkey, tval in line_template.items():
                                        item[tkey] = copy.deepcopy(tval)
                
                elif isinstance(template_value, dict):
                    # Nested dict handling
                    if key not in target:
                        # Key doesn't exist - add from template
                        target[key] = copy.deepcopy(template_value)
                    elif isinstance(target[key], dict):
                        # Both are dicts - merge recursively
                        merge_template(target[key], template_value)
                    else:
                        # Target value is not a dict, replace with template
                        target[key] = copy.deepcopy(template_value)
                
                else:
                    # Simple value - always use template value (override)
                    target[key] = copy.deepcopy(template_value)
            
            return target
        
        result = merge_template(result, template)
        return result
        
    except Exception as e:
        logger.error(f"✗ Error applying template: {type(e).__name__}: {e}")
        return copy.deepcopy(document) if document else {}
    



# if __name__ == "__main__":
#     # Debug/test code here
#     logger.info("✅ Document operations module loaded successfully")
#     logger.info(f"Python path: {sys.path[0]}")

#     import json
#     test_file = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'invoice_data_raw.json')
#     with open(test_file, 'r') as f:
#         test_data = json.load(f)

#     from ic_shared.configuration.defines import PEPPOL_DEFAULTS

#     print("********** TEST DATA **********")    
#     print(json.dumps(test_data, indent=2))  

#     print("********** PEPPOL DEFAULTS **********")  
#     print(json.dumps(PEPPOL_DEFAULTS, indent=2))  

#     template_applied_json = apply_peppol_json_template(test_data, PEPPOL_DEFAULTS)
#     print("********** MERGED WITH TEMPLATE **********")
#     print(json.dumps(template_applied_json, indent=2))   

#     # Validate: Check that all fields from test_data exist in merged
#     def check_all_keys_exist(original: dict, result: dict, path: str = "") -> bool:
#         """Recursively check that all keys from original exist in result"""
#         all_exist = True
#         for key, value in original.items():
#             current_path = f"{path}.{key}" if path else key
            
#             if key not in result:
#                 logger.error(f"❌ Missing key in merged: {current_path}")
#                 all_exist = False
#             elif isinstance(value, dict) and isinstance(result.get(key), dict):
#                 # Recurse for nested dicts
#                 if not check_all_keys_exist(value, result[key], current_path):
#                     all_exist = False
#             elif isinstance(value, list) and isinstance(result.get(key), list):
#                 # For lists, check structure but don't compare values
#                 if len(value) > 0 and isinstance(value[0], dict) and len(result[key]) > 0:
#                     if isinstance(result[key][0], dict):
#                         # Check first item structure
#                         if not check_all_keys_exist(value[0], result[key][0], f"{current_path}[0]"):
#                             all_exist = False
        
#         return all_exist
    
#     print("\n********** VALIDATION **********")
#     if check_all_keys_exist(test_data, template_applied_json):
#         logger.success("✅ All fields from test_data exist in merged")
#     else:
#         logger.error("❌ Some fields from test_data are missing in merged")

#     custom_file = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'custom_corrected.json')
#     with open(custom_file, 'r') as f:
#         custom_data  = json.load(f)

#     print("********** CUSTOM DATA **********")
#     print(json.dumps(custom_data, indent=2)) 

#     merged_custom_json = merge_peppol_json(template_applied_json, custom_data)
#     print("********** MERGED CUSTOM **********")
#     print(json.dumps(merged_custom_json, indent=2)) 


