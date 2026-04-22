"""Shared test fixtures for the self-tuning QA agent test suite."""

from pathlib import Path

import pytest
import yaml

from src.agent.runtime import AgentRuntime
from src.common.types import ProviderRequest
from src.dataset.builder import DatasetBuilder
from src.evaluation.engine import EvaluationEngine
from src.evaluation.evaluators.auto import AutoEvaluator
from src.harness.orchestrator import HarnessOrchestrator
from src.harness.version_manager import VersionManager


class FakeProvider:
    """Deterministic provider that returns a canned answer containing target keywords."""

    def __init__(self, answer: str = "Docker is a container platform used to package applications.") -> None:
        self.answer = answer
        self.last_request: ProviderRequest | None = None

    def generate(self, request: ProviderRequest) -> str:
        self.last_request = request
        return self.answer


@pytest.fixture()
def strategies_dir(tmp_path: Path) -> Path:
    """Create a strategies directory with a v001 version promoted to production."""
    strategies = tmp_path / "strategies"
    manager = VersionManager(strategies)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly and concisely."})
    manager.promote_to_production("v001")
    return strategies


@pytest.fixture()
def version_manager(strategies_dir: Path) -> VersionManager:
    return VersionManager(strategies_dir)


@pytest.fixture()
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture()
def agent_runtime(version_manager: VersionManager, fake_provider: FakeProvider) -> AgentRuntime:
    return AgentRuntime(version_manager=version_manager, provider=fake_provider, model_name="test-model")


@pytest.fixture()
def evaluation_engine() -> EvaluationEngine:
    return EvaluationEngine(evaluator=AutoEvaluator())


@pytest.fixture()
def harness_orchestrator(version_manager: VersionManager) -> HarnessOrchestrator:
    return HarnessOrchestrator(version_manager=version_manager, min_samples=1)


@pytest.fixture()
def dataset_builder(tmp_path: Path) -> DatasetBuilder:
    return DatasetBuilder(output_dir=tmp_path / "dataset_output")
