# defines.py
# Application constants and file paths

import os
from pathlib import Path

# File paths for document storage (mounted from project root via Docker)
# These should NOT be created here - they are mounted from the host
BASE_DOCUMENTS_DIR = Path("/app/documents")  # Use absolute path (mounted location)
DOCUMENTS_RAW_DIR = BASE_DOCUMENTS_DIR / "raw"
DOCUMENTS_PROCESSED_DIR = BASE_DOCUMENTS_DIR / "processed"

# Note: Directories are mounted via Docker bind mount, not created locally
