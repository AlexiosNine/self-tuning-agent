from pathlib import Path

from src.common.config import AppConfig, load_config


def test_load_config_reads_yaml_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
model:
  provider: claude
  model_name: claude-sonnet-4-6
paths:
  strategies_dir: strategies
  datasets_dir: datasets
thresholds:
  min_samples: 100
  canary_ratio: 0.1
""".strip()
    )

    config = load_config(config_file)

    assert isinstance(config, AppConfig)
    assert config.model.provider == "claude"
    assert config.paths.strategies_dir == Path("strategies")
    assert config.thresholds.canary_ratio == 0.1
