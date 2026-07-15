# Biz2X — Loan Default Risk Early Warning System

Proactive early-warning prototype for the Biz2X SSE case study: flag borrowers likely to become delinquent within **30 days**, surface explainable alerts, and ground analyst Q&A in borrower data.

## Repository layout

```text
biz2x-assignment/
├── backend/          FastAPI API, risk engine, JWT auth, LLM integration
├── frontend/         Next.js (TypeScript) analyst & borrower UI
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Critical design rule

**Risk category, severity, and recommended action are never produced by the LLM.**  
The rule engine scores deterministically; the LLM only narrates results and answers grounded analyst questions.

## Quick start

### 1. Backend (port 5001)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Optional: set LLM_API_TOKEN in .env
uvicorn app.main:app --reload --port 5001
```

### 2. Frontend (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and pick a demo user.

### 3. Docker (full stack)

```bash
docker compose up --build
```

## Demo users

| Login ID | Role | Access |
|----------|------|--------|
| A001 | Analyst | B101, B102, B103, B107, B109 |
| A002 | Analyst | B104–B106, B108, B110 |
| M001 | Manager | Full portfolio |
| U_B101 … U_B110 | Borrower | Own account only |

**Showcase borrowers:** B101 (healthy Low) · B110 (Critical multi-signal) · B108/B109 (edge cases)

## Tests

```bash
cd backend
pytest tests -v
```

32 automated tests cover risk scoring, RBAC, JWT auth, security controls, and production config validation.

## Documentation

| Doc | Contents |
|-----|----------|
| [backend/README.md](backend/README.md) | Architecture, API, assumptions, security, demo script |
| [frontend/README.md](frontend/README.md) | Routes, env vars, UI overview |

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Pydantic, PyJWT |
| Frontend | Next.js 16, TypeScript, Tailwind |
| Scoring | Deterministic rule engine |
| LLM | Anthropic wrapper (explanation + Q&A only) |
| Storage | JSON file (`StorageBackend` abstraction) |
