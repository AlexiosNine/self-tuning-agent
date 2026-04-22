from src.common.types import QuestionType
from src.evaluation.engine import EvaluationEngine
from src.evaluation.evaluators.auto import AutoEvaluator


def test_engine_classifies_factual_question_and_scores_keywords() -> None:
    engine = EvaluationEngine(evaluator=AutoEvaluator())

    result = engine.evaluate(
        question="What is Docker?",
        answer="Docker is a container platform used to package applications.",
    )

    assert result.question_type is QuestionType.FACTUAL
    assert result.auto_score == 1.0
