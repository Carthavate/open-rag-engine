import { describe, expect, it } from "vitest";
import { ApiError, Engine, type Reply, type Transport } from "./api";

function fake(replies: Record<string, Reply>, lines: string[] = [], streamReply: Reply = { status: 200, body: "" }) {
  const sent: { method: string; path: string; body?: unknown }[] = [];
  const transport: Transport = {
    async send(method, path, body) {
      sent.push({ method, path, body });
      return replies[`${method} ${path}`] ?? { status: 404, body: '{"title":"Not found","detail":"Unknown"}' };
    },
    async stream(_path, _body, onLine) {
      lines.forEach(onLine);
      return streamReply;
    },
  };
  return { engine: new Engine(transport), sent };
}

const done = { type: "done", question: "q", text: "1.2 kW [1].", abstained: false, grounded: true, invalid_citations: [], citations: [], sources: [] };

describe("Engine", () => {
  it("parses JSON replies and sends bodies", async () => {
    const { engine, sent } = fake({ "POST /categories": { status: 201, body: '{"id":"a1","name":"Physics"}' } });
    expect(await engine.addCategory("Physics")).toEqual({ id: "a1", name: "Physics" });
    expect(sent).toEqual([{ method: "POST", path: "/categories", body: { name: "Physics" } }]);
  });

  it("treats 204 as no content", async () => {
    const { engine } = fake({ "DELETE /sections/s1": { status: 204, body: "" } });
    await expect(engine.deleteSection("s1")).resolves.toBeUndefined();
  });

  it("turns problem details into ApiError with the engine's explanation", async () => {
    const { engine } = fake({ "GET /library": { status: 503, body: '{"title":"Engine unavailable","detail":"The engine isn\'t running."}' } });
    await expect(engine.library()).rejects.toEqual(new ApiError(503, "The engine isn't running."));
  });

  it("streams tokens and returns the final answer", async () => {
    const tokens: string[] = [];
    const lines = ['{"type":"token","text":"1.2 "}', '{"type":"token","text":"kW [1]."}', JSON.stringify(done)];
    const { engine } = fake({}, lines);
    const answer = await engine.ask({ kind: "section", id: "s1" }, "q", [], (t) => tokens.push(t));
    expect(tokens.join("")).toBe("1.2 kW [1].");
    expect(answer.grounded).toBe(true);
  });

  it("reports a refused question and an error inside the stream", async () => {
    const refused = fake({}, [], { status: 409, body: '{"detail":"Still indexing: Optics."}' }).engine;
    await expect(refused.ask({ kind: "section", id: "s1" }, "q", [], () => {})).rejects.toThrow("Still indexing");
    const broken = fake({}, ['{"type":"error","status":503,"title":"x","detail":"The local language model isn\'t running."}']).engine;
    await expect(broken.ask({ kind: "category", id: "c1" }, "q", [], () => {})).rejects.toThrow("language model");
  });

  it("notices an answer that never finished", async () => {
    const { engine } = fake({}, ['{"type":"token","text":"half"}']);
    await expect(engine.ask({ kind: "section", id: "s1" }, "q", [], () => {})).rejects.toThrow("before it was complete");
  });
});
