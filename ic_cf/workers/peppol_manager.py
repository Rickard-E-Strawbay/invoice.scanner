"""PEPPOL Schema Manager - handles loading and extracting mandatory fields from PEPPOL 3.0 schema."""

import json
import os
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("PeppolManager")


class PeppolManager:
    """Manager for PEPPOL 3.0 schema operations."""
    
    def __init__(self):
        """Initialize the manager by loading PEPPOL scheme."""
        self._peppol_scheme = self._load_peppol_scheme()
    
    def _load_peppol_scheme(self) -> dict:
        """Load PEPPOL 3.0 schema from JSON file.
        
        Returns:
            dict: Loaded PEPPOL schema, empty dict on error
        """
        try:
            # Get path to the JSON file in ic_shared/utils
            import ic_shared.utils as utils_module
            utils_dir = os.path.dirname(utils_module.__file__)
            schema_path = os.path.join(utils_dir, "3_0_peppol.json")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                peppol_scheme = json.load(f)
        
            logger.success(f"✅ Loaded PEPPOL 3.0 schema from {schema_path}")
            return peppol_scheme
        except FileNotFoundError:
            logger.error(f"❌ PEPPOL schema file not found at {schema_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse PEPPOL schema JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading PEPPOL schema: {e}")
            return {}
    
    def get_mandatory_fields(self) -> dict:
        """Extract all mandatory (Obligation: required) fields from PEPPOL schema.
        
        Returns:
            dict: Dictionary with structure {'fieldname': {'BT-ID': 'BT-5', 'Description': '...', ...}}
        """
        mandatory_fields = {}
        
        def extract_mandatory_recursive(obj, path=""):
            """Recursively extract mandatory fields from schema."""
            if isinstance(obj, dict):
                # Check if this object has Obligation field
                obligation = obj.get("Obligation")
                bt_id = obj.get("BT-ID")
                
                if obligation == "required":
                    field_name = path.split(".")[-1] if path else "root"
                    mandatory_fields[field_name] = {
                        "BT-ID": bt_id,
                        "Description": obj.get("Description", ""),
                        "Type": obj.get("Type", ""),
                        "Example": obj.get("Example", ""),
                        "UBL-XPath": obj.get("UBL-XPath", ""),
                        "Obligation": "required"
                    }
                
                # Recurse into nested Properties
                properties = obj.get("Properties", {})
                for key, value in properties.items():
                    new_path = f"{path}.{key}" if path else key
                    extract_mandatory_recursive(value, new_path)
            
            elif isinstance(obj, list):
                # Handle arrays
                for item in obj:
                    extract_mandatory_recursive(item, path)
        
        try:
            # Check that self._peppol_scheme is loaded
            if not self._peppol_scheme:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return {}
            
            logger.info(f"📊 Processing PEPPOL scheme to extract mandatory fields")
            
            # Start extraction from self._peppol_scheme
            extract_mandatory_recursive(self._peppol_scheme)
            
            logger.success(f"✅ Extracted {len(mandatory_fields)} mandatory PEPPOL fields")
            return mandatory_fields
            
        except Exception as e:
            logger.error(f"❌ Error extracting mandatory fields: {e}")
            return {}
