export interface StartPayload {
  era?: string;
  scenario?: string;
  turns?: number;
  num_agents?: number;
  world_size?: number;
  overrides?: string[];
}

export interface SimulationSnapshot {
  world?: unknown;
  agents?: unknown[];
  turn?: number;
  timestamp?: number;
  occurred_at?: string;
  logs?: unknown[];
  actions?: unknown[];
  structures?: unknown[];
  events?: unknown[];
  heatmap?: unknown[];
  interactions?: unknown[];
  cohorts?: unknown[];
}

async function get<T>(url: string): Promise<T> {
  const resp = await fetch(url, { method: "GET" });
  if (!resp.ok) {
    throw new Error(`${resp.status}`);
  }
  return (await resp.json()) as T;
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!resp.ok) {
    let msg = `${resp.status}`;
    try {
      const j = await resp.json();
      if (j && j.error) msg = j.error;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return (await resp.json()) as T;
}

export async function startSimulation(payload: StartPayload): Promise<void> {
  await post("/api/simulation/start", payload);
}

export async function stopSimulation(): Promise<void> {
  await post("/api/simulation/stop", {});
}

export async function fetchSimulationSnapshot(): Promise<SimulationSnapshot | null> {
  try {
    const data = await get<{ world?: unknown } & SimulationSnapshot>("/api/simulation-data");
    return data ?? null;
  } catch {
    return null;
  }
}

export async function trinityBroadcast(content: string, targets?: number[]): Promise<void> {
  await post("/api/interactions", { role: "trinity", action: "broadcast", content, targets });
}

export async function agentInteraction(agentId: number, targetId: number, content: string): Promise<void> {
  await post("/api/interactions", {
    role: "agent",
    agent_id: agentId,
    target_id: targetId,
    interaction_type: "chat",
    content,
  });
}

