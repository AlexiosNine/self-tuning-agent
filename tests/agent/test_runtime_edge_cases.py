"""Edge case tests for AgentRuntime: Unicode, whitespace, provider errors, boundary conditions."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.agent.runtime import MAX_QUESTION_LENGTH, AgentRuntime
from src.common.exceptions import FileOperationError, VersionNotFoundError
from src.harness.version_manager import VersionManager


def _setup_runtime(tmp_path: Path, provider: AsyncMock | None = None) -> AgentRuntime:
    """Helper: create a VersionManager with one production version and return a runtime."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    if provider is None:
        provider = AsyncMock()
        provider.generate.return_value = ("Answer", 10, 5)

    return AgentRuntime(manager, provider, "test-model")


# --- Unicode / special characters ---


@pytest.mark.asyncio
async def test_answer_with_unicode_question(tmp_path: Path) -> None:
    """Unicode characters in questions are handled correctly."""
    runtime = _setup_runtime(tmp_path)
    result = await runtime.answer("What is 日本語?")
    assert result.answer == "Answer"


@pytest.mark.asyncio
async def test_answer_with_emoji_question(tmp_path: Path) -> None:
    """Emoji in questions are handled correctly."""
    runtime = _setup_runtime(tmp_path)
    result = await runtime.answer("What does 🐍 mean?")
    assert result.answer == "Answer"


# --- Whitespace handling ---


@pytest.mark.asyncio
async def test_answer_strips_whitespace(tmp_path: Path) -> None:
    """Leading/trailing whitespace and internal newlines are stripped."""
    provider = AsyncMock()
    provider.generate.return_value = ("Answer", 10, 5)
    runtime = _setup_runtime(tmp_path, provider)

    result = await runtime.answer("  What is\n\tDocker?  ")
    assert result.answer == "Answer"

    # Verify the stripped question was sent to provider
    call_args = provider.generate.call_args[0][0]
    assert call_args.user_prompt == "What is\n\tDocker?"


@pytest.mark.asyncio
async def test_answer_none_question(tmp_path: Path) -> None:
    """None question raises ValueError (via falsy check)."""
    runtime = _setup_runtime(tmp_path)
    with pytest.raises((ValueError, TypeError)):
        await runtime.answer(None)  # type: ignore[arg-type]


# --- Boundary conditions ---


@pytest.mark.asyncio
async def test_answer_exactly_at_max_length(tmp_path: Path) -> None:
    """Question at exactly MAX_QUESTION_LENGTH succeeds."""
    runtime = _setup_runtime(tmp_path)
    question = "x" * MAX_QUESTION_LENGTH
    result = await runtime.answer(question)
    assert result.answer == "Answer"


@pytest.mark.asyncio
async def test_answer_one_over_max_length(tmp_path: Path) -> None:
    """Question one char over MAX_QUESTION_LENGTH is rejected."""
    runtime = _setup_runtime(tmp_path)
    with pytest.raises(ValueError, match="exceeds"):
        await runtime.answer("x" * (MAX_QUESTION_LENGTH + 1))


@pytest.mark.asyncio
async def test_answer_single_char_question(tmp_path: Path) -> None:
    """Single character question is valid."""
    runtime = _setup_runtime(tmp_path)
    result = await runtime.answer("?")
    assert result.answer == "Answer"


# --- Provider errors ---


@pytest.mark.asyncio
async def test_answer_provider_raises_exception(tmp_path: Path) -> None:
    """Provider exception propagates to caller."""
    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError("API timeout")
    runtime = _setup_runtime(tmp_path, provider)

    with pytest.raises(RuntimeError, match="API timeout"):
        await runtime.answer("What is Docker?")


@pytest.mark.asyncio
async def test_answer_provider_returns_empty_string(tmp_path: Path) -> None:
    """Provider returning empty string is still a valid AnswerResult."""
    provider = AsyncMock()
    provider.generate.return_value = ("", 10, 5)
    runtime = _setup_runtime(tmp_path, provider)

    result = await runtime.answer("What is Docker?")
    assert result.answer == ""


@pytest.mark.asyncio
async def test_answer_provider_returns_very_long_response(tmp_path: Path) -> None:
    """Very long provider response is accepted."""
    provider = AsyncMock()
    provider.generate.return_value = ("x" * 100_000, 10, 5)
    runtime = _setup_runtime(tmp_path, provider)

    result = await runtime.answer("What is Docker?")
    assert len(result.answer) == 100_000


# --- Broken production symlink ---


@pytest.mark.asyncio
async def test_answer_broken_current_symlink(tmp_path: Path) -> None:
    """Broken current symlink raises VersionNotFoundError or FileOperationError."""
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    manager = VersionManager(strategies_dir)

    current_link = strategies_dir / "current"
    current_link.symlink_to(strategies_dir / "deleted_version")

    provider = AsyncMock()
    runtime = AgentRuntime(manager, provider, "test-model")

    with pytest.raises((VersionNotFoundError, FileOperationError)):
        await runtime.answer("What is Docker?")
