from typing import Any


def render_system_prompt(prompt_config: dict[str, Any]) -> str:
    return str(prompt_config["system_prompt"])
