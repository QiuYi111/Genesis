import { useEffect } from "react";
import { useSimulationStore } from "../state/store";
import { MockTurnStream } from "../services/mockTurnStream";

const stream = new MockTurnStream();

export function useMockTurnStream(): void {
  const ingestTurn = useSimulationStore((state) => state.ingestTurn);
  const updateConnection = useSimulationStore((state) => state.updateConnection);

  useEffect(() => {
    updateConnection({ status: "connecting" });
    const unsubscribe = stream.subscribe({
      onTurn: (turn) => {
        ingestTurn(turn);
      },
      onConnectionUpdate: (next) => {
        updateConnection(next);
      }
    });
    stream.start();
    return () => {
      unsubscribe();
      stream.stop();
    };
  }, [ingestTurn, updateConnection]);
}
