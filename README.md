# Invoice Scanner

En automatiserad fakturascannings- och analyslösning med React frontend och Flask backend.

## Funktioner

- 📤 **Dra och släpp** filuppladdning för fakturor (PDF, JPG, PNG)
- 📊 **Dokumenthantering** - Visa, redigera och spåra skannade fakturor
- 🔐 **Användarautentisering** och företagsroller
- 💳 **Abonnement och fakturering** för olika plantyper
- 👨‍💼 **Admin panel** för företagsadministration
- 📝 **Fakturautomatisering** - Extrahera och analysera fakturordata

## Starta hela stacken

1. Bygg och starta både backend och frontend:

```bash
cd /Users/rickardelmqvist/Development/invoice.scanner
docker compose up --build
```

2. Frontend nås på:
   - http://localhost:5173

3. Backend API nås på:
   - http://localhost:8000

## Arkitektur

- **Frontend**: React med Vite, körs i Docker på port 5173
- **Backend**: Flask, PostgreSQL, körs i Docker på port 8000
- **Databas**: PostgreSQL för lagrande av användare, företag, fakturor och dokumentstatus

## Projektstruktur

```
invoice.scanner/
├── invoice.scanner.api/          # Flask backend
│   ├── main.py                   # Huvudapplikation
│   ├── db_config.py              # Databaskonfiguration
│   ├── db_utils.py               # Databasverktyg
│   ├── defines.py                # Globala konstanter
│   ├── documents/                # Dokumentlagring
│   │   ├── raw/                  # Orörda originalfiler
│   │   └── processed/            # Bearbetade filer
│   ├── lib/                      # Bibliotek
│   │   ├── email_service.py      # Mejlhantering
│   │   └── llm/                  # LLM-integration
│   └── requirements.txt          # Python-beroenden
│
└── invoice.scanner.frontend.react/  # React frontend
    ├── src/
    │   ├── components/           # React-komponenter
    │   │   ├── Dashboard.jsx     # Huvudinstrumentpanel
    │   │   ├── ScanInvoice.jsx   # Filuppladdning
    │   │   ├── DocumentDetail.jsx # Fakturaredaktör
    │   │   ├── Admin.jsx         # Admin panel
    │   │   └── ...
    │   ├── contexts/             # React Context
    │   └── App.jsx               # Huvudapp
    └── package.json
```

## API-endpoints

### Dokumenthantering
- `POST /auth/documents/upload` - Ladda upp nytt dokument
- `GET /auth/documents` - Hämta alla dokument för företag
- `PUT /auth/documents/<id>` - Uppdatera fakturadata

## Vanliga kommandon

```bash
# Starta stacken
docker compose up --build

# Stoppa stacken
docker compose down

# Se loggar
docker compose logs -f

# Starta bara backend
docker compose up backend

# Starta bara frontend
docker compose up frontend
```

## Miljövariabler

Backend kräver `.env`-fil i `invoice.scanner.api/.env`:
```
DATABASE_URL=postgresql://user:password@db:5432/invoice_scanner
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
# ...
```

## Utveckling

### Backend
```bash
cd invoice.scanner.api
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd invoice.scanner.frontend.react
npm install
npm run dev
```

---

**Senast uppdaterad**: 20 december 2025
