import { useEffect, useMemo, useState } from "react";
import { Engine, type EngineApi } from "../lib/api";
import { host, type EngineState } from "../lib/host";
import { MockEngine } from "../lib/mock";

/** The engine's state as the window reports it, and an API client once it is ready. */
export function useEngine(): { engine: EngineState; api: EngineApi | null } {
  const [engine, setEngine] = useState<EngineState>({ state: "starting" });
  useEffect(() => host.onEngine(setEngine), []);
  const api = useMemo(() => {
    if (engine.state !== "ready") return null;
    return engine.transport === "mock" ? new MockEngine() : new Engine(engine.transport);
  }, [engine]);
  return { engine, api };
}
