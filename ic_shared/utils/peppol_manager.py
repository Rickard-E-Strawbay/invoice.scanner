"""PEPPOL Schema Manager - handles loading and extracting mandatory fields from PEPPOL 3.0 schema."""

import json
import os
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("PeppolManager")


class PeppolManager:
    """Manager for PEPPOL 3.0 schema operations."""
    
    # Class-level cache - loaded only once for all instances
    _cached_peppol_scheme = None
    _cached_all_fields = None
    _cached_mandatory_fields = None
    _cached_sections_order = None
    
    def __init__(self):
        """Initialize the manager - uses cached schema if already loaded."""
        if PeppolManager._cached_peppol_scheme is None:
            PeppolManager._cached_peppol_scheme = self._load_peppol_scheme()
        self._peppol_scheme = PeppolManager._cached_peppol_scheme
    
    def _load_peppol_scheme(self) -> dict:
        """Load PEPPOL 3.0 schema from JSON file.
        
        Returns:
            dict: Loaded PEPPOL schema, empty dict on error
        """
        try:
            # Get path to the JSON file in ic_shared/utils
            utils_dir = os.path.dirname(__file__)
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
        
    def get_peppol_scheme(self) -> dict:
        """Get the loaded PEPPOL schema.
        
        Returns:
            dict: PEPPOL schema
        """
        return self._peppol_scheme  
    
    def get_mandatory_fields(self) -> dict:
        """Extract all mandatory (Obligation: required) fields from PEPPOL schema, grouped by section.
        Uses class-level cache to avoid repeated processing.
        
        Returns:
            dict: Dictionary with structure {'Header': {'fieldname': {...}}, 'Seller': {...}, ...}
        """
        # Return cached result if available
        if PeppolManager._cached_mandatory_fields is not None:
            return PeppolManager._cached_mandatory_fields
        
        grouped_fields = {}
        
        try:
            # Check that self._peppol_scheme is loaded
            if not self._peppol_scheme:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return {}
            
            # Navigate to PeppolInvoice.Properties to find sections
            peppol_invoice = self._peppol_scheme.get("Properties", {}).get("PeppolInvoice", {})
            sections = peppol_invoice.get("Properties", {})
            
            total_fields = 0
            
            # Process each section
            for section_name, section_obj in sections.items():
                if isinstance(section_obj, dict):
                    section_props = section_obj.get("Properties", {})
                    
                    section_fields = {}
                    
                    # Extract mandatory fields from this section
                    for field_name, field_obj in section_props.items():
                        if isinstance(field_obj, dict):
                            obligation = field_obj.get("Obligation")
                            
                            # Only include required fields
                            if obligation == "required":
                                bt_id = field_obj.get("BT-ID")
                                section_fields[field_name] = {
                                    "BT-ID": bt_id,
                                    "Description": field_obj.get("Description", ""),
                                    "Type": field_obj.get("Type", ""),
                                    "Example": field_obj.get("Example", ""),
                                    "UBL-XPath": field_obj.get("UBL-XPath", ""),
                                    "Obligation": "required"
                                }
                    
                    # Add section to grouped_fields even if it has no mandatory fields
                    grouped_fields[section_name] = section_fields
                    total_fields += len(section_fields)
            
            # Cache the result
            PeppolManager._cached_mandatory_fields = grouped_fields
            logger.success(f"✅ Extracted {total_fields} mandatory PEPPOL fields in {len(grouped_fields)} sections (including empty sections)")
            return grouped_fields
            
        except Exception as e:
            logger.error(f"❌ Error extracting mandatory fields: {e}")
            return {}
    
    def get_sections_order(self) -> list:
        """Get the exact order of sections from the PEPPOL JSON document (Properties/PeppolInvoice/Properties).
        Uses class-level cache to avoid repeated processing.
        
        Returns:
            list: List of section names in document order
        """
        # Return cached result if available
        if PeppolManager._cached_sections_order is not None:
            return PeppolManager._cached_sections_order
        
        try:
            if not self._peppol_scheme:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return []
            
            peppol_invoice = self._peppol_scheme.get("Properties", {}).get("PeppolInvoice", {})
            sections = peppol_invoice.get("Properties", {})
            
            # Return keys in their original order (preserved in modern Python dicts)
            sections_order = list(sections.keys())
            
            # Cache the result
            PeppolManager._cached_sections_order = sections_order
            return sections_order
            
        except Exception as e:
            logger.error(f"❌ Error retrieving sections order: {e}")
            return []    
        
    def get_all_fields(self, force_refresh=False) -> dict:
        """Extract ALL fields (mandatory and non-mandatory) from PEPPOL schema, grouped by section.
        Each field includes its obligation status. Uses class-level cache.
        
        Returns:
            dict: Dictionary with structure {'Header': {'fieldname': {..., 'Obligation': 'required'}}, ...}
        """
        # Return cached result if available
        if PeppolManager._cached_all_fields is not None and not force_refresh:
            return PeppolManager._cached_all_fields
        
        grouped_fields = {}
        
        try:
            if not self._peppol_scheme:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return {}
            
            # Navigate to PeppolInvoice.Properties to find sections
            peppol_invoice = self._peppol_scheme.get("Properties", {}).get("PeppolInvoice", {})
            sections = peppol_invoice.get("Properties", {})
            
            total_fields = 0
            
            # Process each section
            for section_name, section_obj in sections.items():
                if isinstance(section_obj, dict):
                    section_props = section_obj.get("Properties", {})
                    
                    section_fields = {}
                    
                    # Extract ALL fields from this section (both mandatory and non-mandatory)
                    for field_name, field_obj in section_props.items():
                        if isinstance(field_obj, dict):
                            obligation = field_obj.get("Obligation", "optional")  # Default to optional if not specified
                            bt_id = field_obj.get("BT-ID")
                            section_fields[field_name] = {
                                "BT-ID": bt_id,
                                "Description": field_obj.get("Description", ""),
                                "Type": field_obj.get("Type", ""),
                                "Example": field_obj.get("Example", ""),
                                "UBL-XPath": field_obj.get("UBL-XPath", ""),
                                "Obligation": obligation,
                                "map": field_obj.get("map")  # Include map attribute for extraction
                            }
                    
                    # Add section to grouped_fields even if it has no fields
                    grouped_fields[section_name] = section_fields
                    total_fields += len(section_fields)
            
            # Cache the result
            PeppolManager._cached_all_fields = grouped_fields
            return grouped_fields
            
        except Exception as e:
            logger.error(f"❌ Error extracting all fields: {e}")
            return {}
    
    @classmethod
    def reset_cache(cls):
        """Reset the class-level cache - forces complete reload on next instantiation.
        
        Useful for:
        - Testing with updated schema files
        - Forcing refresh without restarting the application
        - Debugging cache issues
        """
        cls._cached_peppol_scheme = None
        cls._cached_all_fields = None
        cls._cached_mandatory_fields = None
        cls._cached_sections_order = None
        logger.success("✅ PEPPOL cache cleared - will reload on next access")