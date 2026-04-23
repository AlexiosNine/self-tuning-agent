from pathlib import Path

import pytest

from src.agent.runtime import AgentRuntime
from src.common.exceptions import VersionNotFoundError
from src.common.types import ProviderRequest
from src.harness.version_manager import VersionManager


class FakeProvider:
    def __init__(self) -> None:
        self.last_request: ProviderRequest | None = None

    async def generate(self, request: ProviderRequest) -> tuple[str, int, int]:
        self.last_request = request
        return ("Docker is a container platform.", 10, 5)


@pytest.mark.asyncio
async def test_runtime_uses_current_strategy_prompt(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    provider = FakeProvider()
    runtime = AgentRuntime(version_manager=manager, provider=provider, model_name="claude-sonnet-4-6")

    result = await runtime.answer("What is Docker?")

    assert result.answer == "Docker is a container platform."
    assert result.strategy_version == "v001"
    assert provider.last_request is not None
    assert provider.last_request.system_prompt == "Answer clearly."


@pytest.mark.asyncio
async def test_answer_empty_question(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    runtime = AgentRuntime(version_manager=manager, provider=FakeProvider(), model_name="test")

    with pytest.raises(ValueError, match="cannot be empty"):
        await runtime.answer("")


@pytest.mark.asyncio
async def test_answer_whitespace_only_question(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    runtime = AgentRuntime(version_manager=manager, provider=FakeProvider(), model_name="test")

    with pytest.raises(ValueError, match="cannot be empty"):
        await runtime.answer("   ")


@pytest.mark.asyncio
async def test_answer_too_long_question(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Test"})
    manager.promote_to_production("v001")

    runtime = AgentRuntime(version_manager=manager, provider=FakeProvider(), model_name="test")

    with pytest.raises(ValueError, match="exceeds"):
        await runtime.answer("x" * 10001)


@pytest.mark.asyncio
async def test_answer_no_production_version(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()

    runtime = AgentRuntime(version_manager=VersionManager(strategies_dir), provider=FakeProvider(), model_name="test")

    with pytest.raises(VersionNotFoundError, match="No production"):
        await runtime.answer("What is Docker?")
