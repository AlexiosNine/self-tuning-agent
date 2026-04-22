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
