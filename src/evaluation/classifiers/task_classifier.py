from src.common.types import QuestionType


class TaskClassifier:
    def classify(self, question: str) -> QuestionType:
        lowered = question.lower()
        if lowered.startswith("what") or lowered.startswith("who") or lowered.startswith("when"):
            return QuestionType.FACTUAL
        if lowered.startswith("why") or lowered.startswith("how"):
            return QuestionType.REASONING
        return QuestionType.CREATIVE
