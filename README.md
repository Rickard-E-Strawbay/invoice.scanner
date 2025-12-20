# Invoice Scanner

An automated invoice scanning and analysis solution with React frontend and Flask backend.

## Features

- 📤 **Drag and drop** file upload for invoices (PDF, JPG, PNG)
- 📊 **Document management** - View, edit, and track scanned invoices
- 🔐 **User authentication** and company roles
- 💳 **Subscriptions and billing** for different plan types
- 👨‍💼 **Admin panel** for company administration
- 📝 **Invoice automation** - Extract and analyze invoice data

## Start the full stack

1. Build and start both backend and frontend:

```bash
cd /Users/rickardelmqvist/Development/invoice.scanner
docker compose up --build
```

2. Frontend is accessible at:
   - http://localhost:5173

3. Backend API is accessible at:
   - http://localhost:8000

## Architecture

- **Frontend**: React with Vite, runs in Docker on port 5173
- **Backend**: Flask, PostgreSQL, runs in Docker on port 8000
- **Database**: PostgreSQL for storing users, companies, invoices, and document statuses

## Project Structure

```
invoice.scanner/
├── invoice.scanner.api/          # Flask backend
│   ├── main.py                   # Main application
│   ├── db_config.py              # Database configuration
│   ├── db_utils.py               # Database utilities
│   ├── defines.py                # Global constants
│   ├── documents/                # Document storage
│   │   ├── raw/                  # Original unmodified files
│   │   └── processed/            # Processed files
│   ├── lib/                      # Libraries
│   │   ├── email_service.py      # Email handling
│   │   └── llm/                  # LLM integration
│   └── requirements.txt          # Python dependencies
│
└── invoice.scanner.frontend.react/  # React frontend
    ├── src/
    │   ├── components/           # React components
    │   │   ├── Dashboard.jsx     # Main dashboard
    │   │   ├── ScanInvoice.jsx   # File upload
    │   │   ├── DocumentDetail.jsx # Invoice editor
    │   │   ├── Admin.jsx         # Admin panel
    │   │   └── ...
    │   ├── contexts/             # React Context
    │   └── App.jsx               # Main app
    └── package.json
```

## API Endpoints

### Document Management
- `POST /auth/documents/upload` - Upload new document
- `GET /auth/documents` - Get all documents for company
- `PUT /auth/documents/<id>` - Update invoice data

## Common Commands

```bash
# Start the stack
docker compose up --build

# Stop the stack
docker compose down

# View logs
docker compose logs -f

# Start only backend
docker compose up backend

# Start only frontend
docker compose up frontend
```

## Environment Variables

Backend requires `.env` file in `invoice.scanner.api/.env`:
```
DATABASE_URL=postgresql://user:password@db:5432/invoice_scanner
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
# ...
```

## Development

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

**Last updated**: December 20, 2025
