# System Prompt för Invoice Scanner Projekt

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

**GÖR:**
- Undersök först
- Fråga
- Vänd på tanken om det redan finns en bättre lösning
- Respektera befintliga design-beslut

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

## CI/CD PIPELINE - DETALJERAD DEFINITION

### Branch-strategi

```
main (production branch)
  └─ Triggers: PROD deployment
  └─ Requires: Manual approval från TEST

re_deploy_start / feature/* (development branches)
  └─ Triggers: TEST deployment
  └─ Automatic: No approval needed
```

### GitHub Actions Workflows (3 st)

#### 1️⃣ build.yml - Build & Push Docker Images
**Triggers:** Push to `re_deploy_start` eller `main`

**Docker images som byggs:**
- `api:test` & `api:prod` (samma image med test/prod tag)
- `frontend:test` & `frontend:prod` (samma image)
- `worker:test` & `worker:prod` (samma image)

**Push location:**
- TEST-projekt: `europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/`
- PROD-projekt: `europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/`

**Steg i build.yml:**
```yaml
1. Checkout code
2. Setup Google Cloud SDK
3. Authenticate with GCP_SA_KEY_TEST (för TEST branch)
   eller GCP_SA_KEY_PROD (för main branch)
4. Build 3 Docker images (api, frontend, worker)
5. Push images till rätt Artifact Registry
6. Tag images: {image-name}:latest, {image-name}:{git-sha}
7. Update deployment manifests med nya SHA
```

#### 2️⃣ test-deploy.yml - Deploy to TEST
**Triggers:** Automatic efter build.yml + Push to `re_deploy_start`

**Environment:**
- GCP Project: `strawbayscannertest`
- Cloud Run services:
  - `invoice-scanner-api-test`
  - `invoice-scanner-frontend-test`

**Environment variables från GCP Secret Manager (test secrets):**
```
DATABASE_HOST=invoice-scanner-test.c.strawbayscannertest.cloudsql.googleapis.com
DATABASE_NAME=invoice_scanner
DATABASE_USER=scanner_test
DATABASE_PASSWORD=(från secret_key_test)
DATABASE_PORT=5432

FLASK_SECRET_KEY=(från secret_key_test)
FLASK_ENV=test

EMAIL_SENDER=(från gmail_sender)
EMAIL_PASSWORD=(från gmail_password)

OPENAI_API_KEY=(från openai_api_key)

GCP_PROJECT=strawbayscannertest
GCP_REGION=europe-west1
```

**Steg i test-deploy.yml:**
```yaml
1. Checkout code
2. Setup Google Cloud SDK
3. Authenticate with GCP_SA_KEY_TEST
4. Fetch 6 secrets från GCP Secret Manager (test project)
5. Deploy API Cloud Run service:
   - Image: europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/api:latest
   - Environment variables (från steg 4)
   - Memory: 512MB
   - Concurrency: 80
   - Timeout: 1800 seconds
6. Deploy Frontend Cloud Run service:
   - Image: europe-west1-docker.pkg.dev/strawbayscannertest/invoice-scanner/frontend:latest
   - Memory: 256MB
   - Concurrency: 100
7. Run smoke tests (curl to API health check)
8. Output: TEST URLs (api-test-xxxxx.run.app, frontend-test-xxxxx.run.app)
```

#### 3️⃣ prod-deploy.yml - Deploy to PROD (with manual approval)
**Triggers:** Manual approval needed + Push to `main`

**Manual Approval Gate:**
- GitHub: Pull Request approval required before merge to `main`
- Eller: Manual trigger via GitHub Actions UI (Dispatch event)
- Timeout: 24 hours för approval

**Environment:**
- GCP Project: `strawbayscannerprod`
- Cloud Run services:
  - `invoice-scanner-api-prod`
  - `invoice-scanner-frontend-prod`

**Environment variables från GCP Secret Manager (prod secrets):**
```
DATABASE_HOST=invoice-scanner-prod.c.strawbayscannerprod.cloudsql.googleapis.com
DATABASE_NAME=invoice_scanner
DATABASE_USER=scanner_prod
DATABASE_PASSWORD=(från db_password_prod)
DATABASE_PORT=5432

FLASK_SECRET_KEY=(från secret_key_prod)
FLASK_ENV=production

EMAIL_SENDER=(från gmail_sender)
EMAIL_PASSWORD=(från gmail_password)

OPENAI_API_KEY=(från openai_api_key)

GCP_PROJECT=strawbayscannerprod
GCP_REGION=europe-west1
```

**Steg i prod-deploy.yml:**
```yaml
1. Require manual approval (GitHub Actions environment)
2. Checkout code
3. Setup Google Cloud SDK
4. Authenticate with GCP_SA_KEY_PROD
5. Fetch 6 secrets från GCP Secret Manager (prod project)
6. Deploy API Cloud Run service:
   - Image: europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/api:latest
   - Environment variables (från steg 5)
   - Memory: 512MB
   - Concurrency: 80
   - Timeout: 1800 seconds
7. Deploy Frontend Cloud Run service:
   - Image: europe-west1-docker.pkg.dev/strawbayscannerprod/invoice-scanner/frontend:latest
   - Memory: 256MB
   - Concurrency: 100
8. Run smoke tests (curl to API health check)
9. Verify database connectivity
10. Output: PROD URLs (api-prod-xxxxx.run.app, frontend-prod-xxxxx.run.app)
```

### Docker Image Strategy

**Samma images, olika runtime environment:**
```
Build-tid (build.yml):
  ├─ api:latest (Python:3.11-slim + Flask)
  ├─ frontend:latest (Node:20-alpine + Vite build output)
  └─ worker:latest (Python:3.11-bullseye + OCR deps)
  
  └─ Tag och push till BÅDE TEST och PROD Artifact Registry

Runtime (test-deploy.yml / prod-deploy.yml):
  ├─ Samma api:latest image
  │  └─ Konfigureras via environment variables
  │     └─ DATABASE_HOST -> appoints till test eller prod Cloud SQL
  │     └─ FLASK_SECRET_KEY -> test eller prod secret
  │     └─ GCP_PROJECT -> strawbayscannertest eller strawbayscannerprod
  │
  └─ Samma frontend:latest image
     └─ API_URL environment variable pekar till test eller prod API
```

### Arkitektur-diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         GitHub                                   │
│  main (prod) ←─ Pull Request ← re_deploy_start (dev)            │
└────────────────────┬───────────────────────┬─────────────────────┘
                     │                       │
                     │ Push to main          │ Push to re_deploy_start
                     │                       │
         ┌───────────▼─────────┐   ┌────────▼──────────┐
         │   build.yml         │   │   build.yml       │
         │ (GCP_SA_KEY_PROD)   │   │ (GCP_SA_KEY_TEST) │
         │ Build & Push Images │   │ Build & Push Img  │
         └──────────┬──────────┘   └────────┬──────────┘
                    │                       │
         ┌──────────▼──────────┐   ┌────────▼──────────────┐
         │  Artifact Registry  │   │ Artifact Registry    │
         │   PROD Project      │   │  TEST Project        │
         │  (eu-west1 repo)    │   │  (eu-west1 repo)     │
         └──────────┬──────────┘   └────────┬──────────────┘
                    │                       │
                    │                       │
                    │                  ┌────▼────────────────┐
                    │                  │  test-deploy.yml    │
                    │                  │ (GCP_SA_KEY_TEST)   │
                    │                  │ Fetch secrets_test  │
                    │                  │ Deploy to TEST      │
                    │                  └────┬────────────────┘
                    │                       │
                    │                  ┌────▼──────────────┐
                    │                  │  TEST Cloud Run   │
                    │                  │  - api-test       │
                    │                  │  - frontend-test  │
                    │                  │ Smoke tests OK    │
                    │                  └───────────────────┘
                    │                       │
                    │ Manual Approval       │
                    │ (GitHub Environments) │
                    │  - Wait for approval  │
                    │  - 24h timeout        │
                    │ <CLICK "APPROVE">     │
                    │                       │
         ┌──────────▼──────────┐           │
         │  prod-deploy.yml    │◄──────────┘
         │ (GCP_SA_KEY_PROD)   │
         │ Fetch secrets_prod  │
         │ Deploy to PROD      │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  PROD Cloud Run     │
         │  - api-prod         │
         │  - frontend-prod    │
         │ Smoke tests OK      │
         └─────────────────────┘
```

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

**I prod-deploy.yml:**
```yaml
environment:
  name: production
  url: https://api-prod-xxxxx.run.app
```

---

### Complete CI/CD Flow Exempel

**Scenario: Utvecklare pushar feature**

```
1. Utvecklare: git push origin my-feature
2. GitHub: Öppnar PR mot re_deploy_start
3. GitHub: CI-checks kör linting, tester, etc
4. Utvecklare: Merge PR
5. GitHub: Detekterar push till re_deploy_start
6. build.yml: 
   - Använder GCP_SA_KEY_TEST
   - Bygger api:latest, frontend:latest, worker:latest
   - Pushar till strawbayscannertest Artifact Registry
7. test-deploy.yml (auto-trigger efter build):
   - Använder GCP_SA_KEY_TEST
   - Hämtar 6 secrets från TEST Secret Manager
   - Deployar till Cloud Run services
   - Kör smoke tests
8. Utvecklare testas på: api-test-xxxxx.run.app
```

**Scenario: Merge till main (PROD deployment)**

```
1. PR merged in GitHub → main
2. GitHub: Detekterar push till main
3. build.yml: 
   - Använder GCP_SA_KEY_PROD
   - Bygger och pushar till strawbayscannerprod Artifact Registry
4. prod-deploy.yml-job: PAUSES och väntar på approval
   - GitHub visar: "This job requires manual approval"
   - Timeout: 24 timmar
5. Rickard klickar "Approve" i GitHub Actions UI
6. prod-deploy.yml (resumed):
   - Använder GCP_SA_KEY_PROD
   - Hämtar 6 secrets från PROD Secret Manager
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

**build.yml** (Build & Push)
- Triggers: push to `re_deploy_start` or `main`
- Detects branch → chooses TEST or PROD GCP project
- Builds 3 Docker images (API, Frontend, Worker)
- Tags with `:latest` AND `:github.sha` (for rollback)
- Pushes to correct Artifact Registry
- Uses secrets: `GCP_SA_KEY_TEST` or `GCP_SA_KEY_PROD`

**test-deploy.yml** (Deploy to TEST)
- Triggers: automatically after build.yml (on re_deploy_start branch)
- Waits for manual approval: NO
- Project: strawbayscannertest
- Fetches 5 secrets from Secret Manager (test variants)
- Deploys API Cloud Run: 512Mi RAM, 1 CPU, max 10 instances
- Deploys Frontend Cloud Run: 256Mi RAM, 1 CPU, max 10 instances
- Runs smoke tests (health checks)
- Outputs: Service URLs for testing

**prod-deploy.yml** (Deploy to PROD with approval)
- Triggers: automatically after build.yml (on main branch)
- **Waits for manual approval: YES** (24h timeout)
- Project: strawbayscannerprod
- Fetches 5 secrets from Secret Manager (prod variants)
- Deploys API Cloud Run: 512Mi RAM, 1 CPU, min 1 instance, max 20 instances
- Deploys Frontend Cloud Run: 256Mi RAM, 1 CPU, min 1 instance, max 20 instances
- Runs smoke tests (health checks)
- Outputs: Service URLs (production live!)

**Status:** All 3 workflows created and ready to test

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

### FASE 4: GitHub Actions Workflows (0% done)
- [ ] `.github/workflows/build.yml` - Build & push images
- [ ] `.github/workflows/test-deploy.yml` - Deploy to TEST
- [ ] `.github/workflows/prod-deploy.yml` - Deploy to PROD with manual approval
- [ ] Testa alla workflows

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
