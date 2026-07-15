# Biz2X Early Warning frontend

Next.js (TypeScript) UI for the Loan Default Risk Early Warning System.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env.local   # optional — defaults to http://localhost:5001
npm run dev
```

Open `http://localhost:3000` and pick a demo user.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:5001` | FastAPI backend URL |

## Routes

| Path | Audience | Purpose |
|------|----------|---------|
| `/` | Public | Demo login picker (calls `POST /api/auth/login`) |
| `/dashboard` | Analyst / manager | Alerts table + portfolio summary |
| `/borrower` | Borrower | Deterministic account update (no LLM) |
| `/borrowers/[id]` | Analyst / manager | Assessment, streaming LLM explanation, Q&A, scenario |

Protected routes use Next.js `middleware.ts` (session cookie) plus client-side role redirects.

## Docker

From repo root:

```bash
docker compose up --build
```

See `../backend/README.md` for full system documentation, assumptions, test scenarios, and demo script.
