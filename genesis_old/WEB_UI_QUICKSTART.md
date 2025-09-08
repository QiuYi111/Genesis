# 🌍 Project Genesis Web UI

## Quick Start

The web UI provides real-time visualization and monitoring of the sociology simulation. Here's how to get started:

### 1. Install and Run
```bash
# Install dependencies
uv sync

# Run simulation with web UI (simple version)
uv run python run_simple_web_simulation.py

# Or run with full Hydra config (if config issues are resolved)
uv run python run_web_simulation.py
```

### 2. Access Web Interface
- **Web UI**: http://localhost:8081
- **WebSocket**: ws://localhost:8765 (automatic)

### 3. Verify Installation
```bash
# Test all components
uv run python test_web_ui.py
```

## 🎯 Features

### Interactive Map
- **🖱️ Click agents** to see detailed information (inventory, skills, social connections)
- **🖱️ Click map tiles** to see terrain type and available resources  
- **🔍 Zoom** with mouse wheel to see details
- **🎯 Reset view** button to center and reset zoom

### Real-time Monitoring
- **📊 Live updates** via WebSocket connection
- **🔄 Auto-refresh** toggle for continuous updates
- **📈 Status panel** showing turn, agent count, groups, era
- **🟢 Connection indicator** showing WebSocket status

### Information Panels
- **👥 Agents tab**: Selected agent details and agent list
- **🌍 Terrain tab**: Tile information and world statistics
- **📝 Logs tab**: Live simulation events and messages

### Data Export
- **💾 Export button** downloads current simulation state as JSON
- **📄 File export** automatically saves data every turn
- **📊 Historical data** can be analyzed with log parser

## 🗂️ File Structure

```
web_ui/
├── index.html                    # Main web interface
└── js/
    └── simulation-ui.js          # Interactive map and UI logic

sociology_simulation/
├── web_monitor.py               # Real-time data export & WebSocket server
└── log_parser.py               # Historical log analysis

run_simple_web_simulation.py    # Simple simulation runner (recommended)
run_web_simulation.py           # Full Hydra config runner
test_web_ui.py                  # Web UI component tests
WEB_UI_GUIDE.md                 # Detailed user guide
```

## 🎮 Usage Examples

### Monitoring Agent Behavior
1. Start simulation: `uv run python run_simple_web_simulation.py`
2. Open web UI: http://localhost:8081
3. Click on red circles (agents) to see their details
4. Watch agents move and change actions in real-time
5. Check the Agents tab for complete agent list

### Exploring the World
1. Click on different map tiles to see terrain and resources
2. Use mouse wheel to zoom in for detailed view
3. Check the Terrain tab for world statistics
4. Look for resource dots on tiles (small colored circles)

### Viewing Simulation Logs
1. Switch to the Logs tab in the sidebar
2. Watch live log messages as simulation progresses
3. Look for skill unlocks, group formations, and Trinity actions
4. Use color coding: Green=Info, Yellow=Warning, Red=Error

### Exporting Data
1. Click the "💾 Export" button to download current state
2. Check `web_data/` directory for auto-exported files
3. Use exported JSON for analysis or replay

## 🔧 Technical Details

### Map Visualization
- **Terrain Colors**: Mountain (brown), Forest (dark green), Grassland (light green), Water (blue), Desert (yellow)
- **Agent Display**: Red circles for agents, yellow for selected agent
- **Resource Indicators**: Small colored dots showing available resources
- **Interactive Elements**: Click-to-select, zoom, pan, tooltip on hover

### Real-time Updates
- **WebSocket Connection**: Automatic real-time data streaming
- **Data Format**: JSON messages with simulation state
- **Update Frequency**: Every simulation turn (configurable)
- **Fallback**: Manual refresh if WebSocket fails

### Data Export Format
```json
{
  "world": {
    "size": 32,
    "turn": 15,
    "terrain": ["GRASSLAND", "FOREST", ...],
    "resources": [{}, {"wood": 2}, ...]
  },
  "agents": [
    {
      "aid": 0,
      "name": "Rok",
      "x": 5, "y": 3,
      "inventory": {"wood": 2, "stone": 1},
      "skills": {"foraging": 3, "crafting": 1},
      "current_action": "foraging"
    }
  ]
}
```

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Error: [Errno 48] address already in use
# Solution: Change port in run_simple_web_simulation.py
await monitor.start_http_server("localhost", 8082)  # Different port
```

### WebSocket Connection Failed
- Check simulation is running
- Verify no firewall blocking port 8765
- Check browser console for error messages
- Try manual refresh if auto-refresh fails

### No Map Data
- Ensure simulation has started (check terminal output)
- Verify turn counter is increasing
- Check `/api/simulation-data` endpoint manually
- Look for errors in simulation logs

### Missing Dependencies
```bash
# Install websockets if missing
uv add websockets

# Verify all dependencies
uv sync
```

## 🎯 Advanced Usage

### Custom Simulation Parameters
Edit `run_simple_web_simulation.py` to customize:
```python
config = {
    'world': {
        'size': 64,        # Larger world
        'num_agents': 20   # More agents
    },
    'runtime': {
        'turns': 100       # Longer simulation
    }
}
```

### Historical Data Analysis
```bash
# Parse historical logs
uv run python -m sociology_simulation.log_parser logs/ -o analysis.json

# View timeline and summaries
uv run python -m sociology_simulation.log_parser logs/ --timeline --summary
```

### Custom Web UI
Modify `web_ui/js/simulation-ui.js` to add:
- New visualization layers
- Custom interaction handlers  
- Additional data displays
- Custom export formats

## ✅ Verification

Run the test suite to verify everything works:
```bash
uv run python test_web_ui.py
```

Expected output:
```
🎉 All tests passed! Web UI should work correctly.

To run the web simulation:
  uv run python run_simple_web_simulation.py
  Then open: http://localhost:8081
```

## 📖 More Information

- **[Detailed User Guide](WEB_UI_GUIDE.md)** - Comprehensive usage instructions
- **[Project README](README.md)** - Overall project information
- **[Configuration Guide](docs/user-guide/configuration.md)** - Simulation parameters

---

**🚀 Ready to explore emergent social behavior in real-time!**