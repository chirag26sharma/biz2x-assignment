"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ExplanationStreamPanel } from "@/components/ExplanationStreamPanel";
import { LlmStreamOutput } from "@/components/LlmStreamOutput";
import {
  formatINR,
  getAssessment,
  getProfile,
  runScenario,
  type RiskAssessment,
} from "@/lib/api";
import { streamQuestion } from "@/lib/stream";
import { categoryClass, severityClass } from "@/lib/styles";

export default function BorrowerDetailPage() {
  const params = useParams<{ borrowerId: string }>();
  const borrowerId = typeof params.borrowerId === "string" ? params.borrowerId : "";
  const { session, setSession, ready } = useAuth();
  const router = useRouter();

  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [scenario, setScenario] = useState<RiskAssessment | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [question, setQuestion] = useState("Why was this borrower flagged?");
  const [answerText, setAnswerText] = useState("");
  const [answerStatus, setAnswerStatus] = useState<string | null>(null);
  const [answerStreaming, setAnswerStreaming] = useState(false);
  const [answerLlmUsed, setAnswerLlmUsed] = useState<boolean | null>(null);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [assessmentLoading, setAssessmentLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(true);
  const [scenarioBusy, setScenarioBusy] = useState(false);
  const qaAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!ready || !borrowerId) return;
    if (!session) {
      router.replace("/");
      return;
    }
    if (session.user.role === "borrower") {
      router.replace("/borrower");
      return;
    }

    setAssessment(null);
    setProfile(null);
    setScenario(null);
    setAssessmentError(null);
    setProfileError(null);
    setActionError(null);
    setAnswerText("");
    setAssessmentLoading(true);
    setProfileLoading(true);

    const token = session.token;

    getAssessment(token, borrowerId)
      .then(setAssessment)
      .catch((e: Error) => setAssessmentError(e.message))
      .finally(() => setAssessmentLoading(false));

    getProfile(token, borrowerId)
      .then(setProfile)
      .catch((e: Error) => setProfileError(e.message))
      .finally(() => setProfileLoading(false));
  }, [ready, session, router, borrowerId]);

  async function onAsk() {
    if (!session || !borrowerId || !question.trim()) return;
    qaAbortRef.current?.abort();
    const ac = new AbortController();
    qaAbortRef.current = ac;

    setAnswerText("");
    setAnswerLlmUsed(null);
    setAnswerStreaming(true);
    setAnswerStatus("Sending question…");
    setActionError(null);

    try {
      await streamQuestion(
        session.token,
        borrowerId,
        question.trim(),
        {
          onStatus: (s) => setAnswerStatus(s.message),
          onChunk: (chunk) => setAnswerText((prev) => prev + chunk),
          onDone: (d) => {
            setAnswerLlmUsed(d.llm_used ?? false);
            setAnswerStreaming(false);
            setAnswerStatus(null);
            if (d.full_text) setAnswerText(d.full_text);
          },
          onError: (msg) => {
            setActionError(msg);
            setAnswerStreaming(false);
            setAnswerStatus(null);
          },
        },
        ac.signal,
      );
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") {
        setActionError(e.message);
        setAnswerStreaming(false);
        setAnswerStatus(null);
      }
    }
  }

  async function onScenario() {
    if (!session || !borrowerId) return;
    setScenarioBusy(true);
    setActionError(null);
    try {
      setScenario(await runScenario(session.token, borrowerId));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Scenario failed");
    } finally {
      setScenarioBusy(false);
    }
  }

  useEffect(() => () => qaAbortRef.current?.abort(), []);

  if (!ready) return null;
  if (!session || session.user.role === "borrower") return null;
  if (!borrowerId) return <main className="shell"><p className="panel muted">Invalid borrower.</p></main>;

  const loan = profile?.loan as
    | { outstanding_balance?: number; emi_amount?: number; next_due_date?: string }
    | undefined;

  return (
    <main className="shell fade-in">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">Biz2X Early Warning</div>
          <div className="brand-sub">
            <Link href="/dashboard">← Dashboard</Link>
            {" · "}
            {String(profile?.name ?? borrowerId)} ({borrowerId})
          </div>
        </div>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            setSession(null);
            router.push("/");
          }}
        >
          Sign out
        </button>
      </header>

      {actionError && (
        <p className="panel" style={{ color: "var(--critical)", marginBottom: "1rem" }}>
          {actionError}
        </p>
      )}

      <div className="stack">
        {assessmentLoading && (
          <p className="panel muted">Loading risk assessment…</p>
        )}

        {assessmentError && !assessment && (
          <p className="panel" style={{ color: "var(--critical)" }}>
            Assessment unavailable: {assessmentError}
          </p>
        )}

        {assessment && (
          <section className="panel">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div className="row">
                <span className={`badge ${categoryClass(assessment.risk_category)}`}>
                  {assessment.risk_category}
                </span>
                <span className={`badge ${severityClass(assessment.severity)}`}>
                  {assessment.severity}
                </span>
                <span className="mono">score {assessment.risk_score}</span>
              </div>
              {loan && (
                <div className="muted" style={{ fontSize: "0.9rem" }}>
                  Outstanding {formatINR(loan.outstanding_balance ?? 0)} · EMI{" "}
                  {formatINR(loan.emi_amount ?? 0)} · next due {loan.next_due_date}
                </div>
              )}
            </div>
            <p style={{ margin: "0.85rem 0 0", textTransform: "capitalize" }}>
              Recommended action: <strong>{assessment.recommended_action}</strong>
            </p>
          </section>
        )}

        <ExplanationStreamPanel token={session.token} borrowerId={borrowerId} />

        {assessment && (
          <section className="panel">
            <h2 style={{ marginTop: 0, fontSize: "1.15rem" }}>Deterministic signals</h2>
            <ul className="signal-list">
              {assessment.signals.map((s) => (
                <li key={s.code}>
                  <strong>{s.label}</strong>{" "}
                  <span className="muted mono">+{s.points}</span>
                  <div className="muted" style={{ fontSize: "0.9rem" }}>
                    {s.detail}
                  </div>
                </li>
              ))}
            </ul>
            {!assessment.signals.length && (
              <p className="muted" style={{ margin: 0 }}>
                No stress signals.
              </p>
            )}
          </section>
        )}

        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: "1.15rem" }}>Analyst Q&A</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            Answers are grounded only in this borrower&apos;s data and assessment.
          </p>
          <div className="row">
            <input
              className="input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about this borrower…"
              disabled={answerStreaming}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !answerStreaming) onAsk();
              }}
            />
            <button
              type="button"
              className={`btn btn-primary${answerStreaming ? " is-loading" : ""}`}
              disabled={answerStreaming || !question.trim()}
              onClick={onAsk}
            >
              {answerStreaming ? (
                <>
                  <span className="btn-spinner" />
                  Asking…
                </>
              ) : (
                "Ask"
              )}
            </button>
          </div>

          {(answerStreaming || answerText) && (
            <div className="llm-answer-box">
              <LlmStreamOutput
                text={answerText}
                streaming={answerStreaming}
                status={answerStatus}
                emptyLabel="Preparing answer…"
              />
              {!answerStreaming && answerLlmUsed === false && (
                <p className="muted" style={{ fontSize: "0.8rem", marginTop: "0.5rem", marginBottom: 0 }}>
                  LLM fallback used — check LLM_API_TOKEN in backend .env
                </p>
              )}
              {!answerStreaming && answerLlmUsed && (
                <p className="muted" style={{ fontSize: "0.8rem", marginTop: "0.5rem", marginBottom: 0 }}>
                  Answer streamed from LLM · grounded in borrower data only
                </p>
              )}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2 style={{ margin: 0, fontSize: "1.15rem" }}>Scenario: miss next EMI</h2>
            <button
              type="button"
              className={`btn btn-ghost${scenarioBusy ? " is-loading" : ""}`}
              disabled={scenarioBusy}
              onClick={onScenario}
            >
              {scenarioBusy ? "Simulating…" : "Simulate"}
            </button>
          </div>
          {scenario && assessment && (
            <div style={{ marginTop: "0.85rem" }}>
              <div className="row">
                <span className={`badge ${categoryClass(scenario.risk_category)}`}>
                  {scenario.risk_category}
                </span>
                <span className="mono">score {scenario.risk_score}</span>
                <span style={{ textTransform: "capitalize" }}>
                  → {scenario.recommended_action}
                </span>
              </div>
              <p className="muted" style={{ fontSize: "0.9rem", marginBottom: 0 }}>
                Compared to current score {assessment.risk_score} ({assessment.risk_category}).
              </p>
            </div>
          )}
        </section>

        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: "1.15rem" }}>Payment / utilization snapshot</h2>
          {profileLoading && <p className="muted">Loading payment data…</p>}
          {profileError && !profile && (
            <p className="muted" style={{ color: "var(--critical)" }}>
              Payment data unavailable: {profileError}
            </p>
          )}
          {profile && assessment && (
            <pre
              className="mono"
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontSize: "0.78rem",
                maxHeight: 280,
                overflow: "auto",
                color: "var(--muted)",
              }}
            >
              {JSON.stringify(
                {
                  scenario_tag: profile.scenario_tag,
                  indicators: assessment.indicators,
                  payments: profile.payments,
                  balance_history: profile.balance_history,
                },
                null,
                2,
              )}
            </pre>
          )}
          {profile && !assessment && (
            <pre className="mono" style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.78rem", color: "var(--muted)" }}>
              {JSON.stringify(
                {
                  payments: profile.payments,
                  balance_history: profile.balance_history,
                },
                null,
                2,
              )}
            </pre>
          )}
        </section>
      </div>
    </main>
  );
}
