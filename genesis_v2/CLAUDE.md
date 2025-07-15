# Project Genesis - Claude's Memory

## Project Overview

**Project Genesis** is a revolutionary LLM-driven sociology simulation engine that creates emergent social complexity from simple agent behaviors. This is a complete rewrite (v2) focusing on LLM-native design.

## Current Development Phase

- **Phase**: 1 - Foundation (Week 1-2)
- **Status**: Core infrastructure complete, moving to basic simulation
- **Branch**: Currently on `gh-pages` for web interface development

## Core Architecture

### Trinity System (🗿)

- **Purpose**: Central intelligence observing agent behaviors and dynamically creating capabilities
- **Components**:
  - Behavior Observer: Monitors all agent interactions
  - Skill Generator: Creates new skills based on observed needs
  - Rule Evolution: Updates rules as complexity emerges
  - Resource/Terrain Generation: Creates evolving world
  - Event Orchestrator: Triggers world events
  - Age Changer: Determines era progression (stone→bronze→etc)

### Agent Architecture

- **LLM-Native Design**: Every decision powered by language models
- **Key Components**:
  - Perception Engine: Processes world state and social context
  - Decision Engine: LLM-powered action selection
  - Memory System: Personal and cultural memory storage
  - Skill System: Dynamic capabilities from Trinity
  - Motivation System: Life goals and adaptive planning
  - Inventory/Crafting: Resource management and tool creation
  - Attributes: Health, strength, intelligence, etc.

### World Engine

- **64×64 cellular world** with realistic terrain and resources
- **Dynamic Systems**: Climate, resources, building, social spaces
- **Economic Layer**: Food, water, materials with real scarcity

## Technical Stack

- **Language**: Python 3.10+
- **Package Manager**: uv
- **Configuration**: Hydra
- **LLM Providers**: DeepSeek, OpenAI, Mock
- **Memory**: Context-aware with semantic retrieval
- **Web Interface**: Responsive monitoring dashboard

## Key Design Principles

1. **Emergence Over Prescription**: Complex structures from simple rules
2. **LLM-Native**: Every interaction mediated by language models
3. **Dynamic Evolution**: Rules, skills, and structures evolve in real-time
4. **Observable Emergence**: Clear tracking of social complexity development

## Development Roadmap

Once you think you finshed something and tested it, you can mark it as completed in the CLAUDE.md file

- **Important**: Try update phase items in your memory after finish a task

### Phase 1: Foundation (Week 1-2) 🟡 In Progress

- [X] Project structure setup
- [X] Configuration system (Hydra)
- [X] Basic world grid (64×64)
- [X] Simple terrain generation
- [X] Agent base class
- [X] LLM integration foundation
- [ ] Agent movement and basic actions
- [ ] Simple resource system (food/water)
- [ ] Basic LLM prompting
- [ ] Simulation loop
- [ ] State persistence
- [ ] CLI interface

### Phase 2: Intelligence (Week 3-4) 🔴 Pending

- Robust LLM service layer
- JSON schema parsing
- Multi-provider support
- Context-aware prompting
- Memory system
- Goal-oriented behavior
- Social interaction modeling

### Phase 3: Trinity System (Week 5-6) 🔴 Pending

- Pattern recognition system
- Behavior analytics
- Skill generation engine
- Rule evolution system
- Era progression mechanism

### Phase 4: Social Complexity (Week 7-8) 🔴 Pending

- Group formation dynamics
- Leadership emergence
- Economic systems
- Cultural evolution
- Governance structures

### Phase 5: Production (Week 9-10) 🔴 Pending

- Performance optimization
- Web interface
- Documentation
- Testing suite

## Key Metrics & Success Criteria

- **Simulation**: 100+ concurrent agents, 10+ steps/sec
- **LLM**: <2s response time, 99.9% JSON parsing success
- **Memory**: <2GB usage for 100 agents
- **Emergence**: Observable social structure formation

## Current Focus

Working on Phase 1 completion - implementing basic agent movement, resource systems, and simulation loop before moving to Phase 2 LLM intelligence features.

## Git Branches

- `main`: Core simulation engine
- `dev`: Active development
- `gh-pages`: Web interface and documentation