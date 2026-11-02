import { useCallback, useEffect, useRef, useState } from "react";
import type { EngineApi } from "../lib/api";
import { clearChat, historyOf, loadChat, saveChat } from "../lib/chats";
import type { ChatMessage, Scope } from "../lib/types";

const newId = () => crypto.randomUUID();

/** One conversation per section or category: streams answers in, keeps them on this computer. */
export function useChat(api: EngineApi | null, scope: Scope | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scopeKey = scope ? `${scope.kind}:${scope.id}` : "";

  useEffect(() => {
    abortRef.current?.abort();
    setBusy(false);
    setMessages(scope ? loadChat(localStorage, scope) : []);
    // scopeKey captures the scope's identity; the object itself changes on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeKey]);

  const update = useCallback(
    (change: (messages: ChatMessage[]) => ChatMessage[]) => {
      setMessages((current) => {
        const next = change(current);
        if (scope) saveChat(localStorage, scope, next);
        return next;
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scopeKey],
  );

  const send = useCallback(
    async (question: string) => {
      if (!api || !scope || busy || !question.trim()) return;
      const history = historyOf(messages);
      const answerId = newId();
      update((m) => [
        ...m,
        { id: newId(), role: "user", text: question.trim() },
        { id: answerId, role: "assistant", text: "", status: "streaming" },
      ]);
      const patch = (change: (m: Extract<ChatMessage, { role: "assistant" }>) => ChatMessage) =>
        update((all) => all.map((m) => (m.id === answerId && m.role === "assistant" ? change(m) : m)));
      const controller = new AbortController();
      abortRef.current = controller;
      setBusy(true);
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
        setBusy(false);
        abortRef.current = null;
      }
    },
    [api, scope, busy, messages, update],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const clear = useCallback(() => {
    if (!scope) return;
    clearChat(localStorage, scope);
    setMessages([]);
  }, [scope]);

  return { messages, busy, send, stop, clear };
}
