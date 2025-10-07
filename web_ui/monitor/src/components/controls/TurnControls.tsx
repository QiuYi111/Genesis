import { useMemo } from "react";
import {
  selectRecentTurns,
  useSimulationStore
} from "../../state/store";

import "../../styles/turn-controls.css";

export function TurnControls(): JSX.Element {
  const playbackMode = useSimulationStore((state) => state.playbackMode);
  const setPlaybackMode = useSimulationStore((state) => state.setPlaybackMode);
  const jumpToTurn = useSimulationStore((state) => state.jumpToTurn);
  const recentTurns = useSimulationStore(selectRecentTurns);
  const connection = useSimulationStore((state) => state.connection);

  const isLive = playbackMode === "live";

  const badgeText = useMemo(() => {
    switch (connection.status) {
      case "connecting":
        return "Negotiating stream";
      case "degraded":
        return `Degraded · ${connection.reconnectAttempts} retries`;
      case "offline":
        return "Offline – showing cached buffer";
      default:
        return connection.lastTurnId ? `Live · Turn ${connection.lastTurnId}` : "Standby";
    }
  }, [connection]);

  return (
    <div className="turn-controls">
      <div className="turn-controls__primary">
        <button
          className={isLive ? "active" : ""}
          onClick={() => setPlaybackMode("live")}
          aria-pressed={isLive}
        >
          Live
        </button>
        <button
          className={playbackMode === "paused" ? "active" : ""}
          onClick={() => setPlaybackMode("paused")}
          aria-pressed={playbackMode === "paused"}
        >
          Pause
        </button>
        <button
          className={playbackMode === "scrubbing" ? "active" : ""}
          onClick={() => setPlaybackMode("scrubbing")}
          aria-pressed={playbackMode === "scrubbing"}
        >
          Investigate
        </button>
      </div>
      <div className="turn-controls__secondary">
        <span className={`turn-controls__status turn-controls__status--${connection.status}`}>
          {badgeText}
        </span>
        <label className="turn-controls__scrub">
          <span>Scrub to turn</span>
          <select
            value={""}
            onChange={(event) => {
              const targetTurn = Number(event.target.value);
              if (!Number.isNaN(targetTurn)) {
                jumpToTurn(targetTurn);
              }
            }}
          >
            <option value="" disabled>
              Recent turns
            </option>
            {recentTurns.map((turn) => (
              <option key={turn.turnId} value={turn.turnId}>
                Turn {turn.turnId} · latency {turn.latencyMs.toFixed(0)} ms
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
