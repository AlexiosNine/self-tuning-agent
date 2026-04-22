from src.harness.version_manager import VersionManager


class StrategyOptimizer:
    def __init__(self, version_manager: VersionManager) -> None:
        self.version_manager = version_manager

    def create_mutation(self, parent_version: str, new_version: str) -> str:
        parent_prompt = self.version_manager.load_prompt_config(parent_version)
        mutated_prompt = {
            "system_prompt": f"{parent_prompt['system_prompt']} Include concrete definitions before examples.",
        }
        self.version_manager.create_version(new_version, parent_version, mutated_prompt)
        return new_version
