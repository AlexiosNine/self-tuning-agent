from src.common.types import QuestionType


class TaskClassifier:
    def classify(self, question: str) -> QuestionType:
        lowered = question.lower()
        if lowered.startswith(("what", "who", "when")):
            return QuestionType.FACTUAL
        if lowered.startswith(("why", "how")):
            return QuestionType.REASONING
        return QuestionType.CREATIVE
