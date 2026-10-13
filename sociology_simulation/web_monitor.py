"""Web monitoring, orchestration, and data export system for the simulation."""

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets
from aiohttp import web
from loguru import logger as loguru_logger
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig

logger = logging.getLogger(__name__)


class SimulationMonitor:
    """Monitor and export simulation data for web UI consumption."""
    
    def __init__(self, output_dir: str = "web_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Current simulation state
        self.current_data = {
            "world": None,
            "agents": [],
            "turn": 0,
            "timestamp": None,
            "logs": [],
            "actions": [],
            "structures": [],
        }

        # WebSocket connections
        self.websocket_clients = set()
        self.websocket_server = None
        
        # HTTP server for API
        self.http_app = None
        self.http_server = None
        
        # Export settings
        self.export_interval = 1  # Export every turn
        self.max_log_entries = 1000
        self.max_action_entries = 2000

        # Simulation orchestration metadata
        self.simulation_status: Dict[str, Any] = {
            "state": "idle",
            "turn": 0,
            "total_turns": 0,
            "era": None,
            "num_agents": 0,
            "world_size": 0,
            "started_at": None,
            "stopped_at": None,
            "last_outcome": None,
            "overrides": [],
            "error": None,
        }
        self._world_reference = None
        self._stop_requested = False
        self.orchestrator = None  # Initialised lazily to avoid circular imports
        # Track last-known actions to emit structured action events per agent
        self._last_agent_action: Dict[int, Any] = {}
        # Track discovered structures (markets, settlements, buildings)
        self._structures: List[Dict[str, Any]] = []
        self._structure_ids: set = set()

    # ------------------------------------------------------------------
    # Simulation lifecycle helpers
    # ------------------------------------------------------------------
    def attach_world(self, world) -> None:
        """Expose the live world object for operator interaction."""
        self._world_reference = world

    def detach_world(self) -> None:
        """Clear world reference when simulation stops."""
        self._world_reference = None

    def get_world(self):
        """Return the active world instance, if any."""
        return self._world_reference

    def update_status(self, **kwargs: Any) -> None:
        """Update simulation status metadata."""
        self.simulation_status.update(kwargs)

    def request_stop(self) -> None:
        """Signal the running simulation to stop after the current turn."""
        self._stop_requested = True

    def clear_stop_request(self) -> None:
        """Reset stop request flag after simulation terminates."""
        self._stop_requested = False

    def should_stop(self) -> bool:
        """Check if a stop has been requested."""
        return self._stop_requested

    def enqueue_interaction(self, interaction: Dict[str, Any]) -> bool:
        """Queue an operator/agent interaction for processing next turn."""
        world = self.get_world()
        if world is None:
            return False
        world.pending_interactions.append(interaction)
        return True

    def broadcast_from_trinity(self, message: str, targets: Optional[List[int]] = None) -> int:
        """Inject a Trinity broadcast into agent logs."""
        world = self.get_world()
        if world is None:
            return 0

        delivered = 0
        recipients = world.agents
        if targets:
            target_ids = set(targets)
            recipients = [agent for agent in world.agents if agent.aid in target_ids]

        for agent in recipients:
            agent.log.append(f"【Trinity】{message}")
            delivered += 1

        if delivered:
            self.add_log_entry("INFO", f"Trinity broadcast delivered to {delivered} agents")
        return delivered

    def get_simulation_status(self) -> Dict[str, Any]:
        """Return a snapshot of the simulation orchestration status."""
        return dict(self.simulation_status)

    def _ensure_orchestrator(self) -> "MonitorSimulationController":
        """Lazy instantiate the orchestration controller."""
        if self.orchestrator is None:
            self.orchestrator = MonitorSimulationController(self)
        return self.orchestrator
        
    def update_world_data(self, world, agents: List, turn: int):
        """Update world data from simulation."""
        try:
            # Extract world data
            current_era = getattr(world, 'current_era', None)
            if current_era is None:
                current_era = getattr(world, 'era_prompt', 'Stone Age')

            world_data = {
                "size": world.size,
                "turn": turn,
                "era": current_era,
                "terrain": self._serialize_terrain(world),
                "resources": self._serialize_resources(world),
                "groups": self._serialize_groups(world),
                "stats": self._calculate_world_stats(world, agents)
            }
            
            # Extract agent data
            agent_data = []
            for agent in agents:
                # Extract position coordinates
                if hasattr(agent, 'pos') and agent.pos:
                    x, y = agent.pos
                else:
                    x, y = getattr(agent, 'x', 0), getattr(agent, 'y', 0)
                
                agent_info = {
                    "aid": agent.aid,
                    "name": agent.name,
                    "x": x,
                    "y": y,
                    "health": getattr(agent, 'health', 100),
                    "current_action": getattr(agent, 'current_action', None),
                    "inventory": dict(agent.inventory) if hasattr(agent, 'inventory') else {},
                    "skills": dict(agent.skills) if hasattr(agent, 'skills') else {},
                    "group_id": getattr(agent, 'group_id', None),
                    "social_connections": self._serialize_social_connections(agent),
                    "reputation": getattr(agent, 'reputation', 0),
                    "memory": self._serialize_memory(agent)
                }
                agent_data.append(agent_info)
            
            # Detect agent action changes for action events
            action_events: List[Dict[str, Any]] = []
            for a in agent_data:
                aid = a["aid"]
                act = a.get("current_action")
                last = self._last_agent_action.get(aid)
                if act and act != last:
                    action_events.append({
                        "aid": aid,
                        "name": a.get("name"),
                        "action": act,
                        "x": a.get("x"),
                        "y": a.get("y"),
                        "turn": turn,
                        "timestamp": time.time(),
                    })
                    self._last_agent_action[aid] = act

            # Update current data
            self.current_data.update({
                "world": world_data,
                "agents": agent_data,
                "turn": turn,
                "timestamp": time.time(),
                # Maintain a rolling buffer of action events for consumers without WS
                "actions": (self.current_data.get("actions", []) + action_events)[-self.max_action_entries:],
                # Keep structures in sync
                "structures": list(self._structures),
            })

            # Keep orchestration status in sync
            self.simulation_status.update({
                "turn": turn,
                "era": world_data.get("era"),
                "num_agents": len(agent_data),
            })
            if self._stop_requested:
                self.simulation_status.setdefault("state", "running")
                if self.simulation_status["state"] != "idle":
                    self.simulation_status["state"] = "stopping"
            elif self.simulation_status.get("state") in {"initializing", "starting"}:
                self.simulation_status["state"] = "running"
            self.simulation_status["error"] = None

            # Export to file if needed
            if turn % self.export_interval == 0:
                self._export_to_file()
            
            # Send to WebSocket clients
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._broadcast_update())
                    if action_events:
                        asyncio.create_task(self._broadcast_actions(action_events))
            except RuntimeError:
                # No event loop running, skip WebSocket broadcast
                pass
            
        except Exception as e:
            logger.error(f"Error updating world data: {e}")
    
    def _serialize_terrain(self, world) -> List[str]:
        """Serialize terrain data from either `world.map` (2D) or `world.terrain` (dict)."""
        out: List[str] = []
        # Preferred: 2D map from the modern World implementation
        if hasattr(world, "map") and getattr(world, "map") is not None:
            grid = world.map
            # Flatten in row-major order: index = y * size + x
            for y in range(world.size):
                for x in range(world.size):
                    try:
                        out.append(grid[x][y])
                    except Exception:
                        out.append("GRASSLAND")
            return out

        # Fallback: dict-based terrain from simple runner
        terr = getattr(world, "terrain", None)
        if isinstance(terr, dict):
            for y in range(world.size):
                for x in range(world.size):
                    out.append(terr.get((x, y), "GRASSLAND"))
            return out

        # Last resort: all grassland
        for _y in range(world.size):
            for _x in range(world.size):
                out.append("GRASSLAND")
        return out
    
    def _serialize_resources(self, world) -> List[Dict[str, int]]:
        """Serialize resource data from dict keyed by (x,y)."""
        resources: List[Dict[str, int]] = []
        wr = getattr(world, "resources", {})
        for y in range(world.size):
            for x in range(world.size):
                tile = {}
                try:
                    if (x, y) in wr:
                        tile = dict(wr[(x, y)])
                except Exception:
                    tile = {}
                resources.append(tile)
        return resources
    
    def _serialize_groups(self, world) -> List[Dict[str, Any]]:
        """Serialize group data."""
        groups = []
        if hasattr(world, 'social_manager') and hasattr(world.social_manager, 'groups'):
            for group_id, group in world.social_manager.groups.items():
                group_data = {
                    "id": group_id,
                    "name": getattr(group, 'name', f"Group {group_id}"),
                    "member_count": len(getattr(group, 'members', [])),
                    "leader": getattr(group, 'leader', None),
                    "type": getattr(group, 'group_type', 'unknown'),
                    "reputation": getattr(group, 'reputation', 0)
                }
                groups.append(group_data)
        return groups
    
    def _serialize_social_connections(self, agent) -> List[Dict[str, Any]]:
        """Serialize agent social connections (supports dict or list representations)."""
        out: List[Dict[str, Any]] = []
        sc = getattr(agent, "social_connections", None)
        if isinstance(sc, dict):
            for target_id, meta in sc.items():
                out.append({
                    "target_id": target_id,
                    "name": getattr(meta, "name", f"Agent {target_id}") if hasattr(meta, "name") else f"Agent {target_id}",
                    "relationship": (meta.get("relationship_type") if isinstance(meta, dict) else getattr(meta, "relationship_type", "acquaintance")) or "acquaintance",
                    "strength": (meta.get("strength") if isinstance(meta, dict) else getattr(meta, "strength", 0.5)) or 0.5,
                })
        elif isinstance(sc, list):
            for conn in sc:
                if hasattr(conn, "target_id"):
                    out.append({
                        "target_id": conn.target_id,
                        "name": getattr(conn, "name", f"Agent {conn.target_id}"),
                        "relationship": getattr(conn, "relationship_type", "acquaintance"),
                        "strength": getattr(conn, "strength", 0.5),
                    })
        return out[:10]
    
    def _serialize_memory(self, agent) -> List[str]:
        """Serialize agent's recent memories defensively."""
        mem = getattr(agent, "memory", None)
        out: List[str] = []
        # Common patterns: list-like or dict of categories -> lists
        if isinstance(mem, list):
            for item in mem[-5:]:
                out.append(str(getattr(item, "content", item)))
        elif isinstance(mem, dict):
            # Flatten last items from dict values
            for val in mem.values():
                if isinstance(val, list) and val:
                    out.append(str(getattr(val[-1], "content", val[-1])))
            out = out[-5:]
        elif hasattr(mem, "memories"):
            try:
                recent = list(mem.memories)[-5:]
                for m in recent:
                    out.append(str(getattr(m, "content", m)))
            except Exception:
                pass
        return out
    
    def _calculate_world_stats(self, world, agents: List) -> Dict[str, Any]:
        """Calculate world statistics."""
        stats = {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if getattr(a, 'current_action', None)]),
            "total_groups": 0,
            "total_resources": 0,
            "technologies_discovered": 0
        }
        
        # Count groups
        if hasattr(world, 'social_manager') and hasattr(world.social_manager, 'groups'):
            stats["total_groups"] = len(world.social_manager.groups)
        
        # Count resources
        if hasattr(world, 'resources'):
            for tile_resources in world.resources.values():
                stats["total_resources"] += sum(tile_resources.values())
        
        # Count technologies
        if hasattr(world, 'tech_system') and hasattr(world.tech_system, 'discovered_techs'):
            stats["technologies_discovered"] = len(world.tech_system.discovered_techs)
        
        return stats
    
    def add_log_entry(self, level: str, message: str, agent_id: Optional[int] = None):
        """Add a log entry for web UI display."""
        log_entry = {
            "timestamp": time.time(),
            "level": level.upper(),
            "message": message,
            "agent_id": agent_id
        }
        
        self.current_data["logs"].append(log_entry)
        
        # Keep only recent logs
        if len(self.current_data["logs"]) > self.max_log_entries:
            self.current_data["logs"] = self.current_data["logs"][-self.max_log_entries:]

        # Attempt to extract structured structures from log messages
        new_struct = self._maybe_extract_structure_from_message(message)
        if new_struct:
            self._structures.append(new_struct)
            self._structure_ids.add(new_struct["id"])
            self.current_data["structures"] = list(self._structures)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._broadcast_structures([new_struct]))
            except RuntimeError:
                pass

        # Send log to WebSocket clients
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._broadcast_log(log_entry))
        except RuntimeError:
            # No event loop running, skip WebSocket broadcast
            pass
    
    def _export_to_file(self):
        """Export current data to JSON file."""
        try:
            filename = f"simulation_turn_{self.current_data['turn']:03d}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, indent=2, ensure_ascii=False)
            
            # Also update latest.json
            latest_path = self.output_dir / "latest.json"
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error exporting to file: {e}")
    
    async def _broadcast_update(self):
        """Broadcast simulation update to all WebSocket clients."""
        if not self.websocket_clients:
            return
        
        message = {
            "type": "simulation_update",
            "data": self.current_data
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_log(self, log_entry: Dict[str, Any]):
        """Broadcast log entry to all WebSocket clients."""
        if not self.websocket_clients:
            return
        
        message = {
            "type": "log_entry",
            "data": log_entry
        }
        
        await self._broadcast_message(message)

    async def _broadcast_actions(self, events: List[Dict[str, Any]]):
        """Broadcast per-agent action events to all WebSocket clients."""
        if not self.websocket_clients or not events:
            return
        message = {
            "type": "actions_update",
            "data": {"events": events},
        }
        await self._broadcast_message(message)

    async def _broadcast_structures(self, items: List[Dict[str, Any]]):
        """Broadcast new structures to all WebSocket clients."""
        if not self.websocket_clients or not items:
            return
        message = {
            "type": "structures_update",
            "data": {"structures": items},
        }
        await self._broadcast_message(message)

    def _maybe_extract_structure_from_message(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse simulation logs to extract structure placement events.

        Supported examples:
          - "New market established at (7, 2): market_1"
          - "New settlement at (x, y): FooVillage"
          - "Built hut at (3, 4)"
        """
        try:
            import re
            m = re.search(r"New\s+market\s+established\s+at\s*\((\d+),\s*(\d+)\)\s*:\s*([\w-]+)", text, re.IGNORECASE)
            if m:
                x, y, sid = int(m.group(1)), int(m.group(2)), m.group(3)
                if sid not in self._structure_ids:
                    return {"id": sid, "kind": "market", "name": sid, "x": x, "y": y}

            m = re.search(r"New\s+settlement\s+(?:established\s+)?at\s*\((\d+),\s*(\d+)\)\s*:?\s*([\w-]+)?", text, re.IGNORECASE)
            if m:
                x, y = int(m.group(1)), int(m.group(2))
                name = m.group(3) or f"settlement_{x}_{y}"
                if name not in self._structure_ids:
                    return {"id": name, "kind": "settlement", "name": name, "x": x, "y": y}

            m = re.search(r"Built\s+(hut|house|workshop|temple)\s+at\s*\((\d+),\s*(\d+)\)", text, re.IGNORECASE)
            if m:
                kind = m.group(1).lower()
                x, y = int(m.group(2)), int(m.group(3))
                sid = f"{kind}_{x}_{y}"
                if sid not in self._structure_ids:
                    return {"id": sid, "kind": kind, "name": sid, "x": x, "y": y}
        except Exception:
            return None
        return None
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket clients."""
        if not self.websocket_clients:
            return
        
        message_str = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.websocket_clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected_clients
    
    async def websocket_handler(self, websocket, path=None):
        """Handle WebSocket connections."""
        logger.info(f"New WebSocket client connected from {websocket.remote_address}")
        self.websocket_clients.add(websocket)
        
        try:
            # Send current data to new client
            if self.current_data["world"]:
                await websocket.send(json.dumps({
                    "type": "simulation_update",
                    "data": self.current_data
                }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from client: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_clients.discard(websocket)
    
    async def _handle_websocket_message(self, websocket, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        message_type = data.get("type")
        
        if message_type == "request_update":
            # Send current data
            await websocket.send(json.dumps({
                "type": "simulation_update",
                "data": self.current_data
            }))
        elif message_type == "request_logs":
            # Send recent logs
            await websocket.send(json.dumps({
                "type": "logs_update",
                "data": {"logs": self.current_data["logs"][-50:]}  # Last 50 logs
            }))
    
    async def start_websocket_server(self, host: str = "localhost", port: int = 8765):
        """Start WebSocket server."""
        try:
            self.websocket_server = await websockets.serve(
                self.websocket_handler, host, port
            )
            logger.info(f"WebSocket server started on {host}:{port}")
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
    
    async def stop_websocket_server(self):
        """Stop WebSocket server."""
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            logger.info("WebSocket server stopped")
    
    def setup_http_server(self, host: str = "localhost", port: int = 8080):
        """Setup HTTP server for API and static files."""
        self.http_app = web.Application()
        
        # API routes
        self.http_app.router.add_get('/api/simulation-data', self._api_simulation_data)
        self.http_app.router.add_get('/api/agents', self._api_agents)
        self.http_app.router.add_get('/api/world', self._api_world)
        self.http_app.router.add_get('/api/logs', self._api_logs)
        self.http_app.router.add_get('/api/structures', self._api_structures)
        self.http_app.router.add_get('/api/simulation-status', self._api_simulation_status)
        self.http_app.router.add_post('/api/simulation/start', self._api_start_simulation)
        self.http_app.router.add_post('/api/simulation/stop', self._api_stop_simulation)
        self.http_app.router.add_post('/api/interactions', self._api_create_interaction)

        # Static files (serve web UI)
        web_ui_path = Path(__file__).parent.parent / "web_ui"
        if web_ui_path.exists():
            monitor_dist = web_ui_path / "monitor" / "dist"
            control_page = web_ui_path / "control.html"

            if monitor_dist.exists() and (monitor_dist / "index.html").exists():
                # Serve the React monitor build when available
                async def _serve_monitor_index(_request):
                    return web.FileResponse(path=monitor_dist / "index.html")

                self.http_app.router.add_get('/', _serve_monitor_index)
                self.http_app.router.add_static('/', monitor_dist, name='static-monitor')
                logger.info("Serving React monitor (dist) at '/'")
            else:
                # No React build – serve lightweight control page that uses backend APIs
                async def _serve_control(_request):
                    if control_page.exists():
                        return web.FileResponse(path=control_page)
                    raise web.HTTPNotFound(text="control.html not found in web_ui/")

                self.http_app.router.add_get('/', _serve_control)
                self.http_app.router.add_static('/', web_ui_path, name='static-webui-root')
                logger.info("Serving lightweight control page at '/'. Classic UI is deprecated and no longer default.")

        return self.http_app
    
    async def _api_simulation_data(self, request):
        """API endpoint for simulation data."""
        return web.json_response(self.current_data)
    
    async def _api_agents(self, request):
        """API endpoint for agents data."""
        return web.json_response({"agents": self.current_data["agents"]})
    
    async def _api_world(self, request):
        """API endpoint for world data."""
        return web.json_response({"world": self.current_data["world"]})
    
    async def _api_logs(self, request):
        """API endpoint for logs."""
        limit = int(request.query.get('limit', 50))
        logs = self.current_data["logs"][-limit:]
        return web.json_response({"logs": logs})

    async def _api_structures(self, request):
        """Return known structures placed on the map."""
        return web.json_response({"structures": self.current_data.get("structures", [])})

    async def _api_simulation_status(self, request):
        """Return orchestration status for dashboards."""
        return web.json_response({"status": self.get_simulation_status()})

    async def _api_start_simulation(self, request):
        """Start a new simulation run with optional overrides."""
        controller = self._ensure_orchestrator()
        if controller.is_running():
            return web.json_response({"error": "Simulation already running"}, status=400)

        payload: Dict[str, Any] = {}
        if request.can_read_body:
            try:
                payload = await request.json()
            except json.JSONDecodeError:
                return web.json_response({"error": "Invalid JSON payload"}, status=400)

        overrides = payload.get("overrides", [])
        if overrides is None:
            overrides = []
        if not isinstance(overrides, list):
            return web.json_response({"error": "overrides must be a list"}, status=400)

        overrides = list(overrides)

        # Convenience parameters
        era = payload.get("era")
        if era:
            overrides.append(f"simulation.era_prompt={json.dumps(era)}")

        scenario = payload.get("scenario")
        if scenario:
            overrides.append(f"simulation={scenario}")

        for field, key in (
            ("turns", "runtime.turns"),
            ("num_agents", "world.num_agents"),
            ("world_size", "world.size"),
        ):
            if field in payload and payload[field] is not None:
                try:
                    value = int(payload[field])
                except (TypeError, ValueError):
                    return web.json_response({"error": f"{field} must be an integer"}, status=400)
                overrides.append(f"{key}={value}")

        try:
            cfg = await controller.start(overrides)
        except RuntimeError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception as exc:  # pragma: no cover - defensive guard for unexpected failures
            logger.exception("Failed to start simulation via monitor", exc_info=exc)
            return web.json_response({"error": "Failed to start simulation"}, status=500)

        summary = {
            "era": cfg.simulation.era_prompt,
            "turns": cfg.runtime.turns,
            "num_agents": cfg.world.num_agents,
            "world_size": cfg.world.size,
        }

        return web.json_response({
            "status": "starting",
            "config": summary,
            "overrides": overrides,
        })

    async def _api_stop_simulation(self, request):
        """Request the running simulation to stop."""
        controller = self._ensure_orchestrator()
        if not controller.is_running():
            return web.json_response({"status": self.simulation_status.get("state", "idle")})

        await controller.stop()
        self.update_status(state="stopping")
        return web.json_response({"status": "stopping"})

    async def _api_create_interaction(self, request):
        """Queue operator interactions or Trinity directives."""
        if self.get_world() is None:
            return web.json_response({"error": "Simulation is not running"}, status=400)

        if not request.can_read_body:
            return web.json_response({"error": "Missing JSON payload"}, status=400)

        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        role = payload.get("role", "agent")

        if role == "agent":
            try:
                agent_id = int(payload["agent_id"])
                target_id = int(payload["target_id"])
            except (KeyError, TypeError, ValueError):
                return web.json_response({"error": "agent_id and target_id must be integers"}, status=400)

            content = payload.get("content")
            if not content:
                return web.json_response({"error": "content is required"}, status=400)

            interaction_type = payload.get("interaction_type", "chat")
            interaction = {
                "type": interaction_type,
                "source_id": agent_id,
                "target_id": target_id,
                "content": content,
            }

            if not self.enqueue_interaction(interaction):
                return web.json_response({"error": "Failed to queue interaction"}, status=400)

            self.add_log_entry(
                "INFO",
                f"Queued {interaction_type} from agent {agent_id} to {target_id}",
                agent_id=agent_id,
            )
            return web.json_response({"status": "queued", "interaction": interaction})

        if role == "trinity":
            action = payload.get("action", "broadcast")

            if action == "broadcast":
                content = payload.get("content")
                if not content:
                    return web.json_response({"error": "content is required"}, status=400)

                targets = payload.get("targets")
                target_ids = None
                if targets is not None:
                    if not isinstance(targets, list):
                        return web.json_response({"error": "targets must be a list"}, status=400)
                    try:
                        target_ids = [int(t) for t in targets]
                    except (TypeError, ValueError):
                        return web.json_response({"error": "targets must be integers"}, status=400)

                delivered = self.broadcast_from_trinity(content, target_ids)
                self.add_log_entry("INFO", f"Trinity broadcast: {content}")
                return web.json_response({"status": "broadcast", "delivered": delivered})

            if action == "set_era":
                new_era = payload.get("era")
                if not new_era:
                    return web.json_response({"error": "era is required"}, status=400)

                world = self.get_world()
                world.trinity.era_prompt = new_era
                self.simulation_status["era"] = new_era
                if self.current_data.get("world"):
                    self.current_data["world"]["era"] = new_era
                self.add_log_entry("INFO", f"Era updated to {new_era} by operator")
                return web.json_response({"status": "era_updated", "era": new_era})

            return web.json_response({"error": f"Unknown Trinity action '{action}'"}, status=400)

        return web.json_response({"error": f"Unknown role '{role}'"}, status=400)
    
    async def start_http_server(self, host: str = "localhost", port: int = 8080):
        """Start HTTP server."""
        try:
            runner = web.AppRunner(self.http_app)
            await runner.setup()
            
            site = web.TCPSite(runner, host, port)
            await site.start()
            
            logger.info(f"HTTP server started on http://{host}:{port}")
            return runner
        except Exception as e:
            logger.error(f"Error starting HTTP server: {e}")
            return None


class LogCapture:
    """Capture log messages for web UI display."""
    
    def __init__(self, monitor: SimulationMonitor):
        self.monitor = monitor
        self.original_handlers = []
        self._loguru_handler_id = None
    
    def start_capture(self):
        """Start capturing log messages."""
        # Get the root logger
        root_logger = logging.getLogger()
        
        # Create our custom handler
        handler = logging.Handler()
        handler.emit = self._emit_log
        
        # Add handler to root logger
        root_logger.addHandler(handler)
        self.original_handlers.append(handler)

        # Also capture Loguru logs into the monitor (without printing to console)
        if self._loguru_handler_id is None:
            def _loguru_sink(message):  # message is a loguru Message
                try:
                    record = message.record
                    lvl = record.get("level").name if record.get("level") else "INFO"
                    txt = record.get("message", "")
                    # Attach optional agent_id from "extra" if present
                    agent_id = None
                    extra = record.get("extra") or {}
                    if "agent_id" in extra:
                        agent_id = extra["agent_id"]
                    self.monitor.add_log_entry(lvl, txt, agent_id)
                except Exception:
                    pass

            # Add at INFO level; simulation uses info/debug mostly
            self._loguru_handler_id = loguru_logger.add(_loguru_sink, level="INFO")
    
    def _emit_log(self, record):
        """Custom log emit function."""
        try:
            message = record.getMessage()
            level = record.levelname
            
            # Extract agent ID if present in the message
            agent_id = None
            if hasattr(record, 'agent_id'):
                agent_id = record.agent_id
            
            self.monitor.add_log_entry(level, message, agent_id)
        except Exception as e:
            # Don't let logging errors break the simulation
            print(f"Logging error: {e}")
    
    def stop_capture(self):
        """Stop capturing log messages."""
        root_logger = logging.getLogger()
        for handler in self.original_handlers:
            root_logger.removeHandler(handler)
        self.original_handlers.clear()
        if self._loguru_handler_id is not None:
            try:
                loguru_logger.remove(self._loguru_handler_id)
            except Exception:
                pass
            self._loguru_handler_id = None


class MonitorSimulationController:
    """Coordinate simulation execution for the web monitor."""

    def __init__(self, monitor: SimulationMonitor):
        self.monitor = monitor
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._active_config: Optional[DictConfig] = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, overrides: List[str]) -> DictConfig:
        async with self._lock:
            if self.is_running():
                raise RuntimeError("Simulation already running")

            cfg = self._compose_config(overrides)
            self.monitor.update_status(
                state="starting",
                total_turns=cfg.runtime.turns,
                era=cfg.simulation.era_prompt,
                num_agents=cfg.world.num_agents,
                world_size=cfg.world.size,
                overrides=list(overrides),
                turn=0,
                started_at=time.time(),
                stopped_at=None,
                last_outcome=None,
                error=None,
            )
            self.monitor.clear_stop_request()

            self._task = asyncio.create_task(self._run(cfg))
            self._task.add_done_callback(self._on_complete)
            self._active_config = cfg
            return cfg

    async def stop(self) -> None:
        async with self._lock:
            if not self.is_running():
                return
            self.monitor.request_stop()

    def get_active_config(self) -> Optional[DictConfig]:
        return self._active_config

    def _compose_config(self, overrides: List[str]) -> DictConfig:
        config_dir = Path(__file__).parent / "conf"

        try:
            global_hydra = GlobalHydra.instance()
            if global_hydra.is_initialized():
                global_hydra.clear()
        except ValueError:
            # Hydra not initialised yet; nothing to clear
            pass

        with initialize_config_dir(version_base=None, config_dir=str(config_dir), job_name="monitor"):
            cfg = compose(config_name="config", overrides=overrides)
        return cfg

    async def _run(self, cfg: DictConfig) -> None:
        from .main import run_simulation_from_config

        try:
            await run_simulation_from_config(cfg, monitor=self.monitor)
        except Exception as exc:  # pragma: no cover - runtime guard
            self.monitor.update_status(
                state="error",
                error=str(exc),
                stopped_at=time.time(),
                last_outcome="error",
            )
            self.monitor.add_log_entry("ERROR", f"Simulation crashed: {exc}")
            raise

    def _on_complete(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception as exc:  # pragma: no cover - already reported in _run
            logger.error(f"Simulation task ended with error: {exc}")
        finally:
            self._task = None
            self._active_config = None


# Global monitor instance
_global_monitor = None

def get_monitor() -> SimulationMonitor:
    """Get the global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SimulationMonitor()
    return _global_monitor

def start_web_servers(host: str = "localhost", ws_port: int = 8765, http_port: int = 8080):
    """Start both WebSocket and HTTP servers."""
    monitor = get_monitor()
    
    async def run_servers():
        # Setup HTTP server
        http_app = monitor.setup_http_server(host, http_port)
        http_runner = await monitor.start_http_server(host, http_port)
        
        # Start WebSocket server
        await monitor.start_websocket_server(host, ws_port)
        
        logger.info(f"Web servers started:")
        logger.info(f"  Web UI: http://{host}:{http_port}")
        logger.info(f"  WebSocket: ws://{host}:{ws_port}")
        
        # Keep servers running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down web servers...")
        finally:
            await monitor.stop_websocket_server()
            if http_runner:
                await http_runner.cleanup()
    
    # Run in separate thread
    def run_in_thread():
        asyncio.run(run_servers())
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    return thread
