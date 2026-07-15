# Demo Guide — 5-Minute Interview Walkthrough

Use this script when presenting the Biz2X SSE assignment to interviewers.

**Before you start:** Backend on port 5001, frontend on port 3000, optional `LLM_API_TOKEN` set.

---

## 0:00 — Problem framing (30 sec)

> "This is a proactive early-warning system for a digital lending platform. It flags borrowers likely to become delinquent within 30 days — before they actually default. Scoring is fully deterministic; the LLM only explains and answers analyst questions."

Open [http://localhost:3000](http://localhost:3000)

---

## 0:30 — Analyst login & dashboard (45 sec)

1. Click **Anita Sharma (A001)** — analyst
2. Dashboard shows borrowers **sorted by severity**
3. Point out portfolio stats: Critical count, outstanding at risk
4. Mention: "A001 only sees assigned borrowers — RBAC enforced at API layer"

**Talking point:** Risk category and action are rule-based, not LLM-generated.

---

## 1:15 — Critical borrower deep dive (90 sec)

1. Sign out → login **Rahul Mehta (A002)**
2. Open **B110** (Critical — multi-signal)
3. Show:
   - **Assessment panel** — score, category, recommended action
   - **Deterministic signals** — DPD, utilization, income, etc.
   - **DPD trend chart** — visual risk trajectory
   - **Payment history table** — formatted, not raw JSON
4. Wait for **streaming LLM explanation** (or note template fallback if no token)

**Talking point:** Page loads assessment instantly; LLM streams separately so UI isn't blocked.

---

## 2:45 — Analyst Q&A (45 sec)

1. Default question: *"Why was this borrower flagged?"*
2. Click **Ask** — show grounded streaming answer
3. Say: "Prompt is constrained to this borrower's data only — no inventing other accounts"

---

## 3:30 — Scenario simulation (30 sec)

1. Click **Simulate** — miss next EMI
2. Show score increase vs baseline
3. "What-if for collections planning without changing production data"

---

## 4:00 — Contrast healthy borrower (30 sec)

1. Go to dashboard → open **B101** (Vikram Patel — Low risk)
2. Brief contrast: few signals, low score, no action needed

---

## 4:30 — RBAC & borrower view (30 sec)

1. Sign out → login **U_B101** (borrower)
2. Show **plain-language account update** — no internal risk labels
3. Try navigating to `/borrowers/B102` — blocked (403 from API)

**Talking point:** Borrowers never see "Critical", analyst notes, or LLM explanations.

---

## 5:00 — Engineering extras (if time)

| Topic | Where to point |
|-------|----------------|
| 32 backend tests | `pytest tests -v` |
| 4 Playwright E2E tests | `npm run test:e2e` |
| JWT + audit logs | `app/auth/`, `app/auth/audit.py` |
| Production probes | `/health`, `/ready`, `/metrics` |
| Documented assumptions | `backend/app/config.py` + README |

---

## Showcase borrower cheat sheet

| ID | Scenario | Category | Login as |
|----|----------|----------|----------|
| B101 | Healthy | Low | A001 |
| B102 | Rising DPD | High Risk | A001 |
| B110 | Multi-signal | Critical | A002 |
| B108 | Missing payments | Watchlist (capped) | A002 |
| B109 | Insufficient history | Watchlist (capped) | A001 |

---

## If LLM is slow or unavailable

> "The system degrades gracefully — deterministic assessment always works; LLM narration falls back to a template. In production we'd add caching and async job queues."

---

## Recording a video (optional)

Record screen + voice following sections 0:00–4:30. Upload to Loom/YouTube unlisted and add link to your submission email.
