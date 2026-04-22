import json
from pathlib import Path

from src.common.types import EvaluationRecord, QuestionType
from src.dataset.builder import DatasetBuilder


def test_builder_exports_only_high_quality_records(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    records = [
        EvaluationRecord(
            question="What is Docker?",
            answer="Docker is a container platform.",
            question_type=QuestionType.FACTUAL,
            auto_score=0.95,
            human_label="positive",
        ),
        EvaluationRecord(
            question="Bad sample",
            answer="no",
            question_type=QuestionType.FACTUAL,
            auto_score=0.2,
        ),
    ]

    generic_path = builder.build_generic_dataset(records)
    lines = generic_path.read_text().splitlines()

    assert len(lines) == 1
    assert '"question": "What is Docker?"' in lines[0]


def test_builder_filters_negative_human_label(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    records = [
        EvaluationRecord(
            question="What is Python?",
            answer="Python is a programming language.",
            question_type=QuestionType.FACTUAL,
            auto_score=0.9,
            human_label="negative",
        ),
    ]

    generic_path = builder.build_generic_dataset(records)
    lines = generic_path.read_text().splitlines()

    assert lines == []


def test_builder_filters_short_answer(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    records = [
        EvaluationRecord(
            question="What is Go?",
            answer="A lang.",
            question_type=QuestionType.FACTUAL,
            auto_score=0.9,
            human_label="positive",
        ),
    ]

    generic_path = builder.build_generic_dataset(records)
    lines = generic_path.read_text().splitlines()

    assert lines == []


def test_builder_generic_format_structure(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    records = [
        EvaluationRecord(
            question="What is Rust?",
            answer="Rust is a systems programming language.",
            question_type=QuestionType.REASONING,
            auto_score=0.85,
            human_label="positive",
            user_feedback="Great answer",
        ),
    ]

    generic_path = builder.build_generic_dataset(records)
    line = json.loads(generic_path.read_text().splitlines()[0])

    assert line["question"] == "What is Rust?"
    assert line["answer"] == "Rust is a systems programming language."
    assert line["task_type"] == "reasoning"
    assert line["metadata"]["auto_eval_score"] == 0.85
    assert line["metadata"]["human_annotation"] == "positive"
    assert line["metadata"]["user_feedback"] == "Great answer"


def test_builder_output_path(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    generic_path = builder.build_generic_dataset([])

    expected = tmp_path / "processed" / "finetuning" / "generic" / "train.jsonl"
    assert generic_path == expected


def test_builder_none_human_label_passes_filter(tmp_path: Path) -> None:
    builder = DatasetBuilder(output_dir=tmp_path)
    records = [
        EvaluationRecord(
            question="What is Kubernetes?",
            answer="Kubernetes is a container orchestration platform.",
            question_type=QuestionType.FACTUAL,
            auto_score=0.82,
            human_label=None,
        ),
    ]

    generic_path = builder.build_generic_dataset(records)
    lines = generic_path.read_text().splitlines()

    assert len(lines) == 1
    assert '"question": "What is Kubernetes?"' in lines[0]
