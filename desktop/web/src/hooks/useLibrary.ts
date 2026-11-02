import { useCallback, useEffect, useRef, useState } from "react";
import type { EngineApi } from "../lib/api";
import type { Library } from "../lib/types";

const POLL_MS = 1000;

/** The categories and sections, refreshed after every change and every second while a section is indexing. */
export function useLibrary(api: EngineApi | null, onError: (message: string) => void) {
  const [library, setLibrary] = useState<Library | null>(null);
  const errorRef = useRef(onError);
  errorRef.current = onError;

  const refresh = useCallback(async () => {
    if (!api) return;
    try {
      setLibrary(await api.library());
    } catch (error) {
      errorRef.current(error instanceof Error ? error.message : String(error));
    }
  }, [api]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const indexing = library?.sections.some((s) => s.status.state === "indexing") ?? false;
  useEffect(() => {
    if (!indexing) return;
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [indexing, refresh]);

  /** Runs a change against the engine, then refreshes; errors become a notice instead of a crash. */
  const run = useCallback(
    async <T,>(action: (api: EngineApi) => Promise<T>): Promise<T | undefined> => {
      if (!api) return undefined;
      try {
        const result = await action(api);
        await refresh();
        return result;
      } catch (error) {
        errorRef.current(error instanceof Error ? error.message : String(error));
        return undefined;
      }
    },
    [api, refresh],
  );

  return { library, refresh, run };
}
