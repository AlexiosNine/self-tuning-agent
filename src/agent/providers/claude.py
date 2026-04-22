from anthropic import Anthropic
from anthropic.types import TextBlock

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
        first_block = response.content[0]
        if isinstance(first_block, TextBlock):
            text: str = first_block.text
            return text
        return ""
