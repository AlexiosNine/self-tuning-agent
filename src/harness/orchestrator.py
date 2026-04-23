from src.common.exceptions import InvalidVersionStateError, VersionNotFoundError
from src.common.types import EvaluationRecord
from src.harness.optimizer import StrategyOptimizer
from src.harness.trigger import OptimizationTrigger
from src.harness.version_manager import VersionManager


class HarnessOrchestrator:
    def __init__(self, version_manager: VersionManager, min_samples: int) -> None:
        self.version_manager = version_manager
        self.trigger = OptimizationTrigger(min_samples=min_samples)
        self.optimizer = StrategyOptimizer(version_manager)

    def maybe_optimize(self, records: list[EvaluationRecord]) -> str | None:
        if not self.trigger.should_optimize(records):
            return None

        current_link = self.version_manager.strategies_dir / "current"

        if not current_link.exists() and not current_link.is_symlink():
            raise ValueError("No production version set (current symlink missing)")

        if not current_link.is_symlink():
            raise ValueError("'current' is not a symlink")

        current_version = current_link.resolve().name

        version_suffix = current_version.removeprefix("v")
        try:
            current_number = int(version_suffix)
        except ValueError as e:
            raise ValueError(
                f"Cannot parse version number from '{current_version}'. "
                f"Expected format: v001, v002, etc."
            ) from e

        new_version = f"v{current_number + 1:03d}"
        return self.optimizer.create_mutation(current_version, new_version, records)
