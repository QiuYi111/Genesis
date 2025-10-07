import type {
  AgentSummary,
  CohortMetric,
  ConnectionState,
  InteractionRecord,
  TimelineEvent,
  TurnPayload
} from "../types/simulation";

interface Subscriber {
  onTurn: (turn: TurnPayload) => void;
  onConnectionUpdate?: (connection: Partial<ConnectionState>) => void;
}

export class MockTurnStream {
  private subscribers = new Set<Subscriber>();
  private tickHandle: number | null = null;
  private turnId = 0;

  subscribe(subscriber: Subscriber): () => void {
    this.subscribers.add(subscriber);
    return () => {
      this.subscribers.delete(subscriber);
    };
  }

  start(): void {
    if (this.tickHandle !== null) {
      return;
    }
    this.tickHandle = window.setInterval(() => {
      this.emitTurn();
    }, 2750);
  }

  stop(): void {
    if (this.tickHandle !== null) {
      window.clearInterval(this.tickHandle);
      this.tickHandle = null;
    }
  }

  private emitTurn(): void {
    this.turnId += 1;
    const now = new Date();
    const latency = 40 + Math.random() * 120;

    if (Math.random() > 0.88) {
      this.pushConnection({ status: "degraded", latencyMs: latency, reconnectAttempts: 0 });
    } else {
      this.pushConnection({ status: "live", latencyMs: latency });
    }

    const turn: TurnPayload = {
      turnId: this.turnId,
      revision: 1,
      hash: cryptoRandomId(),
      occurredAt: now.toISOString(),
      latencyMs: latency,
      events: this.generateEvents(this.turnId),
      agents: this.generateAgents(),
      cohorts: this.generateCohorts(),
      heatmap: this.generateHeatmap(),
      interactions: this.generateInteractions(this.turnId, now)
    };

    for (const subscriber of this.subscribers) {
      subscriber.onTurn(turn);
    }
  }

  private pushConnection(update: Partial<ConnectionState>): void {
    for (const subscriber of this.subscribers) {
      subscriber.onConnectionUpdate?.(update);
    }
  }

  private generateEvents(turnId: number): TimelineEvent[] {
    const seeds: TimelineEvent[] = [
      {
        id: `alert-${turnId}-conflict`,
        turnId,
        severity: Math.random() > 0.8 ? "critical" : "warning",
        title: "Faction skirmish",
        description: "Border friction escalated around the northern ridge.",
        relatedAgents: ["A-03", "B-11"]
      },
      {
        id: `alert-${turnId}-resource`,
        turnId,
        severity: "info",
        title: "Resource caravan dispatched",
        description: "Logistics routed surplus grain to coastal settlements.",
        relatedAgents: ["L-07"]
      }
    ];

    if (Math.random() > 0.7) {
      seeds.push({
        id: `alert-${turnId}-famine`,
        turnId,
        severity: "critical",
        title: "Famine risk",
        description: "Morale collapsing in delta enclave due to spoiled harvest.",
        relatedAgents: ["C-22", "C-24", "C-27"]
      });
    }

    return seeds;
  }

  private generateAgents(): AgentSummary[] {
    return Array.from({ length: 42 }, (_, idx) => ({
      id: `A-${idx.toString().padStart(2, "0")}`,
      name: `Agent ${idx}`,
      faction: idx % 2 === 0 ? "Aurora" : "Horizon",
      role: idx % 3 === 0 ? "Scout" : "Diplomat",
      morale: 50 + Math.sin((this.turnId + idx) / 3) * 30,
      resources: 100 + Math.cos((this.turnId + idx) / 5) * 40,
      location: {
        x: Math.floor(Math.random() * 20),
        y: Math.floor(Math.random() * 20)
      },
      status: (idx % 5 === 0 ? "engaged" : "moving") as AgentSummary["status"]
    }));
  }

  private generateCohorts(): CohortMetric[] {
    return [
      {
        name: "Aurora Coalition",
        value: 72 + Math.sin(this.turnId / 2) * 6,
        trend: Math.random() > 0.5 ? "up" : "flat",
        unit: "morale index"
      },
      {
        name: "Horizon Syndicate",
        value: 61 + Math.cos(this.turnId / 3) * 4,
        trend: Math.random() > 0.6 ? "down" : "flat",
        unit: "morale index"
      },
      {
        name: "Logistics",
        value: 48 + Math.sin(this.turnId / 1.5) * 8,
        trend: Math.random() > 0.55 ? "up" : "down",
        unit: "supply health"
      }
    ];
  }

  private generateHeatmap() {
    return Array.from({ length: 60 }, () => ({
      x: Math.floor(Math.random() * 20),
      y: Math.floor(Math.random() * 20),
      intensity: Math.random()
    }));
  }

  private generateInteractions(turnId: number, now: Date): InteractionRecord[] {
    const records: InteractionRecord[] = [
      {
        id: `interaction-${turnId}-op`,
        actor: "user",
        turnId,
        intent: "Deploy scouts",
        content: "Requesting recon sweep over ridge cluster 7.",
        outcome: "Trinity queued scout action",
        timestamp: new Date(now.getTime() - 1200).toISOString()
      },
      {
        id: `interaction-${turnId}-trinity`,
        actor: "trinity",
        turnId,
        intent: "Advisory",
        content: "Detected rising famine risk; recommend rationing directive.",
        outcome: "Operator acknowledged",
        timestamp: new Date(now.getTime() - 800).toISOString()
      }
    ];

    if (Math.random() > 0.5) {
      records.push({
        id: `interaction-${turnId}-agent`,
        actor: "agent",
        turnId,
        intent: "Trade offer",
        content: "Agent C-22 proposes grain exchange with Horizon enclave.",
        outcome: "Pending operator approval",
        timestamp: new Date(now.getTime() - 400).toISOString()
      });
    }

    return records;
  }
}

function cryptoRandomId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
