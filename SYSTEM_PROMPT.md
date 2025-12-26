# System Prompt för Invoice Scanner Projekt

## 🎯 CURRENT STATUS (Dec 26, 2025 - ~21:30)

**Overall Progress:** 90% Complete (pg8000 Migration Complete - Cloud SQL Initialized - GitHub Actions Automated Deployment Starting)

| FASE | Status | Details |
|------|--------|---------|
| FASE 0 | ✅ 100% | GCP Infrastructure (APIs, Service Accounts, GitHub Secrets) |
| FASE 1 | ✅ 100% | GCP Secret Manager (12 secrets: db_password, secret_key, gmail, openai) |
| FASE 2 | ✅ 100% | Cloud SQL (PostgreSQL instances initialized + schemas deployed) |
| FASE 3 | ✅ 100% | Docker Images (api, frontend, worker - pushed to both registries) |
| FASE 4 | ✅ 100% | GitHub Actions: Single unified pipeline.yml with conditional jobs |
| FASE 4B | ✅ 100% | Local Docker-Compose: Tested and verified, port standardization |
| FASE 4C | ✅ 100% | Database Driver Migration: pg8000 unified driver (COMPLETED & tested) |
| FASE 5 | ⏳ 20% | Cloud Run Deployment (Database initialized - GitHub Actions deployment starting) |
| FASE 6-8 | 0% | Cloud Tasks, Testing, Monitoring |

**Session Dec 26 - pg8000 Migration Complete**

✅ **MIGRATION COMPLETED:**
- Successfully migrated from psycopg2 to pg8000 (Pure Python PostgreSQL driver)
- pg8000 is only driver supported by Cloud SQL Connector (pymysql, pg8000, pytds)
- Unified database configuration: all modules now use pg8000
- Standardized environment variables: all use DATABASE_* naming convention (no DB_* mixing)

✅ **Implementation Completed:**
1. ✅ Created pg8000_wrapper.py with RealDictCursor compatibility in both API and Processing
2. ✅ Updated requirements.txt: removed psycopg2-binary, added pg8000
3. ✅ API db_config.py already using DATABASE_* variables
4. ✅ Processing config/db_utils.py already using DATABASE_* variables
5. ✅ docker-compose.yml already standardized to DATABASE_* naming

✅ **Local Testing Verified:**
- All 14 containers start and become healthy
- API connects to database via pg8000 TCP (log: "Using pg8000 TCP connection")
- Processing workers connect and ready for tasks
- pg8000_wrapper RealDictCursor compatibility layer working
- Document processing successful (status updates working)
- Git committed with detailed message (commit: 03db1c6)

**Next:** Automated GitHub Actions deployment starting (Option A - push to re_deploy_start branch to trigger build + deploy-test)

---

## Kritiska Instruktioner för AI-assistenten

### 1. UNDERSÖK FÖRST - SKAPA SIST
**ALDRIG** börja skapa filer, dockerfiler, konfigurationer eller strukturer utan att först:
- ✅ Läsa vad som redan finns (`ls -la`, `find`, `cat`)
- ✅ Förstå den befintliga arkitekturen
- ✅ Checka `git status` och befintliga branches
- ✅ **FRÅGA ANVÄNDAREN** vad som redan är gjort innan du börjar

### 2. FRÅGA INNAN DU GÖR KAOS
Om du tänker skapa:
- Flera konfigurationsfiler (docker-compose.yml, .env-filer, etc.)
- Deployment-strukturer eller GitHub Actions
- Stora config-system
- Dokumentation

**FRÅGA ALLTID ANVÄNDAREN:**
```
Innan jag börjar, vill du att jag ska:
1. [Alternativ A]
2. [Alternativ B]
3. [Alternativ C]

Eller har du redan något specifikt i åtanke?
```

### 3. GREP OCH EXAMINE FÖRST
Innan ändringar i existerande kod:
```bash
# Checka vad som redan finns
grep -r "docker-compose" .
grep -r "ENVIRONMENT" .
git log --oneline -10

# Förstå arkitekturen
find . -name "*.yml" -o -name "*.yaml" | head -20
find . -name "Dockerfile*" | head -20
find . -name "requirements.txt" | head -20
```

### 4. RESPEKTERA BEFINTLIGA DECISIONS
- Om det redan finns en docker-compose.yml → modifiera, inte skapa nya
- Om det redan finns en Dockerfile-struktur → följ samma mönster
- Om det redan finns en requirements.txt → checka innehållet innan du lägger till
- Om det redan finns ett branch-system → förstå namngivningen

### 5. DOKUMENTERA VALEN
När du gör ändringar, förklara:
- ✅ VAD du gjorde
- ✅ VARFÖR du gjorde det så
- ✅ VAD som redan fanns
- ✅ VAD som är nästa steg

### 6. FELLA FÄLLORNA
**GÖR INTE:**
- Skapa 16+ deployment-filer på gut känsla
- Implementera komplexe system utan att fråga först
- Ignorera att `docker-compose.local.yml` redan kan existera
- Anta att användaren vill ha Path A/B/C utan att fråga

### 7. EFTER VARJE OPERATION
- Läs denna fil och se till att hålla kritiska instruktioner i minnet.
- **SPECIELL UPPMÄRKSAMHET:** Se avsnittet "DATABASE DRIVER STRATEGY: pg8000 Migration"
- Kolla Current Status för vad som är KLART vs ⏳ vs ❌

**GÖR:**
- Undersök först
- Fråga
- Vänd på tanken om det redan finns en bättre lösning
- Respektera befintliga design-beslut

### 8. KRITISKA REGLER FÖR pg8000 MIGRATIONEN (Dec 26)

**ALDRIG implementera pg8000-migrationen utan att:**
1. ✅ Läsa ALLA filer som använder `psycopg2.connect()` eller `RealDictCursor`
2. ✅ Förstå hur RealDictCursor används i varje fil
3. ✅ Grep-a för alla `DB_*` och `DATABASE_*` environment variables
4. ✅ Verifiera att docker-compose.yml får samma update
5. ✅ Testa lokalt med alla 13 containers innan Cloud Run
6. ✅ **HÅLLA ENHETLIGHET:** Inte blanda DATABASE_* och DB_* naming

**GÖR:**
- Refactor systematiskt (API → Processing → docker-compose)
- Test lokalt efter VARJE steg
- Bekräfta att RealDictCursor wrapper fungerar identiskt
- Dokumentera ändringar i git commits

**GÖR INTE:**
- Implementera endast halva migrationen
- Blanda gamla och nya environment variable-namn
- Hoppa över processing-modulen
- Förvänta Cloud Run att fungera innan lokal test är klar

## Projekt-specifikt

### Invoice Scanner Status
- **Repo:** https://github.com/Rickard-E-Strawbay/invoice.scanner
- **Branch-struktur:** main (production), re_deploy_start (current development)
- **Huvuddelar:** API (Flask), Frontend (React), Processing (Workers)
- **Docker:** Använder docker-compose.yml (INTE docker-compose.local.yml)

### Innan du skapar något deployment/GCP-relaterat:
1. FRÅGA vad som redan är gjort
2. Läs deployment/ om det finns
3. Checka .github/workflows om GitHub Actions redan finns
4. Fråga om vilken PATH (A/B/C) eller approach användaren vill ha

### Filer att ALDRIG skapa utan att fråga:
- Nya docker-compose*.yml
- .env-filer eller .env.*
- Deployment-manualer (15000+ ord)
- GitHub Actions workflows
- Hela config-system (invoice.scanner.api/config/)

## Användarens Preferenser
- Vill ha ENKLA lösningar först
- Vill att jag ska FRÅGA innan komplexitet
- Gillar TYDLIGA instruktioner
- Vill FÖRSTÅ vad som görs, inte bara att det görs

---

## GCP DEPLOYMENT ARKITEKTUR & STRATEGI

### Infrastruktur-beslut (GODKÄND av användare)

**Secrets Management:**
- ✅ GitHub Secrets: Endast `GCP_SA_KEY` (Service Account JSON)
- ✅ GCP Secret Manager: Alla application secrets (DB passwords, API keys, etc.)
- Full audit trail + rotation via GCP

**Databas:**
- ✅ Cloud SQL PostgreSQL (test + prod)
- Private networking (inte exponerat)
- Automatisk backup på prod

**Deployment-modell:**
```
┌─────────────────────────────────────────────────┐
│  API + Frontend: Cloud Run (persistent)         │
│  - Alltid tillgänglig                           │
│  - Auto-scaling på trafik                       │
│  - ~$10-50/månad för låg trafik                 │
│                                                 │
│  Workers: Serverless (on-demand)                │
│  - Preprocessing, OCR, LLM, Extraction         │
│  - Cloud Tasks + Cloud Pub/Sub                 │
│  - Betala bara per execution                   │
│                                                 │
│  Data: Cloud SQL + Cloud Storage               │
└─────────────────────────────────────────────────┘
```

---

## CI/CD PIPELINE - DETALJERAD DEFINITION (v3 - UNIFIED - Dec 25)

### Branch-strategi (PR-baserad säkerhet)

```
1. Developer creates feature branch
   └─ git checkout -b feature/my-feature
   
2. Developer pushes and creates Pull Request against re_deploy_start
   └─ GitHub: Requires 1 approval
   └─ GitHub: PR must be reviewed

3. Reviewer approves PR
   └─ Developer merges to re_deploy_start

4. After merge to re_deploy_start:
   └─ pipeline.yml:build triggers automatically (push event)
   └─ Auto-detects branch = re_deploy_start
   └─ Builds images, pushes to TEST Artifact Registry
   └─ pipeline.yml:deploy-test triggers automatically (after build)
   └─ Deploys to TEST Cloud Run
   └─ Smoke tests run
   └─ ✅ TEST environment live

5. For PROD: Developer creates PR main ← re_deploy_start
   └─ GitHub: Requires 1-2 approvals
   └─ GitHub: PR must be reviewed

6. Reviewer approves PROD PR
   └─ Developer merges to main

7. After merge to main:
   └─ pipeline.yml:build triggers automatically (push event)
   └─ Auto-detects branch = main
   └─ Builds images, pushes to PROD Artifact Registry
   └─ pipeline.yml:deploy-prod job appears (waiting)
   └─ ⚠️ MANUAL APPROVAL GATE (GitHub environment: "production")
   └─ Admin/Reviewer clicks "Approve" in GitHub UI
   └─ pipeline.yml:deploy-prod resumes (24h timeout)
   └─ Deploys to PROD Cloud Run
   └─ Smoke tests run
   └─ ✅ PROD environment live
```

### GitHub Actions Workflows (1 file, 3 conditional jobs - FINAL)

**File:** `.github/workflows/pipeline.yml`

**Structure:**
```yaml
on:
  push:
    branches: [re_deploy_start, main]

jobs:
  build: ...              # Always runs (detects branch)
  deploy-test: ...        # Runs only on re_deploy_start (needs: build)
  deploy-prod: ...        # Runs only on main (needs: build, environment: production)
```

#### 1️⃣ build job - Build & Push Docker Images (UNIFIED)
**Triggers:** Push to `re_deploy_start` OR `main`

**Auto-detects branch and uses correct GCP project:**
```yaml
Branch detection logic (in first step):
  if github.ref == 'refs/heads/main' 
    → use GCP_SA_KEY_PROD 
    → push to strawbayscannerprod registry
  
  else (re_deploy_start)
    → use GCP_SA_KEY_TEST 
    → push to strawbayscannertest registry
```

**Docker images som byggs:**
- `api:latest` & `api:{git-sha}` 
- `frontend:latest` & `frontend:{git-sha}`
- `worker:latest` & `worker:{git-sha}` (optional)

**Push location (auto-detected):**
- TEST-projekt: `europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/`
- PROD-projekt: `europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/`

**Steps i build job:**
```yaml
1. Checkout code
2. Detect branch → determine GCP project + registry + SA key
3. Authenticate to Google Cloud (GCP_SA_KEY_TEST or GCP_SA_KEY_PROD)
4. Configure Docker authentication to Artifact Registry
5. Build API image:     docker build → tag latest + sha → push
6. Build Frontend image: docker build → tag latest + sha → push
7. Build Worker image:   docker build → tag latest + sha → push (if exists)
8. Build summary: Show which environment + registry used
```

**Outputs from build:**
- `registry` - Which Artifact Registry used
- `environment` - "test" or "prod"
- `gcp_project` - Project ID used

#### 2️⃣ deploy-test job - Deploy to TEST (Conditional on re_deploy_start)
**Triggers:** After pipeline.yml:build completes, ONLY if on `re_deploy_start`
**Condition:** `if: github.ref == 'refs/heads/re_deploy_start'`
**Environment:** GitHub environment "test" (no approval required)
**Dependencies:** `needs: build`

**What it does:**
1. Waits for build job to complete
2. Only runs if branch is re_deploy_start
3. Authenticates to GCP TEST project
4. Fetches 5 secrets from GCP Secret Manager (test project)
5. Deploys invoice-scanner-api-test to Cloud Run
6. Deploys invoice-scanner-frontend-test to Cloud Run
7. Runs smoke tests (curl /health endpoint)
8. Outputs service URLs

**Configuration:**
- Memory: API 512Mi, Frontend 256Mi
- CPU: 1 for each
- Max instances: 10 each
- Environment variables: Auto-injected from GCP secrets

#### 3️⃣ deploy-prod job - Deploy to PROD (Conditional on main, with manual approval)
**Triggers:** After pipeline.yml:build completes, ONLY if on `main`
**Condition:** `if: github.ref == 'refs/heads/main'`
**Environment:** GitHub environment "production" (REQUIRES manual approval)
**Dependencies:** `needs: build`

**What it does:**
1. Waits for build job to complete
2. Only runs if branch is main
3. ⚠️ PAUSES and waits for manual approval (24h timeout)
4. After approval: Authenticates to GCP PROD project
5. Fetches 5 secrets from GCP Secret Manager (prod project)
6. Deploys invoice-scanner-api-prod to Cloud Run
7. Deploys invoice-scanner-frontend-prod to Cloud Run
8. Runs smoke tests
9. Outputs service URLs

**Configuration:**
- Memory: API 512Mi, Frontend 256Mi
- CPU: 1 for each
- Min instances: 1 each (always running - cheaper idle state)
- Max instances: 20 each (auto-scale under load)
- Environment variables: Auto-injected from GCP secrets (prod variants)

### Arkitektur-diagram (UPDATED - UNIFIED)
```
┌──────────────────────────────────────────────────────────────────┐
│                         GitHub                                   │
│  main (prod) ←─ Pull Request ← re_deploy_start (dev)            │
└────────────────────┬───────────────────────┬─────────────────────┘
                     │                       │
                     │ Push to main          │ Push to re_deploy_start
                     │                       │
         ┌───────────▼─────────┐   ┌────────▼──────────────┐
         │   pipeline.yml      │   │   pipeline.yml        │
         │   :build job        │   │   :build job          │
         │ (GCP_SA_KEY_PROD)   │   │ (GCP_SA_KEY_TEST)     │
         │ Build & Push Images │   │ Build & Push Images   │
         │ to PROD registry    │   │ to TEST registry      │
         └──────────┬──────────┘   └────────┬──────────────┘
                    │                       │
         ┌──────────▼──────────┐   ┌────────▼──────────────┐
         │  Artifact Registry  │   │ Artifact Registry    │
         │   PROD Project      │   │  TEST Project        │
         │  (eu-west1 repo)    │   │  (eu-west1 repo)     │
         └──────────┬──────────┘   └────────┬──────────────┘
                    │                       │
         ┌──────────▼────────────┐   ┌─────▼──────────────┐
         │  pipeline.yml         │   │  pipeline.yml      │
         │  :deploy-prod job     │   │  :deploy-test job  │
         │ (requires approval!)  │   │ (auto-run)         │
         │                       │   │                    │
         │ ⚠️ MANUAL APPROVAL    │   │ Fetch secrets_test │
         │ GATE (24h timeout)    │   │ Deploy to TEST     │
         │ <CLICK "APPROVE">     │   └─────┬──────────────┘
         │                       │         │
         │ After approval:       │    ┌────▼──────────────┐
         │ Fetch secrets_prod    │    │  TEST Cloud Run   │
         │ Deploy to PROD        │    │  - api-test       │
         └──────────┬────────────┘    │  - frontend-test  │
                    │                 │ Smoke tests OK    │
         ┌──────────▼──────────┐      └───────────────────┘
         │  PROD Cloud Run     │
         │  - api-prod         │
         │  - frontend-prod    │
         │ Smoke tests OK      │
         └─────────────────────┘
```

**Key points:**
- ✅ Single `pipeline.yml` file (not 3 separate files)
- ✅ All jobs in one place
- ✅ Branch detection in first step of build job
- ✅ deploy-test runs ONLY if branch is re_deploy_start
- ✅ deploy-prod runs ONLY if branch is main (with approval)
- ✅ Clean, maintainable, no duplication

### Secret Manager Mapping

**GCP Secret Manager → Environment Variables:**

TEST-projekt (`strawbayscannertest`):
```
Secret name              → Env var               → Används i
─────────────────────────────────────────────────────────────────
db_user_test            → DATABASE_USER         → Cloud Run API
db_password_test        → DATABASE_PASSWORD     → Cloud Run API
secret_key_test         → FLASK_SECRET_KEY      → Cloud Run API
gmail_sender            → EMAIL_SENDER          → Cloud Run API
gmail_password          → EMAIL_PASSWORD        → Cloud Run API
openai_api_key          → OPENAI_API_KEY        → Cloud Run API
```

PROD-projekt (`strawbayscannerprod`):
```
Secret name              → Env var               → Används i
─────────────────────────────────────────────────────────────────
db_user_prod            → DATABASE_USER         → Cloud Run API
db_password_prod        → DATABASE_PASSWORD     → Cloud Run API
secret_key_prod         → FLASK_SECRET_KEY      → Cloud Run API
gmail_sender            → EMAIL_SENDER          → Cloud Run API
gmail_password          → EMAIL_PASSWORD        → Cloud Run API
openai_api_key          → OPENAI_API_KEY        → Cloud Run API
```

### GitHub Environments (Manual Approval)

**GitHub → Settings → Environments:**

Skapa två environments:
```
test
├─ Deployment branches: re_deploy_start, feature/*
└─ No approval needed

production
├─ Deployment branches: main
├─ Required reviewers: (Rickard)
└─ Timeout: 24 hours
```

**I pipeline.yml (deploy-prod job):**
```yaml
environment:
  name: production
  url: https://api-prod-xxxxx.run.app
```

---

### Complete CI/CD Flow Exempel (UNIFIED PIPELINE)

**Scenario: Utvecklare pushar feature**

```
1. Utvecklare: git push origin my-feature
2. GitHub: Öppnar PR mot re_deploy_start
3. GitHub: CI-checks kör linting, tester, etc
4. Utvecklare/Reviewer: Merge PR
5. GitHub: Detekterar push till re_deploy_start
6. pipeline.yml:build: 
   - Detekterar branch = re_deploy_start
   - Använder GCP_SA_KEY_TEST
   - Bygger api:latest, frontend:latest, worker:latest
   - Pushar till strawbayscannertest Artifact Registry
7. pipeline.yml:deploy-test (auto-trigger efter build):
   - Villkor: if: github.ref == 'refs/heads/re_deploy_start'
   - Kör automatiskt (no approval needed)
   - Använder GCP_SA_KEY_TEST
   - Hämtar 5 secrets från TEST Secret Manager
   - Deployar till Cloud Run services
   - Kör smoke tests
8. Utvecklare testar på: api-test-xxxxx.run.app
```

**Scenario: Merge till main (PROD deployment)**

```
1. PR merged in GitHub → main
2. GitHub: Detekterar push till main
3. pipeline.yml:build: 
   - Detekterar branch = main
   - Använder GCP_SA_KEY_PROD
   - Bygger och pushar till strawbayscannerprod Artifact Registry
4. pipeline.yml:deploy-prod-job: PAUSES och väntar på approval
   - Villkor: if: github.ref == 'refs/heads/main' + environment: production
   - GitHub visar: "This job requires manual approval"
   - Timeout: 24 timmar
5. Rickard loggar in i GitHub Actions UI
   - Ser deploy-prod job i Pending state
   - Klickar "Review deployments" → "production" → "Approve and deploy"
6. pipeline.yml:deploy-prod (resumed):
   - Använder GCP_SA_KEY_PROD
   - Hämtar 5 secrets från PROD Secret Manager
   - Deployar till Cloud Run (prod services)
   - Kör smoke tests
7. Live på: api-prod-xxxxx.run.app
```

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

### FASE 5: Cloud Run Deployment (GitHub Actions Automated Deployment)
- [x] ✅ Database schema initialized (init.sql deployed to Cloud SQL TEST + PROD)
- [x] ✅ Cloud SQL Proxy configured in pipeline.yml (DATABASE_HOST=localhost)
- [x] ✅ init.sql run manually on Cloud SQL
- [ ] ⏳ Push to re_deploy_start branch (triggers GitHub Actions)
- [ ] ⏳ GitHub Actions:build job - builds 3 Docker images, pushes to TEST registry
- [ ] ⏳ GitHub Actions:deploy-test job - auto-deploys to Cloud Run TEST
- [ ] ⏳ Test login flow (API → Cloud SQL connectivity in Cloud Run)
- [ ] Verify: API service running on Cloud Run TEST
- [ ] Verify: Frontend service running on Cloud Run TEST
- [ ] Setup Cloud Storage bucket (documents)
- [ ] Create PR: re_deploy_start → main (for PROD deployment)

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
