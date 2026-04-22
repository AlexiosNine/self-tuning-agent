from src.common.types import EvaluationRecord


class QualityFilter:
    """Filters evaluation records by quality criteria.

    Criteria:
      - auto_score >= 0.8
      - human_label is None or "positive"
      - answer length (stripped) >= 10 characters
    """

    def is_high_quality(self, record: EvaluationRecord) -> bool:
        has_positive_human_label = record.human_label in {None, "positive"}
        return (
            record.auto_score >= 0.8
            and has_positive_human_label
            and len(record.answer.strip()) >= 10
        )
