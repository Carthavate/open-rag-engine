import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "./primitives";

function Sheet({ open, onClose, children }: { open: boolean; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-[#17183a]/35 p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            className="sticker w-full max-w-sm rounded-[20px] p-5"
            initial={{ scale: 0.96, y: 8 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.97, y: 4 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export type NameRequest = { title: string; label: string; action: string; initial?: string; onSubmit: (name: string) => void };

/** Asks for a name: new category, new section, or rename. */
export function NameDialog({ request, onClose }: { request: NameRequest | null; onClose: () => void }) {
  const [name, setName] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (request) {
      setName(request.initial ?? "");
      setTimeout(() => input.current?.select(), 30);
    }
  }, [request]);
  const valid = name.trim().length > 0 && name.trim().length <= 80;
  const submit = () => {
    if (!request || !valid) return;
    request.onSubmit(name.trim());
    onClose();
  };
  return (
    <Sheet open={request !== null} onClose={onClose}>
      <h2 className="text-[24px]">{request?.title}</h2>
      <label className="mt-4 block text-[13px] font-bold text-ink-2">
        {request?.label}
        <input
          ref={input}
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          className="mt-1.5 block h-10 w-full rounded-xl border-[2.5px] border-edge bg-card-2 px-3 text-[15px] text-ink outline-none focus:shadow-[3px_3px_0_var(--cobalt)]"
        />
      </label>
      <div className="mt-5 flex justify-end gap-2">
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="primary" disabled={!valid} onClick={submit}>
          {request?.action}
        </Button>
      </div>
    </Sheet>
  );
}

export type ConfirmRequest = { title: string; body: string; action: string; onConfirm: () => void };

export function ConfirmDialog({ request, onClose }: { request: ConfirmRequest | null; onClose: () => void }) {
  return (
    <Sheet open={request !== null} onClose={onClose}>
      <h2 className="text-[24px]">{request?.title}</h2>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-2">{request?.body}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="danger"
          onClick={() => {
            request?.onConfirm();
            onClose();
          }}
        >
          {request?.action}
        </Button>
      </div>
    </Sheet>
  );
}
