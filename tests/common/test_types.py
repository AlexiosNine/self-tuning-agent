from src.common.types import EvaluationRecord, QuestionType, StrategyStatus, StrategyVersion


def test_strategy_version_and_evaluation_record_validate() -> None:
    version = StrategyVersion(
        version_id="v001",
        status=StrategyStatus.DRAFT,
        parent_version=None,
    )
    record = EvaluationRecord(
        question="What is Docker?",
        answer="A container platform.",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9,
    )

    assert version.version_id == "v001"
    assert version.status is StrategyStatus.DRAFT
    assert record.question_type is QuestionType.FACTUAL
    assert record.auto_score == 0.9
