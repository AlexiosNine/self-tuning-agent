"""Concurrent operation tests for VersionManager."""

import threading
from pathlib import Path

from src.common.types import StrategyStatus
from src.harness.version_manager import VersionManager


def test_concurrent_version_creation(tmp_path: Path) -> None:
    """Concurrent version creation should not corrupt state."""
    manager = VersionManager(tmp_path)
    errors: list[Exception] = []

    def create_version(version_id: str) -> None:
        try:
            manager.create_version(version_id, None, {"system_prompt": f"prompt-{version_id}"})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=create_version, args=(f"v{i:03d}",)) for i in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0

    for i in range(10):
        version = manager.load_version(f"v{i:03d}")
        assert version.version_id == f"v{i:03d}"
        assert version.status == StrategyStatus.DRAFT


def test_concurrent_promote_and_rollback(tmp_path: Path) -> None:
    """Concurrent promote and rollback should leave consistent state."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})
    manager.create_version("v002", "v001", {"system_prompt": "v2"})
    manager.promote_to_production("v001")

    results: list[str] = []

    def promote() -> None:
        try:
            manager.promote_to_production("v002")
            results.append("promote_ok")
        except Exception as e:
            results.append(f"promote_err:{e}")

    def rollback() -> None:
        try:
            manager.rollback("v001")
            results.append("rollback_ok")
        except Exception as e:
            results.append(f"rollback_err:{e}")

    t1 = threading.Thread(target=promote)
    t2 = threading.Thread(target=rollback)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # At least one operation should succeed
    assert len([r for r in results if "_ok" in r]) >= 1

    # Final state: symlink must be valid
    current = tmp_path / "current"
    assert current.exists()
    assert current.is_symlink()
    assert current.resolve().name in ["v001", "v002"]


def test_concurrent_create_same_version(tmp_path: Path) -> None:
    """Two threads creating the same version: one succeeds, one gets VersionAlreadyExistsError."""
    manager = VersionManager(tmp_path)
    results: list[str] = []

    def create() -> None:
        try:
            manager.create_version("v001", None, {"system_prompt": "test"})
            results.append("ok")
        except Exception:
            results.append("conflict")

    t1 = threading.Thread(target=create)
    t2 = threading.Thread(target=create)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results.count("ok") == 1
    assert results.count("conflict") == 1


def test_concurrent_rapid_promotions(tmp_path: Path) -> None:
    """Rapid sequential promotions of different versions leave a valid final state."""
    manager = VersionManager(tmp_path)
    version_ids = [f"v{i:03d}" for i in range(5)]
    for vid in version_ids:
        manager.create_version(vid, None, {"system_prompt": f"prompt-{vid}"})

    errors: list[Exception] = []

    def promote(vid: str) -> None:
        try:
            manager.promote_to_production(vid)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=promote, args=(vid,)) for vid in version_ids]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0

    current = tmp_path / "current"
    assert current.exists()
    assert current.is_symlink()
    assert current.resolve().name in version_ids
