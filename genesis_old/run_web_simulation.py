#!/usr/bin/env python3
"""
Run sociology simulation with web UI monitoring.
This script starts the simulation and web servers together.
"""

import asyncio
import threading
import time
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sociology_simulation.main import main as simulation_main
from sociology_simulation.web_monitor import start_web_servers, get_monitor, LogCapture
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simulation_with_monitoring():
    """Run simulation with web monitoring enabled."""
    
    # Get monitor instance
    monitor = get_monitor()
    
    # Start log capture
    log_capture = LogCapture(monitor)
    log_capture.start_capture()
    
    try:
        # Start web servers in background
        logger.info("Starting web servers...")
        web_thread = start_web_servers(
            host="localhost",
            ws_port=8765,
            http_port=8081  # Use different port to avoid conflicts
        )
        
        # Give servers time to start
        time.sleep(2)
        
        logger.info("Web UI available at: http://localhost:8081")
        logger.info("WebSocket server at: ws://localhost:8765")
        logger.info("Starting simulation...")
        
        # Import and patch the main simulation to use our monitor
        from sociology_simulation import main
        
        # Monkey patch the World.step method to export data
        original_step = None
        
        def patched_step(self):
            """Patched World.step method that exports data to monitor."""
            nonlocal original_step
            
            # Call original step method
            result = original_step(self)
            
            # Export data to monitor
            try:
                monitor.update_world_data(self, self.agents, self.turn)
            except Exception as e:
                logger.error(f"Error updating monitor: {e}")
            
            return result
        
        # Apply the patch when simulation starts
        def patch_world_class():
            """Apply monitoring patch to World class."""
            from sociology_simulation.world import World
            nonlocal original_step
            
            if original_step is None:
                original_step = World.step
                World.step = patched_step
                logger.info("Applied monitoring patch to World class")
        
        # Patch before running simulation
        patch_world_class()
        
        # Run the simulation with default config
        import sys
        import os
        
        # Set working directory to ensure config is found
        os.chdir(project_root)
        
        # Add basic arguments to run a simple simulation
        sys.argv = [
            'run_web_simulation.py',
            'runtime.turns=30',
            'world.num_agents=10',
            'world.size=32'
        ]
        
        # Run the simulation
        simulation_main()
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Error during simulation: {e}")
        raise
    finally:
        # Cleanup
        log_capture.stop_capture()
        logger.info("Simulation ended")


if __name__ == "__main__":
    run_simulation_with_monitoring()