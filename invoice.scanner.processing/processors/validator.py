"""
VALIDATOR - Quality Check and Automated Evaluation

Denna processor validerar extraherad data och bestämmer
om dokumentet är ready för export eller behöver manual review.

EVALUATION CRITERIA:
    Excellent (0.95-1.0):
    - Confidence > 0.95
    - Alle required fields filled
    - Data är konsistent

    Good (0.85-0.95):
    - Confidence > 0.85
    - Alla critical fields filled
    - Minor issues (ex: missing vendor email)

    Fair (0.70-0.85):
    - Confidence > 0.70
    - Några fields missing
    - Needs manual review

    Poor (<0.70):
    - Low confidence
    - Multiple missing fields
    - Definite manual review needed
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Validator:
    """Validate and evaluate extracted invoice data"""
    
    # Required fields for valid invoice
    REQUIRED_FIELDS = [
        'invoice_number',
        'invoice_date',
        'total'
    ]
    
    # Critical fields for automatic approval
    CRITICAL_FIELDS = [
        'invoice_number',
        'invoice_date',
        'vendor_name',
        'total',
        'currency'
    ]
    
    def evaluate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate extracted data and assign quality score
        
        Args:
            extracted_data: Data from DataExtractor
        
        Returns:
            {
                'quality_score': 0.92,
                'status': 'approved' eller 'manual_review',
                'recommendation': 'auto_export',
                'issues': [],
                'warnings': [],
                'missing_fields': ['vendor_email'],
                'validation_details': {...}
            }
        """
        
        issues = []
        warnings = []
        missing_fields = []
        
        try:
            # 1. Check required fields
            for field in self.REQUIRED_FIELDS:
                if not extracted_data.get(field):
                    missing_fields.append(field)
                    issues.append(f"Missing required field: {field}")
            
            # 2. Check data consistency
            consistency_issues = self._check_consistency(extracted_data)
            issues.extend(consistency_issues)
            
            # 3. Check for common errors
            error_checks = self._check_common_errors(extracted_data)
            issues.extend(error_checks['issues'])
            warnings.extend(error_checks['warnings'])
            
            # 4. Calculate quality score
            confidence = extracted_data.get('confidence', 0.0)
            quality_score = self._calculate_quality_score(
                confidence,
                len(missing_fields),
                len(issues)
            )
            
            # 5. Determine recommendation
            recommendation = self._determine_recommendation(
                quality_score,
                missing_fields,
                issues
            )
            
            # 6. Determine status
            if recommendation == 'auto_export':
                status = 'approved'
            elif recommendation == 'manual_review':
                status = 'manual_review'
            else:
                status = 'manual_review'
            
            return {
                'quality_score': quality_score,
                'status': status,
                'recommendation': recommendation,
                'issues': issues,
                'warnings': warnings,
                'missing_fields': missing_fields,
                'validation_details': {
                    'required_fields_filled': len(self.REQUIRED_FIELDS) - len([f for f in self.REQUIRED_FIELDS if f in missing_fields]),
                    'critical_fields_filled': sum(1 for f in self.CRITICAL_FIELDS if extracted_data.get(f)),
                    'confidence_score': confidence,
                    'data_consistency': consistency_issues == [],
                    'evaluated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'quality_score': 0.0,
                'status': 'manual_review',
                'recommendation': 'manual_review',
                'issues': [f"Validation error: {str(e)}"],
                'warnings': [],
                'missing_fields': missing_fields,
                'validation_details': {'error': str(e)}
            }
    
    def _check_consistency(self, data: Dict) -> list:
        """Check data consistency"""
        issues = []
        
        try:
            # Amount consistency
            if data.get('amount') and data.get('vat') and data.get('total'):
                expected_total = data['amount'] + data['vat']
                if abs(expected_total - data['total']) > 0.01:  # 1 cent tolerance
                    issues.append(f"Amount inconsistency: {data['amount']} + {data['vat']} ≠ {data['total']}")
            
            # VAT rate consistency
            if data.get('vat_rate'):
                if data['vat_rate'] < 0 or data['vat_rate'] > 100:
                    issues.append(f"Invalid VAT rate: {data['vat_rate']}%")
            
            # Date logic
            if data.get('invoice_date') and data.get('due_date'):
                try:
                    from datetime import datetime
                    inv_date = datetime.fromisoformat(data['invoice_date'])
                    due_date = datetime.fromisoformat(data['due_date'])
                    
                    if due_date < inv_date:
                        issues.append("Due date is before invoice date")
                    
                    days_diff = (due_date - inv_date).days
                    if days_diff > 120:
                        issues.append(f"Unusually long payment term: {days_diff} days")
                except:
                    pass
            
            # Amount validation
            if data.get('total'):
                if data['total'] <= 0:
                    issues.append("Total amount is zero or negative")
                if data['total'] > 1000000:
                    issues.append(f"Unusually large amount: {data['total']}")
        
        except Exception as e:
            logger.warning(f"Consistency check failed: {e}")
        
        return issues
    
    def _check_common_errors(self, data: Dict) -> Dict:
        """Check för common OCR/LLM errors"""
        issues = []
        warnings = []
        
        # Invoice number patterns
        if data.get('invoice_number'):
            inv_num = str(data['invoice_number'])
            if len(inv_num) > 50:
                warnings.append("Unusually long invoice number")
            if len(inv_num) < 1:
                issues.append("Empty invoice number")
        
        # Vendor name checks
        if data.get('vendor_name'):
            name = str(data['vendor_name'])
            if len(name) < 2:
                issues.append("Vendor name too short")
            if len(name) > 200:
                warnings.append("Unusually long vendor name")
        
        # Email validation
        if data.get('vendor_email'):
            email = str(data['vendor_email'])
            if '@' not in email:
                warnings.append("Vendor email format invalid")
        
        return {'issues': issues, 'warnings': warnings}
    
    def _calculate_quality_score(
        self,
        confidence: float,
        missing_count: int,
        issue_count: int
    ) -> float:
        """
        Calculate overall quality score (0-1)
        
        Weighted factors:
        - Confidence: 60% (från LLM)
        - Missing fields: 25% (critical data)
        - Issues: 15% (consistency problems)
        """
        
        # Confidence component (60%)
        conf_score = confidence * 0.6
        
        # Missing fields component (25%)
        # Penalize 1 point per missing field (max 3 fields = 0 points)
        missing_penalty = min(missing_count / 3.0, 1.0)
        missing_score = (1.0 - missing_penalty) * 0.25
        
        # Issues component (15%)
        # Penalize 1 point per issue (max 5 issues = 0 points)
        issue_penalty = min(issue_count / 5.0, 1.0)
        issue_score = (1.0 - issue_penalty) * 0.15
        
        total_score = conf_score + missing_score + issue_score
        return max(0.0, min(1.0, total_score))  # Clamp to 0-1
    
    def _determine_recommendation(
        self,
        quality_score: float,
        missing_fields: list,
        issues: list
    ) -> str:
        """Determine action recommendation"""
        
        # High quality - auto export
        if quality_score >= 0.85 and not missing_fields and len(issues) == 0:
            return 'auto_export'
        
        # Good quality but some issues - review recommended
        if quality_score >= 0.80 and len(missing_fields) <= 2 and len(issues) <= 2:
            return 'review_possible'
        
        # Everything else - manual review
        return 'manual_review'
