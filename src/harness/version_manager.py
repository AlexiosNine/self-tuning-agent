import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from src.common.exceptions import (
    FileOperationError,
    InvalidVersionStateError,
    VersionAlreadyExistsError,
    VersionNotFoundError,
)
from src.common.logger import setup_logger
from src.common.types import StrategyStatus, StrategyVersion

logger = setup_logger(__name__)


class VersionManager:
    def __init__(self, strategies_dir: Path) -> None:
        self.strategies_dir = strategies_dir
        self._prompt_cache: dict[str, dict[str, Any]] = {}

    def load_version(self, version_id: str) -> StrategyVersion:
        """Load version metadata from disk.

        Args:
            version_id: Version identifier

        Returns:
            StrategyVersion object

        Raises:
            VersionNotFoundError: Version does not exist
            FileOperationError: Failed to read or parse metadata
        """
        metadata_path = self.strategies_dir / version_id / "metadata.json"

        try:
            data = json.loads(metadata_path.read_text())
        except FileNotFoundError as e:
            logger.error(f"Version {version_id} not found")
            raise VersionNotFoundError(f"Version {version_id} not found") from e
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted metadata for {version_id}: {e}")
            raise FileOperationError(f"Failed to parse metadata for {version_id}: {e}") from e
        except OSError as e:
            logger.error(f"Failed to read metadata for {version_id}: {e}")
            raise FileOperationError(f"Failed to read metadata for {version_id}: {e}") from e

        try:
            version = StrategyVersion.model_validate(data)
            logger.info(f"Loaded version {version_id}")
            return version
        except ValidationError as e:
            logger.error(f"Invalid metadata schema for {version_id}: {e}")
            raise FileOperationError(f"Invalid metadata schema for {version_id}: {e}") from e

    def load_prompt_config(self, version_id: str) -> dict[str, Any]:
        """Load prompt configuration from disk.

        Args:
            version_id: Version identifier

        Returns:
            Prompt configuration dict

        Raises:
            VersionNotFoundError: Version does not exist
            FileOperationError: Failed to read or parse prompt config
        """
        if version_id in self._prompt_cache:
            logger.debug(f"Returning cached prompt config for {version_id}")
            return self._prompt_cache[version_id]

        prompt_path = self.strategies_dir / version_id / "prompt.yaml"

        try:
            data = yaml.safe_load(prompt_path.read_text())
            if data is None:
                raise FileOperationError(f"Empty prompt config for version {version_id}")
            result: dict[str, Any] = data
            self._prompt_cache[version_id] = result
            logger.info(f"Loaded prompt config for {version_id}")
            return result
        except FileNotFoundError as e:
            logger.error(f"Prompt config for {version_id} not found")
            raise VersionNotFoundError(f"Version {version_id} prompt config not found") from e
        except yaml.YAMLError as e:
            logger.error(f"Corrupted prompt config for {version_id}: {e}")
            raise FileOperationError(f"Failed to parse prompt config for {version_id}: {e}") from e
        except OSError as e:
            logger.error(f"Failed to read prompt config for {version_id}: {e}")
            raise FileOperationError(f"Failed to read prompt config for {version_id}: {e}") from e

    def promote_to_production(self, version_id: str) -> None:
        """Promote a version to production with atomic symlink replacement.

        Args:
            version_id: Version identifier to promote

        Raises:
            VersionNotFoundError: Version does not exist
            FileOperationError: Failed to update symlink or metadata
        """
        logger.info(f"Promoting {version_id} to production")

        version_dir = self.strategies_dir / version_id
        if not version_dir.exists():
            logger.error(f"Version {version_id} does not exist")
            raise VersionNotFoundError(f"Version {version_id} not found")

        current_link = self.strategies_dir / "current"
        # Use PID + timestamp + thread ID for uniqueness
        temp_link = self.strategies_dir / f".current.tmp.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}"

        try:
            # Atomic symlink replacement
            temp_link.symlink_to(version_dir, target_is_directory=True)
            temp_link.replace(current_link)  # Atomic on POSIX
            logger.info(f"Symlink updated to {version_id}")
        except OSError as e:
            logger.error(f"Failed to create symlink: {e}")
            temp_link.unlink(missing_ok=True)
            raise FileOperationError(f"Symlink operation failed: {e}") from e

        # Update metadata
        version = self.load_version(version_id)
        updated = version.model_copy(update={"status": StrategyStatus.PRODUCTION})
        try:
            (version_dir / "metadata.json").write_text(updated.model_dump_json(indent=2))
            logger.info(f"Updated {version_id} status to PRODUCTION")
        except OSError as e:
            logger.error(f"Failed to update metadata: {e}")
            raise FileOperationError(f"Metadata update failed: {e}") from e

    def rollback(self, version_id: str) -> str:
        """Rollback a production version to its parent.

        Args:
            version_id: Version to rollback (must be PRODUCTION)

        Returns:
            Parent version ID that was promoted

        Raises:
            VersionNotFoundError: If version does not exist
            InvalidVersionStateError: If version is not PRODUCTION or has no parent
        """
        logger.info("Rolling back version %s", version_id)

        version = self.load_version(version_id)

        if version.status != StrategyStatus.PRODUCTION:
            raise InvalidVersionStateError(
                f"Cannot rollback {version_id}: status is {version.status}, expected production"
            )

        if not version.parent_version:
            raise InvalidVersionStateError(f"Cannot rollback {version_id}: no parent version")

        parent_id = version.parent_version

        # Promote parent back to production (uses atomic symlink)
        self.promote_to_production(parent_id)

        # Mark rolled-back version
        rolled_back = version.model_copy(update={"status": StrategyStatus.ROLLBACK})
        version_dir = self.strategies_dir / version_id
        try:
            (version_dir / "metadata.json").write_text(rolled_back.model_dump_json(indent=2))
        except OSError as e:
            logger.error("Failed to update rollback status for %s: %s", version_id, e)
            raise FileOperationError(f"Metadata update failed for {version_id}") from e

        logger.info("Rolled back %s to %s", version_id, parent_id)
        return parent_id

    def create_version(self, version_id: str, parent_version: str | None, prompt_config: dict[str, Any]) -> None:
        """Create a new version with configuration files.

        Args:
            version_id: Version identifier
            parent_version: Parent version ID (None for initial version)
            prompt_config: Prompt configuration dict

        Raises:
            VersionAlreadyExistsError: Version already exists
            FileOperationError: Failed to create version files
        """
        version_dir = self.strategies_dir / version_id

        try:
            version_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as e:
            logger.error(f"Version {version_id} already exists")
            raise VersionAlreadyExistsError(f"Version {version_id} already exists") from e
        except OSError as e:
            logger.error(f"Failed to create version directory for {version_id}: {e}")
            raise FileOperationError(f"Failed to create version {version_id}: {e}") from e

        self._prompt_cache.pop(version_id, None)

        try:
            (version_dir / "prompt.yaml").write_text(yaml.safe_dump(prompt_config))
            (version_dir / "rag_config.yaml").write_text(yaml.safe_dump({"top_k": 4}))
            (version_dir / "tool_config.yaml").write_text(yaml.safe_dump({"tools": []}))

            metadata = StrategyVersion(
                version_id=version_id, status=StrategyStatus.DRAFT, parent_version=parent_version
            )
            (version_dir / "metadata.json").write_text(metadata.model_dump_json(indent=2))

            logger.info(f"Created version {version_id}")
        except OSError as e:
            logger.error(f"Failed to write config files for {version_id}: {e}")
            raise FileOperationError(f"Failed to write config files for {version_id}: {e}") from e
