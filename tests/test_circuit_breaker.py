from unittest.mock import AsyncMock, Mock

import pytest
from aiobreaker import CircuitBreakerState
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.agent.providers.claude import ClaudeProvider
from src.common.exceptions import ProviderError
from src.common.types import ProviderRequest


@pytest.fixture
def mock_client() -> Mock:
    return Mock(spec=AsyncAnthropic)


@pytest.fixture
def provider(mock_client: Mock) -> ClaudeProvider:
    return ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(provider: ClaudeProvider, mock_client: Mock) -> None:
    """Test that circuit breaker opens after consecutive failures."""

    # Create an async mock that raises an exception
    async def raise_error(*args: object, **kwargs: object) -> None:
        raise Exception("API error")

    mock_client.messages.create = AsyncMock(side_effect=raise_error)

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    # First 3 failures should raise ProviderError
    for _ in range(3):
        with pytest.raises(ProviderError):
            await provider.generate(request)

    # 4th call should raise CircuitBreakerError wrapped in ProviderError
    with pytest.raises(ProviderError, match="Circuit breaker open"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_circuit_breaker_allows_success(provider: ClaudeProvider, mock_client: Mock) -> None:
    """Test that circuit breaker allows successful calls."""
    mock_text_block = TextBlock(text="Test answer", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    mock_response.usage = Mock(input_tokens=10, output_tokens=5)

    # Create an async mock that returns the response
    async def return_response(*args: object, **kwargs: object) -> Mock:
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=return_response)

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    result = await provider.generate(request)
    assert result == ("Test answer", 10, 5)
    assert provider._breaker.current_state == CircuitBreakerState.CLOSED


def test_circuit_breaker_custom_config() -> None:
    """Test circuit breaker with custom configuration."""
    from datetime import timedelta

    mock_client = Mock(spec=AsyncAnthropic)
    provider = ClaudeProvider(client=mock_client, fail_max=5, reset_timeout=30)

    assert provider._breaker.fail_max == 5
    assert provider._breaker.timeout_duration == timedelta(seconds=30)
