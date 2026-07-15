# Biz2X Early Warning — Frontend

Next.js (TypeScript) UI for the Loan Default Risk Early Warning System.

> **New to the project?** Start with [../GETTING_STARTED.md](../GETTING_STARTED.md)

## Run locally

```bash
cd frontend
npm install
cp .env.example .env.local   # optional — defaults to http://localhost:5001
npm run dev
```

Requires backend running on port **5001**. Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:5001` | FastAPI backend URL |

## Routes

| Path | Audience | Purpose |
|------|----------|---------|
| `/` | Public | Demo login picker (JWT via `POST /api/auth/login`) |
| `/dashboard` | Analyst / manager | Alerts table + portfolio summary |
| `/borrower` | Borrower | Deterministic account update (no LLM) |
| `/borrowers/[id]` | Analyst / manager | Assessment, DPD chart, LLM stream, Q&A, scenario |

Protected routes: `middleware.ts` (cookie) + client-side role redirects.

## Components

| Component | Purpose |
|-----------|---------|
| `AuthProvider` | JWT session in localStorage + cookie |
| `ExplanationStreamPanel` | Auto-streaming analyst LLM explanation |
| `DpdTrendChart` | DPD bar chart across recent EMI cycles |
| `PaymentHistoryTable` | Formatted payment + utilization table |
| `LlmStreamOutput` | Markdown rendering for LLM streams |

## Tests

```bash
# E2E (backend + frontend must be running)
npm run test:e2e

# Interactive debug
npm run test:e2e:ui
```

## Docker

From repo root: `docker compose up --build`

See [../backend/README.md](../backend/README.md) for API, assumptions, and security.
