# SRM AI SETU

A full-stack CRM system with AI capabilities built with FastAPI + PostgreSQL.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| PostgreSQL | 14+ |
| Git | any |

---

## Setup (First Time)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "SRM AI SETU"
```

### 2. Create & activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Set up PostgreSQL

1. Open **pgAdmin** or **psql** and create a new database:
   ```sql
   CREATE DATABASE crm_ai_setu;
   ```
2. Make sure your PostgreSQL service is running (default port **5432**).

### 5. Configure environment variables

```bash
# Copy the template
copy backend\.env.example backend\.env      # Windows
# cp backend/.env.example backend/.env     # macOS/Linux
```

Open `backend/.env` and fill in your values:

```env
PROJECT_NAME="SRM AI SETU"
DATABASE_URL="postgresql://AI%20SETU:0412@localhost:5432/crm_ai_setu"
SECRET_KEY="your_long_random_secret_key_here"
```

> **To generate a secure SECRET_KEY:**
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### 6. Run database migrations

```bash
cd backend
alembic upgrade head
cd ..
```

### 7. Start the server

```bash
python app.py
```

If you run from VS Code, prefer the launch profile named SRM Server (Stable Uvicorn).
It runs the backend directly with Uvicorn in an integrated terminal and is more stable
than running arbitrary current-file launches from the top-right Run button.

The app will be available at:
- **Frontend UI:** http://127.0.0.1:8000/frontend/template/index.html
- **API Docs:** http://127.0.0.1:8000/docs

---

## Production / Live Deployment

Do not use the VS Code Run button for live hosting. Use a process manager/service
so the app auto-recovers and stays online.

Windows (PowerShell example):

```powershell
$env:SRM_HOST="0.0.0.0"
$env:SRM_PORT="8000"
e:/CRM AI SETU/.venv/Scripts/python.exe e:/CRM AI SETU/app.py
```

Linux (systemd/supervisor/docker recommended):

```bash
SRM_HOST=0.0.0.0 SRM_PORT=8000 python app.py
```

If port 8000 is occupied, launcher will automatically move to the next free port.
To pin strictly to one port in live environments, ensure your process manager starts
only one instance and reserve the port for that service.

---

## Common Errors

| Error | Fix |
|-------|-----|
| `connection refused` on port 5432 | PostgreSQL is not running — start the service |
| `password authentication failed` | Wrong password in `DATABASE_URL` inside `.env` |
| `database "crm_ai_setu" does not exist` | Run `CREATE DATABASE crm_ai_setu;` in psql/pgAdmin |
| `ModuleNotFoundError` | Run `pip install -r backend/requirements.txt` in your venv |

---

## Project Structure

```
SRM AI SETU/
├── app.py               # Entry point — runs the server
├── backend/
│   ├── .env             # Your local config (NOT committed to git)
│   ├── .env.example     # Template — copy this to .env
│   ├── requirements.txt
│   ├── alembic/         # Database migrations
│   └── app/             # FastAPI application
├── frontend/
│   ├── template/        # HTML pages
│   └── js/              # JavaScript files
└── README.md
```

<!-- do not forget to create this for google meet or env file -->
credentials.json.sample