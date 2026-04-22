from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class QuestionType(StrEnum):
    FACTUAL = "factual"
    REASONING = "reasoning"
    CREATIVE = "creative"


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    OFFLINE_EVAL = "offline_eval"
    CANARY = "canary"
    PRODUCTION = "production"
    REJECTED = "rejected"
    ROLLBACK = "rollback"


class StrategyVersion(BaseModel):
    version_id: str
    status: StrategyStatus
    parent_version: str | None = None


class EvaluationRecord(BaseModel):
    question: str
    answer: str
    question_type: QuestionType
    auto_score: float = Field(ge=0.0, le=1.0)
    human_label: str | None = None
    user_feedback: str | None = None


class AnswerResult(BaseModel):
    answer: str
    strategy_version: str
    model_name: str


class ScoreResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reason: str


class ProviderRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    model_name: str


class Evaluator(Protocol):
    def evaluate(self, question: str, answer: str, question_type: QuestionType) -> ScoreResult: ...
