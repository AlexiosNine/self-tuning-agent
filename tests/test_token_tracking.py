"""Tests for token usage tracking metrics."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.agent.providers.claude import ClaudeProvider
from src.agent.runtime import AgentRuntime
from src.common.metrics import tokens_input_total, tokens_output_total
from src.common.types import ProviderRequest
from src.harness.version_manager import VersionManager


@pytest.mark.asyncio
async def test_token_metrics_recorded_on_success(tmp_path: Path) -> None:
    """Test that token metrics are recorded when provider succeeds."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    provider = AsyncMock()
    provider.generate.return_value = ("Answer", 100, 50)

    runtime = AgentRuntime(manager, provider, "test-model")

    # Get initial metric values
    initial_input = tokens_input_total.labels(strategy_version="v001", model_name="test-model")._value.get()
    initial_output = tokens_output_total.labels(strategy_version="v001", model_name="test-model")._value.get()

    await runtime.answer("What is Docker?")

    # Verify metrics increased
    final_input = tokens_input_total.labels(strategy_version="v001", model_name="test-model")._value.get()
    final_output = tokens_output_total.labels(strategy_version="v001", model_name="test-model")._value.get()

    assert final_input == initial_input + 100
    assert final_output == initial_output + 50


@pytest.mark.asyncio
async def test_token_metrics_not_recorded_on_error(tmp_path: Path) -> None:
    """Test that token metrics are not recorded when provider fails."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError("API error")

    runtime = AgentRuntime(manager, provider, "test-model")

    # Get initial metric values
    initial_input = tokens_input_total.labels(strategy_version="v001", model_name="test-model")._value.get()
    initial_output = tokens_output_total.labels(strategy_version="v001", model_name="test-model")._value.get()

    with pytest.raises(RuntimeError):
        await runtime.answer("What is Docker?")

    # Verify metrics did not change
    final_input = tokens_input_total.labels(strategy_version="v001", model_name="test-model")._value.get()
    final_output = tokens_output_total.labels(strategy_version="v001", model_name="test-model")._value.get()

    assert final_input == initial_input
    assert final_output == initial_output


@pytest.mark.asyncio
async def test_token_metrics_correct_labels(tmp_path: Path) -> None:
    """Test that token metrics use correct labels (strategy_version, model_name)."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v002", None, {"system_prompt": "Test"})
    manager.promote_to_production("v002")

    provider = AsyncMock()
    provider.generate.return_value = ("Answer", 200, 100)

    runtime = AgentRuntime(manager, provider, "claude-sonnet-4-6")

    # Get initial metric values for v002 and claude-sonnet-4-6
    initial_input = tokens_input_total.labels(strategy_version="v002", model_name="claude-sonnet-4-6")._value.get()
    initial_output = tokens_output_total.labels(strategy_version="v002", model_name="claude-sonnet-4-6")._value.get()

    await runtime.answer("What is Docker?")

    # Verify metrics increased with correct labels
    final_input = tokens_input_total.labels(strategy_version="v002", model_name="claude-sonnet-4-6")._value.get()
    final_output = tokens_output_total.labels(strategy_version="v002", model_name="claude-sonnet-4-6")._value.get()

    assert final_input == initial_input + 200
    assert final_output == initial_output + 100


@pytest.mark.asyncio
async def test_token_extraction_from_claude_response() -> None:
    """Test that ClaudeProvider correctly extracts token usage from response."""
    mock_client = Mock(spec=AsyncAnthropic)
    provider = ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)

    mock_text_block = TextBlock(text="Test answer", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    mock_response.usage = Mock(input_tokens=150, output_tokens=75)

    # Create an async mock that returns the response
    async def return_response(*args: object, **kwargs: object) -> Mock:
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=return_response)

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    text, input_tokens, output_tokens = await provider.generate(request)

    assert text == "Test answer"
    assert input_tokens == 150
    assert output_tokens == 75


@pytest.mark.asyncio
async def test_token_extraction_handles_missing_usage() -> None:
    """Test that ClaudeProvider handles responses without usage field."""
    mock_client = Mock(spec=AsyncAnthropic)
    provider = ClaudeProvider(client=mock_client, fail_max=3, reset_timeout=1)

    mock_text_block = TextBlock(text="Test answer", type="text")
    mock_response = Mock()
    mock_response.content = [mock_text_block]
    # No usage field
    del mock_response.usage

    # Create an async mock that returns the response
    async def return_response(*args: object, **kwargs: object) -> Mock:
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=return_response)

    request = ProviderRequest(
        system_prompt="Test system",
        user_prompt="Test question",
        model_name="claude-3-5-sonnet-20241022",
    )

    text, input_tokens, output_tokens = await provider.generate(request)

    assert text == "Test answer"
    assert input_tokens == 0
    assert output_tokens == 0
