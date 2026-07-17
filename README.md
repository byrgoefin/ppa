# Elite Dangerous Power Play Analyzer

A web application that ingests Elite Dangerous faction and Power Play data,
visualises a faction's territory in three views (table, 2D map, 3D map), and
produces AI-assisted fortify/expand recommendations backed by rule-based scoring.

## Stack

- **Backend** — Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend** — React 18, TypeScript, Vite 5, D3.js, react-three-fiber (Three.js)
- **Ingestion** — Spansh `factions.json.gz` (streaming via `ijson`) + EDSM API
- **Auth** — Admin-only JWT (HS256, 8-hour expiry); read views are public

---

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the project directory
cd elite-powerplay-app

# 2. Copy the example env file and fill in your values
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY, and optionally AI_API_KEY

# 3. Start all services
docker compose up --build

# 4. Open the app
open http://localhost:3000
```

The backend creates all database tables automatically on first startup.

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit DATABASE_URL and SECRET_KEY
uvicorn main:app --reload
```

API available at <http://localhost:8000>  
Interactive docs at <http://localhost:8000/docs>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at <http://localhost:5173> (proxies `/api` → `http://localhost:8000`)

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection URL |
| `POSTGRES_PASSWORD` | Yes | `pp_password` | PG password (used by docker-compose) |
| `SECRET_KEY` | Yes | dev key | JWT signing secret |
| `LLM_ENABLED` | No | `false` | Enable LLM recommendation summaries |
| `AI_PROVIDER` | No | `openai` | `openai` or `custom` |
| `AI_API_KEY` | If LLM enabled | — | Provider API key |
| `SPANSH_INGEST_INTERVAL_HOURS` | No | `24` | Spansh ingest schedule |
| `EDSM_SYNC_INTERVAL_HOURS` | No | `6` | EDSM sync schedule |

---

## Sub-Task Status

| # | Description | Status |
|---|---|---|
| 1 | Project Scaffold & Database Schema | ✅ Done |
| 2 | Spansh Data Ingestion Service | ⬜ Pending |
| 3 | EDSM Power Play Sync Service | ⬜ Pending |
| 4 | Factions & Systems API Endpoints | ⬜ Pending |
| 5 | Recommendation Engine (Rule-Based) | ⬜ Pending |
| 6 | LLM Summary Integration | ⬜ Pending |
| 7 | Frontend: Selectors & Table View | ⬜ Pending |
| 8 | Frontend: 2D Map View | ⬜ Pending |
| 9 | Frontend: 3D Map View | ⬜ Pending |
| 10 | Admin Panel & Ingestion Status UI | ⬜ Pending |

---

## Creating the first admin user

After the backend starts, you can create an admin user directly via the Python REPL or a migration script:

```python
from db.session import SessionLocal
from models.models import AdminUser
from routers.auth import hash_password

db = SessionLocal()
user = AdminUser(email="admin@example.com", hashed_password=hash_password("yourpassword"))
db.add(user)
db.commit()
db.close()
```
