from src.common.types import QuestionType, ScoreResult


class AutoEvaluator:
    def evaluate(self, question: str, answer: str, question_type: QuestionType) -> ScoreResult:  # noqa: ARG002
        lowered_answer = answer.lower()
        if question_type is QuestionType.FACTUAL:
            keywords = ("docker", "container")
            score = 1.0 if all(keyword in lowered_answer for keyword in keywords) else 0.3
            return ScoreResult(score=score, reason="keyword match")
        if question_type is QuestionType.REASONING:
            score = 0.8 if "because" in lowered_answer or "therefore" in lowered_answer else 0.4
            return ScoreResult(score=score, reason="reasoning marker check")
        score = 0.7 if len(answer.strip()) >= 40 else 0.3
        return ScoreResult(score=score, reason="creative length check")
