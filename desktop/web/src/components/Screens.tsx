import { AlertTriangle, FolderPlus, Library, RotateCcw } from "lucide-react";
import type { EngineState } from "../lib/host";
import { Button, LogoMark, Spinner } from "./primitives";

export function EngineScreen({ engine, onRestart }: { engine: EngineState; onRestart: () => void }) {
  return (
    <div className="grid h-full place-items-center p-8">
      <div className="sticker w-full max-w-md rounded-[24px] p-7 text-center">
        <LogoMark className="text-[24px]" />
        {engine.state === "failed" ? (
          <>
            <h1 className="mt-5 flex items-center justify-center gap-2 text-[28px]">
              <AlertTriangle className="size-5 text-bad" /> The engine didn't start
            </h1>
            <pre className="selectable mt-3 max-h-48 overflow-auto rounded-xl border-2 border-edge bg-card-2 p-3 text-left font-mono text-[11.5px] whitespace-pre-wrap text-ink-2">
              {engine.message}
            </pre>
            <Button variant="primary" className="mt-4" icon={<RotateCcw className="size-3.5" />} onClick={onRestart}>
              Try again
            </Button>
          </>
        ) : (
          <>
            <h1 className="mt-5 text-[30px]">Starting Open RAG</h1>
            <p className="mt-1 text-[14px] text-ink-2">Loading the engine on this computer. Nothing goes online.</p>
            <Spinner className="mt-5 size-5 text-accent" />
          </>
        )}
      </div>
    </div>
  );
}

export function Welcome({ onNewCategory }: { onNewCategory: () => void }) {
  return (
    <div className="grid h-full place-items-center p-8">
      <div className="max-w-lg text-center">
        <div className="sticker mx-auto grid size-16 -rotate-6 place-items-center bg-mint text-[#17183a]">
          <Library className="size-8" strokeWidth={2.4} />
        </div>
        <h1 className="mt-5 text-[40px] leading-[1.05]">Ask questions about your own documents</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
          Organise your material into <b className="font-bold text-ink">categories</b> (a subject or a research area) and{" "}
          <b className="font-bold text-ink">sections</b> (a course, a session, a project). Each section answers only from its own
          folders, with sources you can open. Everything stays on this computer.
        </p>
        <Button variant="primary" className="mt-6 h-11 px-5 text-[15px]" icon={<FolderPlus className="size-4" />} onClick={onNewCategory}>
          Create your first category
        </Button>
      </div>
    </div>
  );
}

export function Pick({ text }: { text: string }) {
  return <div className="grid h-full place-items-center text-[14px] text-ink-2">{text}</div>;
}
