"""Tests for ClaudeProvider retry logic and circuit_breaker_failures metric.

This module validates:
- Retry on APIStatusError and APIConnectionError
- Retry exhaustion reraises the last exception
- Non-retryable exceptions don't trigger retry
- circuit_breaker_failures metric increments when circuit opens
- circuit_breaker_state metric tracks state transitions
"""

from unittest.mock import AsyncMock, Mock, patch

import anthropic
import pytest
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock
from prometheus_client import REGISTRY

from src.agent.providers.claude import ClaudeProvider
from src.common.exceptions import ProviderError
from src.common.types import ProviderRequest


@pytest.fixture
def mock_client() -> Mock:
    """Fixture providing a mock AsyncAnthropic client."""
    return Mock(spec=AsyncAnthropic)


@pytest.fixture
def provider(mock_client: Mock) -> ClaudeProvider:
    """Fixture providing a ClaudeProvider with low fail_max for fast tests."""
    return ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)


@pytest.fixture
def request_obj() -> ProviderRequest:
    """Fixture providing a standard ProviderRequest."""
    return ProviderRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is Docker?",
        model_name="claude-3-5-sonnet-20241022",
    )


def _make_api_status_error(*args: object, **kwargs: object) -> anthropic.APIStatusError:
    """Create a minimal APIStatusError for testing."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.headers = {}
    mock_response.text = "Internal Server Error"
    return anthropic.APIStatusError(
        message="Internal Server Error",
        response=mock_response,
        body={"error": {"message": "Internal Server Error"}},
    )


def _make_api_connection_error(*args: object, **kwargs: object) -> anthropic.APIConnectionError:
    """Create a minimal APIConnectionError for testing."""
    return anthropic.APIConnectionError(request=Mock())


# ===== Retry on APIStatusError =====


@pytest.mark.asyncio
async def test_retry_on_api_status_error_succeeds_on_third_attempt(
    provider: ClaudeProvider, mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that generate() retries on APIStatusError and succeeds on 3rd attempt."""
    mock_text_block = TextBlock(text="Docker is a container platform.", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    mock_response.usage = Mock(input_tokens=10, output_tokens=5)

    call_count = 0

    async def side_effect(*args: object, **kwargs: object) -> Mock:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise _make_api_status_error()
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    result = await provider.generate(request_obj)

    assert result == ("Docker is a container platform.", 10, 5)
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_api_connection_error_succeeds_on_second_attempt(
    provider: ClaudeProvider, mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that generate() retries on APIConnectionError and succeeds on 2nd attempt."""
    mock_text_block = TextBlock(text="Success response", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    mock_response.usage = Mock(input_tokens=8, output_tokens=4)

    call_count = 0

    async def side_effect(*args: object, **kwargs: object) -> Mock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _make_api_connection_error()
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    result = await provider.generate(request_obj)

    assert result == ("Success response", 8, 4)
    assert call_count == 2


# ===== Retry Exhaustion =====


@pytest.mark.asyncio
async def test_retry_exhaustion_reraises_api_status_error(
    mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that after 3 APIStatusError failures, the exception is reraised."""
    # Use fail_max=10 to prevent circuit breaker from opening during retry
    provider = ClaudeProvider(client=mock_client, fail_max=10, reset_timeout=1)

    async def raise_status_error(*args: object, **kwargs: object) -> None:
        raise _make_api_status_error()

    mock_client.messages.create = AsyncMock(side_effect=raise_status_error)

    with pytest.raises(anthropic.APIStatusError):
        await provider.generate(request_obj)


@pytest.mark.asyncio
async def test_retry_exhaustion_reraises_api_connection_error(
    mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that after 3 APIConnectionError failures, the exception is reraised."""
    # Use fail_max=10 to prevent circuit breaker from opening during retry
    provider = ClaudeProvider(client=mock_client, fail_max=10, reset_timeout=1)

    async def raise_connection_error(*args: object, **kwargs: object) -> None:
        raise _make_api_connection_error()

    mock_client.messages.create = AsyncMock(side_effect=raise_connection_error)

    with pytest.raises(anthropic.APIConnectionError):
        await provider.generate(request_obj)


@pytest.mark.asyncio
async def test_retry_exhaustion_calls_api_exactly_three_times(
    mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that retry logic calls the API exactly 3 times before giving up."""
    # Use fail_max=10 to prevent circuit breaker from opening during retry
    provider = ClaudeProvider(client=mock_client, fail_max=10, reset_timeout=1)

    call_count = 0

    async def side_effect(*args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        raise _make_api_status_error()

    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    with pytest.raises(anthropic.APIStatusError):
        await provider.generate(request_obj)

    assert call_count == 3


# ===== Non-Retryable Exceptions =====


@pytest.mark.asyncio
async def test_non_retryable_exception_does_not_retry(
    provider: ClaudeProvider, mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that generic exceptions are not retried - only called once."""
    call_count = 0

    async def side_effect(*args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError("Unexpected error")

    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    with pytest.raises(ProviderError):
        await provider.generate(request_obj)

    # Should only be called once - no retry for non-retryable exceptions
    assert call_count == 1


@pytest.mark.asyncio
async def test_provider_error_does_not_retry(
    provider: ClaudeProvider, mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that ProviderError is not retried."""
    call_count = 0

    async def side_effect(*args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        raise ProviderError("Provider-level error")

    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    with pytest.raises(ProviderError):
        await provider.generate(request_obj)

    assert call_count == 1


# ===== circuit_breaker_failures Metric =====


@pytest.mark.asyncio
async def test_circuit_breaker_failures_metric_increments_when_circuit_opens(
    mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that circuit_breaker_failures counter increments when circuit breaker opens."""
    from src.common.metrics import circuit_breaker_failures

    # Get baseline count before test
    baseline = _get_counter_value(circuit_breaker_failures)

    # Use fail_max=3 so circuit opens after 3 failures
    provider = ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)

    async def raise_error(*args: object, **kwargs: object) -> None:
        raise Exception("Simulated API failure")

    mock_client.messages.create = AsyncMock(side_effect=raise_error)

    # Exhaust the circuit breaker (3 failures to open it)
    for _ in range(3):
        with pytest.raises(ProviderError):
            await provider.generate(request_obj)

    # Next call should trigger CircuitBreakerError and increment the metric
    with pytest.raises(ProviderError, match="Circuit breaker open"):
        await provider.generate(request_obj)

    current = _get_counter_value(circuit_breaker_failures)
    assert current > baseline, "circuit_breaker_failures should have incremented"


@pytest.mark.asyncio
async def test_circuit_breaker_state_metric_increments_on_open(
    mock_client: Mock, request_obj: ProviderRequest
) -> None:
    """Test that circuit_breaker_state metric tracks open state transitions."""
    from src.common.metrics import circuit_breaker_state

    baseline = _get_labeled_counter_value(circuit_breaker_state, {"state": "open"})

    provider = ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)

    async def raise_error(*args: object, **kwargs: object) -> None:
        raise Exception("Simulated API failure")

    mock_client.messages.create = AsyncMock(side_effect=raise_error)

    # Exhaust the circuit breaker
    for _ in range(3):
        with pytest.raises(ProviderError):
            await provider.generate(request_obj)

    # Trigger the open circuit
    with pytest.raises(ProviderError, match="Circuit breaker open"):
        await provider.generate(request_obj)

    current = _get_labeled_counter_value(circuit_breaker_state, {"state": "open"})
    assert current > baseline, "circuit_breaker_state{state='open'} should have incremented"


def test_circuit_breaker_metrics_registered_in_prometheus() -> None:
    """Test that circuit breaker metrics are registered in Prometheus registry."""
    metric_names = {collector.name for collector in REGISTRY.collect()}

    assert any(
        name in metric_names
        for name in ("agent_circuit_breaker_failures", "agent_circuit_breaker_failures_total")
    ), "circuit_breaker_failures metric not found in registry"

    assert any(
        name in metric_names
        for name in ("agent_circuit_breaker_state_changes", "agent_circuit_breaker_state_changes_total")
    ), "circuit_breaker_state metric not found in registry"


# ===== Helpers =====


def _get_counter_value(counter: object) -> float:
    """Get the current total value of a Counter metric."""
    for family in REGISTRY.collect():
        if family.name in (counter._name, counter._name + "_total"):  # type: ignore[attr-defined]
            for sample in family.samples:
                if sample.name.endswith("_total") or sample.name == family.name:
                    return sample.value
    return 0.0


def _get_labeled_counter_value(counter: object, labels: dict[str, str]) -> float:
    """Get the current value of a labeled Counter metric for specific label values."""
    for family in REGISTRY.collect():
        if family.name in (counter._name, counter._name + "_total"):  # type: ignore[attr-defined]
            for sample in family.samples:
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0.0
