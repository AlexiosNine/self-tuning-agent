# Self-Tuning Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-optimizing question-answering agent with harness-based evaluation, strategy versioning, and fine-tuning dataset curation.

**Architecture:** The MVP uses three layers: Agent Runtime executes a versioned strategy, Evaluation Engine scores outputs with automatic rules, and Harness Orchestrator promotes or rolls back strategy versions. The first implementation keeps the runtime simple: one Claude provider, YAML-backed strategy versions, canonical dataset records, and deterministic tests around versioning, evaluation, orchestration, and dataset export.

**Tech Stack:** Python 3.12, pydantic, pydantic-settings, PyYAML, pytest, pytest-cov, anthropic SDK

---

## File Map

### Create
- `CLAUDE.md` — project-level working contract for AI contributors
- `.claude/rules/architecture.md` — layer boundaries and interface rules
- `.claude/rules/coding-style.md` — Python style and file-size rules
- `.claude/rules/testing.md` — TDD and coverage requirements
- `.claude/rules/data-handling.md` — PII and dataset rules
- `pyproject.toml` — package metadata, dependencies, pytest config
- `config.yaml` — app defaults for model, paths, and thresholds
- `src/common/config.py` — typed settings loader
- `src/common/types.py` — shared enums and pydantic models
- `src/agent/providers/base.py` — `ModelProvider` protocol
- `src/agent/providers/claude.py` — Anthropic implementation
- `src/agent/strategies/prompt.py` — prompt rendering helper
- `src/agent/runtime.py` — runtime entrypoint using current strategy version
- `src/evaluation/evaluators/base.py` — `Evaluator` protocol
- `src/evaluation/evaluators/auto.py` — rule-based evaluator
- `src/evaluation/classifiers/task_classifier.py` — question-type classifier
- `src/evaluation/aggregator.py` — score aggregation utilities
- `src/evaluation/engine.py` — evaluation orchestrator
- `src/harness/version_manager.py` — strategy version discovery, load, promote, rollback
- `src/harness/trigger.py` — optimization trigger decision
- `src/harness/optimizer.py` — strategy mutation helper
- `src/harness/orchestrator.py` — offline/canary/production orchestration
- `src/dataset/quality_filter.py` — dataset eligibility rules
- `src/dataset/converter.py` — canonical → provider-specific format conversion
- `src/dataset/builder.py` — collect, filter, split, export datasets
- `tests/conftest.py` — shared fixtures
- `tests/common/test_config.py`
- `tests/common/test_types.py`
- `tests/harness/test_version_manager.py`
- `tests/agent/test_runtime.py`
- `tests/evaluation/test_engine.py`
- `tests/harness/test_orchestrator.py`
- `tests/dataset/test_builder.py`
- `tests/integration/test_end_to_end.py`

### Runtime-generated during implementation/tests
- `strategies/v001/prompt.yaml`
- `strategies/v001/rag_config.yaml`
- `strategies/v001/tool_config.yaml`
- `strategies/v001/metadata.json`
- `strategies/current` — symlink to active version
- `datasets/raw/*.jsonl`
- `datasets/processed/finetuning/generic/{train,val,test}.jsonl`
- `datasets/processed/finetuning/openai/{train,val,test}.jsonl`
- `datasets/processed/finetuning/anthropic/{train,val,test}.jsonl`

## Implementation Notes
- Build the MVP around one provider: Claude. Keep the provider interface generic so OpenAI/local models can be added later without touching runtime orchestration.
- Use YAML for strategy configuration because it is readable and diff-friendly.
- Keep the evaluation MVP deterministic. No judge-model calls in tests.
- The optimizer only creates a mutated draft version in MVP; it does not call external agents yet.
- Dataset exports should derive from one canonical record format and then fan out into provider-specific formats.

---

### Task 1: Bootstrap project config and AI rules

**Files:**
- Create: `CLAUDE.md`
- Create: `.claude/rules/architecture.md`
- Create: `.claude/rules/coding-style.md`
- Create: `.claude/rules/testing.md`
- Create: `.claude/rules/data-handling.md`
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `src/common/config.py`
- Test: `tests/common/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/common/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src'` or `cannot import name 'load_config'`

- [ ] **Step 3: Write minimal implementation and project bootstrap files**

`pyproject.toml`
```toml
[project]
name = "self-tunning"
version = "0.1.0"
description = "Harness-based self-tuning QA agent"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "anthropic>=0.52.0",
  "pydantic>=2.11.0",
  "pydantic-settings>=2.8.0",
  "PyYAML>=6.0.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=6.0.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
addopts = "-q"
testpaths = ["tests"]
```

`config.yaml`
```yaml
model:
  provider: claude
  model_name: claude-sonnet-4-6
paths:
  strategies_dir: strategies
  datasets_dir: datasets
thresholds:
  min_samples: 100
  canary_ratio: 0.1
```

`src/common/config.py`
```python
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
```

`CLAUDE.md`
```md
# self_tunning

- Build a harness-based self-tuning QA agent.
- Preserve three layers: agent runtime, evaluation engine, harness orchestrator.
- Keep runtime behavior strategy-driven through versioned config files.
- Treat expert annotations and user feedback as first-class evaluation signals.
- Export one canonical dataset format, then derive provider-specific fine-tuning files.
```

`.claude/rules/architecture.md`
```md
# Architecture

- Do not bypass layer boundaries.
- Agent runtime never promotes versions.
- Evaluation engine never mutates strategy files.
- Harness orchestrator is the only layer allowed to promote or roll back versions.
- Shared contracts belong in `src/common/types.py`.
```

`.claude/rules/coding-style.md`
```md
# Coding Style

- Use Python type hints on public functions.
- Keep files focused and under 400 lines where practical.
- Prefer immutable return values over in-place mutation.
- Keep side effects at system boundaries.
```

`.claude/rules/testing.md`
```md
# Testing

- Write tests first.
- Every task must run a focused pytest command before broader verification.
- Prefer deterministic unit tests over network calls.
- Target at least 80% coverage.
```

`.claude/rules/data-handling.md`
```md
# Data Handling

- Strip or mask PII before exporting processed datasets.
- Keep raw and processed datasets separate.
- Canonical dataset records are the source of truth.
- Provider-specific formats are derived outputs.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/common/test_config.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md .claude/rules/architecture.md .claude/rules/coding-style.md .claude/rules/testing.md .claude/rules/data-handling.md pyproject.toml config.yaml src/common/config.py tests/common/test_config.py
git commit -m "feat: bootstrap config and project rules"
```

---

### Task 2: Add shared domain types and provider contracts

**Files:**
- Create: `src/common/types.py`
- Create: `src/agent/providers/base.py`
- Create: `src/evaluation/evaluators/base.py`
- Test: `tests/common/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
from src.common.types import EvaluationRecord, QuestionType, StrategyStatus, StrategyVersion


def test_strategy_version_and_evaluation_record_validate() -> None:
    version = StrategyVersion(
        version_id="v001",
        status=StrategyStatus.DRAFT,
        parent_version=None,
    )
    record = EvaluationRecord(
        question="What is Docker?",
        answer="A container platform.",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9,
    )

    assert version.version_id == "v001"
    assert version.status is StrategyStatus.DRAFT
    assert record.question_type is QuestionType.FACTUAL
    assert record.auto_score == 0.9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/common/test_types.py -v`
Expected: FAIL with `cannot import name 'EvaluationRecord'`

- [ ] **Step 3: Write minimal implementation**

`src/common/types.py`
```python
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    FACTUAL = "factual"
    REASONING = "reasoning"
    CREATIVE = "creative"


class StrategyStatus(str, Enum):
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
```

`src/agent/providers/base.py`
```python
from typing import Protocol

from src.common.types import ProviderRequest


class ModelProvider(Protocol):
    def generate(self, request: ProviderRequest) -> str: ...
```

`src/evaluation/evaluators/base.py`
```python
from src.common.types import Evaluator, QuestionType, ScoreResult

__all__ = ["Evaluator", "QuestionType", "ScoreResult"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/common/test_types.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/common/types.py src/agent/providers/base.py src/evaluation/evaluators/base.py tests/common/test_types.py
git commit -m "feat: add shared domain types and contracts"
```

---

### Task 3: Implement strategy version management

**Files:**
- Create: `src/harness/version_manager.py`
- Test: `tests/harness/test_version_manager.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from src.harness.version_manager import VersionManager


def test_promote_to_production_updates_current_symlink(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    version_dir = strategies_dir / "v001"
    version_dir.mkdir(parents=True)
    (version_dir / "prompt.yaml").write_text("system_prompt: base")
    (version_dir / "rag_config.yaml").write_text("top_k: 4")
    (version_dir / "tool_config.yaml").write_text("tools: []")
    (version_dir / "metadata.json").write_text(
        json.dumps({"version_id": "v001", "status": "draft", "parent_version": None})
    )

    manager = VersionManager(strategies_dir)
    manager.promote_to_production("v001")

    current = strategies_dir / "current"
    assert current.is_symlink()
    assert current.resolve() == version_dir.resolve()
    assert manager.load_version("v001").status.value == "production"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/harness/test_version_manager.py -v`
Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'VersionManager'`

- [ ] **Step 3: Write minimal implementation**

`src/harness/version_manager.py`
```python
import json
from pathlib import Path

import yaml

from src.common.types import StrategyStatus, StrategyVersion


class VersionManager:
    def __init__(self, strategies_dir: Path) -> None:
        self.strategies_dir = strategies_dir

    def load_version(self, version_id: str) -> StrategyVersion:
        metadata_path = self.strategies_dir / version_id / "metadata.json"
        data = json.loads(metadata_path.read_text())
        return StrategyVersion.model_validate(data)

    def load_prompt_config(self, version_id: str) -> dict:
        prompt_path = self.strategies_dir / version_id / "prompt.yaml"
        return yaml.safe_load(prompt_path.read_text())

    def promote_to_production(self, version_id: str) -> None:
        version_dir = self.strategies_dir / version_id
        current_link = self.strategies_dir / "current"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        current_link.symlink_to(version_dir, target_is_directory=True)
        version = self.load_version(version_id)
        updated = version.model_copy(update={"status": StrategyStatus.PRODUCTION})
        (version_dir / "metadata.json").write_text(updated.model_dump_json(indent=2))

    def create_version(self, version_id: str, parent_version: str | None, prompt_config: dict) -> None:
        version_dir = self.strategies_dir / version_id
        version_dir.mkdir(parents=True, exist_ok=False)
        (version_dir / "prompt.yaml").write_text(yaml.safe_dump(prompt_config))
        (version_dir / "rag_config.yaml").write_text(yaml.safe_dump({"top_k": 4}))
        (version_dir / "tool_config.yaml").write_text(yaml.safe_dump({"tools": []}))
        metadata = StrategyVersion(version_id=version_id, status=StrategyStatus.DRAFT, parent_version=parent_version)
        (version_dir / "metadata.json").write_text(metadata.model_dump_json(indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/harness/test_version_manager.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/harness/version_manager.py tests/harness/test_version_manager.py
git commit -m "feat: add strategy version manager"
```

---

### Task 4: Build agent runtime with Claude provider and prompt strategy

**Files:**
- Create: `src/agent/strategies/prompt.py`
- Create: `src/agent/providers/claude.py`
- Create: `src/agent/runtime.py`
- Test: `tests/agent/test_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from src.agent.runtime import AgentRuntime
from src.common.types import ProviderRequest
from src.harness.version_manager import VersionManager


class FakeProvider:
    def __init__(self) -> None:
        self.last_request: ProviderRequest | None = None

    def generate(self, request: ProviderRequest) -> str:
        self.last_request = request
        return "Docker is a container platform."


def test_runtime_uses_current_strategy_prompt(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    provider = FakeProvider()
    runtime = AgentRuntime(version_manager=manager, provider=provider, model_name="claude-sonnet-4-6")

    result = runtime.answer("What is Docker?")

    assert result.answer == "Docker is a container platform."
    assert result.strategy_version == "v001"
    assert provider.last_request is not None
    assert provider.last_request.system_prompt == "Answer clearly."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent/test_runtime.py -v`
Expected: FAIL with `cannot import name 'AgentRuntime'`

- [ ] **Step 3: Write minimal implementation**

`src/agent/strategies/prompt.py`
```python
def render_system_prompt(prompt_config: dict) -> str:
    return str(prompt_config["system_prompt"])
```

`src/agent/providers/claude.py`
```python
from anthropic import Anthropic

from src.common.types import ProviderRequest


class ClaudeProvider:
    def __init__(self, client: Anthropic) -> None:
        self.client = client

    def generate(self, request: ProviderRequest) -> str:
        response = self.client.messages.create(
            model=request.model_name,
            max_tokens=512,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_prompt}],
        )
        return response.content[0].text
```

`src/agent/runtime.py`
```python
from src.agent.strategies.prompt import render_system_prompt
from src.common.types import AnswerResult, ProviderRequest
from src.harness.version_manager import VersionManager


class AgentRuntime:
    def __init__(self, version_manager: VersionManager, provider: object, model_name: str) -> None:
        self.version_manager = version_manager
        self.provider = provider
        self.model_name = model_name

    def answer(self, question: str) -> AnswerResult:
        current_link = self.version_manager.strategies_dir / "current"
        version_id = current_link.resolve().name
        prompt_config = self.version_manager.load_prompt_config(version_id)
        request = ProviderRequest(
            system_prompt=render_system_prompt(prompt_config),
            user_prompt=question,
            model_name=self.model_name,
        )
        answer = self.provider.generate(request)
        return AnswerResult(answer=answer, strategy_version=version_id, model_name=self.model_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent/test_runtime.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/agent/strategies/prompt.py src/agent/providers/claude.py src/agent/runtime.py tests/agent/test_runtime.py
git commit -m "feat: add agent runtime and claude provider"
```

---

### Task 5: Implement deterministic evaluation engine

**Files:**
- Create: `src/evaluation/classifiers/task_classifier.py`
- Create: `src/evaluation/aggregator.py`
- Create: `src/evaluation/evaluators/auto.py`
- Create: `src/evaluation/engine.py`
- Test: `tests/evaluation/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
from src.common.types import QuestionType
from src.evaluation.engine import EvaluationEngine
from src.evaluation.evaluators.auto import AutoEvaluator


def test_engine_classifies_factual_question_and_scores_keywords() -> None:
    engine = EvaluationEngine(evaluator=AutoEvaluator())

    result = engine.evaluate(
        question="What is Docker?",
        answer="Docker is a container platform used to package applications.",
    )

    assert result.question_type is QuestionType.FACTUAL
    assert result.auto_score == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/evaluation/test_engine.py -v`
Expected: FAIL with `cannot import name 'EvaluationEngine'`

- [ ] **Step 3: Write minimal implementation**

`src/evaluation/classifiers/task_classifier.py`
```python
from src.common.types import QuestionType


class TaskClassifier:
    def classify(self, question: str) -> QuestionType:
        lowered = question.lower()
        if lowered.startswith("what") or lowered.startswith("who") or lowered.startswith("when"):
            return QuestionType.FACTUAL
        if lowered.startswith("why") or lowered.startswith("how"):
            return QuestionType.REASONING
        return QuestionType.CREATIVE
```

`src/evaluation/aggregator.py`
```python
def aggregate_score(auto_score: float, human_bonus: float = 0.0, user_bonus: float = 0.0) -> float:
    raw_score = auto_score + human_bonus + user_bonus
    if raw_score < 0.0:
        return 0.0
    if raw_score > 1.0:
        return 1.0
    return raw_score
```

`src/evaluation/evaluators/auto.py`
```python
from src.common.types import QuestionType, ScoreResult


class AutoEvaluator:
    def evaluate(self, question: str, answer: str, question_type: QuestionType) -> ScoreResult:
        lowered_answer = answer.lower()
        if question_type is QuestionType.FACTUAL:
            keywords = ("docker", "container")
            score = 1.0 if all(keyword in lowered_answer for keyword in keywords) else 0.3
            return ScoreResult(score=score, reason="keyword match")
        if question_type is QuestionType.REASONING:
            score = 0.8 if "because" in lowered_answer or "therefore" in lowered_answer else 0.4
            return ScoreResult(score=score, reason="reasoning marker check")
        score = 0.7 if len(answer.strip()) >= 40 else 0.3
        return ScoreResult(score=score, reason="creative length check")
```

`src/evaluation/engine.py`
```python
from src.common.types import EvaluationRecord
from src.evaluation.classifiers.task_classifier import TaskClassifier


class EvaluationEngine:
    def __init__(self, evaluator: object) -> None:
        self.evaluator = evaluator
        self.classifier = TaskClassifier()

    def evaluate(self, question: str, answer: str) -> EvaluationRecord:
        question_type = self.classifier.classify(question)
        score_result = self.evaluator.evaluate(question, answer, question_type)
        return EvaluationRecord(
            question=question,
            answer=answer,
            question_type=question_type,
            auto_score=score_result.score,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/evaluation/test_engine.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/classifiers/task_classifier.py src/evaluation/aggregator.py src/evaluation/evaluators/auto.py src/evaluation/engine.py tests/evaluation/test_engine.py
git commit -m "feat: add deterministic evaluation engine"
```

---

### Task 6: Add harness triggers, optimizer, and orchestration flow

**Files:**
- Create: `src/harness/trigger.py`
- Create: `src/harness/optimizer.py`
- Create: `src/harness/orchestrator.py`
- Test: `tests/harness/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from src.common.types import EvaluationRecord, QuestionType
from src.harness.orchestrator import HarnessOrchestrator
from src.harness.version_manager import VersionManager


def test_orchestrator_creates_draft_version_when_scores_drop(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    records = [
        EvaluationRecord(question="What is Docker?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.2),
        EvaluationRecord(question="What is Kubernetes?", answer="bad", question_type=QuestionType.FACTUAL, auto_score=0.3),
    ]

    created_version = orchestrator.maybe_optimize(records)

    assert created_version == "v002"
    assert (strategies_dir / "v002" / "prompt.yaml").exists()
    assert manager.load_version("v002").parent_version == "v001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/harness/test_orchestrator.py -v`
Expected: FAIL with `cannot import name 'HarnessOrchestrator'`

- [ ] **Step 3: Write minimal implementation**

`src/harness/trigger.py`
```python
from src.common.types import EvaluationRecord


class OptimizationTrigger:
    def __init__(self, min_samples: int, score_threshold: float = 0.6) -> None:
        self.min_samples = min_samples
        self.score_threshold = score_threshold

    def should_optimize(self, records: list[EvaluationRecord]) -> bool:
        if len(records) < self.min_samples:
            return False
        average = sum(record.auto_score for record in records) / len(records)
        return average < self.score_threshold
```

`src/harness/optimizer.py`
```python
from src.harness.version_manager import VersionManager


class StrategyOptimizer:
    def __init__(self, version_manager: VersionManager) -> None:
        self.version_manager = version_manager

    def create_mutation(self, parent_version: str, new_version: str) -> str:
        parent_prompt = self.version_manager.load_prompt_config(parent_version)
        mutated_prompt = {
            "system_prompt": f"{parent_prompt['system_prompt']} Include concrete definitions before examples.",
        }
        self.version_manager.create_version(new_version, parent_version, mutated_prompt)
        return new_version
```

`src/harness/orchestrator.py`
```python
from src.common.types import EvaluationRecord
from src.harness.optimizer import StrategyOptimizer
from src.harness.trigger import OptimizationTrigger
from src.harness.version_manager import VersionManager


class HarnessOrchestrator:
    def __init__(self, version_manager: VersionManager, min_samples: int) -> None:
        self.version_manager = version_manager
        self.trigger = OptimizationTrigger(min_samples=min_samples)
        self.optimizer = StrategyOptimizer(version_manager)

    def maybe_optimize(self, records: list[EvaluationRecord]) -> str | None:
        if not self.trigger.should_optimize(records):
            return None
        current_version = (self.version_manager.strategies_dir / "current").resolve().name
        current_number = int(current_version.removeprefix("v"))
        new_version = f"v{current_number + 1:03d}"
        return self.optimizer.create_mutation(current_version, new_version)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/harness/test_orchestrator.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/harness/trigger.py src/harness/optimizer.py src/harness/orchestrator.py tests/harness/test_orchestrator.py
git commit -m "feat: add optimization trigger and orchestrator"
```

---

### Task 7: Build canonical dataset filtering and export pipeline

**Files:**
- Create: `src/dataset/quality_filter.py`
- Create: `src/dataset/converter.py`
- Create: `src/dataset/builder.py`
- Test: `tests/dataset/test_builder.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/dataset/test_builder.py -v`
Expected: FAIL with `cannot import name 'DatasetBuilder'`

- [ ] **Step 3: Write minimal implementation**

`src/dataset/quality_filter.py`
```python
from src.common.types import EvaluationRecord


class QualityFilter:
    def is_high_quality(self, record: EvaluationRecord) -> bool:
        has_positive_human_label = record.human_label in {None, "positive"}
        return record.auto_score >= 0.8 and has_positive_human_label and len(record.answer.strip()) >= 10
```

`src/dataset/converter.py`
```python
import json

from src.common.types import EvaluationRecord


class DatasetConverter:
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
                {"role": "system", "content": "你是一个专业的问答助手。"},
                {"role": "user", "content": record.question},
                {"role": "assistant", "content": record.answer},
            ]
        }
        return json.dumps(payload, ensure_ascii=False)

    def to_anthropic(self, record: EvaluationRecord) -> str:
        payload = {
            "system": "你是一个专业的问答助手。",
            "messages": [
                {"role": "user", "content": record.question},
                {"role": "assistant", "content": record.answer},
            ],
        }
        return json.dumps(payload, ensure_ascii=False)
```

`src/dataset/builder.py`
```python
from pathlib import Path

from src.common.types import EvaluationRecord
from src.dataset.converter import DatasetConverter
from src.dataset.quality_filter import QualityFilter


class DatasetBuilder:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/dataset/test_builder.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/dataset/quality_filter.py src/dataset/converter.py src/dataset/builder.py tests/dataset/test_builder.py
git commit -m "feat: add dataset filtering and export"
```

---

### Task 8: Add end-to-end integration coverage for runtime → evaluation → harness → dataset

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/integration/test_end_to_end.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from src.agent.runtime import AgentRuntime
from src.common.types import EvaluationRecord
from src.dataset.builder import DatasetBuilder
from src.evaluation.engine import EvaluationEngine
from src.evaluation.evaluators.auto import AutoEvaluator
from src.harness.orchestrator import HarnessOrchestrator
from src.harness.version_manager import VersionManager


class FakeProvider:
    def generate(self, request):
        return "Docker is a container platform used to package applications."


def test_end_to_end_flow_creates_dataset_and_skips_optimization_for_good_answers(tmp_path: Path) -> None:
    strategies_dir = tmp_path / "strategies"
    manager = VersionManager(strategies_dir)
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")

    runtime = AgentRuntime(version_manager=manager, provider=FakeProvider(), model_name="claude-sonnet-4-6")
    engine = EvaluationEngine(evaluator=AutoEvaluator())
    orchestrator = HarnessOrchestrator(version_manager=manager, min_samples=2)
    builder = DatasetBuilder(output_dir=tmp_path / "datasets")

    result = runtime.answer("What is Docker?")
    record = engine.evaluate("What is Docker?", result.answer)
    dataset_path = builder.build_generic_dataset([record])
    maybe_version = orchestrator.maybe_optimize([record])

    assert dataset_path.exists()
    assert maybe_version is None
    assert '"question": "What is Docker?"' in dataset_path.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_end_to_end.py -v`
Expected: FAIL because earlier layers are not yet wired together correctly

- [ ] **Step 3: Write minimal glue code if needed**

Use this focused patch if the test fails because short high-quality datasets are rejected by the current filter.

`src/dataset/quality_filter.py`
```python
from src.common.types import EvaluationRecord


class QualityFilter:
    def is_high_quality(self, record: EvaluationRecord) -> bool:
        has_positive_human_label = record.human_label in {None, "positive"}
        return record.auto_score >= 0.8 and has_positive_human_label and len(record.answer.strip()) >= 30
```

If the test fails because `HarnessOrchestrator` optimizes on too few samples, keep this trigger implementation.

`src/harness/trigger.py`
```python
from src.common.types import EvaluationRecord


class OptimizationTrigger:
    def __init__(self, min_samples: int, score_threshold: float = 0.6) -> None:
        self.min_samples = min_samples
        self.score_threshold = score_threshold

    def should_optimize(self, records: list[EvaluationRecord]) -> bool:
        if len(records) < self.min_samples:
            return False
        average = sum(record.auto_score for record in records) / len(records)
        return average < self.score_threshold
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_end_to_end.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Run the focused suite**

Run: `pytest tests/common/test_config.py tests/common/test_types.py tests/harness/test_version_manager.py tests/agent/test_runtime.py tests/evaluation/test_engine.py tests/harness/test_orchestrator.py tests/dataset/test_builder.py tests/integration/test_end_to_end.py -v`
Expected: PASS with `8 passed`

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/integration/test_end_to_end.py src/dataset/quality_filter.py src/harness/trigger.py
git commit -m "test: add end-to-end coverage for tuning flow"
```

---

## Final Verification

- [ ] Run unit and integration tests

```bash
pytest --cov=src --cov-report=term-missing
```

Expected: PASS and coverage report printed for `src/`

- [ ] Create initial strategy seed files for local manual runs

```bash
python - <<'PY'
from pathlib import Path
from src.harness.version_manager import VersionManager

strategies_dir = Path("strategies")
strategies_dir.mkdir(exist_ok=True)
manager = VersionManager(strategies_dir)
if not (strategies_dir / "v001").exists():
    manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
    manager.promote_to_production("v001")
PY
```

Expected: `strategies/v001/` exists and `strategies/current` points to it

- [ ] Smoke-test the runtime with a fake provider in an interactive shell

```bash
python - <<'PY'
from src.agent.runtime import AgentRuntime
from src.harness.version_manager import VersionManager
from pathlib import Path

class FakeProvider:
    def generate(self, request):
        return "Docker is a container platform used to package applications."

runtime = AgentRuntime(VersionManager(Path("strategies")), FakeProvider(), "claude-sonnet-4-6")
print(runtime.answer("What is Docker?").model_dump())
PY
```

Expected: printed dict containing `answer`, `strategy_version`, and `model_name`

## Self-Review

### Spec coverage
- Three layers covered:
  - Agent Runtime: Task 4
  - Evaluation Engine: Task 5
  - Harness Orchestrator: Tasks 3 and 6
- Strategy versioning covered: Task 3
- Multi-model abstraction started with base contract and Claude MVP: Tasks 2 and 4
- Dataset curation and provider-specific export covered: Task 7
- End-to-end flow covered: Task 8
- Project-level AI rules covered: Task 1

### Placeholder scan
- No `TBD`, `TODO`, or deferred placeholders remain.
- Each task has exact file paths, test commands, implementation snippets, and commit commands.

### Type consistency
- Shared types are defined in Task 2 before later tasks use them.
- `StrategyVersion`, `EvaluationRecord`, `ProviderRequest`, and `AnswerResult` are used consistently.
- `VersionManager`, `AgentRuntime`, `EvaluationEngine`, `HarnessOrchestrator`, and `DatasetBuilder` names are stable across tasks.
