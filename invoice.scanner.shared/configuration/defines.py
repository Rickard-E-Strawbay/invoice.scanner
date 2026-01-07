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
