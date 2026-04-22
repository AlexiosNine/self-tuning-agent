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
