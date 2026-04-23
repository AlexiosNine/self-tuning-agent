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
        EvaluationRecord(
            question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3
        ),
    ]

    created_version = orchestrator.maybe_optimize(records)

    assert created_version == "v002"
    assert (strategies_dir / "v002" / "prompt.yaml").exists()
    assert manager.load_version("v002").parent_version == "v001"


def test_orchestrator_handles_missing_current_symlink(tmp_path: Path) -> None:
    """Test that maybe_optimize() raises clear error when current symlink doesn't exist."""
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    manager = VersionManager(strategies_dir)

    # Create v001 but don't promote it (no current symlink)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(
            question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3
        ),
    ]

    # Should raise ValueError when trying to parse "current" as version number
    try:
        orchestrator.maybe_optimize(records)
        assert False, "Expected ValueError"
    except ValueError as e:
        # Verify error message mentions the problematic value
        assert "current" in str(e).lower() or "invalid literal" in str(e).lower()


def test_orchestrator_handles_non_standard_version_names(tmp_path: Path) -> None:
    """Test version parsing with non-standard names like v001-hotfix."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)

    # Create version with non-standard name
    manager.create_version("v001-hotfix", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001-hotfix")

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(
            question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3
        ),
    ]

    # Should raise ValueError when trying to parse version number
    try:
        orchestrator.maybe_optimize(records)
        assert False, "Expected ValueError for non-standard version name"
    except ValueError as e:
        # Verify error message mentions the problematic version name
        assert "v001-hotfix" in str(e) or "invalid literal" in str(e).lower()


def test_orchestrator_handles_four_digit_version_numbers(tmp_path: Path) -> None:
    """Test version parsing with 4-digit version numbers (v1000+)."""
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)

    # Create version v999 and promote it
    manager.create_version("v999", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v999")

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(
            question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3
        ),
    ]

    created_version = orchestrator.maybe_optimize(records)

    # Should create v1000 (4-digit version)
    # Note: Current implementation uses :03d format, so this will create "1000" not "v1000"
    assert created_version == "v1000"
    assert (strategies_dir / "v1000" / "prompt.yaml").exists()


def test_orchestrator_error_message_clarity_for_missing_symlink(tmp_path: Path) -> None:
    """Test that error message for missing current symlink is clear and actionable."""
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    manager = VersionManager(strategies_dir)

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(
            question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3
        ),
    ]

    try:
        orchestrator.maybe_optimize(records)
        assert False, "Expected exception"
    except Exception as e:
        error_msg = str(e).lower()
        # Error should mention the missing file/symlink
        assert any(
            keyword in error_msg for keyword in ["current", "symlink", "no such file", "not found"]
        ), f"Error message not clear: {e}"

