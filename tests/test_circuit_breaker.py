from unittest.mock import Mock

import pybreaker
import pytest
from anthropic import Anthropic
from anthropic.types import TextBlock

from src.agent.providers.claude import ClaudeProvider
from src.common.exceptions import ProviderError
from src.common.types import ProviderRequest


@pytest.fixture
def mock_client() -> Mock:
    return Mock(spec=Anthropic)


@pytest.fixture
def provider(mock_client: Mock) -> ClaudeProvider:
    return ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)


def test_circuit_breaker_opens_after_failures(provider: ClaudeProvider, mock_client: Mock) -> None:
    """Test that circuit breaker opens after consecutive failures."""
    mock_client.messages.create.side_effect = Exception("API error")

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    # First 3 failures should raise ProviderError
    for _ in range(3):
        with pytest.raises(ProviderError):
            provider.generate(request)

    # 4th call should raise CircuitBreakerError wrapped in ProviderError
    with pytest.raises(ProviderError, match="Circuit breaker open"):
        provider.generate(request)


def test_circuit_breaker_allows_success(provider: ClaudeProvider, mock_client: Mock) -> None:
    """Test that circuit breaker allows successful calls."""
    mock_text_block = TextBlock(text="Test answer", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    result = provider.generate(request)
    assert result == "Test answer"
    assert provider._breaker.current_state == pybreaker.STATE_CLOSED


def test_circuit_breaker_custom_config() -> None:
    """Test circuit breaker with custom configuration."""
    mock_client = Mock(spec=Anthropic)
    provider = ClaudeProvider(client=mock_client, fail_max=5, reset_timeout=30)

    assert provider._breaker.fail_max == 5
    assert provider._breaker.reset_timeout == 30
