from pathlib import Path

import yaml
from pydantic import BaseModel


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


def load_config(file_path: Path) -> AppConfig:
    data = yaml.safe_load(file_path.read_text())
    return AppConfig.model_validate(data)
