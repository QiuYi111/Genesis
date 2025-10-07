import { selectLogs, useSimulationStore } from "../../state/store";

export function MessageBox(): JSX.Element {
  const logs = useSimulationStore(selectLogs);
  return (
    <div style={wrapper}>
      <div style={header}>Simulation Messages</div>
      <div style={box}>
        {logs.map((l, idx) => (
          <div key={`${idx}-${l.timestamp}`} style={row}>
            <span style={time}>{formatTime(l.timestamp)}</span>
            <span style={{ ...level, ...levelColor(l.level) }}>{l.level}</span>
            <span style={msg}>{l.message}</span>
          </div>
        ))}
        {logs.length === 0 && <div style={empty}>No messages yet.</div>}
      </div>
    </div>
  );
}

function levelColor(lv: string): React.CSSProperties {
  const t = lv.toUpperCase();
  if (t === "ERROR" || t === "CRITICAL") return { color: "#ff6b6b", borderColor: "#ff6b6b33" };
  if (t === "WARNING" || t === "WARN") return { color: "#ffd166", borderColor: "#ffd16633" };
  return { color: "#9be9a8", borderColor: "#9be9a833" };
}

function formatTime(value: string): string {
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const wrapper: React.CSSProperties = {
  border: "1px solid #20283b",
  borderRadius: 8,
  background: "#0f131a",
};
const header: React.CSSProperties = {
  padding: "6px 8px",
  fontSize: 12,
  color: "#8aa0b4",
  borderBottom: "1px solid #20283b",
};
const box: React.CSSProperties = {
  maxHeight: 140,
  overflow: "auto",
  padding: 8,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  fontSize: 12,
};
const row: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "86px 68px 1fr",
  gap: 8,
  alignItems: "baseline",
  padding: "2px 0",
};
const time: React.CSSProperties = { color: "#8aa0b4" };
const level: React.CSSProperties = { border: "1px solid", borderRadius: 999, padding: "1px 6px" };
const msg: React.CSSProperties = { whiteSpace: "pre-wrap" };
const empty: React.CSSProperties = { color: "#8aa0b4" };

