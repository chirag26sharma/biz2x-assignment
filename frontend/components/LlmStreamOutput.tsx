"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  text: string;
  streaming?: boolean;
  status?: string | null;
  emptyLabel?: string;
};

export function LlmStreamOutput({ text, streaming, status, emptyLabel }: Props) {
  const hasText = text.trim().length > 0;

  return (
    <div className="llm-output">
      {streaming && status && (
        <div className="llm-status" role="status" aria-live="polite">
          <span className="llm-status-dot" />
          {status}
        </div>
      )}
      <div className="llm-prose llm-markdown">
        {hasText ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
        ) : streaming ? (
          <p className="llm-placeholder">Waiting for response…</p>
        ) : (
          <p className="llm-placeholder">{emptyLabel ?? "No output yet."}</p>
        )}
        {streaming && hasText && <span className="llm-cursor" aria-hidden="true" />}
      </div>
    </div>
  );
}
