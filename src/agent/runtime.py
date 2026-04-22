from src.agent.providers.base import ModelProvider
from src.agent.strategies.prompt import render_system_prompt
from src.common.exceptions import VersionNotFoundError
from src.common.logger import setup_logger
from src.common.types import AnswerResult, ProviderRequest
from src.harness.version_manager import VersionManager

logger = setup_logger(__name__)

MAX_QUESTION_LENGTH = 10000


class AgentRuntime:
    def __init__(self, version_manager: VersionManager, provider: ModelProvider, model_name: str) -> None:
        self.version_manager = version_manager
        self.provider = provider
        self.model_name = model_name

    def answer(self, question: str) -> AnswerResult:
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

        answer = self.provider.generate(request)
        logger.info("Generated answer (version=%s, length=%d)", version_id, len(answer))

        return AnswerResult(answer=answer, strategy_version=version_id, model_name=self.model_name)
