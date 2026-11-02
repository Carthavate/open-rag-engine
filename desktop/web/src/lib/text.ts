/** Splits a stream of text chunks into complete lines (the engine streams answers as one JSON object per line). */
export class LineSplitter {
  private buffer = "";

  push(chunk: string): string[] {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";
    return lines.filter((line) => line.trim());
  }

  flush(): string[] {
    const rest = this.buffer;
    this.buffer = "";
    return rest.trim() ? [rest] : [];
  }
}

export type AnswerPart = { kind: "text"; text: string } | { kind: "cite"; numbers: number[] };

const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

/** "It draws 1.2 kW [1][2, 3]." becomes text and citation parts, so citations can be drawn as clickable pills. */
export function splitCitations(text: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    if (match.index > last) parts.push({ kind: "text", text: text.slice(last, match.index) });
    parts.push({ kind: "cite", numbers: match[1].split(",").map((n) => Number(n.trim())) });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ kind: "text", text: text.slice(last) });
  return parts;
}

/** "C:/Courses/Physics/lecture 3.pdf" -> "lecture 3.pdf" */
export function fileName(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path;
}

/** "C:/Courses/Physics" -> "Courses › Physics" (the last two folders), for compact folder rows. */
export function shortFolder(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts.slice(-2).join(" › ") || path;
}
