# Invoice Scanner - Quick Start Guide

This guide gives you everything you need to get started with Invoice Scanner processing service.

## 📋 Prerequisites

```bash
# Check installations
docker --version        # >= 20.10
docker-compose --version # >= 1.29
git --version          # Installed

# Optional: GPU support
nvidia-docker --version # For CUDA (if you have GPU)
```

## 🚀 5-Minute Setup

### Step 1: Clone & Navigate
```bash
cd invoice.scanner
```

### Step 2: Configure Environment
```bash
# Copy template
cp invoice.scanner.processing/.env.example .env

# Edit .env and add your API keys:
# - OPENAI_API_KEY=sk-... (recommended)
# - ANTHROPIC_API_KEY=sk-ant-... (alternative)
# - GOOGLE_API_KEY=AIza... (alternative)

nano .env  # Or open .env in your editor
```

### Step 3: Start Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Should show:
# NAME                             STATUS
# invoice.scanner.postgres         Up (healthy)
# invoice.scanner.redis            Up (healthy)
# invoice.scanner.api              Up
# invoice.scanner.processing       Up
# invoice.scanner.worker.preprocessing.1   Up
# invoice.scanner.worker.preprocessing.2   Up
# invoice.scanner.worker.ocr.1             Up
# invoice.scanner.worker.llm.1             Up
# invoice.scanner.worker.extraction.1      Up
# invoice.scanner.flower           Up
```

### Step 4: Verify Setup
```bash
# Check Redis
docker-compose exec redis redis-cli ping
# Response: PONG

# Check PostgreSQL
docker-compose exec db pg_isready
# Response: accepting connections

# Check API is running
curl http://localhost:5000/health
# Response: Should return 200 OK (if health endpoint exists)
```

### Step 5: Open Dashboards
```bash
# Frontend
open http://localhost:3000

# API
open http://localhost:5000

# Monitoring (Flower - best for debugging)
open http://localhost:5555
```

## 📤 Test Upload & Processing

### Option A: Via cURL (Command Line)

```bash
# 1. Get authentication token (if required)
# First, login via the web UI or get a token

# 2. Upload a test invoice
curl -X POST http://localhost:5000/documents/upload \
  -F "file=@path/to/invoice.pdf" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response example:
# {
#   "message": "Document uploaded and queued for processing",
#   "document": {
#     "id": "abc-123-def",
#     "status": "preprocessing"
#   },
#   "task_id": "celery-task-789"
# }

# 3. Poll for status (replace doc_id with actual ID)
curl http://localhost:5000/documents/abc-123-def/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
# {
#   "status": "preprocessing",  # Updates as processing continues
#   "progress": {
#     "percentage": 33
#   },
#   "quality_score": null
# }
```

### Option B: Via Frontend UI

1. Open http://localhost:3000
2. Login with your credentials
3. Navigate to "Scan Invoice"
4. Click "Choose File" and select a PDF/JPG
5. Watch real-time progress

### Option C: Via Python Script

```python
import requests
import time

API_URL = "http://localhost:5000"
TOKEN = "your-auth-token"

# Upload
files = {'file': open('invoice.pdf', 'rb')}
headers = {'Authorization': f'Bearer {TOKEN}'}
response = requests.post(f"{API_URL}/documents/upload", files=files, headers=headers)

doc_id = response.json()['document']['id']
print(f"Uploaded: {doc_id}")

# Poll status
while True:
    status_response = requests.get(
        f"{API_URL}/documents/{doc_id}/status",
        headers=headers
    )
    data = status_response.json()
    print(f"Status: {data['status']} ({data['progress']['percentage']}%)")
    
    if data['status'] in ['approved', 'manual_review', 'error']:
        print(f"Final status: {data['status']}")
        print(f"Quality score: {data['quality_score']}")
        break
    
    time.sleep(2)  # Check every 2 seconds
```

## 🔍 Monitoring & Debugging

### View Real-Time Task Status
```bash
# Open Flower dashboard
open http://localhost:5555

# Shows:
# - Tasks in progress
# - Failed tasks
# - Execution times
# - Worker stats
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker_ocr_1
docker-compose logs -f worker_llm_1

# Follow specific document processing
docker-compose logs -f | grep "abc-123-def"
```

### Check Worker Status

```bash
# SSH into processing container
docker-compose exec processing bash

# Inside container:
celery -A tasks.celery_app inspect active      # Current tasks
celery -A tasks.celery_app inspect active_queues # Queues
celery -A tasks.celery_app inspect stats       # Worker stats
celery -A tasks.celery_app inspect reserved    # Reserved tasks
```

## 🔧 Configuration

### Change LLM Provider

```bash
# In .env, comment/uncomment:

# Option 1: OpenAI (rekommenderad)
OPENAI_API_KEY=sk-your-key
# GOOGLE_API_KEY=
# ANTHROPIC_API_KEY=

# Option 2: Google Gemini
# OPENAI_API_KEY=
GOOGLE_API_KEY=AIza-your-key
# ANTHROPIC_API_KEY=

# Option 3: Anthropic Claude
# OPENAI_API_KEY=
# GOOGLE_API_KEY=
ANTHROPIC_API_KEY=sk-ant-your-key

# Restart services
docker-compose restart worker_llm_1
```

### Enable GPU Acceleration (OCR 10x Faster)

```bash
# 1. Check if you have NVIDIA GPU
nvidia-smi

# 2. Install nvidia-docker
# macOS: brew install nvidia-docker
# Linux: https://github.com/NVIDIA/nvidia-docker

# 3. In docker-compose.yml, uncomment for worker_ocr_1:
# runtime: nvidia
# environment:
#   NVIDIA_VISIBLE_DEVICES: 0
#   PADDLE_DEVICE: gpu

# 4. Rebuild and restart
docker-compose build worker_ocr_1
docker-compose up -d worker_ocr_1

# 5. Verify GPU usage
docker-compose exec worker_ocr_1 nvidia-smi
```

### Scale Workers

```bash
# Add more preprocessing workers
docker-compose up -d --scale worker_preprocessing_1=4

# Or manually start additional instances
docker-compose up -d worker_preprocessing_3
docker-compose up -d worker_preprocessing_4

# View all workers
docker-compose ps | grep worker
```

## 🐛 Common Issues

### Issue: "Can't connect to Redis"
```
Error: REDIS connection error
Solution:
  1. Check Redis is running: docker-compose ps redis
  2. Restart Redis: docker-compose restart redis
  3. Check .env REDIS_URL is correct
```

### Issue: "No LLM provider configured"
```
Error: ValueError: No LLM provider configured
Solution:
  1. Edit .env and set at least one API key
  2. Restart worker: docker-compose restart worker_llm_1
  3. Verify: docker-compose logs -f worker_llm_1 | grep "provider"
```

### Issue: "OCR takes too long"
```
Problem: OCR step takes 15-30 seconds per document
Solution:
  1. Enable GPU (see above) - reduces to 1-2 seconds
  2. Or increase OCR workers: scale worker_ocr_1 to 2-3 instances
  3. Or switch OCR engine in code: tesseract vs paddleocr
```

### Issue: "Task timeouts after 5 minutes"
```
Error: Task timeout / SoftTimeLimitExceeded
Solution:
  1. Check which step is timing out (view logs)
  2. If LLM: API is slow, increase timeout in config/celery_config.py
  3. If OCR: enable GPU or increase worker resources
  4. Retry: tasks retry automatically with exponential backoff
```

### Issue: "Processing doesn't start after upload"
```
Problem: Document stays in "preprocessing" status forever
Solution:
  1. Check workers are running: docker-compose ps | grep worker
  2. Check Redis: docker-compose exec redis redis-cli ping
  3. Restart all workers: docker-compose restart worker_preprocessing_1
  4. Check logs: docker-compose logs -f worker_preprocessing_1
```

## 📊 Performance Expectations

### Without GPU
```
Document: Standard A4 invoice PDF

Step times:
  Preprocessing: 2-3 sec
  OCR: 10-15 sec  ← slow
  LLM: 5-10 sec
  Extraction: 1-2 sec
  Evaluation: 0.5-1 sec
  ─────────────────────
  Total: 19-31 seconds per invoice
  
Throughput: ~150 invoices/hour on single machine
```

### With GPU (NVIDIA CUDA)
```
Document: Same as above

Step times:
  Preprocessing: 2-3 sec
  OCR: 1-2 sec  ← 10x faster!
  LLM: 5-10 sec
  Extraction: 1-2 sec
  Evaluation: 0.5-1 sec
  ─────────────────────
  Total: 10-18 seconds per invoice
  
Throughput: ~300 invoices/hour on single machine (50% faster)
```

## 🧹 Cleanup

```bash
# Stop all services
docker-compose down

# Stop and remove data (CAREFUL - deletes database!)
docker-compose down -v

# Remove processed files
rm -rf invoice.scanner.api/documents/processed/*

# View disk usage
docker-compose exec postgres du -sh /var/lib/postgresql/data
```

## 📈 Next Steps

1. **Integrate with your system** - Use API endpoints in your app
2. **Customize processors** - Modify prompts, validation rules
3. **Add monitoring** - Set up alerts for failed documents
4. **Optimize LLM** - Test different models for cost/accuracy
5. **Deploy to production** - Use Kubernetes or similar

## 📚 Full Documentation

- [Full Architecture](./ARCHITECTURE.md)
- [Processing Service README](./invoice.scanner.processing/README.md)
- [API Documentation](./invoice.scanner.api/main.py) - Inline comments

## 💬 Support

Check logs first:
```bash
docker-compose logs -f
```

Common files to review:
- [config/celery_config.py](./invoice.scanner.processing/config/celery_config.py)
- [config/llm_providers.py](./invoice.scanner.processing/config/llm_providers.py)
- [tasks/document_tasks.py](./invoice.scanner.processing/tasks/document_tasks.py)

---

**Happy processing! 🎉**
