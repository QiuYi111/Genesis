import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { ConnectionState, InteractionRecord, TimelineEvent, TurnPayload } from "../types/simulation";

const TURN_BUFFER_LIMIT = 120;

type PlaybackMode = "live" | "paused" | "scrubbing";

type SimulationState = {
  turns: TurnPayload[];
  currentTurnId: number | null;
  playbackMode: PlaybackMode;
  connection: ConnectionState;
  alerts: TimelineEvent[];
  interactionHistory: InteractionRecord[];
  ingestTurn: (turn: TurnPayload) => void;
  jumpToTurn: (turnId: number) => void;
  setPlaybackMode: (mode: PlaybackMode) => void;
  updateConnection: (partial: Partial<ConnectionState>) => void;
  recordInteraction: (interaction: InteractionRecord) => void;
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
  interactionHistory: [] as InteractionRecord[]
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
        draft.turns.push(turn);
        if (draft.turns.length > TURN_BUFFER_LIMIT) {
          draft.turns.splice(0, draft.turns.length - TURN_BUFFER_LIMIT);
        }
        draft.connection.lastTurnId = turn.turnId;
        draft.connection.latencyMs = turn.latencyMs;
        draft.connection.status = "live";
        draft.alerts = mergeAlerts(draft.alerts, turn.events);
        draft.interactionHistory = mergeInteractions(draft.interactionHistory, turn.interactions);

        if (draft.playbackMode === "live" || draft.currentTurnId === null) {
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

export function selectAlerts(state: SimulationState): TimelineEvent[] {
  return state.alerts;
}
