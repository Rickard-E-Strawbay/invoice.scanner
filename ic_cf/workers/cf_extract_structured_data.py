import json
import os
import re
import requests
from workers.cf_base import cf_base
from ic_shared.utils.peppol_manager import PeppolManager
from ic_shared.database.connection import fetch_all, execute_sql
from ic_shared.database.document_operations import apply_peppol_json_template

from ic_shared.configuration.defines import ENTER, EXIT, ERROR
from ic_shared.configuration.defines import EXTRACTION_STATUS, PEPPOL_DEFAULTS
from ic_shared.logging import ComponentLogger

logger = ComponentLogger("cf_extract_structured_data")

class cf_extract_structured_data(cf_base):
    """Cloud Function entry point for structured data extraction worker."""
    
    def __init__(self, cloud_event):
        super().__init__(cloud_event, "cf_extract_structured_data")
        self._peppol_manager = PeppolManager()
    
    def execute(self):
        """Execute the structured data extraction worker logic."""
        ENTER_STATUS = EXTRACTION_STATUS[ENTER]
        EXIT_STATUS = EXTRACTION_STATUS[EXIT]
        ERROR_STATUS = EXTRACTION_STATUS[ERROR]
        # FAIL_STATUS = EXTRACTION_STATUS[FAIL]

        self._update_document_status(ENTER_STATUS)

        # Map raw invoice data to structured PEPPOL data
        try:

            dict_full_data = self._load_document_data()
            peppol_str = dict_full_data.get("invoice_data_raw")
            invoice_data_peppol = json.loads(peppol_str) if isinstance(peppol_str, str) else (peppol_str or {})

            print("**************************************")
            print(invoice_data_peppol)
            print("**************************************")

            


            # Merge PEPPOL defaults with nested structure - defaults fill missing values
            invoice_data_peppol = apply_peppol_json_template(invoice_data_peppol, PEPPOL_DEFAULTS)

            # Verify that values added from PEPPOL_DEFAULTS are present and correct
            # self._validate_peppol_defaults_applied(invoice_data_peppol, PEPPOL_DEFAULTS)
            

            # Save extracted and post predict adjusted PEPPOL data to database
            invoice_data_peppol = json.dumps(invoice_data_peppol)
            
            print("**************************************")
            print(invoice_data_peppol)
            print("**************************************")


            dict_additional_fields = {}
            dict_additional_fields["invoice_data_peppol"] = invoice_data_peppol
            dict_additional_fields["invoice_data_user_corrected"] = "{}"
            dict_additional_fields["invoice_data_peppol_final"] = invoice_data_peppol

            self._update_document_status(EXIT_STATUS, None, dict_additional_fields)


            
            self._publish_to_topic()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to map/save PEPPOL data: {str(e)}")
            self._update_document_status(ERROR_STATUS)
            raise

        self._update_document_status(EXIT_STATUS)

    def _map_to_peppol(self) -> dict:
        """Map raw invoice data to PEPPOL structure using the map attribute."""
        
        # 1. Get raw invoice data from database
        sql = "SELECT invoice_data_raw FROM documents WHERE id = %s"
        results, success = fetch_all(sql, (str(self.document_id),))

        print("invoice_data_raw:", results)
        
        if not success or not results:
            raise ValueError(f"Document not found: {self.document_id}")
        
        raw_data = results[0].get("invoice_data_raw")
        if not raw_data:
            raise ValueError(f"No raw invoice data found for document: {self.document_id}")
        
        # Parse JSON if it's a string
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        # print(raw_data)
        
        self.logger.info(f"Processing raw invoice data with keys: {list(raw_data.keys())}")
        
        # 2. Get all PEPPOL fields with their map attributes
        all_fields = self._peppol_manager.get_all_fields()

        for section_name, section_fields in all_fields.items():
            for field_name, field_info in section_fields.items():
                map_path = field_info.get("map")

        
        # 3. Create PEPPOL output structure organized by section
        peppol_data = {}
        
        for section_name, section_fields in all_fields.items():
            peppol_data[section_name] = {}
            
            for field_name, field_info in section_fields.items():
                map_path = field_info.get("map")
                
                if not map_path:
                    continue  # Skip fields without mapping
                
                # Extract value from raw_data using the map path
                value = self._extract_value_from_raw_data(raw_data, map_path)
                
                if value is not None:
                    peppol_data[section_name][field_name] = value
                    self.logger.info(f"✓ Mapped {section_name}.{field_name}: {map_path} = {value}")
                else:
                    self.logger.debug(f"✗ No value found for {section_name}.{field_name} at path: {map_path}")
        
        return peppol_data
    
    def _validate_peppol_defaults_applied(self, peppol_data: dict, defaults: dict):
        """Validate that PEPPOL defaults have been correctly applied to peppol_data.
        
        Checks that all fields from defaults are present in peppol_data with correct values.
        Logs any missing or mismatched values for debugging.
        """
        missing_defaults = []
        mismatched_defaults = []
        
        for section_key, section_defaults in defaults.items():
            if section_key not in peppol_data:
                missing_defaults.append(f"{section_key} (entire section missing)")
                continue
            
            if isinstance(section_defaults, dict):
                for field_key, default_value in section_defaults.items():
                    if field_key not in peppol_data[section_key]:
                        missing_defaults.append(f"{section_key}.{field_key}")
                    elif peppol_data[section_key][field_key] != default_value:
                        # Only report if was empty and now has a value (expected behavior)
                        if peppol_data[section_key][field_key]:
                            mismatched_defaults.append(
                                f"{section_key}.{field_key}: expected {default_value}, "
                                f"got {peppol_data[section_key][field_key]}"
                            )
        
        if missing_defaults:
            self.logger.warning(f"⚠️  Missing default fields: {', '.join(missing_defaults)}")
        
        if mismatched_defaults:
            self.logger.warning(f"⚠️  Mismatched default values: {', '.join(mismatched_defaults)}")
        
        if not missing_defaults and not mismatched_defaults:
            self.logger.success("✅ All PEPPOL defaults correctly applied")
    
    def _extract_value_from_raw_data(self, data: dict, path: str):
        """Extract value from nested dict using dot notation and array syntax.
        
        Examples:
            - "debtor.name" → data["debtor"]["name"]
            - "articleRows[].description" → [row["description"] for row in data["articleRows"]]
            - "vats[].percentage" → [vat["percentage"] for vat in data["vats"]]
        """
        
        if path == "calculated_from_articleRows":
            # Calculate sum of exclVAT from article rows
            if "articleRows" in data and isinstance(data["articleRows"], list):
                return sum(self._parse_float(row.get("exclVAT", 0) or 0) for row in data["articleRows"])
            return None
        
        # Check if path contains array notation
        if "[]" in path:
            base_path, remaining = path.split("[].", 1)
            obj = self._get_nested_value(data, base_path)
            
            if isinstance(obj, list):
                # Extract from each array element
                results = []
                for item in obj:
                    val = self._get_nested_value(item, remaining)
                    if val is not None:
                        results.append(val)
                return results if results else None
            return None
        
        # Regular nested path (dot notation)
        return self._get_nested_value(data, path)
    
    def _parse_float(self, value):
        """Parse float value, handling both comma and point as decimal separator.
        
        Examples:
            - "145.01" → 145.01
            - "145,01" → 145.01
            - 145 → 145.0
        """
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Replace comma with point for European format
            normalized = value.replace(",", ".")
            try:
                return float(normalized)
            except ValueError:
                self.logger.warning(f"⚠️  Could not parse float value: {value}")
                return 0.0
        
        return 0.0
    
    def _get_nested_value(self, obj: dict, path: str):
        """Get value from nested dict using dot notation."""
        keys = path.split(".")
        current = obj
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None
        
        return current
    
    def _merge_defaults_into_peppol(self, peppol_data: dict, defaults: dict):
        """Merge nested PEPPOL defaults into peppol_data.
        
        Defaults fill in missing or empty values - they don't override existing LLM predictions.
        Works recursively for nested structures matching invoice_template.json format.
        """
        for section_key, section_value in defaults.items():
            # If section doesn't exist in peppol_data, create it
            if section_key not in peppol_data:
                peppol_data[section_key] = {}
            
            # If default value is a dict, merge nested structure
            if isinstance(section_value, dict):
                for field_key, default_field_value in section_value.items():
                    # Set if field doesn't exist OR if field is empty/falsy
                    if field_key not in peppol_data[section_key] or not peppol_data[section_key][field_key]:
                        peppol_data[section_key][field_key] = default_field_value
            else:
                # For non-dict values, only set if section was empty
                if not peppol_data[section_key]:
                    peppol_data[section_key] = section_value

    def _save_to_peppol(self, peppol_data: dict):
        """Save auto-mapped PEPPOL data to invoice_data_peppol."""
        peppol_json = json.dumps(peppol_data)
        
        sql = """
            UPDATE documents 
            SET invoice_data_peppol = %s 
            WHERE id = %s
        """
        
        results, success = execute_sql(sql, (peppol_json, str(self.document_id)))
        
        if not success:
            raise ValueError(f"Failed to save PEPPOL data for document: {self.document_id}")
    
    def _save_to_peppol_final(self, peppol_data: dict):
        """Save final PEPPOL data (after user corrections) to invoice_data_peppol_final."""
        peppol_json = json.dumps(peppol_data)
        
        sql = """
            UPDATE documents 
            SET invoice_data_peppol_final = %s 
            WHERE id = %s
        """
        
        results, success = execute_sql(sql, (peppol_json, str(self.document_id)))
        
        if not success:
            raise ValueError(f"Failed to save final PEPPOL data for document: {self.document_id}")
    
    def _get_peppol_final_data(self) -> dict:
        """Fetch invoice_data_peppol_final from database (user-corrected data)."""
        sql = "SELECT invoice_data_peppol_final FROM documents WHERE id = %s"
        results, success = fetch_all(sql, (str(self.document_id),))
        
        if not success or not results:
            return None
        
        final_data = results[0].get("invoice_data_peppol_final")
        if not final_data:
            return None
        
        # Parse JSON if it's a string
        if isinstance(final_data, str):
            try:
                return json.loads(final_data)
            except json.JSONDecodeError:
                self.logger.warning("Invalid JSON in invoice_data_peppol_final, skipping merge")
                return None
        
        return final_data
    
    def _merge_peppol_with_final(self, peppol_data: dict, peppol_final: dict) -> dict:
        """Merge peppol_data with peppol_final, where peppol_final takes precedence.
        
        peppol_final values override peppol_data values for each field.
        If a field exists in peppol_final, it replaces the one in peppol_data.
        New sections/fields from peppol_final are added.
        """
        # Deep copy to avoid modifying the original
        merged = json.loads(json.dumps(peppol_data))
        
        # Iterate through final data and update/add to merged
        for section_name, section_fields in peppol_final.items():
            if section_name not in merged:
                merged[section_name] = {}
            
            # Update section with final data (final takes precedence)
            merged[section_name].update(section_fields)
        
        self.logger.info(f"Merged PEPPOL data: {len(merged)} sections, final overrides applied")
        return merged

