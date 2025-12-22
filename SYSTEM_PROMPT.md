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

**CI/CD Pipeline:**
```
Push to branch (main/test)
  ↓ Build Docker images
  ↓ Push to Artifact Registry
  ↓ Run tests (lint, security scan)
  ↓ Deploy to TEST environment (Cloud Run)
  ↓ Manual approval needed
  ↓ Deploy to PROD environment (Cloud Run)
  ↓ Smoke tests & verification
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
