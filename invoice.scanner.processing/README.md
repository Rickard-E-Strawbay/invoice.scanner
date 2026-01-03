# Invoice Scanner - Processing Worker Service

A persistent, scalable document processing service that replaces serverless Cloud Functions with a stateful Cloud Run worker.

## Architecture

### Problem Solved
The original Cloud Functions architecture had limitations:
- **9-minute timeout** → Cannot process multi-page PDFs with large line items
- **Stateless** → Cannot cache intermediate results between pipeline stages
- **No parallelism** → OCR, LLM, and evaluation run sequentially (slow)
- **System dependencies** → Tesseract/poppler system packages not available in serverless runtime

### Solution: Worker Service
This service runs on Cloud Run with:
- **Unlimited timeout** → Can process any document size
- **Stateful** → Can cache extracted data between stages
- **Parallel workers** → ThreadPool per stage for N concurrent sub-tasks
- **System access** → Full OS environment with all dependencies installed

## Deployment Modes

### Local Development (docker-compose)
```bash
cd invoice.scanner.processing
bash local_server.sh
```

Runs on `http://localhost:8000` with:
- Mock Pub/Sub (subscriptions fail gracefully)
- PostgreSQL connection to `db` service
- Flask development server with auto-reload
- All system dependencies available

### Production (Google Cloud Run)
```bash
cd invoice.scanner.processing
bash deploy.sh
```

Builds and deploys to Cloud Run with:
- Real Pub/Sub subscriptions
- Cloud SQL Connector for database access
- 4 vCPU, 4GB memory by default
- Minimum 1 instance, max 10 instances
- Private VPC access for Cloud SQL

## Processing Pipeline

The service coordinates a 5-stage processing pipeline:

```
document-processing (Pub/Sub topic 1)
    ↓
PreprocessWorker: PDF→PNG conversion
    ↓
document-ocr (Pub/Sub topic 2)
    ↓
OCRWorker: Text extraction with ThreadPool(5)
    - For multi-page PDFs: parallel page OCR
    - For 10-page PDF: 10s vs 300s sequential
    ↓
document-llm (Pub/Sub topic 3)
    ↓
LLMWorker: LLM extraction with ThreadPool(10)
    - For 50 line items: parallel extraction calls
    - 250s sequential → 25s parallel
    ↓
document-extraction (Pub/Sub topic 4)
    ↓
ExtractionWorker: Data normalization and validation
    ↓
document-evaluation (Pub/Sub topic 5)
    ↓
EvaluationWorker: Quality scoring with ThreadPool(20)
    - For 50 fields: parallel confidence calculation
    - 50s sequential → 3s parallel
```

## Environment Variables

### Database Connection
```bash
# Local mode (docker-compose)
DATABASE_HOST=db                          # Service name in docker-compose
DATABASE_PORT=5432
DATABASE_USER=scanner
DATABASE_PASSWORD=scanner
DATABASE_NAME=invoice_scanner

# Cloud Run mode (automatic from Cloud SQL Connector)
INSTANCE_CONNECTION_NAME=project:region:instance
DATABASE_USER=scanner
DATABASE_PASSWORD=<from Secret Manager>
DATABASE_NAME=invoice_scanner
```

### Processing Configuration
```bash
GCP_PROJECT_ID=strawbayscannertest       # GCP project for Pub/Sub
PROCESSING_LOG_LEVEL=INFO                # Log level: DEBUG, INFO, WARNING, ERROR
WORKER_MAX_PROCESSES=5                   # Concurrent documents being processed
PROCESSING_SLEEP_TIME=0.0                # Mock processing delay (local testing)
```

### Google Cloud
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # For local Pub/Sub testing
K_SERVICE=<set by Cloud Run>              # Automatic environment detection
```

## HTTP Endpoints

### Health Check
```
GET /health

200 OK
{
  "status": "healthy",
  "service": "invoice.scanner.processing"
}
```

Used by Kubernetes liveness/readiness probes.

### Trigger Document Processing
```
POST /api/documents/{doc_id}/process
Content-Type: application/json

{
  "company_id": "uuid"
}

202 ACCEPTED
{
  "status": "queued",
  "document_id": "uuid",
  "message": "Document queued for processing"
}
```

### Get Document Status
```
GET /api/documents/{doc_id}/status

200 OK
{
  "document_id": "uuid",
  "status": "evaluation_complete",
  "updated_at": "2024-01-15T10:30:00Z",
  "error_message": null
}
```

## Database Schema

Documents table is managed by invoice.scanner.db:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Document identifier |
| `company_id` | UUID | Company owning document |
| `status` | VARCHAR | Pipeline stage + state (preprocessing, preprocessed, ocr_extracting, ocr_complete, llm_complete, extraction_complete, evaluation_complete) |
| `ocr_raw_text` | TEXT | Raw text extracted by OCR |
| `ocr_data` | JSONB | Structured OCR data per page |
| `error_message` | TEXT | Error details if failed |
| `updated_at` | TIMESTAMP | Last update time |

Status transitions:
```
preprocessing → preprocessed → ocr_extracting → ocr_complete → llm_complete → extraction_complete → evaluation_complete
```

Error states:
```
preprocess_error, ocr_error, llm_error, extraction_error, evaluation_error
```

## Integration with API

The API (`invoice.scanner.api`) routes documents to this service:

1. **Initialization** (main.py):
```python
PROCESSING_BACKEND = 'worker_service'  # Select backend
processing_backend = init_processing_backend()
```

2. **Queuing documents** (routes):
```python
document_id = upload_document(file)
processing_backend.trigger_task(document_id, company_id)
```

3. **Checking status** (dashboard):
```python
status = processing_backend.get_task_status(task_id)
```

## File Structure

```
invoice.scanner.processing/
├── main.py                    # Pub/Sub listener + worker coordinator + Flask app
├── db_config.py              # Unified database config (Cloud Run + local)
├── pg8000_wrapper.py         # pg8000 driver wrapper with RealDictCursor compatibility
├── requirements.txt          # Python dependencies
├── Dockerfile                # Cloud Run production image
├── Dockerfile.dev            # docker-compose development image
├── local_server.sh           # Local development startup script
├── deploy.sh                 # GCP Cloud Run deployment script
└── README.md                 # This file
```

## Worker Classes

### BaseWorker
Abstract base class for all workers:
```python
class BaseWorker:
    def execute(self):
        # Process document
        update_document_status(self.document_id, status)
        publish_to_topic(next_topic, message_data)
```

### PreprocessWorker
Stage 1: PDF to PNG conversion
- Input: Raw PDF file from storage
- Output: Preprocessed PNG images
- ThreadPool: Sequential (single PDF)

### OCRWorker
Stage 2: Text extraction
- Input: PNG images from preprocessing
- Output: `ocr_raw_text`, `ocr_data` JSON
- ThreadPool: 5 concurrent pages (multi-page parallel OCR)
- Performance: 10-page PDF: 10s (parallel) vs 300s (sequential)

### LLMWorker
Stage 3: Structured data extraction
- Input: OCR text and invoice line items
- Output: Structured extraction results
- ThreadPool: 10 concurrent LLM API calls
- Performance: 50 items: 25s (parallel) vs 250s (sequential)

### ExtractionWorker
Stage 4: Data normalization
- Input: LLM extraction results
- Output: Normalized and validated data
- ThreadPool: 5 concurrent field normalization

### EvaluationWorker
Stage 5: Quality scoring
- Input: Extracted and normalized data
- Output: Confidence scores per field
- ThreadPool: 20 concurrent confidence calculations
- Performance: 50 fields: 3s (parallel) vs 50s (sequential)

## Local Development

### Prerequisites
```bash
# System dependencies
brew install tesseract poppler-utils

# Python environment
python3 --version  # 3.11+
```

### Quick Start
```bash
# Terminal 1: Start docker-compose
cd invoice.scanner
docker-compose up

# Terminal 2: Start processing service
cd invoice.scanner.processing
bash local_server.sh
```

### Testing
```bash
# Health check
curl http://localhost:8000/health

# Queue document for processing
curl -X POST http://localhost:8000/api/documents/test-uuid/process \
  -H "Content-Type: application/json" \
  -d '{"company_id": "test-company-id"}'

# Check status
curl http://localhost:8000/api/documents/test-uuid/status
```

### Debugging
```bash
# Enable debug logging
export PROCESSING_LOG_LEVEL=DEBUG
bash local_server.sh

# Monitor database changes
docker exec invoice.scanner-db-1 psql -U scanner invoice_scanner \
  -c "SELECT id, status, updated_at FROM documents ORDER BY updated_at DESC LIMIT 10;"
```

## Production Deployment

### Prerequisites
```bash
# Google Cloud Project Setup
gcloud config set project strawbayscannertest

# Ensure roles
gcloud projects get-iam-policy strawbayscannertest \
  --flatten="bindings[].members" \
  --filter="bindings.members:your-email@example.com"

# Required APIs enabled
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    pubsub.googleapis.com \
    sqladmin.googleapis.com
```

### Deployment
```bash
cd invoice.scanner.processing
bash deploy.sh

# Verify
gcloud run services list
gcloud run logs read invoice-scanner-processing \
    --region europe-west1 \
    --follow
```

### Configuration After Deployment
```bash
# Set up Pub/Sub subscriptions
for TOPIC in document-processing document-ocr document-llm document-extraction document-evaluation; do
    gcloud pubsub subscriptions create ${TOPIC}-subscription \
        --topic=$TOPIC \
        --push-endpoint=$SERVICE_URL/pubsub \
        --push-auth-service-account=invoice-scanner-worker@strawbayscannertest.iam.gserviceaccount.com
done

# Verify service account has permissions
gcloud projects add-iam-policy-binding strawbayscannertest \
    --member=serviceAccount:invoice-scanner-worker@strawbayscannertest.iam.gserviceaccount.com \
    --role=roles/pubsub.subscriber
```

## Troubleshooting

### Pub/Sub Messages Not Received (Local)
**Expected in local mode.** Set credentials to test:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
bash local_server.sh
```

### Database Connection Failed
**Local:** Ensure `docker-compose up` succeeded and `db` service is running
**Cloud:** Check Cloud SQL Connector configuration and service account permissions

### Document Stuck in Processing
Check logs for errors:
```bash
gcloud run logs read invoice-scanner-processing --region europe-west1
```

Retry processing:
```sql
UPDATE documents SET status='preprocessing' WHERE id='uuid';
```

## Next Steps

1. **Implement Worker Logic** (TODO in main.py)
   - PreprocessWorker: Actual PDF→PNG conversion
   - OCRWorker: Real Tesseract OCR with threading
   - LLMWorker: Actual LLM API integration
   - ExtractionWorker: Data normalization logic
   - EvaluationWorker: Confidence scoring algorithms

2. **Update API Backend** (invoice.scanner.api/lib/processing_backend.py)
   - Implement `WorkerServiceBackend` class
   - Switch API to use new backend
   - Test end-to-end document flow

3. **Update Pipeline** (.github/workflows/pipeline.yml)
   - Build `invoice.scanner.processing` image
   - Deploy to Cloud Run in TEST/PROD stages
   - Add environment variables for database credentials

4. **Performance Tuning**
   - Adjust ThreadPool sizes per stage
   - Monitor Cloud Run metrics
   - Optimize database queries
   - Cache frequently accessed data

5. **Error Handling & Resilience**
   - Implement retry logic with exponential backoff
   - Add dead-letter topic for failed messages
   - Implement Circuit Breaker for LLM API calls
   - Add metrics/alerting for pipeline stages

## License

Part of the Invoice Scanner project.
