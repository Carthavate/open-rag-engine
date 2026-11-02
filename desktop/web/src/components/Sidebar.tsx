import { AlertCircle, BookOpen, ChevronRight, FolderClosed, Pencil, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import type { Category, Library, Scope, Section } from "../lib/types";
import { IconButton, Spinner } from "./primitives";

type Props = {
  library: Library | null;
  selection: Scope | null;
  onSelect: (scope: Scope) => void;
  onNewCategory: () => void;
  onNewSection: (category: Category) => void;
  onRenameCategory: (category: Category) => void;
  onDeleteCategory: (category: Category) => void;
};

export function Sidebar(props: Props) {
  const { library, onNewCategory } = props;
  return (
    <aside className="sticker m-3 mr-0 flex w-72 shrink-0 flex-col rounded-[20px]">
      <div className="flex items-center justify-between px-4 pt-4 pb-1">
        <span className="font-mono text-[11.5px] font-semibold tracking-[0.1em] text-ink-2 uppercase">Library</span>
        <IconButton label="New category" onClick={onNewCategory}>
          <Plus className="size-4" />
        </IconButton>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {library?.categories.map((category) => (
          <CategoryGroup
            key={category.id}
            category={category}
            sections={library.sections.filter((s) => s.category_id === category.id)}
            {...props}
          />
        ))}
        {library && library.categories.length === 0 && (
          <p className="px-3 py-2 text-[13px] leading-relaxed text-ink-2">
            Create a category, such as a subject or a research area, to start.
          </p>
        )}
      </nav>
      <footer className="m-3 flex items-center gap-2 rounded-xl border-2 border-edge bg-done px-3 py-2 text-[12px] font-bold text-ink">
        <ShieldCheck className="size-4 shrink-0 text-mint" />
        Offline. Nothing leaves this computer.
      </footer>
    </aside>
  );
}

function CategoryGroup({
  category,
  sections,
  selection,
  onSelect,
  onNewSection,
  onRenameCategory,
  onDeleteCategory,
}: Props & { category: Category; sections: Section[] }) {
  const [open, setOpen] = useState(true);
  const selected = selection?.kind === "category" && selection.id === category.id;
  return (
    <div className="mb-1">
      <div
        className={`group flex h-9 items-center gap-1 rounded-xl border-2 pr-1 pl-1 transition ${selected ? "border-edge bg-accent text-on-accent" : "border-transparent hover:bg-card-2"}`}
      >
        <IconButton label={open ? "Collapse" : "Expand"} className="size-6" onClick={() => setOpen(!open)}>
          <ChevronRight className={`size-3.5 transition ${open ? "rotate-90" : ""}`} />
        </IconButton>
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-[14px] font-bold"
          onClick={() => onSelect({ kind: "category", id: category.id })}
          title="Ask across every section in this category"
        >
          <FolderClosed className="size-4 shrink-0 opacity-70" />
          <span className="truncate">{category.name}</span>
        </button>
        <div className="hidden group-focus-within:flex group-hover:flex">
          <IconButton label="New section" className="size-6" onClick={() => onNewSection(category)}>
            <Plus className="size-3.5" />
          </IconButton>
          <IconButton label="Rename category" className="size-6" onClick={() => onRenameCategory(category)}>
            <Pencil className="size-3.5" />
          </IconButton>
          <IconButton label="Delete category" className="size-6" onClick={() => onDeleteCategory(category)}>
            <Trash2 className="size-3.5" />
          </IconButton>
        </div>
      </div>
      {open && (
        <div className="mt-0.5 space-y-0.5 pl-5">
          {sections.map((section) => (
            <SectionRow
              key={section.id}
              section={section}
              selected={selection?.kind === "section" && selection.id === section.id}
              onClick={() => onSelect({ kind: "section", id: section.id })}
            />
          ))}
          {sections.length === 0 && (
            <button
              type="button"
              onClick={() => onNewSection(category)}
              className="flex h-8 w-full items-center gap-2 rounded-lg px-2 text-[13px] text-ink-2 hover:bg-card-2 hover:text-ink"
            >
              <Plus className="size-3.5" /> Add a section
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function SectionRow({ section, selected, onClick }: { section: Section; selected: boolean; onClick: () => void }) {
  const { state } = section.status;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-9 w-full items-center gap-2 rounded-xl border-2 px-2 text-left text-[14px] transition ${selected ? "border-edge bg-sun font-bold text-[#17183a] shadow-[2px_2px_0_var(--shadow)]" : "border-transparent text-ink hover:bg-card-2"}`}
    >
      <BookOpen className={`size-4 shrink-0 ${selected ? "" : "text-accent"}`} strokeWidth={2.4} />
      <span className="min-w-0 flex-1 truncate">{section.name}</span>
      {state === "indexing" ? (
        <Spinner className="size-3.5" />
      ) : state === "error" ? (
        <AlertCircle className={`size-4 ${selected ? "" : "text-bad"}`} aria-label="Indexing failed" />
      ) : (
        <span className={`font-mono text-[11.5px] font-semibold tabular-nums ${selected ? "text-[#17183a]" : "text-ink-2"}`}>{section.documents || ""}</span>
      )}
    </button>
  );
}
