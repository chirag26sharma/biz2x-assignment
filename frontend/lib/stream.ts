import { API_BASE } from "./config";

export type StreamHandlers = {
  onMeta?: (data: Record<string, unknown>) => void;
  onStatus?: (data: { phase: string; message: string }) => void;
  onChunk?: (text: string) => void;
  onDone?: (data: { llm_used?: boolean; full_text?: string; grounded?: boolean }) => void;
  onError?: (message: string) => void;
};

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n").filter(Boolean);
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  return { event, data: dataLines.join("\n") };
}

async function emitTextChunks(text: string, handlers: StreamHandlers): Promise<void> {
  const words = text.split(/\s+/).filter(Boolean);
  handlers.onStatus?.({ phase: "streaming", message: "Streaming response…" });
  for (let i = 0; i < words.length; i += 2) {
    const chunk = words.slice(i, i + 2).join(" ");
    const suffix = i + 2 >= words.length ? "" : " ";
    handlers.onChunk?.(chunk + suffix);
    await new Promise((r) => setTimeout(r, 18));
  }
}

async function sleep(ms: number): Promise<void> {
  await new Promise((r) => setTimeout(r, ms));
}

function httpError(
  status: number,
  detail: string,
  retryAfter?: number,
): Error & { status?: number; retryAfter?: number } {
  const err = new Error(detail) as Error & { status?: number; retryAfter?: number };
  err.status = status;
  err.retryAfter = retryAfter;
  return err;
}

async function parseErrorResponse(res: Response): Promise<Error & { status?: number; retryAfter?: number }> {
  let detail = res.statusText;
  let retryAfter: number | undefined;
  try {
    const body = (await res.json()) as { detail?: string | { detail?: string }; retry_after_seconds?: number };
    if (typeof body.detail === "string") detail = body.detail;
    else if (body.detail && typeof body.detail === "object" && "detail" in body.detail) {
      detail = String(body.detail.detail ?? detail);
    }
    const headerRetry = Number(res.headers.get("Retry-After"));
    const headerRetrySec =
      !Number.isNaN(headerRetry) && headerRetry > 0 ? headerRetry : undefined;
    retryAfter = body.retry_after_seconds ?? headerRetrySec;
  } catch {
    const headerRetry = Number(res.headers.get("Retry-After"));
    if (!Number.isNaN(headerRetry) && headerRetry > 0) retryAfter = headerRetry;
  }
  return httpError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail), retryAfter);
}

export async function consumeSseStream(
  path: string,
  token: string,
  handlers: StreamHandlers,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Accept: "text/event-stream",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
    signal: options.signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Streaming not supported");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const parsed = parseSseBlock(part);
      if (!parsed) continue;
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(parsed.data) as Record<string, unknown>;
      } catch {
        handlers.onError?.("Malformed stream payload");
        continue;
      }
      switch (parsed.event) {
        case "meta":
          handlers.onMeta?.(payload);
          break;
        case "status":
          handlers.onStatus?.(payload as { phase: string; message: string });
          break;
        case "chunk":
          handlers.onChunk?.(String(payload.text ?? ""));
          break;
        case "done":
          handlers.onDone?.(payload as { llm_used?: boolean; full_text?: string });
          break;
        case "error":
          handlers.onError?.(String(payload.message ?? "Stream error"));
          break;
        default:
          break;
      }
    }
  }
}

async function fallbackExplanation(
  token: string,
  borrowerId: string,
  handlers: StreamHandlers,
): Promise<void> {
  const { getExplanation } = await import("./api");
  handlers.onStatus?.({ phase: "fallback", message: "Using standard explanation endpoint…" });
  const res = await getExplanation(token, borrowerId);
  await emitTextChunks(res.explanation, handlers);
  handlers.onDone?.({ llm_used: res.llm_used, full_text: res.explanation, grounded: true });
}

async function fallbackQuestion(
  token: string,
  borrowerId: string,
  question: string,
  handlers: StreamHandlers,
): Promise<void> {
  const { askQuestion } = await import("./api");
  handlers.onStatus?.({ phase: "fallback", message: "Using standard Q&A endpoint…" });
  const res = await askQuestion(token, borrowerId, question);
  await emitTextChunks(res.answer, handlers);
  handlers.onDone?.({ llm_used: res.llm_used ?? false, full_text: res.answer, grounded: true });
}

async function withStreamFallback<T extends () => Promise<void>>(
  run: T,
  fallback: () => Promise<void>,
  handlers: StreamHandlers,
): Promise<void> {
  try {
    await run();
  } catch (e) {
    const err = e as Error & { status?: number; retryAfter?: number };
    if (err.status === 429) {
      const waitSec = err.retryAfter ?? 2;
      handlers.onStatus?.({ phase: "retry", message: `Rate limited — retrying in ${waitSec}s…` });
      await sleep(waitSec * 1000);
      try {
        await run();
        return;
      } catch (retryErr) {
        const retry = retryErr as Error & { status?: number };
        if (retry.status === 404 || /not found/i.test(retry.message)) {
          await fallback();
          return;
        }
        if (retry.status === 429) {
          handlers.onStatus?.({ phase: "fallback", message: "Still rate limited — using non-stream endpoint…" });
          await fallback();
          return;
        }
        throw retryErr;
      }
    }
    if (err.status === 404 || /not found/i.test(err.message)) {
      await fallback();
      return;
    }
    throw e;
  }
}

export async function streamExplanation(
  token: string,
  borrowerId: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  handlers.onStatus?.({ phase: "started", message: "Connecting…" });
  const run = () =>
    consumeSseStream(`/api/borrowers/${borrowerId}/explanation/stream`, token, handlers, { signal });
  await withStreamFallback(run, () => fallbackExplanation(token, borrowerId, handlers), handlers);
}

export async function streamQuestion(
  token: string,
  borrowerId: string,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  handlers.onStatus?.({ phase: "started", message: "Sending question…" });
  const run = () =>
    consumeSseStream(`/api/borrowers/${borrowerId}/qa/stream`, token, handlers, {
      method: "POST",
      body: { question },
      signal,
    });
  await withStreamFallback(
    run,
    () => fallbackQuestion(token, borrowerId, question, handlers),
    handlers,
  );
}

