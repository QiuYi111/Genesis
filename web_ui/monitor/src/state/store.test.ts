import { afterEach, describe, expect, it } from "vitest";
import { resetSimulationStore, selectCurrentTurn, useSimulationStore } from "./store";
import type { TurnPayload } from "../types/simulation";

const baseTurn: TurnPayload = {
  turnId: 1,
  revision: 1,
  hash: "abc",
  occurredAt: new Date().toISOString(),
  latencyMs: 100,
  events: [],
  agents: [],
  cohorts: [],
  heatmap: [],
  interactions: [],
  world: {
    size: 4,
    terrain: Array.from({ length: 16 }, () => "PLAINS"),
    resources: Array.from({ length: 16 }, () => ({}))
  }
};

describe("useSimulationStore", () => {
  afterEach(() => {
    resetSimulationStore();
  });

  it("keeps most recent turn as current in live mode", () => {
    const { ingestTurn } = useSimulationStore.getState();
    ingestTurn(baseTurn);
    ingestTurn({ ...baseTurn, turnId: 2 });

    const state = useSimulationStore.getState();
    expect(state.currentTurnId).toBe(2);
    expect(selectCurrentTurn(state)?.turnId).toBe(2);
  });

  it("does not overflow the buffer", () => {
    const { ingestTurn } = useSimulationStore.getState();
    for (let idx = 0; idx < 150; idx += 1) {
      ingestTurn({ ...baseTurn, turnId: idx + 10, hash: `hash-${idx}` });
    }
    expect(useSimulationStore.getState().turns.length).toBeLessThanOrEqual(120);
  });
});
