# Cloud Multi-Agent Code Style Enforcer

A production-grade, cloud-native code analysis system using multiple AI agents with reinforcement learning for personalized code style enforcement.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Efficiency and Scalability Features](#efficiency-and-scalability-features)
- [Project Structure](#project-structure)
- [API Specification](#api-specification)
- [Development Phases](#development-phases)
- [Infrastructure](#infrastructure)

---

## Architecture Overview

This system analyzes code using multiple specialized AI agents running in parallel, with results merged using reinforcement learning weights that adapt based on user feedback.

### Core Components

- **Multi-Agent Analysis**: Parallel AI agents for style, naming, minimalism, docstrings, and security
- **Distributed Caching**: Redis-based cache for instant results on previously analyzed code
- **Async RL Pipeline**: Asynchronous reinforcement learning with SQS queue and background workers
- **Rate Limiting**: Global rate limiting to prevent abuse and control costs
- **Observability**: Comprehensive metrics for latency, cache hits, and token usage

---

## Efficiency and Scalability Features

### 1. Parallel Agents with Shared Context

- Single normalized code representation shared across all agents
- All agents run in parallel using `asyncio.gather`
- Shared LLM client instance for efficiency

### 2. Parse-First Architecture

```
Raw Code
    ↓
Parser (AST)
    ├── fails? → SyntaxError (100% confidence, no LLM call)
    └── passes → Structured AST + tokens
                     ↓
               All Agents (LLM + AST rules)
                     ↓
               Final Suggestions
```

**Guarantees:**
- No LLM tokens wasted on unparseable code
- Duplicate function/class definitions caught before LLM runs (severity 4)
- Unreachable code (`if False:`, `while 0:`) detected deterministically
- AST-based findings have 100% confidence
- Agents receive structured ParseResult, not raw text

**Parser extracts:**
- All imports (module, names, line, is_from)
- All function/class definitions (name, line, args, decorators)
- All assignments (targets, value_type)
- All control flow (if/for/while/try/with, is_unreachable)

### 3. Code Hashing with Distributed Cache

```python
# Workflow
1. Compute code_hash from normalized code
2. Check Redis cache
3. Cache hit → return previous AnalysisResult instantly
4. Cache miss → run agents, store result in cache
5. Cache shared across multiple ECS tasks
```

### 4. Asynchronous RL Updates

- `/feedback` endpoint does not update RL weights directly
- Pushes message to SQS queue and returns `"status": "queued"`
- Separate worker (`feedback_processor`) reads queue and updates DynamoDB
- Decouples feedback response from RL computation

### 5. Full Context Storage for RL

- Hot path: Small cache structure in Redis
- Cold storage: Full `(code, analysis_result, feedback)` in S3 for advanced RL training

### 6. Agent Timeouts and Circuit Breakers

- Each agent has strict timeout
- Failed/timeout agents are skipped and logged
- Other agents continue and return results
- Overall latency protected

### 7. Global Rate Limiting

- Per IP or per API key rate limiting
- Implemented in `rate_limiter.py`
- Protects LLM bill and prevents abuse

### 8. Metrics and Observability

Track key metrics:
- Latency (P50, P99)
- Token usage per agent
- Cache hit rate
- RL queue depth
- Error rates
- Expose to Prometheus or CloudWatch

---

## Project Structure

```
code-style-enforcer/
├── pyproject.toml
├── README.md
├── .gitignore
├── .env.example
│
├── infra/
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── dynamodb.tf
│       ├── redis.tf
│       ├── ecs_service_api.tf
│       ├── ecs_service_worker.tf
│       ├── iam_roles.tf
│       └── sqs_queue.tf
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api/
│       │   └── apiClient.js
│       ├── components/
│       │   ├── CodeEditor.jsx
│       │   ├── SuggestionsList.jsx
│       │   ├── AgentWeightsBar.jsx
│       │   └── RatingPanel.jsx
│       ├── pages/
│       │   └── Home.jsx
│       └── styles/
│           └── main.css
│
├── src/
│   └── backend/
│       ├── main.py                      # FastAPI app entry
│       ├── config.py                    # Environment, model config, limits
│       ├── logging_config.py            # Structured logging with request-id
│       │
│       ├── api/
│       │   ├── schemas.py               # Pydantic models
│       │   ├── routes_code.py           # /analyze endpoint
│       │   ├── routes_feedback.py       # /feedback endpoint
│       │   ├── routes_agents.py         # /agents/weights endpoint
│       │   ├── routes_health.py         # /health endpoint
│       │   └── dependencies.py          # Auth, rate limiting, request-id
│       │
│       ├── core/
│       │   ├── code_hash.py             # Normalized hash of code
│       │   ├── models.py                # Suggestion, AgentResult, AnalysisResult
│       │   ├── cache.py                 # Redis cache wrapper
│       │   └── rate_limiter.py          # Global rate limiting
│       │
│       ├── agents/
│       │   ├── base_agent.py
│       │   ├── style_agent.py
│       │   ├── naming_agent.py
│       │   ├── minimalism_agent.py
│       │   ├── docstring_agent.py
│       │   ├── security_agent.py
│       │   └── langchain_chains/
│       │       ├── common_prompt_fragments.py
│       │       ├── style_chain.py
│       │       ├── naming_chain.py
│       │       ├── minimalism_chain.py
│       │       ├── docstring_chain.py
│       │       └── security_chain.py
│       │
│       ├── services/
│       │   ├── agent_dispatcher.py      # Run agents in parallel with timeouts
│       │   ├── suggestion_merger.py     # Merge suggestions with RL weights
│       │   ├── analyzer_service.py      # Full analyze pipeline
│       │   ├── feedback_service.py      # Publish feedback to queue
│       │   └── rl_context_builder.py    # Build RL state from analysis
│       │
│       ├── rl/
│       │   ├── policy_store.py          # DynamoDB based agent weights
│       │   ├── preference_policy.py     # Scoring logic
│       │   ├── reward_engine.py         # Feedback → reward value
│       │   └── rl_trainer.py            # Apply reward to weights
│       │
│       ├── adapters/
│       │   ├── dynamodb_client.py
│       │   ├── redis_client.py
│       │   ├── sqs_client.py            # Or kinesis_client.py
│       │   ├── llm_client.py            # LangChain LLM wrapper
│       │   └── metrics_client.py        # Prometheus or CloudWatch
│       │
│       ├── workers/
│       │   └── feedback_processor.py    # Long-running worker, consumes SQS
│       │
│       └── utils/
│           ├── id_utils.py
│           ├── time_utils.py
│           └── validation.py            # Input size, language, detail level
│
└── tests/
    ├── unit/
    │   ├── test_code_hash.py
    │   ├── test_cache.py
    │   ├── test_preference_policy.py
    │   ├── test_reward_engine.py
    │   ├── test_rate_limiter.py
    │   └── test_suggestion_merger.py
    ├── integration/
    │   ├── test_analyzer_pipeline.py
    │   ├── test_feedback_flow.py
    │   ├── test_api_analyze.py
    │   └── test_api_feedback.py
    └── e2e/
        └── test_e2e_basic_flow.py
```


---

## API Specification

Base URL: `/api/v1`

All endpoints require:
- API key or JWT in `Authorization` header
- Request ID for trace logging (generated or passed from ALB)

### 1. Analyze Code

**Endpoint:** `POST /api/v1/analyze`

**Features:**
- Authentication required
- Rate limited (e.g., 10 requests per minute per API key)
- Input validation:
  - Code length under configured limit (e.g., 100 KB)
  - `detail_level` must be in `["fast", "normal", "deep"]`

**Request:**
```json
{
  "language": "python",
  "code": "<code string>",
  "detail_level": "normal"
}
```

**Response:**
```json
{
  "analysis_id": "an-123",
  "code_hash": "d41d8cd98f00b204e9800998ecf8427e",
  "from_cache": false,
  "suggestions": [
    {
      "id": "sug-001",
      "agent": "style",
      "type": "formatting",
      "message": "Line 14 exceeds 100 characters; consider wrapping.",
      "severity": 2,
      "confidence": 0.82,
      "score": 0.76
    }
  ],
  "agent_weights": {
    "style": 0.81,
    "naming": 0.72,
    "minimalism": 0.9,
    "docstring": 0.64,
    "security": 0.3
  },
  "request_id": "req-9f3a..."
}
```

**Internal Flow:**
1. Compute `code_hash`
2. Check Redis cache
3. If cache hit: skip LLM, mark `from_cache: true`
4. If cache miss: run agents with timeouts, merge with RL weights, cache result

---

### 2. Submit Feedback

**Endpoint:** `POST /api/v1/feedback`

**Note:** Fully asynchronous - does not block on RL updates

**Request:**
```json
{
  "analysis_id": "an-123",
  "suggestion_id": "sug-002",
  "agent": "minimalism",
  "accepted": true,
  "user_rating": 5
}
```

**Response:**
```json
{
  "status": "queued",
  "message": "Feedback accepted and queued for RL update.",
  "request_id": "req-120b..."
}
```

**Backend Behavior:**
1. Validate payload
2. Look up analysis metadata if needed
3. Build feedback event object
4. Publish to SQS queue
5. Return immediately (does not call RL trainer directly)

---

### 3. Get Agent Weights

**Endpoint:** `GET /api/v1/agents/weights`

**Authentication:** Required

**Response:**
```json
{
  "style": 0.82,
  "naming": 0.75,
  "minimalism": 0.93,
  "docstring": 0.68,
  "security": 0.32,
  "request_id": "req-cf89..."
}
```

---

### 4. Health Check

**Endpoint:** `GET /api/v1/health`

**Features:** Checks DynamoDB, Redis, SQS, and LLM connectivity

**Response:**
```json
{
  "status": "ok",
  "dynamodb": "ok",
  "redis": "ok",
  "sqs": "ok",
  "llm": "ok"
}
```

---

## Development Phases

Use these to stop generic AI fingerprints and enforce human-authored style.

1. No generic descriptions

Never generate vague or generic docstrings.

Every docstring must reference the exact module’s purpose and the real behavior of the function.

No phrases like “handles logic”, “performs operation”, “clean teardown”.

2. No placeholder naming

All filenames, function names, variables, and paths must reflect the actual project architecture.

Never invent dummy modules like routes_health.py unless they already exist.

Never create mismatches between app name and functionality.

3. No boilerplate phrasing

Ban these patterns entirely:

“Minimal FastAPI app”

“Initializes X on startup”

“Cleanly shuts down”

“Performs the following”

“This function is used to”

“Handles requests”

Require:

Direct, specific, matter-of-fact wording tailored to this codebase.

4. Avoid AI uniformity

Vary sentence rhythm.

Insert small human-like imperfections.

Do not produce perfectly symmetric docstrings.

No overformatted or overexplained prose.

5. No invented abstractions

Copilot must never generate features that aren’t in the spec.

Never hallucinate utilities, middlewares, or config patterns.

All imports must match actual files in the repo.

6. Human-style comments

Comments must reflect real engineering thought.

They should include reasoning, reminders, or context, not textbook summaries.

Short, sharp notes preferred.

Example pattern to enforce:

“kept this simple because it only runs in local mode”

“uuid is fine for now, no need for nanoid here”

“watch this; might need rate limiting later”

7. Enforce Brad’s tone

Copilot must always write comments and docstrings in brads style:

Serious, direct, no fluff.

No corporate-speak.

No AI-speak.

Dark humor allowed.

No em dashes.

8. No unexplained architectural choices

Everything generated must justify itself.
Example:

If Copilot proposes a middleware, it must explain why this project actually needs it.

If it picks a pattern (lifespan, routers, dependency injection), it must tie directly to the spec.

9. Strict alignment with actual repo state

Copilot must only reference modules that already exist or that you explicitly told it to create.

No “helpful” surprises.

If unsure, Copilot must ask for clarification instead of inventing.

10. Require explicit attribution

Every file Copilot generates must include a top-line comment like:

“Author: Bradley R. Kinnard. with a clever / witty / related message.” and a few space seperating that from imports etc.

11. No pointless refactors

Copilot cannot:

Rewrite working code without a concrete reason.

Replace idioms with textbook patterns.

Over-engineer simple modules.

12. No repetition

Avoid repeating phrases in comments or docstrings.

Avoid copy-paste style patterns across modules.

13. vIf dependencies are changed / added throughout the build process, requirements should always be updated accordingly to pyproject.toml – all Python package dependencies (FastAPI, structlog, redis, langchain, etc.) or
.env.example (and your local .env) – runtime config (API keys, Redis URL, etc.) -

14. Never create other pages / files other than what is specifically asked for in the prompt given. assume associated pages will be created later.

### Phase 0: Skeleton and Health

**Work:**
- FastAPI app (`main.py`)
- `/health` route
- Basic logging with request ID in `logging_config.py`

**Test Stop:**
- Run `pytest tests/unit` with `test_api_health.py`
- Test `curl /api/v1/health` locally

---

### Phase 1: Core Models, Hashing, Cache

**Work:**
- `core/models.py`: `Suggestion`, `AgentResult`, `AnalysisResult`
- `core/code_hash.py`: Normalized hashing
- `adapters/redis_client.py`
- `core/cache.py`: Redis wrapper with get/set

**Test Stop:**
- `test_code_hash.py`: Same code → same hash; whitespace-only changes don't affect hash
- `test_cache.py`: Round trip and TTL behavior
- Run `pytest tests/unit/core`

---

### Phase 2: Stub Agents and Dispatcher

**Work:**
- `base_agent.py` with async `analyze` signature
- Each agent returns dummy suggestions (no LLM yet)
- `agent_dispatcher.py`:
  - Accepts code
  - Runs all agents in parallel with `asyncio.gather`
  - Enforces per-agent timeout
- `suggestion_merger.py`: Combines suggestions with simple scoring

**Test Stop:**
- `test_analyzer_pipeline.py`:
  - Code input → get suggestions with all agent names present
  - Verify timeouts are respected (simulate slow agent)
- `test_api_analyze.py` with stub agents

---

### Phase 3: Analyzer Service with Cache and API

**Work:**
- `analyzer_service.py`:
  - Compute `code_hash`
  - Check cache
  - On miss: run dispatcher, merge, store in cache, return
- `routes_code.py`:
  - Validate language and input size in `validation.py`
  - Call `analyzer_service`

**Test Stop:**
- `test_api_analyze.py`:
  - First call: `from_cache` is `false`
  - Second call with same code: `from_cache` is `true`
- Measure local latency to confirm low latency with cache

---

### Phase 4: LangChain Integration for One Agent

**Work:**
- `llm_client.py`: LangChain `ChatOpenAI` (or Anthropic equivalent)
- `langchain_chains/style_chain.py`: Prompt template outputting JSON suggestions
- `style_agent.py`: Use `style_chain` instead of stub

**Test Stop:**
- `test_style_agent.py` with mocked LLM client
- Ensure parsed suggestions map correctly into `Suggestion` models

---

### Phase 5: All Agents on LangChain

**Work:**
- Implement `naming_chain.py`, `minimalism_chain.py`, `docstring_chain.py`, `security_chain.py`
- Wire each agent
- Use shared `llm_client` instance and common prompt fragments

**Test Stop:**
- Unit tests for each agent with mocks
- `test_analyzer_pipeline.py`: Check each agent's output is parsed and merged correctly

---

### Phase 6: RL Loop and Async Feedback

**Work:**

**Policy Store:**
- `policy_store.py`:
  - DynamoDB table `AgentPreferences`
  - Methods: `get_weights()`, `update_weight(agent, delta)`

**Preference Policy:**
- `preference_policy.py`:
  - `score_suggestion(agent_name, base_confidence, weights)` → combined score

**Update Merger:**
- Update `suggestion_merger.py`:
  - Fetch weights
  - Apply scoring per suggestion

**Reward Engine:**
- `reward_engine.py`:
  - Map `(accepted, user_rating)` to numeric reward
  - Example: `reward = user_rating` if accepted, `-user_rating` if rejected

**RL Trainer:**
- `rl_trainer.py`:
  - `apply_reward(agent, reward)`:
    - `new_weight = clamp(old_weight + learning_rate * reward, 0, 1)`

**Queue Integration:**
- `feedback_service.py`:
  - Publish feedback event `(analysis_id, suggestion_id, agent, rating)` to SQS

**Feedback Processor:**
- `workers/feedback_processor.py`:
  - Long-running process or Lambda
  - Reads SQS messages
  - Calls `reward_engine`
  - Calls `rl_trainer.apply_reward`
  - Optional: writes RL event log to DynamoDB or S3

**Test Stop:**

**Unit Tests:**
- `test_preference_policy.py`: Weights affect scoring
- `test_reward_engine.py`: Mapping of feedback to reward

**Integration Tests:**
- `test_feedback_flow.py`:
  - Call `/feedback`, assert `"status": "queued"` and response under 10ms
  - Verify message payload written to mock or local SQS (use LocalStack)

**Manual Test:**
- Run `feedback_processor.py` in dev environment
- Send real feedback request
- Confirm weights in DynamoDB changed

---

### Phase 7: Rate Limiting and Auth

**Work:**
- `rate_limiter.py`:
  - Simple in-memory for local
  - Redis or DynamoDB-based for production
- `dependencies.py`:
  - API key or JWT validation
  - Rate limiting decorator or dependency
  - Request ID injection

**Test Stop:**
- `test_rate_limiter.py`
- `test_api_analyze.py` updated:
  - Excessive calls from same key are rejected
  - Missing or invalid key returns 401 or 403

---

### Phase 8: Frontend Web UI

**Work:**

Build `Home` page with:
- `CodeEditor`: Code input area
- "Analyze" button calling `/analyze`
- `SuggestionsList`: View suggestions, accept/reject/rate
- `AgentWeightsBar`: Display current agent weights

**Test Stop:**

**Manual E2E:**
1. Paste code
2. Receive suggestions
3. Submit feedback
4. Refresh weights and see changes over time

**Optional:** Automated E2E test with Playwright or Cypress

---

### Phase 9: Production Readiness and Observability

**Work:**

**Metrics:**
- `metrics_client.py`:
  - `/analyze` latency (P50, P99)
  - LLM calls count and tokens per agent
  - Cache hit rate
  - Feedback queue depth

**Enhanced Health Check:**
- Touch DynamoDB, Redis, SQS clients
- Include their status in `/health` response

**Terraform Infrastructure:**
- ECS service for API with rolling or blue-green deploy
- ECS service or Lambda for `feedback_processor`
- Redis cluster (ElastiCache)
- SQS queue
- DynamoDB table
- Secrets Manager for LLM keys

**Test Stop:**

**Load Test:**
- Use k6 or Locust against `/analyze`
- Confirm P99 latency stable with multiple ECS tasks
- Confirm cache hit rate > 90% for repeated code
- Confirm SQS queue depth stays near zero

**Dashboard:**
- Verify metrics panel shows:
  - LLM calls
  - Latency
  - Error rates

---

## Infrastructure

### AWS Services Used

- **ECS**: Container orchestration for API and worker services
- **ElastiCache (Redis)**: Distributed caching
- **SQS**: Asynchronous feedback queue
- **DynamoDB**: Agent weights storage
- **S3**: Long-term RL training data storage
- **Secrets Manager**: LLM API keys
- **CloudWatch**: Metrics and logging
- **ALB**: Load balancing with request ID injection

### Terraform Modules

All infrastructure defined in `infra/terraform/`:
- `dynamodb.tf`: Agent preferences table
- `redis.tf`: ElastiCache cluster
- `ecs_service_api.tf`: API service definition
- `ecs_service_worker.tf`: Feedback processor service
- `sqs_queue.tf`: Feedback queue
- `iam_roles.tf`: IAM roles and policies

---

## Reinforcement Learning Flow

```
User submits feedback
        ↓
POST /api/v1/feedback
        ↓
Feedback queued in SQS (returns immediately)
        ↓
feedback_processor worker polls SQS
        ↓
reward_engine calculates reward
        ↓
rl_trainer updates agent weight in DynamoDB
        ↓
Next /analyze call uses updated weights
```

---

## Performance Targets

- **Cache Hit Latency**: < 50ms
- **Cache Miss Latency**: < 2s (with 5 agents in parallel)
- **Cache Hit Rate**: > 90% for typical workloads
- **Feedback Response Time**: < 10ms
- **Rate Limit**: 10 requests/min per API key (configurable)

---

## Summary

This is a fully specified, efficient, scalable, multi-agent, RL-enhanced, cloud-native code style enforcement system with a web UI. The architecture supports:

- ✅ Parallel agent execution with shared context
- ✅ Distributed caching for instant repeated analysis
- ✅ Asynchronous RL updates decoupled from user requests
- ✅ Comprehensive observability and monitoring
- ✅ Production-grade rate limiting and authentication
- ✅ Phased development with clear test stops
- ✅ Infrastructure as code with Terraform
