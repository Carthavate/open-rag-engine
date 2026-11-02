import { ExternalLink } from "lucide-react";
import { useState, type ReactNode } from "react";
import { CREDITS, SOURCE_URL, type Credit } from "../lib/credits";
import { host } from "../lib/host";
import { Sheet } from "./Dialogs";
import { Button, LogoMark } from "./primitives";

function Initials({ credit, className = "" }: { credit: Credit; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`grid size-7 place-items-center rounded-full border-2 border-edge bg-sun font-display text-[12px] text-[#17183a] ${className}`}
    >
      {credit.initials}
    </span>
  );
}

function LinkButton({ href, label, children }: { href: string; label: string; children: ReactNode }) {
  return (
    <Button className="h-8 px-3 text-[13px]" aria-label={label} title={href} onClick={() => host.openLink(href)}>
      {children}
      <ExternalLink className="size-3.5 opacity-60" />
    </Button>
  );
}

/** The sidebar's "Developed by" line; it opens the Credits sheet with both authors' GitHub and LinkedIn. */
export function Credits() {
  const [open, setOpen] = useState(false);
  const first = (c: Credit) => c.name.split(" ")[0];
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mx-3 mb-3 flex items-center gap-2 rounded-xl border-2 border-transparent px-2 py-1.5 text-left text-[12.5px] text-ink-2 transition hover:border-edge hover:bg-card-2 hover:text-ink"
      >
        <span className="flex shrink-0 -space-x-1">
          {CREDITS.map((c) => (
            <Initials key={c.name} credit={c} className="size-6 text-[10.5px]" />
          ))}
        </span>
        <span className="min-w-0">
          Developed by <b className="text-ink">{CREDITS.map(first).join(" & ")}</b>
        </span>
      </button>

      <Sheet open={open} onClose={() => setOpen(false)}>
        <div className="flex items-center gap-3">
          <LogoMark />
          <h2 className="text-[24px]">Credits</h2>
        </div>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
          Open RAG is developed by Wadi and Ghassen, from the RAG course we made for the AI Engineering Arena.
        </p>
        <ul className="mt-4 space-y-3">
          {CREDITS.map((c) => (
            <li key={c.name} className="rounded-2xl border-2 border-edge bg-card-2 p-3">
              <div className="flex items-center gap-3">
                <Initials credit={c} className="size-10 text-[16px]" />
                <div className="min-w-0">
                  <p className="font-display text-[18px] leading-tight">{c.name}</p>
                  <p className="text-[12.5px] text-ink-2">{c.role}</p>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <LinkButton href={c.github} label={`${c.name} on GitHub`}>GitHub</LinkButton>
                <LinkButton href={c.linkedin} label={`${c.name} on LinkedIn`}>LinkedIn</LinkButton>
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[12.5px] text-ink-2">
          Free and open source (AGPL-3.0).{" "}
          <button type="button" className="font-bold text-accent underline underline-offset-2" onClick={() => host.openLink(SOURCE_URL)}>
            Source code
          </button>
        </p>
        <div className="mt-4 flex justify-end">
          <Button variant="primary" onClick={() => setOpen(false)}>
            Close
          </Button>
        </div>
      </Sheet>
    </>
  );
}
