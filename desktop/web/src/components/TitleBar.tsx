import { Copy, Minus, Square, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { host } from "../lib/host";
import { LogoMark } from "./primitives";

/** The window's title bar, drawn in the Arena's top-bar style. Dragging it moves the window, double-clicking maximises,
 * and right-clicking shows the window menu, because it is a native drag region. */
export function TitleBar({ children }: { children?: ReactNode }) {
  const [maximized, setMaximized] = useState(false);
  useEffect(() => host.onWindowState(setMaximized), []);
  return (
    <header className="drag flex h-12 shrink-0 items-center gap-3 border-b-[2.5px] border-edge bg-card pl-4 select-none">
      <LogoMark className="text-[15px]" />
      <span className="font-display text-[20px] leading-none">Open RAG</span>
      <div className="min-w-0 flex-1 truncate text-[13px] text-ink-2">{children}</div>
      {host.isDesktop && (
        <div className="no-drag flex h-full items-stretch">
          <WindowButton label="Minimise" onClick={() => host.windowAction("minimize")}>
            <Minus className="size-4" strokeWidth={2.5} />
          </WindowButton>
          <WindowButton label={maximized ? "Restore" : "Maximise"} onClick={() => host.windowAction("maximize")}>
            {maximized ? <Copy className="size-3.5 -scale-x-100" strokeWidth={2.5} /> : <Square className="size-3.5" strokeWidth={2.5} />}
          </WindowButton>
          <WindowButton label="Close" danger onClick={() => host.windowAction("close")}>
            <X className="size-4" strokeWidth={2.5} />
          </WindowButton>
        </div>
      )}
    </header>
  );
}

function WindowButton({ label, danger, onClick, children }: { label: string; danger?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`grid w-12 place-items-center text-ink-2 transition ${danger ? "hover:bg-tomato hover:text-white" : "hover:bg-card-2 hover:text-ink"}`}
    >
      {children}
    </button>
  );
}
