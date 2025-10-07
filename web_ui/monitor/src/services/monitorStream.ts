import { useEffect } from "react";
import { useSimulationStore } from "../state/store";
import type { AgentSummary, InteractionRecord, TurnPayload, WorldState } from "../types/simulation";

function mapBackendToTurnPayload(snapshot: any): TurnPayload | null {
  if (!snapshot || !snapshot.world) return null;

  const world: WorldState = {
    size: snapshot.world.size ?? 0,
    terrain: Array.isArray(snapshot.world.terrain) ? snapshot.world.terrain : [],
    resources: Array.isArray(snapshot.world.resources) ? snapshot.world.resources : [],
  };

  const agents: AgentSummary[] = (snapshot.agents || []).map((a: any) => {
    const id = String(a.aid ?? a.id ?? "?");
    const name = a.name ?? `Agent ${id}`;
    const x = Math.floor(a.x ?? (a.pos?.[0] ?? 0));
    const y = Math.floor(a.y ?? (a.pos?.[1] ?? 0));
    const inventory = a.inventory || {};
    const resources = Object.values(inventory).reduce((sum: number, v: any) => sum + (Number(v) || 0), 0);
    const action = String(a.current_action ?? "idle").toLowerCase();
    let status: AgentSummary["status"] = "idle";
    if (action.includes("move")) status = "moving";
    else if (action.includes("interact") || action.includes("fight") || action.includes("trade")) status = "engaged";
    else if (action.includes("rest") || action.includes("recover")) status = "recovering";

    return {
      id,
      name,
      faction: String(a.group_id ?? "Cohort"),
      role: a.role ?? (action ? action : "Citizen"),
      morale: Number(a.health ?? 100),
      resources,
      location: { x, y },
      status,
    };
  });

  // We don't have cohorts/heatmap/events from backend yet; keep empty for now.
  const turnId = Number(snapshot.turn ?? 0);

  const payload: TurnPayload = {
    turnId,
    revision: 1,
    hash: Math.random().toString(16).slice(2),
    occurredAt: new Date().toISOString(),
    latencyMs: 0,
    events: [],
    agents,
    cohorts: [],
    heatmap: [],
    interactions: [],
    world,
  };
  return payload;
}

function mapLogToInteraction(log: any): InteractionRecord | null {
  if (!log) return null;
  const content: string = String(log.message ?? "");
  let actor: InteractionRecord["actor"] = "agent";
  if (content.includes("【Trinity】") || /\bTrinity\b/.test(content)) actor = "trinity";
  if (/Operator|用户|User/.test(content)) actor = "user";
  return {
    id: `log-${log.timestamp}-${Math.random().toString(16).slice(2)}`,
    turnId: 0,
    actor,
    intent: actor === "trinity" ? "Advisory" : actor === "user" ? "Operator" : "Agent",
    content,
    outcome: "",
    timestamp: new Date(log.timestamp ? log.timestamp * 1000 : Date.now()).toISOString(),
  };
}

export function useMonitorStream(): void {
  const ingestTurn = useSimulationStore((s) => s.ingestTurn);
  const updateConnection = useSimulationStore((s) => s.updateConnection);
  const recordInteraction = useSimulationStore((s) => s.recordInteraction);
  const appendLogs = useSimulationStore((s) => s.appendLogs);
  const setStructures = useSimulationStore((s) => s.setStructures);
  const mergeStructures = useSimulationStore((s) => s.mergeStructures);
  const updateAgentAction = useSimulationStore((s) => s.updateAgentAction);

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
            const turn = mapBackendToTurnPayload(msg.data);
            if (turn) ingestTurn(turn);
            const actions = Array.isArray(msg.data?.actions) ? msg.data.actions : [];
            for (const ev of actions) {
              const rec: InteractionRecord = {
                id: `act-${ev.aid}-${ev.timestamp}-${Math.random().toString(16).slice(2)}`,
                actor: "agent",
                turnId: Number(ev.turn ?? 0),
                intent: "Action",
                content: `${ev.name ?? ev.aid}: ${String(ev.action ?? "").replace(/_/g, " ")}`,
                outcome: "",
                timestamp: new Date((ev.timestamp ?? Date.now()) * 1000).toISOString(),
              };
              recordInteraction(rec);
            }
            const structures = Array.isArray(msg.data?.structures) ? msg.data.structures : null;
            if (structures) setStructures(structures);
          } else if (msg.type === "log_entry") {
            const entry = msg.data;
            if (entry && entry.message) {
              const ts = new Date((entry.timestamp ?? Date.now()) * 1000).toISOString();
              appendLogs([{ timestamp: ts, level: String(entry.level || "INFO"), message: String(entry.message) }]);
              const parsed = extractAgentAttempt(entry.message as string);
              if (parsed) {
                updateAgentAction(String(parsed.id), parsed.action);
              }
            }
          } else if (msg.type === "actions_update") {
            const events = (msg.data?.events ?? []) as any[];
            for (const ev of events) {
              const rec: InteractionRecord = {
                id: `act-${ev.aid}-${ev.timestamp}-${Math.random().toString(16).slice(2)}`,
                actor: "agent",
                turnId: Number(ev.turn ?? 0),
                intent: "Action",
                content: `${ev.name ?? ev.aid}: ${String(ev.action ?? "").replace(/_/g, " ")}`,
                outcome: "",
                timestamp: new Date((ev.timestamp ?? Date.now()) * 1000).toISOString(),
              };
              recordInteraction(rec);
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
  }, [ingestTurn, updateConnection, recordInteraction, appendLogs, setStructures, mergeStructures, updateAgentAction]);
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

function stripColorCodes(s: string): string {
  // Remove ANSI and bracketed color marks (e.g., \x1b[93m or [93m)
  return s
    .replace(/\x1b\[[0-9;]*m/g, "")
    .replace(/\[[0-9]{1,3}m/g, "")
    .replace(/\[0m/g, "");
}

function extractAgentAttempt(message: string): { id: number; action: string } | null {
  const text = stripColorCodes(message).trim();
  if (!text) return null;
  // Pattern A (Chinese): Eldra(7) 行动 → Move north to chat ...
  let m = text.match(/([^\(\s]+)\((\d+)\)[^\n]*?行动\s*→\s*(.+)$/);
  if (m) {
    const id = Number(m[2]);
    const action = m[3].trim();
    return { id, action };
  }
  // Pattern B (English): Grok(2): (age 29) attempting: Gather flint ...
  m = text.match(/[^\(\s]+\((\d+)\).*?attempting:\s*(.+)$/i);
  if (m) {
    const id = Number(m[1]);
    const action = m[2].trim();
    return { id, action };
  }
  return null;
}
