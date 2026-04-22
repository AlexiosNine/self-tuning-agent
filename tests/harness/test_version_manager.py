import json
from pathlib import Path

from src.harness.version_manager import VersionManager


def test_promote_to_production_updates_current_symlink(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    version_dir = strategies_dir / "v001"
    version_dir.mkdir(parents=True)
    (version_dir / "prompt.yaml").write_text("system_prompt: base")
    (version_dir / "rag_config.yaml").write_text("top_k: 4")
    (version_dir / "tool_config.yaml").write_text("tools: []")
    (version_dir / "metadata.json").write_text(
        json.dumps({"version_id": "v001", "status": "draft", "parent_version": None})
    )

    manager = VersionManager(strategies_dir)
    manager.promote_to_production("v001")

    current = strategies_dir / "current"
    assert current.is_symlink()
    assert current.resolve() == version_dir.resolve()
    assert manager.load_version("v001").status.value == "production"


def test_create_version_generates_all_files(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    manager = VersionManager(strategies_dir)

    prompt_config = {"system_prompt": "You are a helpful assistant", "temperature": 0.7}
    manager.create_version("v001", None, prompt_config)

    version_dir = strategies_dir / "v001"
    assert version_dir.exists()
    assert (version_dir / "prompt.yaml").exists()
    assert (version_dir / "rag_config.yaml").exists()
    assert (version_dir / "tool_config.yaml").exists()
    assert (version_dir / "metadata.json").exists()

    version = manager.load_version("v001")
    assert version.version_id == "v001"
    assert version.status.value == "draft"
    assert version.parent_version is None


def test_load_prompt_config_returns_dict(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    version_dir = strategies_dir / "v001"
    version_dir.mkdir(parents=True)
    (version_dir / "prompt.yaml").write_text("system_prompt: test\ntemperature: 0.5")

    manager = VersionManager(strategies_dir)
    config = manager.load_prompt_config("v001")

    assert config["system_prompt"] == "test"
    assert config["temperature"] == 0.5


def test_create_version_with_parent(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    manager = VersionManager(strategies_dir)

    manager.create_version("v001", None, {"system_prompt": "base"})
    manager.create_version("v002", "v001", {"system_prompt": "improved"})

    v002 = manager.load_version("v002")
    assert v002.parent_version == "v001"


def test_promote_replaces_existing_symlink(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    v001_dir = strategies_dir / "v001"
    v002_dir = strategies_dir / "v002"
    v001_dir.mkdir(parents=True)
    v002_dir.mkdir(parents=True)

    for version_dir in [v001_dir, v002_dir]:
        (version_dir / "prompt.yaml").write_text("system_prompt: base")
        (version_dir / "rag_config.yaml").write_text("top_k: 4")
        (version_dir / "tool_config.yaml").write_text("tools: []")
        version_id = version_dir.name
        (version_dir / "metadata.json").write_text(
            json.dumps({"version_id": version_id, "status": "draft", "parent_version": None})
        )

    manager = VersionManager(strategies_dir)
    manager.promote_to_production("v001")
    manager.promote_to_production("v002")

    current = strategies_dir / "current"
    assert current.resolve() == v002_dir.resolve()
