# Loan Default Risk Early Warning System

> **How to run:** see [../GETTING_STARTED.md](../GETTING_STARTED.md) in the repo root.

Biz2X SSE case study prototype: detect borrowers likely to become delinquent within **30 days**, surface explainable alerts, and ground analyst Q&A in borrower data only.

## Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI |
| Frontend | Next.js (TypeScript) + Tailwind |
| Scoring | Deterministic rule engine (`app/services/risk_engine.py`) |
| LLM | Anthropic wrapper at `https://llm-wrapper-741152993481.asia-south1.run.app` — **explanation + Q&A only** |
| Storage | JSON file via `StorageBackend` abstraction (DB stub ready) |

## Critical design rule

**Risk category, severity, and recommended action are never produced by the LLM.**  
The LLM only:

1. Narrates an already-computed assessment  
2. Answers analyst questions grounded strictly in that borrower’s data  

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# set LLM_API_TOKEN in .env if you want live LLM responses
uvicorn app.main:app --reload --port 5001
```

Health: `GET http://localhost:5001/health`

### Frontend

```bash
cd frontend
npm install
# optional: cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000` and pick a demo user.

### Docker (full stack)

From the repo root:

```bash
docker compose up --build
```

Backend: `http://localhost:5001` · Frontend: `http://localhost:3000`

### Automated tests

```bash
cd backend
pip install -r requirements.txt
pytest tests -v
```

## Simulated authentication & RBAC

Login via `POST /api/auth/login` with `{ "user_id": "A001" }` returns a signed JWT.  
Send `Authorization: Bearer <token>`.

| Role | Access |
|------|--------|
| `borrower` | Own assessment, profile (redacted), and **deterministic** `/borrower-update` only — no LLM |
| `analyst` | Assigned borrowers + LLM explanation, Q&A, scenario simulation |
| `manager` | Full portfolio (bonus summary view) + same analyst LLM features |

Analyst-only endpoints use `require_analyst_or_manager` (`app/auth/dependencies.py`).

### Production-oriented note (assignment §5)

In a real LMS deployment this prototype’s header token would be replaced by:

- IdP SSO / bank IAM with short-lived JWTs  
- Row-level security on borrower tables keyed by `subject_id` / analyst assignment  
- Audit logs for every access to risk explanations and Q&A  
- Field-level redaction (borrowers never see analyst notes / internal scenario tags)  
- Secrets (LLM tokens, DB) only in vault / KMS, never in client bundles  

## System flow

```
mock_dataset.json
      │
      ▼
 StorageBackend (file today / DB later)
      │
      ▼
 Risk engine (signals → score → category → severity → action)
      │
      ├─► Alerts API / Dashboard
      ├─► Borrower template (deterministic, no LLM)
      ├─► Explanation service ──► LLM wrapper (analyst narration only)
      └─► Analyst Q&A ──────────► LLM wrapper (grounded context only)
```

## Sample data schema

See `data/mock_dataset.json`.

```text
users[]: { user_id, name, role, borrower_id? }
borrowers[]: {
  borrower_id, name, assigned_analyst_id,
  loan: { loan_id, loan_amount, emi_amount, outstanding_balance, credit_limit, next_due_date },
  payments[]: { due_date, due_amount, paid_amount, paid_date, days_past_due, status, channel, auto_debit_failed },
  transactions[]: { date, amount, type, category, description },
  balance_history[]: { date, account_balance, credit_limit, outstanding_balance },
  scenario_tag, notes
}
```

### Demo borrowers (scenario coverage)

| ID | Scenario |
|----|----------|
| B101 | Healthy / Low risk |
| B102 | Rising DPD trend |
| B103 | Frequent failed auto-debits |
| B104 | Rising credit utilization |
| B105 | Reduced income inflows |
| B106 | Skipped / partial payments |
| B107 | Declining account balance |
| B108 | Missing payments data (edge) |
| B109 | Insufficient history (edge) |
| B110 | Critical multi-signal |

Analyst **A001** owns B101, B102, B103, B107, B109.  
Analyst **A002** owns B104, B105, B106, B108, B110.

## Documented assumptions (centralized in `app/config.py`)

Assignment does not specify these parameters; they are configurable and overrideable via env when needed:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `delinquency_horizon_days` | 30 | Early-warning target horizon |
| `min_payment_history_cycles` | 3 | Below this → insufficient history; High/Critical capped to Watchlist |
| `payment_trend_window` | 3 | Last N EMIs for DPD / partial trends |
| `failed_autodebit_lookback_days` | 60 | Failed auto-debit count window |
| `transaction_lookback_days` | 90 | Max age of transactions considered for income signals |
| `income_baseline_days` / `income_recent_days` | 90 / 30 | Income decline comparison windows |
| `balance_trend_window` | 3 | Account-balance decline snapshots |
| **Utilization** | `outstanding_balance / credit_limit × 100` | Rising util = rise vs earliest balance snapshot |
| Utilization bands | 70% watch / 85% high / +15pt rise | Fire utilization signals |
| Income decline | ≥ 30% vs comparable baseline | Reduced inflows signal |
| Balance decline | ≥ 25% across snapshots | Declining balance signal |
| Current DPD | 1 / 15 / 30 | Watch / High / Critical bands |
| Score bands | 20 / 45 / 70 | Watchlist / High Risk / Critical |
| `as_of` for demo | `2026-07-15` | Matches mock dataset `as_of_date` |

### Action mapping (deterministic)

| Category | Typical action |
|----------|----------------|
| Low | no action |
| Watchlist | soft reminder (or manual review if history incomplete) |
| High Risk | proactive call, or payment plan offer if income/partial signals |
| Critical | restructuring review or manual analyst review |

## API surface

All borrower endpoints accept optional `?as_of=YYYY-MM-DD` (demo default: `2026-07-15`).

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | — | Liveness probe |
| GET | `/ready` | — | Readiness probe (storage loaded) |
| GET | `/metrics` | — | Prometheus-style counters |
| GET | `/api/auth/users` | — | Demo login picker (`ALLOW_DEMO_LOGIN`) |
| POST | `/api/auth/login` | — | Returns signed JWT + HttpOnly cookie |
| GET | `/api/auth/me` | Bearer | Validate current session |
| GET | `/api/alerts` | Bearer | Visible borrowers, sorted by severity |
| GET | `/api/borrowers/{id}/assessment` | Bearer + RBAC | Rule-based assessment |
| GET | `/api/borrowers/{id}/profile` | Bearer + RBAC | Full borrower JSON (redacted for borrowers) |
| GET | `/api/borrowers/{id}/borrower-update` | Bearer + RBAC | Deterministic borrower message (no LLM) |
| GET | `/api/borrowers/{id}/explanation` | Analyst/manager | LLM narration of assessment |
| GET | `/api/borrowers/{id}/explanation/stream` | Analyst/manager | SSE stream (`meta`, `status`, `chunk`, `done`) |
| POST | `/api/borrowers/{id}/qa` | Analyst/manager | Grounded Q&A (question max 500 chars) |
| POST | `/api/borrowers/{id}/qa/stream` | Analyst/manager | SSE Q&A stream |
| POST | `/api/borrowers/{id}/scenario` | Analyst/manager | Miss-next-EMI simulation |
| GET | `/api/portfolio/summary` | Bearer | Portfolio rollup by role |
| GET | `/api/config/public` | — | Thresholds, `llm_configured`, `api_version` |

OpenAPI docs: `http://localhost:5001/docs` when the server is running.

### Security architecture

| Layer | Implementation |
|-------|----------------|
| **Authentication** | HS256 JWT (`PyJWT`) issued by `POST /api/auth/login`; 8h expiry; HttpOnly `eews_token` cookie |
| **Authorization** | Role dependencies + per-borrower RBAC; analyst LLM routes blocked for borrowers |
| **Audit trail** | JSON audit log (`audit` logger) for login, profile/assessment access, LLM, Q&A, scenarios |
| **Input validation** | Pydantic schemas; borrower ID path regex; Q&A sanitization + injection pattern blocklist |
| **LLM guardrails** | Pre-computed risk never from LLM; post-LLM narration guard detects category/score override attempts |
| **Rate limiting** | Per-IP limits: general (120/min), LLM (15/min), login (20/min) |
| **HTTP hardening** | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS in production |
| **CORS** | Explicit origin list; credentials enabled for cookie auth |
| **Error handling** | Generic 500 messages in production; `request_id` in error payload |
| **PII redaction** | Borrower role never sees `assigned_analyst_id`, `notes`, `scenario_tag` |

#### Production auth env (required when `APP_ENV=production`)

```env
APP_ENV=production
JWT_SECRET=<openssl rand -hex 32>
ALLOW_DEMO_LOGIN=false
ALLOW_LEGACY_USER_ID_AUTH=false
CORS_ORIGINS=https://your-frontend.example.com
```

Startup **fails fast** if production secrets or flags are unsafe (`app/startup.py`).

#### Run production server

```bash
gunicorn -c gunicorn.conf.py app.main:app
```

## Storage abstraction

```text
app/storage/base.py      → StorageBackend interface
app/storage/file_store.py → JSON implementation (default)
app/storage/db_store.py   → stub for future DATABASE_URL
app/storage/factory.py    → STORAGE_BACKEND=file|db
```

When DB credentials are provided, implement `DatabaseStorage` methods and set:

```env
STORAGE_BACKEND=db
DATABASE_URL=postgresql://...
```

## Test scenarios / edge cases

1. **Low risk** — login `A001` → B101 stays Low / no action.  
2. **DPD trend** — B102 shows worsening DPD + High Risk.  
3. **Failed auto-debits** — B103 fires failed-debit signal.  
4. **Utilization** — B104 high + rising utilization.  
5. **Income drop** — B105 income decline → payment plan offer path.  
6. **Partials/skips** — B106 partial/skipped payments.  
7. **Balance decline** — B107 declining cash balance.  
8. **Missing payments** — B108 empty payment list → Watchlist + manual review, category capped.  
9. **Insufficient history** — B109 < 3 cycles → Watchlist cap.  
10. **Critical stack** — B110 multi-signal Critical → restructuring review.  
11. **RBAC borrower** — login `U_B101` cannot open B102.  
12. **RBAC analyst** — `A001` cannot open B104 (assigned to A002).  
13. **Q&A grounding** — ask “Why was borrower flagged?” on detail page; refuse out-of-scope inventing.  
14. **Scenario** — “miss next EMI” increases score relative to baseline.  

Without `LLM_API_TOKEN`, explanation/Q&A use deterministic template fallbacks so the demo still runs.

### Automated tests

```bash
pytest tests -v
```

Covers risk-engine scenarios (B101–B110), RBAC, JWT auth, security headers, prompt-injection blocking, LLM guard, audit logging, and production startup validation (**32 tests**).

## Demo presentation script (~5 min)

1. **Login as A001** → dashboard shows assigned borrowers sorted by severity.  
2. **Open B110** (Critical) → show deterministic assessment signals, then streaming LLM explanation.  
3. **Ask Q&A** — “Why was this borrower flagged?” — grounded answer from borrower data.  
4. **Run scenario** — miss next EMI → score increases.  
5. **Contrast B101** (Low) on same analyst.  
6. **RBAC** — switch to A002, show B104 visible but B101 blocked.  
7. **Borrower view** — login `U_B101` → plain deterministic update, no internal risk labels.  

## Production readiness

| Capability | Status | Details |
|------------|--------|---------|
| **Health probes** | Implemented | `/health` (liveness), `/ready` (readiness + borrower count) |
| **Metrics** | Implemented | `/metrics` — request, error, auth, LLM, rate-limit counters |
| **Structured logging** | Implemented | JSON logs in `APP_ENV=production`; access + audit loggers |
| **Request tracing** | Implemented | `X-Request-Id` on every response; propagated to audit logs |
| **Graceful lifecycle** | Implemented | FastAPI lifespan startup validation + shutdown log |
| **CI pipeline** | Implemented | `.github/workflows/ci.yml` — pytest + `npm run build` |
| **Container deploy** | Implemented | `Dockerfile`, `docker-compose.yml`, non-root user, `/ready` healthcheck |
| **Process model** | Implemented | `gunicorn.conf.py` with uvicorn workers for production |
| **Config validation** | Implemented | Production fail-fast on weak JWT / open demo endpoints |
| **Automated tests** | 32 tests | Risk, RBAC, security, LLM guard, production config |

### Remaining for full bank production

| Area | Next step |
|------|-----------|
| Identity | Replace demo login with IdP SSO (OIDC/SAML) |
| Database | Implement `DatabaseStorage` + row-level security |
| Secrets | Vault/KMS for `JWT_SECRET`, `LLM_API_TOKEN` |
| Rate limits | Redis-backed per-user limits behind load balancer |
| LLM governance | Formal output validation, cost caps, model allowlist |
| Observability | Ship logs to Datadog/Splunk; add distributed tracing |

## Trade-offs & limitations

- Heuristic scoring, not a calibrated PD model  
- Mock static as-of date (no streaming ingestion)  
- Auth is simulated for demos (cookie + Bearer token)  
- LLM output is prompted to stay grounded but not formally verified with citations/RAG retrieval beyond prompt context  
- File storage is single-process; swap to DB for concurrency  
- SSE streaming simulates token chunks after full LLM response (wrapper is non-streaming)

## Project layout

```text
backend/
  app/
    config.py
    main.py
    auth/
    middleware/   # rate limiting
    models/
    routers/
    services/   # risk_engine, llm_client, explanation, qa
    storage/
  tests/          # pytest suite
  data/mock_dataset.json
  Dockerfile
frontend/
  app/          # login, dashboard, borrower self-view, detail
  components/
  lib/
  middleware.ts   # route cookie guard
  Dockerfile
docker-compose.yml
```
