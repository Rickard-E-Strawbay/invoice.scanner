# FASE 6E - Quick Reference Card

## 🎯 What This Solves

Document processing now works identically in:
- **LOCAL**: `docker-compose` → Celery workers → Redis
- **CLOUD**: GCP Cloud Functions → Pub/Sub

**Same API code** - just environment variables change!

---

## 📁 Files Created

```
invoice.scanner.api/lib/processing_backend.py (NEW)
├── ProcessingBackend (abstract)
├── LocalCeleryBackend (for docker-compose)
├── CloudFunctionsBackend (for GCP)
├── MockBackend (for testing)
└── get_processing_backend() factory

cloud_functions_processing.py (NEW)
├── cf_preprocess_document
├── cf_extract_ocr_text
├── cf_predict_invoice_data
├── cf_extract_structured_data
└── cf_run_automated_evaluation

deploy_cloud_functions.sh (NEW)
├── Creates Pub/Sub topics
├── Deploys all 5 functions
└── Auto-detects env vars

.env.cloud.functions.yaml (NEW)
└── Environment variables template

requirements_cloud_functions.txt (NEW)
└── Cloud Functions dependencies

CLOUD_FUNCTIONS_DEPLOYMENT.md (NEW)
└── Complete deployment guide

FASE_6E_SUMMARY.md (NEW)
└── Implementation summary

SYSTEM_PROMPT.md (UPDATED)
└── Added FASE 6E documentation
```

---

## 🚀 Quick Start

### LOCAL (docker-compose)
```bash
# Already works! Just run:
docker-compose down && docker-compose up -d --build

# Upload test document:
curl -X POST http://localhost:5001/documents/upload \
  -F "file=@test.pdf" \
  -H "Authorization: Bearer TOKEN"

# Monitor:
curl http://localhost:5001/documents/{id}/status \
  -H "Authorization: Bearer TOKEN"
```

### CLOUD (GCP)
```bash
# 1. Deploy Cloud Functions (one command)
./deploy_cloud_functions.sh strawbayscannertest europe-west1

# 2. Set Cloud Run API env var
gcloud run services update invoice-scanner-api-test \
  --update-env-vars=PROCESSING_BACKEND=cloud_functions \
  --region=europe-west1 \
  --project=strawbayscannertest

# 3. Same upload/status endpoints work!
```

---

## 🔧 How It Works

### Configuration

| Environment | Variable | Value |
|---|---|---|
| LOCAL | `PROCESSING_BACKEND` | `local` (auto-detect) |
| LOCAL | `PROCESSING_SERVICE_URL` | `http://localhost:5002` |
| CLOUD | `PROCESSING_BACKEND` | `cloud_functions` |
| CLOUD | `GCP_PROJECT_ID` | `strawbayscannertest` |

### Auto-Detection

```python
# Code automatically selects backend:
backend = get_processing_backend()

# Priority:
# 1. PROCESSING_BACKEND env var (explicit)
# 2. GCP_PROJECT_ID env var (auto-detect cloud)
# 3. Default to 'local' (docker-compose)
```

---

## 📊 Architecture

### LOCAL PIPELINE
```
API upload → LocalCeleryBackend → 
  HTTP POST processing_http:5002 → 
    Celery.delay(document_id) → 
      Redis queue → 
        Workers (preprocess → ocr → llm → extraction → eval) →
          Database status updates
```

### CLOUD PIPELINE
```
API upload → CloudFunctionsBackend →
  Pub/Sub publish(document-processing) →
    cf_preprocess_document (triggered) →
      Pub/Sub publish(document-ocr) →
        cf_extract_ocr_text (triggered) →
          ... (continue 3 more) →
            Database status updates
```

---

## ✅ Integration Points

### API (`main.py`)
```python
# Initialize backend (auto-selects based on env)
processing_backend = init_processing_backend()

# In upload_document():
result = processing_backend.trigger_task(doc_id, company_id)
task_id = result['task_id']

# Status endpoint already works:
GET /documents/{id}/status → Database query
```

### Processing Service (http_service.py)
```
No changes needed - already has:
POST /api/tasks/orchestrate → Celery task queue
GET  /api/tasks/status/{id} → Task status
```

### Cloud Functions (cloud_functions_processing.py)
```
5 new functions (one per stage):
- Each triggered by Pub/Sub message
- Updates database status
- Publishes to next-stage topic
```

---

## 🧪 Testing

### LOCAL (Verify)
```bash
# 1. Check processing_http is responding
curl http://localhost:5002/health

# 2. Upload document
curl -X POST http://localhost:5001/documents/upload \
  -F "file=@test.pdf" \
  -H "Authorization: Bearer TOKEN"

# 3. Monitor processing
while true; do
  curl http://localhost:5001/documents/{id}/status \
    -H "Authorization: Bearer TOKEN" | jq .status
  sleep 2
done

# 4. Check Celery workers
docker logs invoice.scanner.worker.preprocessing.1 | tail -20
```

### CLOUD (Deploy & Test)
```bash
# 1. Deploy functions
./deploy_cloud_functions.sh strawbayscannertest

# 2. Check deployment
gcloud functions list --project=strawbayscannertest

# 3. Check Pub/Sub topics
gcloud pubsub topics list --project=strawbayscannertest

# 4. Test via API (same endpoint, different backend)
# ... same curl commands as local ...

# 5. Monitor Cloud Functions
gcloud functions logs read cf-preprocess-document \
  --limit 50 \
  --project=strawbayscannertest
```

---

## 🎓 Key Concepts

### Backend Abstraction
- **Interface**: `ProcessingBackend` ABC
- **Implementations**: LocalCelery, CloudFunctions, Mock
- **Selection**: Automatic based on environment
- **Benefit**: Single API code works everywhere

### Pub/Sub Orchestration (Cloud)
- **Topics**: 5 topics (one per stage transition)
- **Functions**: 5 functions (one per processing stage)
- **Messages**: `{document_id, company_id, stage}`
- **Flow**: Serial (each function publishes to next)
- **Guarantee**: At-least-once delivery (idempotent)

### Database as State Store
- **Source of Truth**: documents.status column
- **Updates**: Each stage updates status
- **Polling**: API queries database for current status
- **Resilience**: Survives function/queue failures

---

## 📈 Performance

| Aspect | LOCAL | CLOUD |
|--------|-------|-------|
| Total Time | ~25s | ~25s + propagation |
| Throughput | Limited by workers | Auto-scales with Pub/Sub |
| Cost | Fixed (server) | Variable (per execution) |
| Cold Start | None | ~1s first time |
| Monitoring | docker logs | Cloud Logging |

---

## 🔒 Security

✅ **LOCAL**: Docker network isolation, no external access  
✅ **CLOUD**: IAM auth, Private IP SQL, Secret Manager  

---

## 📖 Read More

- `SYSTEM_PROMPT.md` → FASE 6E section (comprehensive)
- `CLOUD_FUNCTIONS_DEPLOYMENT.md` → Step-by-step guide
- `FASE_6E_SUMMARY.md` → Full implementation details
- `processing_backend.py` → Code comments and docstrings
- `cloud_functions_processing.py` → Function-level documentation

---

## 🚨 Common Issues

| Problem | Solution |
|---------|----------|
| `ConnectionError: processing service unavailable` | Check docker-compose is running (`docker ps`) |
| Cloud Functions not triggering | Check Pub/Sub subscription exists and has permissions |
| Database connection timeout | Verify VPC Access Connector is configured |
| Status stuck on 'preprocessing' | Check worker logs: `docker logs invoice.scanner.worker.preprocessing.1` |

---

## ✨ Next Steps

1. ✅ Test locally (docker-compose)
2. Deploy Cloud Functions (`./deploy_cloud_functions.sh`)
3. Test in Cloud (Cloud Run API)
4. Implement actual processing (replace mocked 5s delays)
5. Monitor production
6. Optimize costs and performance

---

## 👨‍💻 Developer Notes

**Developing locally?**
- Use `docker-compose` - includes everything
- PROCESSING_BACKEND auto-selects to 'local'
- Changes to code don't require redeploy
- Redis/workers restart with `docker-compose down && up`

**Deploying to Cloud?**
- Use `./deploy_cloud_functions.sh` - one command
- Set Cloud Run env vars for PROCESSING_BACKEND=cloud_functions
- Same code works - no changes needed
- Monitor via Cloud Logging and Pub/Sub console

**Adding new processing stage?**
- Create Cloud Function
- Create new Pub/Sub topic
- Add topic to previous function's publish call
- Add function to deploy script
- Test locally first, then deploy

---

**Created**: December 26, 2025  
**Status**: ✅ COMPLETE - Ready for testing and deployment
