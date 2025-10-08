import { useEffect } from "react";
import { useSimulationStore } from "../state/store";
import {
  buildAgentActionMap,
  mapSnapshotToTurnPayload,
  normalizeActionEvents,
  normalizeLogEntries
} from "./transformers";

export function useMonitorStream(): void {
  const ingestTurn = useSimulationStore((s) => s.ingestTurn);
  const updateConnection = useSimulationStore((s) => s.updateConnection);
  const recordInteraction = useSimulationStore((s) => s.recordInteraction);
  const appendLogs = useSimulationStore((s) => s.appendLogs);
  const replaceLogs = useSimulationStore((s) => s.replaceLogs);
  const setStructures = useSimulationStore((s) => s.setStructures);
  const mergeStructures = useSimulationStore((s) => s.mergeStructures);
  const updateAgentAction = useSimulationStore((s) => s.updateAgentAction);
  const setAgentActions = useSimulationStore((s) => s.setAgentActions);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectAttempts = 0;
    let closed = false;

    function connect() {
      updateConnection({ status: "connecting" });
      const url = buildWsUrl();
      ws = new WebSocket(url);

      ws.onopen = () => {
        reconnectAttempts = 0;
        updateConnection({ status: "live", reconnectAttempts });
        // Request current snapshot if needed
        ws?.send(JSON.stringify({ type: "request_update" }));
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "simulation_update") {
            const turn = mapSnapshotToTurnPayload(msg.data);
            if (turn) {
              ingestTurn(turn);
              setAgentActions(buildAgentActionMap(turn.agents));
            }
            const normalizedActions = normalizeActionEvents(msg.data?.actions ?? []);
            for (const { interaction, agentId, actionText } of normalizedActions) {
              recordInteraction(interaction);
              if (agentId && actionText) {
                updateAgentAction(agentId, actionText);
              }
            }
            const structures = Array.isArray(msg.data?.structures) ? msg.data.structures : null;
            if (structures) setStructures(structures);
            const logEntries = normalizeLogEntries(msg.data?.logs ?? []);
            if (logEntries.length) {
              replaceLogs(logEntries.slice(-200));
            }
          } else if (msg.type === "log_entry") {
            const entries = normalizeLogEntries([msg.data]);
            if (entries.length) {
              appendLogs(entries);
            }
          } else if (msg.type === "logs_update") {
            const entries = normalizeLogEntries(msg.data?.logs ?? []);
            if (entries.length) {
              replaceLogs(entries);
            }
          } else if (msg.type === "actions_update") {
            const normalizedEvents = normalizeActionEvents(msg.data?.events ?? []);
            for (const { interaction, agentId, actionText } of normalizedEvents) {
              recordInteraction(interaction);
              if (agentId && actionText) {
                updateAgentAction(agentId, actionText);
              }
            }
          } else if (msg.type === "structures_update") {
            const items = (msg.data?.structures ?? []) as any[];
            if (items.length) mergeStructures(items);
          }
        } catch {
          // ignore bad messages
        }
      };

      ws.onclose = () => {
        if (closed) return;
        reconnectAttempts += 1;
        updateConnection({ status: "offline", reconnectAttempts });
        setTimeout(connect, Math.min(3000 + reconnectAttempts * 500, 8000));
      };

      ws.onerror = () => {
        updateConnection({ status: "degraded" });
      };
    }

    connect();

    return () => {
      closed = true;
      try { ws?.close(); } catch { /* ignore */ }
    };
  }, [
    ingestTurn,
    updateConnection,
    recordInteraction,
    appendLogs,
    replaceLogs,
    setStructures,
    mergeStructures,
    updateAgentAction,
    setAgentActions,
  ]);
}

function buildWsUrl(): string {
  const loc = window.location;
  const protocol = loc.protocol === "https:" ? "wss:" : "ws:";
  // WebMonitor runs WS on 8765 by default; assume same host
  const host = loc.hostname + ":" + (loc.port || (loc.protocol === "https:" ? "443" : "80"));
  // If UI served on 8081 and backend WS on 8765, try to replace port
  const maybeDefaultUi = loc.port === "8081";
  const wsHost = maybeDefaultUi ? loc.hostname + ":8765" : host;
  return `${protocol}//${wsHost}`;
}
