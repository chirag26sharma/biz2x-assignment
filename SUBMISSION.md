# Submission Checklist — Biz2X SSE Assignment

Use this before submitting your assignment to Biz2X.

## Repository

- [ ] GitHub repo is public/accessible: [chirag26sharma/biz2x-assignment](https://github.com/chirag26sharma/biz2x-assignment)
- [ ] Root `README.md` present with quick start
- [ ] `frontend/` contains full source (not empty submodule)
- [ ] No secrets committed (`.env` gitignored; only `.env.example`)

## Runnable demo

- [ ] `cd backend && uvicorn app.main:app --port 5001` starts without errors
- [ ] `cd frontend && npm run dev` starts without errors
- [ ] Login as A001 → dashboard loads alerts
- [ ] Login as U_B101 → borrower view loads
- [ ] B110 shows assessment + DPD chart + payment table

## Tests

- [ ] `cd backend && pytest tests -v` — **46 passed**
- [ ] `cd frontend && npm run test:e2e` — **4 passed** (with both servers running)

## Documentation

- [ ] [GETTING_STARTED.md](GETTING_STARTED.md) — setup guide
- [ ] [ARCHITECTURE.md](ARCHITECTURE.md) — system design
- [ ] [DEMO.md](DEMO.md) — interview walkthrough
- [ ] [backend/README.md](backend/README.md) — API + assumptions

## Case study requirements

- [ ] Deterministic risk scoring (LLM never sets category/severity/action)
- [ ] LLM used only for analyst explanation + grounded Q&A
- [ ] RBAC: borrower / analyst / manager
- [ ] Edge cases: B108 (missing data), B109 (insufficient history)
- [ ] Documented thresholds in `config.py` + README
- [ ] Bonus: portfolio summary, scenario simulation, DPD trend chart

## Optional polish

- [ ] `LLM_API_TOKEN` set for live LLM demo
- [ ] 3–5 min screen recording linked in submission email
- [ ] Docker: `docker compose up --build` verified

## Suggested submission email snippet

```
Subject: Biz2X SSE Assignment — Loan Default Risk Early Warning System

Hi,

Please find my submission:
Repo: https://github.com/chirag26sharma/biz2x-assignment

Quick start: see GETTING_STARTED.md
Demo script: see DEMO.md

Stack: FastAPI + Next.js TypeScript
Tests: 32 backend pytest + 4 Playwright E2E

Demo users: A001 (analyst), A002 (analyst), U_B101 (borrower)
Showcase: B110 (Critical) vs B101 (Low)

Thank you,
[Your name]
```
