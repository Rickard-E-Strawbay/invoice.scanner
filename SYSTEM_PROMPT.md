# System Prompt för Invoice Scanner Projekt

---

## 📋 QUICK REFERENCE - Läs detta först!

| Vad | Status | Vad gör vi |
|-----|--------|-----------|
| **Local Docker** | ✅ Ready | Alla 14 containers bygger + health |
| **pg8000 Driver** | ✅ Complete | Testad med pg8000_wrapper + RealDictCursor |
| **Database** | ✅ Ready | Cloud SQL TEST+PROD initialiserad |
| **GitHub Actions** | ✅ Ready | Pipeline.yml (single file, 3 jobs) |
| **GCP Secrets** | ✅ Ready | 12 secrets i Secret Manager |
| **Docker Images** | ✅ Ready | Api, Frontend, Worker pushed till registries |
| **Cloud Run TEST** | ✅ Live | API rev 00048 + Frontend deployed & working |
| **Admin Panel** | ✅ Working | User/Company management, Enable/Disable buttons |
| **NEXT STEP** | 👉 DO THIS | Test document processing (Scan service) |

**Enkelt sagt:**
- Cloud Run TEST är live och fungerar
- Admin panel fungerar (Enable/Disable buttons working)
- Email är temp disabled (SMTP kan inte nå från Cloud Run)
- Ready to test document processing

---

**Overall Progress:** 98% Complete - Ready for Document Processing Testing

| FASE | Status | Details | Last Updated |
|------|--------|---------|--------------|
| FASE 0 | ✅ 100% | GCP Infrastructure (APIs, Service Accounts, GitHub Secrets) | Dec 25 |
| FASE 1 | ✅ 100% | GCP Secret Manager (12 secrets configured) | Dec 25 |
| FASE 2 | ✅ 100% | Cloud SQL (PostgreSQL instances initialized + schemas deployed) | Dec 26 |
| FASE 3 | ✅ 100% | Docker Images (api, frontend, worker - pushed to both registries) | Dec 24 |
| FASE 4 | ✅ 100% | GitHub Actions: Single unified pipeline.yml with conditional jobs | Dec 25 |
| FASE 4B | ✅ 100% | Local Docker-Compose: Fresh rebuild completed - all 14 containers healthy | Dec 26 22:30 |
| FASE 4C | ✅ 100% | Database Driver Migration: pg8000 unified driver + RealDictCursor wrapper | Dec 26 |
| **FASE 5** | ✅ 100% | Cloud Run Deployment (API & Frontend deployed to TEST) | **Dec 26 16:40** |
| **FASE 5A** | ✅ 100% | JSON Serialization: PG8000DictRow → dict conversion fixes | **Dec 26 16:45** |
| **FASE 5B** | ✅ 100% | VPC Access Connectors: Private IP connectivity TEST+PROD | **Dec 26** |
| **FASE 5C** | ✅ 100% | Session Management: Environment-aware Flask session cookies (HTTPS) | **Dec 26** |
| **FASE 5D** | ✅ 100% | API Response Fields: company_enabled added to user responses | **Dec 26 16:32** |
| **FASE 5E** | ✅ 100% | Email Service: Disabled in Cloud Run (pending SendGrid migration) | **Dec 26 16:40** |
| FASE 6 | ⏳ Testing | Document processing, Scan service validation | **NEXT** |
| FASE 7-8 | 0% | Cloud Tasks, Monitoring, Production validation | Future |

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

## 🎯 FOKUS JUST NU - December 26, 2025 (16:40)

**FASE 5 är COMPLETE:** API & Frontend deployed till Cloud Run TEST ✅

### Vad som är gjort ✅
- ✅ Cloud Run TEST deployment working (API 00048, Frontend deployed)
- ✅ JSON serialization fixed (PG8000DictRow → dict conversion)
- ✅ `company_enabled` field added to user API responses
- ✅ Session cookies environment-aware (HTTPS in Cloud Run)
- ✅ VPC Access Connectors configured for Private IP Cloud SQL
- ✅ Email service disabled (temporary - pending SendGrid migration)
- ✅ Admin user management fully functional (Enable/Disable buttons working)
- ✅ Company management functional (Disable button tested, Enable pending company status)

### Känd begränsning ⚠️
- Email: Disabled i Cloud Run TEST (SMTP kan inte nå Gmail från Cloud Run)
  - Temporary fix: Returns success without sending
  - Long-term: Migrate to SendGrid API
  - Location: `invoice.scanner.api/lib/email_service.py` line 1 (TODO comment in place)

### Nästa steg 👉
**FASE 6: Document Processing / Scan Service Testing**
1. Test document upload via frontend
2. Verify processing service triggers correctly
3. Check vectorstore integration (Chroma)
4. Validate document retrieval

**Blockers:** None - System is fully operational for testing

### Git Status
- Branch: `re_deploy_start` 
- Commits ahead: Latest fixes pushed (email disable, company_enabled fields)
- Ready to: Test FASE 6 (processing) or merge to main for PROD



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
|----------|--------|-----------|
| pg8000 driver | Cloud SQL Connector krävs | Inte psycopg2 |
| DATABASE_* vars | Standardiserad naming | Inte DB_* mix |
| Single pipeline.yml | Clean + maintainable | Inte 3 files |
| Cloud SQL Private IP | Säkerhet | Inte public |
| RealDictCursor wrapper | Backward compatibility | Inte raw pg8000 |
| docker-compose.yml | Source of truth | Inte .local variant |

### VID PROBLEM
Ordning: Logs (GitHub Actions) → Logs (Cloud Run) → Logs (Cloud SQL) → FIX KOD → RE-PUSH

## Användarens Preferenser
- Vill ha ENKLA lösningar först
- Vill att jag ska FRÅGA innan komplexitet
- Gillar TYDLIGA instruktioner
- Vill FÖRSTÅ vad som görs, inte bara att det görs
- **VIKTIGAST:** Trust the pipeline - det är korrekt konfigurerat

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
