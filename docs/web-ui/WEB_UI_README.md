# Sociology Simulation Web UI

A comprehensive web-based visualization tool for the sociology simulation project that displays terrain, agents, resources, and agent interactions in real-time.

## Features

### 🗺️ **Interactive World Map**
- **Terrain Visualization**: Different terrain types (Ocean, Forest, Grassland, Mountain, Desert, etc.) with color-coded display
- **Zoom and Pan**: Navigate through the 64x64 world grid
- **Click to Select**: Click on agents to view detailed information

### 👥 **Agent Visualization**
- **Agent Positions**: Red circles show agent locations on the map
- **Health Bars**: Visual health indicators below each agent
- **Agent Names**: Optional name display above agents
- **Agent Selection**: Click agents to see detailed stats
- **Agent List**: Side panel showing all agents with quick selection

### 📦 **Resource Display**
- **Resource Locations**: Brown squares indicate resource deposits
- **Resource Counts**: Numbers show quantity at each location
- **Resource Types**: Wood, fish, stone, apples, etc.
- **Resource Totals**: Summary panel showing total resources

### 💬 **Chat Bubbles**
- **Real-time Conversations**: Chat bubbles appear above agents during interactions
- **Message History**: View all conversations in the message panel
- **Agent Interactions**: See who is talking to whom and about what

### ⏰ **Turn-based Playback**
- **Turn Navigation**: Step through simulation turns
- **Agent Movement**: Watch agents move and interact over time
- **Status Tracking**: Monitor agent health, hunger, and inventory changes

## How to Use

### Method 1: Load Simulation Log Files
1. Open `sociology_simulation_web_ui.html` in a web browser
2. Click "Choose Log File" and select a `.log` file from the `logs/` directory
3. The simulation data will be parsed and visualized automatically
4. Use the turn selector to navigate through different simulation turns

### Method 2: Export Data First (Recommended)
1. **Export simulation data to JSON:**
   ```bash
   python3 export_simulation_data.py --log-file logs/latest_log.log --output web_ui_data.json
   ```

2. **Open the web UI:**
   - Open `sociology_simulation_web_ui.html` in a web browser
   - The UI will load with sample data by default

3. **Load your exported data:**
   - Click "Choose Log File" and select your exported JSON file
   - Or modify the HTML to load your JSON file directly

### Method 3: Generate Sample Data
1. Open `sociology_simulation_web_ui.html` in a web browser
2. Click "Generate Sample Data" to see a demo with 20 agents over 10 turns
3. This is useful for testing the UI without running the simulation

## Controls

- **Turn Selector**: Choose which simulation turn to display
- **Show Resources**: Toggle resource visualization on/off
- **Show Agent Names**: Toggle agent name display on/off
- **Show Chat Bubbles**: Toggle conversation bubbles on/off
- **Agent List**: Click any agent in the list to select and focus on them
- **Map Interaction**: Click on agents in the map to select them

## File Structure

```
├── sociology_simulation_web_ui.html    # Main web interface
├── export_simulation_data.py           # Data export script
├── web_ui_data.json                   # Exported simulation data
└── logs/                              # Simulation log files
    ├── sociology_simulation_*.log     # Individual simulation logs
    └── ...
```

## Technical Details

### Data Format
The web UI expects data in the following JSON format:
```json
{
  "metadata": {
    "era": "Stone Age",
    "world_size": 64,
    "num_agents": 20
  },
  "world": {
    "terrain": [[terrain_type, ...], ...],
    "resources": {"x,y": {"resource_type": count}}
  },
  "turns": [{
    "turn": 0,
    "agents": [{
      "id": 0,
      "name": "Agent Name",
      "pos": [x, y],
      "health": 100,
      "hunger": 0,
      "attributes": {...},
      "inventory": {...}
    }],
    "conversations": [...]
  }]
}
```

### Terrain Types
- **OCEAN**: Blue water areas
- **FOREST**: Green wooded areas  
- **GRASSLAND**: Light green plains
- **MOUNTAIN**: Gray elevated areas
- **DESERT**: Yellow sandy areas
- **RIVER**: Light blue waterways
- **And more**: CAVE, SWAMP, TUNDRA, JUNGLE, etc.

### Agent Information
Each agent displays:
- **Position**: (x, y) coordinates
- **Age**: Agent's current age
- **Health**: 0-100% health level
- **Hunger**: 0-100% hunger level
- **Attributes**: Strength, curiosity, charm
- **Inventory**: Items and quantities
- **Goal**: Personal objective

## Troubleshooting

### Log File Not Loading
- Ensure the log file is from a recent simulation run
- Check that the file contains proper simulation data
- Try using the data export script first

### No Agents Visible
- Check if the turn selector shows available turns
- Verify the log file contains agent data
- Try generating sample data to test the UI

### Performance Issues
- Large world sizes (>100x100) may be slow
- Consider reducing the number of displayed elements
- Use a modern web browser for better performance

## Development

To modify the web UI:
1. Edit `sociology_simulation_web_ui.html`
2. The file is completely self-contained with HTML, CSS, and JavaScript
3. No build process or dependencies required
4. Just open in a browser to test changes

### Adding New Features
- **New terrain types**: Add to `terrainColors` object
- **New visualizations**: Modify the `renderWorld()` function
- **New data sources**: Update the data parsing functions
- **New interactions**: Add event listeners and handlers

## Browser Compatibility

Tested and working on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

Part of the Sociology Simulation project.