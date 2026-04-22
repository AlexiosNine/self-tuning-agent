from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.common.logger import setup_logger


class ModelConfig(BaseModel):
    provider: str
    model_name: str


class PathConfig(BaseModel):
    strategies_dir: Path
    datasets_dir: Path


class ThresholdConfig(BaseModel):
    min_samples: int
    canary_ratio: float


class AppConfig(BaseModel):
    model: ModelConfig
    paths: PathConfig
    thresholds: ThresholdConfig
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path | None = Field(default=None, description="Optional log file path")


def load_config(file_path: Path) -> AppConfig:
    data = yaml.safe_load(file_path.read_text())
    config = AppConfig.model_validate(data)

    # Initialize logger
    setup_logger("self-tuning-agent", level=config.log_level, log_file=config.log_file)

    return config
