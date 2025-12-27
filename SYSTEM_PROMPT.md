# System Prompt för Invoice Scanner Projekt

---

## ⚠️ AI-ASSISTENTENS KRITISKA INSTRUKTIONER

### ÖVERSTA PRIORITET - Läs innan du gör något
1. **LÄSA DENNA FIL** innan någon operation
2. **FRÅGA innan komplexitet** - inte bara implementera
3. **RESPEKTERA befintliga decisions** - inte överskriv
4. **TESTA lokalt innan Cloud** - docker-compose först

### REGLER SOM MÅSTE FÖLJAS
- ✅ **ALDRIG** skapa docker-compose files utan att fråga
- ✅ **ALDRIG** ändra .github/workflows/pipeline.yml utan att fråga
- ✅ **ALDRIG** manuellt deploy till Cloud Run (pipeline gör det)
- ✅ **ALDRIG** manuellt build till GCP registries (pipeline gör det)
- ✅ **FRÅGA FÖRST** innan ändringar i GCP Secret Manager
- ✅ **FRÅGA FÖRST** innan ändringar i Cloud SQL config

### VÅR PROCESS (ej pipeline)
1. Läs vad som redan finns (`ls`, `grep`, `git log`)
2. Förstå arkitekturen
3. Fråga användaren: "Vill du att jag ska [X] eller [Y]?"
4. Plan + dokumentera
5. Test lokalt (docker-compose)
6. Verifiera git diff
7. Commit med kontext

### BEFINTLIGA DECISIONS - RESPEKTERA
| Decision | Varför | Ändra INTE |
|----------|--------|----------|
| pg8000 driver | Cloud SQL Connector krävs | Inte psycopg2 |
| DATABASE_* vars | Standardiserad naming | Inte DB_* mix |
| Single pipeline.yml | Clean + maintainable | Inte 3 files |
| Cloud SQL Private IP | Säkerhet | Inte public |
| RealDictCursor wrapper | Backward compatibility | Inte raw pg8000 |
| docker-compose.yml | Source of truth | Inte .local variant |

### VID PROBLEM
Ordning: Logs (GitHub Actions) → Logs (Cloud Run) → Logs (Cloud SQL) → FIX KOD → RE-PUSH

### Användarens Preferenser
- Vill ha ENKLA lösningar först
- Vill att jag ska FRÅGA innan komplexitet
- Gillar TYDLIGA instruktioner
- Vill FÖRSTÅ vad som görs, inte bara att det görs
- **VIKTIGAST:** Trust the pipeline - det är korrekt konfigurerat

---

## 📋 QUICK REFERENCE - Läs detta först!

**NUVARANDE ARKITEKTUR (Dec 27, 2025):**

| Komponenter | Status | Beskrivning |
|-------------|--------|------------|
| **LOCAL (docker-compose)** | ✅ Ready | 4 services: API, Frontend, PostgreSQL, Redis |
| **LOCAL Processing** | ✅ Ready | Cloud Functions Framework på :9000 (external) |
| **GCP Cloud Functions** | ✅ Ready | 5 functions (preprocess, ocr, llm, extraction, evaluation) |
| **Deployment Script** | ✅ Ready | cloud_functions/deploy.sh för TEST + PROD |
| **Database** | ✅ Ready | Cloud SQL TEST + PROD |
| **Storage** | ✅ Ready | Local volumes (local) + GCS (cloud) |
| **CI/CD** | ✅ Ready | GitHub Actions pipeline.yml |

**Enkelt sagt:**
- ✅ Samma kod kör lokalt och i GCP
- ✅ Cloud Functions Framework simulerar GCP lokalt
- ✅ Ingen Celery workers - renare arkitektur
- ✅ Ready to deploy till GCP TEST och PROD

---

**Overall Progress:** FASE 6E COMPLETE - Cloud Functions Unified Architecture

| FASE | Status | Details | Last Updated |
|------|--------|---------|--------------|
| FASE 0-5 | ✅ 100% | Infrastructure, Secrets, Cloud SQL, Cloud Run | Dec 26 |
| FASE 6 | ✅ 100% | Storage Service (Local + GCS hybrid) | Dec 26 |
| **FASE 6E** | ✅ 100% | Unified Cloud Functions Architecture | **Dec 27** |
| **FASE 7** | 🚀 IN PROGRESS | Deploy to GCP TEST - Local → Cloud deploy → Cloud test | **Dec 27** |
| **FASE 7** | � IN PROGRESS | Deploy Cloud Functions to GCP TEST | **Dec 27 - STARTING NOW** |
| **FASE 8** | 🔄 READY | Deploy Cloud Functions to GCP PROD | Ready after FASE 7 ✅ |

---

## 🎯 CURRENT STATE - FASE 6E COMPLETE (Dec 27)

### Architecture Changed
```
BEFORE (Celery-based):
├── LOCAL: invoice.scanner.processing/ (7 workers + processing_http)
└── CLOUD: cloud_functions_processing.py (5 Cloud Functions)

AFTER (Unified Cloud Functions):
├── LOCAL: invoice.scanner.cloud.functions/ → ./local_server.sh (functions-framework :9000)
└── CLOUD: invoice.scanner.cloud.functions/ → ./deploy.sh (5 Cloud Functions on GCP)

RESULT: Same code everywhere ✅
```

### What Changed
1. ✅ Removed: `invoice.scanner.processing/` (Celery workers not needed)
2. ✅ Removed: All Celery references from docker-compose.yml
3. ✅ Simplified: docker-compose from 14 → 4 services
4. ✅ Created: cloud_functions/ folder with complete structure
5. ✅ Created: dev-start.sh (starts docker-compose + Cloud Functions Framework in new Terminal)
6. ✅ Updated: docker-compose.yml (4 lean services)

### Folder Structure (NEW)
```
invoice.scanner/
├── docker-compose.yml          (4 services: api, frontend, db, redis)
├── dev-start.sh               (Start docker-compose + Cloud Functions Framework)
├── invoice.scanner.cloud.functions/
│   ├── main.py               (5 Cloud Functions)
│   ├── requirements.txt       (functions-framework + deps)
│   ├── local_server.sh        (Run functions-framework :9000)
│   ├── deploy.sh              (Deploy to GCP TEST/PROD)
│   ├── .env.yaml              (Config vars)
│   └── README.md              (Instructions)
├── invoice.scanner.api/       (Flask API)
├── invoice.scanner.frontend.react/ (React UI)
└── invoice.scanner.db/        (Database init)
```

### Services Running
```
docker-compose (Terminal 1):
├─ api:5001        (Flask API)
├─ frontend:8080   (React + Nginx)
├─ db:5432         (PostgreSQL)
└─ redis:6379      (Cache)

cloud_functions (Terminal 2):
└─ :9000           (functions-framework)
```

---

## 🚀 HOW TO USE

### Start Everything Locally
```bash
# Starts everything: docker-compose + Cloud Functions Framework in new Terminal
./dev-start.sh

# Or manually (two terminals):

# Terminal 1: Docker services
docker-compose up -d

# Terminal 2: Cloud Functions Framework
cd invoice.scanner.cloud.functions && ./local_server.sh
```

### Test Document Processing
```bash
# 1. Login
curl -X POST http://localhost:5001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "rickard@strawbay.io", "password": "Test123"}' \
    -c /tmp/cookies.txt

# 2. Upload document
curl -X POST http://localhost:5001/auth/documents/upload \
    -b /tmp/cookies.txt \
    -F "file=@/tmp/test.pdf"

# 3. Check status
curl -X GET http://localhost:5001/auth/documents/{doc_id}/status \
    -b /tmp/cookies.txt
```

### Deploy to GCP
```bash
# TEST
cd invoice.scanner.cloud.functions
./deploy.sh strawbayscannertest europe-west1

# PROD
./deploy.sh strawbayscannerprod europe-west1
```

---

## 📋 QUICK REFERENCE - Läs detta först!

| Vad | Status | Vad gör vi |
|-----|--------|-----------|
| **Local Docker** | ✅ Ready | 4 services (api, frontend, db, redis) |
| **pg8000 Driver** | ✅ Complete | Testad med pg8000_wrapper + RealDictCursor |
| **Database** | ✅ Ready | Cloud SQL TEST+PROD initialiserad |
| **GitHub Actions** | ✅ Ready | Pipeline.yml (single file, 3 jobs) |
| **GCP Secrets** | ✅ Ready | 12 secrets i Secret Manager |
| **Docker Images** | ✅ Ready | Api, Frontend pushed till registries |
| **Cloud Run TEST** | ✅ Live | API + Frontend deployed & working |
| **Cloud Functions** | ✅ Ready | 5 functions i cloud_functions/main.py |
| **Processing Backend** | ✅ UNIFIED | LocalCeleryBackend → LocalCloudFunctionsBackend |
| **Local Processing** | ✅ READY | Cloud Functions Framework :9000 |
| **NEXT STEP** | 👉 DO THIS | Test locally, then deploy to GCP TEST |

**Enkelt sagt:**
- Cloud Run TEST är live och fungerar perfekt
- Admin panel fungerar
- Document processing lokalt: ✅ READY (Cloud Functions Framework)
- Document processing molnet: ✅ READY (5 Cloud Functions) - Ready to deploy
- **Samma kod överallt** - ingen Celery komplexitet
| FASE 6D | ✅ 100% | Configure environment-aware storage (local vs GCS) | **Dec 26 17:10** |
| **FASE 6E** | ✅ 100% | Processing Backend Abstraction + Cloud Functions | **Dec 26** |
| **FASE 7** | 🔄 IN PROGRESS | Deploy Cloud Functions to GCP TEST - Detailed steps | **Dec 26** |
| **FASE 8** | 📋 PREPARED | Deploy Cloud Functions to GCP PROD - Same steps | **Ready** |
| FASE 9 | 0% | Monitoring, Production validation | Future |

### 🚀 WHAT'S READY NOW (Dec 26, 22:30)

✅ **Infrastructure & Code:**
- All 14 Docker containers build and run locally (fresh rebuild verified)
- pg8000 database driver unified across all modules (pg8000_wrapper.py in place)
- Database: Cloud SQL TEST + PROD initialized with schemas
- GitHub Actions pipeline.yml configured and ready (single file, 3 conditional jobs)
- All GCP secrets and credentials configured

✅ **Next Action - SIMPLE 3-STEP PROCESS:**
1. **Push to re_deploy_start** → GitHub Actions pipeline.yml:build triggers automatically
2. **Build completes** → pipeline.yml:deploy-test triggers automatically (no approval needed)
3. **TEST Cloud Run services live** → Verify API/Frontend connectivity, then merge to main for PROD

**Current Blockers:** NONE - System is fully ready for deployment

---

## 🎯 FOKUS JUST NU - December 27, 2025 (15:00)

**FASE 6E: COMPLETE ✅ | FASE 7: STARTED 🚀 Deploy Cloud Functions to GCP TEST** Dec 27

### Status December 27, 2025 ✅
1. ✅ Frontend visar `status_name` från databas (inte `status_key`)
2. ✅ API returnerar `status_name` via LEFT JOIN med `document_status` tabell
3. ✅ Cloud Functions har `PROCESSING_SLEEP_TIME` miljövariabel (default 1.0s)
4. ✅ Local Pub/Sub simulator implementerat - end-to-end testning fungerar
5. ✅ `dev-start.sh` startar Cloud Functions i nytt Terminal-fönster
6. ✅ Alla 19 möjliga statuser från `document_status`-tabellen displayas
7. ✅ API timeout ökat till 30 sekunder för pålitlig processering
8. ✅ `.gitignore` uppdaterad - genererade filer uteslutna från git

### Vad som är gjort ✅
- ✅ Unified Cloud Functions arkitektur (samma kod lokalt och i GCP)
- ✅ Local Pub/Sub simulator för end-to-end lokal testning
- ✅ Frontend visar mänskliga status-namn från databas
- ✅ Dokumentbearbetning fungerar lokalt komplett (preprocessing → ocr → llm → extraction → evaluation → completed)
- ✅ Alla statusalternativ implementerade och testade
- ✅ Frontend fixed (fullscreen violation)

### Pipeline status
- **Building:** API + Frontend only
- **Deploying:** API + Frontend to Cloud Run TEST  
- **Processing:** Runs locally via docker-compose (no Cloud Run deployment)

### Nästa steg 👉
**LOCAL TESTING (kan göra nu):**
1. Verifiera frontend kan ladda upp document
2. Verifiera filen sparas i `./documents/raw/` (volume mount)
3. Verifiera processing kan läsa från storage_service
4. Verifiera processing pipeline startar (mockad)

**CLOUD TESTING (när pipeline klar):**
1. Verifiera Cloud Run API mottager upload
2. Verifiera filen sparas i `gs://invoice-scanner-test-docs/raw/`
3. Verifiera dokumentstatus uppdateras i database

### Git Status
- Branch: `re_deploy_start`
- Latest: Removed processing Cloud Run deployment (keeping local)
- Ready: Full storage_service testing lokalt och i Cloud

---

## 🎯 FASE 6: DOCUMENT STORAGE STRATEGY (Dec 26, 16:45)

### Problem
- Cloud Run har **ephemeral filesystem** (raderas vid container restart)
- Local använder Docker volume (`./documents/` mountad)
- Upload endpoint försöker skriva till `/app/documents/raw/` → **fails på Cloud Run**

### Error
```
[upload_document] Error: [Errno 2] No such file or directory: '/app/documents/raw/98863725-c6b8-4170-800b-d66cf4bb57e7.pdf'
```

### Solution: HYBRID APPROACH (Local volumes + GCS)

| Strategi | Local | Cloud | Kostnad | Komplexitet |
|----------|-------|-------|---------|-------------|
| **Hybrid: Volumes + GCS** ⭐⭐ | ✅ | ✅ | Låg | Medel |
| GCS endast | ✗ | ✅ | Låg | Låg |
| Cloud Filestore | ✗ | ✅ | Högt | Låg |

**Valda strategi: HYBRID** för att:
1. ✅ Local dev exakt samma som idag (volumes)
2. ✅ Cloud Run får persistent storage (GCS)
3. ✅ Same code, environment-aware backend

### Implementation Plan (5 Steps)

#### Step 1: Create GCS Bucket
- Projekt: `strawbayscannertest` (TEST), `strawbayproduction` (PROD)
- Bucket name: `invoice-scanner-test-docs` (TEST), `invoice-scanner-prod-docs` (PROD)
- Region: `europe-west1`
- Access: Via Cloud Run service account IAM
- Retention: Standard (no lifecycle policy initially)

#### Step 2: Create Storage Abstraction Layer
- New file: `invoice.scanner.api/lib/storage_service.py`
- Interface: `StorageService` (abstract)
- Implementations:
  - `LocalStorageService`: Read/write from `/app/documents/`
  - `GCSStorageService`: Read/write from GCS bucket
- Selection via environment variable: `STORAGE_TYPE=local|gcs`

#### Step 3: Update Document Endpoints
- `upload_document`: Change from direct file write to `StorageService.save()`
- `get_document`: Change from direct file read to `StorageService.get()`
- `delete_document`: Change to `StorageService.delete()`
- `list_documents`: Change to `StorageService.list()`

#### Step 4: Environment Configuration
- **Local (docker-compose.yml)**: `STORAGE_TYPE=local` → Uses volumes
- **Cloud Run TEST**: `STORAGE_TYPE=gcs` + bucket creds → Uses GCS
- **Cloud Run PROD**: `STORAGE_TYPE=gcs` + separate bucket → Uses GCS

#### Step 5: Data Migration (Optional)
- Script: Copy existing `documents/raw/` to GCS bucket
- Only needed if TEST has existing data

### Code Changes Required
1. Create `storage_service.py` (new file)
2. Update `app.py` - import and use StorageService
3. Update environment configs (docker-compose, Cloud Run env vars)
4. No changes to endpoints - same API, different backend

### Local Compatibility ✅
- **No changes to docker-compose.yml volumes**
- **Same code, different STORAGE_TYPE env var**
- **Works exactly as before locally**

### Success Criteria
- ✅ Local: Files written to `./documents/raw/`
- ✅ Cloud Run TEST: Files written to `gs://invoice-scanner-test-docs/`
- ✅ API response: Same regardless of backend
- ✅ No frontend changes needed

---

## Projekt-specifikt

### Invoice Scanner - Core Info
- **Repo:** https://github.com/Rickard-E-Strawbay/invoice.scanner
- **Branches:** main (PROD) ← PR ← re_deploy_start (TEST)
- **Architecture:** API (Flask) + Frontend (React) + Workers (Celery)
- **Docker:** docker-compose.yml (single source of truth)
- **Deployment:** GitHub Actions (auto-builds + auto-deploys)

### Filer ALDRIG ändra utan att fråga:
- `.github/workflows/pipeline.yml`
- docker-compose.yml (infrastruktur)
- Hele config-system (invoice.scanner.api/config/)
- .env-filer (använd GCP Secret Manager istället)

---

## 🎯 FASE 6E: PROCESSING BACKEND ABSTRACTION (Dec 26 - ✅ COMPLETED)

### Problem Löst
Document processing behövde fungera i två miljöer:
- **LOCAL**: Celery + Redis (docker-compose)
- **CLOUD**: Cloud Functions + Pub/Sub (GCP)

Med **samma API kod** i båda!

### Lösning: Processing Backend Abstraction

**Skapad fil: `invoice.scanner.api/lib/processing_backend.py`**

Abstrakt interface med tre implementeringar:
```python
class ProcessingBackend(ABC):
    def trigger_task(document_id, company_id) → task_id
    def get_task_status(task_id) → status

class LocalCeleryBackend(ProcessingBackend):
    # LOCAL: HTTP POST to processing_http:5002/api/tasks/orchestrate
    # Queue → Redis → Celery Workers → Database status updates

class CloudFunctionsBackend(ProcessingBackend):
    # CLOUD: Publish to Pub/Sub → Cloud Functions trigger
    # Processing via serverless functions, auto-scaling

class MockBackend(ProcessingBackend):
    # TESTING: No-op backend for unit tests
```

### Environment-Aware Initialization

```python
backend = get_processing_backend()  # Auto-selects based on env vars

# LOCAL (docker-compose):
PROCESSING_BACKEND=local  # or auto-detects if PROCESSING_SERVICE_URL set
PROCESSING_SERVICE_URL=http://localhost:5002

# CLOUD (Cloud Run):
PROCESSING_BACKEND=cloud_functions
GCP_PROJECT_ID=strawbayscannertest
PUBSUB_TOPIC_ID=document-processing
```

### Code Changes Made

**1. Created `lib/processing_backend.py`** (NEW)
- ProcessingBackend abstract base class
- LocalCeleryBackend - wraps HTTP POST to processing service
- CloudFunctionsBackend - publishes to Pub/Sub
- MockBackend - for testing
- get_processing_backend() factory function
- init_processing_backend() singleton pattern

**2. Updated `main.py` - initialize backend**
```python
# At app startup:
from lib.processing_backend import init_processing_backend
processing_backend = init_processing_backend()
```

**3. Updated `upload_document()` endpoint**
```python
# OLD:
response = requests.post(f'{processing_url}/api/tasks/orchestrate', ...)

# NEW:
result = processing_backend.trigger_task(doc_id, company_id)
task_id = result['task_id']
```

### Cloud Functions Implementation

**Created: `cloud_functions_processing.py`**

5 Cloud Functions (one per processing stage):
1. `cf_preprocess_document` - Pub/Sub trigger, preprocesses image
2. `cf_extract_ocr_text` - Extracts text via OCR
3. `cf_predict_invoice_data` - LLM predictions
4. `cf_extract_structured_data` - Data structuring
5. `cf_run_automated_evaluation` - Quality evaluation

Each function:
- Triggered by Pub/Sub message with `stage` parameter
- Updates document status in database
- Publishes to next-stage topic on completion
- Handles errors gracefully (sets status to 'error')

### Pub/Sub Topic Architecture

```
document-processing (initial)
         ↓
    cf_preprocess_document
         ↓
    document-ocr
         ↓
    cf_extract_ocr_text
         ↓
    document-llm
         ↓
    cf_predict_invoice_data
         ↓
    document-extraction
         ↓
    cf_extract_structured_data
         ↓
    document-evaluation
         ↓
    cf_run_automated_evaluation
         ↓
    [COMPLETED - Database status = 'completed']
```

### Deployment - Cloud Functions

**Structure: cloud_functions/**

Files:
- `main.py` - 5 Cloud Functions (same code local + cloud)
- `requirements.txt` - functions-framework dependencies
- `local_server.sh` - Run locally on :9000
- `deploy.sh` - Deploy to GCP TEST/PROD
- `.env.yaml` - Configuration

### Testing Strategy (NEW - Unified)

**LOCAL TESTING:**
1. Start docker-compose: `docker-compose up -d`
2. Start Cloud Functions: `cd invoice.scanner.cloud.functions && ./local_server.sh`
3. Upload document via API: POST /auth/documents/upload
4. Monitor processing: GET /auth/documents/{id}/status
5. Verify database updates in real-time

**CLOUD TESTING:**
1. Deploy: `cd invoice.scanner.cloud.functions && ./deploy.sh strawbayscannertest`
2. Same upload/status flow via Cloud Run API
3. Verify Pub/Sub topics and Cloud Functions execute
4. Check Cloud SQL for status updates

### Benefits

✅ **Same code** - `main.py` runs local and cloud identically  
✅ **No Celery complexity** - functions-framework is simpler  
✅ **Easy to test** - simulate GCP locally before deploying  
✅ **Scalable** - Cloud Functions auto-scale based on load  
✅ **Cost-efficient** - Pay only for actual execution time  
✅ **Reliable** - Pub/Sub guarantees message delivery  

### Files Created

- ✅ **invoice.scanner.cloud.functions/main.py** - 5 Cloud Functions
- ✅ **invoice.scanner.cloud.functions/local_server.sh** - Local testing
- ✅ **invoice.scanner.cloud.functions/deploy.sh** - GCP deployment
- ✅ **invoice.scanner.cloud.functions/requirements.txt** - Dependencies
- ✅ **invoice.scanner.cloud.functions/.env.yaml** - Configuration
- ✅ **dev-start.sh** - Combined startup script (docker-compose + functions-framework in new Terminal)
- ✅ **REMOVED**: invoice.scanner.processing/ (Celery not needed)
- ✅ **UPDATED**: docker-compose.yml (4 services only)

### Git Commit

```
FASE 6E: Unified Cloud Functions Architecture

- Create cloud_functions/ with main.py (5 Cloud Functions)
- Add local_server.sh (functions-framework :9000) for local testing
- Add deploy.sh for automated GCP deployment
- Remove invoice.scanner.processing/ (Celery replaced by Cloud Functions)
- Simplify docker-compose.yml (4 services: api, frontend, db, redis)
- Create dev-server.sh for easy local startup
- Add cloud_functions/README.md with instructions
- Same code runs local and cloud - no duplication
```

---

## 🎯 FAS E 7: DEPLOY TO GCP TEST (NEW - Cloud Functions Based)

---

## 🎯 FASE 7: DEPLOY CLOUD FUNCTIONS TO GCP TEST (Dec 27 - 🚀 IN PROGRESS)

### Strategi: Test Locally → Deploy → Test i Cloud

Varje steg måste:
1. ✅ Fungera lokalt (docker-compose)
2. ✅ Deployas till GCP TEST
3. ✅ Testas i GCP
4. ✅ Dokumenteras för PROD (FASE 8)

### Step 1: Verify Local Setup (MANDATORY FIRST)

**Verifiera att LocalCeleryBackend fungerar:**

```bash
# Terminal 1: Start docker-compose
cd /Users/rickardelmqvist/Development/invoice.scanner
docker-compose down -v
docker-compose up -d --build

# Wait for health checks
sleep 15
docker-compose ps

# Should see: 14 services, most healthy or "health: starting"
```

**Verifiera processing backend initialiseras:**

```bash
# Check API logs
docker logs invoice.scanner.api 2>&1 | grep -i "processing_backend\|Processing"

# Should see: "[INIT] Processing backend initialized: local"
```

**Test document upload och processing lokalt:**

```bash
# Login
curl -X POST http://localhost:5001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "rickard@strawbay.io", "password": "Test123"}' \
    -c /tmp/cookies.txt

# Upload dokument
cd /tmp && FILE="test_$(date +%s).pdf" && echo "Test" > "$FILE"
curl -X POST http://localhost:5001/auth/documents/upload \
    -b /tmp/cookies.txt \
    -F "file=@$FILE"

# Should return: 201 with task_id

# Check status
DOC_ID="<from response>" # Copy från response
curl -X GET http://localhost:5001/auth/documents/$DOC_ID/status \
    -b /tmp/cookies.txt

# Should show: "status": "preprocessing" → eventually "approved"

# Wait and check again
sleep 10
curl -X GET http://localhost:5001/auth/documents/$DOC_ID/status \
    -b /tmp/cookies.txt

# Verify Celery workers processed it
docker logs invoice.scanner.worker.preprocessing.1 | tail -20
docker logs invoice.scanner.worker.ocr.1 | tail -20
docker logs invoice.scanner.worker.llm.1 | tail -20
```

**✅ Success Criteria - Local:**
- API returns 201 with valid task_id
- Status updates: preprocessing → ocr_extracting → prediction → extraction → approved
- Workers logs show task execution
- Database status updates correctly

---

### Step 2: Configure GCP Project (TEST)

**Set project:**

```bash
gcloud config set project strawbayscannertest
gcloud config list | grep project

# Should show: project = strawbayscannertest
```

**Verify authentication:**

```bash
gcloud auth list
gcloud auth application-default login

# Should show: elmqvistrickard@gmail.com as active
```

---

### Step 3: Enable Required APIs (TEST)

**Check which APIs are already enabled:**

```bash
gcloud services list --enabled --project=strawbayscannertest

# Look for:
# - cloudfunctions.googleapis.com
# - pubsub.googleapis.com
# - cloudbuild.googleapis.com
# - cloudresourcemanager.googleapis.com
```

**Enable missing APIs:**

```bash
gcloud services enable \
    cloudfunctions.googleapis.com \
    pubsub.googleapis.com \
    cloudbuild.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=strawbayscannertest

# Takes 1-2 minutes
# Should see: "Operation "..." finished successfully."
```

**Verify APIs enabled:**

```bash
gcloud services list --enabled --project=strawbayscannertest | grep -E "cloudfunctions|pubsub"

# Should show both enabled
```

---

### Step 4: Create Pub/Sub Topics (TEST)

**Create 5 topics for processing pipeline:**

```bash
PROJECT_ID="strawbayscannertest"

echo "[DEPLOY] Creating Pub/Sub topics..."

gcloud pubsub topics create document-processing \
    --project=$PROJECT_ID

gcloud pubsub topics create document-ocr \
    --project=$PROJECT_ID

gcloud pubsub topics create document-llm \
    --project=$PROJECT_ID

gcloud pubsub topics create document-extraction \
    --project=$PROJECT_ID

gcloud pubsub topics create document-evaluation \
    --project=$PROJECT_ID

# Each should return: "Created topic [projects/strawbayscannertest/topics/...]"
```

**Verify all topics created:**

```bash
gcloud pubsub topics list --project=$PROJECT_ID

# Should show all 5 topics
```

**Document topology (for reference):**

```
document-processing
        ↓
cf_preprocess_document
        ↓
document-ocr
        ↓
cf_extract_ocr_text
        ↓
document-llm
        ↓
cf_predict_invoice_data
        ↓
document-extraction
        ↓
cf_extract_structured_data
        ↓
document-evaluation
        ↓
cf_run_automated_evaluation
        ↓
[DONE - status='completed']
```

---

### Step 5: Deploy Cloud Functions (TEST)

**Prepare deployment:**

```bash
cd /Users/rickardelmqvist/Development/invoice.scanner

# Verify script exists
ls -la deploy_cloud_functions.sh

# Make executable
chmod +x deploy_cloud_functions.sh

# Verify cloud_functions_processing.py exists
ls -la cloud_functions_processing.py
```

**Run deployment script:**

```bash
./deploy_cloud_functions.sh strawbayscannertest europe-west1

# Script will:
# 1. Create GCS bucket (if not exists)
# 2. Deploy 5 Cloud Functions
# 3. Configure environment variables
# 4. Set up Cloud SQL connectivity

# Deployment takes 3-5 minutes per function (15-20 min total)
# Watch output for errors
```

**Monitor deployment:**

```bash
# In another terminal, watch Cloud Build logs
gcloud builds log <BUILD_ID> --stream --project=strawbayscannertest

# Or check functions status
watch -n 2 "gcloud functions list --project=strawbayscannertest"

# Wait until all 5 functions show "Active"
```

**Verify all functions deployed:**

```bash
gcloud functions list --project=strawbayscannertest

# Should show 5 functions:
# - cf-preprocess-document
# - cf-extract-ocr-text
# - cf-predict-invoice-data
# - cf-extract-structured-data
# - cf-run-automated-evaluation
```

**Verify function details:**

```bash
gcloud functions describe cf-preprocess-document \
    --project=strawbayscannertest \
    --region=europe-west1

# Look for:
# eventTrigger:
#   resource: projects/strawbayscannertest/topics/document-processing
#   eventType: google.pubsub.topic.publish

# Should show it's triggered by correct Pub/Sub topic
```

---

### Step 6: Verify Cloud Functions Configuration (TEST)

**Check environment variables on functions:**

```bash
# Each function should have:
# - GCP_PROJECT_ID=strawbayscannertest
# - DATABASE_HOST=127.0.0.1
# - DATABASE_PORT=5432
# - DATABASE_USER=scanner_test
# - DATABASE_PASSWORD=<from Secret Manager>
# - DATABASE_NAME=invoice_scanner
# - INSTANCE_CONNECTION_NAME=strawbayscannertest:europe-west1:invoice-scanner-test

gcloud functions describe cf-preprocess-document \
    --project=strawbayscannertest \
    --region=europe-west1 \
    --gen2 \
    --format='value(serviceConfig.environmentVariables)'

# Verify all are set
```

**Check Cloud SQL connectivity configuration:**

```bash
# Verify INSTANCE_CONNECTION_NAME is set correctly
gcloud sql instances describe invoice-scanner-test \
    --project=strawbayscannertest \
    --format='value(connectionName)'

# Should return: strawbayscannertest:europe-west1:invoice-scanner-test
```

---

### Step 7: Test Cloud Functions End-to-End (TEST)

**Publish test message to Pub/Sub manually:**

```bash
# First, let's test if function triggers
gcloud pubsub topics publish document-processing \
    --message='{"document_id":"test-123","company_id":"test-456","stage":"preprocess"}' \
    --project=strawbayscannertest

# Should return: messageIds: ['<ID>']
```

**Monitor function execution:**

```bash
# Watch function logs in real-time
gcloud functions logs read cf-preprocess-document \
    --project=strawbayscannertest \
    --region=europe-west1 \
    --limit=50 \
    --follow

# Should see function executed (or error if Cloud SQL unreachable)
```

**If error occurs - troubleshoot:**

```bash
# Check function logs more detailed
gcloud functions logs read cf-preprocess-document \
    --project=strawbayscannertest \
    --region=europe-west1 \
    --limit=100

# Common issues:
# 1. Cloud SQL not reachable - Check VPC Connector setup
# 2. Database credentials wrong - Check Secret Manager
# 3. Pub/Sub topic mismatch - Verify topic name matches trigger

# Check Cloud SQL connectivity from Cloud Functions
# (Cloud SQL Proxy should be auto-injected)
```

---

### Step 8: Test via API Upload (TEST - FULL END-TO-END)

**Configure API to use CloudFunctionsBackend:**

Cloud Run API service needs environment variable:
```
PROCESSING_BACKEND=cloud_functions
GCP_PROJECT_ID=strawbayscannertest
```

**Update Cloud Run service (optional - for testing):**

```bash
gcloud run services update invoice-scanner-api-test \
    --region=europe-west1 \
    --update-env-vars="PROCESSING_BACKEND=cloud_functions,GCP_PROJECT_ID=strawbayscannertest" \
    --project=strawbayscannertest

# Wait 1-2 minutes for update
```

**Test full flow:**

```bash
# Get Cloud Run API URL
API_URL=$(gcloud run services describe invoice-scanner-api-test \
    --platform=managed \
    --region=europe-west1 \
    --project=strawbayscannertest \
    --format='value(status.url)')

echo "API URL: $API_URL"

# Login
curl -X POST $API_URL/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "rickard@strawbay.io", "password": "Test123"}' \
    -c /tmp/cookies-cloud.txt

# Upload document
cd /tmp && FILE="cloud_test_$(date +%s).pdf" && echo "Test" > "$FILE"
RESPONSE=$(curl -X POST $API_URL/auth/documents/upload \
    -b /tmp/cookies-cloud.txt \
    -F "file=@$FILE")

echo $RESPONSE | jq .

# Extract document ID and task ID
DOC_ID=$(echo $RESPONSE | jq -r '.document.id')
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

echo "Document ID: $DOC_ID"
echo "Task ID: $TASK_ID"

# Monitor Pub/Sub topic
gcloud pubsub subscriptions create test-monitor --topic=document-processing \
    --project=strawbayscannertest 2>/dev/null || true

gcloud pubsub subscriptions pull test-monitor --auto-ack \
    --limit=1 \
    --project=strawbayscannertest

# Should see the document message published

# Monitor Cloud Function execution
gcloud functions logs read cf-preprocess-document \
    --project=strawbayscannertest \
    --region=europe-west1 \
    --limit=20 \
    --follow

# Check document status via API
sleep 5
curl -X GET $API_URL/auth/documents/$DOC_ID/status \
    -b /tmp/cookies-cloud.txt | jq .

# Should show: status = "preprocessing" initially, then progress through pipeline
```

**Expected behavior:**
```
1. Upload → API returns 201 with task_id
2. Pub/Sub publishes message to document-processing topic
3. cf_preprocess_document triggered → processes → publishes to document-ocr
4. cf_extract_ocr_text triggered → processes → publishes to document-llm
5. ... continues through all 5 functions ...
6. API /documents/{id}/status shows progress
7. Final status = "approved" or "completed"
```

**Success Criteria:**
- ✅ Message published to Pub/Sub
- ✅ Cloud Function triggered and executed
- ✅ Database status updated
- ✅ Pipeline progressed through at least 2 stages
- ✅ No errors in function logs

---

### Step 9: Rollback Test (LOCAL AGAIN)

**Ensure local still works after Cloud Functions changes:**

```bash
# Stop Cloud Run API from using cloud_functions
# (Update env var back to local OR just use local)

# Verify local still works
docker-compose ps

# If stopped, restart
docker-compose up -d

# Re-test local flow
curl -X POST http://localhost:5001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "rickard@strawbay.io", "password": "Test123"}' \
    -c /tmp/cookies.txt

cd /tmp && FILE="rollback_$(date +%s).pdf" && echo "Test" > "$FILE"
curl -X POST http://localhost:5001/auth/documents/upload \
    -b /tmp/cookies.txt \
    -F "file=@$FILE" | jq '.document.id'

# Verify Celery still processes
docker logs invoice.scanner.worker.preprocessing.1 | tail -5
```

**✅ Success Criteria:**
- Local processing still works identically
- Both backends can run independently
- No code changes needed to switch between them

---

## 🎯 FASE 8: DEPLOY CLOUD FUNCTIONS TO GCP PROD (Prepared)

**Same steps as FASE 7 but for PROD project:**

Replace all instances of:
- `strawbayscannertest` → `strawbayscannerprod`
- `invoice-scanner-test` → `invoice-scanner-prod`
- `scanner_test` → `scanner_prod`

**Run same deployment script:**
```bash
./deploy_cloud_functions.sh strawbayscannerprod europe-west1
```

**Then test same way:**
- Manual Pub/Sub message → Function execution
- Full API upload → Pipeline execution
- Verify database updates

**Then update Cloud Run API service:**
```bash
gcloud run services update invoice-scanner-api-prod \
    --region=europe-west1 \
    --update-env-vars="PROCESSING_BACKEND=cloud_functions,GCP_PROJECT_ID=strawbayscannerprod" \
    --project=strawbayscannerprod
```

---

### Files Created/Modified

- ✅ **NEW**: `lib/processing_backend.py` (Backend abstraction)
- ✅ **NEW**: `cloud_functions_processing.py` (GCP implementation)
- ✅ **NEW**: `deploy_cloud_functions.sh` (Deployment script)
- ✅ **NEW**: `requirements_cloud_functions.txt` (Dependencies)
- ✅ **UPDATED**: `main.py` (Use ProcessingBackend)

### Git Commit

```
FASE 6E: Processing Backend Abstraction + Cloud Functions

- Create ProcessingBackend abstraction with LocalCeleryBackend, CloudFunctionsBackend, MockBackend
- Implement environment-aware backend selection
- Create 5 Cloud Functions for each processing stage
- Add Pub/Sub-based orchestration for GCP
- Maintain same API code for both local and cloud deployments
- Add deployment script for Cloud Functions setup
```

---

## GCP DEPLOYMENT - ÖVERGRIPANDE ARKITEKTUR

### Enkel flöde (Branch → Deploy)

```
feature branch → PR → re_deploy_start (merge)
  ↓
  Pipeline.yml:build (auto-trigger)
    - Auto-detects branch
    - Uses GCP_SA_KEY_TEST
    - Builds 3 images (API, Frontend, Worker)
    - Pushs to TEST Artifact Registry
  ↓
  Pipeline.yml:deploy-test (auto-trigger)
    - Fetches TEST secrets from Secret Manager
    - Deploys API + Frontend to Cloud Run TEST
    - Runs smoke tests
  ↓
  ✅ TEST Cloud Run services live


main branch deployment (manual approval):
  ↓
  Create PR: re_deploy_start → main
  ↓
  Pipeline.yml:build (auto-trigger)
    - Uses GCP_SA_KEY_PROD
    - Builds to PROD Artifact Registry
  ↓
  Pipeline.yml:deploy-prod (waits for approval)
    - ⚠️ MANUAL APPROVAL GATE (24h timeout)
    - After approval: Fetches PROD secrets
    - Deploys to Cloud Run PROD
  ↓
  ✅ PROD Cloud Run services live
```

### Secrets Mapping

**TEST-projekt → Environment Variables:**
```
db_user_test → DATABASE_USER
db_password_test → DATABASE_PASSWORD
secret_key_test → FLASK_SECRET_KEY
gmail_sender → EMAIL_SENDER
gmail_password → EMAIL_PASSWORD
openai_api_key → OPENAI_API_KEY
```

**PROD-projekt → samma pattern** (med _prod suffixes)

### Key Architecture Points
- ✅ **Private Cloud SQL** - Private IP + Cloud SQL Auth Proxy sidecar
- ✅ **Centralized Secrets** - GCP Secret Manager (not in code)
- ✅ **pg8000 Driver** - Pure Python (Cloud SQL Connector compatible)
- ✅ **Single Pipeline** - `.github/workflows/pipeline.yml` (not 3 separate files)
- ✅ **Branch Detection** - Auto-selects TEST vs PROD based on branch

---

## CI/CD PIPELINE - SIMPLIFIED

**File:** `.github/workflows/pipeline.yml` (single file, 3 conditional jobs - FINAL)

**How it works:**
1. **push to re_deploy_start** → build job (auto) → deploy-test job (auto)
2. **push to main** → build job (auto) → deploy-prod job (waits for manual approval)

**Each branch gets right secrets:**
- re_deploy_start: GCP_SA_KEY_TEST → TEST Artifact Registry → TEST Cloud Run
- main: GCP_SA_KEY_PROD → PROD Artifact Registry → PROD Cloud Run

**That's it!** The pipeline handles everything (building, pushing, deploying).

---

---

## IMPLEMENTATION CHECKLISTA

### FASE 0: Setup (NÄSTA - 0% done)
- [ ] GCP Project IDs dokumenterade
- [ ] Aktivera APIs: Cloud Run, Cloud SQL, Artifact Registry, Secret Manager, Cloud Tasks
- [ ] Service Accounts skapade (test + prod)
- [ ] GitHub Secrets konfigurerad: `GCP_SA_KEY`

### FASE 1: GCP Secret Manager (0% done)
- [ ] Skapa secrets i GCP Secret Manager (test project):
  - `db_password`, `db_user`, `api_key`, `gmail_password`, etc.
- [ ] Samma secrets i prod project
- [ ] Testa läsning från GitHub Actions

### FASE 2: Cloud SQL Setup (0% done)
- [ ] Skapa PostgreSQL instans (test)
  - Name: `invoice-scanner-test`
  - Network: Private IP
- [ ] Skapa PostgreSQL instans (prod)
  - Name: `invoice-scanner-prod`
  - Backup enabled
- [ ] Kör init.sql på båda
- [ ] Verifiera anslutning från Cloud Run

### FASE 3: Docker Images ✅ 100% KLART

**Docker Images Built & Pushed to Artifact Registry:**

TEST-projekt (`strawbayscannertest`):
```
✅ europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/api:latest
✅ europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/frontend:latest
✅ europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/worker:latest
```

PROD-projekt (`strawbayscannerprod`):
```
✅ europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/api:latest
✅ europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/frontend:latest
✅ europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/worker:latest
```

**Image Details:**
- API: 1.44 GB (python:3.11-slim, Flask, optimized dependencies)
- Frontend: 83.1 MB (Node 20-alpine builder + nginx multi-stage)
- Worker: 4.02 GB (python:3.11-bullseye + OCR dependencies)

**Pushed:** Dec 24, 2025
**Status:** All 6 images successfully pushed to both registries

### FASE 4: GitHub Actions Workflows ✅ 100% KLART

**Single Unified Pipeline:** `.github/workflows/pipeline.yml`
- ✅ build job - Detects branch, builds 3 images, pushes to correct registry
- ✅ deploy-test job - Conditional on re_deploy_start, no approval needed
- ✅ deploy-prod job - Conditional on main, requires `environment: production` approval
- ✅ All 3 jobs in one file for maintainability
- ✅ Branch detection logic in build job first step
- ✅ Jobs properly chain with `needs: build` dependency
- ✅ Uses secrets: `GCP_SA_KEY_TEST` or `GCP_SA_KEY_PROD` (auto-selected)

**Cleanup completed:**
- ✅ Removed old build.yml, test-deploy.yml, prod-deploy.yml
- ✅ Removed .bak backup files
- ✅ Workflows directory now contains ONLY pipeline.yml
- ✅ Committed and pushed to origin/re_deploy_start

**Status:** All 3 conditional jobs ready to execute on branch push

**What's needed:**
- ⏳ User creates PR on re_deploy_start to test
- ⏳ First merge to re_deploy_start (pipeline.yml:build + pipeline.yml:deploy-test run)
- ⏳ First merge to main (pipeline.yml:build + pipeline.yml:deploy-prod with approval)

---

## DATABASE MIGRATION STRATEGY (DECIDED Dec 26)

**Decision:** Use **Versionalized SQL Migrations** approach for future database changes

### How it works:
- Each database change gets its own versioned SQL file: `migrations/001_initial.sql`, `002_add_column_x.sql`, etc.
- Files are named: `{number}_{description}.sql` (e.g., `001_initial.sql`, `002_add_invoices_table.sql`)
- Run migrations in order (only once per environment)
- Track which migrations have run in a `schema_migrations` table

### Initial Setup (Dec 26 - COMPLETED):
- [x] ✅ Run `invoice.scanner.db/init.sql` manually on Cloud SQL TEST
- [x] ✅ Verify: Check that users table has test user (rickard@strawbay.io)
- [x] ✅ Run same init.sql on PROD after TEST is verified

### Future Database Changes:
1. Create new file: `migrations/002_your_change.sql`
2. Document what changed
3. Run it manually on TEST first
4. After verification, run on PROD
5. Add to git + commit

### Directory Structure:
```
invoice.scanner.db/
├── init.sql (initial schema + seed data)
└── migrations/
    ├── 002_add_feature_x.sql
    ├── 003_update_permissions.sql
    └── ...
```

---

## CLOUD SQL PROXY CONFIGURATION (DECIDED Dec 26)

**Problem (Dec 26 08:15):** Cloud Run API couldn't connect to Cloud SQL
- Error: `connection to server at "invoice-scanner-test.c.strawbayscannertest.cloudsql.googleapis.com" port 5432 failed: Connection timed out`
- Root cause: Cloud SQL is Private IP only, API tried public hostname

**Solution:** Cloud SQL Auth Proxy sidecar in Cloud Run
- Already configured in pipeline.yml with `--add-cloudsql-instances` flag
- Creates secure tunnel from Cloud Run container to Cloud SQL
- Exposes connection on `localhost:5432`

**Implementation (Dec 26):**
1. ✅ pipeline.yml already has `--add-cloudsql-instances` flag in both deploy-test and deploy-prod
2. ✅ Changed DATABASE_HOST from `invoice-scanner-test.c.strawbayscannertest.cloudsql.googleapis.com` to `localhost`
3. ✅ Same for PROD: `invoice-scanner-prod.c.strawbayscannerprod.cloudsql.googleapis.com` → `localhost`
4. Rationale: Cloud SQL Proxy maps port 5432 to localhost internally

**Environment Variables in Cloud Run:**
```
TEST:
  DATABASE_HOST=localhost (with Cloud SQL Proxy sidecar)
  DATABASE_PORT=5432
  DATABASE_USER=scanner_test
  DATABASE_PASSWORD=(from Secret Manager)
  DATABASE_NAME=invoice_scanner

PROD: (same pattern)
  DATABASE_HOST=localhost
  DATABASE_PORT=5432
  DATABASE_USER=scanner_prod
  DATABASE_PASSWORD=(from Secret Manager)
  DATABASE_NAME=invoice_scanner
```

**How it works:**
1. Cloud Run container starts with `--add-cloudsql-instances=project:region:instance`
2. Google Cloud Proxy sidecar automatically starts (injected by Cloud Run)
3. Proxy creates secure connection to Cloud SQL (Private IP)
4. Proxy listens on `localhost:5432` inside container
5. Application connects to `localhost:5432` (authenticated via Cloud Run service account)

**Reference:**
- [Google Cloud SQL Auth Proxy Docs](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Cloud Run + Cloud SQL Integration](https://cloud.google.com/run/docs/configuring/sql-connectors)

**Status:** ✅ CONFIGURED in pipeline.yml (both TEST and PROD)

---

## VPC ACCESS CONNECTOR (REQUIRED FOR PRIVATE IP) - Dec 26

**Problem Discovered:** 
- Cloud SQL instances are Private IP only (secure by default)
- Cloud Run services need special networking to reach Private IP
- Error without VPC Connector: `Cloud SQL instance does not have any IP addresses matching preference: PRIMARY`

**Solution:** VPC Access Connector
- Creates a managed VPC connector between Cloud Run and VPC (where Cloud SQL lives)
- Allows Cloud Run to reach Private IP resources securely
- Must be in same region as Cloud Run (europe-west1)

**Implementation (REQUIRED - Must Run Manually):**

### Step 1: Create VPC Access Connector (one-time setup)
```bash
gcloud compute networks vpc-access connectors create run-connector \
  --region=europe-west1 \
  --network=default \
  --range=10.8.0.0/28 \
  --project=strawbayscannertest
```

### Step 2: Update Cloud Run Services to Use Connector (TEST environment)
```bash
gcloud run services update invoice-scanner-api-test \
  --region=europe-west1 \
  --vpc-connector=run-connector \
  --vpc-egress=all \
  --project=strawbayscannertest

gcloud run services update invoice-scanner-frontend-test \
  --region=europe-west1 \
  --vpc-connector=run-connector \
  --vpc-egress=all \
  --project=strawbayscannertest
```

### Step 3: Update Cloud Run Services to Use Connector (PROD environment)
```bash
gcloud compute networks vpc-access connectors create run-connector \
  --region=europe-west1 \
  --network=default \
  --range=10.8.0.0/28 \
  --project=strawbayscannerprod

gcloud run services update invoice-scanner-api-prod \
  --region=europe-west1 \
  --vpc-connector=run-connector \
  --vpc-egress=all \
  --project=strawbayscannerprod

gcloud run services update invoice-scanner-frontend-prod \
  --region=europe-west1 \
  --vpc-connector=run-connector \
  --vpc-egress=all \
  --project=strawbayscannerprod
```

**Why this works:**
- VPC Connector bridges Cloud Run ↔ VPC network
- Cloud SQL Private IP exists in VPC
- Cloud Run can now reach Private IP via connector
- `--vpc-egress=all` routes all outbound traffic through connector

**Status:** ✅ IMPLEMENTED Dec 26 (manually for TEST, must repeat for PROD)

**In pipeline.yml:** 
- Consider adding VPC connector setup to deploy-test/deploy-prod jobs if possible
- Alternative: Document as manual post-deployment step

---

## DATABASE DRIVER STRATEGY: pg8000 Migration (DECIDED Dec 26)

### Problem Discovery (Dec 26 - CRITICAL)

**Error in Cloud Run logs (10:00:39):**
```
"Driver 'psycopg2' is not supported."
```

**Root Cause Investigation:**
- Cloud SQL Connector API documentation discovered: Only supports `pymysql`, `pg8000`, `pytds`
- psycopg2 is NOT supported by Cloud SQL Connector
- Current code attempted: `connector.connect(..., "psycopg2", ...)`
- This was doomed to fail in Cloud Run

**Architecture Issue (SIMULTANEOUS DISCOVERY):**
- API uses `DATABASE_*` environment variables
- Processing uses `DB_*` environment variables (old naming convention)
- Two separate database connection systems in same project
- Cannot fix one without fixing both

### Solution: Unified pg8000 Strategy

**Why pg8000?**
- ✅ Pure Python PostgreSQL driver (no C dependencies)
- ✅ Cloud SQL Connector officially supports it
- ✅ Works with local TCP connections (docker-compose)
- ✅ Works with future Connector mode in Cloud Run
- ✅ Single solution for all environments

**Challenges:**
- pg8000 doesn't have `RealDictCursor` built-in (like psycopg2)
- Current codebase heavily uses RealDictCursor for dictionary-like row access
- Solution: Create wrapper layer providing RealDictCursor interface for pg8000

### Implementation Plan (3-Part Refactoring)

**Part 1: Create Shared Database Abstraction Layer**
- Location: `/shared/pg8000_wrapper.py`
- Provides: `RealDictCursor`-like interface for pg8000 rows
- Supports: Both local TCP (docker-compose) and future Connector mode (Cloud Run)
- Implements: Connection pooling for efficiency

**Part 2: Standardize Environment Variables Across Entire Project**
- Converge: `DB_*` variables → `DATABASE_*` (uniform naming)
- Files affected:
  - `invoice.scanner.api/db_config.py` - Already uses DATABASE_*
  - `invoice.scanner.api/db_utils.py` - Uses db_config imports
  - `invoice.scanner.processing/config/db_utils.py` - Uses old DB_* (needs update)
  - `docker-compose.yml` - Update all 13 services to use DATABASE_*
- Rationale: Single naming convention simplifies debugging + matches Cloud Run

**Part 3: Update Both API and Processing Modules**
- API: Refactor db_config.py to use shared pg8000 wrapper
- Processing: Update config/db_utils.py to use shared wrapper + new env vars
- Verify: All existing functionality preserved (RealDictCursor behavior replicated)
- Test: All 13 containers work locally before Cloud Run

### Critical Instructions (Must Remember)

**When implementing pg8000 migration:**

1. **INVESTIGATE FIRST**
   - Grep for all uses of `psycopg2.connect()`
   - Find all places using `RealDictCursor`
   - Check all environment variable references
   - Understand current connection patterns

2. **STANDARDIZE NAMING SYSTEMATICALLY**
   - Don't leave dual naming convention (mixing DATABASE_* and DB_*)
   - Update docker-compose.yml simultaneously
   - Verify all 13 containers get correct variables
   - No half-migrations

3. **TEST LOCALLY BEFORE CLOUD RUN**
   - Run all 13 containers with new pg8000 wrapper
   - Test API login endpoint (uses database)
   - Test processing workers (use database queries)
   - Verify RealDictCursor compatibility layer works

4. **MAINTAIN BACKWARD COMPATIBILITY**
   - Existing code should not know it's pg8000 internally
   - RealDictCursor interface must be identical to psycopg2 version
   - All cursors should still behave like dictionaries

### Current Status (Dec 26 - Migration Complete ✅)

**Completed (ALL):**
- ✅ Identified driver incompatibility (psycopg2 not supported by Cloud SQL Connector)
- ✅ Analyzed entire project structure (unified pg8000 approach)
- ✅ Created pg8000_wrapper.py with RealDictCursor compatibility in API and Processing
- ✅ Updated requirements.txt: Removed psycopg2-binary, added pg8000
- ✅ API db_config.py configured for pg8000 (DATABASE_* variables)
- ✅ Processing config/db_utils.py configured for pg8000 (DATABASE_* variables)
- ✅ docker-compose.yml standardized to DATABASE_* naming (no DB_* mixing)
- ✅ Local testing: all 14 containers healthy, database connections working
- ✅ Document processing verified (status updates working correctly)
- ✅ Git commit with detailed migration message (commit: 03db1c6)

**Status:** READY FOR CLOUD RUN DEPLOYMENT
- All components use unified pg8000 driver
- Both local (docker-compose) and Cloud Run (via Connector) compatible
- RealDictCursor compatibility maintained for existing code
- No psycopg2 dependencies remaining

---

### FASE 5: Cloud Run TEST Deployment (NEXT - Ready to Start)

**Status:** ✅ All prerequisites complete - Ready for GitHub Actions pipeline

**Steps to execute:**
- [ ] 1. Verify local: `docker-compose down && docker-compose up -d --build` (DONE ✅)
- [ ] 2. Commit any pending changes: `git add . && git commit -m "..."`
- [ ] 3. Push to re_deploy_start: `git push origin re_deploy_start`
- [ ] 4. Monitor GitHub Actions: https://github.com/Rickard-E-Strawbay/invoice.scanner/actions
  - build job runs (~5-10 min): builds api, frontend, worker images
  - deploy-test job runs (~3-5 min): deploys to Cloud Run TEST
  - Both jobs should complete successfully with smoke tests passing
- [ ] 5. After deployment: Test API/Frontend on Cloud Run TEST URLs
- [ ] 6. Create PR: re_deploy_start → main (for PROD deployment)
- [ ] 7. After PROD PR approval: Merge to main (pipeline.yml:deploy-prod with manual approval gate)

### FASE 6: Cloud Tasks Setup (0% done)
- [ ] Konfigurera Cloud Tasks queue för workers
- [ ] Cloud Pub/Sub topics för events
- [ ] Worker-container ready för on-demand execution

### FASE 7: Testing & Verification (0% done)
- [ ] Test pipeline från GitHub push
- [ ] Manual approval flow testat
- [ ] Smoke tests på Cloud Run services
- [ ] Database connectivity verified
- [ ] Secrets läses korrekt

### FASE 8: Monitoring & Alerts (0% done)
- [ ] Google Cloud Logging configured
- [ ] Error alerts setup
- [ ] Performance monitoring
- [ ] Backup verification (prod)

---

## GCP PROJEKT KONFIGURATION

**GCP Project IDs:**
- ✅ Test: `strawbayscannertest`
- ✅ Prod: `strawbayscannerprod`

**Region:**
- ✅ `europe-west1` (Belgien)

**URLs:**
- ✅ GCP-genererade URLs (ex: `api-xxxxx.run.app`)

## GCP SECRETS STRATEGI (GODKÄND)

**GitHub Secrets (Option A - Två separata):**
- `GCP_SA_KEY_TEST` → Service Account JSON från TEST-projekt
- `GCP_SA_KEY_PROD` → Service Account JSON från PROD-projekt

**Varför två:** CI/CD pipeline kan automatiskt välja rätt secret baserat på miljö (test branch → TEST secret, main branch → PROD secret)

**Säkerhet:**
- ✅ Aldrig lagra secrets i kod
- ✅ GitHub Secrets är encrypted
- ✅ Loggar visar inte secret-värden
- ✅ Endast Actions kan läsa secrets under körning

---

## GCP SETUP STATUS - FASE 0: ✅ 100% KLART

**APIs Aktiverade: ✅ KLART**
- ✅ TEST-projekt: Alla 5 APIs enabled
- ✅ PROD-projekt: Alla 5 APIs enabled

**Service Accounts: ✅ KLART**
- ✅ TEST-projekt: `github-deployer` skapad (Editor role)
- ✅ PROD-projekt: `github-deployer` skapad (Editor role)

**JSON-Nycklar: ✅ KLART**
- ✅ TEST-projekt: JSON-nyckel nedladdad
- ✅ PROD-projekt: JSON-nyckel nedladdad

**GitHub Secrets: ✅ KLART**
- ✅ `GCP_SA_KEY_TEST` → Ligger i GitHub
- ✅ `GCP_SA_KEY_PROD` → Ligger i GitHub

**Progress FASE 0:**
- ✅ [x] APIs aktiverade (test + prod)
- ✅ [x] Service Accounts skapade (test + prod)
- ✅ [x] JSON-nycklar exporterade (test + prod)
- ✅ [x] GitHub Secrets konfigurerad (Option A)

---

## IMPLEMENTATION CHECKLISTA - UPPDATERAD

### FASE 0: Setup ✅ KLART (100%)
- ✅ GCP Project IDs dokumenterade
- ✅ Aktivera APIs: Cloud Run, Cloud SQL, Artifact Registry, Secret Manager, Cloud Tasks
- ✅ Service Accounts skapade (test + prod)
- ✅ GitHub Secrets konfigurerad: `GCP_SA_KEY_TEST` + `GCP_SA_KEY_PROD`

### FASE 1: GCP Secret Manager ✅ KLART (100%)

**Database Credentials: ✅ SKAPADE I GCP SECRET MANAGER**

TEST-projekt (`strawbayscannertest`) secrets:
- ✅ `db_user_test` = `scanner_test`
- ✅ `db_password_test` = `3ksaMsUqY5EW60FvXmp5MNv9i!mbkoQX`

PROD-projekt (`strawbayscannerprod`) secrets:
- ✅ `db_user_prod` = `scanner_prod`
- ✅ `db_password_prod` = `94LVGuefzk0g#a4Mbu2u!mu@I7R%PItl`

**Flask SECRET_KEY: ✅ SKAPADE**

TEST-projekt:
- ✅ `secret_key_test` = `cWz$o%u-Mnfse1k%bhNf3K_xRcvSeFxnHlQzgt5H!wSWYtliIB4COYyKNq7iq7Gi`

PROD-projekt:
- ✅ `secret_key_prod` = `kWKmBqNA@7WSERqjAP%E8X6ulY%cvX!!j6hUQ8DgiZqCyjq8Ag@4OTEXhx5P9LWz`

**Email Credentials: ✅ SKAPADE (samma i både test och prod)**

BÅDA projekt:
- ✅ `gmail_sender` = `rickard@strawbay.io`
- ✅ `gmail_password` = `ggse prtk gmye nrqe`

**LLM API Keys: ✅ SKAPADE (samma i både test och prod)**

BÅDA projekt:
- ✅ `openai_api_key` = (från Secret Manager)

**Summa FASE 1:**
- ✅ 6 secrets i TEST-projekt
- ✅ 6 secrets i PROD-projekt
- ✅ Alla användaruppgifter från befintlig `.env` migrerade
- ✅ Starka, genererade lösenord för databaskonton
- ✅ Starka, genererade Flask SECRET_KEY för båda miljöer

### FASE 2: Cloud SQL Setup ✅ KLART (100%)

**TEST-projekt (`strawbayscannertest`): ✅ KLART**

PostgreSQL Instans:
- ✅ Instance name: `invoice-scanner-test`
- ✅ Machine type: db-f1-micro (Shared-core, 0.614 GB RAM)
- ✅ Region: europe-west1 (belgien)
- ✅ Private IP: Enabled
- ✅ Database: `invoice_scanner` skapad
- ✅ User: `scanner_test` skapad
- ✅ Root password: `0R@UMO1Mr-s-hKVA6Y5JwSWQUrcIY1RN`

**PROD-projekt (`strawbayscannerprod`): ✅ KLART**

PostgreSQL Instans:
- ✅ Instance name: `invoice-scanner-prod`
- ✅ Machine type: db-f1-micro (Shared-core)
- ✅ Region: europe-west1
- ✅ Private IP: Enabled
- ✅ Backup: Enabled
- ✅ Database: `invoice_scanner` skapad
- ✅ User: `scanner_prod` skapad
- ✅ Root password: `HP!#mtYvvxmGxgvJP7AynwmlBvFyGd_r`

### FASE 3: Docker Images (0% done)
- [ ] Dockerfile API: Ready för Cloud Run
- [ ] Dockerfile Frontend: Ready för Cloud Run
- [ ] Dockerfile Worker: Ready för Cloud Tasks
- [ ] Build & push till Artifact Registry (test först)

### FASE 4: GitHub Actions Workflows (100% KLART)
- ✅ `.github/workflows/pipeline.yml` - Single file with build + conditional deploys
- ✅ build job - Auto-detects branch, builds 3 images, pushes to correct registry
- ✅ deploy-test job - Runs on re_deploy_start (no approval)
- ✅ deploy-prod job - Runs on main (requires approval)
- ✅ All jobs in one unified file

### FASE 5: Cloud Run Deployment (0% done)
- [ ] Deploy API service (test)
  - Environment variables från Secret Manager
  - Cloud SQL proxy
- [ ] Deploy Frontend service (test)
  - Build from Docker image
- [ ] Setup Cloud Storage bucket (documents)
- [ ] Samma setup för prod

### FASE 6: Cloud Tasks Setup (0% done)
- [ ] Konfigurera Cloud Tasks queue för workers
- [ ] Cloud Pub/Sub topics för events
- [ ] Worker-container ready för on-demand execution

### FASE 7: Testing & Verification (0% done)
- [ ] Test pipeline från GitHub push
- [ ] Manual approval flow testat
- [ ] Smoke tests på Cloud Run services
- [ ] Database connectivity verified
- [ ] Secrets läses korrekt

### FASE 8: Monitoring & Alerts (0% done)
- [ ] Google Cloud Logging configured
- [ ] Error alerts setup
- [ ] Performance monitoring
- [ ] Backup verification (prod)

---

### TEST-Projektet (`strawbayscannertest`)

**Aktiverade APIs:**
- ✅ Cloud Run Admin API
- ✅ Cloud SQL Admin API
- ✅ Artifact Registry API
- ✅ Secret Manager API
- ✅ Cloud Tasks API

**Service Accounts:**
- ✅ `github-deployer` (Editor role) - Behöver JSON-nyckel

**Kommande:**
- ⏳ JSON-nyckel exporterad
- ⏳ Cloud SQL PostgreSQL instans
- ⏳ Cloud Storage bucket
- ⏳ Secret Manager secrets

---

### PROD-Projektet (`strawbayscannerprod`)

**Aktiverade APIs:**
- ✅ Cloud Run Admin API
- ✅ Cloud SQL Admin API
- ✅ Artifact Registry API
- ✅ Secret Manager API
- ✅ Cloud Tasks API

**Service Accounts:**
- ✅ `github-deployer` (Editor role) - Behöver JSON-nyckel

**Kommande:**
- ⏳ JSON-nyckel exporterad
- ⏳ Cloud SQL PostgreSQL instans (med backup)
- ⏳ Cloud Storage bucket
- ⏳ Secret Manager secrets

---

**Summa:** Undersök, Fråga, Skapa. Inte: Skapa, Skapa, Skapa, sedan rätta allt.
