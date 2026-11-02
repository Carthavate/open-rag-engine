/** The bridge to the Open RAG window (WPF + WebView2). The page reaches the engine only through the window: API calls
 * and questions travel as messages, and the window forwards them with the engine's token, which the page never sees.
 * In a normal browser it falls back to the mock engine, or to a real `ore serve` given as ?api=...&token=... */

import { httpTransport, type Reply, type Transport } from "./api";

export type EngineState =
  | { state: "starting" }
  | { state: "ready"; transport: Transport | "mock" }
  | { state: "failed"; message: string };

export interface Host {
  readonly isDesktop: boolean;
  onEngine(listener: (state: EngineState) => void): () => void;
  onNotice(listener: (message: string) => void): () => void;
  pickFolder(): Promise<string | null>;
  openSource(path: string): void;
  revealSource(path: string): void;
  restartEngine(): void;
  /** Opens a web page in the default browser; the window opens only the links on its own list. */
  openLink(url: string): void;
  /** The custom title bar's buttons; only the desktop window has them. */
  windowAction(action: "minimize" | "maximize" | "close"): void;
  onWindowState(listener: (maximized: boolean) => void): () => void;
}

interface WebViewBridge {
  postMessage(message: unknown): void;
  addEventListener(type: "message", listener: (e: MessageEvent) => void): void;
  removeEventListener(type: "message", listener: (e: MessageEvent) => void): void;
}

declare global {
  interface Window {
    chrome?: { webview?: WebViewBridge };
  }
}

type HostMessage =
  | { type: "engine"; state: "starting" | "ready" | "failed"; message?: string }
  | { type: "folderPicked"; id: string; path: string | null }
  | { type: "notice"; message: string }
  | { type: "windowState"; maximized: boolean }
  | { type: "apiResult"; id: string; status: number; body: string }
  | { type: "askLine"; id: string; line: string }
  | { type: "askEnd"; id: string; status: number; body: string };

/** Library calls are quick; one that takes this long means the engine is stuck. Answers stream and have no limit. */
const API_TIMEOUT_MS = 120_000;

function desktopHost(bridge: WebViewBridge): Host {
  const listen = (handler: (m: HostMessage) => void) => {
    const listener = (e: MessageEvent) => handler(e.data as HostMessage);
    bridge.addEventListener("message", listener);
    return () => bridge.removeEventListener("message", listener);
  };

  /** Sends a message and resolves with the first reply that carries the same id. */
  const request = <T extends HostMessage>(message: Record<string, unknown>, isReply: (m: HostMessage, id: string) => m is T) => {
    const id = crypto.randomUUID();
    return new Promise<T>((resolve) => {
      const stop = listen((m) => {
        if (m && isReply(m, id)) {
          stop();
          resolve(m);
        }
      });
      bridge.postMessage({ ...message, id });
    });
  };

  const timedOut: Reply = { status: 504, body: '{"detail":"The engine took too long to answer. Try again."}' };

  const transport: Transport = {
    async send(method, path, body) {
      const reply = await Promise.race([
        request(
          { type: "api", method, path, body: body ?? null },
          (m, id): m is Extract<HostMessage, { type: "apiResult" }> => m.type === "apiResult" && m.id === id,
        ),
        new Promise<null>((resolve) => setTimeout(() => resolve(null), API_TIMEOUT_MS)),
      ]);
      return reply ? { status: reply.status, body: reply.body } : timedOut;
    },
    stream(_path, body, onLine, signal) {
      const id = crypto.randomUUID();
      return new Promise<Reply>((resolve) => {
        const cancel = () => bridge.postMessage({ type: "cancel", id });
        const stop = listen((m) => {
          if (m?.type === "askLine" && m.id === id) onLine(m.line);
          if (m?.type === "askEnd" && m.id === id) {
            stop();
            signal?.removeEventListener("abort", cancel);
            resolve({ status: m.status, body: m.body });
          }
        });
        signal?.addEventListener("abort", cancel);
        bridge.postMessage({ type: "ask", id, body });
      });
    },
  };

  return {
    isDesktop: true,
    onEngine(listener) {
      const stop = listen((m) => {
        if (m?.type !== "engine") return;
        if (m.state === "ready") listener({ state: "ready", transport });
        else if (m.state === "failed") listener({ state: "failed", message: m.message ?? "The engine couldn't start." });
        else listener({ state: "starting" });
      });
      bridge.postMessage({ type: "ready" });
      return stop;
    },
    onNotice: (listener) => listen((m) => m?.type === "notice" && listener(m.message)),
    async pickFolder() {
      const reply = await request(
        { type: "pickFolder" },
        (m, id): m is Extract<HostMessage, { type: "folderPicked" }> => m.type === "folderPicked" && m.id === id,
      );
      return reply.path;
    },
    openSource: (path) => bridge.postMessage({ type: "openSource", path }),
    revealSource: (path) => bridge.postMessage({ type: "revealSource", path }),
    restartEngine: () => bridge.postMessage({ type: "restartEngine" }),
    openLink: (url) => bridge.postMessage({ type: "openLink", url }),
    windowAction: (action) => bridge.postMessage({ type: "window", action }),
    onWindowState: (listener) => listen((m) => m?.type === "windowState" && listener(m.maximized)),
  };
}

function browserHost(): Host {
  const params = new URLSearchParams(window.location.search);
  const api = params.get("api");
  const token = params.get("token");
  const engine: EngineState = { state: "ready", transport: api && token ? httpTransport(api, token) : "mock" };
  return {
    isDesktop: false,
    onEngine(listener) {
      listener(engine);
      return () => {};
    },
    onNotice: () => () => {},
    pickFolder: async () => window.prompt("Folder path (browser preview)") || null,
    openSource: (path) => window.alert(`Would open ${path}`),
    revealSource: (path) => window.alert(`Would show ${path} in Explorer`),
    restartEngine: () => window.location.reload(),
    openLink: (url) => window.open(url, "_blank", "noopener,noreferrer"),
    windowAction: () => {},
    onWindowState: () => () => {},
  };
}

export const host: Host = window.chrome?.webview ? desktopHost(window.chrome.webview) : browserHost();
