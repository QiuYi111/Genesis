import "../../styles/panel.css";
import { useMemo } from "react";
import { selectCurrentTurn, useSimulationStore } from "../../state/store";

const GRID_SIZE = 20;

export function MapPanel(): JSX.Element {
  const currentTurn = useSimulationStore(selectCurrentTurn);

  const heatmapGrid = useMemo(() => {
    if (!currentTurn) {
      return Array.from({ length: GRID_SIZE * GRID_SIZE }, () => 0);
    }
    const base = Array.from({ length: GRID_SIZE * GRID_SIZE }, () => 0);
    for (const cell of currentTurn.heatmap) {
      const index = cell.y * GRID_SIZE + cell.x;
      if (index >= 0 && index < base.length) {
        base[index] = cell.intensity;
      }
    }
    return base;
  }, [currentTurn]);

  return (
    <div className="panel panel--map">
      <div className="panel__header">
        <div>
          <h2>Spatial Overview</h2>
          <p>Heatmap of morale and resource pressure for turn {currentTurn?.turnId ?? "—"}</p>
        </div>
        <span className="panel__badge">{currentTurn ? formatTime(currentTurn.occurredAt) : "Awaiting stream"}</span>
      </div>
      <div className="map-grid" role="presentation">
        {heatmapGrid.map((intensity, idx) => {
          const hue = 180 - intensity * 120;
          const alpha = 0.12 + intensity * 0.85;
          return <div key={idx} style={{ backgroundColor: `hsla(${hue}, 90%, 55%, ${alpha})` }} />;
        })}
      </div>
      <footer className="panel__footer">
        <div className="panel__footer-metric">
          <span className="label">Live Agents</span>
          <strong>{currentTurn?.agents.length ?? 0}</strong>
        </div>
        <div className="panel__footer-metric">
          <span className="label">Critical Alerts</span>
          <strong>
            {currentTurn?.events.filter((event) => event.severity === "critical").length ?? 0}
          </strong>
        </div>
        <div className="panel__footer-metric">
          <span className="label">Latency</span>
          <strong>{currentTurn ? `${currentTurn.latencyMs.toFixed(0)} ms` : "—"}</strong>
        </div>
      </footer>
    </div>
  );
}

function formatTime(value: string): string {
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
