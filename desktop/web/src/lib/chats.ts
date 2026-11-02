import type { ChatMessage, Scope, Turn } from "./types";

const MAX_SAVED = 60;
const HISTORY_TURNS = 6;

/** Minimal storage interface so tests can pass a fake. */
export type KeyValueStore = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export const chatKey = (scope: Scope) => `openrag.chat.${scope.kind}.${scope.id}`;

/** Conversations are kept per section or category on this computer, so they survive restarts. */
export function loadChat(store: KeyValueStore, scope: Scope): ChatMessage[] {
  try {
    const raw = store.getItem(chatKey(scope));
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

export function saveChat(store: KeyValueStore, scope: Scope, messages: ChatMessage[]): void {
  const finished = messages.filter((m) => m.role === "user" || m.status !== "streaming").slice(-MAX_SAVED);
  try {
    store.setItem(chatKey(scope), JSON.stringify(finished));
  } catch {
    // Storage full or unavailable: the conversation still works, it just isn't kept.
  }
}

export function clearChat(store: KeyValueStore, scope: Scope): void {
  try {
    store.removeItem(chatKey(scope));
  } catch {
    // Nothing to clear.
  }
}

/** The last few completed question/answer pairs, so follow-up questions can be understood. */
export function historyOf(messages: ChatMessage[]): Turn[] {
  const turns: Turn[] = [];
  for (let i = 0; i < messages.length - 1; i++) {
    const asked = messages[i];
    const answered = messages[i + 1];
    if (asked.role === "user" && answered.role === "assistant" && answered.status === "done") {
      turns.push({ question: asked.text, answer: answered.text });
    }
  }
  return turns.slice(-HISTORY_TURNS);
}
