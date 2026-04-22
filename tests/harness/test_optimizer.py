from pathlib import Path

from src.common.types import EvaluationRecord, QuestionType
from src.harness.optimizer import MutationType, StrategyOptimizer, select_mutation_type
from src.harness.version_manager import VersionManager


def test_select_mutation_factual_failures():
    records = [
        EvaluationRecord(question="What is X?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(question="What is Y?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3),
    ]
    assert select_mutation_type(records) == MutationType.ADD_DEFINITION


def test_select_mutation_reasoning_failures():
    records = [
        EvaluationRecord(question="Why does X?", answer="bad", question_type=QuestionType.REASONING, auto_score=0.3),
        EvaluationRecord(question="How does Y?", answer="bad", question_type=QuestionType.REASONING, auto_score=0.2),
    ]
    assert select_mutation_type(records) == MutationType.ADD_REASONING


def test_select_mutation_creative_failures():
    records = [
        EvaluationRecord(question="Write a poem", answer="bad", question_type=QuestionType.CREATIVE, auto_score=0.2),
    ]
    assert select_mutation_type(records) == MutationType.ADD_EXAMPLE


def test_select_mutation_no_failures():
    records = [
        EvaluationRecord(question="What is X?", answer="good", question_type=QuestionType.FACTUAL, auto_score=0.9),
    ]
    assert select_mutation_type(records) == MutationType.SIMPLIFY


def test_optimizer_creates_version_with_guidance(tmp_path: Path):
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    optimizer = StrategyOptimizer(manager)
    records = [
        EvaluationRecord(question="What is X?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
    ]

    version = optimizer.create_mutation("v001", "v002", records)

    assert version == "v002"
    config = manager.load_prompt_config("v002")
    assert "definitions" in config["system_prompt"].lower()


def test_optimizer_without_records_uses_simplify(tmp_path: Path):
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})

    optimizer = StrategyOptimizer(manager)
    optimizer.create_mutation("v001", "v002")

    config = manager.load_prompt_config("v002")
    assert "simple" in config["system_prompt"].lower()
