# defines.py
# Application constants and file paths

import os
from pathlib import Path

# File paths for document storage
BASE_DOCUMENTS_DIR = Path(os.path.dirname(__file__)) / "documents"
DOCUMENTS_RAW_DIR = BASE_DOCUMENTS_DIR / "raw"
DOCUMENTS_PROCESSED_DIR = BASE_DOCUMENTS_DIR / "processed"

# Ensure directories exist
DOCUMENTS_RAW_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
