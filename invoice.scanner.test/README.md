# Invoice Scanner Test Container

VSCode Dev Container for testing Cloud Functions (`cf_preprocess_document`) locally with debugging support.

---

## Quick Start

### Prerequisites
- VSCode with "Dev Containers" extension installed
- Docker Desktop running
- Local docker-compose stack running: `./dev-start.sh` (from project root)

### Open in VSCode Dev Container

1. **Open VSCode in the project root:**
   ```bash
   code /path/to/invoice.scanner
   ```

2. **Open Dev Container:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type: `Dev Containers: Open in Container`
   - Select `invoice.scanner.test`

3. **Wait for setup:**
   - Container builds (first time: ~2-3 minutes)
   - Dependencies install automatically
   - VSCode reopens inside the container ✅

---

## Running Tests

### Via VSCode Debug UI (Recommended)

1. **Open test file:**
   - Navigate to `tests/test_cf_preprocess.py`

2. **Set breakpoints:**
   - Click on line numbers to add breakpoints
   - Can breakpoint in test file AND in `main.py` (Cloud Functions)

3. **Start debugging:**
   - Press `F5` or `Run → Start Debugging`
   - Choose:
     - `Python: Debug test_cf_preprocess` (normal)
     - `Python: Debug with breakpoints` (pause at first line)

4. **Step through code:**
   - `F10` = Step over
   - `F11` = Step into (enter function)
   - `Shift+F11` = Step out
   - `F5` = Continue to next breakpoint

### Via Terminal

```bash
# Inside container terminal:
python tests/test_cf_preprocess.py

# With verbose output:
python -v tests/test_cf_preprocess.py

# Run pytest if available:
pytest tests/test_cf_preprocess.py -v
```

---

## Debugging Features

### Breakpoints in Multiple Files

You can set breakpoints in:
- ✅ `invoice.scanner.test/tests/test_cf_preprocess.py`
- ✅ `invoice.scanner.cloud.functions/main.py` (all functions)
- ✅ `invoice.scanner.api/main.py` (if needed)

The debugger will stop at any breakpoint and allow stepping through all code.

### Example Debugging Session

```
test_cf_preprocess.py:120
    cf_preprocess_document(cloud_event)  ← BREAKPOINT HERE
                          ↓ (F11 to step in)
main.py:321 (cf_preprocess_document)
    update_document_status(...)  ← ANOTHER BREAKPOINT
                          ↓ (F11 to step in)
main.py:253 (update_document_status)
    get_db_connection()
    cursor.execute(...)              ← Inspect variables here
```

### Watch Variables

In the Debug panel (left sidebar):
- **Variables**: Local and global scope
- **Watch**: Add custom expressions
- **Call Stack**: See function call chain

---

## Environment Configuration

The Dev Container automatically sets:
```
DATABASE_HOST=db                      ← Docker network hostname
DATABASE_PORT=5432
DATABASE_USER=scanner_local
DATABASE_PASSWORD=scanner_local
DATABASE_NAME=invoice_scanner
PYTHONPATH=/workspace:...             ← Includes cloud.functions & api
```

These connect to the `db` service from your docker-compose stack.

---

## Database Connection Setup

### Prerequisites
The dev container must be connected to the same Docker network as your docker-compose services.

### Initial Setup (First Time Only)

1. **Start your docker-compose services** (from host machine):
   ```bash
   cd /path/to/invoice.scanner
   docker-compose up -d
   ```

2. **Get your dev container ID** (from VSCode terminal):
   ```bash
   hostname
   # Returns something like: a1b2c3d4e5f6
   ```

3. **Connect dev container to docker network** (from host machine):
   ```bash
   docker network connect invoicescanner_invoice.scanner <CONTAINER_ID>
   ```
   Replace `<CONTAINER_ID>` with the output from step 2.

4. **Verify connection** (from VSCode terminal):
   ```bash
   python test_db_conn.py
   ```
   You should see: `✓ Successfully connected with pg8000!`

### Testing Database Connection

Use the provided test script to verify connectivity:
```bash
python test_db_conn.py
```

This script will:
- Try to connect via pg8000
- Try to connect via psycopg2
- Test socket connectivity if drivers fail
- Show detailed error messages if connection fails

### Querying the Database

Once connected, you can query directly from the terminal:
```bash
# Inside container terminal:
psql -h db -U scanner_local -d invoice_scanner

# Now you can run SQL queries:
invoice_scanner=# SELECT COUNT(*) FROM documents;
invoice_scanner=# SELECT id, email FROM users LIMIT 5;
```

### Common Connection Issues

| Problem | Solution |
|---------|----------|
| `Can't create a connection to host db` | Dev container not on same network. Run step 3 above. |
| `Name or service not known` | Same as above - network connection needed. |
| `psycopg2 not found` | Library not installed. Run `pip install psycopg2-binary`. |
| `connection refused` | docker-compose services not running. Run `docker-compose up -d`. |

---

## Linked Directories (Mounts)

The container has bind mounts to the following directories on your host:

### Mounted Directories

| Host Location | Container Path | Purpose |
|---|---|---|
| `../invoice.scanner.cloud.functions` | `/mounts/invoice.scanner.cloud.functions` | Cloud Functions code |
| `../invoice.scanner.api` | `/mounts/invoice.scanner.api` | API server code |
| `./` | `/workspace` | Test container code |

### Live File Synchronization

With **bind mounts**, file changes are reflected **immediately at runtime**:
- ✅ Edit files on your **host** → Changes visible in **container** instantly
- ✅ Code running in **container** modifies files → Changes visible on **host** instantly
- ✅ No rebuild or restart needed (ideal for development)

### Accessing Mounted Code

You can import from the mounted directories:
```python
from main import cf_preprocess_document  # From cloud.functions mount
from main import get_db_connection       # From cloud.functions mount
```

Or access them directly:
```python
import sys
sys.path.insert(0, '/mounts/invoice.scanner.cloud.functions')
from main import some_function
```

### Verifying Mounts

To check if mounts are accessible inside the container:
```bash
# Inside container terminal:
python test_mounts.py
```

This will list the contents of all mounted directories and confirm they're accessible.

---

## Troubleshooting

### Container won't build
```bash
# Rebuild from scratch:
# VSCode: Dev Containers: Rebuild Container
# Or manually:
docker-compose down -v
```

### Database connection errors
- Ensure `./dev-start.sh` is running (docker-compose services active)
- Check: `docker-compose ps` shows `db` container running
- Verify: `docker-compose logs db` shows no errors

### Python imports not found
- Restart VSCode: `Ctrl+Shift+P` → `Developer: Reload Window`
- Or rebuild container

### Debugger not stopping at breakpoints
- Set breakpoint BEFORE starting debugging
- Or use `Python: Debug with breakpoints` configuration to pause at first line

---

## Extended Development

### Add more tests
```bash
# Inside container:
touch tests/test_next_function.py
# Edit and debug
```

### Install additional packages
```bash
# Edit requirements.txt (add dependency)
# Then rebuild container:
# VSCode: Dev Containers: Rebuild Container
```

### Analyze database
```bash
# Inside container terminal:
psql -h db -U scanner_local -d invoice_scanner
# Now you can query: SELECT * FROM documents;
```

---

## Architecture

```
┌─ Your Computer ───────────────────┐
│                                   │
│  VSCode (running inside container)│
│  ├─ Edit code                     │
│  ├─ Set breakpoints               │
│  ├─ Run tests with debugging      │
│  └─ Step through code             │
│                                   │
│  ┌─ Docker Container ────────┐    │
│  │ Python 3.11              │    │
│  │ All dependencies          │    │
│  │ test_cf_preprocess.py ✅  │    │
│  │ main.py (linked) ✅       │    │
│  │ debugpy (debugger) ✅     │    │
│  └──────────────────────────┘    │
│                                   │
│  ┌─ Docker Network ──────────┐    │
│  │ db (PostgreSQL)           │    │
│  │ api (Flask)               │    │
│  │ frontend (React)          │    │
│  └──────────────────────────┘    │
└───────────────────────────────────┘
```

---

## Files Structure

```
invoice.scanner.test/
├── .devcontainer/
│   ├── Dockerfile              ← Test container image
│   ├── devcontainer.json       ← VSCode config
│   └── launch.json             ← Debugger config
├── requirements.txt            ← Combined dependencies
├── README.md                   ← This file
└── tests/
    └── test_cf_preprocess.py   ← Your test file
```

---

## Resources

- [VSCode Dev Containers Docs](https://code.visualstudio.com/docs/devcontainers/containers)
- [Python Debugging in VSCode](https://code.visualstudio.com/docs/python/debugging)
- [Docker Development Best Practices](https://docs.docker.com/develop/dev-best-practices/)
