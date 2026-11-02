import { describe, expect, it } from "vitest";
import { fileName, LineSplitter, shortFolder, splitCitations } from "./text";

describe("LineSplitter", () => {
  it("joins lines split across chunks and drops blank ones", () => {
    const lines = new LineSplitter();
    expect(lines.push('{"n":1}\n{"n"')).toEqual(['{"n":1}']);
    expect(lines.push(":2}\n\n")).toEqual(['{"n":2}']);
    expect(lines.push('{"n":3}')).toEqual([]);
    expect(lines.flush()).toEqual(['{"n":3}']);
    expect(lines.flush()).toEqual([]);
  });
});

describe("splitCitations", () => {
  it("turns [n] and [n, m] into citation parts", () => {
    expect(splitCitations("It draws 1.2 kW [1][2, 3].")).toEqual([
      { kind: "text", text: "It draws 1.2 kW " },
      { kind: "cite", numbers: [1] },
      { kind: "cite", numbers: [2, 3] },
      { kind: "text", text: "." },
    ]);
  });

  it("leaves text without citations alone", () => {
    expect(splitCitations("No sources.")).toEqual([{ kind: "text", text: "No sources." }]);
    expect(splitCitations("")).toEqual([]);
  });
});

describe("paths", () => {
  it("shows file names and short folders", () => {
    expect(fileName("C:/Courses/Physics/lecture 3.pdf")).toBe("lecture 3.pdf");
    expect(fileName("C:\\a\\b.md")).toBe("b.md");
    expect(shortFolder("C:/Courses/Physics/")).toBe("Courses › Physics");
  });
});
