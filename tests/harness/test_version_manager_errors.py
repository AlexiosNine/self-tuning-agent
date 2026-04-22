"""Error handling tests for VersionManager."""

import json
import threading
from pathlib import Path

import pytest

from src.common.exceptions import (
    FileOperationError,
    VersionAlreadyExistsError,
    VersionNotFoundError,
)
from src.harness.version_manager import VersionManager


def test_load_version_not_found(tmp_path: Path) -> None:
    """Test that loading a non-existent version raises VersionNotFoundError."""
    manager = VersionManager(tmp_path)
    with pytest.raises(VersionNotFoundError, match="v999"):
        manager.load_version("v999")


def test_load_version_corrupted_json(tmp_path: Path) -> None:
    """Test that loading corrupted metadata raises FileOperationError."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    (version_dir / "metadata.json").write_text("invalid json{")

    with pytest.raises(FileOperationError, match="metadata"):
        manager.load_version("v001")


def test_load_version_invalid_schema(tmp_path: Path) -> None:
    """Test that loading invalid metadata schema raises FileOperationError."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    # Missing required fields
    (version_dir / "metadata.json").write_text(json.dumps({"invalid": "data"}))

    with pytest.raises(FileOperationError, match="metadata"):
        manager.load_version("v001")


def test_load_prompt_config_not_found(tmp_path: Path) -> None:
    """Test that loading non-existent prompt config raises VersionNotFoundError."""
    manager = VersionManager(tmp_path)
    with pytest.raises(VersionNotFoundError, match="v999"):
        manager.load_prompt_config("v999")


def test_load_prompt_config_corrupted_yaml(tmp_path: Path) -> None:
    """Test that loading corrupted YAML raises FileOperationError."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    (version_dir / "prompt.yaml").write_text("invalid: yaml: content: [")

    with pytest.raises(FileOperationError, match="prompt"):
        manager.load_prompt_config("v001")


def test_create_version_already_exists(tmp_path: Path) -> None:
    """Test that creating an existing version raises VersionAlreadyExistsError."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "test"})

    with pytest.raises(VersionAlreadyExistsError, match="v001"):
        manager.create_version("v001", None, {"system_prompt": "test2"})


def test_create_version_io_error(tmp_path: Path) -> None:
    """Test that I/O errors during creation raise FileOperationError."""
    manager = VersionManager(tmp_path)
    # Make strategies_dir read-only to trigger permission error
    tmp_path.chmod(0o444)

    try:
        with pytest.raises(FileOperationError, match="create"):
            manager.create_version("v001", None, {"system_prompt": "test"})
    finally:
        # Restore permissions for cleanup
        tmp_path.chmod(0o755)


def test_promote_version_not_found(tmp_path: Path) -> None:
    """Test that promoting non-existent version raises VersionNotFoundError."""
    manager = VersionManager(tmp_path)
    with pytest.raises(VersionNotFoundError, match="v999"):
        manager.promote_to_production("v999")


def test_promote_concurrent_safe(tmp_path: Path) -> None:
    """Test that concurrent promotions don't corrupt symlink."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})
    manager.create_version("v002", None, {"system_prompt": "v2"})

    errors: list[Exception] = []

    def promote(version_id: str) -> None:
        try:
            manager.promote_to_production(version_id)
        except Exception as e:
            errors.append(e)

    # Simulate concurrent promotions
    threads = [
        threading.Thread(target=promote, args=("v001",)),
        threading.Thread(target=promote, args=("v002",)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify symlink is valid (points to one of the versions)
    current = tmp_path / "current"
    assert current.exists()
    assert current.is_symlink()
    assert current.resolve().name in ["v001", "v002"]

    # No errors should have occurred
    assert len(errors) == 0
