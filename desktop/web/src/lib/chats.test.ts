import { describe, expect, it } from "vitest";
import { chatKey, clearChat, historyOf, loadChat, saveChat, type KeyValueStore } from "./chats";
import type { ChatMessage } from "./types";

function memory(): KeyValueStore & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => void data.set(k, v),
    removeItem: (k) => void data.delete(k),
  };
}

const scope = { kind: "section", id: "abc" } as const;
const user = (text: string): ChatMessage => ({ id: text, role: "user", text });
const bot = (text: string, status: "done" | "streaming" | "error" = "done"): ChatMessage => ({
  id: `a-${text}`,
  role: "assistant",
  text,
  status,
});

describe("chats", () => {
  it("saves finished messages per scope and loads them back", () => {
    const store = memory();
    saveChat(store, scope, [user("q1"), bot("a1"), user("q2"), bot("…", "streaming")]);
    expect(loadChat(store, scope).map((m) => m.text)).toEqual(["q1", "a1", "q2"]);
    expect(loadChat(store, { kind: "category", id: "abc" })).toEqual([]);
    clearChat(store, scope);
    expect(store.data.has(chatKey(scope))).toBe(false);
  });

  it("survives corrupt storage", () => {
    const store = memory();
    store.setItem(chatKey(scope), "{not json");
    expect(loadChat(store, scope)).toEqual([]);
  });

  it("builds history only from completed exchanges", () => {
    const history = historyOf([user("q1"), bot("a1"), user("q2"), bot("x", "error"), user("q3"), bot("a3")]);
    expect(history).toEqual([
      { question: "q1", answer: "a1" },
      { question: "q3", answer: "a3" },
    ]);
  });
});
