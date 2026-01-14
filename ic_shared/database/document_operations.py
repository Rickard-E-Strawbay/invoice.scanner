"""
Document operations - generic database functions for document management.

These functions are shared across API, Cloud Functions, and other services.
Uses fetch_all() for SELECT queries and execute_sql() for UPDATE/INSERT/DELETE.
"""

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
    

def merge_delta_into_existing(existing_data: dict, delta_data: dict) -> dict:
    """
    Deep merge delta into existing data structure.
    Delta values override existing values, but new keys are added while preserving existing ones.
    
    This is designed specifically for merging user corrections (delta) into existing data.
    - If delta has a key, it overrides existing (or adds if new)
    - If delta doesn't have a key, existing value is preserved
    - Works recursively for nested dicts
    
    Args:
        existing_data (dict): The existing data (base to merge into)
        delta_data (dict): The changes/corrections (merges into base)
    
    Returns:
        dict: Merged result with delta overriding existing values
    
    Example:
        existing = {"meta": {"ubl_version_id": "2.2"}}
        delta = {"meta": {"invoice_number": "00001"}}
        result = merge_delta_into_existing(existing, delta)
        # result = {"meta": {"ubl_version_id": "2.2", "invoice_number": "00001"}}
    """
    try:
        # Deep copy to avoid modifying originals
        result = copy.deepcopy(existing_data) if existing_data else {}
        
        # If delta is empty, return existing as-is
        if not delta_data:
            return result
        
        def deep_merge(base: dict, updates: dict) -> dict:
            """Recursively merge updates into base, with updates taking precedence."""
            for key, update_value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(update_value, dict):
                    # Both are dicts, merge recursively
                    base[key] = deep_merge(base[key], update_value)
                else:
                    # Override or add new key
                    base[key] = copy.deepcopy(update_value)
            
            return base
        
        result = deep_merge(result, delta_data)
        return result
        
    except Exception as e:
        logger.error(f"✗ Error merging delta: {type(e).__name__}: {e}")
        return copy.deepcopy(existing_data) if existing_data else {}
    

def merge_peppol_json(peppol_slave: dict, peppol_master: dict) -> dict:
    """
    Merge two Peppol JSON structures, preferring values from master over slave.
    
    This function creates a new merged document without modifying the originals.
    - Missing nodes from peppol_master are added to the result
    - Values in peppol_master override corresponding values in peppol_slave
    - Works recursively for nested dict structures
    
    Args:
        peppol_slave (dict): The primary document (typically user-corrected data)
        peppol_master (dict): The secondary document (typically LLM-extracted data)
    
    Returns:
        dict: A new merged document with values from both sources, 
              preferring master values where conflicts exist.
              Original documents are not modified.
    
    Example:
        slave = {"meta": {"invoice_number": "INV-001"}}
        master = {"meta": {"invoice_number": "INV-002", "currency": "SEK"}}
        result = merge_peppol_json(slave, master)
        # result = {"meta": {"invoice_number": "INV-002", "currency": "SEK"}}
    """
    try:
        # Create a deep copy of slave to avoid modifying the original
        merged = copy.deepcopy(peppol_slave) if peppol_slave else {}
        
        # If master is empty or None, return the copy of slave
        if not peppol_master:
            return merged
        
        # Recursive merge function
        def recursive_merge(target: dict, source: dict) -> dict:
            """
            Recursively merge source values into target.
            Source values override target values.
            Handles arrays specially: merges array defaults to all items.
            """
            for key, source_value in source.items():
                if key not in target:
                    # Key doesn't exist in target, add it from source
                    target[key] = copy.deepcopy(source_value)
                elif isinstance(source_value, list) and isinstance(target.get(key), list):
                    # Both are arrays - special handling for line_items
                    if key == "line_items" and source_value and len(source_value) > 0:
                        # Check if source items have different structure (actual items vs template)
                        # If source has multiple items or items with different content, treat as actual items
                        source_is_template = len(source_value) == 1
                        
                        if source_is_template:
                            # Single item: treat as template and merge into each target item
                            source_template = source_value[0]
                            if isinstance(source_template, dict):
                                # Merge source template into each target item
                                for i in range(len(target[key])):
                                    if isinstance(target[key][i], dict):
                                        # Recursively merge template values into each line item
                                        target[key][i] = recursive_merge(target[key][i], source_template)
                        else:
                            # Multiple items: treat as actual line items and merge by index
                            # Match source items to target items by index
                            for i in range(len(source_value)):
                                if i < len(target[key]):
                                    # Merge source item into existing target item
                                    if isinstance(target[key][i], dict) and isinstance(source_value[i], dict):
                                        target[key][i] = recursive_merge(target[key][i], source_value[i])
                                else:
                                    # Source has more items than target, add them
                                    target[key].append(copy.deepcopy(source_value[i]))
                    else:
                        # For other arrays, use source value
                        target[key] = copy.deepcopy(source_value)
                elif isinstance(source_value, dict) and isinstance(target.get(key), dict):
                    # Both are dicts, merge recursively
                    target[key] = recursive_merge(target[key], source_value)
                elif source_value is not None and source_value != "":
                    # Source has a non-empty value, use it (override target)
                    target[key] = copy.deepcopy(source_value)
            
            return target
        
        # Perform the merge
        merged = recursive_merge(merged, peppol_master)
        
        # Validate tax_scheme in line_items
        if "line_items" in merged and isinstance(merged["line_items"], list):
            # Get line_item template from source (master) for applying to missing items
            line_item_template = None
            if isinstance(peppol_master, dict) and "line_items" in peppol_master and isinstance(peppol_master["line_items"], list) and len(peppol_master["line_items"]) > 0:
                if isinstance(peppol_master["line_items"][0], dict):
                    line_item_template = peppol_master["line_items"][0]
            
            for i, item in enumerate(merged["line_items"]):
                if isinstance(item, dict):
                    if "tax_scheme" not in item or not item.get("tax_scheme"):
                        # Apply template fields to this item
                        if line_item_template:
                            for template_key, template_val in line_item_template.items():
                                if template_key not in item:
                                    item[template_key] = copy.deepcopy(template_val)
        
        return merged
        
    except Exception as e:
        logger.error(f"✗ Error merging Peppol JSON: {type(e).__name__}: {e}")
        # On error, return a deep copy of slave to avoid data loss
        return copy.deepcopy(peppol_slave) if peppol_slave else {}


def apply_peppol_json_template(document: dict, template: dict) -> dict:
    """
    Apply a PEPPOL template to a document, filling in missing fields with template defaults.
    
    Unlike merge_peppol_json which is for merging two complete documents,
    this function applies a template structure to a document:
    - Missing top-level fields are added from template
    - For line_items: template is applied to ALL existing items (not just matched by index)
    - Existing values in document are NEVER overwritten by template
    - Template provides structure and defaults only
    
    Args:
        document (dict): The document to apply template to (e.g., invoice data from LLM)
        template (dict): The template with default structure and values (e.g., PEPPOL_DEFAULTS)
    
    Returns:
        dict: A new document with template defaults applied. Original documents not modified.
    
    Example:
        document = {"meta": {"invoice_number": "INV-001"}, "line_items": [{"quantity": "5"}]}
        template = {"meta": {"currency": "SEK"}, "line_items": [{"tax_rate": "0.25"}]}
        result = apply_peppol_json_template(document, template)
        # result = {
        #     "meta": {"invoice_number": "INV-001", "currency": "SEK"},
        #     "line_items": [{"quantity": "5", "tax_rate": "0.25"}]
        # }
    """
    try:
        # Create a deep copy of document to avoid modifying the original
        result = copy.deepcopy(document) if document else {}
        
        # If template is empty, return document as-is
        if not template:
            return result
        
        # Recursive function to apply template
        def apply_template(target: dict, source_template: dict) -> dict:
            """
            Recursively apply template values to target.
            Only adds missing fields; never overwrites existing values.
            For line_items, applies template to all items (not just one).
            """
            for key, template_value in source_template.items():
                if key not in target:
                    # Key doesn't exist in target, add it from template
                    target[key] = copy.deepcopy(template_value)
                
                elif key == "line_items" and isinstance(template_value, list) and isinstance(target.get(key), list):
                    # Special case: apply template to all line items
                    if template_value and len(template_value) > 0:
                        # Get the template for line items (first item)
                        line_item_template = template_value[0]
                        if isinstance(line_item_template, dict):
                            # Apply this template to ALL items in target's line_items
                            for i in range(len(target[key])):
                                if isinstance(target[key][i], dict):
                                    # For each line item, explicitly apply all template fields
                                    for template_key, template_val in line_item_template.items():
                                        if template_key not in target[key][i]:
                                            target[key][i][template_key] = copy.deepcopy(template_val)
                
                elif isinstance(template_value, dict) and isinstance(target.get(key), dict):
                    # Both are dicts, recursively apply template
                    target[key] = apply_template(target[key], template_value)
                # else: target has a value and it's not a dict/list, don't overwrite
            
            return target
        
        # Apply the template
        result = apply_template(result, template)
        return result
        
    except Exception as e:
        logger.error(f"✗ Error applying template: {type(e).__name__}: {e}")
        # On error, return a deep copy of document to avoid data loss
        return copy.deepcopy(document) if document else {}