import { ApiError, type EngineApi } from "./api";
import { IDLE, type AnswerDone, type Category, type IndexStatus, type Library, type Scope, type Section, type Source } from "./types";

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

let counter = 0;
const newId = () => `m${++counter}`;

/** Pretends to be the engine in a normal browser, so the interface can be designed without Python or models. */
export class MockEngine implements EngineApi {
  private state: Library;
  private readonly docs = new Map<string, string[]>();

  constructor() {
    const physics: Category = { id: newId(), name: "Physics" };
    const research: Category = { id: newId(), name: "Thesis research" };
    const optics = this.section("Lesson 3: Optics", physics.id, ["C:/Courses/Physics/Optics"]);
    const papers = this.section("Retrieval papers", research.id, ["D:/Research/Papers"]);
    this.docs.set(optics.id, ["refraction.pdf", "lenses.md", "lab-sheet.pdf"]);
    this.docs.set(papers.id, ["rrf-cormack-2009.pdf", "colbert.pdf"]);
    this.state = {
      categories: [physics, research],
      sections: [
        { ...optics, documents: 3 },
        { ...papers, documents: 2 },
      ],
    };
  }

  private section(name: string, categoryId: string, folders: string[] = []): Section {
    return { id: newId(), name, category_id: categoryId, folders, documents: 0, status: IDLE };
  }

  async library() {
    await delay(120);
    return structuredClone(this.state);
  }

  async addCategory(name: string) {
    const category = { id: newId(), name };
    this.state = { ...this.state, categories: [...this.state.categories, category] };
    return category;
  }

  async renameCategory(id: string, name: string) {
    this.state = { ...this.state, categories: this.state.categories.map((c) => (c.id === id ? { ...c, name } : c)) };
    return { id, name };
  }

  async deleteCategory(id: string) {
    if (this.state.sections.some((s) => s.category_id === id)) {
      throw new ApiError(422, "Move or delete the sections in this category first");
    }
    this.state = { ...this.state, categories: this.state.categories.filter((c) => c.id !== id) };
  }

  async addSection(name: string, categoryId: string) {
    const section = this.section(name, categoryId);
    this.state = { ...this.state, sections: [...this.state.sections, section] };
    return section;
  }

  async updateSection(id: string, patch: { name?: string; category_id?: string }) {
    this.patch(id, (s) => ({ ...s, ...patch }));
  }

  async deleteSection(id: string) {
    this.state = { ...this.state, sections: this.state.sections.filter((s) => s.id !== id) };
  }

  async addFolder(sectionId: string, path: string) {
    this.patch(sectionId, (s) => ({ ...s, folders: s.folders.includes(path) ? s.folders : [...s.folders, path] }));
  }

  async removeFolder(sectionId: string, path: string) {
    this.patch(sectionId, (s) => ({ ...s, folders: s.folders.filter((f) => f !== path) }));
  }

  async index(sectionId: string): Promise<IndexStatus> {
    const total = Math.max(1, this.get(sectionId).folders.length * 4);
    const names = Array.from({ length: total }, (_, i) => `document-${i + 1}.pdf`);
    this.docs.set(sectionId, names);
    const step = (done: number) => {
      const finished = done >= total;
      const status: IndexStatus = finished
        ? { ...IDLE, done, total, report: { added: total, updated: 0, unchanged: 0, removed: 0, failed: [] } }
        : { ...IDLE, state: "indexing", done, total, current: names[done] };
      this.patch(sectionId, (s) => ({ ...s, status, documents: finished ? total : s.documents }));
      if (!finished) setTimeout(() => step(done + 1), 450);
    };
    step(0);
    return this.get(sectionId).status;
  }

  async documents(sectionId: string) {
    return (this.docs.get(sectionId) ?? []).map((name) => ({ source: `C:/Docs/${name}`, name, chunks: 4 }));
  }

  async ask(scope: Scope, question: string, _history: unknown, onToken: (t: string) => void, signal?: AbortSignal) {
    const sectionId = scope.kind === "section" ? scope.id : this.state.sections.find((s) => s.category_id === scope.id)?.id;
    const names = sectionId ? (this.docs.get(sectionId) ?? []) : [];
    if (names.length === 0) {
      const abstain = "I don't know based on the provided documents.";
      onToken(abstain);
      return this.done(question, abstain, [], true);
    }
    const sources: Source[] = names.slice(0, 3).map((name, i) => ({
      number: i + 1,
      label: name,
      source: `C:/Docs/${name}`,
      page: name.endsWith(".pdf") ? i + 2 : null,
      section_id: sectionId ?? null,
      score: 4 - i,
      snippet: `A passage from ${name} that talks about ${question.toLowerCase().replace(/\?$/, "")} in some detail…`,
    }));
    const text = `Here is what your documents say: light bends when it passes between materials of different density [1], which is why a lens can focus it [2].`;
    for (const word of text.split(/(?<= )/)) {
      await delay(35, signal);
      onToken(word);
    }
    return this.done(question, text, sources, false);
  }

  private done(question: string, text: string, sources: Source[], abstained: boolean): AnswerDone {
    return {
      type: "done",
      question,
      text,
      abstained,
      grounded: !abstained,
      invalid_citations: [],
      citations: sources.slice(0, 2),
      sources,
    };
  }

  private get(id: string): Section {
    const section = this.state.sections.find((s) => s.id === id);
    if (!section) throw new ApiError(404, `Unknown section: ${id}`);
    return section;
  }

  private patch(id: string, change: (s: Section) => Section) {
    this.get(id);
    this.state = { ...this.state, sections: this.state.sections.map((s) => (s.id === id ? change(s) : s)) };
  }
}
