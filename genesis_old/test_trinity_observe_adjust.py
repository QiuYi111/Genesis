#!/usr/bin/env python3
"""Test Trinity observe/adjust functionality with NullProvider"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sociology_simulation'))

from sociology_simulation.bible import Bible
from sociology_simulation.trinity import Trinity
from sociology_simulation.services.llm_provider import NullProvider, NullPlanner


class MockWorld:
    """Minimal mock world for testing Trinity"""
    def __init__(self):
        self.size = 10
        self.map = [['grass' for _ in range(self.size)] for _ in range(self.size)]
        self.resources = {}
        self.agents = []


def test_trinity_observe_adjust():
    """Test Trinity observe/adjust with NullProvider"""
    print("Testing Trinity observe/adjust functionality...")
    
    # Create Trinity with NullProvider
    bible = Bible()
    trinity = Trinity(bible, "石器时代测试时代")
    
    # Test observe method
    events = [
        {"type": "move", "agent_id": 1, "position": (1, 1)},
        {"type": "forage", "agent_id": 1, "resource": "apple", "amount": 2},
        {"type": "craft", "agent_id": 2, "item": "tool", "success": True}
    ]
    
    trinity.observe(events)
    stats = trinity.get_stats()
    
    print(f"✓ Observe method works, stats: {list(stats.keys())}")
    assert "move" in stats
    assert "forage" in stats
    assert "craft" in stats
    
    # Test adjust method with mock world
    world = MockWorld()
    actions = trinity.adjust(world)
    
    print(f"✓ Adjust method works, actions: {actions}")
    assert actions.resource_regen_multiplier == 1.0  # Default from NullPlanner
    assert actions.terrain_adjustments is None
    assert actions.skill_updates is None
    
    # Test with different planner
    class TestPlanner:
        def plan(self, signals):
            return {
                "regen": 1.5,
                "terrain": [((0, 0), "mountain")],
                "skills": {"new_skill": {"level": 1}}
            }
    
    trinity.set_planner(TestPlanner())
    actions = trinity.adjust(world)
    
    print(f"✓ Custom planner works, actions: {actions}")
    assert actions.resource_regen_multiplier == 1.5
    assert actions.terrain_adjustments == [((0, 0), "mountain")]
    assert actions.skill_updates == {"new_skill": {"level": 1}}
    
    print("✅ All Trinity observe/adjust tests passed!")


def test_resource_status_calculation():
    """Test resource status calculation"""
    print("\nTesting resource status calculation...")
    
    bible = Bible()
    trinity = Trinity(bible, "测试时代")
    
    world = MockWorld()
    # Add some resources
    world.resources[(1, 1)] = {"apple": 5, "wood": 2}
    world.resources[(2, 2)] = {"apple": 3}
    world.map[1][1] = "forest"
    world.map[2][2] = "grass"
    
    # Set up resource rules
    trinity.resource_rules = {
        "apple": {"forest": 0.8, "grass": 0.3},
        "wood": {"forest": 0.9, "grass": 0.1}
    }
    
    status = trinity.compute_resource_status(world)
    
    print(f"✓ Resource status calculated: {list(status.keys())}")
    assert "apple" in status
    assert "wood" in status
    assert status["apple"]["current_count"] == 8  # 5 + 3
    assert status["wood"]["current_count"] == 2
    
    print("✅ Resource status tests passed!")


if __name__ == "__main__":
    test_trinity_observe_adjust()
    test_resource_status_calculation()
    print("\n🎉 All tests completed successfully!")