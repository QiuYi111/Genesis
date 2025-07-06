# MCP Integration Design for Generative Sociology Simulation

## Problem Statement

The current system has LLM generating JSON responses that frequently fail parsing, breaking the generative flow. The goal is to replace unreliable JSON generation with structured MCP tool calls while preserving all generative capabilities.

## Core Principle

**LLM should still drive all decisions and generation, but through structured tool calls instead of JSON output.**

## Current Generative Flow vs MCP Flow

### Current (Problematic):
```
Agent Perception → LLM Prompt → JSON Response → JSON Parsing (FAILS) → Fallback
```

### MCP Enhanced:
```
Agent Perception → LLM with MCP Tools → Tool Calls → Structured Execution
```

## MCP Tools Design

### 1. Agent Action Tools

Replace `generate_agent_action()` JSON output with structured tools:

```python
# Instead of LLM returning: {"action": "move north", "reasoning": "..."}
# LLM calls tool: move_agent(direction="north", reasoning="looking for resources")

@tool
def move_agent(direction: str, reasoning: str):
    """Move agent in specified direction"""
    
@tool  
def collect_resource(resource_type: str, amount: int, reasoning: str):
    """Collect resources from current location"""
    
@tool
def craft_item(item_name: str, materials: List[str], reasoning: str):
    """Craft item using available materials"""
    
@tool
def social_interact(target_agent: str, interaction_type: str, message: str):
    """Interact with another agent"""
```

### 2. Trinity Rule Generation Tools

Replace Trinity's JSON rule generation with:

```python
@tool
def create_terrain_type(name: str, description: str, movement_cost: float, resources: List[str]):
    """Define a new terrain type for the world"""
    
@tool
def set_resource_distribution(resource: str, terrain_probabilities: Dict[str, float]):
    """Set resource spawn probabilities per terrain"""
    
@tool
def create_world_rule(rule_name: str, description: str, conditions: List[str], effects: List[str]):
    """Create a new world rule that governs agent behavior"""
    
@tool
def trigger_era_transition(new_era: str, transition_events: List[str]):
    """Transition to a new historical era"""
```

### 3. Action Resolution Tools

Replace complex JSON action resolution with:

```python
@tool
def resolve_movement(agent_id: int, new_position: Tuple[int, int], energy_cost: int):
    """Resolve agent movement with positioning and energy"""
    
@tool
def resolve_resource_collection(agent_id: int, resource_gains: Dict[str, int], skill_experience: float):
    """Resolve resource collection with inventory and skill updates"""
    
@tool
def resolve_social_outcome(initiator: int, target: int, relationship_change: int, knowledge_transfer: List[str]):
    """Resolve social interaction outcomes"""
```

### 4. Skill System Tools

Replace skill JSON generation with:

```python
@tool
def unlock_skill(agent_id: int, skill_name: str, skill_description: str, prerequisites_met: List[str]):
    """Unlock a new skill for an agent"""
    
@tool
def gain_experience(agent_id: int, skill_name: str, experience_points: float, source_action: str):
    """Award skill experience from actions"""
    
@tool
def create_new_skill(skill_name: str, category: str, description: str, unlock_conditions: List[str]):
    """Create entirely new skill discovered through play"""
```

## Implementation Strategy

### Phase 1: Agent Action MCP Integration

1. **Keep existing LLM decision-making** in `agent.act()`
2. **Replace JSON output** with MCP tool calls
3. **Provide rich context** to LLM with tool descriptions
4. **Maintain perception and memory systems**

Example prompt transformation:
```python
# Old prompt: "Generate JSON action: {...}"
# New prompt: "You have these tools available: [move_agent, collect_resource, craft_item, social_interact]. Choose the best tool and parameters based on your perception and goals."
```

### Phase 2: Trinity MCP Integration

1. **Keep Trinity's world AI role**
2. **Replace rule generation JSON** with structured tools
3. **Maintain dynamic rule creation**
4. **Preserve era progression logic**

### Phase 3: Action Handler MCP Integration

1. **Keep complex action resolution**
2. **Replace outcome JSON** with structured tool responses
3. **Maintain fallback systems**
4. **Preserve social interaction complexity**

## Key Benefits

1. **Eliminates JSON parsing failures** - structured tool calls are always valid
2. **Preserves all generative capabilities** - LLM still makes all decisions
3. **Improves reliability** - no more "JSON解析失败，尝试修复"
4. **Maintains complexity** - all current features work through tools
5. **Better debugging** - clear tool call logs vs unclear JSON errors

## Critical: What NOT to Change

- ❌ Don't remove LLM decision-making
- ❌ Don't hardcode actions or rules  
- ❌ Don't eliminate generative content
- ❌ Don't remove perception, memory, or goals
- ❌ Don't simplify the skill system
- ❌ Don't remove Trinity's world management role

## What TO Change

- ✅ Replace JSON generation with tool calls
- ✅ Add structured validation through MCP
- ✅ Improve error handling through tool responses
- ✅ Maintain all existing generative features
- ✅ Keep LLM as the core decision engine

This approach solves the JSON parsing issues while preserving the sophisticated generative simulation that makes this system unique.