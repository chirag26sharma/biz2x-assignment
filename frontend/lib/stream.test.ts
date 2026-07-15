import * as api from "./api";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { consumeSseStream, streamExplanation, type StreamHandlers } from "./stream";

function sseBody(...blocks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const payload = blocks.join("\n\n") + "\n\n";
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(payload));
      controller.close();
    },
  });
}

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("consumeSseStream", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("parses meta, chunk, and done SSE events", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(
        sseBody(
          'event: meta\ndata: {"borrower_id":"B101"}',
          'event: chunk\ndata: {"text":"Hello "}',
          'event: done\ndata: {"llm_used":true,"full_text":"Hello world"}',
        ),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      ),
    );

    const meta: unknown[] = [];
    const chunks: string[] = [];
    let done: Record<string, unknown> | undefined;

    await consumeSseStream("/api/test/stream", "token", {
      onMeta: (d) => meta.push(d),
      onChunk: (t) => chunks.push(t),
      onDone: (d) => {
        done = d;
      },
    });

    expect(meta).toEqual([{ borrower_id: "B101" }]);
    expect(chunks).toEqual(["Hello "]);
    expect(done).toMatchObject({ llm_used: true, full_text: "Hello world" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/test/stream"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  it("throws structured error on 429 with retryAfter", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(429, { detail: "Rate limit exceeded", retry_after_seconds: 7 }, { "Retry-After": "7" }),
    );

    await expect(consumeSseStream("/api/test/stream", "token", {})).rejects.toMatchObject({
      message: "Rate limit exceeded",
      status: 429,
      retryAfter: 7,
    });
  });
});

describe("streamExplanation", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("falls back to REST explanation when stream returns 404", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(404, { detail: "Not found" }));

    vi.spyOn(api, "getExplanation").mockResolvedValue({
      borrower_id: "B101",
      risk_category: "Low",
      severity: "Low",
      recommended_action: "no_action",
      key_reasons: [],
      explanation: "Deterministic fallback explanation.",
      grounded: true,
      llm_used: false,
    });

    const statuses: string[] = [];
    const chunks: string[] = [];
    let donePayload: { llm_used?: boolean; grounded?: boolean } | undefined;

    const handlers: StreamHandlers = {
      onStatus: (s) => statuses.push(s.phase),
      onChunk: (t) => chunks.push(t),
      onDone: (d) => {
        donePayload = d;
      },
    };

    const run = streamExplanation("token", "B101", handlers);
    await vi.runAllTimersAsync();
    await run;

    expect(statuses).toContain("fallback");
    expect(chunks.join("")).toContain("Deterministic fallback");
    expect(donePayload).toMatchObject({ llm_used: false, grounded: true });
  });

  it("retries after 429 then falls back to REST when still rate limited", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(429, { detail: "Rate limit exceeded", retry_after_seconds: 1 }),
    );

    vi.spyOn(api, "getExplanation").mockResolvedValue({
      borrower_id: "B110",
      risk_category: "Critical",
      severity: "Critical",
      recommended_action: "restructuring_review",
      key_reasons: [],
      explanation: "Still rate limited fallback.",
      grounded: true,
      llm_used: false,
    });

    const phases: string[] = [];
    const handlers: StreamHandlers = {
      onStatus: (s) => phases.push(s.phase),
      onDone: () => {},
    };

    const promise = streamExplanation("token", "B110", handlers);
    await vi.runAllTimersAsync();
    await promise;

    expect(phases).toContain("retry");
    expect(phases).toContain("fallback");
  });
});
