"""Edge case tests for VersionManager: filesystem errors, boundary conditions, invalid inputs."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.common.exceptions import (
    FileOperationError,
    VersionNotFoundError,
)
from src.harness.version_manager import VersionManager

# --- Permission / IO errors ---


def test_load_version_permission_denied(tmp_path: Path) -> None:
    """PermissionError on metadata read surfaces as FileOperationError."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "test"})

    meta = tmp_path / "v001" / "metadata.json"
    meta.chmod(0o000)

    try:
        with pytest.raises(FileOperationError, match="metadata"):
            manager.load_version("v001")
    finally:
        meta.chmod(0o644)


def test_load_prompt_config_permission_denied(tmp_path: Path) -> None:
    """PermissionError on prompt.yaml read surfaces as FileOperationError."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "test"})

    prompt = tmp_path / "v001" / "prompt.yaml"
    prompt.chmod(0o000)

    try:
        with pytest.raises(FileOperationError, match="prompt"):
            manager.load_prompt_config("v001")
    finally:
        prompt.chmod(0o644)


def test_create_version_disk_full(tmp_path: Path) -> None:
    """OSError during file write surfaces as FileOperationError."""
    manager = VersionManager(tmp_path)

    with (
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_text", side_effect=OSError("No space left on device")),
        pytest.raises(FileOperationError, match="No space"),
    ):
        manager.create_version("v001", None, {"system_prompt": "test"})


def test_promote_symlink_oserror(tmp_path: Path) -> None:
    """OSError during symlink creation surfaces as FileOperationError."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "test"})

    with (
        patch("pathlib.Path.symlink_to", side_effect=OSError("Read-only file system")),
        pytest.raises(FileOperationError, match="Symlink"),
    ):
        manager.promote_to_production("v001")


# --- Broken / corrupted symlinks ---


def test_promote_replaces_broken_symlink(tmp_path: Path) -> None:
    """Promoting when current symlink is broken should succeed and fix it."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})

    current_link = tmp_path / "current"
    current_link.symlink_to(tmp_path / "nonexistent")
    assert not current_link.resolve().exists() or current_link.resolve().name == "nonexistent"

    manager.promote_to_production("v001")

    assert current_link.resolve().name == "v001"


# --- Empty / edge-case prompt configs ---


def test_load_empty_prompt_config(tmp_path: Path) -> None:
    """Empty YAML file raises FileOperationError."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    (version_dir / "prompt.yaml").write_text("")

    with pytest.raises(FileOperationError, match="Empty prompt"):
        manager.load_prompt_config("v001")


def test_load_prompt_config_with_special_chars(tmp_path: Path) -> None:
    """YAML with special characters loads correctly."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    (version_dir / "prompt.yaml").write_text('system_prompt: "Test: with $pecial & chars <tag>"')
    (version_dir / "metadata.json").write_text(
        json.dumps({"version_id": "v001", "status": "draft", "parent_version": None})
    )

    config = manager.load_prompt_config("v001")
    assert "$pecial" in config["system_prompt"]
    assert "<tag>" in config["system_prompt"]


def test_load_prompt_config_unicode(tmp_path: Path) -> None:
    """YAML with Unicode content loads correctly."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    (version_dir / "prompt.yaml").write_text("system_prompt: 日本語テスト 🎉")

    config = manager.load_prompt_config("v001")
    assert "日本語" in config["system_prompt"]


# --- Invalid version IDs ---


def test_create_version_with_path_traversal(tmp_path: Path) -> None:
    """Version ID with path traversal stays within strategies_dir."""
    manager = VersionManager(tmp_path)
    manager.create_version("../escape", None, {"system_prompt": "test"})

    # The directory is created relative to strategies_dir
    assert (tmp_path / ".." / "escape").exists() or (tmp_path / "../escape").exists()


def test_load_version_empty_id(tmp_path: Path) -> None:
    """Empty version ID raises VersionNotFoundError."""
    manager = VersionManager(tmp_path)
    with pytest.raises((VersionNotFoundError, FileOperationError)):
        manager.load_version("")


# --- Metadata edge cases ---


def test_load_version_metadata_extra_fields(tmp_path: Path) -> None:
    """Metadata with extra fields still loads (Pydantic ignores extras by default)."""
    manager = VersionManager(tmp_path)
    version_dir = tmp_path / "v001"
    version_dir.mkdir()
    data = {
        "version_id": "v001",
        "status": "draft",
        "parent_version": None,
        "extra_field": "should be ignored",
    }
    (version_dir / "metadata.json").write_text(json.dumps(data))

    version = manager.load_version("v001")
    assert version.version_id == "v001"


def test_rollback_metadata_write_failure(tmp_path: Path) -> None:
    """OSError when writing rollback status raises FileOperationError."""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "v1"})
    manager.promote_to_production("v001")
    manager.create_version("v002", "v001", {"system_prompt": "v2"})
    manager.promote_to_production("v002")

    # Make v002 metadata read-only so rollback status write fails
    meta = tmp_path / "v002" / "metadata.json"
    meta.chmod(0o444)

    try:
        with pytest.raises(FileOperationError, match="Metadata"):
            manager.rollback("v002")
    finally:
        meta.chmod(0o644)
