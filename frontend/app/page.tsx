"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { listUsers, login, type AuthUser, type UserRole } from "@/lib/api";

function resolvePostLoginPath(role: UserRole): string {
  const next =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("next")
      : null;
  if (next && next.startsWith("/") && !next.startsWith("//")) {
    if (role === "borrower" && (next.startsWith("/dashboard") || next.startsWith("/borrowers"))) {
      return "/borrower";
    }
    if (role !== "borrower" && next === "/borrower") {
      return "/dashboard";
    }
    return next;
  }
  return role === "borrower" ? "/borrower" : "/dashboard";
}

export default function HomePage() {
  const { session, setSession, ready } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    if (session) {
      router.replace(resolvePostLoginPath(session.user.role));
      return;
    }
    listUsers()
      .then(setUsers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ready, session, router]);

  async function signIn(user: AuthUser) {
    try {
      const { user: verified, token, expires_in } = await login(user.user_id);
      setSession({
        user: verified,
        token,
        expiresAt: Date.now() + expires_in * 1000,
      });
      router.push(resolvePostLoginPath(verified.role));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  const analysts = users.filter((u) => u.role === "analyst" || u.role === "manager");
  const borrowers = users.filter((u) => u.role === "borrower");

  return (
    <main className="shell fade-in">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">Biz2X Early Warning</div>
          <div className="brand-sub">Loan default risk monitoring · prototype</div>
        </div>
      </header>

      <section className="panel" style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ margin: "0 0 0.4rem", fontSize: "1.75rem" }}>Select a demo role</h1>
        <p className="muted" style={{ margin: 0, maxWidth: "42rem" }}>
          Simulated authentication. Borrowers only see their own explanation; analysts only
          see assigned borrowers. Risk category, severity, and actions are rule-based — the
          LLM only narrates and answers grounded questions.
        </p>
      </section>

      {error && (
        <p className="panel" style={{ color: "var(--critical)", marginBottom: "1rem" }}>
          Could not reach API ({error}). Start the backend on port 5001.
        </p>
      )}

      {loading ? (
        <p className="muted">Loading users…</p>
      ) : (
        <div className="stack">
          <section>
            <h2 style={{ fontSize: "1.1rem", marginBottom: "0.65rem" }}>Credit / collections</h2>
            <div className="login-grid">
              {analysts.map((u) => (
                <button
                  key={u.user_id}
                  type="button"
                  className="login-card"
                  data-testid={`login-${u.user_id}`}
                  onClick={() => signIn(u)}
                >
                  <div style={{ fontWeight: 700 }}>{u.name}</div>
                  <div className="muted mono">
                    {u.user_id} · {u.role}
                  </div>
                </button>
              ))}
            </div>
          </section>
          <section>
            <h2 style={{ fontSize: "1.1rem", marginBottom: "0.65rem" }}>Borrowers</h2>
            <div className="login-grid">
              {borrowers.map((u) => (
                <button
                  key={u.user_id}
                  type="button"
                  className="login-card"
                  data-testid={`login-${u.user_id}`}
                  onClick={() => signIn(u)}
                >
                  <div style={{ fontWeight: 700 }}>{u.name}</div>
                  <div className="muted mono">
                    {u.user_id} · borrower {u.borrower_id}
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
