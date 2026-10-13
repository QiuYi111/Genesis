import type {
  AgentSummary,
  InteractionRecord,
  TurnPayload,
  WorldGroupSummary,
  WorldState,
  WorldStats
} from "../types/simulation";

const STATUS_NAMES: Record<AgentSummary["status"], string> = {
  idle: "Idle",
  moving: "On the move",
  engaged: "Engaged",
  recovering: "Recovering"
};

function safeNumber(value: unknown, fallback = 0): number {
  const num = typeof value === "string" ? Number(value) : value;
  return typeof num === "number" && Number.isFinite(num) ? num : fallback;
}

function safeString(value: unknown, fallback = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return fallback;
}

function mapWorldStats(stats: any): WorldStats | undefined {
  if (!stats || typeof stats !== "object") {
    return undefined;
  }
  return {
    total_agents: safeNumber(stats.total_agents ?? stats.totalAgents ?? stats.agents),
    active_agents: safeNumber(stats.active_agents ?? stats.activeAgents ?? stats.active),
    total_groups: safeNumber(stats.total_groups ?? stats.groups),
    total_resources: safeNumber(stats.total_resources ?? stats.resources),
    technologies_discovered: safeNumber(stats.technologies_discovered ?? stats.tech)
  };
}

function mapWorldGroups(groups: any): WorldGroupSummary[] | undefined {
  if (!Array.isArray(groups)) {
    return undefined;
  }
  return groups
    .map((group) => ({
      id: safeString(group.id ?? group.group_id ?? group.name ?? "group"),
      name: safeString(group.name ?? group.id ?? "Group"),
      member_count: safeNumber(group.member_count ?? group.members ?? group.memberCount),
      reputation: safeNumber(group.reputation),
      type: safeString(group.type ?? group.group_type ?? "unknown"),
      leader: group.leader ?? null
    }))
    .sort((a, b) => b.member_count - a.member_count);
}

export function mapSnapshotToTurnPayload(snapshot: any): TurnPayload | null {
  if (!snapshot || typeof snapshot !== "object" || !snapshot.world) {
    return null;
  }

  const worldPayload = snapshot.world ?? {};

  const worldTurnSource = worldPayload.turn ?? snapshot.turn;
  const worldTurn =
    typeof worldTurnSource === "number" || typeof worldTurnSource === "string"
      ? safeNumber(worldTurnSource)
      : undefined;

  const world: WorldState = {
    size: safeNumber(worldPayload.size),
    terrain: Array.isArray(worldPayload.terrain) ? worldPayload.terrain : [],
    resources: Array.isArray(worldPayload.resources) ? worldPayload.resources : [],
    era: typeof worldPayload.era === "string" ? worldPayload.era : undefined,
    turn: worldTurn,
    stats: mapWorldStats(worldPayload.stats),
    groups: mapWorldGroups(worldPayload.groups)
  };

  const agents: AgentSummary[] = Array.isArray(snapshot.agents)
    ? snapshot.agents.map((raw: any) => {
        const id = safeString(raw.aid ?? raw.id ?? "?");
        const name = safeString(raw.name ?? `Agent ${id}`);
        const x = safeNumber(raw.x ?? raw.pos?.[0]);
        const y = safeNumber(raw.y ?? raw.pos?.[1]);
        const inventory = raw.inventory || {};
        const resources = Object.values(inventory).reduce((sum: number, value: any) => {
          const amount = safeNumber(value);
          return sum + amount;
        }, 0);
        const currentAction = typeof raw.current_action === "string" ? raw.current_action : null;
        const action = safeString(currentAction).toLowerCase();
        let status: AgentSummary["status"] = "idle";
        if (action.includes("move")) status = "moving";
        else if (action.includes("interact") || action.includes("fight") || action.includes("trade")) status = "engaged";
        else if (action.includes("rest") || action.includes("recover")) status = "recovering";

        return {
          id,
          name,
          faction: safeString(raw.group_id ?? raw.faction ?? "Cohort"),
          role: safeString(raw.role ?? (currentAction || "Citizen")),
          morale: safeNumber(raw.health ?? raw.morale ?? 100),
          resources,
          location: { x, y },
          status,
          currentAction
        };
      })
    : [];

  const turnId = safeNumber(snapshot.turn ?? worldPayload.turn);
  const revision = safeNumber(snapshot.revision ?? snapshot.turn_revision ?? 1, 1);
  const rawTimestamp = snapshot.timestamp ?? snapshot.occurred_at;
  let timestampSeconds: number;
  if (typeof rawTimestamp === "number" && Number.isFinite(rawTimestamp)) {
    timestampSeconds = rawTimestamp;
  } else if (typeof rawTimestamp === "string") {
    const numeric = Number(rawTimestamp);
    if (Number.isFinite(numeric)) {
      timestampSeconds = numeric;
    } else {
      const parsed = Date.parse(rawTimestamp);
      timestampSeconds = Number.isFinite(parsed) ? parsed / 1000 : Date.now() / 1000;
    }
  } else {
    timestampSeconds = Date.now() / 1000;
  }
  const occurredAt = typeof snapshot.occurred_at === "string"
    ? new Date(snapshot.occurred_at).toISOString()
    : new Date(timestampSeconds * 1000).toISOString();

  const hash = safeString(snapshot.hash, `${turnId}-${revision}-${Math.round(timestampSeconds * 1000)}`);

  const payload: TurnPayload = {
    turnId,
    revision,
    hash,
    occurredAt,
    latencyMs: safeNumber(snapshot.latencyMs ?? snapshot.latency_ms),
    events: Array.isArray(snapshot.events) ? snapshot.events : [],
    agents,
    cohorts: Array.isArray(snapshot.cohorts) ? snapshot.cohorts : [],
    heatmap: Array.isArray(snapshot.heatmap) ? snapshot.heatmap : [],
    interactions: Array.isArray(snapshot.interactions) ? snapshot.interactions : [],
    world
  };

  return payload;
}

export function buildAgentActionMap(agents: AgentSummary[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const agent of agents) {
    const label = agent.currentAction ? humanizeActionText(agent.currentAction) : STATUS_NAMES[agent.status] ?? "Idle";
    map[agent.id] = label;
  }
  return map;
}

export function humanizeActionText(action: string): string {
  if (!action) {
    return "Idle";
  }
  return action
    .replace(/[\[\]]/g, " ")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b(\w)/g, (match) => match.toUpperCase());
}

export interface NormalizedActionEvent {
  interaction: InteractionRecord;
  agentId: string | null;
  actionText: string | null;
}

export function normalizeActionEvents(events: any[]): NormalizedActionEvent[] {
  if (!Array.isArray(events)) {
    return [];
  }
  return events.map((event: any) => {
    const agentId =
      event.aid != null
        ? safeString(event.aid)
        : event.agent_id != null
          ? safeString(event.agent_id)
          : null;
    const actionText = typeof event.action === "string" ? humanizeActionText(event.action) : null;
    const name = safeString(event.name ?? agentId ?? "Agent");
    const turnId = safeNumber(event.turn);
    let tsValue: number;
    if (typeof event.timestamp === "number" && Number.isFinite(event.timestamp)) {
      tsValue = event.timestamp;
    } else if (typeof event.timestamp === "string") {
      const numeric = Number(event.timestamp);
      if (Number.isFinite(numeric)) {
        tsValue = numeric;
      } else {
        const parsed = Date.parse(event.timestamp);
        tsValue = Number.isFinite(parsed) ? parsed / 1000 : Date.now() / 1000;
      }
    } else {
      tsValue = Date.now() / 1000;
    }
    const isoTimestamp = new Date(tsValue * 1000).toISOString();
    const interaction: InteractionRecord = {
      id: safeString(event.id, `act-${agentId ?? "unknown"}-${Math.round(tsValue * 1000)}`),
      actor: "agent",
      turnId,
      intent: "Action",
      content: `${name}: ${actionText ?? "Action"}`,
      outcome: "",
      timestamp: isoTimestamp
    };
    return { interaction, agentId, actionText };
  });
}

export function normalizeLogEntries(entries: any[]): { timestamp: string; level: string; message: string }[] {
  if (!Array.isArray(entries)) {
    return [];
  }
  return entries.map((entry: any) => {
    let ts: number;
    if (typeof entry.timestamp === "number" && Number.isFinite(entry.timestamp)) {
      ts = entry.timestamp;
    } else if (typeof entry.timestamp === "string") {
      const numeric = Number(entry.timestamp);
      if (Number.isFinite(numeric)) {
        ts = numeric;
      } else {
        const parsed = Date.parse(entry.timestamp);
        ts = Number.isFinite(parsed) ? parsed / 1000 : Date.now() / 1000;
      }
    } else {
      ts = Date.now() / 1000;
    }
    return {
      timestamp: new Date(ts * 1000).toISOString(),
      level: safeString(entry.level ?? "INFO").toUpperCase(),
      message: safeString(entry.message ?? "")
    };
  });
}
