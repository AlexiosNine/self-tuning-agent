from enum import StrEnum

from src.common.logger import setup_logger
from src.common.types import EvaluationRecord, QuestionType
from src.harness.version_manager import VersionManager

logger = setup_logger(__name__)


class MutationType(StrEnum):
    ADD_DEFINITION = "add_definition"
    ADD_REASONING = "add_reasoning"
    ADD_EXAMPLE = "add_example"
    SIMPLIFY = "simplify"


MUTATION_GUIDANCE: dict[MutationType, str] = {
    MutationType.ADD_DEFINITION: "Include concrete definitions before examples.",
    MutationType.ADD_REASONING: "Explain reasoning step-by-step using 'because' or 'therefore'.",
    MutationType.ADD_EXAMPLE: "Provide specific examples to illustrate concepts.",
    MutationType.SIMPLIFY: "Use simple, clear language. Keep answers under 200 words.",
}


def select_mutation_type(records: list[EvaluationRecord]) -> MutationType:
    """Select mutation type based on failure patterns in evaluation records."""
    low_score_records = [r for r in records if r.auto_score < 0.6]

    if not low_score_records:
        return MutationType.SIMPLIFY

    # Count failures by question type
    type_counts: dict[QuestionType, int] = {}
    for record in low_score_records:
        type_counts[record.question_type] = type_counts.get(record.question_type, 0) + 1

    # Find the most common failure type
    worst_type = max(type_counts, key=lambda t: type_counts[t])

    if worst_type == QuestionType.FACTUAL:
        return MutationType.ADD_DEFINITION
    if worst_type == QuestionType.REASONING:
        return MutationType.ADD_REASONING
    return MutationType.ADD_EXAMPLE


class StrategyOptimizer:
    def __init__(self, version_manager: VersionManager) -> None:
        self.version_manager = version_manager

    def create_mutation(
        self,
        parent_version: str,
        new_version: str,
        records: list[EvaluationRecord] | None = None,
    ) -> str:
        mutation_type = select_mutation_type(records) if records else MutationType.SIMPLIFY
        logger.info(
            "Creating mutation %s from %s (type=%s)",
            new_version, parent_version, mutation_type,
        )

        parent_prompt = self.version_manager.load_prompt_config(parent_version)
        base_prompt = parent_prompt["system_prompt"]
        guidance = MUTATION_GUIDANCE[mutation_type]

        mutated_prompt = {"system_prompt": f"{base_prompt} {guidance}"}
        self.version_manager.create_version(new_version, parent_version, mutated_prompt)

        logger.info("Created mutation %s", new_version)
        return new_version
