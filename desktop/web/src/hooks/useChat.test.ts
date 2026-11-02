// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { EngineApi } from "../lib/api";
import { chatKey, saveChat } from "../lib/chats";
import type { AnswerDone, ChatMessage, Scope } from "../lib/types";
import { useChat } from "./useChat";

const A: Scope = { kind: "section", id: "a" };
const B: Scope = { kind: "section", id: "b" };

function answer(text: string): AnswerDone {
  return { type: "done", question: "q", text, abstained: false, grounded: true, invalid_citations: [], citations: [], sources: [] };
}

/** An engine whose answers wait until the test releases them, so a reply can arrive after a scope switch. */
function slowEngine() {
  const pending: ((text: string) => void)[] = [];
  const api = {
    ask: (_scope: Scope, _q: string, _h: unknown, onToken: (t: string) => void) =>
      new Promise<AnswerDone>((resolve) =>
        pending.push((text) => {
          onToken(text);
          resolve(answer(text));
        }),
      ),
  } as unknown as EngineApi;
  return { api, release: (text: string) => pending.shift()?.(text) };
}

const saved = (scope: Scope) => JSON.parse(localStorage.getItem(chatKey(scope)) ?? "[]") as ChatMessage[];

afterEach(() => localStorage.clear());

describe("useChat", () => {
  it("streams an answer into the current conversation and saves it", async () => {
    const { api, release } = slowEngine();
    const { result } = renderHook(() => useChat(api, A));
    let sending!: Promise<void>;
    act(() => {
      sending = result.current.send("power?");
    });
    expect(result.current.busy).toBe(true);
    await act(async () => {
      release("1.2 kW [1].");
      await sending;
    });
    expect(result.current.busy).toBe(false);
    expect(result.current.messages.map((m) => m.text)).toEqual(["power?", "1.2 kW [1]."]);
    await waitFor(() => expect(saved(A).map((m) => m.text)).toEqual(["power?", "1.2 kW [1]."]));
  });

  it("a late reply never lands in, or overwrites, another section's conversation", async () => {
    saveChat(localStorage, B, [{ id: "b1", role: "user", text: "B's question" }]);
    const { api, release } = slowEngine();
    const { result, rerender } = renderHook(({ scope }) => useChat(api, scope), { initialProps: { scope: A } });
    let sending!: Promise<void>;
    act(() => {
      sending = result.current.send("A's question");
    });
    rerender({ scope: B });
    await act(async () => {
      release("A's answer");
      await sending;
    });
    expect(result.current.messages.map((m) => m.text)).toEqual(["B's question"]);
    expect(result.current.busy).toBe(false);
    await new Promise((r) => setTimeout(r, 500));
    expect(saved(B).map((m) => m.text)).toEqual(["B's question"]);
    expect(saved(A).every((m) => m.text !== "B's question")).toBe(true);
  });
});
