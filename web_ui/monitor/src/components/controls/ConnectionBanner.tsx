import { useEffect } from "react";
import { useSimulationStore } from "../../state/store";

import "../../styles/connection-banner.css";

export function ConnectionBanner(): JSX.Element | null {
  const connection = useSimulationStore((state) => state.connection);
  const updateConnection = useSimulationStore((state) => state.updateConnection);

  useEffect(() => {
    if (connection.status === "offline") {
      const timer = window.setTimeout(() => {
        updateConnection({ status: "connecting", reconnectAttempts: connection.reconnectAttempts + 1 });
      }, 4000);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [connection, updateConnection]);

  if (connection.status === "live" && connection.latencyMs && connection.latencyMs < 120) {
    return null;
  }

  const tone = connection.status === "offline" ? "danger" : connection.status === "degraded" ? "warning" : "info";

  return (
    <div className={`connection-banner connection-banner--${tone}`} role="status">
      <strong>{connection.status.toUpperCase()}</strong>
      <span>
        Latency: {connection.latencyMs ? `${connection.latencyMs.toFixed(0)} ms` : "—"} · Last turn:
        {" "}
        {connection.lastTurnId ?? "n/a"}
      </span>
    </div>
  );
}
