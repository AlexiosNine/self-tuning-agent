import json
from pathlib import Path

import yaml

from src.common.types import StrategyStatus, StrategyVersion


class VersionManager:
    def __init__(self, strategies_dir: Path) -> None:
        self.strategies_dir = strategies_dir

    def load_version(self, version_id: str) -> StrategyVersion:
        metadata_path = self.strategies_dir / version_id / "metadata.json"
        data = json.loads(metadata_path.read_text())
        return StrategyVersion.model_validate(data)

    def load_prompt_config(self, version_id: str) -> dict:
        prompt_path = self.strategies_dir / version_id / "prompt.yaml"
        return yaml.safe_load(prompt_path.read_text())

    def promote_to_production(self, version_id: str) -> None:
        version_dir = self.strategies_dir / version_id
        current_link = self.strategies_dir / "current"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        current_link.symlink_to(version_dir, target_is_directory=True)
        version = self.load_version(version_id)
        updated = version.model_copy(update={"status": StrategyStatus.PRODUCTION})
        (version_dir / "metadata.json").write_text(updated.model_dump_json(indent=2))

    def create_version(self, version_id: str, parent_version: str | None, prompt_config: dict) -> None:
        version_dir = self.strategies_dir / version_id
        version_dir.mkdir(parents=True, exist_ok=False)
        (version_dir / "prompt.yaml").write_text(yaml.safe_dump(prompt_config))
        (version_dir / "rag_config.yaml").write_text(yaml.safe_dump({"top_k": 4}))
        (version_dir / "tool_config.yaml").write_text(yaml.safe_dump({"tools": []}))
        metadata = StrategyVersion(version_id=version_id, status=StrategyStatus.DRAFT, parent_version=parent_version)
        (version_dir / "metadata.json").write_text(metadata.model_dump_json(indent=2))
