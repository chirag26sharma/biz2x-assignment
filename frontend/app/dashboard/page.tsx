"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  formatINR,
  getPortfolio,
  listAlerts,
  type AlertSummary,
  type PortfolioSummary,
} from "@/lib/api";
import { categoryClass, severityClass } from "@/lib/styles";

export default function DashboardPage() {
  const { session, setSession, ready } = useAuth();
  const router = useRouter();
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    if (!session) {
      router.replace("/");
      return;
    }
    if (session.user.role === "borrower") {
      router.replace("/borrower");
      return;
    }

    Promise.all([listAlerts(session.token), getPortfolio(session.token)])
      .then(([a, p]) => {
        setAlerts(a);
        setPortfolio(p);
      })
      .catch((e: Error) => setError(e.message));
  }, [ready, session, router]);

  if (!session || session.user.role === "borrower") return null;

  return (
    <main className="shell fade-in">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">Biz2X Early Warning</div>
          <div className="brand-sub">
            Signed in as {session.user.name} ({session.user.role}) · {session.user.user_id}
          </div>
        </div>
        <button type="button" className="btn btn-ghost" onClick={() => { setSession(null); router.push("/"); }}>
          Sign out
        </button>
      </header>

      {error && (
        <p className="panel" style={{ color: "var(--critical)", marginBottom: "1rem" }}>
          {error}
        </p>
      )}

      {portfolio && (
        <div className="grid-stats">
          <div className="panel">
            <div className="stat-label">Visible borrowers</div>
            <div className="stat-value">{portfolio.total_borrowers}</div>
          </div>
          <div className="panel">
            <div className="stat-label">Critical</div>
            <div className="stat-value" style={{ color: "var(--critical)" }}>
              {portfolio.critical_count}
            </div>
          </div>
          <div className="panel">
            <div className="stat-label">High risk</div>
            <div className="stat-value" style={{ color: "var(--high)" }}>
              {portfolio.high_risk_count}
            </div>
          </div>
          <div className="panel">
            <div className="stat-label">Outstanding at risk</div>
            <div className="stat-value" style={{ fontSize: "1.25rem" }}>
              {formatINR(portfolio.total_outstanding_at_risk)}
            </div>
          </div>
        </div>
      )}

      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.75rem" }}>
          <h1 style={{ margin: 0, fontSize: "1.35rem" }}>Borrowers by risk severity</h1>
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            As of 2026-07-15 · deterministic scoring
          </span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Borrower</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Score</th>
                <th>Key reasons</th>
                <th>Action</th>
                <th>Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr
                  key={a.borrower_id}
                  onClick={() => router.push(`/borrowers/${a.borrower_id}`)}
                >
                  <td>
                    <div style={{ fontWeight: 600 }}>{a.borrower_name}</div>
                    <div className="muted mono">{a.borrower_id}</div>
                  </td>
                  <td>
                    <span className={`badge ${categoryClass(a.risk_category)}`}>
                      {a.risk_category}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${severityClass(a.severity)}`}>{a.severity}</span>
                  </td>
                  <td className="mono">{a.risk_score}</td>
                  <td style={{ maxWidth: 280 }}>
                    {a.key_reasons.length ? a.key_reasons.slice(0, 3).join(" · ") : "None"}
                    {a.insufficient_history && (
                      <div className="muted" style={{ fontSize: "0.8rem", marginTop: 4 }}>
                        Insufficient history
                      </div>
                    )}
                  </td>
                  <td style={{ textTransform: "capitalize" }}>{a.recommended_action}</td>
                  <td>{formatINR(a.outstanding_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!alerts.length && !error && <p className="muted">No borrowers in scope for this user.</p>}
      </section>

      <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
        Tip: open a row for LLM explanation, analyst Q&A, and “what if next EMI is missed?”
        simulation. <Link href="/">Switch user</Link>
      </p>
    </main>
  );
}
