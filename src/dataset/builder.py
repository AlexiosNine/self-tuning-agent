from pathlib import Path

from src.common.types import EvaluationRecord
from src.dataset.converter import DatasetConverter
from src.dataset.quality_filter import QualityFilter


class DatasetBuilder:
    """Orchestrates quality filtering and JSONL export.

    Filters records through QualityFilter, converts via DatasetConverter,
    and writes output to output_dir/processed/finetuning/<format>/train.jsonl.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.quality_filter = QualityFilter()
        self.converter = DatasetConverter()

    def build_generic_dataset(self, records: list[EvaluationRecord]) -> Path:
        generic_dir = self.output_dir / "processed" / "finetuning" / "generic"
        generic_dir.mkdir(parents=True, exist_ok=True)
        output_path = generic_dir / "train.jsonl"
        lines = [
            self.converter.to_generic(record)
            for record in records
            if self.quality_filter.is_high_quality(record)
        ]
        output_path.write_text("\n".join(lines))
        return output_path
