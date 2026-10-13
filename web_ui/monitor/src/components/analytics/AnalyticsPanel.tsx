import { useMemo } from "react";
import { selectCurrentTurn, useSimulationStore } from "../../state/store";
import type { CohortMetric } from "../../types/simulation";
import "../../styles/analytics-panel.css";

export function AnalyticsPanel(): JSX.Element {
  const currentTurn = useSimulationStore(selectCurrentTurn);

  const cohorts: CohortMetric[] = useMemo(() => currentTurn?.cohorts ?? [], [currentTurn]);

  return (
    <div className="panel panel--analytics">
      <div className="panel__header">
        <div>
          <h2>Cohort Signals</h2>
          <p>Compare faction health, morale, and logistical pressure</p>
        </div>
      </div>
      <div className="panel__content analytics-grid">
        {cohorts.map((metric) => (
          <article key={metric.name} className="metric-card">
            <header>
              <h3>{metric.name}</h3>
              <Trend trend={metric.trend} />
            </header>
            <strong>{metric.value.toFixed(1)}</strong>
            <span className="metric-card__unit">{metric.unit}</span>
          </article>
        ))}
        {cohorts.length === 0 && <p className="analytics-empty">No telemetry on active turn.</p>}
      </div>
    </div>
  );
}

function Trend({ trend }: { trend: CohortMetric["trend"] }): JSX.Element {
  const label =
    trend === "up" ? "Improving" : trend === "down" ? "Declining" : "Stable";
  return <span className={`trend trend--${trend}`}>{label}</span>;
}
