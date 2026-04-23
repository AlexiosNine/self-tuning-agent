from prometheus_client import Counter, Histogram

# Request counters
answer_requests_total = Counter(
    "agent_answer_requests_total",
    "Total number of answer requests",
    ["strategy_version", "model_name"],
)

answer_requests_failed = Counter(
    "agent_answer_requests_failed",
    "Total number of failed answer requests",
    ["strategy_version", "model_name", "error_type"],
)

# Latency histograms
answer_latency_seconds = Histogram(
    "agent_answer_latency_seconds",
    "Answer request latency in seconds",
    ["strategy_version", "model_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

provider_call_latency_seconds = Histogram(
    "agent_provider_call_latency_seconds",
    "Provider API call latency in seconds",
    ["model_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# Circuit breaker metrics
circuit_breaker_state = Counter(
    "agent_circuit_breaker_state_changes",
    "Circuit breaker state changes",
    ["state"],
)

circuit_breaker_failures = Counter(
    "agent_circuit_breaker_failures_total",
    "Total circuit breaker failures",
)
