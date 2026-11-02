import { AlertCircle, BookOpen, Pencil, Trash2, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import type { Section } from "../lib/types";
import { Chip, IconButton, Spinner } from "./primitives";

export function MainHeader({ title, subtitle, chip, onRename, onDelete }: {
  title: string;
  subtitle: string;
  chip?: ReactNode;
  onRename: () => void;
  onDelete: () => void;
}) {
  return (
    <header className="flex items-center gap-3 border-b-[2.5px] border-edge px-6 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-[26px] leading-tight">{title}</h1>
          {chip}
        </div>
        <div className="truncate text-[13px] text-ink-2">{subtitle}</div>
      </div>
      <IconButton label="Rename" onClick={onRename}>
        <Pencil className="size-4" />
      </IconButton>
      <IconButton label="Delete" onClick={onDelete}>
        <Trash2 className="size-4" />
      </IconButton>
    </header>
  );
}

export function CategoryPanel({ sections, onSelect }: { sections: Section[]; onSelect: (id: string) => void }) {
  return (
    <aside className="flex w-80 shrink-0 flex-col gap-2.5 overflow-y-auto border-l-[2.5px] border-edge bg-card-2 p-4">
      <h3 className="font-mono text-[11.5px] font-semibold tracking-[0.1em] text-ink-2 uppercase">Sections in this category</h3>
      <p className="text-[13px] leading-snug text-ink-2">Questions here search all of them together.</p>
      {sections.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onSelect(s.id)}
          className="sticker-sm press flex items-center gap-2.5 px-3 py-2 text-left"
        >
          <BookOpen className="size-4 shrink-0 text-accent" />
          <span className="min-w-0 flex-1 truncate text-[14px] font-bold">{s.name}</span>
          {s.status.state === "indexing" ? (
            <Spinner className="size-3.5 text-accent" />
          ) : s.status.state === "error" ? (
            <AlertCircle className="size-4 text-bad" />
          ) : (
            <Chip>{s.documents} docs</Chip>
          )}
        </button>
      ))}
    </aside>
  );
}

export function Toast({ message, onClose }: { message: string | null; onClose: () => void }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          role="alert"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 16 }}
          className="sticker fixed bottom-6 left-1/2 z-40 flex max-w-lg -translate-x-1/2 items-start gap-2 bg-sun px-4 py-2.5 text-[14px] font-bold text-[#17183a]"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span className="selectable">{message}</span>
          <IconButton label="Dismiss" className="-my-1 size-6" onClick={onClose}>
            <X className="size-3.5" />
          </IconButton>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
