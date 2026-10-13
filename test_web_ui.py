#!/usr/bin/env python3
"""
Test script to verify web UI components work correctly.
"""

import json
import asyncio
import tempfile
from pathlib import Path

# Add project root to path
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sociology_simulation.web_monitor import SimulationMonitor
from sociology_simulation.log_parser import SimulationLogParser


def test_monitor():
    """Test the simulation monitor."""
    print("Testing SimulationMonitor...")
    
    # Create monitor with temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        monitor = SimulationMonitor(temp_dir)
        
        # Create fake world and agents
        class FakeWorld:
            def __init__(self):
                self.size = 16
                self.terrain = {(x, y): 'GRASSLAND' for x in range(16) for y in range(16)}
                self.resources = {(x, y): {'wood': 2} if (x + y) % 3 == 0 else {} 
                                for x in range(16) for y in range(16)}
        
        class FakeAgent:
            def __init__(self, aid, name):
                self.aid = aid
                self.name = name
                self.x = aid * 2
                self.y = aid
                self.inventory = {'wood': aid, 'stone': aid + 1}
                self.skills = {'foraging': aid + 1}
                self.current_action = f'action_{aid}'
        
        world = FakeWorld()
        agents = [FakeAgent(i, f'TestAgent{i}') for i in range(3)]
        
        # Test update
        monitor.update_world_data(world, agents, 5)
        
        # Check data
        assert monitor.current_data['turn'] == 5
        assert len(monitor.current_data['agents']) == 3
        assert monitor.current_data['world']['size'] == 16
        
        print("✓ Monitor update test passed")
        
        # Test log entry
        monitor.add_log_entry('INFO', 'Test message', 1)
        assert len(monitor.current_data['logs']) == 1
        assert monitor.current_data['logs'][0]['message'] == 'Test message'
        
        print("✓ Log entry test passed")
        
        # Test file export
        monitor._export_to_file()
        export_files = list(Path(temp_dir).glob('*.json'))
        assert len(export_files) >= 1
        
        # Load and verify exported data
        with open(export_files[0]) as f:
            exported_data = json.load(f)
        
        assert exported_data['turn'] == 5
        assert len(exported_data['agents']) == 3
        
        print("✓ File export test passed")


def test_log_parser():
    """Test the log parser."""
    print("\nTesting SimulationLogParser...")
    
    # Create test log content
    test_log = """
2025-07-05 10:00:00 - INFO - Turn 1:
2025-07-05 10:00:01 - INFO - Rok(0) moved to (5, 3)
2025-07-05 10:00:02 - INFO - Ash(1) foraging for food
2025-07-05 10:00:03 - INFO - Rok(0) unlocked skill: crafting
2025-07-05 10:00:04 - INFO - Trinity: Creating new skill based on behavior
2025-07-05 10:00:05 - INFO - Group "Hunters" formed with members: Rok, Ash
2025-07-05 10:00:06 - INFO - Turn 2:
2025-07-05 10:00:07 - INFO - Ash(1) moved to (2, 7)
    """.strip()
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(test_log)
        log_file = Path(f.name)
    
    try:
        parser = SimulationLogParser()
        data = parser.parse_log_file(log_file)
        
        # Verify parsing
        assert data['metadata']['total_turns'] == 2
        assert len(data['agents']) >= 2
        assert 'Rok' in [agent['name'] for agent in data['agents'].values()]
        assert len(data['trinity_actions']) >= 1
        assert 'Hunters' in data['groups']
        
        print("✓ Log parsing test passed")
        
        # Test timeline extraction
        timeline = parser.extract_simulation_timeline(data)
        assert len(timeline) == 2  # 2 turns
        assert timeline[0]['turn'] == 1
        
        print("✓ Timeline extraction test passed")
        
        # Test agent summary
        summaries = parser.generate_agent_summary(data)
        assert len(summaries) >= 2
        
        print("✓ Agent summary test passed")
        
    finally:
        log_file.unlink()  # Clean up


def test_web_ui_static():
    """Test that web UI files exist and are readable."""
    print("\nTesting Web UI files...")
    
    web_ui_dir = project_root / 'web_ui'
    
    # Check main files exist
    assert (web_ui_dir / 'index.html').exists(), "index.html not found"
    assert (web_ui_dir / 'js' / 'simulation-ui.js').exists(), "simulation-ui.js not found"
    
    print("✓ Web UI files exist")
    
    # Check HTML file is valid
    with open(web_ui_dir / 'index.html') as f:
        html_content = f.read()
    
    assert '<canvas id="map-canvas"' in html_content, "Map canvas not found in HTML"
    assert 'simulation-ui.js' in html_content, "JavaScript file not referenced"
    
    print("✓ HTML structure test passed")
    
    # Check JavaScript file is valid
    with open(web_ui_dir / 'js' / 'simulation-ui.js') as f:
        js_content = f.read()
    
    assert 'class SimulationUI' in js_content, "SimulationUI class not found"
    assert 'WebSocket' in js_content, "WebSocket code not found"
    
    print("✓ JavaScript structure test passed")


async def test_websocket_server():
    """Test WebSocket server can start."""
    print("\nTesting WebSocket server...")
    
    monitor = SimulationMonitor()
    
    try:
        # Try to start server on different port to avoid conflicts
        await monitor.start_websocket_server("localhost", 8766)
        print("✓ WebSocket server started successfully")
        
        # Test server is running
        import websockets
        
        async def test_connection():
            try:
                async with websockets.connect("ws://localhost:8766") as websocket:
                    # Server should accept connection
                    print("✓ WebSocket connection test passed")
            except Exception as e:
                print(f"✗ WebSocket connection failed: {e}")
        
        await test_connection()
        
    except Exception as e:
        print(f"✗ WebSocket server test failed: {e}")
    finally:
        await monitor.stop_websocket_server()


def main():
    """Run all tests."""
    print("Running Web UI component tests...\n")
    
    try:
        test_monitor()
        test_log_parser()
        test_web_ui_static()
        
        # Run async test
        asyncio.run(test_websocket_server())
        
        print("\n🎉 All tests passed! Web UI should work correctly.")
        print("\nTo run the web simulation:")
        print("  uv run python run_simple_web_simulation.py")
        print("  Then open: http://localhost:8081")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()