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

## 📋 QUICK REFERENCE - Läs detta först!

**NUVARANDE ARKITEKTUR (Dec 28, 2025):**

| Komponenter | Status | Beskrivning |
|-------------|--------|------------|
| **LOCAL (docker-compose)** | ✅ Ready | 3 services: API, Frontend, PostgreSQL |
| **LOCAL Processing** | ✅ Ready | Cloud Functions Framework på :9000 |
| **GCP Cloud Functions** | ✅ TESTED | 5 functions (preprocess, ocr, llm, extraction, evaluation) |
| **Database** | ✅ Ready | Cloud SQL TEST + PROD |
| **Storage** | ✅ Ready | Local volumes (local) + GCS (cloud) |
| **CI/CD Pipeline** | ✅ Ready | GitHub Actions pipeline.yml |
| **Cloud Run TEST** | ✅ Live | API + Frontend deployed & working |

**Status Dec 28 - ALLT FUNGERAR:**
- ✅ Samma kod kör lokalt och i GCP
- ✅ Cloud Functions Framework simulerar GCP lokalt
- ✅ GCP TEST: Document processing genom alla 5 stadier ✅
- ✅ Database status uppdateras korrekt
- ✅ pg8000 cursor-fix fungerar i produktion
- ✅ Pub/Sub pipeline end-to-end testad

**Nästa steg:**
1. Deploy Cloud Functions till GCP PROD (samma som TEST)
2. Avsluta tester och fokusera på produktion

---

## 🎯 CURRENT STATE (Dec 28, 2025)

### ✅ FASE 7: GCP TEST COMPLETE

**Document Processed Successfully:**
```
Document ID: 12ee3751-0c8d-42a7-8d41-44b857801f86
Status: completed ✅
Pipeline time: ~14 seconds
All 5 Cloud Functions executed in correct order
Database status updates: VERIFIED
```

**Architecture:**
```
BEFORE (Celery):
├── LOCAL: 7 workers + processing_http
└── CLOUD: Separate Cloud Functions code

AFTER (Unified Cloud Functions) ✅:
├── LOCAL: invoice.scanner.cloud.functions/ → :9000
└── CLOUD: Same code via ./deploy.sh
```

**What Works:**
1. ✅ Local docker-compose (4 services)
2. ✅ Cloud Functions Framework locally
3. ✅ GCP Cloud Functions all 5 active
4. ✅ Pub/Sub topic orchestration
5. ✅ Database connectivity via Cloud SQL Connector
6. ✅ Secret Manager integration
7. ✅ pg8000 cursor context manager fixed
8. ✅ Status updates in database

**Folder Structure:**
```
invoice.scanner/
├── .github/workflows/pipeline.yml
├── docker-compose.yml
├── dev-start.sh
├── invoice.scanner.api/
├── invoice.scanner.frontend.react/
├── invoice.scanner.cloud.functions/
│   ├── main.py (5 Cloud Functions)
│   ├── deploy.sh
│   ├── local_server.sh
│   └── requirements.txt
└── invoice.scanner.db/
```

**Deployment Flow:**
```
Commit with [deploy-cf] flag
  ↓
GitHub Actions pipeline.yml:build
  ├─ Detects branch (re_deploy_start = TEST)
  ├─ Builds API + Frontend images
  ├─ Pushes to Artifact Registry
  └─ Checks [deploy-cf] flag
  ↓
pipeline.yml:deploy-cf (if [deploy-cf])
  ├─ Runs ./deploy.sh strawbayscannertest europe-west1
  ├─ Creates/updates 5 Cloud Functions
  ├─ Configures Pub/Sub topics
  └─ Sets env vars from Secret Manager
  ↓
pipeline.yml:deploy-test
  ├─ Deploys API to Cloud Run TEST
  ├─ Deploys Frontend to Cloud Run TEST
  └─ Runs smoke tests
  ↓
✅ TEST LIVE
```

### ⏳ FASE 8: READY FOR PROD

**Samma steg som FASE 7 men för PROD:**
- Replace: `strawbayscannertest` → `strawbayscannerprod`
- Replace: `test` → `prod` in registries
- Run: `./deploy.sh strawbayscannerprod europe-west1`
- Test: Same procedure as TEST
- Result: PROD deployed with manual approval gate

---

## Implementation Plan (5 Steps)

### Step 1: Merge to PROD Branch
```bash
# Create PR: re_deploy_start → main
# GitHub auto-triggers build job
# After approval: deploy-prod job runs
```

### Step 2: Monitor PROD Deployment
```bash
# Watch GitHub Actions for PROD pipeline
# Verify: Cloud Functions deployed to strawbayscannerprod
# Verify: Cloud Run API + Frontend live
```

### Step 3: Test PROD End-to-End
```bash
# Upload document via PROD Cloud Run Frontend
# Verify: All 5 Cloud Functions execute
# Verify: Database status updates
# Verify: No errors in logs
```

### Step 4: Verify Parity with TEST
- Same document processed in TEST and PROD
- Both should have identical results
- Both should complete in similar time

### Step 5: Monitor & Document
- Keep PROD running stable
- Document any issues
- Setup monitoring if needed

---

## Git Workflow för framtida ändringar

**Feature/Fix:**
```bash
# 1. Code change on re_deploy_start
git commit -m "Fix X [deploy-cf]"  # Add flag if Cloud Functions change
git push origin re_deploy_start

# 2. GitHub Actions:
#    - build job builds images
#    - deploy-cf job (if flag) deploys CF to TEST
#    - deploy-test job deploys to Cloud Run TEST
#    - Result: TEST is live

# 3. Create PR: re_deploy_start → main
# 4. Review + Approve
# 5. Merge to main
# 6. GitHub Actions:
#    - build job builds images for PROD
#    - deploy-cf job (if flag) deploys CF to PROD
#    - deploy-prod job (requires approval)
#    - Result: PROD is live (after approval)
```

**Important Flags:**
- `[deploy-cf]` - Include when Cloud Functions code changes
- Without flag: Only API + Frontend deploy (no CF redeploy)

### Filer som gör något särskilt

| Fil | Vad | Ändra? |
|-----|-----|--------|
| `.github/workflows/pipeline.yml` | Auto-build & deploy | Nej |
| `docker-compose.yml` | Local infrastruktur | Fråga först |
| `invoice.scanner.cloud.functions/main.py` | 5 Cloud Functions | Ja + [deploy-cf] |
| `invoice.scanner.api/main.py` | Flask API | Ja |
| `invoice.scanner.frontend.react/` | React UI | Ja |
| `invoice.scanner.db/init.sql` | Database schema | Fråga först |

### GCP Projekt Info

**TEST:**
- Projekt: `strawbayscannertest`
- Region: `europe-west1`
- Cloud SQL: `invoice-scanner-test`
- Status: ✅ TESTED & VERIFIED

**PROD:**
- Projekt: `strawbayscannerprod`
- Region: `europe-west1`
- Cloud SQL: `invoice-scanner-prod`
- Status: ⏳ READY FOR DEPLOYMENT

### Environment Variables i Secret Manager

**TEST-projekt:**
- `db_user_test` = `scanner_test`
- `db_password_test` = (from Secret Manager)
- `secret_key_test` = (generated)
- Plus: gmail_sender, openai_api_key, etc.

**PROD-projekt:**
- `db_user_prod` = `scanner_prod`
- `db_password_prod` = (from Secret Manager)
- `secret_key_prod` = (generated)
- Plus: gmail_sender, openai_api_key, etc.

---

## Summary

**Status:** 🚀 **READY FOR PRODUCTION**

- ✅ Code tested locally
- ✅ Code deployed & tested in GCP TEST
- ✅ All 5 Cloud Functions verified working
- ✅ pg8000 cursor issue fixed
- ✅ Pipeline automation in place
- ✅ Secrets configured
- ⏳ Ready to deploy to PROD

**Next Action:** Create PR from `re_deploy_start` to `main` and merge for PROD deployment.
