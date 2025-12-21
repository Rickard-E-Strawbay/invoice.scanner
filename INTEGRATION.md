# Integration Guide - Connecting API with Processing Service

This guide explains how the API and Processing Service communicate.

## Overview

```
┌─────────────────────────┐
│  invoice.scanner.api    │
│  (HTTP REST API)        │
│  Port: 5000             │
└────────────┬────────────┘
             │ (Queue task via Redis/Celery)
             ▼
┌─────────────────────────┐
│  Redis                  │
│  (Message Broker)       │
│  Port: 6379             │
└────────────┬────────────┘
             │ (Task subscribed by workers)
             ▼
┌─────────────────────────────────────────┐
│  invoice.scanner.processing             │
│  (Worker Pool)                          │
│  - preprocessing workers                │
│  - ocr worker                           │
│  - llm worker                           │
│  - extraction worker                    │
│  - evaluation worker                    │
└─────────────────────────────────────────┘
```

## Communication Protocol

### 1. API -> Processing (Trigger)

**When user uploads document:**

```python
# In invoice.scanner.api/main.py
@blp_auth.route("/documents/upload", methods=["POST"])
def upload_document():
    # ... save file to disk ...
    
    # Trigger processing task
    from tasks.celery_app import app
    from tasks.document_tasks import orchestrate_document_processing
    
    task = orchestrate_document_processing.delay(
        document_id="abc-123",
        company_id="comp-456"
    )
    
    return {
        "task_id": task.id,
        "status": "preprocessing"
    }
```

**How it works:**
1. API receives file upload
2. Saves file to `/documents/raw/`
3. Creates database record
4. Calls Celery task
5. Returns immediately (HTTP 201)

### 2. Processing -> Database (Update Status)

**Workers update document status:**

```python
# In invoice.scanner.processing/tasks/document_tasks.py
@app.task
def preprocess_document(document_id, company_id):
    # ... processing ...
    update_document_status(document_id, 'preprocessed')
    return result

def update_document_status(document_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE documents SET status = %s WHERE id = %s
    """, (status, document_id))
    conn.commit()
```

**Status flow:**
```
preprocessing → preprocessed → ocr_extracting → 
predicting → extraction → automated_evaluation → 
approved / manual_review
```

### 3. Client -> API (Poll Status)

**Frontend polls for status:**

```javascript
// In frontend: frontend.react/src/components/ScanInvoice.jsx
async function checkProcessingStatus(docId) {
    const response = await fetch(`/documents/${docId}/status`);
    const data = await response.json();
    
    console.log(data);
    // {
    //   "status": "ocr_extracting",
    //   "progress": { "percentage": 50 },
    //   "quality_score": null
    // }
    
    if (data.status === 'approved') {
        // Document ready!
        fetchDocumentData(docId);
    }
}
```

---

## Data Flow in Detail

### Complete Request Cycle

```
1. UPLOAD
   Client
     ↓ POST /documents/upload
   API (/documents/upload endpoint)
     ├─ Save file: /documents/raw/doc-123.pdf
     ├─ Insert DB: documents table
     ├─ Update status: "preprocessing"
     └─ Trigger: orchestrate_document_processing.delay()
         ↓ (sends message to Redis)
   Redis Queue
     ├─ preprocessing queue: [task-1, task-2, ...]
     ├─ ocr queue: [task-1, task-2, ...]
     └─ llm queue: [task-1, ...]

2. PREPROCESSING
   Worker (preprocessing)
     ├─ Receive task from Redis
     ├─ Load /documents/raw/doc-123.pdf
     ├─ Convert PDF → PNG
     ├─ Enhance image quality
     ├─ Save: /documents/processed/doc-123.png
     ├─ Update DB: status = "preprocessed"
     └─ Return: path to processed image

3. OCR EXTRACTION
   Worker (ocr)
     ├─ Receive processed image path
     ├─ Initialize OCR engine (PaddleOCR)
     ├─ Extract text from image
     ├─ Calculate confidence
     ├─ Update DB: status = "ocr_extracting"
     └─ Return: { text, confidence, gpu_used }

4. LLM PREDICTION
   Worker (llm)
     ├─ Receive OCR text
     ├─ Select provider from .env (OpenAI/Gemini/Anthropic)
     ├─ Call LLM API: "Extract invoice fields..."
     ├─ Parse JSON response
     ├─ Update DB: status = "predicting"
     └─ Return: { invoice_number, date, amount, etc }

5. DATA EXTRACTION
   Worker (extraction)
     ├─ Receive LLM predictions
     ├─ Validate schema
     ├─ Normalize dates: "21-Dec-2024" → "2024-12-21"
     ├─ Normalize amounts: "1.234,56" → 1234.56
     ├─ Calculate derived fields
     ├─ Update DB: status = "extraction"
     └─ Return: clean structured data

6. EVALUATION
   Worker (evaluation)
     ├─ Receive structured data
     ├─ Check required fields
     ├─ Validate consistency
     ├─ Calculate quality_score (0-1)
     ├─ Update DB: status = "approved" or "manual_review"
     ├─ Update DB: predicted_accuracy = 0.92
     └─ Return: evaluation report

7. CLIENT POLLS
   Client (Frontend)
     ├─ Poll: GET /documents/doc-123/status
     └─ Returns: status, progress, quality_score
     
   If status === 'approved':
     └─ Fetch document data
         GET /documents/doc-123
         ↓
         Return invoice fields to display
```

---

## Important Configuration

### Environment Variables

**Both API and Processing need these .env settings:**

```bash
# Database (shared)
DB_HOST=postgres
DB_PORT=5432
DB_USER=scanner
DB_PASSWORD=secure_password
DB_NAME=invoice_scanner

# Redis (shared message broker)
REDIS_URL=redis://redis:6379/0

# LLM Providers (processing service uses this)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# File paths (both need to access same documents)
DOCUMENTS_RAW_DIR=/app/documents/raw
DOCUMENTS_PROCESSED_DIR=/app/documents/processed
```

### Docker Network

**Both containers must be on same network:**

```yaml
# docker-compose.yml
networks:
  invoice.scanner:
    driver: bridge

services:
  postgres:
    networks:
      - invoice.scanner
  
  redis:
    networks:
      - invoice.scanner
  
  api:
    networks:
      - invoice.scanner
  
  processing:
    networks:
      - invoice.scanner
  
  worker_ocr_1:
    networks:
      - invoice.scanner
```

### Shared Volume

**Document files must be accessible to all:**

```yaml
volumes:
  documents_data:
    
services:
  api:
    volumes:
      - documents_data:/app/documents
  
  processing:
    volumes:
      - documents_data:/app/documents
```

---

## Error Handling

### If Task Fails

```
Worker catches exception
    ↓
Task retries (max 3 times, exponential backoff)
    ↓
If all retries fail:
    ├─ Update DB: status = "{step}_error"
    ├─ Log error details
    └─ Send to manual_review queue

Client polls and sees: status = "preprocess_error"
```

### Retry Strategy

```python
# config/celery_config.py
RETRY_STRATEGIES = {
    'preprocessing': {
        'max_retries': 2,
        'countdown': 60,      # Wait 60s before retry
    },
    'ocr': {
        'max_retries': 3,
        'countdown': 120,     # Wait 2min before retry
    },
    'llm': {
        'max_retries': 3,
        'countdown': 300,     # Wait 5min before retry (API is slow)
    },
    # ...
}
```

---

## Monitoring Integration

### Flower Dashboard

```bash
# Open monitoring dashboard
open http://localhost:5555

# Shows:
# - All running tasks in real-time
# - Task execution time
# - Success/failure status
# - Worker statistics
# - Queue depths
```

### Logging

```bash
# View logs from all services
docker-compose logs -f

# View specific document processing
docker-compose logs -f | grep "doc-123"

# View specific worker
docker-compose logs -f worker_ocr_1
```

### Health Checks

```bash
# Check all services healthy
docker-compose ps

# Check individual health
docker-compose exec redis redis-cli ping          # → PONG
docker-compose exec db pg_isready                # → accepting connections
curl http://localhost:5000/health                # → 200 OK (if endpoint exists)
```

---

## API Endpoints for Integration

### Upload Document

```http
POST /documents/upload

Headers:
  Authorization: Bearer {token}
  Content-Type: multipart/form-data

Body:
  file: <binary PDF/JPG/PNG>

Response 201:
{
  "message": "Document uploaded and queued for processing",
  "document": {
    "id": "abc-123-def",
    "status": "preprocessing",
    "created_at": "2024-12-21T12:34:56Z"
  },
  "task_id": "celery-task-789"
}
```

### Poll Processing Status

```http
GET /documents/{doc_id}/status

Headers:
  Authorization: Bearer {token}

Response 200:
{
  "document_id": "abc-123-def",
  "status": "ocr_extracting",
  "status_name": "OCR Extracting",
  "status_description": "OCR extraction is in progress",
  "progress": {
    "current_step": 2,
    "total_steps": 6,
    "percentage": 33
  },
  "quality_score": null,
  "created_at": "2024-12-21T12:34:56Z",
  "last_update": "2024-12-21T12:35:02Z"
}
```

### Get Document Data

```http
GET /documents/{doc_id}

Headers:
  Authorization: Bearer {token}

Response 200:
{
  "id": "abc-123-def",
  "status": "approved",
  "invoice_number": "INV-2024-001",
  "invoice_date": "2024-12-21",
  "vendor_name": "Acme Corp",
  "amount": 1000.00,
  "vat": 250.00,
  "total": 1250.00,
  "due_date": "2025-01-20",
  "predicted_accuracy": 0.92,
  "created_at": "2024-12-21T12:34:56Z"
}
```

---

## Troubleshooting Integration

### Issue: Task not starting after upload

```
Solution:
  1. Check Redis is running: docker-compose exec redis redis-cli ping
  2. Check workers are running: docker-compose ps | grep worker
  3. Check logs: docker-compose logs -f worker_preprocessing_1
  4. Restart workers: docker-compose restart worker_preprocessing_1
```

### Issue: Processing hangs at specific step

```
Solution:
  1. Check worker logs for that step
  2. Check Flower dashboard (http://localhost:5555)
  3. If LLM: check API key is set in .env
  4. If OCR: check image file exists and is readable
  5. Restart that worker type
```

### Issue: Database updates not visible in API

```
Solution:
  1. Check database connection string in .env
  2. Check all services use same database
  3. Verify Docker network connectivity
  4. Restart all services: docker-compose restart
```

---

## Next Steps

1. **Test locally:**
   ```bash
   docker-compose up -d
   # Upload test document
   # Monitor with Flower
   ```

2. **Integrate with frontend:**
   - Add polling logic in React
   - Show progress bar
   - Display quality score when done

3. **Customize processors:**
   - Modify LLM prompts
   - Add validation rules
   - Change OCR settings

4. **Deploy to production:**
   - Use managed services (RDS, ElastiCache)
   - Scale workers on Kubernetes/ECS
   - Add monitoring (Prometheus, CloudWatch)

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Full system overview
- [QUICKSTART.md](./QUICKSTART.md) - Quick setup guide
- [invoice.scanner.processing/README.md](./invoice.scanner.processing/README.md) - Processing service details
