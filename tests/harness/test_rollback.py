from pathlib import Path

import pytest

from src.common.exceptions import InvalidVersionStateError, VersionNotFoundError
from src.common.types import StrategyStatus
from src.harness.version_manager import VersionManager


def test_rollback_success(tmp_path: Path):
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})
    manager.promote_to_production("v001")
    manager.create_version("v002", "v001", {"system_prompt": "v2"})
    manager.promote_to_production("v002")

    parent_id = manager.rollback("v002")

    assert parent_id == "v001"
    assert manager.load_version("v001").status == StrategyStatus.PRODUCTION
    assert manager.load_version("v002").status == StrategyStatus.ROLLBACK
    assert (tmp_path / "current").resolve().name == "v001"


def test_rollback_not_production(tmp_path: Path):
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})

    with pytest.raises(InvalidVersionStateError, match="expected production"):
        manager.rollback("v001")


def test_rollback_no_parent(tmp_path: Path):
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})
    manager.promote_to_production("v001")

    with pytest.raises(InvalidVersionStateError, match="no parent"):
        manager.rollback("v001")


def test_rollback_nonexistent_version(tmp_path: Path):
    manager = VersionManager(tmp_path)

    with pytest.raises(VersionNotFoundError):
        manager.rollback("v999")
