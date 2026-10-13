import type {
  AgentSummary,
  CohortMetric,
  ConnectionState,
  InteractionRecord,
  TileResources,
  TimelineEvent,
  TurnPayload,
  WorldState
} from "../types/simulation";

interface Subscriber {
  onTurn: (turn: TurnPayload) => void;
  onConnectionUpdate?: (connection: Partial<ConnectionState>) => void;
}

const STATUS_SEQUENCE: AgentSummary["status"][] = ["moving", "engaged", "recovering", "idle"];
const ROLES = ["Scout", "Diplomat", "Strategist", "Mediator"] as const;
const FACTIONS = ["Aurora", "Horizon", "Zephyr"] as const;

export class MockTurnStream {
  private subscribers = new Set<Subscriber>();
  private tickHandle: number | null = null;
  private turnId = 0;
  private readonly worldSize = 32;
  private readonly terrain: WorldState["terrain"];
  private readonly baseResources: TileResources[];

  constructor() {
    const baseWorld = this.generateWorld();
    this.terrain = baseWorld.terrain;
    this.baseResources = baseWorld.resources;
  }

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
      interactions: this.generateInteractions(this.turnId, now),
      world: this.buildWorldSnapshot()
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
    return Array.from({ length: 48 }, (_, idx) => {
      const faction = FACTIONS[idx % FACTIONS.length];
      const role = ROLES[idx % ROLES.length];
      const status = STATUS_SEQUENCE[(idx + this.turnId) % STATUS_SEQUENCE.length];
      const morale = clamp(52 + Math.sin((this.turnId + idx) / 2.8) * 32, 20, 98);
      const stores = clamp(88 + Math.cos((this.turnId + idx * 1.3) / 4.6) * 38, 30, 140);
      const wanderX = Math.sin((this.turnId + idx * 1.7) / 3.2) * 0.5 + 0.5;
      const wanderY = Math.cos((this.turnId * 0.8 + idx * 1.1) / 3.4) * 0.5 + 0.5;
      const x = clamp(Math.floor(wanderX * (this.worldSize - 1)), 0, this.worldSize - 1);
      const y = clamp(Math.floor(wanderY * (this.worldSize - 1)), 0, this.worldSize - 1);

      return {
        id: `A-${idx.toString().padStart(2, "0")}`,
        name: `Agent ${idx}`,
        faction,
        role,
        morale,
        resources: stores,
        location: { x, y },
        status
      };
    });
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
        name: "Zephyr Compact",
        value: 58 + Math.sin(this.turnId / 1.7) * 5,
        trend: Math.random() > 0.55 ? "up" : "down",
        unit: "influence"
      },
      {
        name: "Logistics",
        value: 48 + Math.sin(this.turnId / 1.5) * 8,
        trend: Math.random() > 0.55 ? "up" : "down",
        unit: "supply health"
      }
    ];
  }

  private generateHeatmap(): TurnPayload["heatmap"] {
    const cells: TurnPayload["heatmap"] = [];
    for (let y = 0; y < this.worldSize; y += 1) {
      for (let x = 0; x < this.worldSize; x += 1) {
        const idx = y * this.worldSize + x;
        const base = (Math.sin((this.turnId + x * 3 + y * 2) / 5) + 1) / 2;
        const resourceBias = (this.baseResources[idx]?.food ?? 0) / 16;
        const intensity = clamp(base * 0.6 + resourceBias * 0.5, 0, 1);
        if (intensity > 0.08) {
          cells.push({ x, y, intensity });
        }
      }
    }
    return cells;
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

  private generateWorld(): WorldState {
    const terrain: WorldState["terrain"] = [];
    const resources: TileResources[] = [];

    for (let y = 0; y < this.worldSize; y += 1) {
      for (let x = 0; x < this.worldSize; x += 1) {
        const elevation = Math.sin(x * 0.27) + Math.cos(y * 0.19);
        const moisture = Math.sin((x + y) * 0.14) + Math.cos((x - y) * 0.11) * 0.6;
        const rim = Math.min(x, y, this.worldSize - 1 - x, this.worldSize - 1 - y);

        let terrainType: string;
        if (rim < 2 || elevation < -1.2) {
          terrainType = "WATER";
        } else if (elevation > 1.2) {
          terrainType = "MOUNTAIN";
        } else if (elevation > 0.8) {
          terrainType = moisture > 0.3 ? "FOREST" : "GRASSLAND";
        } else if (moisture > 1) {
          terrainType = "SWAMP";
        } else if (moisture < -1) {
          terrainType = "DESERT";
        } else if (moisture < -0.2) {
          terrainType = "PLAINS";
        } else if (elevation < -0.6) {
          terrainType = "TUNDRA";
        } else {
          terrainType = "GRASSLAND";
        }

        terrain.push(terrainType);
        resources.push(this.seedResources(terrainType, x, y));
      }
    }

    return { size: this.worldSize, terrain, resources };
  }

  private seedResources(terrain: string, x: number, y: number): TileResources {
    const tile: TileResources = {};
    const noise = Math.sin((x + 13) * 0.45) + Math.cos((y + 7) * 0.32);

    const allocate = (type: keyof TileResources, base: number, variance: number) => {
      const value = Math.max(0, Math.round(base + noise * variance));
      if (value > 0) {
        tile[type] = value;
      }
    };

    switch (terrain) {
      case "FOREST":
        allocate("wood", 8, 3);
        allocate("fruit", 3, 2);
        allocate("food", 2, 2);
        break;
      case "MOUNTAIN":
        allocate("stone", 7, 3);
        allocate("metal", 5, 2);
        break;
      case "WATER":
        allocate("water", 10, 3);
        allocate("food", 2, 2);
        break;
      case "PLAINS":
        allocate("food", 5, 3);
        allocate("wood", 2, 2);
        break;
      case "DESERT":
        allocate("stone", 3, 2);
        allocate("metal", 2, 2);
        break;
      case "SWAMP":
        allocate("water", 6, 2);
        allocate("food", 3, 2);
        break;
      case "TUNDRA":
        allocate("stone", 2, 1);
        allocate("food", 1, 1);
        break;
      default:
        allocate("food", 4, 2);
        allocate("wood", 3, 2);
        break;
    }

    return tile;
  }

  private buildWorldSnapshot(): WorldState {
    const resources = this.baseResources.map((tile, idx) => {
      const x = idx % this.worldSize;
      const y = Math.floor(idx / this.worldSize);
      const seasonal = 1 + Math.sin((this.turnId + x * 2 + y) / 8) * 0.18;
      const supplyShock = 1 + Math.cos((this.turnId + x + y * 2) / 11) * 0.12;
      const next: TileResources = {};
      for (const [key, value] of Object.entries(tile)) {
        const amount = Math.max(0, Math.round(value * seasonal * supplyShock));
        if (amount > 0) {
          next[key] = amount;
        }
      }
      return next;
    });

    return {
      size: this.worldSize,
      terrain: this.terrain,
      resources
    };
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function cryptoRandomId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
