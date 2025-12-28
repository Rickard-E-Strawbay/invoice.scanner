# System Prompt för Invoice Scanner Projekt

> **Last Updated:** December 28, 2025 | **Status:** 🎉 Production Operational

---

## 📑 Table of Contents

1. [⚠️ Kritiska Instruktioner](#-ai-assistentens-kritiska-instruktioner)
2. [� Quick Commands](#-quick-commands)
3. [📋 Quick Reference](#-quick-reference---läs-detta-först)
4. [🎯 Nuvarande Status](#-current-state-dec-28-2025)
5. [🏗️ Arkitektur & Deployment](#-arkitektur--deployment)
6. [📚 Development Workflow](#-development-workflow)
7. [🔧 Configuration & Secrets](#-configuration--secrets)
8. [🆘 Troubleshooting](#-troubleshooting--diagnostics)
9. [📝 Changelog](#-changelog)

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
| Cloud Functions | Serverless processing | Inte Celery |
| [deploy-cf] flag | Trigger CF redeploy | I commit message |

### VID PROBLEM
Ordning: Logs (GitHub Actions) → Logs (Cloud Run) → Logs (Cloud Functions) → FIX KÖD → RE-PUSH

### Användarens Preferenser
- Vill ha ENKLA lösningar först
- Vill att jag ska FRÅGA innan komplexitet
- Gillar TYDLIGA instruktioner
- Vill FÖRSTÅ vad som görs, inte bara att det görs
- **VIKTIGAST:** Trust the pipeline - det är korrekt konfigurerat

---

## � Quick Commands

**Start Local Development:**
```bash
# Start everything (API, Frontend, Database, Cloud Functions)
./dev-start.sh

# This opens 2 terminals:
#   - Terminal 1: Docker services (API @ :5001, Frontend @ :8080, DB @ :5432)
#   - Terminal 2: Cloud Functions Framework (@ :9000)

```

**Deploy Changes:**
```bash
# TEST deployment (automatic on push to re_deploy_start)
git push origin re_deploy_start

# PROD deployment (after PR merge to main)
# Manual approval required in GitHub Actions

# Include [deploy-cf] flag ONLY if Cloud Functions code changed
git commit -m "Fix X [deploy-cf]"
```

**Manual Cloud Functions Deployment:**
```bash
# TEST
cd invoice.scanner.cloud.functions
./deploy.sh strawbayscannertest europe-west1

# PROD
./deploy.sh strawbayscannerprod europe-west1
```

**Check Status:**
```bash
# Local services
docker-compose ps

# Cloud Functions logs (from new terminal)
# Terminal output appears in the Cloud Functions window

# GCP Cloud Functions status
gcloud functions list --v2 --project=strawbayscannertest --format='table(name,status)'
```

**Stop Local Development:**
```bash
# Press Ctrl+C in Docker terminal
# Press Ctrl+C in Cloud Functions terminal
```

---

## 📋 Quick Reference - Läs detta först!

**NUVARANDE ARKITEKTUR (Dec 28, 2025):**

| Komponenter | Port | Status | Beskrivning |
|-------------|------|--------|------------|
| **Frontend (Vite)** | :8080 | ✅ Ready | React app with hot-reload (Dockerfile.dev) |
| **API (Flask)** | :5001 | ✅ Ready | REST API backend |
| **Database (PostgreSQL)** | :5432 | ✅ Ready | invoice_scanner (user: scanner_local) |
| **Cloud Functions Framework** | :9000 | ✅ Ready | Local processing backend simulator |
| **GCP Cloud Functions** | N/A | ✅ Live | 5 functions (TEST + PROD) |
| **Cloud Run API TEST** | HTTPS | ✅ Live | strawbayscannertest |
| **Cloud Run Frontend TEST** | HTTPS | ✅ Live | strawbayscannertest |
| **Cloud Run API PROD** | HTTPS | ✅ Live | strawbayscannerprod |
| **Cloud Run Frontend PROD** | HTTPS | ✅ Live | strawbayscannerprod |

**Local Development Stack (./dev-start.sh):**
```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Terminal 1: Docker Compose                                  │
│  ├─ Frontend:  :8080 (Vite with hot-reload)                │
│  ├─ API:       :5001 (Flask)                                │
│  ├─ Database:  :5432 (PostgreSQL)                           │
│                                                               │
│  Terminal 2: Cloud Functions Framework                       │
│  └─ Functions: :9000 (5 local functions)                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**GCP Deployment Stack:**
```
┌──────────────────────────┬──────────────────────────┐
│      TEST ENVIRONMENT    │    PROD ENVIRONMENT      │
│  (strawbayscannertest)   │ (strawbayscannerprod)    │
├──────────────────────────┼──────────────────────────┤
│                          │                          │
│  Cloud Run:              │  Cloud Run:              │
│  ├─ API (Flask)          │  ├─ API (Flask)          │
│  └─ Frontend (React)     │  └─ Frontend (React)     │
│                          │                          │
│  Cloud Functions:        │  Cloud Functions:        │
│  ├─ preprocess_document  │  ├─ preprocess_document  │
│  ├─ ocr_extract_text     │  ├─ ocr_extract_text     │
│  ├─ llm_process_data     │  ├─ llm_process_data     │
│  ├─ extract_fields       │  ├─ extract_fields       │
│  └─ evaluation_function  │  └─ evaluation_function  │
│                          │                          │
│  Cloud SQL:              │  Cloud SQL:              │
│  └─ invoice-scanner-test │  └─ invoice-scanner-prod │
│                          │                          │
│  Pub/Sub:                │  Pub/Sub:                │
│  └─ orchestration topics │  └─ orchestration topics │
│                          │                          │
└──────────────────────────┴──────────────────────────┘
```

**Status Dec 28 - ALLT OPERATIONELLT:**
- ✅ Local development fully functional (docker-compose + Cloud Functions Framework)
- ✅ TEST environment live with all 5 Cloud Functions
- ✅ PROD environment live with all 5 Cloud Functions
- ✅ Document processing end-to-end in both environments
- ✅ Database status updates verified
- ✅ Pub/Sub pipeline orchestration working
- ✅ CI/CD pipeline fully automated
- ✅ TEST and PROD synchronized
- ✅ Secret Manager integration active

---
## ✅ CURRENT STATE (Dec 28, 2025)

### 🎉 Produktionsläge Operationellt - FASE 9 Complete

**Status Summary:**
| Component | TEST | PROD | Local |
|-----------|------|------|-------|
| Cloud Run API | ✅ Live | ✅ Live | :5001 |
| Cloud Run Frontend | ✅ Live | ✅ Live | :8080 |
| Cloud Functions (5x) | ✅ Active | ✅ Active | :9000 |
| Cloud SQL | ✅ Connected | ✅ Connected | :5432 |
| Document Processing | ✅ Verified | ✅ Verified | ✅ Ready |
| Pipeline Automation | ✅ Working | ✅ Working | N/A |

**What's Working:**
1. ✅ Local development (dev-start.sh starts everything)
2. ✅ Cloud Functions Framework locally (:9000)
3. ✅ All 5 Cloud Functions deployed in TEST and PROD
4. ✅ Pub/Sub orchestration end-to-end
5. ✅ Database connectivity (pg8000 + Cloud SQL Connector)
6. ✅ Secret Manager integration
7. ✅ Status updates in database
8. ✅ Full CI/CD pipeline (GitHub Actions)
9. ✅ Manual approval gate between TEST and PROD
10. ✅ TEST and PROD environments synchronized

**Folder Structure:**
```
invoice.scanner/
├── .github/workflows/
│   └── pipeline.yml              (Automated CI/CD)
├── docker-compose.yml            (Local stack)
├── dev-start.sh                  (Start everything)
├── invoice.scanner.api/
│   ├── main.py
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── invoice.scanner.frontend.react/
│   ├── Dockerfile                (Production)
│   ├── Dockerfile.dev            (Local hot-reload)
│   ├── package.json
│   └── vite.config.mjs
├── invoice.scanner.cloud.functions/
│   ├── main.py                   (5 Cloud Functions)
│   ├── deploy.sh                 (Deploy to GCP)
│   ├── local_server.sh           (Local simulation)
│   └── requirements.txt
└── invoice.scanner.db/
    └── init.sql                  (Schema initialization)
```

---
## �️ Arkitektur & Deployment

### Local Development Architecture

**dev-start.sh - Startup Script**
```bash
# This unified script starts EVERYTHING:

1. Prerequisites check
   ├─ Docker & Docker Compose installed?
   └─ Python 3.11+ installed?

2. Terminal 1: Docker Compose (stays in foreground)
   ├─ Detects host machine IP
   ├─ Starts: db, api, frontend
   ├─ Wait 10 seconds for health checks
   └─ Logs: docker-compose ps

3. Terminal 2: Cloud Functions Framework (new Terminal window)
   ├─ Opens new Terminal automatically (macOS)
   ├─ Runs: invoice.scanner.cloud.functions/local_server.sh
   ├─ Sets environment variables from .env
   └─ Starts: functions-framework on :9000

# On exit (Ctrl+C):
#   - Gracefully stops docker-compose
#   - Cleanup: docker-compose down
```

**docker-compose.yml - Local Services**
```yaml
services:
  db:                    # PostgreSQL 16
    ├─ Port: 5432
    ├─ User: scanner / scanner
    ├─ Database: invoice_scanner
    ├─ Health: pg_isready check
    └─ Init: ./invoice.scanner.db/init.sql

  api:                   # Flask REST API
    ├─ Port: 5001
    ├─ Image: ./invoice.scanner.api/Dockerfile
    ├─ Env: DATABASE_*, STORAGE_*, FLASK_ENV
    ├─ Processing: http://host.docker.internal:9000
    └─ Volumes: ./documents/

  frontend:              # React with Vite
    ├─ Port: 8080
    ├─ Image: ./invoice.scanner.frontend.react/Dockerfile.dev
    ├─ Hot-reload: ON (watches file changes)
    └─ Volumes: ./invoice.scanner.frontend.react/ (live edits)
```

**local_server.sh - Cloud Functions Framework**
```bash
# Cloud Functions Local Server:

Setup:
├─ Find Python (3.11, 3.10, or 3.9+)
├─ Install requirements.txt
└─ Set environment variables

Startup:
├─ PYTHONUNBUFFERED=1 (log immediately)
├─ DATABASE_* env vars (connect to local PostgreSQL)
└─ Start functions-framework on :9000

Entry Point:
└─ cf_preprocess_document (Pub/Sub triggered locally)
```

### GCP Deployment Pipeline

**GitHub Actions (pipeline.yml) - Automated CI/CD**

The pipeline has stages:

```
┌─────────────────────────────────────────────────────────────────┐
│                   PUSH TO re_deploy_start                        │
│                     (TEST Environment)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│   JOB 1: build-test                                              │
│   ├─ Check [deploy-cf] flag in commit message                   │
│   ├─ Build API image → Artifact Registry (test)                 │
│   ├─ Build Frontend image → Artifact Registry (test)            │
│   └─ Output: deploy_cloud_functions flag (true/false)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
        [deploy-cf]? YES    [deploy-cf]? NO
                    ↓                   ↓
        ┌──────────────────┐  Skip CF Deploy
        │ JOB 2:           │
        │ deploy-cloud-    │
        │ functions-test   │
        │ ├─ Run ./deploy.sh
        │ │   strawbayscannertest
        │ │   europe-west1
        │ ├─ Deploy 5 Cloud Fn
        │ └─ Verify deployment
        └──────────────────┘
                    ↓
        ┌──────────────────┐
        │ JOB 3:           │
        │ deploy-test      │
        │ ├─ Fetch secrets │
        │ ├─ Deploy API to │
        │ │   Cloud Run    │
        │ ├─ Deploy Frontend
        │ ├─ Smoke tests   │
        │ └─ Get URLs      │
        └──────────────────┘
                    ↓
           ✅ TEST LIVE
                    ↓
        ┌──────────────────┐
        │ JOB 4:           │
        │ approval-gate    │
        │ ├─ Pause for     │
        │ │   manual review│
        │ └─ Requires      │
        │    GitHub approval
        └──────────────────┘
                    ↓
        ┌──────────────────┐
        │ PROD Pipeline    │
        │ (same as TEST)   │
        │ but for PROD     │
        │ project          │
        └──────────────────┘
                    ↓
           ✅ PROD LIVE
```

**Key Pipeline Features:**
- `[deploy-cf]` flag: Triggers Cloud Functions deployment (if present in commit)
- Approval gate: Manual review required between TEST & PROD
- Automatic rollback: Not configured (manual remediation required)
- Artifact Registry: Stores versioned images (git SHA)
- Secret Manager: Auto-injected at deployment time
- Smoke tests: POST-deployment health checks

---

## 📚 Development Workflow

### Step-by-Step: Adding a New Feature

**Step 1: Start Local Development**
```bash
./dev-start.sh
# Opens 2 terminals:
# - Terminal 1: Docker services running
# - Terminal 2: Cloud Functions Framework running
```

**Step 2: Make Code Changes**
```bash
# Frontend: Changes appear instantly (hot-reload)
# API: docker-compose restart api (if Flask code changes)
# Cloud Functions: Restart local_server.sh terminal (if CF changes)

# Example: Edit React component
vim invoice.scanner.frontend.react/src/components/Dashboard.jsx
# Changes appear instantly in :8080 ✅
```

**Step 3: Commit & Push to TEST**
```bash
git add .
git commit -m "Add feature X"
# Without [deploy-cf] flag: Only API + Frontend deploy

git commit -m "Add feature X [deploy-cf]"
# With [deploy-cf] flag: Also deploys Cloud Functions

git push origin re_deploy_start
```

**Step 4: GitHub Actions Automatically**
```
✓ Builds API + Frontend images
✓ (Optional) Deploys Cloud Functions if [deploy-cf]
✓ Deploys to Cloud Run TEST
✓ Runs smoke tests
✓ TEST is live in ~5 minutes
```

**Step 5: Test in TEST Environment**
```bash
# Upload a test document via TEST Frontend
# Verify: Document processes through all 5 Cloud Functions
# Verify: Database updates correctly
# Check logs if issues arise
```

**Step 6: Create PR to Production**
```bash
# GitHub: Create Pull Request
# Branch: re_deploy_start → main
# Review & Approve
```

**Step 7: Merge Triggers PROD Deployment**
```bash
git merge re_deploy_start  # (on main)
# GitHub Actions automatically:
# ✓ Builds for PROD
# ✓ (Optional) Deploys CF to PROD
# ✓ Waits for manual approval
# ✓ Deploys API + Frontend to PROD
# ✓ PROD is live in ~10 minutes
```

### When to Use [deploy-cf] Flag

```bash
# INCLUDE [deploy-cf] when modifying:
✓ invoice.scanner.cloud.functions/main.py    → MUST use flag
✓ Cloud Functions logic, requirements.txt     → MUST use flag
✓ Pub/Sub topics or orchestration           → MUST use flag

# DO NOT include [deploy-cf] when modifying:
✗ API endpoints or business logic            → skip flag
✗ Frontend components or styling             → skip flag
✗ Database queries or models                 → skip flag
✗ Configuration or environment variables     → skip flag
```

### Important Git Branches

| Branch | Purpose | Deploys To |
|--------|---------|-----------|
| `re_deploy_start` | Development & testing | TEST only |
| `main` | Production release | PROD only |
| `feature/*` | Feature branches | (merge to re_deploy_start) |

---

## 🏷️ Understanding [deploy-cf] Flag

### What Does [deploy-cf] Do?

The `[deploy-cf]` flag in commit messages tells GitHub Actions to **ONLY deploy Cloud Functions**. Here's what happens:

**WITHOUT [deploy-cf] flag:**
```
git push origin re_deploy_start
  ↓
GitHub Actions:
  ✓ Builds API image (new version)
  ✓ Builds Frontend image (new version)
  ✓ Deploys API to Cloud Run TEST (NEW)
  ✓ Deploys Frontend to Cloud Run TEST (NEW)
  ✗ Skips Cloud Functions (keeps old version)
```

**WITH [deploy-cf] flag:**
```
git commit -m "Fix CF logic [deploy-cf]"
git push origin re_deploy_start
  ↓
GitHub Actions:
  ✓ Builds API image (new version)
  ✓ Builds Frontend image (new version)
  ✓ Deploys API to Cloud Run TEST (NEW)
  ✓ Deploys Frontend to Cloud Run TEST (NEW)
  ✓ Deploys Cloud Functions to TEST (NEW) ← [deploy-cf] triggers this
```

### Real-World Examples

**Example 1: Fix a bug in API endpoint**
```bash
# Changes: invoice.scanner.api/main.py
git commit -m "Fix API validation logic"  # ← NO [deploy-cf]
git push origin re_deploy_start

# Result: API deploys, Cloud Functions stay same
```

**Example 2: Update Cloud Functions processing**
```bash
# Changes: invoice.scanner.cloud.functions/main.py
git commit -m "Improve OCR extraction [deploy-cf]"  # ← WITH [deploy-cf]
git push origin re_deploy_start

# Result: Both API AND Cloud Functions deploy
```

**Example 3: Update both API and Cloud Functions**
```bash
# Changes: invoice.scanner.api/main.py + invoice.scanner.cloud.functions/main.py
git commit -m "Sync API and CF changes [deploy-cf]"  # ← WITH [deploy-cf]
git push origin re_deploy_start

# Result: Both API AND Cloud Functions deploy (necessary for consistency)
```

### Why This Matters

- **Cloud Functions are expensive to deploy** - Takes ~2-3 minutes per function
- **API & Frontend are fast** - Takes ~1 minute combined
- **[deploy-cf] flag optimizes cost & time** - Only deploy CF when code actually changes

### Checklist

Before committing:
- [ ] Did I modify `invoice.scanner.cloud.functions/main.py`? → Use `[deploy-cf]`
- [ ] Did I modify `requirements.txt` in cloud.functions? → Use `[deploy-cf]`
- [ ] Did I modify Pub/Sub topics or orchestration? → Use `[deploy-cf]`
- [ ] Did I only modify API or Frontend? → Skip `[deploy-cf]`
- [ ] Did I only modify database schema? → Skip `[deploy-cf]`

---

## 🔧 Configuration & Secrets

### File Reference

| Fil | Vad | Ändra? | Process |
|-----|-----|--------|---------|
| `.github/workflows/pipeline.yml` | Automated CI/CD | ❌ Fråga först | Changes require approval |
| `docker-compose.yml` | Local services | ⚠️ Fråga först | Test locally first |
| `dev-start.sh` | Startup script | ✅ Ja | Restart services |
| `invoice.scanner.cloud.functions/main.py` | 5 Cloud Functions | ✅ Ja | Use [deploy-cf] flag |
| `invoice.scanner.cloud.functions/local_server.sh` | Local CF simulator | ✅ Ja | Restart local_server.sh |
| `invoice.scanner.api/main.py` | Flask API | ✅ Ja | docker-compose restart api |
| `invoice.scanner.api/Dockerfile` | API container | ✅ Ja | docker-compose rebuild api |
| `invoice.scanner.frontend.react/` | React app | ✅ Ja | Auto hot-reload (local) |
| `invoice.scanner.frontend.react/Dockerfile.dev` | Dev hot-reload | ✅ Ja | Rebuild if changed |
| `invoice.scanner.frontend.react/Dockerfile` | Production build | ✅ Ja | Redeploy on pipeline |
| `invoice.scanner.db/init.sql` | Database schema | ⚠️ Fråga först | Requires migration plan |

### GCP Projects

**TEST Project: strawbayscannertest**
```
Region:           europe-west1
Cloud Run:        invoice-scanner-{api,frontend}-test
Cloud Functions:  5 functions (test)
Cloud SQL:        invoice-scanner-test
Artifact Registry: europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner
```

**PROD Project: strawbayscannerprod**
```
Region:           europe-west1
Cloud Run:        invoice-scanner-{api,frontend}-prod
Cloud Functions:  5 functions (prod)
Cloud SQL:        invoice-scanner-prod
Artifact Registry: europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner
```

### Secret Manager

**TEST Secrets (strawbayscannertest):**
```
db_user_test              = scanner_test
db_password_test          = (generated password)
secret_key_test           = (Flask secret)
gmail_sender              = (company email)
gmail_password            = (app password)
openai_api_key            = (API key)
```

**PROD Secrets (strawbayscannerprod):**
```
db_user_prod              = scanner_prod
db_password_prod          = (generated password)
secret_key_prod           = (Flask secret)
gmail_sender              = (company email)
gmail_password            = (app password)
openai_api_key            = (API key)
```

Secrets are automatically injected by pipeline.yml during deployment.

---

## 🆘 Troubleshooting & Diagnostics

### Local Development Issues

**Frontend not hot-reloading**
```bash
# Issue: Changes not appearing in :8080
# Solution:
docker-compose logs frontend  # Check for build errors
docker-compose restart frontend
# Or rebuild:
docker-compose up -d --build frontend
```

**API connection errors**
```bash
# Issue: Frontend can't reach API (:5001)
# Check:
docker-compose ps            # Is API running?
curl http://localhost:5001/health  # API responding?
docker-compose logs api      # Check API logs

# Solution:
docker-compose restart api
# OR rebuild:
docker-compose up -d --build api
```

**Database connection issues**
```bash
# Issue: "could not connect to database"
# Check:
docker-compose ps            # Is db running?
docker-compose logs db       # Check db logs

# Solution:
docker-compose down -v       # Remove volumes
docker-compose up -d db
sleep 10                     # Wait for startup
docker-compose up -d api     # Reconnect API
```

**Cloud Functions Framework not responding**
```bash
# Issue: :9000 returns connection refused
# Solution:
# Check terminal 2 is running (should have opened automatically)
# If not, manually start:
cd invoice.scanner.cloud.functions
./local_server.sh

# If still failing:
python3.11 -m pip install -r requirements.txt
./local_server.sh
```

**"Port already in use" error**
```bash
# Issue: Address already in use (ports :5001, :8080, :5432, :9000)
# Find process:
lsof -i :5001           # Find process on port 5001
lsof -i :8080
lsof -i :5432
lsof -i :9000

# Kill process:
kill -9 <PID>           # Or use Activity Monitor

# Clean restart:
docker-compose down -v
./dev-start.sh
```

### GCP Deployment Issues

**Cloud Functions deployment fails**
```bash
# Check GitHub Actions logs:
1. Go to: github.com/yourrepo/actions
2. Find failed pipeline run
3. Click "deploy-cloud-functions-test" (or PROD)
4. View full logs

# Common issues:
- [deploy-cf] flag missing in commit message
- GCP credentials invalid (check SECRETS in GitHub)
- Requirements.txt has installation errors
- Function name mismatches in main.py

# Manual deployment for debugging:
cd invoice.scanner.cloud.functions
./deploy.sh strawbayscannertest europe-west1
```

**Cloud Run deployment fails**
```bash
# Check logs:
gcloud run logs read invoice-scanner-api-test \
  --project=strawbayscannertest \
  --region=europe-west1 \
  --limit=50

# Common issues:
- Port not exposed (check main.py: app.run(port=5000))
- Missing environment variables (check pipeline.yml)
- Database connection string incorrect
- Secrets not accessible
```

**Document processing fails end-to-end**
```bash
# Check flow:
1. Frontend upload → check browser console
2. API receives → gcloud run logs read (API)
3. Cloud Functions execute → 
   gcloud functions describe cf_preprocess_document \
     --region=europe-west1 \
     --project=strawbayscannertest \
     --gen2
4. Database updates → check Cloud SQL

# Typical issues:
- Missing Cloud Functions (check deployment)
- Pub/Sub topics not configured
- Database user permissions
- API can't reach Cloud Functions
```

### Checking Logs

**Local:**
```bash
docker-compose logs -f api         # API logs
docker-compose logs -f frontend    # Frontend logs
docker-compose logs -f db          # Database logs
# Cloud Functions logs: Check Terminal 2 window
```

**GCP Cloud Run:**
```bash
# TEST
gcloud run logs read invoice-scanner-api-test \
  --project=strawbayscannertest \
  --region=europe-west1

# PROD
gcloud run logs read invoice-scanner-api-prod \
  --project=strawbayscannerprod \
  --region=europe-west1
```

**GCP Cloud Functions:**
```bash
# TEST
gcloud functions logs read cf_preprocess_document \
  --region=europe-west1 \
  --project=strawbayscannertest \
  --gen2

# PROD
gcloud functions logs read cf_preprocess_document \
  --region=europe-west1 \
  --project=strawbayscannerprod \
  --gen2
```

**GitHub Actions Pipeline:**
1. Go to: https://github.com/yourrepo/.github/workflows/
2. Click "pipeline.yml"
3. Find your run
4. Click failed job name
5. View step logs

---

## ⚠️ TODO - Email Configuration (Pending)

**Status:** Email system implemented but secrets not yet created

**Required Setup:**

1. Create SendGrid account:
   ```
   Visit: https://sendgrid.com
   Sign up → Get API key
   ```

2. Create GCP Secret Manager secrets:
   ```bash
   # TEST - Create SendGrid API key secret
   echo "SG.xxxxx..." | gcloud secrets create sendgrid_api_key_test \
     --project=strawbayscannertest \
     --replication-policy="automatic" \
     --data-file=-

   # PROD - Create SendGrid API key secret  
   echo "SG.xxxxx..." | gcloud secrets create sendgrid_api_key_prod \
     --project=strawbayscannerprod \
     --replication-policy="automatic" \
     --data-file=-
   ```

3. Add Gmail credentials to LOCAL .env file:
   ```
   GMAIL_SENDER=your-email@gmail.com
   GMAIL_PASSWORD=your-app-specific-password
   ```

**Email Flow:**
- LOCAL (docker-compose): Gmail SMTP ✅ Configured
- TEST (Cloud Run): SendGrid API ⏳ Awaiting secret creation
- PROD (Cloud Run): SendGrid API ⏳ Awaiting secret creation

---

## 📝 Changelog

**December 28, 2025 - EMAIL SYSTEM IMPLEMENTED**
- ✅ email_service.py: Smart environment-based routing
- ✅ docker-compose.yml: ENVIRONMENT variable added
- ✅ pipeline.yml: TEST and PROD deployments updated
- ⏳ TODO: Create SendGrid API key secrets in GCP

**December 28, 2025 - PROD DEPLOYMENT COMPLETE**
- ✅ Production environment fully operational
- ✅ All 5 Cloud Functions deployed to PROD
- ✅ API + Frontend live in PROD
- ✅ Entire CI/CD pipeline end-to-end tested
- ✅ TEST and PROD synchronized
- ✅ Documentation updated with deployment diagrams
- ✅ Troubleshooting guide added
- ✅ Quick commands reference added

**Key Accomplishments (FASE 9 Complete):**
- ✅ Unified Cloud Functions architecture (same code everywhere)
- ✅ GitHub Actions pipeline fully automated
- ✅ Manual approval gate between TEST and PROD
- ✅ Secret Manager integration verified
- ✅ Database status updates working
- ✅ Pub/Sub orchestration end-to-end
- ✅ Local development fully functional

**Active Monitoring:**
- Monitor PROD stability and performance
- Keep LOCAL, TEST and PROD synchronized
- Ready for new features with established workflow
