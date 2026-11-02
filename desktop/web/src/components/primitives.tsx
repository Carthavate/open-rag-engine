import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "sun";

const VARIANTS: Record<Variant, string> = {
  primary: "sticker-sm press bg-accent text-on-accent",
  secondary: "sticker-sm press bg-card text-ink",
  sun: "sticker-sm press bg-sun text-[#17183a]",
  danger: "sticker-sm press bg-tomato text-white",
  ghost: "rounded-xl text-ink-2 hover:bg-card-2 hover:text-ink",
};

/** The Arena's chunky button: outlined, with a hard shadow that lifts on hover. */
export function Button({
  variant = "secondary",
  icon,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: ReactNode }) {
  return (
    <button
      type="button"
      className={`inline-flex h-9 items-center gap-1.5 px-3.5 text-[14px] font-bold disabled:pointer-events-none disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

export function IconButton({
  label,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`grid size-8 place-items-center rounded-lg text-ink-2 transition hover:bg-card-2 hover:text-ink disabled:pointer-events-none disabled:opacity-40 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Spinner({ className = "size-4" }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Working"
      className={`inline-block animate-spin rounded-full border-[2.5px] border-current border-r-transparent ${className}`}
    />
  );
}

/** The Arena's XP bar: an outlined track with a mint fill. */
export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-4 w-full overflow-hidden rounded-full border-2 border-edge bg-card-2">
      <div className="h-full bg-mint transition-[width] duration-500" style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  );
}

/** A small mono label, like the Arena's XP chips. */
export function Chip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "accent" | "warn" | "bad" | "good" }) {
  const tones = {
    neutral: "border-line text-ink-2 bg-card",
    accent: "border-accent text-accent bg-card",
    warn: "border-edge text-[#17183a] bg-sun",
    bad: "border-bad text-bad bg-card",
    good: "border-edge text-[#17183a] bg-mint",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border-2 px-2 py-px font-mono text-[11.5px] font-semibold whitespace-nowrap ${tones[tone]}`}>
      {children}
    </span>
  );
}

/** The Arena's logo mark: a tilted tomato sticker. */
export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <span
      className={`sticker-sm inline-block -rotate-6 bg-tomato px-2 py-0.5 font-display text-[17px] leading-tight text-white ${className}`}
    >
      RAG
    </span>
  );
}
