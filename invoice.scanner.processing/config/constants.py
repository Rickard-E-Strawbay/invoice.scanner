"""
Global Constants and Defaults

Centralized constants used throughout the processing pipeline.
Makes it easy to adjust values without searching through code.

SECTIONS:
    - Paths and directories
    - Timeouts and timing
    - Processing parameters
    - Status strings
    - Logging formats
"""

# ===== PATHS AND DIRECTORIES =====

DOCUMENTS_BASE_DIR = "/app/documents"
DOCUMENTS_RAW_DIR = f"{DOCUMENTS_BASE_DIR}/raw"
DOCUMENTS_PROCESSED_DIR = f"{DOCUMENTS_BASE_DIR}/processed"

# ===== PREPROCESSING PARAMETERS =====

PREPROCESSING_TARGET_DPI = 300
PREPROCESSING_TARGET_FORMAT = 'png'
PREPROCESSING_MAX_WIDTH = 3000
PREPROCESSING_MAX_HEIGHT = 4000

# ===== OCR PARAMETERS =====

OCR_DEFAULT_ENGINE = 'paddleocr'  # 'paddleocr' or 'tesseract'
OCR_DEFAULT_LANGUAGE = 'en'
OCR_MIN_CONFIDENCE = 0.60  # Minimum acceptable confidence threshold

# ===== LLM PARAMETERS =====

LLM_DEFAULT_TEMPERATURE = 0.7
LLM_DEFAULT_MAX_TOKENS = 2048
LLM_API_TIMEOUT_SECONDS = 300  # 5 minutes for API calls

# ===== TASK TIMEOUTS =====

TASK_SOFT_TIMEOUT_SECONDS = 300   # 5 minutes - triggers SoftTimeLimitExceeded
TASK_HARD_TIMEOUT_SECONDS = 600   # 10 minutes - kills task (SIGTERM)

PREPROCESSING_TIMEOUT = TASK_SOFT_TIMEOUT_SECONDS
OCR_TIMEOUT = 600  # Longer for OCR
LLM_TIMEOUT = 600  # Longer for LLM API calls
EXTRACTION_TIMEOUT = TASK_SOFT_TIMEOUT_SECONDS
EVALUATION_TIMEOUT = TASK_SOFT_TIMEOUT_SECONDS

# ===== RETRY STRATEGIES =====

PREPROCESSING_MAX_RETRIES = 2
PREPROCESSING_RETRY_COUNTDOWN = 60  # 1 minute

OCR_MAX_RETRIES = 3
OCR_RETRY_COUNTDOWN = 120  # 2 minutes

LLM_MAX_RETRIES = 3
LLM_RETRY_COUNTDOWN = 300  # 5 minutes - longer for API timeouts

EXTRACTION_MAX_RETRIES = 2
EXTRACTION_RETRY_COUNTDOWN = 60

EVALUATION_MAX_RETRIES = 2
EVALUATION_RETRY_COUNTDOWN = 60

# ===== DOCUMENT STATUS STRINGS =====
# These match database status values

STATUS_PREPROCESSING = 'preprocessing'
STATUS_PREPROCESSED = 'preprocessed'
STATUS_OCR = 'ocr'
STATUS_LLM = 'llm_extraction'
STATUS_EXTRACTION = 'extraction'
STATUS_EVALUATION = 'evaluation'
STATUS_COMPLETED = 'completed'
STATUS_ERROR = 'error'

STATUS_PREPROCESSING_ERROR = 'preprocess_error'
STATUS_OCR_ERROR = 'ocr_error'
STATUS_LLM_ERROR = 'llm_error'
STATUS_EXTRACTION_ERROR = 'extraction_error'
STATUS_EVALUATION_ERROR = 'evaluation_error'

# ===== QUALITY SCORE THRESHOLDS =====

QUALITY_SCORE_EXCELLENT = 0.95  # High confidence, auto-approve
QUALITY_SCORE_GOOD = 0.85      # Good confidence, can auto-approve
QUALITY_SCORE_FAIR = 0.70      # Fair quality, manual review recommended
QUALITY_SCORE_POOR = 0.0       # Low quality, definite manual review

# ===== RECOMMENDATION STRINGS =====

RECOMMENDATION_APPROVE = 'APPROVE'
RECOMMENDATION_MANUAL_REVIEW = 'MANUAL_REVIEW'
RECOMMENDATION_REJECT = 'REJECT'

# ===== LOGGING PREFIXES =====
# Used to identify task stages in logs for easy parsing

LOG_PREFIX_PREPROCESSING = '[PREPROCESSING]'
LOG_PREFIX_OCR = '[OCR]'
LOG_PREFIX_LLM = '[LLM]'
LOG_PREFIX_EXTRACTION = '[EXTRACTION]'
LOG_PREFIX_EVALUATION = '[EVALUATION]'
LOG_PREFIX_HTTP = '[HTTP]'
LOG_PREFIX_DB = '[DB]'
LOG_PREFIX_TASK = '[TASK'
LOG_PREFIX_ERROR = '[ERROR]'
LOG_PREFIX_CALLBACK = '[CALLBACK]'

# ===== DATABASE DEFAULTS =====

DB_CONNECTION_TIMEOUT = 10  # seconds
DB_HOST_DEFAULT = 'postgres'
DB_PORT_DEFAULT = 5432
DB_NAME_DEFAULT = 'invoice_scanner'
DB_USER_DEFAULT = 'scanner'
DB_PASSWORD_DEFAULT = 'password'

# ===== CELERY DEFAULTS =====

CELERY_BROKER_DEFAULT = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND_DEFAULT = 'redis://redis:6379/0'

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CELERY_RESULT_EXPIRES_SECONDS = 3600  # 1 hour
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevent blocking on slow tasks

# ===== HTTP SERVICE DEFAULTS =====

HTTP_HOST = '0.0.0.0'
HTTP_PORT = 5002
HTTP_DEBUG = False

# ===== MOCK PROCESSING DELAYS =====
# Used when tasks are in mock mode (for testing/development)

MOCK_PREPROCESSING_DELAY = 5  # seconds
MOCK_OCR_DELAY = 5
MOCK_LLM_DELAY = 5
MOCK_EXTRACTION_DELAY = 5
MOCK_EVALUATION_DELAY = 5
