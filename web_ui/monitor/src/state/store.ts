import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  AgentSummary,
  ConnectionState,
  InteractionRecord,
  TimelineEvent,
  TurnPayload,
  Structure
} from "../types/simulation";

const TURN_BUFFER_LIMIT = 120;

type PlaybackMode = "live" | "paused" | "scrubbing";

type SimulationState = {
  turns: TurnPayload[];
  currentTurnId: number | null;
  playbackMode: PlaybackMode;
  connection: ConnectionState;
  alerts: TimelineEvent[];
  interactionHistory: InteractionRecord[];
  logs: { timestamp: string; level: string; message: string }[];
  structures: Structure[];
  agentActions: Record<string, string>;
  selectedAgentId: string | null;
  selectedTile: { x: number; y: number } | null;
  ingestTurn: (turn: TurnPayload) => void;
  jumpToTurn: (turnId: number) => void;
  setPlaybackMode: (mode: PlaybackMode) => void;
  updateConnection: (partial: Partial<ConnectionState>) => void;
  recordInteraction: (interaction: InteractionRecord) => void;
  appendLogs: (entries: { timestamp: string; level: string; message: string }[]) => void;
  replaceLogs: (entries: { timestamp: string; level: string; message: string }[]) => void;
  setStructures: (items: Structure[]) => void;
  mergeStructures: (items: Structure[]) => void;
  updateAgentAction: (agentId: string, actionText: string) => void;
  setAgentActions: (actions: Record<string, string>) => void;
  setSelectedAgent: (agentId: string | null, location?: { x: number; y: number }) => void;
  setSelectedTile: (tile: { x: number; y: number } | null) => void;
};

const initialConnection: ConnectionState = {
  status: "connecting",
  lastTurnId: null,
  latencyMs: null,
  reconnectAttempts: 0
};

const baseState = {
  turns: [] as TurnPayload[],
  currentTurnId: null as number | null,
  playbackMode: "live" as PlaybackMode,
  connection: { ...initialConnection },
  alerts: [] as TimelineEvent[],
  interactionHistory: [] as InteractionRecord[],
  logs: [] as { timestamp: string; level: string; message: string }[],
  structures: [] as Structure[],
  agentActions: {} as Record<string, string>,
  selectedAgentId: null as string | null,
  selectedTile: null as { x: number; y: number } | null
};

export const useSimulationStore = create<SimulationState>()(
  immer((set, get) => ({
    ...baseState,
    ingestTurn: (turn: TurnPayload) => {
      const state = get();

      // Prevent rewinding to older revision without explicit jump.
      if (state.connection.lastTurnId && turn.turnId < state.connection.lastTurnId) {
        return;
      }

      set((draft) => {
        const lastIndex = draft.turns.length - 1;
        const lastTurn = lastIndex >= 0 ? draft.turns[lastIndex] : null;
        if (lastTurn && lastTurn.hash === turn.hash) {
          draft.turns[lastIndex] = turn;
        } else {
          draft.turns.push(turn);
          if (draft.turns.length > TURN_BUFFER_LIMIT) {
            draft.turns.splice(0, draft.turns.length - TURN_BUFFER_LIMIT);
          }
        }
        draft.connection.lastTurnId = turn.turnId;
        draft.connection.latencyMs = turn.latencyMs;
        draft.connection.status = "live";
        draft.alerts = mergeAlerts(draft.alerts, turn.events);
        draft.interactionHistory = mergeInteractions(draft.interactionHistory, turn.interactions);

        if (
          draft.playbackMode === "live" ||
          draft.currentTurnId === null ||
          (lastTurn && draft.currentTurnId === lastTurn.turnId)
        ) {
          draft.currentTurnId = turn.turnId;
        }
      });
    },
    jumpToTurn: (turnId: number) => {
      set((draft) => {
        const match = draft.turns.find((turn) => turn.turnId === turnId);
        if (!match) {
          return;
        }
        draft.currentTurnId = turnId;
        draft.playbackMode = "scrubbing";
      });
    },
    setPlaybackMode: (mode: PlaybackMode) => {
      set((draft) => {
        draft.playbackMode = mode;
        if (mode === "live" && draft.connection.lastTurnId) {
          draft.currentTurnId = draft.connection.lastTurnId;
        }
      });
    },
    updateConnection: (partial: Partial<ConnectionState>) => {
      set((draft) => {
        draft.connection = { ...draft.connection, ...partial };
      });
    },
    recordInteraction: (interaction: InteractionRecord) => {
      set((draft) => {
        draft.interactionHistory = mergeInteractions(draft.interactionHistory, [interaction]);
      });
    },
    appendLogs: (entries) => {
      set((draft) => {
        draft.logs.push(...entries);
        if (draft.logs.length > 400) {
          draft.logs.splice(0, draft.logs.length - 400);
        }
      });
    },
    replaceLogs: (entries) => {
      set((draft) => {
        draft.logs = entries.slice(-400);
      });
    },
    setStructures: (items) => {
      set((draft) => {
        draft.structures = items;
      });
    },
    mergeStructures: (items) => {
      set((draft) => {
        const map = new Map(draft.structures.map((s) => [s.id, s] as const));
        for (const it of items) {
          map.set(it.id, it);
        }
        draft.structures = Array.from(map.values());
      });
    },
    updateAgentAction: (agentId, actionText) => {
      set((draft) => {
        draft.agentActions[agentId] = actionText;
      });
    },
    setAgentActions: (actions) => {
      set((draft) => {
        draft.agentActions = { ...actions };
      });
    },
    setSelectedAgent: (agentId, location) => {
      set((draft) => {
        draft.selectedAgentId = agentId;
        if (location) {
          const shouldUpdateTile =
            !draft.selectedTile ||
            draft.selectedTile.x !== location.x ||
            draft.selectedTile.y !== location.y;
          if (shouldUpdateTile) {
            draft.selectedTile = { ...location };
          }
        }
      });
    },
    setSelectedTile: (tile) => {
      set((draft) => {
        if (!tile) {
          draft.selectedTile = null;
          return;
        }
        const shouldUpdateTile =
          !draft.selectedTile || draft.selectedTile.x !== tile.x || draft.selectedTile.y !== tile.y;
        if (shouldUpdateTile) {
          draft.selectedTile = { ...tile };
        }
      });
    }
  }))
);

export function resetSimulationStore(): void {
  useSimulationStore.setState((state) => ({
    ...state,
    ...baseState,
    connection: { ...initialConnection }
  }));
}

function mergeAlerts(existing: TimelineEvent[], incoming: TimelineEvent[]): TimelineEvent[] {
  const combined = [...existing];
  for (const event of incoming) {
    const index = combined.findIndex((item) => item.id === event.id);
    if (index >= 0) {
      combined[index] = event;
    } else {
      combined.push(event);
    }
  }
  return combined
    .sort((a, b) => b.turnId - a.turnId)
    .slice(0, 150);
}

function mergeInteractions(
  existing: InteractionRecord[],
  incoming: InteractionRecord[]
): InteractionRecord[] {
  const merged = new Map<string, InteractionRecord>();
  for (const item of [...existing, ...incoming]) {
    merged.set(item.id, item);
  }
  return Array.from(merged.values()).sort((a, b) => (a.timestamp > b.timestamp ? -1 : 1)).slice(0, 200);
}

export function selectCurrentTurn(state: SimulationState): TurnPayload | undefined {
  if (state.currentTurnId === null) {
    return undefined;
  }
  return state.turns.find((turn) => turn.turnId === state.currentTurnId);
}

export function selectRecentTurns(state: SimulationState): TurnPayload[] {
  return [...state.turns].sort((a, b) => b.turnId - a.turnId).slice(0, 20);
}

export function selectInteractionHistory(state: SimulationState): InteractionRecord[] {
  return state.interactionHistory;
}

export function selectLogs(state: SimulationState): { timestamp: string; level: string; message: string }[] {
  return state.logs;
}

export function selectAlerts(state: SimulationState): TimelineEvent[] {
  return state.alerts;
}

export function selectAgents(state: SimulationState): AgentSummary[] {
  return selectCurrentTurn(state)?.agents ?? [];
}

export function selectSelectedAgentId(state: SimulationState): string | null {
  return state.selectedAgentId;
}

export function selectSelectedTile(state: SimulationState): { x: number; y: number } | null {
  return state.selectedTile;
}

export function selectStructures(state: SimulationState): Structure[] {
  return state.structures;
}

export function selectAgentActions(state: SimulationState): Record<string, string> {
  return state.agentActions;
}
