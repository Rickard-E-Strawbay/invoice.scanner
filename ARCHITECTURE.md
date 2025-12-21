# Invoice Scanner - Complete Architecture Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   INVOICE SCANNER ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌─────────────────────────────────────┐
│   Frontend   │         │      API Service (Lightweight)      │
│  (React)     │────────>│                                     │
│  Port 3000   │         │  - REST endpoints                   │
└──────────────┘         │  - Authentication (Flask-Session)   │
                         │  - File upload handler              │
                         │  - Polling for status               │
                         │  Port 5000                          │
                         └─────────────┬───────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              ┌─────▼──────┐     ┌────▼──────┐    ┌─────▼──────┐
              │ PostgreSQL  │     │   Redis   │    │  Documents │
              │             │     │           │    │  (Raw/Proc)│
              │ - Users     │     │ Message   │    │            │
              │ - Companies │     │ Broker    │    │  /documents│
              │ - Documents │     │           │    │  /raw      │
              │ - Invoices  │     │ (Celery   │    │  /processed│
              │             │     │  Queue)   │    │            │
              └─────────────┘     └────┬──────┘    └────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
                │   PROCESSING SERVICE (Async Workers)       │
                │                                             │
       ┌────────▼────────┐  ┌──────────────┐  ┌──────────────┐
       │ Preprocessing   │  │    OCR       │  │     LLM      │
       │ Workers (x2)    │  │  Workers     │  │  Workers     │
       │                 │  │  (CPU/GPU)   │  │  (x1)        │
       │ - Image norm    │  │              │  │              │
       │ - PDF->IMG      │  │ - Tesseract  │  │ - OpenAI     │
       │ - Enhancement   │  │ - PaddleOCR  │  │ - Gemini     │
       │                 │  │ - GPU accel  │  │ - Anthropic  │
       │ Low CPU, High   │  │              │  │              │
       │ parallelism     │  │ High CPU,    │  │ Low CPU,     │
       │ (c=4)           │  │ Low parallel │  │ High latency │
       │                 │  │ (c=2)        │  │ (c=1)        │
       └────────┬────────┘  └──────────────┘  └──────────────┘
                │                 │                    │
                └─────────────────┬────────────────────┘
                                  │
                    ┌─────────────┴────────────────┐
                    │                              │
          ┌─────────▼───────────┐    ┌────────────▼────────┐
          │ Extraction Workers  │    │ Evaluation Workers  │
          │ (x1)                │    │ (x1)                │
          │                     │    │                     │
          │ - Data validation   │    │ - Quality check     │
          │ - Normalization     │    │ - Consistency check │
          │ - Format handling   │    │ - Score calculation │
          │ - Derived fields    │    │ - Status decision   │
          └─────────────────────┘    └─────────────────────┘
                    │                          │
                    └──────────────┬───────────┘
                                   │
                            ┌──────▼─────────┐
                            │ Flower Monitor │
                            │ (Port 5555)    │
                            │                │
                            │ Real-time      │
                            │ Task tracking  │
                            │ & metrics      │
                            └────────────────┘
```

## Service Separation

### Service 1: API (`invoice.scanner.api`)
**Responsibility:** HTTP REST interface, authentication, file handling  
**Container:** `invoice.scanner.api`  
**Port:** 5000  
**Dependencies:** PostgreSQL, Redis  
**Resources:** Low CPU, can be replicated  

**Key Endpoints:**
- `POST /documents/upload` - Queue document for processing
- `GET /documents/{id}/status` - Poll processing status
- `GET /documents` - List all documents
- `PUT /documents/{id}` - Update document data

### Service 2: Processing (`invoice.scanner.processing`)
**Responsibility:** Async document processing pipeline  
**Containers:** 6+ workers (preprocessing, OCR, LLM, extraction, evaluation)  
**Dependencies:** Redis (broker), PostgreSQL (state/results)  
**Resources:** Varies by worker type  

**Queue Structure:**
```
preprocessing ─┬─> Worker (c=4, lightweight)
               ├─> Worker (c=4, lightweight)

ocr ──────────────> Worker (c=2, GPU-capable)

llm ──────────────> Worker (c=1, API calls)

extraction ───────> Worker (c=3, data processing)

evaluation ───────> Worker (c=3, validation)
```

## Data Flow Example

```
SCENARIO: User uploads an invoice.pdf

STEP 1: UPLOAD (User -> API)
────────────────────────────
POST /documents/upload
  ├─ File: invoice.pdf
  └─ User: auth token

API Endpoint (/documents/upload):
  1. Validate user authentication ✓
  2. Save invoice.pdf to /documents/raw/
  3. Create document record in DB (status: preprocessing)
  4. Trigger Celery task: orchestrate_document_processing
  └─ Return: 201 Created + document ID + task ID

HTTP Response:
{
  "document": {
    "id": "doc-abc123",
    "status": "preprocessing",
    "raw_filename": "invoice.pdf"
  },
  "task_id": "celery-task-xyz"
}


STEP 2: PREPROCESSING (Worker: preprocessing)
──────────────────────────────────────────────
Celery Task Chain Starts:
  Task 1: preprocess_document(doc_id, company_id)
  
  Processor Actions:
    1. Read: /documents/raw/doc-abc123.pdf
    2. Convert PDF → PNG images
    3. Enhance: denoise, increase contrast
    4. Normalize: resize to max 3000x4000px
    5. Save: /documents/processed/doc-abc123.png
    6. Return: path to processed image
    
  Database: status = "preprocessed"
  Time: ~2-3 seconds


STEP 3: OCR (Worker: ocr, CPU or GPU)
──────────────────────────────────────
Celery Task 2: extract_ocr_text(image_path)

Processor Actions:
  1. Load image: /documents/processed/doc-abc123.png
  2. Initialize OCR engine (PaddleOCR or Tesseract)
  3. Extract text from image
  4. Calculate per-line confidence
  5. Return: OCR result
  
  OCR Result:
  {
    "text": "Invoice #INV-2024-001\nDate: 2024-12-21\n...",
    "overall_confidence": 0.92,
    "gpu_used": true,
    "processing_time": 1.2
  }
  
  Time: ~1-2 sec (GPU) or ~10-15 sec (CPU)


STEP 4: LLM PREDICTION (Worker: llm)
────────────────────────────────────
Celery Task 3: predict_invoice_data(ocr_result, company_id)

LLMProcessor Actions:
  1. Select provider (OpenAI/Gemini/Anthropic) from .env
  2. Create system prompt: "Extract invoice fields..."
  3. API Call: LLM.predict(prompt + ocr_text)
  4. Parse JSON response
  5. Return: structured prediction
  
  LLM Result:
  {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-12-21",
    "vendor_name": "Acme Corp",
    "amount": 1000.00,
    "vat": 250.00,
    "total": 1250.00,
    "due_date": "2025-01-20",
    "confidence": 0.95,
    "provider": "openai",
    "model_used": "gpt-4o"
  }
  
  Time: ~5-10 seconds + API latency


STEP 5: DATA EXTRACTION (Worker: extraction)
─────────────────────────────────────────────
Celery Task 4: extract_structured_data(llm_prediction, company_id)

DataExtractor Actions:
  1. Normalize dates: "21-Dec-2024" → "2024-12-21"
  2. Normalize amounts: "1.234,56 EUR" → 1234.56
  3. Validate data types
  4. Calculate derived fields:
     - If amount + vat known → calculate total
     - If amount + total known → calculate vat_rate
  5. Add metadata: extraction_at, extraction_version
  
  Extracted Data:
  {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-12-21",
    "vendor_name": "Acme Corp",
    "amount": 1000.00,
    "vat": 250.00,
    "total": 1250.00,
    "vat_rate": 25.0,
    "due_date": "2025-01-20",
    "currency": "EUR",
    "confidence": 0.95,
    "extraction_at": "2024-12-21T12:34:56Z",
    "company_id": "comp-abc123"
  }
  
  Time: ~1-2 seconds


STEP 6: EVALUATION (Worker: evaluation)
───────────────────────────────────────
Celery Task 5: run_automated_evaluation(structured_data)

Validator Actions:
  1. Check: all required fields present
  2. Check: data consistency (amount + vat = total)
  3. Check: value ranges (VAT 0-100%, amount > 0)
  4. Check: dates logical (due > invoice)
  5. Calculate: quality_score = f(confidence, missing_fields, issues)
  6. Decide: approved or manual_review
  
  Evaluation Result:
  {
    "quality_score": 0.92,
    "status": "approved",
    "recommendation": "auto_export",
    "issues": [],
    "warnings": [],
    "missing_fields": [],
    "validation_details": {
      "required_fields_filled": 3,
      "critical_fields_filled": 5,
      "confidence_score": 0.95,
      "data_consistency": true
    }
  }
  
  Time: ~0.5-1 second


STEP 7: UPDATE STATUS
─────────────────────
Database Update:
  UPDATE documents SET status = 'approved', 
                       predicted_accuracy = 0.92,
                       updated_at = NOW()
  WHERE id = 'doc-abc123'


STEP 8: POLL (User -> API)
──────────────────────────
GET /documents/{doc-abc123}/status

API Returns:
{
  "document_id": "doc-abc123",
  "status": "approved",
  "status_name": "Approved",
  "progress": {
    "current_step": 6,
    "total_steps": 6,
    "percentage": 100
  },
  "quality_score": 0.92
}

User Interface Updates:
  ✓ Document marked as "Approved"
  ✓ Quality score shown: 92%
  ✓ Extracted data can be reviewed/exported
```

## Why This Architecture Works

### ✅ Scalability
- **API**: Stateless, can replicate horizontally
- **Workers**: Add new instances for any queue without changing API
- **Example**: 100k invoices/month → add 10 OCR workers

### ✅ Resilience
- Worker crash → task retries via Redis
- API restart → doesn't interrupt processing
- Database down → queue persists, resumes when DB back up

### ✅ Resource Efficiency
- **Preprocessing**: Low CPU (lightweight workers can parallelize)
- **OCR**: High CPU (GPU capable, limited concurrency)
- **LLM**: Low CPU (IO-bound, external API)
- **Extraction**: Low CPU (pure computation)
- **Evaluation**: Low CPU (validation logic)

### ✅ Cost Optimization
- **Development**: Run locally with docker-compose
- **Production**: Scale workers per demand
- **GPU**: Optional - adds 10x OCR speedup for extra cost

### ✅ Monitoring
- **Flower Dashboard**: Real-time task tracking
- **Logging**: Structured logs per step
- **Database**: Document status history
- **Metrics**: Processing time per step

## Configuration Examples

### Minimal Development Setup
```bash
# .env
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
```

docker-compose up postgres redis api flower worker_ocr_1 worker_llm_1

### Production Setup (Single Machine)
```yaml
workers:
  preprocessing: 4 instances × 4 concurrency = 16 parallel
  ocr: 2 instances × 2 concurrency = 4 parallel
  llm: 1 instance × 1 concurrency = 1 sequential
  extraction: 2 instances × 3 concurrency = 6 parallel
```

Result: ~200-300 invoices/hour

### Production Setup (Multi-Machine Kubernetes)
```yaml
# Each machine
preprocessing: 8 workers
ocr: 4 workers (GPU)
llm: 2 workers
extraction: 4 workers
```

Result: ~2000+ invoices/hour (linear scaling)

## Next Steps

1. **Test locally**: `docker-compose up -d`
2. **Configure LLM**: Set OPENAI_API_KEY in .env
3. **Upload test document**: Use API /documents/upload
4. **Monitor**: Open http://localhost:5555 (Flower)
5. **Production deploy**: Use Kubernetes or AWS ECS

See [invoice.scanner.processing/README.md](../invoice.scanner.processing/README.md) for detailed documentation.
