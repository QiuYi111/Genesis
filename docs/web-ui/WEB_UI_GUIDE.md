# Web UI Guide for Project Genesis

## Overview

The Project Genesis Web UI provides a real-time, interactive interface for monitoring and visualizing sociology simulations. It features an interactive map, agent tracking, resource visualization, and real-time updates via WebSocket connections.

## Features

### 🗺️ Interactive Map
- **Zoom and Pan**: Mouse wheel to zoom, click and drag to pan
- **Terrain Visualization**: Different colors for mountains, forests, grasslands, water, and desert
- **Resource Indicators**: Small dots showing available resources on each tile
- **Grid Overlay**: Visible when zoomed in for precise positioning

### 👥 Agent Monitoring
- **Real-time Agent Positions**: Agents displayed as colored circles on the map
- **Agent Selection**: Click on agents to view detailed information
- **Agent List**: Sidebar showing all agents with quick selection
- **Detailed Info**: Inventory, skills, social connections, and current actions

### 🌍 World Information
- **Tile Details**: Click on map tiles to see terrain and resource information
- **World Statistics**: Overview of terrain distribution and total resources
- **Group Tracking**: Monitor social groups and their formation

### 📊 Real-time Monitoring
- **Live Updates**: WebSocket connection for real-time simulation data
- **Turn Counter**: Current simulation turn display
- **Status Indicators**: Connection status and simulation state
- **Auto-refresh**: Configurable automatic data updates

### 📝 Logging System
- **Live Logs**: Real-time log entries from the simulation
- **Log Levels**: Color-coded messages (info, warning, error, debug)
- **Log History**: Maintains recent log entries for review

## Quick Start

### 1. Install Dependencies
```bash
# Navigate to project directory
cd project-genesis

# Install with uv (includes websockets dependency)
uv sync
```

### 2. Run with Web UI
```bash
# Start simulation with web monitoring
uv run python run_web_simulation.py

# Or use the integrated web export
uv run python run_with_web_export.py
```

### 3. Access Web Interface
- **Web UI**: http://localhost:8080
- **WebSocket**: ws://localhost:8765 (automatic)

## Interface Guide

### Main Layout

```
┌─────────────────────────────────────────────────┐
│ Header: Status Panel & Connection Info          │
├───────────────────────────┬─────────────────────┤
│                           │ Sidebar Tabs        │
│                           ├─────────────────────┤
│     Interactive Map       │ • Agents Tab        │
│                           │ • Terrain Tab       │
│                           │ • Logs Tab          │
│                           │                     │
│                           │ Selected Info       │
│                           │ Panel              │
│                           │                     │
│                           ├─────────────────────┤
│                           │ Control Buttons     │
└───────────────────────────┴─────────────────────┘
```

### Navigation Controls

| Action | Method |
|--------|--------|
| Zoom In/Out | Mouse wheel |
| Pan Map | Click and drag (planned) |
| Select Agent | Click on red circle |
| Select Tile | Click on map |
| Reset View | "🎯 Reset View" button |
| Refresh Data | "🔄 Refresh" button or R key |
| Toggle Auto-refresh | "▶️ Auto" button or Space key |
| Clear Selection | Escape key |

### Map Legend

| Color | Terrain Type |
|-------|-------------|
| 🟤 Brown | Mountain |
| 🟢 Dark Green | Forest |
| 🟢 Light Green | Grassland |
| 🔵 Blue | Water |
| 🟡 Yellow | Desert |
| 🔴 Red Circle | Agent |
| 🟡 Yellow Circle | Selected Agent |

### Sidebar Tabs

#### Agents Tab
- **Selected Agent**: Detailed information about clicked agent
- **Agent List**: All agents with quick selection and status

**Agent Information Includes:**
- Name and ID
- Current position
- Health status
- Current action
- Inventory items
- Skills and levels
- Social connections
- Group membership

#### Terrain Tab
- **Selected Tile**: Information about clicked map tile
- **World Statistics**: Overall world state and distribution

**Tile Information Includes:**
- Position coordinates
- Terrain type
- Available resources
- Agents present on tile

#### Logs Tab
- **Real-time Logs**: Live simulation events and messages
- **Log Levels**: Color-coded by importance
- **Scrollable History**: Recent simulation events

### Control Panel

| Button | Function |
|--------|----------|
| 🔄 Refresh | Manually update data |
| ▶️ Auto | Toggle auto-refresh (5-second interval) |
| 💾 Export | Download current simulation data as JSON |
| 🎯 Reset View | Center and reset map zoom |

## Technical Details

### WebSocket Communication

The UI connects to a WebSocket server for real-time updates:

```javascript
// Message types received:
{
  "type": "simulation_update",
  "data": {
    "world": {...},
    "agents": [...],
    "turn": 42
  }
}

{
  "type": "log_entry", 
  "data": {
    "timestamp": "...",
    "level": "INFO",
    "message": "Agent action completed"
  }
}
```

### Data Export Format

Exported JSON includes:
```json
{
  "world": {
    "size": 64,
    "turn": 30,
    "terrain": ["GRASSLAND", "FOREST", ...],
    "resources": [{}, {"wood": 3}, ...]
  },
  "agents": [
    {
      "aid": 0,
      "name": "Agent0",
      "x": 12.5,
      "y": 8.3,
      "inventory": {"wood": 2, "stone": 1},
      "skills": {"foraging": 3}
    }
  ],
  "timestamp": "2025-07-05T..."
}
```

### File Structure

```
web_ui/
├── index.html              # Main web interface
├── js/
│   └── simulation-ui.js     # Client-side JavaScript
└── css/ (styles embedded in HTML)

sociology_simulation/
├── web_monitor.py           # WebSocket server & data export
├── log_parser.py           # Historical log analysis
└── ...

run_web_simulation.py        # Main execution script
```

## Configuration

### Server Settings

Edit `run_web_simulation.py` to customize:

```python
# Change server ports
start_web_servers(
    host="localhost",
    ws_port=8765,    # WebSocket port
    http_port=8080   # HTTP port
)
```

### Auto-refresh Interval

Modify `simulation-ui.js`:

```javascript
// Change refresh interval (milliseconds)
ui.refreshInterval = setInterval(() => ui.loadSimulationData(), 5000);
```

### Export Settings

Configure in `web_monitor.py`:

```python
# Export frequency
self.export_interval = 1  # Export every N turns

# Log retention
self.max_log_entries = 1000  # Keep N log entries
```

## Troubleshooting

### Common Issues

**❌ WebSocket Connection Failed**
- Check if simulation is running
- Verify port 8765 is not blocked
- Check browser console for errors

**❌ No Map Data**
- Ensure simulation has started
- Check if export is enabled
- Verify API endpoint at http://localhost:8080/api/simulation-data

**❌ Agents Not Moving**
- Confirm auto-refresh is enabled
- Check simulation is progressing (turn counter)
- Verify WebSocket connection status

**❌ Missing Terrain/Resources**
- Check simulation world generation
- Verify data export in web_monitor.py
- Look for errors in simulation logs

### Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support  
- **Safari**: WebSocket support varies
- **Mobile**: Limited touch support

### Performance Notes

- Large maps (>128x128) may impact performance
- Many agents (>50) can slow rendering
- Auto-refresh increases CPU usage
- Zoom out for better performance with large simulations

## Advanced Usage

### Custom Data Sources

To use different data sources, modify the `loadSimulationData()` function in `simulation-ui.js`:

```javascript
// Load from custom API
const response = await fetch('/api/custom-data');

// Load from static file
const response = await fetch('data/simulation_turn_030.json');
```

### Adding Custom Visualizations

Extend the `draw()` method to add new visual elements:

```javascript
// In simulation-ui.js, after drawing agents:
this.drawCustomOverlay();

drawCustomOverlay() {
    // Custom drawing code here
    this.ctx.fillStyle = '#FFD700';
    // ... drawing logic
}
```

### Log Integration

The web UI can parse historical logs:

```bash
# Parse logs and serve via web UI
uv run python -m sociology_simulation.log_parser logs/ -o web_data/historical.json
```

## Development

### Project Structure

The web UI is designed as a standalone component that can be integrated with any simulation:

1. **Data Export**: `web_monitor.py` handles real-time data extraction
2. **WebSocket Server**: Provides live updates to the UI
3. **HTTP Server**: Serves static files and API endpoints
4. **Client UI**: HTML/JavaScript frontend with interactive features

### Extending the UI

To add new features:

1. **Backend**: Modify `web_monitor.py` to export additional data
2. **Frontend**: Update `simulation-ui.js` to display new information  
3. **API**: Add new endpoints for specific data requests
4. **Styling**: Extend CSS in `index.html` for visual improvements

The system is designed to be modular and extensible for different types of simulations and visualizations.