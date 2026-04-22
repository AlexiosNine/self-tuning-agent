from pathlib import Path

from src.common.types import EvaluationRecord, QuestionType
from src.harness.orchestrator import HarnessOrchestrator
from src.harness.version_manager import VersionManager


def test_orchestrator_creates_draft_version_when_scores_drop(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3),
    ]

    created_version = orchestrator.maybe_optimize(records)

    assert created_version == "v002"
    assert (strategies_dir / "v002" / "prompt.yaml").exists()
    assert manager.load_version("v002").parent_version == "v001"
