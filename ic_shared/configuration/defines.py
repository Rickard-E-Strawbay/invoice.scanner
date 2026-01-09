# defines.py
# Application constants and file paths

import os
from pathlib import Path

# Local Database Configuration
LOCAL_DATABASE_URL = "postgresql://scanner:scanner@db:5432/invoice_scanner"
LOCAL_DATABASE_HOST = "db"
LOCAL_DATABASE_PORT = 5432
LOCAL_DATABASE_USER = "scanner"
LOCAL_DATABASE_PASSWORD = "scanner"
LOCAL_DATABASE_NAME = "invoice_scanner"


# File paths for document storage (mounted from project root via Docker)
# These should NOT be created here - they are mounted from the host
BASE_DOCUMENTS_DIR = Path("/app/documents")  # Use absolute path (mounted location)
DOCUMENTS_RAW_DIR = BASE_DOCUMENTS_DIR / "raw"
DOCUMENTS_PROCESSED_DIR = BASE_DOCUMENTS_DIR / "processed"

# Note: Directories are mounted via Docker bind mount, not created locally

STAGE_PREPROCESS = "preprocess"
STAGE_OCR = "ocr"
STAGE_LLM = "llm"
STAGE_EXTRACTION = "extraction"
STAGE_EVALUATION = "evaluation"

TOPIC_NAME_PROCESSING = "document-processing"
TOPIC_NAME_OCR = "document-ocr"
TOPIC_NAME_LLM = "document-llm"
TOPIC_NAME_EXTRACTION = "document-extraction"
TOPIC_NAME_EVALUATION = "document-evaluation"

ENTER = "start"
EXIT = "stop"

PREPROCESS_STATUS = {ENTER: "preprocessing", EXIT: "preprocessed"}
PREPROCESS_ERROR = "error_preprocessing"

OCR_STATUS = {ENTER: "ocr_extracting", EXIT: "ocr_complete"}
OCR_ERROR = "error_ocr"

LLM_STATUS = {ENTER: "llm_predicting", EXIT: "llm_complete"}
LLM_ERROR = "error_llm"

EXTRACTION_STATUS = {ENTER: "data_extracting", EXIT: "data_extracted"}
EXTRACTION_ERROR = "error_data_extraction"

EVALUATION_STATUS = {ENTER: "evaluating", EXIT: "evaluated"}
EVALUATION_ERROR = "error_evaluation"

ERROR_DESCRIPTIONS = {
    "preprocess_error": "Error during preprocessing",
    "ocr_error": "Error during OCR extraction", 
    "llm_error": "Error during LLM prediction",
    "extraction_error": "Error during data extraction",
    "evaluation_error": "Error during automated evaluation"
}

