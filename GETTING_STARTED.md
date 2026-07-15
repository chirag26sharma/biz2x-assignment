# Getting Started — Biz2X Early Warning System

Step-by-step guide to run the project locally on **Windows**, **macOS**, or **Linux**.

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| Git | any | `git --version` |

Optional:
- **Docker Desktop** — for one-command full stack
- **LLM API token** — for live LLM explanations (fallback templates work without it)

---

## Option A — Local development (recommended for demo)

### Step 1: Clone the repository

```bash
git clone https://github.com/chirag26sharma/biz2x-assignment.git
cd biz2x-assignment
```

### Step 2: Start the backend (port **5001**)

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 5001
```

**macOS / Linux:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 5001
```

Verify backend:
- Health: [http://localhost:5001/health](http://localhost:5001/health)
- API docs: [http://localhost:5001/docs](http://localhost:5001/docs)

#### Optional: enable live LLM responses

Edit `backend/.env`:

```env
LLM_API_TOKEN=your_token_here
```

Without a token, explanation and Q&A use deterministic template fallbacks.

---

### Step 3: Start the frontend (port **3000**)

Open a **new terminal**:

```bash
cd frontend
npm install
```

Optional — create `frontend/.env.local` if backend is not on default port:

```env
NEXT_PUBLIC_API_BASE=http://localhost:5001
```

Start dev server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

### Step 4: Log in with a demo user

| User ID | Role | What to try |
|---------|------|-------------|
| **A001** | Analyst | Dashboard → B102 (High Risk) or B110 via A002 |
| **A002** | Analyst | B110 (Critical multi-signal) |
| **M001** | Manager | Full portfolio view |
| **U_B101** | Borrower | Plain-language account update (no LLM) |

Click a user card on the home page — JWT login happens automatically.

---

## Option B — Docker (full stack)

From the repo root:

```bash
docker compose up --build
```

- Backend: [http://localhost:5001](http://localhost:5001)
- Frontend: [http://localhost:3000](http://localhost:3000)

Set `LLM_API_TOKEN` in `backend/.env` before running compose if you want live LLM output.

---

## Running tests

### Backend (32 unit/integration tests)

```bash
cd backend
pip install -r requirements.txt
pytest tests -v
```

### Frontend E2E (Playwright)

**Requires backend and frontend running** (see Option A).

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

---

## Common issues

| Problem | Fix |
|---------|-----|
| `Could not reach API` on login page | Start backend on port **5001**; check `NEXT_PUBLIC_API_BASE` |
| Port 5001 already in use | Stop other uvicorn processes or change port in both `.env.local` and uvicorn command |
| LLM shows template fallback | Set `LLM_API_TOKEN` in `backend/.env` and restart backend |
| Session expired after restart | Log in again (JWT issued on login) |
| Playwright tests fail | Ensure backend + frontend are both running before `npm run test:e2e` |

---

## Project ports (default)

| Service | Port | URL |
|---------|------|-----|
| Backend API | 5001 | http://localhost:5001 |
| Frontend UI | 3000 | http://localhost:3000 |
| API OpenAPI | 5001 | http://localhost:5001/docs |

---

## Next steps

- [DEMO.md](DEMO.md) — 5-minute interview walkthrough
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design
- [backend/README.md](backend/README.md) — API, assumptions, security
