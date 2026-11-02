import { LineSplitter } from "./text";
import type {
  AnswerDone,
  AskEvent,
  Category,
  DocumentInfo,
  IndexStatus,
  Library,
  Scope,
  Section,
  Turn,
} from "./types";

/** Everything the interface asks of the engine. The real one goes through a transport; the mock one lives in memory. */
export interface EngineApi {
  library(): Promise<Library>;
  addCategory(name: string): Promise<Category>;
  renameCategory(id: string, name: string): Promise<Category>;
  deleteCategory(id: string): Promise<void>;
  addSection(name: string, categoryId: string): Promise<Pick<Section, "id" | "name" | "category_id" | "folders">>;
  updateSection(id: string, patch: { name?: string; category_id?: string }): Promise<unknown>;
  deleteSection(id: string): Promise<void>;
  addFolder(sectionId: string, path: string): Promise<unknown>;
  removeFolder(sectionId: string, path: string): Promise<unknown>;
  index(sectionId: string): Promise<IndexStatus>;
  documents(sectionId: string): Promise<DocumentInfo[]>;
  ask(scope: Scope, question: string, history: Turn[], onToken: (text: string) => void, signal?: AbortSignal): Promise<AnswerDone>;
}

/** A failed request, with the engine's own explanation (RFC 9457 problem details). */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type Reply = { status: number; body: string };

/** How requests reach the engine: through the Open RAG window (desktop) or straight over HTTP (browser development). */
export interface Transport {
  send(method: string, path: string, body?: unknown): Promise<Reply>;
  /** Streams NDJSON lines; resolves when the stream ends, or with the error reply if the engine refused it. */
  stream(path: string, body: unknown, onLine: (line: string) => void, signal?: AbortSignal): Promise<Reply>;
}

export function problem(reply: Reply): ApiError {
  let detail = "";
  try {
    const parsed = JSON.parse(reply.body) as { detail?: string; title?: string };
    detail = parsed.detail || parsed.title || "";
  } catch {
    // Not JSON: fall back to the status below.
  }
  return new ApiError(reply.status, detail || `Request failed (${reply.status}).`);
}

export class Engine implements EngineApi {
  private readonly transport: Transport;

  constructor(transport: Transport) {
    this.transport = transport;
  }

  library = () => this.call<Library>("GET", "/library");
  addCategory = (name: string) => this.call<Category>("POST", "/categories", { name });
  renameCategory = (id: string, name: string) => this.call<Category>("PATCH", `/categories/${id}`, { name });
  deleteCategory = (id: string) => this.call<void>("DELETE", `/categories/${id}`);
  addSection = (name: string, categoryId: string) =>
    this.call<Pick<Section, "id" | "name" | "category_id" | "folders">>("POST", "/sections", { name, category_id: categoryId });
  updateSection = (id: string, patch: { name?: string; category_id?: string }) => this.call("PATCH", `/sections/${id}`, patch);
  deleteSection = (id: string) => this.call<void>("DELETE", `/sections/${id}`);
  addFolder = (sectionId: string, path: string) => this.call("POST", `/sections/${sectionId}/folders`, { path });
  removeFolder = (sectionId: string, path: string) => this.call("POST", `/sections/${sectionId}/folders/remove`, { path });
  index = (sectionId: string) => this.call<IndexStatus>("POST", `/sections/${sectionId}/index`);
  documents = (sectionId: string) => this.call<DocumentInfo[]>("GET", `/sections/${sectionId}/documents`);

  async ask(scope: Scope, question: string, history: Turn[], onToken: (text: string) => void, signal?: AbortSignal) {
    // Filled in by the stream callback; an object, because TypeScript can't follow assignments made inside callbacks.
    const outcome: { answer: AnswerDone | null; failure: ApiError | null } = { answer: null, failure: null };
    const reply = await this.transport.stream(
      "/ask",
      { scope, question, history },
      (line) => {
        const event = JSON.parse(line) as AskEvent;
        if (event.type === "token") onToken(event.text);
        else if (event.type === "done") outcome.answer = event;
        else outcome.failure = new ApiError(event.status, event.detail);
      },
      signal,
    );
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (reply.status >= 400) throw problem(reply);
    if (outcome.failure) throw outcome.failure;
    if (!outcome.answer) throw new ApiError(500, "The answer stopped before it was complete.");
    return outcome.answer;
  }

  private async call<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
    const reply = await this.transport.send(method, path, body);
    if (reply.status >= 400 || reply.status === 0) throw problem(reply);
    return (reply.body ? JSON.parse(reply.body) : undefined) as T;
  }
}

/** Straight to `ore serve` over HTTP, for working on the interface in a browser (`?api=...&token=...`). */
export function httpTransport(baseUrl: string, token: string): Transport {
  const base = baseUrl.replace(/\/$/, "");
  const request = async (method: string, path: string, body?: unknown, signal?: AbortSignal) => {
    try {
      return await fetch(base + path, {
        method,
        signal,
        headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      return new Response(JSON.stringify({ detail: "Can't reach the engine." }), { status: 503 });
    }
  };
  return {
    async send(method, path, body) {
      const response = await request(method, path, body);
      return { status: response.status, body: response.status === 204 ? "" : await response.text() };
    },
    async stream(path, body, onLine, signal) {
      const response = await request("POST", path, body, signal);
      if (!response.ok || !response.body) return { status: response.status, body: await response.text() };
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      const lines = new LineSplitter();
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        lines.push(value).forEach(onLine);
      }
      lines.flush().forEach(onLine);
      return { status: response.status, body: "" };
    },
  };
}
