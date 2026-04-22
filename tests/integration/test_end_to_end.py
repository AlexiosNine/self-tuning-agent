"""End-to-end integration tests for the self-tuning QA agent.

Tests the complete flow: runtime → evaluation → harness → dataset.
"""

import json
from pathlib import Path

from src.agent.runtime import AgentRuntime
from src.common.types import QuestionType
from src.dataset.builder import DatasetBuilder
from src.evaluation.engine import EvaluationEngine
from src.harness.orchestrator import HarnessOrchestrator

from tests.conftest import FakeProvider


class TestEndToEndHappyPath:
    """Happy path: good answer → high score → dataset export → no optimization."""

    def test_full_flow_good_answer_skips_optimization(
        self,
        agent_runtime: AgentRuntime,
        evaluation_engine: EvaluationEngine,
        harness_orchestrator: HarnessOrchestrator,
        dataset_builder: DatasetBuilder,
    ) -> None:
        # Step 1: Agent answers a factual question
        answer_result = agent_runtime.answer("What is Docker?")
        assert "docker" in answer_result.answer.lower()
        assert "container" in answer_result.answer.lower()
        assert answer_result.strategy_version == "v001"

        # Step 2: Evaluation engine scores the answer
        eval_record = evaluation_engine.evaluate(
            question="What is Docker?",
            answer=answer_result.answer,
        )
        assert eval_record.question_type is QuestionType.FACTUAL
        assert eval_record.auto_score == 1.0

        # Step 3: Orchestrator decides NOT to optimize (score is high)
        new_version = harness_orchestrator.maybe_optimize([eval_record])
        assert new_version is None

        # Step 4: Dataset builder exports the high-quality record
        output_path = dataset_builder.build_generic_dataset([eval_record])
        lines = output_path.read_text().splitlines()
        assert len(lines) == 1
        exported = json.loads(lines[0])
        assert exported["question"] == "What is Docker?"
        assert exported["answer"] == answer_result.answer
        assert exported["metadata"]["auto_eval_score"] == 1.0

    def test_runtime_answer_flows_through_evaluation(
        self,
        agent_runtime: AgentRuntime,
        evaluation_engine: EvaluationEngine,
    ) -> None:
        result = agent_runtime.answer("What is Docker?")
        record = evaluation_engine.evaluate(question="What is Docker?", answer=result.answer)

        assert record.question == "What is Docker?"
        assert record.answer == result.answer
        assert record.auto_score >= 0.8

    def test_high_score_record_passes_dataset_quality_filter(
        self,
        agent_runtime: AgentRuntime,
        evaluation_engine: EvaluationEngine,
        dataset_builder: DatasetBuilder,
    ) -> None:
        result = agent_runtime.answer("What is Docker?")
        record = evaluation_engine.evaluate(question="What is Docker?", answer=result.answer)

        output_path = dataset_builder.build_generic_dataset([record])
        lines = output_path.read_text().splitlines()

        # Score is 1.0 and answer is long enough -> should be exported
        assert len(lines) == 1


class TestEndToEndLowScore:
    """Low score path: bad answer → low score → optimization triggered → no dataset export."""

    def test_low_score_triggers_optimization(
        self,
        version_manager,
        evaluation_engine: EvaluationEngine,
        harness_orchestrator: HarnessOrchestrator,
        dataset_builder: DatasetBuilder,
        strategies_dir: Path,
    ) -> None:
        # Use a provider that gives a bad answer (no keywords)
        bad_provider = FakeProvider(answer="It is a software tool.")
        runtime = AgentRuntime(version_manager=version_manager, provider=bad_provider, model_name="test-model")

        result = runtime.answer("What is Docker?")
        record = evaluation_engine.evaluate(question="What is Docker?", answer=result.answer)

        # Score should be low (0.3) because answer lacks "docker" and "container"
        assert record.auto_score < 0.6

        # Orchestrator should trigger optimization
        new_version = harness_orchestrator.maybe_optimize([record])
        assert new_version == "v002"
        assert (strategies_dir / "v002" / "prompt.yaml").exists()

        # Dataset builder should NOT export (score < 0.8)
        output_path = dataset_builder.build_generic_dataset([record])
        lines = output_path.read_text().splitlines()
        assert lines == []


class TestEndToEndMultipleQuestions:
    """Multiple questions flow through the pipeline together."""

    def test_mixed_scores_partial_export(
        self,
        version_manager,
        evaluation_engine: EvaluationEngine,
        dataset_builder: DatasetBuilder,
    ) -> None:
        good_provider = FakeProvider(answer="Docker is a container platform used to package applications.")
        good_runtime = AgentRuntime(version_manager=version_manager, provider=good_provider, model_name="test-model")

        bad_provider = FakeProvider(answer="I don't know.")
        bad_runtime = AgentRuntime(version_manager=version_manager, provider=bad_provider, model_name="test-model")

        good_result = good_runtime.answer("What is Docker?")
        bad_result = bad_runtime.answer("What is Docker?")

        good_record = evaluation_engine.evaluate(question="What is Docker?", answer=good_result.answer)
        bad_record = evaluation_engine.evaluate(question="What is Docker?", answer=bad_result.answer)

        # Only the good record should be exported
        output_path = dataset_builder.build_generic_dataset([good_record, bad_record])
        lines = output_path.read_text().splitlines()
        assert len(lines) == 1
        exported = json.loads(lines[0])
        assert exported["metadata"]["auto_eval_score"] == 1.0
