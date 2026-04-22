import json

from src.common.types import EvaluationRecord


class DatasetConverter:
    """Converts EvaluationRecord to provider-specific JSONL formats.

    Supported formats:
      - generic: canonical format with question, answer, task_type, metadata
      - openai: OpenAI fine-tuning messages format
      - anthropic: Anthropic fine-tuning messages format
    """

    def to_generic(self, record: EvaluationRecord) -> str:
        payload = {
            "question": record.question,
            "answer": record.answer,
            "task_type": record.question_type.value,
            "metadata": {
                "auto_eval_score": record.auto_score,
                "human_annotation": record.human_label,
                "user_feedback": record.user_feedback,
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def to_openai(self, record: EvaluationRecord) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": "You are a professional QA assistant."},
                {"role": "user", "content": record.question},
                {"role": "assistant", "content": record.answer},
            ]
        }
        return json.dumps(payload, ensure_ascii=False)

    def to_anthropic(self, record: EvaluationRecord) -> str:
        payload = {
            "system": "You are a professional QA assistant.",
            "messages": [
                {"role": "user", "content": record.question},
                {"role": "assistant", "content": record.answer},
            ],
        }
        return json.dumps(payload, ensure_ascii=False)
