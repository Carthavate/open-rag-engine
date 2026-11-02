import { AlertTriangle, FileText, FolderOpen, FolderPlus, RefreshCw, X } from "lucide-react";
import type { DocumentInfo, Section } from "../lib/types";
import { fileName, shortFolder } from "../lib/text";
import { Button, IconButton, ProgressBar, Spinner } from "./primitives";

type Props = {
  section: Section;
  documents: DocumentInfo[] | null;
  onAddFolder: () => void;
  onRemoveFolder: (path: string) => void;
  onIndex: () => void;
  onOpenDocument: (path: string) => void;
};

export function SectionPanel({ section, documents, onAddFolder, onRemoveFolder, onIndex, onOpenDocument }: Props) {
  const { status } = section;
  const missing = new Set(status.missing_folders);
  return (
    <aside className="flex w-80 shrink-0 flex-col gap-3 overflow-y-auto border-l-[2.5px] border-edge bg-card-2 p-4">
      <PanelTitle title="Folders" action={<Button icon={<FolderPlus className="size-3.5" />} onClick={onAddFolder}>Add</Button>} />
      {section.folders.length === 0 ? (
        <button
          type="button"
          onClick={onAddFolder}
          className="rounded-xl border-[2.5px] border-dashed border-edge bg-card px-4 py-5 text-center text-[13.5px] font-bold text-ink hover:bg-sun hover:text-[#17183a]"
        >
          Add a folder with this section's documents.
          <span className="mt-1 block text-[12px] font-normal text-ink-2">PDF, Markdown and text files, including subfolders.</span>
        </button>
      ) : (
        <ul className="space-y-1">
          {section.folders.map((folder) => (
            <li key={folder} className="sticker-sm group flex items-center gap-2 px-2.5 py-1.5" title={folder}>
              <FolderOpen className={`size-4 shrink-0 ${missing.has(folder) ? "text-tomato" : "text-accent"}`} strokeWidth={2.4} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] font-bold">{shortFolder(folder)}</div>
                {missing.has(folder) && <div className="text-[11.5px] text-tomato">Not found right now (unplugged?)</div>}
              </div>
              <IconButton label="Remove folder" className="size-6 opacity-0 group-hover:opacity-100" onClick={() => onRemoveFolder(folder)}>
                <X className="size-3.5" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}

      <IndexCard section={section} onIndex={onIndex} />

      <PanelTitle title={`Documents${section.documents ? ` · ${section.documents}` : ""}`} />
      {documents === null ? (
        <Spinner className="mx-auto size-4 text-ink-3" />
      ) : documents.length === 0 ? (
        <p className="text-[13px] text-ink-2">Nothing indexed yet.</p>
      ) : (
        <ul className="-mx-1 space-y-0.5">
          {documents.map((doc) => (
            <li key={doc.source}>
              <button
                type="button"
                title={doc.source}
                onClick={() => onOpenDocument(doc.source)}
                className="flex w-full items-center gap-2 rounded-lg px-1.5 py-1 text-left text-[13px] hover:bg-card"
              >
                <FileText className="size-3.5 shrink-0 text-ink-2" />
                <span className="min-w-0 flex-1 truncate">{doc.name}</span>
                <span className="font-mono text-[11px] font-semibold text-ink-2 tabular-nums">{doc.chunks}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

function PanelTitle({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="font-mono text-[11.5px] font-semibold tracking-[0.1em] text-ink-2 uppercase">{title}</h3>
      {action}
    </div>
  );
}

function IndexCard({ section, onIndex }: { section: Section; onIndex: () => void }) {
  const { status } = section;
  if (status.state === "indexing") {
    const progress = status.total ? status.done / status.total : 0;
    return (
      <div className="sticker-sm p-3">
        <div className="flex items-center gap-2 text-[13px] font-bold text-accent">
          <Spinner className="size-3.5" /> Indexing{status.total ? ` ${status.done} of ${status.total}` : "…"}
        </div>
        <div className="mt-2">
          <ProgressBar value={progress} />
        </div>
        {status.current && <div className="mt-1.5 truncate font-mono text-[11.5px] text-ink-2">{fileName(status.current)}</div>}
      </div>
    );
  }
  if (status.state === "error") {
    return (
      <div className="rounded-xl border-2 border-bad bg-bad-tint p-3 text-[13px] text-bad">
        <div className="flex items-center gap-1.5 font-bold">
          <AlertTriangle className="size-4" /> Indexing failed
        </div>
        <p className="mt-1 text-[12px] leading-snug">{status.error}</p>
        <Button className="mt-2" onClick={onIndex}>Try again</Button>
      </div>
    );
  }
  const report = status.report;
  const never = !report && section.documents === 0;
  return (
    <div className="sticker-sm p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[13px] font-bold text-ink">
          {never ? "Not indexed yet." : `${section.documents} ${section.documents === 1 ? "document" : "documents"} ready.`}
        </div>
        <Button
          variant={never ? "primary" : "secondary"}
          disabled={section.folders.length === 0}
          icon={<RefreshCw className="size-3.5" />}
          onClick={onIndex}
        >
          {never ? "Index" : "Update"}
        </Button>
      </div>
      {report && (
        <div className="mt-1.5 text-[12px] text-ink-2">
          Last update: {report.added} new, {report.updated} changed, {report.removed} removed
          {report.failed.length > 0 && (
            <details className="mt-1 text-tomato">
              <summary className="cursor-pointer">{report.failed.length} couldn't be read</summary>
              <ul className="mt-1 space-y-0.5">
                {report.failed.map((f) => (
                  <li key={f.source} title={f.error}>
                    {fileName(f.source)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
