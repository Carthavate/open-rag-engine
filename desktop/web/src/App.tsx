import { useCallback, useEffect, useMemo, useState } from "react";
import { Chat } from "./components/Chat";
import { ConfirmDialog, NameDialog, type ConfirmRequest, type NameRequest } from "./components/Dialogs";
import { CategoryPanel, MainHeader, Toast } from "./components/Main";
import { Chip, Spinner } from "./components/primitives";
import { EngineScreen, Pick, Welcome } from "./components/Screens";
import { SectionPanel } from "./components/SectionPanel";
import { Sidebar } from "./components/Sidebar";
import { TitleBar } from "./components/TitleBar";
import { useChat } from "./hooks/useChat";
import { useEngine } from "./hooks/useEngine";
import { useLibrary } from "./hooks/useLibrary";
import { host } from "./lib/host";
import type { Category, DocumentInfo, Library, Scope, Section } from "./lib/types";

const SELECTION_KEY = "openrag.selection";
const NOTICE_MS = 7000;

function savedSelection(): Scope | null {
  try {
    return JSON.parse(localStorage.getItem(SELECTION_KEY) ?? "null") as Scope | null;
  } catch {
    return null;
  }
}

function exists(library: Library, scope: Scope | null): boolean {
  if (!scope) return false;
  const items = scope.kind === "section" ? library.sections : library.categories;
  return items.some((item) => item.id === scope.id);
}

export default function App() {
  const { engine, api } = useEngine();
  const [notice, setNotice] = useState<string | null>(null);
  const notify = useCallback((message: string) => setNotice(message), []);
  const { library, run } = useLibrary(api, notify);
  const [selected, setSelected] = useState<Scope | null>(savedSelection);
  const [nameRequest, setNameRequest] = useState<NameRequest | null>(null);
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);

  useEffect(() => host.onNotice(notify), [notify]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  // Keep the selection valid: fall back to the first section, or nothing.
  const selection = useMemo<Scope | null>(() => {
    if (!library) return null;
    if (exists(library, selected)) return selected;
    const first = library.sections[0];
    return first ? { kind: "section", id: first.id } : null;
  }, [library, selected]);

  const select = useCallback((scope: Scope) => {
    setSelected(scope);
    localStorage.setItem(SELECTION_KEY, JSON.stringify(scope));
  }, []);

  const section = selection?.kind === "section" ? library?.sections.find((s) => s.id === selection.id) : undefined;
  const category = library?.categories.find((c) => c.id === (section ? section.category_id : selection?.id));
  const categorySections = category ? (library?.sections.filter((s) => s.category_id === category.id) ?? []) : [];
  const chat = useChat(api, selection);

  const sectionId = section?.id;
  const sectionReady = section ? `${section.documents}:${section.status.state}` : "";
  useEffect(() => {
    if (!api || !sectionId) return;
    let cancelled = false;
    setDocuments(null);
    api.documents(sectionId).then(
      (docs) => !cancelled && setDocuments(docs),
      () => !cancelled && setDocuments([]),
    );
    return () => {
      cancelled = true;
    };
  }, [api, sectionId, sectionReady]);

  if (engine.state !== "ready") {
    return (
      <div className="flex h-full flex-col">
        <TitleBar />
        <div className="min-h-0 flex-1">
          <EngineScreen engine={engine} onRestart={() => host.restartEngine()} />
        </div>
      </div>
    );
  }

  const newCategory = () =>
    setNameRequest({
      title: "New category",
      label: "A subject or research area",
      action: "Create",
      onSubmit: async (name) => {
        const created = await run((a) => a.addCategory(name));
        if (created) select({ kind: "category", id: created.id });
      },
    });
  const newSection = (cat: Category) =>
    setNameRequest({
      title: `New section in ${cat.name}`,
      label: "A course, session, project or reading list",
      action: "Create",
      onSubmit: async (name) => {
        const created = await run((a) => a.addSection(name, cat.id));
        if (created) select({ kind: "section", id: created.id });
      },
    });
  const renameCategory = (cat: Category) =>
    setNameRequest({
      title: "Rename category",
      label: "Name",
      action: "Rename",
      initial: cat.name,
      onSubmit: (name) => void run((a) => a.renameCategory(cat.id, name)),
    });
  const deleteCategory = (cat: Category) =>
    setConfirm({
      title: `Delete "${cat.name}"?`,
      body: "Only empty categories can be deleted. Your files are never touched.",
      action: "Delete",
      onConfirm: () => void run((a) => a.deleteCategory(cat.id)),
    });
  const renameSection = (s: Section) =>
    setNameRequest({
      title: "Rename section",
      label: "Name",
      action: "Rename",
      initial: s.name,
      onSubmit: (name) => void run((a) => a.updateSection(s.id, { name })),
    });
  const deleteSection = (s: Section) =>
    setConfirm({
      title: `Delete "${s.name}"?`,
      body: "Its index and conversation are removed from Open RAG. Your files stay where they are.",
      action: "Delete",
      onConfirm: () => void run((a) => a.deleteSection(s.id)),
    });
  const addFolder = async (s: Section) => {
    const path = await host.pickFolder();
    if (!path) return;
    if ((await run((a) => a.addFolder(s.id, path))) !== undefined) await run((a) => a.index(s.id));
  };
  const removeFolder = async (s: Section, path: string) => {
    if ((await run((a) => a.removeFolder(s.id, path))) !== undefined) await run((a) => a.index(s.id));
  };

  return (
    <div className="flex h-full flex-col">
      <TitleBar>{category && (section ? `${category.name} › ${section.name}` : category.name)}</TitleBar>
      <div className="flex min-h-0 flex-1">
      <Sidebar
        library={library}
        selection={selection}
        onSelect={select}
        onNewCategory={newCategory}
        onNewSection={newSection}
        onRenameCategory={renameCategory}
        onDeleteCategory={deleteCategory}
      />
      <main className="sticker m-3 flex min-w-0 flex-1 flex-col overflow-hidden rounded-[20px]">
        {!library ? (
          <div className="grid h-full place-items-center">
            <Spinner className="size-5 text-accent" />
          </div>
        ) : library.categories.length === 0 ? (
          <Welcome onNewCategory={newCategory} />
        ) : section ? (
          <>
            <MainHeader
              title={section.name}
              subtitle={`${section.documents} ${section.documents === 1 ? "document" : "documents"} · answers only from this section`}
              chip={category && <Chip>{category.name}</Chip>}
              onRename={() => renameSection(section)}
              onDelete={() => deleteSection(section)}
            />
            <div className="flex min-h-0 flex-1">
              <Chat
                title={section.name}
                messages={chat.messages}
                busy={chat.busy}
                onSend={(q) => void chat.send(q)}
                onStop={chat.stop}
                onClear={chat.clear}
                blocked={sectionBlock(section)}
                onOpen={(s) => host.openSource(s.source)}
                onReveal={(s) => host.revealSource(s.source)}
              />
              <SectionPanel
                section={section}
                documents={documents}
                onAddFolder={() => void addFolder(section)}
                onRemoveFolder={(path) => void removeFolder(section, path)}
                onIndex={() => void run((a) => a.index(section.id))}
                onOpenDocument={(path) => host.openSource(path)}
              />
            </div>
          </>
        ) : category ? (
          <>
            <MainHeader
              title={category.name}
              subtitle={`${categorySections.length} ${categorySections.length === 1 ? "section" : "sections"} · answers from all of them`}
              chip={<Chip tone="accent">Whole category</Chip>}
              onRename={() => renameCategory(category)}
              onDelete={() => deleteCategory(category)}
            />
            <div className="flex min-h-0 flex-1">
              <Chat
                title={category.name}
                messages={chat.messages}
                busy={chat.busy}
                onSend={(q) => void chat.send(q)}
                onStop={chat.stop}
                onClear={chat.clear}
                blocked={categoryBlock(categorySections)}
                onOpen={(s) => host.openSource(s.source)}
                onReveal={(s) => host.revealSource(s.source)}
              />
              <CategoryPanel sections={categorySections} onSelect={(id) => select({ kind: "section", id })} />
            </div>
          </>
        ) : (
          <Pick text="Choose a section on the left, or create one in a category." />
        )}
      </main>
      </div>
      <NameDialog request={nameRequest} onClose={() => setNameRequest(null)} />
      <ConfirmDialog request={confirm} onClose={() => setConfirm(null)} />
      <Toast message={notice} onClose={() => setNotice(null)} />
    </div>
  );
}

function sectionBlock(section: Section): string | null {
  if (section.status.state === "indexing") return "Indexing… you can ask as soon as it finishes.";
  if (section.folders.length === 0) return "Add a folder with this section's documents to start.";
  if (section.documents === 0) return "Index this section to start asking questions.";
  return null;
}

function categoryBlock(sections: Section[]): string | null {
  if (sections.length === 0) return "This category has no sections yet.";
  if (sections.some((s) => s.status.state === "indexing")) return "A section in this category is indexing… ask when it finishes.";
  if (sections.every((s) => s.documents === 0)) return "Index a section in this category to start asking questions.";
  return null;
}
