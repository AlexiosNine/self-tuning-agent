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
        current_version = (self.version_manager.strategies_dir / "current").resolve().name
        current_number = int(current_version.removeprefix("v"))
        new_version = f"v{current_number + 1:03d}"
        return self.optimizer.create_mutation(current_version, new_version)
