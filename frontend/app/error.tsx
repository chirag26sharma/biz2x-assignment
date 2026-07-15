"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="shell">
      <section className="panel">
        <h1 style={{ marginTop: 0, fontSize: "1.25rem" }}>Something went wrong</h1>
        <p className="muted">{error.message || "An unexpected error occurred."}</p>
        <button type="button" className="btn btn-primary" onClick={reset}>
          Try again
        </button>
      </section>
    </main>
  );
}
