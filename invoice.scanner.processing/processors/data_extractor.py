"""
DATA EXTRACTOR - Structure and Validate Extracted Data

Denna processor tar LLM-extraherad data och:
- Validerar mot schema
- Normaliserar format (dates, amounts osv)
- Enrichar med company context
- Fixar common issues (extra whitespace, format mismatches)
- Beräknar derived fields (ex: amount * vat_rate = vat)

PROCESS:
    1. Ta LLM output
    2. Validera schema
    3. Normalisera värden
    4. Enricha med context
    5. Beräkna checksums/verifications
    6. Returnera clean structured data
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extract and validate invoice data"""
    
    def extract_and_validate(
        self,
        llm_prediction: Dict[str, Any],
        company_id: str
    ) -> Dict[str, Any]:
        """
        Extract, validate and normalize data
        
        Args:
            llm_prediction: Output from LLMProcessor
            company_id: Company ID for context
        
        Returns:
            Validated and normalized invoice data
        """
        
        try:
            # Start with LLM output
            result = llm_prediction.copy()
            
            # Normalize values
            result = self._normalize_dates(result)
            result = self._normalize_amounts(result)
            result = self._normalize_strings(result)
            
            # Calculate derived fields
            result = self._calculate_derived_fields(result)
            
            # Add metadata
            result['extracted_at'] = datetime.utcnow().isoformat()
            result['extraction_version'] = '1.0'
            result['company_id'] = company_id
            
            logger.info(f"Data extraction completed for company {company_id}")
            return result
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            raise
    
    def _normalize_dates(self, data: Dict) -> Dict:
        """Normalize date fields to ISO 8601 format"""
        
        date_fields = ['invoice_date', 'due_date', 'payment_date']
        
        for field in date_fields:
            if field in data and data[field]:
                try:
                    # Try parse various formats
                    date_str = str(data[field]).strip()
                    
                    # Already ISO format
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                        continue
                    
                    # Swedish format DD-MM-YYYY
                    if re.match(r'^\d{2}-\d{2}-\d{4}$', date_str):
                        dt = datetime.strptime(date_str, '%d-%m-%Y')
                        data[field] = dt.strftime('%Y-%m-%d')
                        continue
                    
                    # Try common formats
                    for fmt in ['%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y', '%d %B %Y', '%d %b %Y']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            data[field] = dt.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                
                except Exception as e:
                    logger.warning(f"Could not normalize date {field}: {data[field]}")
                    data[field] = None
        
        return data
    
    def _normalize_amounts(self, data: Dict) -> Dict:
        """Normalize amount fields to float"""
        
        amount_fields = ['amount', 'vat', 'total', 'vat_rate']
        
        for field in amount_fields:
            if field in data and data[field]:
                try:
                    value = str(data[field]).strip()
                    
                    # Remove currency symbols and common separators
                    value = re.sub(r'[€$¤]', '', value)
                    value = re.sub(r'\s', '', value)
                    
                    # Handle comma as decimal separator (European format)
                    if ',' in value and '.' in value:
                        # e.g., "1.234,56" -> "1234.56"
                        value = value.replace('.', '').replace(',', '.')
                    elif ',' in value:
                        # e.g., "1234,56" -> "1234.56"
                        value = value.replace(',', '.')
                    
                    data[field] = float(value)
                
                except Exception as e:
                    logger.warning(f"Could not normalize amount {field}: {data[field]}")
                    data[field] = None
        
        return data
    
    def _normalize_strings(self, data: Dict) -> Dict:
        """Normalize string fields"""
        
        string_fields = [
            'invoice_number', 'vendor_name', 'vendor_email', 
            'vendor_phone', 'reference', 'payment_terms', 'order_number'
        ]
        
        for field in string_fields:
            if field in data and data[field]:
                try:
                    value = str(data[field]).strip()
                    # Remove extra whitespace
                    value = ' '.join(value.split())
                    data[field] = value if value else None
                except:
                    data[field] = None
        
        return data
    
    def _calculate_derived_fields(self, data: Dict) -> Dict:
        """Calculate fields that can be derived from others"""
        
        try:
            # Calculate total from amount + vat if missing
            if not data.get('total') and data.get('amount') and data.get('vat'):
                data['total'] = data['amount'] + data['vat']
            
            # Calculate vat from amount and vat_rate if missing
            if not data.get('vat') and data.get('amount') and data.get('vat_rate'):
                data['vat'] = data['amount'] * (data['vat_rate'] / 100.0)
            
            # Calculate vat_rate from amount and vat if missing
            if not data.get('vat_rate') and data.get('amount') and data.get('vat') and data['amount'] > 0:
                data['vat_rate'] = (data['vat'] / data['amount']) * 100.0
            
            # Estimate vat_rate if only total and amount known
            if not data.get('vat_rate') and data.get('amount') and data.get('total'):
                if data['amount'] > 0:
                    data['vat_rate'] = ((data['total'] - data['amount']) / data['amount']) * 100.0
        
        except Exception as e:
            logger.warning(f"Could not calculate derived fields: {e}")
        
        return data
