import { selectInteractionHistory, useSimulationStore } from "../../state/store";
import "../../styles/interaction-panel.css";

export function InteractionPanel(): JSX.Element {
  const interactions = useSimulationStore(selectInteractionHistory);

  return (
    <div className="panel panel--interaction">
      <div className="panel__header">
        <div>
          <h2>Interaction Ledger</h2>
          <p>Trace operator prompts and Trinity responses for replay</p>
        </div>
      </div>
      <div className="panel__content interaction-list">
        {interactions.map((interaction) => (
          <article key={interaction.id} className={`interaction-card interaction-card--${interaction.actor}`}>
            <header>
              <span>{formatActor(interaction.actor)}</span>
              <time dateTime={interaction.timestamp}>{formatTimestamp(interaction.timestamp)}</time>
            </header>
            <p className="interaction-card__intent">{interaction.intent}</p>
            <p className="interaction-card__content">{interaction.content}</p>
            <footer>
              <span>{interaction.outcome}</span>
              <span>Turn {interaction.turnId}</span>
            </footer>
          </article>
        ))}
        {interactions.length === 0 && <p className="interaction-empty">Awaiting user or agent actions.</p>}
      </div>
    </div>
  );
}

function formatActor(actor: "user" | "agent" | "trinity"): string {
  if (actor === "user") return "Operator";
  if (actor === "trinity") return "Trinity";
  return "Agent";
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
