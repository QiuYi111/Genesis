import "../../styles/panel.css";
import "../../styles/map-panel.css";
import type { MouseEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  selectAgents,
  selectCurrentTurn,
  selectSelectedAgentId,
  selectSelectedTile,
  useSimulationStore
} from "../../state/store";
import { selectStructures, selectAgentActions } from "../../state/store";
import type { AgentSummary, TileResources, WorldState, Structure } from "../../types/simulation";

// Use adjustable tile size to make the board feel lighter
const DEFAULT_TILE_SIZE = 12;
const TERRAIN_COLORS: Record<string, string> = {
  MOUNTAIN: "#4c4f69",
  FOREST: "#2f7e4d",
  GRASSLAND: "#4c9c58",
  PLAINS: "#6ea45a",
  DESERT: "#c8a15a",
  WATER: "#2d5b9c",
  SWAMP: "#3f6854",
  TUNDRA: "#9ba7b7",
  DEFAULT: "#506070"
};

const RESOURCE_EMOJI: Record<string, string> = {
  wood: "🪵",
  stone: "🪨",
  water: "💧",
  food: "🌾",
  metal: "⛓️",
  fruit: "🍇"
};

const STATUS_LABEL: Record<AgentSummary["status"], string> = {
  idle: "Idle",
  moving: "Moving",
  engaged: "Engaged",
  recovering: "Recovering"
};

const LEGEND_ORDER: Array<{ terrain: keyof typeof TERRAIN_COLORS; label: string }> = [
  { terrain: "FOREST", label: "Forest" },
  { terrain: "GRASSLAND", label: "Grassland" },
  { terrain: "PLAINS", label: "Plains" },
  { terrain: "MOUNTAIN", label: "Mountain" },
  { terrain: "DESERT", label: "Desert" },
  { terrain: "SWAMP", label: "Swamp" },
  { terrain: "TUNDRA", label: "Tundra" },
  { terrain: "WATER", label: "Water" }
];

interface HoverState {
  x: number;
  y: number;
  clientX: number;
  clientY: number;
  agent?: AgentSummary;
}

export function MapPanel(): JSX.Element {
  const currentTurn = useSimulationStore(selectCurrentTurn);
  const agents = useSimulationStore(selectAgents);
  const selectedAgentId = useSimulationStore(selectSelectedAgentId);
  const selectedTile = useSimulationStore(selectSelectedTile);
  const setSelectedAgent = useSimulationStore((state) => state.setSelectedAgent);
  const setSelectedTile = useSimulationStore((state) => state.setSelectedTile);
  const structures = useSimulationStore(selectStructures);
  const agentActionsMap = useSimulationStore(selectAgentActions);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [tileSize, setTileSize] = useState<number>(DEFAULT_TILE_SIZE);
  const [hover, setHover] = useState<HoverState | null>(null);
  const [showResources, setShowResources] = useState(true);
  const [showStatus, setShowStatus] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showStructures, setShowStructures] = useState(true);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const world = currentTurn?.world;

  const heatmapLookup = useMemo(() => {
    const map = new Map<string, number>();
    if (!currentTurn) {
      return map;
    }
    for (const cell of currentTurn.heatmap) {
      map.set(makeTileKey(cell.x, cell.y), cell.intensity);
    }
    return map;
  }, [currentTurn]);

  const agentClusters = useMemo(() => {
    const clusters = new Map<string, AgentSummary[]>();
    for (const agent of agents) {
      const key = makeTileKey(agent.location.x, agent.location.y);
      const existing = clusters.get(key) ?? [];
      existing.push(agent);
      existing.sort((a, b) => a.id.localeCompare(b.id));
      clusters.set(key, existing);
    }
    return clusters;
  }, [agents]);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId]
  );

  const roster = useMemo(() => {
    return [...agents].sort((a, b) => {
      if (a.faction !== b.faction) {
        return a.faction.localeCompare(b.faction);
      }
      return b.morale - a.morale;
    });
  }, [agents]);

  useEffect(() => {
    if (!world) {
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const pixelRatio = window.devicePixelRatio || 1;
    const mapSize = world.size * tileSize;
    canvas.width = mapSize * pixelRatio;
    canvas.height = mapSize * pixelRatio;
    canvas.style.width = "100%";
    canvas.style.height = "100%";

    context.save();
    context.scale(pixelRatio, pixelRatio);
    context.clearRect(0, 0, mapSize, mapSize);
    context.fillStyle = theme === "dark" ? "#05070f" : "#f6f8fa";
    context.fillRect(0, 0, mapSize, mapSize);

    for (let y = 0; y < world.size; y += 1) {
      for (let x = 0; x < world.size; x += 1) {
        const index = y * world.size + x;
        const terrain = world.terrain[index];
        const color = TERRAIN_COLORS[terrain] ?? TERRAIN_COLORS.DEFAULT;
        const originX = x * tileSize;
        const originY = y * tileSize;

        context.fillStyle = color;
        context.fillRect(originX, originY, tileSize, tileSize);

        const intensity = heatmapLookup.get(makeTileKey(x, y)) ?? 0;
        if (showHeatmap && intensity > 0.01) {
          context.fillStyle = `rgba(255, 156, 94, ${0.2 + intensity * 0.55})`;
          context.fillRect(originX, originY, tileSize, tileSize);
        }

        // Subtle grid only when zoomed enough
        if (tileSize >= 14) {
          context.strokeStyle = "rgba(6, 9, 18, 0.5)";
          context.strokeRect(originX, originY, tileSize, tileSize);
        }

        // Draw up to two resource emojis for a quick glance
        const resources = world.resources[index] ?? {};
        const entries = Object.entries(resources)
          .filter(([, v]) => (v as number) > 0)
          .sort((a, b) => (b[1] as number) - (a[1] as number))
          .slice(0, 2);
        if (showResources && entries.length) {
          context.font = `${Math.max(10, tileSize * 0.9)}px system-ui, Apple Color Emoji`;
          context.textAlign = "left";
          context.textBaseline = "top";
          const emojiSize = Math.max(10, tileSize * 0.8);
          let offset = 1;
          for (const [k] of entries) {
            const em = RESOURCE_EMOJI[k] ?? "";
            if (em) {
              context.fillText(em, originX + 1, originY + offset);
              offset += Math.max(emojiSize * 0.55, 10);
            }
          }
        }
      }
    }

    if (selectedTile && isTileInside(world, selectedTile)) {
      context.lineWidth = 2;
      context.strokeStyle = "rgba(123, 241, 168, 0.9)";
      context.strokeRect(
        selectedTile.x * tileSize + 1,
        selectedTile.y * tileSize + 1,
        tileSize - 2,
        tileSize - 2
      );
    }

    for (const [key, cluster] of agentClusters.entries()) {
      const [tileX, tileY] = key.split(":").map(Number);
      const baseX = tileX * tileSize;
      const baseY = tileY * tileSize;

      cluster.forEach((agent, index) => {
        const offset = agentOffset(index, tileSize, Math.max(6, tileSize * 0.6));
        const centerX = baseX + offset.x + tileSize / 2;
        const centerY = baseY + offset.y + tileSize / 2;

        // Agent emoji based on age/status
        const emoji = agentEmoji(agent);

        context.font = `${Math.max(12, tileSize)}px system-ui, Apple Color Emoji`;
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(emoji, centerX, centerY);

        // Selected ring
        if (agent.id === selectedAgentId) {
          context.strokeStyle = "rgba(255,255,255,0.85)";
          context.lineWidth = 2;
          context.beginPath();
          context.arc(centerX, centerY, Math.max(6, tileSize * 0.4), 0, Math.PI * 2);
          context.stroke();
        }

        // Status blip in corner
        const status = showStatus ? statusEmoji(agent.status) : "";
        if (status) {
          context.font = `${Math.max(10, tileSize * 0.8)}px system-ui, Apple Color Emoji`;
          context.textAlign = "right";
          context.textBaseline = "top";
          context.fillText(status, baseX + tileSize - 1, baseY + 1);
        }
      });
    }

    // Draw structures layer
    if (showStructures && Array.isArray(structures)) {
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.font = `${Math.max(12, tileSize)}px system-ui, Apple Color Emoji`;
      for (const s of structures as Structure[]) {
        const cx = s.x * tileSize + tileSize / 2;
        const cy = s.y * tileSize + tileSize / 2;
        context.fillText(structureEmoji(s.kind, s.name), cx, cy);
      }
    }

    context.restore();
  }, [world, heatmapLookup, agentClusters, selectedTile, selectedAgentId, tileSize, showResources, showStatus, showHeatmap, showStructures, theme, structures]);

  useEffect(() => {
    if (!selectedAgent || !world) {
      return;
    }
    const { x, y } = selectedAgent.location;
    if (!selectedTile || selectedTile.x !== x || selectedTile.y !== y) {
      setSelectedTile({ x, y });
    }
  }, [selectedAgent, selectedTile, setSelectedTile, world]);

  const handlePointerMove = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!world) {
      setHover(null);
      return;
    }
    const coords = translatePointer(event, canvasRef.current, world.size, tileSize);
    if (!coords) {
      setHover(null);
      return;
    }
    const key = makeTileKey(coords.x, coords.y);
    const agent = agentClusters.get(key)?.[0];
    setHover({ x: coords.x, y: coords.y, clientX: event.clientX, clientY: event.clientY, agent });
  };

  const handlePointerLeave = () => {
    setHover(null);
  };

  const handleClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!world) {
      return;
    }
    const coords = translatePointer(event, canvasRef.current, world.size, tileSize);
    if (!coords) {
      return;
    }
    const key = makeTileKey(coords.x, coords.y);
    const occupants = agentClusters.get(key);
    setSelectedTile({ x: coords.x, y: coords.y });
    if (occupants && occupants.length > 0) {
      const chosen = occupants.find((candidate) => candidate.id === selectedAgentId) ?? occupants[0];
      setSelectedAgent(chosen.id, chosen.location);
    } else {
      setSelectedAgent(null);
    }
  };

  const tileKey = selectedTile ? makeTileKey(selectedTile.x, selectedTile.y) : null;
  const tileIntensity = tileKey ? heatmapLookup.get(tileKey) ?? 0 : 0;
  const tileAgents = tileKey ? agentClusters.get(tileKey) ?? [] : [];
  const tileResources =
    selectedTile && world
      ? world.resources[selectedTile.y * world.size + selectedTile.x]
      : undefined;
  const tileTerrain =
    selectedTile && world ? world.terrain[selectedTile.y * world.size + selectedTile.x] : undefined;

  const resourceEntries = useMemo(() => {
    if (!tileResources) {
      return [] as Array<[string, number]>;
    }
    return Object.entries(tileResources).sort((a, b) => b[1] - a[1]);
  }, [tileResources]);

  const averageMorale = useMemo(() => {
    if (agents.length === 0) {
      return 0;
    }
    const total = agents.reduce((sum, agent) => sum + agent.morale, 0);
    return Math.round(total / agents.length);
  }, [agents]);

  const hoverIntensity = hover ? heatmapLookup.get(makeTileKey(hover.x, hover.y)) ?? 0 : 0;

  return (
    <div className="panel panel--map map-panel">
      <div className="panel__header">
        <div>
          <h2>Spatial Ops Board</h2>
          <p>Pixel terrain with live agent overlays and resource telemetry</p>
        </div>
        <div className="panel__badge" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Icon size
            <input
              type="range"
              min={8}
              max={20}
              step={1}
              value={tileSize}
              onChange={(e) => setTileSize(Number(e.target.value))}
              style={{ marginLeft: 8 }}
            />
          </label>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Resources
            <input type="checkbox" checked={showResources} onChange={(e) => setShowResources(e.target.checked)} style={{ marginLeft: 6 }} />
          </label>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Status
            <input type="checkbox" checked={showStatus} onChange={(e) => setShowStatus(e.target.checked)} style={{ marginLeft: 6 }} />
          </label>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Heatmap
            <input type="checkbox" checked={showHeatmap} onChange={(e) => setShowHeatmap(e.target.checked)} style={{ marginLeft: 6 }} />
          </label>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Structures
            <input type="checkbox" checked={showStructures} onChange={(e) => setShowStructures(e.target.checked)} style={{ marginLeft: 6 }} />
          </label>
          <label style={{ fontSize: 12, opacity: 0.85 }}>
            Theme
            <select value={theme} onChange={(e) => setTheme(e.target.value as any)} style={{ marginLeft: 6 }}>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </label>
          {currentTurn ? formatTime(currentTurn.occurredAt) : "Awaiting stream"}
        </div>
      </div>
      <div className="map-panel__content">
        <div className="map-panel__canvas-wrapper">
          {world ? (
            <>
              <div className="map-panel__canvas-surface">
                <canvas
                  ref={canvasRef}
                  className="map-panel__canvas"
                  role="presentation"
                  onClick={handleClick}
                  onMouseMove={handlePointerMove}
                  onMouseLeave={handlePointerLeave}
                />
              </div>
              <Legend />
              {hover && (
                <Tooltip
                  hover={hover}
                  world={world}
                  resources={world.resources[hover.y * world.size + hover.x]}
                  intensity={hoverIntensity}
                />
              )}
            </>
          ) : (
            <div className="map-panel__empty">Awaiting telemetry…</div>
          )}
        </div>
        <aside className="map-panel__sidebar">
          <section className="map-panel__summary">
            <h3>Tile Focus</h3>
            {selectedTile && world ? (
              <>
                <p>
                  ({selectedTile.x}, {selectedTile.y}) — {formatTerrain(tileTerrain)}
                </p>
                <div className="map-panel__summary-grid">
                  <span>Pressure</span>
                  <strong>{Math.round(tileIntensity * 100)}</strong>
                  <span>Occupants</span>
                  <strong>{tileAgents.length}</strong>
                </div>
                {resourceEntries.length > 0 ? (
                  <div className="map-panel__resource-list">
                    {resourceEntries.map(([resource, value]) => (
                      <span key={resource} className="map-panel__resource-tag">
                        <span className="map-panel__resource-icon">{RESOURCE_EMOJI[resource] ?? ""}</span>
                        {formatResource(resource)} {value}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="map-panel__muted">No stored resources</p>
                )}
                {tileAgents.length > 0 && (
                  <div className="map-panel__tile-agents">
                    {tileAgents.map((agent) => (
                      <button
                        key={agent.id}
                        type="button"
                        className="map-panel__tile-agent-pill"
                        onClick={() => setSelectedAgent(agent.id, agent.location)}
                      >
                        {agent.name}
                      </button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="map-panel__muted">Select a tile or agent to inspect terrain and inventories.</p>
            )}
          </section>
          <section className="map-panel__summary">
            <h3>Agent Spotlight</h3>
            {selectedAgent ? (
              <>
                <p>
                  {selectedAgent.name} — {selectedAgent.role}
                </p>
                <div className="map-panel__summary-grid">
                  <span>Faction</span>
                  <strong>{selectedAgent.faction}</strong>
                  <span>Status</span>
                  <strong>{STATUS_LABEL[selectedAgent.status]}</strong>
                  <span>Morale</span>
                  <strong>{Math.round(selectedAgent.morale)}</strong>
                  <span>Stores</span>
                  <strong>{Math.round(selectedAgent.resources)}</strong>
                </div>
                <p className="map-panel__muted">
                  Position ({selectedAgent.location.x}, {selectedAgent.location.y})
                </p>
              </>
            ) : (
              <p className="map-panel__muted">Choose an agent from the roster to see detailed telemetry.</p>
            )}
          </section>
          <section className="map-panel__roster">
            <header>
              <h3>Agent Roster</h3>
              <span>{agents.length}</span>
            </header>
            <div className="map-panel__agent-list">
            {roster.map((agent) => (
              <button
                key={agent.id}
                type="button"
                className={classNames(
                  "map-panel__agent",
                  agent.id === selectedAgentId && "map-panel__agent--selected"
                )}
                onClick={() => setSelectedAgent(agent.id, agent.location)}
              >
                <div className="map-panel__agent-title">
                  <span className="map-panel__agent-name">
                    <span
                      className="map-panel__agent-faction"
                      style={{ backgroundColor: factionColor(agent.faction) }}
                      aria-hidden
                    />
                    {agent.name}
                  </span>
                  <span className={classNames("map-panel__agent-status", `map-panel__agent-status--${agent.status}`)}>
                    {STATUS_LABEL[agent.status]}
                  </span>
                </div>
                <div className="map-panel__agent-meta">
                  <span>Morale {Math.round(agent.morale)}</span>
                  <span>Stores {Math.round(agent.resources)}</span>
                </div>
                {agentActionsMap[agent.id] && (
                  <div className="map-panel__agent-traits" style={{ color: "#9bb4c8" }}>
                    {truncate(agentActionsMap[agent.id], 120)}
                  </div>
                )}
                <div className="map-panel__agent-traits">
                  <span>{agent.role}</span>
                  <span>
                    ({agent.location.x}, {agent.location.y})
                  </span>
                </div>
              </button>
            ))}
            </div>
          </section>
        </aside>
      </div>
      <footer className="panel__footer">
        <div className="panel__footer-metric">
          <span className="label">Live Agents</span>
          <strong>{agents.length}</strong>
        </div>
        <div className="panel__footer-metric">
          <span className="label">Critical Alerts</span>
          <strong>{currentTurn?.events.filter((event) => event.severity === "critical").length ?? 0}</strong>
        </div>
        <div className="panel__footer-metric">
          <span className="label">Avg Morale</span>
          <strong>{averageMorale}</strong>
        </div>
        <div className="panel__footer-metric">
          <span className="label">Latency</span>
          <strong>{currentTurn ? `${currentTurn.latencyMs.toFixed(0)} ms` : "—"}</strong>
        </div>
      </footer>
    </div>
  );
}

function makeTileKey(x: number, y: number): string {
  return `${x}:${y}`;
}

function translatePointer(
  event: MouseEvent<HTMLCanvasElement>,
  canvas: HTMLCanvasElement | null,
  worldSize: number,
  tileSize: number
): { x: number; y: number } | null {
  if (!canvas) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    return null;
  }
  const pixelRatio = window.devicePixelRatio || 1;
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const canvasX = ((event.clientX - rect.left) * scaleX) / pixelRatio;
  const canvasY = ((event.clientY - rect.top) * scaleY) / pixelRatio;
  const tileX = Math.floor(canvasX / tileSize);
  const tileY = Math.floor(canvasY / tileSize);
  if (tileX < 0 || tileY < 0 || tileX >= worldSize || tileY >= worldSize) {
    return null;
  }
  return { x: tileX, y: tileY };
}

function agentOffset(index: number, tileSize: number, markerSize: number): { x: number; y: number } {
  const center = (tileSize - markerSize) / 2;
  const offsets = [
    { x: center, y: center },
    { x: 2, y: 2 },
    { x: tileSize - markerSize - 2, y: 2 },
    { x: 2, y: tileSize - markerSize - 2 },
    { x: tileSize - markerSize - 2, y: tileSize - markerSize - 2 }
  ];
  return offsets[index % offsets.length];
}

function factionColor(faction: string): string {
  if (faction.toLowerCase().includes("aur")) {
    return "#7bf1a8";
  }
  if (faction.toLowerCase().includes("horizon")) {
    return "#58c6ff";
  }
  if (faction.toLowerCase().includes("zephyr")) {
    return "#f5a97f";
  }
  return "#c1c9ff";
}

function agentEmoji(agent: AgentSummary): string {
  // Age and status driven.
  // We don't have gender; use neutral person by default.
  const age = (agent as any).age as number | undefined;
  const status = agent.status;
  // Status overlay handled separately; base figure by age
  if (typeof age === "number") {
    if (age < 12) return "🧒";
    if (age > 60) return "🧓";
  }
  // Role-based flair
  const role = (agent.role || "").toLowerCase();
  if (role.includes("scout")) return "🧭";
  if (role.includes("diplomat")) return "🤝";
  if (role.includes("strateg")) return "🧠";
  if (role.includes("mediator")) return "🕊️";
  return "🧑";
}

function statusEmoji(status: AgentSummary["status"]): string {
  switch (status) {
    case "moving":
      return "🏃";
    case "engaged":
      return "⚔️";
    case "recovering":
      return "🛌";
    default:
      return "";
  }
}

function structureEmoji(kind: string, name?: string): string {
  const k = (kind || "").toLowerCase();
  if (k.includes("market")) return "💰";
  if (k.includes("settlement") || k.includes("village")) return "🏘️";
  if (k.includes("house") || k.includes("hut") || k.includes("camp")) return "🏠";
  if (k.includes("temple")) return "⛩️";
  if (k.includes("workshop")) return "🛠️";
  return "🏢";
}

function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function formatResource(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1);
}

function formatTerrain(terrain?: string): string {
  if (!terrain) {
    return "Unknown";
  }
  return terrain.charAt(0) + terrain.slice(1).toLowerCase();
}

function formatTime(value: string): string {
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function isTileInside(world: WorldState, tile: { x: number; y: number }): boolean {
  return tile.x >= 0 && tile.y >= 0 && tile.x < world.size && tile.y < world.size;
}

function Legend(): JSX.Element {
  return (
    <div className="map-panel__legend">
      {LEGEND_ORDER.map(({ terrain, label }) => (
        <span key={terrain} className="map-panel__legend-item">
          <span
            className="map-panel__legend-swatch"
            style={{ backgroundColor: TERRAIN_COLORS[terrain] ?? TERRAIN_COLORS.DEFAULT }}
          />
          {label}
        </span>
      ))}
      <span className="map-panel__legend-item">
        <span className="map-panel__legend-swatch" style={{ backgroundColor: "#ff9c5e" }} /> Pressure
      </span>
    </div>
  );
}

function Tooltip({
  hover,
  world,
  resources,
  intensity
}: {
  hover: HoverState;
  world: WorldState;
  resources: TileResources | undefined;
  intensity: number;
}): JSX.Element {
  const index = hover.y * world.size + hover.x;
  const terrain = world.terrain[index];
  const entries = resources ? Object.entries(resources).sort((a, b) => b[1] - a[1]).slice(0, 4) : [];

  return (
    <div className="map-panel__tooltip" style={{ left: hover.clientX, top: hover.clientY }}>
      <strong>
        Tile ({hover.x}, {hover.y})
      </strong>
      <p>{formatTerrain(terrain)}</p>
      <p className="map-panel__tooltip-metric">Pressure {Math.round(intensity * 100)}</p>
      {hover.agent && (
        <p className="map-panel__tooltip-agent">
          {hover.agent.name} — {STATUS_LABEL[hover.agent.status]}
        </p>
      )}
      {entries.length > 0 ? (
        <ul>
          {entries.map(([resource, value]) => (
            <li key={resource}>
              {RESOURCE_EMOJI[resource] ?? ""} {formatResource(resource)} {value}
            </li>
          ))}
        </ul>
      ) : (
        <p className="map-panel__tooltip-empty">No notable resources</p>
      )}
    </div>
  );
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}
