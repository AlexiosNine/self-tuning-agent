import pytest
from prometheus_client import REGISTRY

from src.common.metrics import (
    answer_latency_seconds,
    answer_requests_failed,
    answer_requests_total,
)


def test_metrics_registered() -> None:
    """Test that all metrics are registered with Prometheus."""
    metric_names = [collector.name for collector in REGISTRY.collect()]

    # Note: Counter metrics have "_total" suffix in the registry
    assert "agent_answer_requests" in metric_names or "agent_answer_requests_total" in metric_names
    assert "agent_answer_requests_failed" in metric_names or "agent_answer_requests_failed_total" in metric_names
    assert "agent_answer_latency_seconds" in metric_names
    assert "agent_provider_call_latency_seconds" in metric_names
    assert (
        "agent_circuit_breaker_state_changes" in metric_names
        or "agent_circuit_breaker_state_changes_total" in metric_names
    )
    assert "agent_circuit_breaker_failures" in metric_names or "agent_circuit_breaker_failures_total" in metric_names


def test_answer_requests_total_labels() -> None:
    """Test that answer_requests_total has correct labels."""
    answer_requests_total.labels(strategy_version="v1", model_name="claude-3-5-sonnet-20241022").inc()

    for family in REGISTRY.collect():
        # Counter metrics may appear as "name" or "name_total"
        if family.name in ("agent_answer_requests_total", "agent_answer_requests"):
            for sample in family.samples:
                if sample.labels.get("strategy_version") == "v1":
                    assert sample.labels["model_name"] == "claude-3-5-sonnet-20241022"
                    assert sample.value >= 1.0
                    return

    pytest.fail("Metric not found")


def test_answer_requests_failed_labels() -> None:
    """Test that answer_requests_failed has correct labels."""
    answer_requests_failed.labels(
        strategy_version="v1", model_name="claude-3-5-sonnet-20241022", error_type="provider_error"
    ).inc()

    for family in REGISTRY.collect():
        if family.name == "agent_answer_requests_failed":
            for sample in family.samples:
                if sample.labels.get("error_type") == "provider_error":
                    assert sample.labels["strategy_version"] == "v1"
                    assert sample.labels["model_name"] == "claude-3-5-sonnet-20241022"
                    return

    pytest.fail("Metric not found")


def test_latency_histogram_buckets() -> None:
    """Test that latency histograms have correct buckets."""
    answer_latency_seconds.labels(strategy_version="v1", model_name="claude-3-5-sonnet-20241022").observe(1.5)

    for family in REGISTRY.collect():
        if family.name == "agent_answer_latency_seconds":
            # Check that buckets exist
            bucket_samples = [s for s in family.samples if s.name.endswith("_bucket")]
            assert len(bucket_samples) > 0
            return

    pytest.fail("Histogram not found")
