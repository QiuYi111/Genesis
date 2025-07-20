# Project Genesis Refactoring Plan

## Executive Summary

This document outlines the comprehensive refactoring strategy for unifying the two existing codebases (v1 sociology_simulation and v2 genesis_v2) into a single, production-ready simulation engine. The v2 architecture provides a superior foundation, and the refactoring will selectively migrate mature features from v1 while eliminating duplication and technical debt.

## Current State Analysis

### v1 (Legacy) Characteristics
- **Architecture**: Monolithic, tightly coupled components
- **LLM Integration**: Reactive, post-hoc JSON parsing fixes
- **Language**: Mixed Chinese/English variable naming
- **Features**: Mature social systems, economic systems, cultural memory
- **Issues**: JSON parsing failures, complex state management

### v2 (Genesis) Characteristics
- **Architecture**: Modular, clean separation of concerns
- **LLM Integration**: Proactive, schema-driven design
- **Language**: Consistent English naming
- **Features**: Advanced Trinity system, LLM-native agents
- **Status**: Foundation complete, ready for feature integration

## Unified Architecture

### Core Module Structure
```
genesis/
├── core/
│   ├── __init__.py
│   ├── simulation.py          # Main orchestrator
│   ├── world.py              # World state management
│   └── events.py             # Event system
├── agents/
│   ├── __init__.py
│   ├── base.py               # Agent base class (from v2)
│   ├── memory.py            # Memory management (enhanced from v1)
│   ├── skills.py            # Skill system
│   ├── social.py            # Social connections (from v1)
│   └── groups.py            # Group dynamics (from v1)
├── llm/
│   ├── __init__.py
│   ├── providers/            # LLM provider implementations
│   ├── schemas.py           # JSON schemas
│   ├── prompting.py         # Prompt management
│   └── conversation.py      # Chat system (from v1)
├── trinity/
│   ├── __init__.py
│   ├── system.py            # Trinity orchestration (v2)
│   ├── observer.py          # Behavior observation
│   ├── generator.py         # Skill/rule generation
│   ├── cultural_memory.py   # Cultural evolution (from v1)
│   ├── technology.py        # Tech progression (from v1)
│   ├── economy.py           # Economic systems (from v1)
│   └── politics.py          # Political systems (from v1)
├── world/
│   ├── __init__.py
│   ├── terrain.py           # Terrain generation
│   ├── resources.py         # Resource management
│   ├── buildings.py         # Building system
│   └── climate.py           # Climate system
├── web/
│   ├── __init__.py
│   ├── api.py               # Web API
│   ├── export.py            # Data export (from v1)
│   └── monitor.py           # Real-time monitoring
└── utils/
    ├── __init__.py
    ├── config.py           # Configuration management
    └── logging.py          # Logging utilities
```

## Migration Strategy

### Phase 1: Foundation Merge (Week 1-2)
**Priority**: High
**Goal**: Establish unified codebase structure

#### Tasks:
1. **Repository Structure**
   - Create new unified repository structure
   - Migrate v2 core components as foundation
   - Set up proper package structure

2. **Configuration System**
   - Unify v1's Hydra config with v2's OmegaConf
   - Create single configuration schema
   - Implement environment-based configuration

3. **Core Classes**
   - Use v2's Agent as base class
   - Port v1's social features into v2 structure
   - Migrate v1's world systems to v2 architecture

### Phase 2: Feature Integration (Week 3-4)
**Priority**: High
**Goal**: Migrate mature v1 features to v2 architecture

#### Social Systems (from v1)
- **Social connections**: Port relationship system
- **Group dynamics**: Migrate group formation and leadership
- **Reputation system**: Integrate reputation mechanics
- **Communication**: Add conversation system

#### Economic Systems (from v1)
- **Resource rules**: Port advanced resource distribution
- **Trade mechanics**: Implement exchange system
- **Market dynamics**: Add market formation
- **Wealth accumulation**: Track agent wealth

#### Cultural Systems (from v1)
- **Cultural memory**: Port cultural knowledge system
- **Technology progression**: Implement tech tree
- **Knowledge transfer**: Add skill sharing
- **Cultural norms**: Dynamic rule evolution

### Phase 3: Advanced Integration (Week 5-6)
**Priority**: Medium
**Goal**: Enhance v2 Trinity system with v1 capabilities

#### Trinity Enhancement
- **Behavior analytics**: Port v1's pattern recognition
- **Skill generation**: Enhance with v1's skill system
- **Rule evolution**: Add v1's dynamic rules
- **Era progression**: Implement v1's age progression

#### LLM Integration
- **Conversation system**: Port v1's chat capabilities
- **Goal generation**: Add v1's goal setting
- **Memory integration**: Combine memory systems

### Phase 4: Web & Monitoring (Week 7-8)
**Priority**: Medium
**Goal**: Create unified web interface

#### Web Features
- **Real-time monitoring**: Port v1's web export
- **Interactive visualization**: Enhanced dashboard
- **Simulation control**: Start/stop/pause functionality
- **Data export**: JSON/CSV export capabilities

### Phase 5: Testing & Optimization (Week 9-10)
**Priority**: Medium
**Goal**: Ensure production readiness

#### Testing
- **Unit tests**: Comprehensive test suite
- **Integration tests**: End-to-end testing
- **Performance tests**: Load testing with 100+ agents
- **LLM tests**: Response time and accuracy testing

## Detailed Component Mapping

### Agent System Migration
```
v1 Agent Features → v2 Agent Base Class
├── Social connections → agents/social.py
├── Group membership → agents/groups.py
├── Cultural memory → trinity/cultural_memory.py
├── Technology skills → trinity/technology.py
└── Economic behaviors → trinity/economy.py
```

### World System Migration
```
v1 World Features → v2 World Engine
├── Terrain generation → world/terrain.py
├── Resource rules → world/resources.py
├── Building system → world/buildings.py
├── Climate system → world/climate.py
└── Event system → core/events.py
```

### Trinity System Enhancement
```
v1 Trinity Features → v2 Trinity System
├── Behavior observation → trinity/observer.py
├── Rule evolution → trinity/generator.py
├── Skill generation → trinity/generator.py
├── Age progression → trinity/system.py
└── Cultural evolution → trinity/cultural_memory.py
```

## Technical Specifications

### Performance Targets
- **Agent count**: 100+ concurrent agents
- **Turn processing**: <2 seconds per turn
- **LLM response time**: <1 second average
- **Memory usage**: <2GB for full simulation
- **JSON parsing**: 99.9% success rate

### Configuration Schema
```yaml
simulation:
  name: "Unified Genesis Simulation"
  max_turns: 1000
  seed: 42

world:
  width: 64
  height: 64
  terrain_types: ["grassland", "forest", "mountain", "water", "desert"]

agents:
  count: 50
  starting_inventory:
    food: 5
    water: 5
    wood: 2

llm:
  provider: "deepseek"
  model: "deepseek-chat"
  temperature: 0.7
  max_retries: 3

trinity:
  observation_frequency: 5
  skill_generation: true
  rule_evolution: true
  era_progression: true

web:
  enabled: true
  port: 8080
  export_format: "json"
```

## Implementation Checklist

### Week 1-2: Foundation
- [ ] Create unified repository structure
- [ ] Migrate v2 core components
- [ ] Unify configuration system
- [ ] Set up development environment
- [ ] Create migration scripts

### Week 3-4: Feature Integration
- [ ] Port social systems from v1
- [ ] Migrate economic systems
- [ ] Integrate cultural memory
- [ ] Add technology progression
- [ ] Implement conversation system

### Week 5-6: Trinity Enhancement
- [ ] Enhance behavior observation
- [ ] Add rule evolution system
- [ ] Implement era progression
- [ ] Integrate cultural evolution
- [ ] Add economic governance

### Week 7-8: Web Integration
- [ ] Port web export functionality
- [ ] Create real-time dashboard
- [ ] Add interactive controls
- [ ] Implement data visualization
- [ ] Add export capabilities

### Week 9-10: Testing & Polish
- [ ] Write comprehensive tests
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] User guide creation
- [ ] Production deployment

## Risk Mitigation

### Technical Risks
- **LLM API failures**: Implement mock provider fallback
- **Memory overflow**: Implement memory limits and cleanup
- **Performance degradation**: Add performance monitoring

### Migration Risks
- **Feature regression**: Maintain backward compatibility layer
- **Configuration conflicts**: Create migration scripts
- **Data loss**: Implement state backup and recovery

## Success Criteria

### Technical Metrics
- All v1 features successfully ported to v2 architecture
- 100+ agents running simultaneously
- <2 second turn processing time
- 99.9% JSON parsing success rate
- Zero feature regression

### User Experience
- Seamless migration from v1 to unified system
- Enhanced web interface with real-time monitoring
- Improved documentation and examples
- Better error handling and debugging

## Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Foundation | 2 weeks | Unified codebase, config system |
| Feature Integration | 2 weeks | Social, economic, cultural systems |
| Trinity Enhancement | 2 weeks | Advanced behavior analysis |
| Web Integration | 2 weeks | Real-time monitoring dashboard |
| Testing & Polish | 2 weeks | Production-ready system |

## Next Steps

1. **Review and approve** this plan
2. **Set up development environment** for unified codebase
3. **Begin Phase 1** implementation
4. **Establish testing framework** early
5. **Create migration timeline** and milestones

This refactoring plan ensures a smooth transition from the legacy v1 system to the modern v2 architecture while preserving all valuable features and capabilities.