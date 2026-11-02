import { AlertTriangle, ExternalLink, FolderSearch, Info } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { splitCitations } from "../lib/text";
import type { ChatMessage, Source } from "../lib/types";
import { Chip, IconButton } from "./primitives";

type SourceActions = { onOpen: (source: Source) => void; onReveal: (source: Source) => void };

export function MessageView({ message, ...actions }: { message: ChatMessage } & SourceActions) {
  if (message.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="selectable max-w-[75%] rounded-[18px] rounded-br-md border-[2.5px] border-edge bg-accent px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap text-on-accent shadow-[3px_3px_0_var(--shadow)]">
          {message.text}
        </div>
      </motion.div>
    );
  }
  const { answer, status } = message;
  const sources = answer?.sources ?? [];
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="max-w-[86%]">
      <div className="selectable text-[15.5px] leading-[1.7] whitespace-pre-wrap text-ink">
        {status === "streaming" && !message.text && <span className="text-ink-3">Searching your documents…</span>}
        {splitCitations(message.text).map((part, i) =>
          part.kind === "text" ? (
            <span key={i}>{part.text}</span>
          ) : (
            part.numbers.map((n) => <CitationPill key={`${i}-${n}`} number={n} source={sources[n - 1]} onOpen={actions.onOpen} />)
          ),
        )}
        {status === "streaming" && message.text && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse rounded-sm bg-sun align-middle" />}
      </div>
      {status === "error" && (
        <div className="mt-2 flex items-start gap-2 rounded-xl border-2 border-bad bg-bad-tint px-3 py-2 text-[13.5px] font-bold text-bad">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          {message.error}
        </div>
      )}
      {status === "stopped" && <div className="mt-1 text-[12px] text-ink-3">Stopped.</div>}
      {answer && <AnswerNotes abstained={answer.abstained} grounded={answer.grounded} invalid={answer.invalid_citations} />}
      {answer && answer.sources.length > 0 && !answer.abstained && <Sources answerSources={answer.sources} cited={answer.citations} {...actions} />}
    </motion.div>
  );
}

function CitationPill({ number, source, onOpen }: { number: number; source?: Source; onOpen: (s: Source) => void }) {
  return (
    <button
      type="button"
      disabled={!source}
      onClick={() => source && onOpen(source)}
      title={source ? `${source.label}${source.page ? `, page ${source.page}` : ""}` : "Unknown source"}
      className="mx-0.5 inline-grid h-[20px] min-w-[20px] -translate-y-px place-items-center rounded-full border-2 border-edge bg-sun px-1 align-middle font-mono text-[11px] font-semibold text-[#17183a] transition hover:bg-tomato hover:text-white"
    >
      {number}
    </button>
  );
}

function AnswerNotes({ abstained, grounded, invalid }: { abstained: boolean; grounded: boolean; invalid: number[] }) {
  if (abstained) {
    return (
      <div className="mt-2">
        <Chip>
          <Info className="size-3" /> Not found in your documents
        </Chip>
      </div>
    );
  }
  if (invalid.length > 0) {
    return (
      <div className="mt-2">
        <Chip tone="warn">
          <AlertTriangle className="size-3" /> Cites a source that doesn't exist: check this answer
        </Chip>
      </div>
    );
  }
  if (!grounded) {
    return (
      <div className="mt-2">
        <Chip tone="warn">
          <AlertTriangle className="size-3" /> No source cited: check this answer
        </Chip>
      </div>
    );
  }
  return null;
}

function Sources({ answerSources, cited, onOpen, onReveal }: { answerSources: Source[]; cited: Source[] } & SourceActions) {
  const [all, setAll] = useState(false);
  const shown = all || cited.length === 0 ? answerSources : cited;
  const hidden = answerSources.length - shown.length;
  return (
    <div className="mt-3 space-y-1.5">
      {shown.map((source) => (
        <div key={source.number} className="group flex items-start gap-2.5 rounded-xl border-2 border-edge bg-card-2 px-3 py-2">
          <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border-2 border-edge bg-sun font-mono text-[11px] font-semibold text-[#17183a]">
            {source.number}
          </span>
          <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onOpen(source)}>
            <div className="truncate text-[13.5px] font-bold text-ink">
              {source.label}
            </div>
            <div className="line-clamp-2 text-[12.5px] leading-snug text-ink-2">{source.snippet}</div>
          </button>
          <div className="flex shrink-0 opacity-0 transition group-hover:opacity-100">
            <IconButton label="Open document" onClick={() => onOpen(source)}>
              <ExternalLink className="size-3.5" />
            </IconButton>
            <IconButton label="Show in folder" onClick={() => onReveal(source)}>
              <FolderSearch className="size-3.5" />
            </IconButton>
          </div>
        </div>
      ))}
      {hidden > 0 && (
        <button type="button" onClick={() => setAll(true)} className="px-1 text-[13px] font-bold text-accent underline-offset-2 hover:underline">
          Show {hidden} more {hidden === 1 ? "passage" : "passages"} it read
        </button>
      )}
    </div>
  );
}
