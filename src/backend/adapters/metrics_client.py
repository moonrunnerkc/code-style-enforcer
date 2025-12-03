# Author: Bradley R. Kinnard — counting everything

"""Prometheus metrics. Import and use from anywhere."""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest

# latency for the full analyze pipeline
analyze_latency = Histogram(
    "analyze_latency_seconds",
    "Time spent in /analyze endpoint",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# cache hits vs misses
cache_hit_total = Counter(
    "cache_hit_total",
    "Cache hits on code analysis"
)
cache_miss_total = Counter(
    "cache_miss_total",
    "Cache misses on code analysis"
)

# LLM token usage by agent
llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM tokens consumed",
    ["agent"]  # style, naming, etc
)

# feedback events
feedback_queued_total = Counter(
    "feedback_queued_total",
    "Feedback events queued to SQS"
)
feedback_processed_total = Counter(
    "feedback_processed_total",
    "Feedback events processed by worker"
)

# rate limit hits
rate_limit_hit_total = Counter(
    "rate_limit_hit_total",
    "Requests rejected by rate limiter"
)

# agent errors
agent_error_total = Counter(
    "agent_error_total",
    "Agent failures",
    ["agent"]
)

# current RL weights as gauges so you can graph them
agent_weight = Gauge(
    "agent_weight",
    "Current RL weight per agent",
    ["agent"]
)


def get_metrics() -> bytes:
    """dump all metrics in prometheus format"""
    return generate_latest(REGISTRY)
