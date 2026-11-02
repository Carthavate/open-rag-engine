/** The shapes the engine's local API returns (see open_rag_engine/api.py). */

export type Category = { id: string; name: string };

export type IndexState = "idle" | "indexing" | "error";

export type IndexReport = {
  added: number;
  updated: number;
  unchanged: number;
  removed: number;
  failed: { source: string; error: string }[];
};

export type IndexStatus = {
  state: IndexState;
  done: number;
  total: number;
  current: string | null;
  error: string | null;
  missing_folders: string[];
  report: IndexReport | null;
};

export type Section = {
  id: string;
  name: string;
  category_id: string;
  folders: string[];
  documents: number;
  status: IndexStatus;
};

export type Library = { categories: Category[]; sections: Section[] };

export type DocumentInfo = { source: string; name: string; chunks: number };

export type Source = {
  number: number;
  label: string;
  source: string;
  page: number | null;
  section_id: string | null;
  score: number;
  snippet: string;
};

export type AnswerDone = {
  type: "done";
  question: string;
  text: string;
  abstained: boolean;
  grounded: boolean;
  invalid_citations: number[];
  citations: Source[];
  sources: Source[];
};

export type AskEvent =
  | { type: "token"; text: string }
  | AnswerDone
  | { type: "error"; status: number; title: string; detail: string };

export type ScopeKind = "section" | "category";
export type Scope = { kind: ScopeKind; id: string };

export type Turn = { question: string; answer: string };

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      text: string;
      status: "streaming" | "done" | "error" | "stopped";
      answer?: AnswerDone;
      error?: string;
    };

export const IDLE: IndexStatus = {
  state: "idle",
  done: 0,
  total: 0,
  current: null,
  error: null,
  missing_folders: [],
  report: null,
};
