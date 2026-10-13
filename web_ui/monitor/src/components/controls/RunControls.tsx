import { useState } from "react";
import { startSimulation, stopSimulation } from "../../services/monitorApi";

export function RunControls(): JSX.Element {
  const [era, setEra] = useState("");
  const [turns, setTurns] = useState<string>("");
  const [numAgents, setNumAgents] = useState<string>("");
  const [worldSize, setWorldSize] = useState<string>("");
  const [scenario, setScenario] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleStart() {
    setBusy(true);
    try {
      await startSimulation({
        era: era || undefined,
        scenario: scenario || undefined,
        turns: turns ? Number(turns) : undefined,
        num_agents: numAgents ? Number(numAgents) : undefined,
        world_size: worldSize ? Number(worldSize) : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      await stopSimulation();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        placeholder="Era"
        value={era}
        onChange={(e) => setEra(e.target.value)}
        style={inputStyle}
      />
      <input
        placeholder="turns"
        inputMode="numeric"
        value={turns}
        onChange={(e) => setTurns(e.target.value)}
        style={{ ...inputStyle, width: 84 }}
      />
      <input
        placeholder="num_agents"
        inputMode="numeric"
        value={numAgents}
        onChange={(e) => setNumAgents(e.target.value)}
        style={{ ...inputStyle, width: 110 }}
      />
      <input
        placeholder="world_size"
        inputMode="numeric"
        value={worldSize}
        onChange={(e) => setWorldSize(e.target.value)}
        style={{ ...inputStyle, width: 110 }}
      />
      <input
        placeholder="scenario"
        value={scenario}
        onChange={(e) => setScenario(e.target.value)}
        style={{ ...inputStyle, width: 120 }}
      />
      <button onClick={handleStart} disabled={busy}>
        Start
      </button>
      <button onClick={handleStop} disabled={busy}>
        Stop
      </button>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "#11151d",
  color: "#e7ecf3",
  border: "1px solid #263047",
  borderRadius: 6,
  padding: "6px 8px",
  fontSize: 12,
};

