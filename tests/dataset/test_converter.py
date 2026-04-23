"""Tests for DatasetConverter - validates provider-specific format conversion.

This module tests the conversion of EvaluationRecord to OpenAI and Anthropic
fine-tuning formats, ensuring correct structure, Unicode handling, and field mapping.
"""

import json

import pytest

from src.common.types import EvaluationRecord, QuestionType
from src.dataset.converter import DatasetConverter


@pytest.fixture
def converter() -> DatasetConverter:
    """Fixture providing a DatasetConverter instance."""
    return DatasetConverter()


@pytest.fixture
def sample_record() -> EvaluationRecord:
    """Fixture providing a sample EvaluationRecord with all fields."""
    return EvaluationRecord(
        question="What is Docker?",
        answer="Docker is a container platform.",
        question_type=QuestionType.FACTUAL,
        auto_score=0.95,
        human_label="positive",
        user_feedback="Great answer",
    )


# ===== OpenAI Format Tests =====


def test_to_openai_format_structure(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_openai() produces correct messages array structure."""
    result = converter.to_openai(sample_record)
    payload = json.loads(result)

    assert "messages" in payload
    assert isinstance(payload["messages"], list)
    assert len(payload["messages"]) == 3


def test_to_openai_role_fields(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_openai() includes correct role fields."""
    result = converter.to_openai(sample_record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"


def test_to_openai_system_message(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_openai() includes system message."""
    result = converter.to_openai(sample_record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["content"] == "You are a professional QA assistant."


def test_to_openai_content_mapping(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_openai() correctly maps question and answer to content fields."""
    result = converter.to_openai(sample_record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[1]["content"] == "What is Docker?"
    assert messages[2]["content"] == "Docker is a container platform."


def test_to_openai_unicode_preservation(converter: DatasetConverter) -> None:
    """Test that to_openai() preserves Unicode characters (ensure_ascii=False)."""
    record = EvaluationRecord(
        question="什么是Docker？",
        answer="Docker是一个容器平台。",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9,
    )
    result = converter.to_openai(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[1]["content"] == "什么是Docker？"
    assert messages[2]["content"] == "Docker是一个容器平台。"
    # Verify raw string contains Unicode, not escaped
    assert "什么是Docker" in result


def test_to_openai_all_question_types(converter: DatasetConverter) -> None:
    """Test that to_openai() works with all QuestionType values."""
    for question_type in QuestionType:
        record = EvaluationRecord(
            question="Test question",
            answer="Test answer",
            question_type=question_type,
            auto_score=0.8,
        )
        result = converter.to_openai(record)
        payload = json.loads(result)

        # Should produce valid JSON regardless of question_type
        assert "messages" in payload
        assert len(payload["messages"]) == 3


def test_to_openai_empty_strings(converter: DatasetConverter) -> None:
    """Test that to_openai() handles empty strings gracefully."""
    record = EvaluationRecord(
        question="",
        answer="",
        question_type=QuestionType.FACTUAL,
        auto_score=0.5,
    )
    result = converter.to_openai(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[1]["content"] == ""
    assert messages[2]["content"] == ""


def test_to_openai_special_characters(converter: DatasetConverter) -> None:
    """Test that to_openai() handles special characters correctly."""
    record = EvaluationRecord(
        question='What is "Docker"?',
        answer="It's a container platform.\nSupports multi-line text.",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9,
    )
    result = converter.to_openai(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[1]["content"] == 'What is "Docker"?'
    assert messages[2]["content"] == "It's a container platform.\nSupports multi-line text."


# ===== Anthropic Format Tests =====


def test_to_anthropic_format_structure(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_anthropic() produces correct structure with top-level system field."""
    result = converter.to_anthropic(sample_record)
    payload = json.loads(result)

    assert "system" in payload
    assert "messages" in payload
    assert isinstance(payload["messages"], list)
    assert len(payload["messages"]) == 2


def test_to_anthropic_system_field(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_anthropic() places system prompt at top level."""
    result = converter.to_anthropic(sample_record)
    payload = json.loads(result)

    assert payload["system"] == "You are a professional QA assistant."


def test_to_anthropic_role_fields(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_anthropic() includes correct role fields in messages."""
    result = converter.to_anthropic(sample_record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_to_anthropic_content_mapping(converter: DatasetConverter, sample_record: EvaluationRecord) -> None:
    """Test that to_anthropic() correctly maps question and answer."""
    result = converter.to_anthropic(sample_record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["content"] == "What is Docker?"
    assert messages[1]["content"] == "Docker is a container platform."


def test_to_anthropic_unicode_preservation(converter: DatasetConverter) -> None:
    """Test that to_anthropic() preserves Unicode characters (ensure_ascii=False)."""
    record = EvaluationRecord(
        question="什么是Kubernetes？",
        answer="Kubernetes是一个容器编排平台。",
        question_type=QuestionType.REASONING,
        auto_score=0.85,
    )
    result = converter.to_anthropic(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["content"] == "什么是Kubernetes？"
    assert messages[1]["content"] == "Kubernetes是一个容器编排平台。"
    # Verify raw string contains Unicode
    assert "什么是Kubernetes" in result


def test_to_anthropic_all_question_types(converter: DatasetConverter) -> None:
    """Test that to_anthropic() works with all QuestionType values."""
    for question_type in QuestionType:
        record = EvaluationRecord(
            question="Test question",
            answer="Test answer",
            question_type=question_type,
            auto_score=0.8,
        )
        result = converter.to_anthropic(record)
        payload = json.loads(result)

        # Should produce valid JSON regardless of question_type
        assert "system" in payload
        assert "messages" in payload
        assert len(payload["messages"]) == 2


def test_to_anthropic_empty_strings(converter: DatasetConverter) -> None:
    """Test that to_anthropic() handles empty strings gracefully."""
    record = EvaluationRecord(
        question="",
        answer="",
        question_type=QuestionType.CREATIVE,
        auto_score=0.5,
    )
    result = converter.to_anthropic(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["content"] == ""
    assert messages[1]["content"] == ""


def test_to_anthropic_special_characters(converter: DatasetConverter) -> None:
    """Test that to_anthropic() handles special characters correctly."""
    record = EvaluationRecord(
        question='What is "Kubernetes"?',
        answer="It's a container orchestration platform.\nSupports multi-line text.",
        question_type=QuestionType.REASONING,
        auto_score=0.9,
    )
    result = converter.to_anthropic(record)
    payload = json.loads(result)
    messages = payload["messages"]

    assert messages[0]["content"] == 'What is "Kubernetes"?'
    assert messages[1]["content"] == "It's a container orchestration platform.\nSupports multi-line text."

