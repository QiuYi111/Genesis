import { useEffect } from "react";
import { fetchSimulationSnapshot } from "../services/monitorApi";
import {
  buildAgentActionMap,
  mapSnapshotToTurnPayload,
  normalizeLogEntries
} from "../services/transformers";
import { useSimulationStore } from "../state/store";
import type { Structure } from "../types/simulation";

const SNAPSHOT_REFRESH_INTERVAL_MS = 15000;

export function useSimulationBootstrap(): void {
  const ingestTurn = useSimulationStore((s) => s.ingestTurn);
  const setAgentActions = useSimulationStore((s) => s.setAgentActions);
  const setStructures = useSimulationStore((s) => s.setStructures);
  const replaceLogs = useSimulationStore((s) => s.replaceLogs);

  useEffect(() => {
    let cancelled = false;
    let timer: number | null = null;

    async function hydrateFromSnapshot(): Promise<void> {
      try {
        const snapshot = await fetchSimulationSnapshot();
        if (cancelled || !snapshot) {
          return;
        }
        const turn = mapSnapshotToTurnPayload(snapshot);
        if (turn) {
          const state = useSimulationStore.getState();
          const last = state.turns[state.turns.length - 1];
          if (!last || last.hash !== turn.hash) {
            ingestTurn(turn);
          }
          setAgentActions(buildAgentActionMap(turn.agents));
        }
        if (Array.isArray(snapshot.structures)) {
          setStructures(snapshot.structures as Structure[]);
        }
        if (Array.isArray(snapshot.logs)) {
          const entries = normalizeLogEntries(snapshot.logs).slice(-200);
          replaceLogs(entries);
        }
      } catch {
        // ignore fetch errors; websocket stream will continue to drive UI
      }
    }

    hydrateFromSnapshot();

    timer = window.setInterval(hydrateFromSnapshot, SNAPSHOT_REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearInterval(timer);
      }
    };
  }, [ingestTurn, replaceLogs, setAgentActions, setStructures]);
}
