export type Severity = "info" | "warning" | "critical";

export interface AgentSummary {
  id: string;
  name: string;
  faction: string;
  role: string;
  morale: number;
  resources: number;
  location: {
    x: number;
    y: number;
  };
  status: "idle" | "moving" | "engaged" | "recovering";
}

export interface CohortMetric {
  name: string;
  value: number;
  trend: "up" | "down" | "flat";
  unit: string;
}

export interface HeatmapCell {
  x: number;
  y: number;
  intensity: number;
}

export interface TileResources {
  [resource: string]: number;
}

export interface WorldState {
  size: number;
  terrain: string[];
  resources: TileResources[];
}

export interface TimelineEvent {
  id: string;
  turnId: number;
  severity: Severity;
  title: string;
  description: string;
  relatedAgents: string[];
}

export interface InteractionRecord {
  id: string;
  turnId: number;
  actor: "user" | "agent" | "trinity";
  intent: string;
  content: string;
  outcome: string;
  timestamp: string;
}

export interface TurnPayload {
  turnId: number;
  revision: number;
  hash: string;
  occurredAt: string;
  latencyMs: number;
  events: TimelineEvent[];
  agents: AgentSummary[];
  cohorts: CohortMetric[];
  heatmap: HeatmapCell[];
  interactions: InteractionRecord[];
  world: WorldState;
}

export interface ConnectionState {
  status: "connecting" | "live" | "degraded" | "offline";
  lastTurnId: number | null;
  latencyMs: number | null;
  reconnectAttempts: number;
}
