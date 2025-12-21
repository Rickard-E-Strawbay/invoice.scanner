# Development Setup Guide

## Quick Start

### 1. Start all services
```bash
./dev-start.sh
```

This will:
- Start all Docker containers (API, Frontend, Workers, Database, Redis)
- Display the startup status
- Print URLs where services are available

### 2. Monitor processing in another terminal
```bash
./dev-monitor.sh
```

This shows live logs from:
- `worker_preprocessing_1` - Image processing worker
- `processing_http` - HTTP service for task triggering
- `api` - Flask API server

### 3. (Optional) Set custom log level
```bash
CELERY_LOG_LEVEL=debug ./dev-start.sh
```

Then in another terminal:
```bash
CELERY_LOG_LEVEL=debug ./dev-monitor.sh
```

Available log levels:
- `debug` - Very detailed, shows every operation
- `info` - Standard level, shows key events (default)
- `warning` - Only warnings and errors
- `error` - Only errors

---

## Manual Service Management

Start a specific service:
```bash
docker-compose up -d worker_preprocessing_1
```

View logs for a service:
```bash
docker-compose logs -f worker_preprocessing_1
```

View logs with tail:
```bash
docker-compose logs -f --tail=100 worker_preprocessing_1
```

Stop all services:
```bash
docker-compose down
```

---

## Testing the Restart Button

### Via API
```bash
curl -X POST http://localhost:5001/documents/<doc_id>/restart \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

### Via Frontend
1. Go to http://localhost:3000
2. Login
3. Click the restart button on a document

### Via Test Script
```bash
python3 /tmp/test_restart_auth.py
```

---

## Understanding the Processing Pipeline

When you click restart:

```
1. Frontend/API
   ↓
2. API calls: POST /documents/{id}/restart
   ↓
3. Processing HTTP Service (port 5002)
   - Receives: {document_id, company_id}
   - Creates Celery task
   ↓
4. Task routed to "preprocessing" queue
   ↓
5. Worker picks up task and executes:
   a) preprocess_document - Image normalization
   b) extract_ocr_text - OCR extraction
   c) predict_invoice_data - LLM analysis
   d) extract_structured_data - Data structuring
   e) run_automated_evaluation - Validation
   ↓
6. Results stored in database
   Status changes: preprocessing → ocr → llm → extraction → evaluation → completed
```

---

## Monitoring Redis Queue

View current queues:
```bash
docker exec invoice.scanner.redis redis-cli -n 0 KEYS "celery*"
```

View tasks in preprocessing queue:
```bash
docker exec invoice.scanner.redis redis-cli -n 0 LLEN "preprocessing"
```

Inspect a task:
```bash
docker exec invoice.scanner.redis redis-cli -n 0 GET "celery-task-meta-<task_id>"
```

---

## Common Issues

### Tasks not executing
1. Check worker is running: `docker ps | grep worker_preprocessing`
2. Check task routing: `docker-compose logs worker_preprocessing_1 | grep "queues"`
3. Check Redis: `docker-compose logs redis`

### Logs not showing
- Try: `docker-compose logs -f --tail=50 worker_preprocessing_1`
- Check container is running: `docker-compose ps`

### Import errors
- Rebuild: `docker-compose build --no-cache processing`
- Restart: `docker-compose restart worker_preprocessing_1`

---

## Performance Tips

### For development
- Use `CELERY_LOG_LEVEL=debug` only when troubleshooting
- Watch specific worker: `docker-compose logs -f worker_preprocessing_1 | grep -E "Received|SUCCESS|ERROR"`
- Use separate terminals for dev-start and dev-monitor

### For debugging a task
1. Trigger restart
2. Get task ID from response or logs
3. Check task status: `docker exec invoice.scanner.redis redis-cli -n 0 GET "celery-task-meta-<id>"`
4. View detailed logs: `docker-compose logs worker_preprocessing_1 | grep <task_id>`
