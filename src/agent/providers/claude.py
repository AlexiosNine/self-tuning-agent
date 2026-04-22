import anthropic
from anthropic import Anthropic
from anthropic.types import TextBlock
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.exceptions import ProviderError
from src.common.logger import setup_logger
from src.common.types import ProviderRequest

logger = setup_logger(__name__)


class ClaudeProvider:
    def __init__(self, client: Anthropic) -> None:
        self.client = client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIStatusError, anthropic.APIConnectionError)),
        reraise=True,
    )
    def generate(self, request: ProviderRequest) -> str:
        logger.info("Calling Claude API: model=%s", request.model_name)
        try:
            response = self.client.messages.create(
                model=request.model_name,
                max_tokens=512,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
            )
            first_block = response.content[0]
            if isinstance(first_block, TextBlock):
                text: str = first_block.text
                logger.info("Claude response: %d chars", len(text))
                return text
            raise ProviderError("Unexpected response format: no TextBlock")
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            logger.warning("Claude API error, will retry")
            raise
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling Claude: %s", e)
            raise ProviderError(f"Provider call failed: {e}") from e
