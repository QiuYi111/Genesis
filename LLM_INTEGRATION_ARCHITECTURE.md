# Project Genesis - LLM Integration Architecture

## 📋 Product Requirements Document (PRD)

### Executive Summary

**Project**: Project Genesis - Robust LLM Integration Architecture
**Vision**: Create a resilient, scalable, and maintainable LLM-driven sociology simulation engine that allowing LLM doing simple actions and show emergent social complexity.
**Target Users**: Researchers, sociologists, game developers, AI researcher Problem Statement

**Current Issues**:

- 80% of simulation failures due to JSON parsing errors
- API timeouts causing simulation hangs
- LLM services fail frequently
- Memory leaks from unbounded conversation history
- Complex async chains creating deadlocks

**User Impact**:

- Researchers cannot complete long-running simulations
- Development blocked by unstable LLM dependencies
- Inconsistent results across different LLM providers

### Product Requirements

#### Functional Requirements

| Requirement ID | Description                                                            | Priority | Acceptance Criteria                                                           |
| -------------- | ---------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------- |
| FR-001         | Robust JSON parsing or use function call, mcp to get 99%+ success rate | P0       | <0.1% parsing failures across 10k simulations                                 |
| FR-002         | Generative Skills, actions and resources                               | P0       | emegent agents action happens, index-like growth of action and env complixity |
| FR-003         | Configurable LLM provider switching                                    | P1       | Switch between DeepSeek/OpenAI without code changes                           |
| FR-004         | Real-time LLM call monitoring                                          | P1       | Display API usage, latency, and error rates                                   |
| FR-005         | Memory-bounded conversation history                                    | P1       | Max 1000 conversations per simulation                                         |
| FR-006         | Batch LLM request processing                                           | P2       | Process 50+ agent decisions concurrently                                      |
| FR-007         | Comprehensive LLM response caching                                     | P2       | 70%+ cache hit rate for repeated requests                                     |

#### Non-Functional Requirements

| Requirement ID | Description                     | Target              |
| -------------- | ------------------------------- | ------------------- |
| NFR-001        | Simulation uptime               | 99.9%               |
| NFR-002        | LLM response time               | <2s average         |
| NFR-003        | Memory usage                    | <2GB for 100 agents |
| NFR-004        | LLM action parsing success rate | 99.9%               |
| NFR-005        | API failure recovery time       | <30 seconds         |

```

```


```

```

## 🏗️ Technical Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────┐
│           Simulation Core            │
├─────────────────────────────────────┤
│  World Engine → Agent System        │
│              ↓                      │
│         Trinity System              │
│              ↓                      │
│      LLM Integration Layer          │
└─────────────────────────────────────┘
         │
┌─────────────────────────────────────┐
│         LLM Services                 │
├─────────────────────────────────────┤
│  Response Parser  │  Mock Service   │
│  Cache Layer      │  Rate Limiter   │
└─────────────────────────────────────┘
         │
┌─────────────────────────────────────┐
│        External APIs                 │
├─────────────────────────────────────┤
│  DeepSeek API  │  OpenAI API       │
│  Local LLM     │  Health Checks    │
└─────────────────────────────────────┘
```

### Data Flow Architecture

#### Request Processing Pipeline

1. **Agent Request** → json or funcion call or mcp
2. **Cache Check** → Return cached response if available
3. **LLM Call** → Make API request with retry logic
4. **Store Cache** → Cache successful responses
5. **Error Handling** → Fallback to mock/safe defaults

#### Error Recovery Flow

- **API Failure** → Switch to mock responses
- **Timeout** → Retry with exponential backoff → Mock fallback
- **Rate Limit** → Queue management → Batch processing

### Configuration Architecture

#### LLM Configuration Schema

```yaml
# config/llm.yaml
llm:
  providers:
    deepseek:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      temperature: 0.7
  
    openai:
      api_key_env: "OPENAI_API_KEY"
      base_url: "https://api.openai.com/v1"
      model: "gpt-3.5-turbo"
      temperature: 0.7
  
  mock:
    enabled: false
    response_delay: 0.1
    realistic_errors: true
  
  cache:
    enabled: true
    ttl: 3600
    max_size: 10000
  
  rate_limit:
    requests_per_minute: 60
    burst_limit: 10
  
  retry:
    max_attempts: 3
    backoff_factor: 2.0
    max_wait: 30.0
```

### API Design

#### Core Interfaces

```python
class LLMProvider(Protocol):
    """Core LLM provider interface"""
    async def generate(self, prompt: str, context: Dict) -> str: ...
    async def validate_response(self, response: str, schema: Type) -> bool: ...

class DeepSeekProvider(LLMProvider):
    async def generate(self, prompt: str, context: Dict) -> str:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.config.base_url,
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config.temperature
                }
            )
            return response.json()["choices"][0]["message"]["content"]
```

### Monitoring & Observability

#### Metrics Collection

```python
class LLMMetrics:
    def __init__(self):
        self.metrics = {
            'requests_total': Counter(),
            'requests_success': Counter(),
            'requests_failed': Counter(),
            'response_time': Histogram(),
            'cache_hit_rate': Gauge(),
            'json_parse_errors': Counter()
        }
```

#### Health Checks

```python
class HealthChecker:
    async def check_llm_health(self, provider: str) -> HealthStatus:
        try:
            response = await self.test_llm_call(provider)
            return HealthStatus(
                status="healthy",
                latency=response.duration,
                last_check=datetime.now()
            )
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                error=str(e),
                last_check=datetime.now()
            )
```

### Testing Strategy

#### Test Architecture

```python
class LLMTestHarness:
    """Comprehensive testing for LLM integration"""
  
    def __init__(self):
        self.mock_provider = MockLLMProvider()
        self.test_scenarios = TestScenarioGenerator()
  
    async def test_json_parsing(self):
        malformed_jsons = [
            "{'key': 'value'}",
            '{"key": "value",}',
            'Invalid JSON string',
            'Partial JSON {"key": "value"'
        ]
  
        for malformed in malformed_jsons:
            result = await self.parser.parse(malformed, TestSchema)
            assert result is not None
```

### Deployment Architecture

#### Local Development

```bash
# Mock mode
genesis run --mock-mode
genesis run --provider=deepseek --api-key=mock_key

# Real LLM
export DEEPSEEK_API_KEY="your_key"
genesis run --provider=deepseek
```

#### Production Deployment

```yaml
# docker-compose.yml
services:
  genesis:
    image: genesis:latest
    environment:
      - LLM_PROVIDER=deepseek
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - prometheus
  
  redis:
    image: redis:alpine
  
  prometheus:
    image: prom/prometheus
```

### Migration Plan

#### Phase 1: Foundation (Week 1-2)

- [ ] Implement robust JSON parser
- [ ] Create mock LLM service
- [ ] Add comprehensive error handling

#### Phase 2: Core Integration (Week 3-4)

- [ ] Refactor Trinity system
- [ ] Implement caching layer
- [ ] Add monitoring metrics

#### Phase 3: Advanced Features (Week 5-6)

- [ ] Add batch processing
- [ ] Implement provider switching
- [ ] Add performance optimization

#### Phase 4: Production Ready (Week 7-8)

- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Performance tuning

### Success Metrics

| Metric                  | Current   | Target | Measurement           |
| ----------------------- | --------- | ------ | --------------------- |
| JSON Parse Success Rate | 60%       | 99.9%  | Automated testing     |
| Simulation Uptime       | 70%       | 99.9%  | Production monitoring |
| API Response Time       | 5-30s     | <2s    | Performance testing   |
| Memory Usage            | Unbounded | <2GB   | Memory profiling      |
| Cache Hit Rate          | 0%        | 70%+   | Analytics             |

### Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Run with mock LLM (no API key needed)
python -m sociology_simulation.main \
    llm.mock.enabled=true \
    simulation.era_prompt="stone age tribes" \
    world.num_agents=10 \
    runtime.turns=50

# 3. Run with real LLM
export DEEPSEEK_API_KEY="your_key_here"
python -m sociology_simulation.main \
    llm.providers.deepseek.api_key_env="DEEPSEEK_API_KEY" \
    simulation.era_prompt="bronze age civilization" \
    world.num_agents=20 \
    runtime.turns=100
```

This architecture ensures Project Genesis becomes a production-ready sociology simulation platform that gracefully handles LLM dependencies while maintaining complex emergent behaviors.
