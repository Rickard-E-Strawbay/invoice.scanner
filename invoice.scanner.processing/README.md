# Invoice Scanner - Processing Service

## Overview

This is the **asynchronous document processing service** for Invoice Scanner. It handles all compute-intensive and time-consuming logic for scanning, extracting, and validating invoice data.

**Architecture:**
```
API (invoice.scanner.api)
      ↓ (async request)
Redis (Message Broker)
      ↓
Celery Workers (Processing Service)
      ↓ (results)
Database
```

## Why Separation?

✅ **Scalability** - Add workers without API changes  
✅ **Reliability** - Worker crashes don't affect API  
✅ **Performance** - Dedicated resources for processing  
✅ **Flexibility** - Different resources per worker type  
✅ **GPU Support** - OCR workers can have CUDA  

---

## 📦 Installation & Setup

### Prerequisites
```bash
# Docker & Docker Compose
docker --version  # >= 20.10
docker-compose --version  # >= 1.29

# Optional: GPU support
nvidia-docker --version  # For CUDA support
```

### Quick Start

```bash
# 1. Copy env file
cp .env.example .env

# 2. Set API keys in .env
# - OPENAI_API_KEY
# - GOOGLE_API_KEY (for Gemini)
# - ANTHROPIC_API_KEY

# 3. Start everything
docker-compose up -d

# 4. Check status
docker-compose ps
# Should show: api, postgres, redis, workers...

# 5. Open monitoring dashboard
open http://localhost:5555  # Flower dashboard
```

---

## 🏗️ Architecture

### Service Structure

```
invoice.scanner.processing/
├── config/                 # Konfiguration
│   ├── celery_config.py   # Celery settings, queues, retry strategies
│   ├── llm_providers.py   # LLM configuration (OpenAI, Gemini, Anthropic)
│   └── __init__.py
│
├── tasks/                  # Celery tasks (async work)
│   ├── celery_app.py      # Celery application instance
│   ├── document_tasks.py  # Main orchestrator + task chain
│   ├── preprocessing_tasks.py
│   ├── ocr_tasks.py
│   ├── llm_tasks.py
│   ├── extraction_tasks.py
│   ├── evaluation_tasks.py
│   └── callbacks.py       # Post-processing callbacks
│
├── processors/            # Business logic (reusable)
│   ├── image_processor.py    # Image preprocessing
│   ├── ocr_processor.py      # OCR (Tesseract/PaddleOCR + GPU)
│   ├── llm_processor.py      # LLM calls (3 providers)
│   ├── data_extractor.py     # Data validation & normalization
│   └── validator.py          # Quality scoring & evaluation
│
├── monitoring/           # Observability
│   ├── task_monitor.py   # Task execution tracking
│   └── error_handler.py  # Error & retry handling
│
├── workers/              # Docker images for worker types
│   ├── Dockerfile           # Base worker image
│   ├── Dockerfile.ml        # GPU-optimized OCR worker
│   └── Dockerfile.preprocessing  # Lightweight preprocessing
│
└── requirements.txt      # Python dependencies
```

### Task Flow

```
1. UPLOAD (API)
   └─> orchestrate_document_processing

2. PREPROCESSING
   └─> Image normalization & enhancement
   └─> Output: Enhanced image

3. OCR EXTRACTION
   └─> PaddleOCR or Tesseract
   └─> [GPU-accelerated if available]
   └─> Output: Extracted text + confidence

4. LLM PREDICTION
   └─> Select LLM Provider (OpenAI/Gemini/Anthropic)
   └─> Extract structured data
   └─> Output: Invoice fields (number, date, amount, etc)

5. DATA EXTRACTION
   └─> Validate data schema
   └─> Normalize formats (dates, amounts)
   └─> Calculate derived fields
   └─> Output: Clean structured data

6. EVALUATION
   └─> Quality scoring
   └─> Consistency checks
   └─> Determine: approved or manual_review
   └─> Output: Evaluation report
```

---

## 🔧 Configuration

### LLM Providers

Configure which LLM provider you want to use via `.env`:

#### Option 1: OpenAI (Recommended - highest accuracy)
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o  # or gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
```
**Cost:** ~$0.01-0.03 per invoice  
**Speed:** ~2-5 seconds  
**Accuracy:** Highest (95%+)

#### Option 2: Google Gemini (Cheapest)
```bash
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
GEMINI_TEMPERATURE=0.7
```
**Cost:** ~$0.0005-0.001 per invoice  
**Speed:** Variable  
**Accuracy:** Good (85-90%)

#### Option 3: Anthropic Claude (Balanced)
```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_TEMPERATURE=0.7
```
**Cost:** ~$0.003-0.01 per invoice  
**Speed:** ~3-6 seconds  
**Accuracy:** Highest (94%+)

### GPU Acceleration

For 10x faster OCR processing with NVIDIA GPU:

```bash
# In .env
PADDLE_DEVICE=gpu
CUDA_VISIBLE_DEVICES=0  # or 0,1 for multi-GPU

# In docker-compose.yml, for worker_ocr services:
# Uncomment these lines:
# runtime: nvidia
# environment:
#   - NVIDIA_VISIBLE_DEVICES=all
```

**Check GPU status:**
```bash
docker-compose exec worker_ocr_1 nvidia-smi
```

---

## 🚀 Running Locally

### Terminal 1: Start Core Services
```bash
# Start Redis, PostgreSQL, API
docker-compose up postgres redis api

# Or just what you need:
docker run -p 6379:6379 redis:7-alpine
```

### Terminal 2: Start a Worker
```bash
# Run preprocessing worker
cd invoice.scanner.processing
celery -A tasks.celery_app worker -Q preprocessing -l info

# Eller OCR worker
celery -A tasks.celery_app worker -Q ocr -l info

# Eller LLM worker
celery -A tasks.celery_app worker -Q llm -l info
```

### Terminal 3: Monitor (Flower)
```bash
# Flower dashboard (real-time task monitoring)
celery -A tasks.celery_app inspect active

# Eller via web UI
open http://localhost:5555
```

### Terminal 4: Test Upload
```bash
# Upload a test invoice
curl -X POST http://localhost:5000/documents/upload \
  -F "file=@test_invoice.pdf" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check processing status
curl http://localhost:5000/documents/{doc_id}/processing-status
```

---

## 📊 Monitoring & Debugging

### Flower Web Dashboard

```bash
# Access via browser
open http://localhost:5555

# Shows:
- ✅ Successful tasks
- ❌ Failed tasks
- ⏱️ Task execution times
- 📈 Worker stats
- 🔍 Task arguments & results
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker_ocr_1
docker-compose logs -f worker_llm_1
docker-compose logs -f api

# Follow specific task
docker-compose logs -f | grep "document_id"
```

### Common Issues

#### Issue: "No LLM provider configured"
```
Solution: Check .env file has OPENAI_API_KEY or ANTHROPIC_API_KEY or GOOGLE_API_KEY
```

#### Issue: "PaddleOCR not available"
```
Solution: pip install paddlepaddle paddleocr
(Or already done via requirements.txt)
```

#### Issue: "GPU not detected"
```
Solution: 
1. Check nvidia-docker is installed: nvidia-docker --version
2. Uncomment runtime: nvidia in docker-compose.yml
3. Rebuild: docker-compose build worker_ocr_1
```

#### Issue: "Task timeout after 5 minutes"
```
Solution: Task failed after max retries
Check logs for actual error, likely LLM API timeout
Increase timeouts in config/celery_config.py if needed
```

---

## 🔄 Task Retry & Error Handling

### Automatic Retries

Alla tasks har automatic exponential backoff:

```
Preprocessing:  3 retries × 1min = max 3 minuter
OCR:            3 retries × 2min = max 6 minuter  
LLM:            3 retries × 5min = max 15 minuter (API calls are slow)
Extraction:     2 retries × 1min = max 2 minuter
Evaluation:     2 retries × 1min = max 2 minuter
```

### Status Tracking

Document status uppdateras i realtid:
```
uploaded → preprocessing → preprocessed → 
ocr_extracting → ocr_extracted → 
predicting → predicted → 
extraction → extracted → 
evaluation → evaluation_complete → 
approved/manual_review
```

---

## 📈 Performance Metrics

### Typical Processing Time

**Without GPU:**
```
Preprocessing:     2-3 sec
OCR (CPU):        10-15 sec
LLM:              5-10 sec
Extraction:       1-2 sec
Evaluation:       0.5-1 sec
─────────────────────────
Total:            19-31 sec per invoice
```

**With GPU (CUDA):**
```
Preprocessing:     2-3 sec
OCR (GPU):        1-2 sec (10x faster!)
LLM:              5-10 sec
Extraction:       1-2 sec
Evaluation:       0.5-1 sec
─────────────────────────
Total:            10-18 sec per invoice (50% faster!)
```

### Scalability

**Single machine (8 CPU cores, 16GB RAM):**
- ~100-150 invoices/hour med CPU
- ~200-300 invoices/hour med GPU

**Multiple machines (Kubernetes):**
# Add workers for linear scaling
- Per worker: +20-30 invoices/hour

---

## 🔐 Security

### API Keys
```bash
# Keep .env secrets in production
# Use AWS Secrets Manager or similar

# Rotate keys regularly
# Don't commit .env to git (use .env.example)
```

### Data Privacy
```bash
# All processing happens locally (except LLM API calls)
# Processed files stored in /app/documents/processed/
# Results stored in PostgreSQL

# Consider encrypting sensitive data in DB if needed
```

---

## 📚 Examples

### Use OpenAI for LLM

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

### Use Gemini for LLM

```bash
# .env
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash
```

### Use Anthropic for LLM

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Enable GPU for OCR

```bash
# .env
PADDLE_DEVICE=gpu

# docker-compose.yml - uncomment for worker_ocr services
runtime: nvidia
```

---

## 🛠️ Development

### Adding a New Processing Step

1. Create task in `tasks/new_step_tasks.py`
2. Create processor in `processors/new_processor.py`
3. Add to task chain in `document_tasks.py`
4. Update config routing if needed

### Testing Locally

```bash
# Start services
docker-compose up postgres redis

# Run worker
cd invoice.scanner.processing
celery -A tasks.celery_app worker -Q ocr -l debug

# Upload test file
curl -X POST http://localhost:5000/documents/upload \
  -F "file=@sample_invoice.pdf"
```

### Running Tests

```bash
# (Future: add pytest)
# For now, use Flower dashboard to monitor
```

---

## 📞 Support & Troubleshooting

### Check System Health

```bash
# Redis health
docker-compose exec redis redis-cli ping
# Output: PONG

# PostgreSQL health
docker-compose exec postgres pg_isready
# Output: accepting connections

# Worker status
celery -A tasks.celery_app inspect active
celery -A tasks.celery_app inspect stats
```

### Common Commands

```bash
# Purge failed tasks
celery -A tasks.celery_app purge

# List workers
celery -A tasks.celery_app inspect active_queues

# Get worker stats
celery -A tasks.celery_app inspect stats

# Reset failed tasks counter
celery -A tasks.celery_app control pool_restart

# Check task status
celery -A tasks.celery_app inspect result {task_id}
```

---

## 📖 Documentation

- [Celery Documentation](https://docs.celeryproject.org/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [LangChain](https://python.langchain.com/)
- [Redis](https://redis.io/)

---

## License

Same as Invoice Scanner

---

**Last Updated:** December 2024  
**Version:** 1.0.0
