from src.common.types import EvaluationRecord, Evaluator
from src.evaluation.classifiers.task_classifier import TaskClassifier


class EvaluationEngine:
    def __init__(self, evaluator: Evaluator) -> None:
        self.evaluator = evaluator
        self.classifier = TaskClassifier()

    def evaluate(self, question: str, answer: str) -> EvaluationRecord:
        question_type = self.classifier.classify(question)
        score_result = self.evaluator.evaluate(question, answer, question_type)
        return EvaluationRecord(
            question=question,
            answer=answer,
            question_type=question_type,
            auto_score=score_result.score,
        )
