import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EngineApi } from "../lib/api";
import { clearChat, historyOf, loadChat, saveChat } from "../lib/chats";
import type { ChatMessage, Scope } from "../lib/types";

const newId = () => crypto.randomUUID();
const SAVE_DELAY_MS = 400;

const keyOf = (scope: Scope | null) => (scope ? `${scope.kind}:${scope.id}` : "");
const scopeOf = (key: string): Scope | null => {
  const [kind, id] = key.split(":");
  return kind === "section" || kind === "category" ? { kind, id } : null;
};

/** Messages together with the conversation they belong to, so they can never be saved under another one. */
type Conversation = { key: string; messages: ChatMessage[] };

/** One conversation per section or category: streams answers in, keeps them on this computer.
 *
 * A reply that arrives after the user moved to another section (an aborted or finished answer) is dropped, because
 * every change names the conversation it is for. */
export function useChat(api: EngineApi | null, scope: Scope | null) {
  const scopeKey = keyOf(scope);
  const [conversation, setConversation] = useState<Conversation>({ key: "", messages: [] });
  const [busy, setBusy] = useState(false);
  const running = useRef<AbortController | null>(null);

  // A new scope, or a restarted engine: stop what is running and load that scope's conversation.
  useEffect(() => {
    running.current?.abort();
    running.current = null;
    setBusy(false);
    const target = scopeOf(scopeKey);
    setConversation({ key: scopeKey, messages: target ? loadChat(localStorage, target) : [] });
  }, [scopeKey, api]);

  // Save after changes settle (not on every streamed token), under the conversation's own key.
  useEffect(() => {
    const target = scopeOf(conversation.key);
    if (!target) return;
    const timer = setTimeout(() => saveChat(localStorage, target, conversation.messages), SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [conversation]);

  const messages = useMemo(
    () => (conversation.key === scopeKey ? conversation.messages : []),
    [conversation, scopeKey],
  );

  const send = useCallback(
    async (question: string) => {
      if (!api || !scope || running.current || !question.trim()) return;
      const key = scopeKey;
      const history = historyOf(messages);
      const answerId = newId();
      const controller = new AbortController();
      running.current = controller;
      setBusy(true);
      const update = (change: (all: ChatMessage[]) => ChatMessage[]) =>
        setConversation((c) => (c.key === key ? { key, messages: change(c.messages) } : c));
      const patch = (change: (m: Extract<ChatMessage, { role: "assistant" }>) => ChatMessage) =>
        update((all) => all.map((m) => (m.id === answerId && m.role === "assistant" ? change(m) : m)));
      update((all) => [
        ...all,
        { id: newId(), role: "user", text: question.trim() },
        { id: answerId, role: "assistant", text: "", status: "streaming" },
      ]);
      try {
        const answer = await api.ask(scope, question.trim(), history, (token) => patch((m) => ({ ...m, text: m.text + token })), controller.signal);
        patch((m) => ({ ...m, text: answer.text, status: "done", answer }));
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          patch((m) => ({ ...m, status: "stopped" }));
        } else {
          patch((m) => ({ ...m, status: "error", error: error instanceof Error ? error.message : String(error) }));
        }
      } finally {
        if (running.current === controller) {
          running.current = null;
          setBusy(false);
        }
      }
    },
    [api, scope, scopeKey, messages],
  );

  const stop = useCallback(() => running.current?.abort(), []);

  const clear = useCallback(() => {
    const target = scopeOf(scopeKey);
    if (!target) return;
    clearChat(localStorage, target);
    setConversation({ key: scopeKey, messages: [] });
  }, [scopeKey]);

  return { messages, busy, send, stop, clear };
}
