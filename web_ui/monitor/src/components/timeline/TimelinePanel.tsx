import { selectAlerts, useSimulationStore } from "../../state/store";
import type { Severity } from "../../types/simulation";
import "../../styles/timeline-panel.css";

const severityColor: Record<Severity, string> = {
  info: "badge--info",
  warning: "badge--warning",
  critical: "badge--critical"
};

export function TimelinePanel(): JSX.Element {
  const alerts = useSimulationStore(selectAlerts);

  return (
    <div className="panel panel--timeline">
      <div className="panel__header">
        <div>
          <h2>Event Timeline</h2>
          <p>Jump to significant simulation turns and cross-highlight agents</p>
        </div>
      </div>
      <div className="panel__content timeline-list">
        {alerts.slice(0, 25).map((event) => (
          <article key={event.id} className="timeline-item">
            <header>
              <span className={`badge ${severityColor[event.severity]}`}>{event.severity}</span>
              <h3>Turn {event.turnId}: {event.title}</h3>
            </header>
            <p>{event.description}</p>
            {event.relatedAgents.length > 0 && (
              <footer>
                <span>Agents: {event.relatedAgents.join(", ")}</span>
              </footer>
            )}
          </article>
        ))}
        {alerts.length === 0 && <p className="timeline-empty">Awaiting telemetry…</p>}
      </div>
    </div>
  );
}
