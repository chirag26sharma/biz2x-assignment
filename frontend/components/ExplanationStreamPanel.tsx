"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamExplanation } from "@/lib/stream";
import { LlmStreamOutput } from "./LlmStreamOutput";

type Props = {
  token: string;
  borrowerId: string;
  title?: string;
  subtitle?: string;
};

export function ExplanationStreamPanel({
  token,
  borrowerId,
  title = "LLM explanation (grounded)",
  subtitle = "Category, severity, and action remain rule-based",
}: Props) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>("Connecting…");
  const [streaming, setStreaming] = useState(true);
  const [llmUsed, setLlmUsed] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setText("");
    setError(null);
    setLlmUsed(null);
    setStreaming(true);
    setStatus("Connecting…");

    streamExplanation(token, borrowerId, {
      onStatus: (s) => setStatus(s.message),
      onChunk: (chunk) => setText((prev) => prev + chunk),
      onDone: (d) => {
        setLlmUsed(d.llm_used ?? false);
        setStreaming(false);
        setStatus(null);
        if (d.full_text) setText(d.full_text);
      },
      onError: (msg) => {
        setError(msg);
        setStreaming(false);
        setStatus(null);
      },
    }, ac.signal).catch((e: Error) => {
      if (e.name !== "AbortError") {
        const msg =
          /rate limit/i.test(e.message)
            ? "Explanation is temporarily rate-limited. Wait a moment and click Regenerate."
            : e.message || "Failed to load explanation.";
        setError(msg);
        setStreaming(false);
        setStatus(null);
      }
    });
  }, [token, borrowerId]);

  useEffect(() => {
    start();
    return () => abortRef.current?.abort();
    // Only restart when auth or borrower changes — avoids duplicate streams from callback churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, borrowerId]);

  return (
    <section className="panel">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.5rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.15rem" }}>{title}</h2>
        {!streaming && (
          <button type="button" className="btn btn-ghost" style={{ fontSize: "0.8rem", padding: "0.35rem 0.7rem" }} onClick={start}>
            Regenerate
          </button>
        )}
      </div>
      <LlmStreamOutput text={text} streaming={streaming} status={status} emptyLabel="Generating explanation…" />
      {error && <p className="llm-error">{error}</p>}
      {!streaming && llmUsed !== null && (
        <p className="muted" style={{ fontSize: "0.8rem", marginTop: "0.65rem", marginBottom: 0 }}>
          {llmUsed ? "Generated via LLM wrapper (streamed)" : "Template fallback"} · {subtitle}
        </p>
      )}
    </section>
  );
}
