import random
from dataclasses import dataclass

from src.common.logger import setup_logger
from src.harness.version_manager import VersionManager

logger = setup_logger(__name__)


@dataclass
class ABTestConfig:
    """A/B test configuration for traffic splitting."""

    control_version: str
    treatment_version: str
    treatment_ratio: float  # 0.0 to 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.treatment_ratio <= 1.0:
            raise ValueError(f"treatment_ratio must be between 0.0 and 1.0, got {self.treatment_ratio}")


class ABTestManager:
    """Manages A/B testing for strategy versions."""

    def __init__(self, version_manager: VersionManager) -> None:
        self.version_manager = version_manager
        self._active_test: ABTestConfig | None = None

    def start_test(self, control_version: str, treatment_version: str, treatment_ratio: float) -> None:
        """Start a new A/B test.

        Args:
            control_version: Current production version (control group)
            treatment_version: New version to test (treatment group)
            treatment_ratio: Percentage of traffic to route to treatment (0.0 to 1.0)

        Raises:
            ValueError: If versions don't exist or ratio is invalid
        """
        # Validate versions exist
        self.version_manager.load_version(control_version)
        self.version_manager.load_version(treatment_version)

        self._active_test = ABTestConfig(
            control_version=control_version, treatment_version=treatment_version, treatment_ratio=treatment_ratio
        )

        logger.info(
            "Started A/B test: control=%s, treatment=%s, ratio=%.2f",
            control_version,
            treatment_version,
            treatment_ratio,
        )

    def stop_test(self) -> None:
        """Stop the active A/B test."""
        if self._active_test:
            logger.info(
                "Stopped A/B test: %s vs %s", self._active_test.control_version, self._active_test.treatment_version
            )
            self._active_test = None

    def get_version_for_request(self, request_id: str | None = None) -> str:
        """Get the version to use for a request based on A/B test configuration.

        Args:
            request_id: Optional request identifier for deterministic routing

        Returns:
            Version ID to use (either control or treatment)
        """
        if not self._active_test:
            # No active test, use production version
            current_link = self.version_manager.strategies_dir / "current"
            if not current_link.exists():
                raise ValueError("No production version set and no active A/B test")
            return current_link.resolve().name

        # Deterministic routing if request_id provided
        if request_id:
            hash_value = hash(request_id)
            ratio = (hash_value % 100) / 100.0
        else:
            # Note: random.random() is sufficient for A/B testing traffic splitting
            # This is not used for cryptographic purposes
            ratio = random.random()  # noqa: S311  # nosec B311

        if ratio < self._active_test.treatment_ratio:
            logger.debug("Routing to treatment version: %s", self._active_test.treatment_version)
            return self._active_test.treatment_version
        logger.debug("Routing to control version: %s", self._active_test.control_version)
        return self._active_test.control_version

    @property
    def is_test_active(self) -> bool:
        """Check if an A/B test is currently active."""
        return self._active_test is not None

    @property
    def active_test(self) -> ABTestConfig | None:
        """Get the active A/B test configuration."""
        return self._active_test
