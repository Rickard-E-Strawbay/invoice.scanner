"""PEPPOL Schema Manager V2 - handles loading and extracting fields from PEPPOL 3.0 XML schema."""

import os
import xml.etree.ElementTree as ET
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("PeppolManagerV2")


class PeppolManagerV2:
    """Manager for PEPPOL 3.0 XML schema operations."""
    
    # Class-level cache - loaded only once for all instances
    _cached_peppol_scheme = None
    _cached_all_fields = None
    _cached_mandatory_fields = None
    _cached_sections_order = None
    
    def __init__(self):
        """Initialize the manager - uses cached schema if already loaded."""
        if PeppolManagerV2._cached_peppol_scheme is None:
            PeppolManagerV2._cached_peppol_scheme = self._load_peppol_scheme()
        self._peppol_scheme = PeppolManagerV2._cached_peppol_scheme
    
    def _load_peppol_scheme(self) -> ET.Element:
        """Load PEPPOL 3.0 schema from XML file.
        
        Returns:
            ET.Element: Root element of the XML tree, None on error
        """
        try:
            # Get path to the XML file in ic_shared/utils/peppol
            utils_dir = os.path.dirname(__file__)
            schema_path = os.path.join(utils_dir, "peppol", "3_0_peppol.xml")
            
            tree = ET.parse(schema_path)
            root = tree.getroot()
        
            logger.success(f"✅ Loaded PEPPOL 3.0 XML schema from {schema_path}")
            return root
        except FileNotFoundError:
            logger.error(f"❌ PEPPOL schema file not found at {schema_path}")
            return None
        except ET.ParseError as e:
            logger.error(f"❌ Failed to parse PEPPOL schema XML: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading PEPPOL schema: {e}")
            return None
        
    def get_peppol_scheme(self) -> str:
        """Get the loaded PEPPOL schema as XML string.
        
        Returns:
            str: PEPPOL schema XML as string, empty string if not loaded
        """
        if self._peppol_scheme is None:
            return ""
        
        try:
            return ET.tostring(self._peppol_scheme, encoding='unicode', method='xml')
        except Exception as e:
            logger.error(f"❌ Error converting XML to string: {e}")
            return ""
    
    def get_peppol_scheme_element(self) -> ET.Element:
        """Get the loaded PEPPOL schema as XML Element.
        
        Returns:
            ET.Element: Root element of the PEPPOL schema
        """
        return self._peppol_scheme
    
    def get_mandatory_fields(self) -> dict:
        """Extract all mandatory (Obligation: required) fields from PEPPOL XML schema.
        Uses class-level cache to avoid repeated processing.
        
        Returns:
            dict: Dictionary with BT-ID -> field info mapping
        """
        # Return cached result if available
        if PeppolManagerV2._cached_mandatory_fields is not None:
            return PeppolManagerV2._cached_mandatory_fields
        
        mandatory_fields = {}
        
        try:
            if self._peppol_scheme is None:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return {}
            
            # Find all elements with BT-ID attribute
            for elem in self._peppol_scheme.iter():
                bt_id = elem.get("BT-ID")
                obligation = elem.get("Obligation")
                
                # Only include required fields
                if bt_id and obligation == "required":
                    mandatory_fields[bt_id] = {
                        "BT-ID": bt_id,
                        "Tag": elem.tag,
                        "Text": elem.text or "",
                        "Attributes": dict(elem.attrib),
                        "Description": elem.get("Description", ""),
                        "Type": elem.get("Type", ""),
                        "Example": elem.get("Example", ""),
                        "UBL-XPath": elem.get("UBL-XPath", ""),
                        "Obligation": obligation
                    }
            
            # Cache the result
            PeppolManagerV2._cached_mandatory_fields = mandatory_fields
            logger.success(f"✅ Extracted {len(mandatory_fields)} mandatory PEPPOL fields from XML")
            return mandatory_fields
            
        except Exception as e:
            logger.error(f"❌ Error extracting mandatory fields: {e}")
            return {}
    
    def get_all_fields(self, force_refresh=False) -> dict:
        """Extract ALL fields (mandatory and non-mandatory) from PEPPOL XML schema.
        Each field includes its obligation status. Uses class-level cache.
        
        Returns:
            dict: Dictionary with BT-ID -> field info mapping
        """
        # Return cached result if available
        if PeppolManagerV2._cached_all_fields is not None and not force_refresh:
            return PeppolManagerV2._cached_all_fields
        
        all_fields = {}
        
        try:
            if self._peppol_scheme is None:
                logger.warning("⚠️  PEPPOL scheme not loaded")
                return {}
            
            # Find all elements with BT-ID attribute
            for elem in self._peppol_scheme.iter():
                bt_id = elem.get("BT-ID")
                
                # Include all fields with BT-ID
                if bt_id:
                    obligation = elem.get("Obligation", "optional")
                    all_fields[bt_id] = {
                        "BT-ID": bt_id,
                        "Tag": elem.tag,
                        "Text": elem.text or "",
                        "Attributes": dict(elem.attrib),
                        "Description": elem.get("Description", ""),
                        "Type": elem.get("Type", ""),
                        "Example": elem.get("Example", ""),
                        "UBL-XPath": elem.get("UBL-XPath", ""),
                        "Obligation": obligation,
                        "map": elem.get("map")  # Include map attribute for extraction
                    }
            
            # Cache the result
            PeppolManagerV2._cached_all_fields = all_fields
            logger.success(f"✅ Extracted {len(all_fields)} total PEPPOL fields from XML")
            return all_fields
            
        except Exception as e:
            logger.error(f"❌ Error extracting all fields: {e}")
            return {}
    
    def find_fields_by_obligation(self, obligation: str) -> dict:
        """Find all fields with a specific obligation status.
        
        Args:
            obligation: "required", "optional", or "conditional"
        
        Returns:
            dict: Dictionary with BT-ID -> field info mapping
        """
        try:
            if self._peppol_scheme is None:
                return {}
            
            fields = {}
            for elem in self._peppol_scheme.iter():
                bt_id = elem.get("BT-ID")
                elem_obligation = elem.get("Obligation")
                
                if bt_id and elem_obligation == obligation:
                    fields[bt_id] = {
                        "BT-ID": bt_id,
                        "Tag": elem.tag,
                        "Text": elem.text or "",
                        "Description": elem.get("Description", ""),
                        "Obligation": elem_obligation
                    }
            
            logger.success(f"✅ Found {len(fields)} fields with obligation '{obligation}'")
            return fields
        except Exception as e:
            logger.error(f"❌ Error finding fields by obligation: {e}")
            return {}
    
    def find_field_by_bt_id(self, bt_id: str) -> dict:
        """Find a specific field by its BT-ID.
        
        Args:
            bt_id: The BT-ID to search for
        
        Returns:
            dict: Field info or empty dict if not found
        """
        try:
            if self._peppol_scheme is None:
                return {}
            
            for elem in self._peppol_scheme.iter():
                if elem.get("BT-ID") == bt_id:
                    return {
                        "BT-ID": bt_id,
                        "Tag": elem.tag,
                        "Text": elem.text or "",
                        "Attributes": dict(elem.attrib),
                        "Description": elem.get("Description", ""),
                        "Type": elem.get("Type", ""),
                        "Example": elem.get("Example", ""),
                        "UBL-XPath": elem.get("UBL-XPath", ""),
                        "Obligation": elem.get("Obligation", "optional")
                    }
            
            logger.warning(f"⚠️  Field with BT-ID '{bt_id}' not found")
            return {}
        except Exception as e:
            logger.error(f"❌ Error finding field: {e}")
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
        logger.success("✅ PEPPOL V2 cache cleared - will reload on next access")
