export interface StartPayload {
  era?: string;
  scenario?: string;
  turns?: number;
  num_agents?: number;
  world_size?: number;
  overrides?: string[];
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

