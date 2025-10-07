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
import type { AgentSummary, TileResources, WorldState } from "../../types/simulation";

const TILE_SIZE = 16;
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

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hover, setHover] = useState<HoverState | null>(null);

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
    const mapSize = world.size * TILE_SIZE;
    canvas.width = mapSize * pixelRatio;
    canvas.height = mapSize * pixelRatio;
    canvas.style.width = "100%";
    canvas.style.height = "100%";

    context.save();
    context.scale(pixelRatio, pixelRatio);
    context.clearRect(0, 0, mapSize, mapSize);
    context.fillStyle = "#05070f";
    context.fillRect(0, 0, mapSize, mapSize);

    for (let y = 0; y < world.size; y += 1) {
      for (let x = 0; x < world.size; x += 1) {
        const index = y * world.size + x;
        const terrain = world.terrain[index];
        const color = TERRAIN_COLORS[terrain] ?? TERRAIN_COLORS.DEFAULT;
        const originX = x * TILE_SIZE;
        const originY = y * TILE_SIZE;

        context.fillStyle = color;
        context.fillRect(originX, originY, TILE_SIZE, TILE_SIZE);

        context.fillStyle = "rgba(255, 255, 255, 0.08)";
        context.fillRect(originX, originY, TILE_SIZE, TILE_SIZE * 0.35);
        context.fillStyle = "rgba(0, 0, 0, 0.28)";
        context.fillRect(originX, originY + TILE_SIZE * 0.65, TILE_SIZE, TILE_SIZE * 0.35);

        const intensity = heatmapLookup.get(makeTileKey(x, y)) ?? 0;
        if (intensity > 0.01) {
          context.fillStyle = `rgba(255, 156, 94, ${0.2 + intensity * 0.55})`;
          context.fillRect(originX, originY, TILE_SIZE, TILE_SIZE);
        }

        context.strokeStyle = "rgba(6, 9, 18, 0.7)";
        context.strokeRect(originX, originY, TILE_SIZE, TILE_SIZE);
      }
    }

    if (selectedTile && isTileInside(world, selectedTile)) {
      context.lineWidth = 2;
      context.strokeStyle = "rgba(123, 241, 168, 0.9)";
      context.strokeRect(
        selectedTile.x * TILE_SIZE + 1,
        selectedTile.y * TILE_SIZE + 1,
        TILE_SIZE - 2,
        TILE_SIZE - 2
      );
    }

    for (const [key, cluster] of agentClusters.entries()) {
      const [tileX, tileY] = key.split(":").map(Number);
      const baseX = tileX * TILE_SIZE;
      const baseY = tileY * TILE_SIZE;

      cluster.forEach((agent, index) => {
        const markerSize = 6;
        const offset = agentOffset(index, TILE_SIZE, markerSize);
        const drawX = baseX + offset.x;
        const drawY = baseY + offset.y;

        if (agent.id === selectedAgentId) {
          context.fillStyle = "rgba(0, 0, 0, 0.6)";
          context.fillRect(drawX - 1, drawY - 1, markerSize + 2, markerSize + 2);
          context.strokeStyle = "rgba(255, 255, 255, 0.9)";
          context.strokeRect(drawX - 1, drawY - 1, markerSize + 2, markerSize + 2);
        }

        context.fillStyle = factionColor(agent.faction);
        context.fillRect(drawX, drawY, markerSize, markerSize);
        context.fillStyle = "rgba(0, 0, 0, 0.35)";
        context.fillRect(drawX, drawY + markerSize - 2, markerSize, 2);
      });
    }

    context.restore();
  }, [world, heatmapLookup, agentClusters, selectedTile, selectedAgentId]);

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
    const coords = translatePointer(event, canvasRef.current, world.size);
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
    const coords = translatePointer(event, canvasRef.current, world.size);
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
        <span className="panel__badge">
          {currentTurn ? formatTime(currentTurn.occurredAt) : "Awaiting stream"}
        </span>
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
  worldSize: number
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
  const tileX = Math.floor(canvasX / TILE_SIZE);
  const tileY = Math.floor(canvasY / TILE_SIZE);
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
