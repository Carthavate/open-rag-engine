import { ArrowUp, MessagesSquare, Square, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChatMessage, Source } from "../lib/types";
import { MessageView } from "./Message";
import { IconButton } from "./primitives";

const IDEAS = ["Summarise the key points", "Explain the main idea in simple terms", "What are the important definitions?"];

type Props = {
  title: string;
  messages: ChatMessage[];
  busy: boolean;
  blocked: string | null;
  onSend: (question: string) => void;
  onStop: () => void;
  onClear: () => void;
  onOpen: (source: Source) => void;
  onReveal: (source: Source) => void;
};

export function Chat({ title, messages, busy, blocked, onSend, onStop, onClear, onOpen, onReveal }: Props) {
  const [draft, setDraft] = useState("");
  const list = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [draft]);

  const send = () => {
    if (!draft.trim() || busy || blocked) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={list} className="min-h-0 flex-1 overflow-y-auto px-6 pt-5 pb-2">
        {messages.length === 0 ? (
          <Empty title={title} blocked={blocked} onIdea={(idea) => setDraft(idea)} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.map((m) => (
              <MessageView key={m.id} message={m} onOpen={onOpen} onReveal={onReveal} />
            ))}
          </div>
        )}
      </div>
      <div className="px-6 pt-1 pb-5">
        <div className="mx-auto max-w-3xl">
          {blocked && (
            <div className="mb-2 inline-block rounded-lg border-2 border-edge bg-sun px-2.5 py-1 text-[12.5px] font-bold text-[#17183a]">
              {blocked}
            </div>
          )}
          <div className="sticker flex items-end gap-2 rounded-[18px] p-2 pl-4 transition-shadow focus-within:border-accent focus-within:shadow-[4px_4px_0_var(--cobalt)]">
            <textarea
              ref={box}
              rows={1}
              value={draft}
              disabled={Boolean(blocked)}
              placeholder={`Ask about ${title}`}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              className="max-h-40 min-h-6 flex-1 resize-none bg-transparent py-1.5 text-[15px] leading-6 text-ink outline-none placeholder:text-ink-3 focus-visible:outline-none disabled:opacity-50"
            />
            {messages.length > 0 && !busy && (
              <IconButton label="Clear conversation" onClick={onClear} className="size-8">
                <Trash2 className="size-4" />
              </IconButton>
            )}
            {busy ? (
              <button type="button" aria-label="Stop" onClick={onStop} className="grid size-9 place-items-center rounded-full border-2 border-edge bg-tomato text-white">
                <Square className="size-3 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                aria-label="Ask"
                onClick={send}
                disabled={!draft.trim() || Boolean(blocked)}
                className="grid size-9 place-items-center rounded-full border-2 border-edge bg-accent text-on-accent shadow-[2px_2px_0_var(--shadow)] transition disabled:border-line disabled:bg-card-2 disabled:text-ink-3 disabled:shadow-none"
              >
                <ArrowUp className="size-4" strokeWidth={2.5} />
              </button>
            )}
          </div>
          <div className="mt-2 px-1 text-[12px] text-ink-2">Answers come only from your documents, with sources. Check important facts.</div>
        </div>
      </div>
    </div>
  );
}

function Empty({ title, blocked, onIdea }: { title: string; blocked: string | null; onIdea: (idea: string) => void }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="max-w-md text-center">
        <div className="sticker mx-auto grid size-14 -rotate-6 place-items-center bg-sun text-[#17183a]">
          <MessagesSquare className="size-7" strokeWidth={2.4} />
        </div>
        <h2 className="mt-4 text-[26px]">Ask about {title}</h2>
        <p className="mt-1 text-[14px] text-ink-2">Every answer is built from these documents, with numbered sources you can open.</p>
        {!blocked && (
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {IDEAS.map((idea) => (
              <button
                key={idea}
                type="button"
                onClick={() => onIdea(idea)}
                className="sticker-sm press rounded-full px-3.5 py-1.5 text-[13px] font-bold text-ink"
              >
                {idea}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
