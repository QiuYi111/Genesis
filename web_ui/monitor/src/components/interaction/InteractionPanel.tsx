import { selectInteractionHistory, useSimulationStore } from "../../state/store";
import { useState } from "react";
import { agentInteraction, trinityBroadcast } from "../../services/monitorApi";
import "../../styles/interaction-panel.css";

export function InteractionPanel(): JSX.Element {
  const interactions = useSimulationStore(selectInteractionHistory);
  const [trinityMsg, setTrinityMsg] = useState("");
  const [trinityTargets, setTrinityTargets] = useState("");
  const [agentFrom, setAgentFrom] = useState("");
  const [agentTo, setAgentTo] = useState("");
  const [agentMsg, setAgentMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSendTrinity() {
    if (!trinityMsg.trim()) return;
    setBusy(true);
    try {
      const targets = trinityTargets
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((n) => Number(n))
        .filter((n) => Number.isFinite(n));
      await trinityBroadcast(trinityMsg.trim(), targets.length ? targets : undefined);
      setTrinityMsg("");
      setTrinityTargets("");
    } finally {
      setBusy(false);
    }
  }

  async function onSendAgent() {
    const a = Number(agentFrom);
    const b = Number(agentTo);
    if (!Number.isFinite(a) || !Number.isFinite(b) || !agentMsg.trim()) return;
    setBusy(true);
    try {
      await agentInteraction(a, b, agentMsg.trim());
      setAgentMsg("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel panel--interaction">
      <div className="panel__header">
        <div>
          <h2>Interaction Ledger</h2>
          <p>Trace operator prompts and Trinity responses for replay</p>
        </div>
      </div>
      <div className="panel__content interaction-list">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 8px" }}>Trinity 广播</h3>
            <input
              placeholder="内容"
              value={trinityMsg}
              onChange={(e) => setTrinityMsg(e.target.value)}
              style={inputStyle}
            />
            <input
              placeholder="targets: 逗号分隔 AID 列表，可留空"
              value={trinityTargets}
              onChange={(e) => setTrinityTargets(e.target.value)}
              style={inputStyle}
            />
            <button onClick={onSendTrinity} disabled={busy} style={{ marginTop: 6 }}>
              发送广播
            </button>
          </div>
          <div>
            <h3 style={{ margin: "0 0 8px" }}>Agent 互动</h3>
            <div style={{ display: "flex", gap: 6 }}>
              <input placeholder="source" value={agentFrom} onChange={(e) => setAgentFrom(e.target.value)} style={inputStyle} />
              <input placeholder="target" value={agentTo} onChange={(e) => setAgentTo(e.target.value)} style={inputStyle} />
            </div>
            <input
              placeholder="内容"
              value={agentMsg}
              onChange={(e) => setAgentMsg(e.target.value)}
              style={inputStyle}
            />
            <button onClick={onSendAgent} disabled={busy} style={{ marginTop: 6 }}>
              发送互动
            </button>
          </div>
        </div>
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

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "#11151d",
  color: "#e7ecf3",
  border: "1px solid #263047",
  borderRadius: 6,
  padding: "6px 8px",
  fontSize: 12,
  marginBottom: 6,
};
