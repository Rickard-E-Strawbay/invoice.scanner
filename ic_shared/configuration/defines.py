# defines.py
# Application constants and file paths

import os
from pathlib import Path

# Local Database Configuration
LOCAL_DATABASE_URL = "postgresql://scanner_local:scanner_local@db:5432/invoice_scanner"
LOCAL_DATABASE_HOST = "db"
LOCAL_DATABASE_PORT = 5432
LOCAL_DATABASE_USER = "scanner_local"
LOCAL_DATABASE_PASSWORD = "scanner_local"
LOCAL_DATABASE_NAME = "invoice_scanner"


# File paths for document storage (mounted from project root via Docker)
# These should NOT be created here - they are mounted from the host
# Allow override via environment variable for local development
BASE_DOCUMENTS_DIR = Path(os.getenv('BASE_DOCUMENTS_DIR', '/app/documents'))
DOCUMENTS_RAW_DIR = BASE_DOCUMENTS_DIR / "raw"
DOCUMENTS_PROCESSED_DIR = BASE_DOCUMENTS_DIR / "processed"

# Note: Directories are mounted via Docker bind mount, not created locally

# STAGE_PREPROCESS = "preprocess"
STAGE_PREPROCESS = "processing"
STAGE_OCR = "ocr"
STAGE_LLM = "llm"
STAGE_EXTRACTION = "extraction"
STAGE_EVALUATION = "evaluation"

STAGES = [
    STAGE_PREPROCESS,
    STAGE_OCR,
    STAGE_LLM,
    STAGE_EXTRACTION,
    STAGE_EVALUATION
]

# TOPIC_NAME_PROCESSING = "document-processing"
# TOPIC_NAME_OCR = "document-ocr"
# TOPIC_NAME_LLM = "document-llm"
# TOPIC_NAME_EXTRACTION = "document-extraction"
# TOPIC_NAME_EVALUATION = "document-evaluation"

# TOPIC_NAMES = [ 
#     TOPIC_NAME_PROCESSING,
#     TOPIC_NAME_OCR,
#     TOPIC_NAME_LLM,
#     TOPIC_NAME_EXTRACTION,
#     TOPIC_NAME_EVALUATION
# ]

ENTER = "start"
EXIT = "stop"
FAIL = "fail"
ERROR = "error"

PREPROCESS_STATUS = {ENTER: "processing", EXIT: "processed", FAIL: "fail_processing", ERROR: "error_processing"}
OCR_STATUS = {ENTER: "ocr_extracting", EXIT: "ocr_complete", FAIL: "fail_ocr", ERROR: "error_ocr"}
LLM_STATUS = {ENTER: "llm_predicting", EXIT: "llm_complete", FAIL: "fail_llm", ERROR: "error_llm"}
EXTRACTION_STATUS = {ENTER: "data_extracting", EXIT: "data_extracted", FAIL: "fail_data_extraction", ERROR: "error_data_extraction"}
EVALUATION_STATUS = {ENTER: "scan_evaluating", EXIT: "scan_evaluated", FAIL: "fail_evaluation", ERROR: "error_evaluation"}

ERROR_DESCRIPTIONS = {
    "preprocess_error": "Error during preprocessing",
    "ocr_error": "Error during OCR extraction", 
    "llm_error": "Error during LLM prediction",
    "extraction_error": "Error during data extraction",
    "evaluation_error": "Error during automated evaluation"
}

COMPANY_SETTINGS_DEFAULTS = {
    "scanner_settings": {
        "name": "Scanner Settings",
        "parameters": [
            {"name": "Require Peppol ID", "key": "peppol_id_required", "type": "boolean", "value": True, "description": "Require Peppol ID for all processed invoices."},
            {"name": "Require Supplier Registration Number", "key": "supplier_registration_required", "type": "boolean", "value": True, "description": "Require Supplier Registration Number for all processed invoices."},
            {"name": "Confidence Error", "key": "confidence_error_threshold", "type": "float", "value": 0.8, "description": "Minimum confidence level for accepting extracted data."},
            {"name": "Confidence Warning", "key": "confidence_warning_threshold", "type": "float", "value": 0.85, "description": "Minimum confidence level for accepting extracted data."}
        ]
    }
}

PEPPOL_DEFAULTS = {
    "meta":{
        "ubl_version_id":{"v":"2.1","p":1.0},
        "customization_id":{"v":"urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0","p":1.0},
        "profile_id":{"v":"urn:fdc:peppol.eu:2017:billing:01:1.0","p":1.0},
        "document_type":{"v":"invoice","p":1.0},
        "document_id":{"v":"380","p":1.0}
    },
    "supplier":{
        "tax_scheme":{"v":"VAT","p":1.0}
    },
    "tax_total":{
        "tax_scheme":{"v":"VAT","p":1.0}
    },
    "line_items": [
        {
            "tax_scheme":{"v":"VAT","p":1.0}
        }
    ]
}

