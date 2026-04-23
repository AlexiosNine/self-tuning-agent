import time

from src.agent.providers.base import ModelProvider
from src.agent.strategies.prompt import render_system_prompt
from src.common.exceptions import ProviderError, VersionNotFoundError
from src.common.logger import setup_logger
from src.common.metrics import (
    answer_latency_seconds,
    answer_requests_failed,
    answer_requests_total,
    tokens_input_total,
    tokens_output_total,
)
from src.common.types import AnswerResult, ProviderRequest
from src.harness.version_manager import VersionManager

logger = setup_logger(__name__)

MAX_QUESTION_LENGTH = 10000


class AgentRuntime:
    def __init__(self, version_manager: VersionManager, provider: ModelProvider, model_name: str) -> None:
        self.version_manager = version_manager
        self.provider = provider
        self.model_name = model_name

    async def answer(self, question: str) -> AnswerResult:
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Question exceeds {MAX_QUESTION_LENGTH} characters")

        question = question.strip()
        logger.info("Answering question: %s...", question[:80])

        current_link = self.version_manager.strategies_dir / "current"
        if not current_link.exists() and not current_link.is_symlink():
            raise VersionNotFoundError("No production strategy version set")

        version_id = current_link.resolve().name
        prompt_config = self.version_manager.load_prompt_config(version_id)

        request = ProviderRequest(
            system_prompt=render_system_prompt(prompt_config),
            user_prompt=question,
            model_name=self.model_name,
        )

        start_time = time.time()
        try:
            answer, input_tokens, output_tokens = await self.provider.generate(request)
            latency = time.time() - start_time

            answer_requests_total.labels(strategy_version=version_id, model_name=self.model_name).inc()
            answer_latency_seconds.labels(strategy_version=version_id, model_name=self.model_name).observe(latency)
            tokens_input_total.labels(strategy_version=version_id, model_name=self.model_name).inc(input_tokens)
            tokens_output_total.labels(strategy_version=version_id, model_name=self.model_name).inc(output_tokens)

            logger.info("Generated answer (version=%s, length=%d, latency=%.2fs)", version_id, len(answer), latency)

            return AnswerResult(answer=answer, strategy_version=version_id, model_name=self.model_name)
        except ProviderError as e:
            latency = time.time() - start_time
            answer_requests_failed.labels(
                strategy_version=version_id, model_name=self.model_name, error_type="provider_error"
            ).inc()
            answer_latency_seconds.labels(strategy_version=version_id, model_name=self.model_name).observe(latency)
            logger.error("Provider error (version=%s, latency=%.2fs): %s", version_id, latency, e)
            raise
        except Exception as e:
            latency = time.time() - start_time
            answer_requests_failed.labels(
                strategy_version=version_id, model_name=self.model_name, error_type="unexpected_error"
            ).inc()
            answer_latency_seconds.labels(strategy_version=version_id, model_name=self.model_name).observe(latency)
            logger.error("Unexpected error (version=%s, latency=%.2fs): %s", version_id, latency, e)
            raise
