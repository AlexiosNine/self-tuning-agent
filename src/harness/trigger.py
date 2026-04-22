from src.common.types import EvaluationRecord


class OptimizationTrigger:
    def __init__(self, min_samples: int, score_threshold: float = 0.6) -> None:
        self.min_samples = min_samples
        self.score_threshold = score_threshold

    def should_optimize(self, records: list[EvaluationRecord]) -> bool:
        if len(records) < self.min_samples:
            return False
        average = sum(record.auto_score for record in records) / len(records)
        return average < self.score_threshold
