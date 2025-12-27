# Invoice Scanner

Document processing system with Cloud Functions architecture.

## 🚀 Quick Start

### Start Local Development
```bash
./dev-start.sh
```

This starts everything needed:
- 4 Docker services (API, Frontend with Vite hot-reload, Database, Redis)
- Cloud Functions Framework in new Terminal (:9000)

### Services & URLs
- **API:** http://localhost:5001
- **Frontend:** http://localhost:8080 (Vite dev-server with hot-reload)
- **Database:** localhost:5432
- **Redis:** localhost:6379
- **Cloud Functions Framework:** http://localhost:9000 (in separate Terminal)

## 📋 Architecture

**Unified Cloud Functions approach:**
- Same code runs locally (functions-framework) and in GCP (Cloud Functions)
- 5-stage processing pipeline (preprocess → OCR → LLM → extraction → evaluation)
- Pub/Sub message chaining for orchestration
- Cloud SQL for persistence
- GCS for document storage (cloud only)

See [SYSTEM_PROMPT.md](SYSTEM_PROMPT.md) for detailed architecture documentation.

## 📁 Project Structure

```
invoice.scanner/
├── dev-start.sh                           # ⭐ START HERE (starts docker + Cloud Functions)
├── docker-compose.yml                     # Local infrastructure (4 services)
├── invoice.scanner.api/                   # Flask REST API
├── invoice.scanner.frontend.react/        # React UI
├── invoice.scanner.db/                    # Database initialization
├── invoice.scanner.cloud.functions/       # 5 Cloud Functions
│   ├── main.py                            # Function implementations
│   ├── local_server.sh                    # Run locally (:9000)
│   ├── deploy.sh                          # Deploy to GCP
│   └── requirements.txt                   # Dependencies
└── SYSTEM_PROMPT.md                       # Full documentation
```

## 🧪 Testing

### Local
```bash
./dev-start.sh
```

This opens 2 things:
- Docker services in background (API, Frontend, Database, Redis)
- New Terminal window with Cloud Functions Framework logs

### Upload & Process Document
```bash
# 1. Login
curl -X POST http://localhost:5001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "user@example.com", "password": "password"}' \
    -c /tmp/cookies.txt

# 2. Upload
curl -X POST http://localhost:5001/auth/documents/upload \
    -b /tmp/cookies.txt \
    -F "file=@/path/to/document.pdf"

# 3. Check Status
curl -X GET http://localhost:5001/auth/documents/{doc_id}/status \
    -b /tmp/cookies.txt
```

## ☁️ Deploy to GCP

### TEST Environment
```bash
cd invoice.scanner.cloud.functions
./deploy.sh strawbayscannertest europe-west1
```

### PRODUCTION
```bash
cd invoice.scanner.cloud.functions
./deploy.sh strawbayscannerprod europe-west1
```

## 📚 Documentation

- [SYSTEM_PROMPT.md](SYSTEM_PROMPT.md) - Full architecture & guidelines
- [invoice.scanner.cloud.functions/README.md](invoice.scanner.cloud.functions/README.md) - Cloud Functions details

## 🔧 Development

### Requirements
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend development)
- GCP credentials (for cloud deployment)

### Key Files
- `invoice.scanner.api/main.py` - API entry point
- `invoice.scanner.api/lib/processing_backend.py` - Processing abstraction
- `invoice.scanner.cloud.functions/main.py` - Cloud Functions implementations
- `docker-compose.yml` - Local infrastructure

### Environment Variables
See `.env` files in respective service folders. For GCP, use Secret Manager.

## 📝 Notes

- All changes to docker-compose.yml, GitHub Actions, or config must be approved first
- Same code runs locally and in GCP (environment-aware)
- Database: Cloud SQL (local via docker, cloud via Private IP)
- Storage: Local volumes (dev) or GCS (cloud)

## 🤝 Contributing

1. Test locally: `./dev-server.sh`
2. Verify functionality before pushing
3. Document changes in commit messages
4. Follow existing code patterns
