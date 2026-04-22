import logging
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


def test_load_config_initializes_logger(tmp_path: Path) -> None:
    # Remove existing handlers to allow setup_logger to add new ones
    logger = logging.getLogger("self-tuning-agent")
    logger.handlers.clear()

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
  min_samples: 10
  canary_ratio: 0.1
log_level: DEBUG
log_file: null
""".strip()
    )

    config = load_config(config_file)

    assert config.log_level == "DEBUG"
    assert config.log_file is None

    # Verify logger was initialized
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) > 0
