import time
from datetime import timedelta

import anthropic
from aiobreaker import CircuitBreaker, CircuitBreakerError
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.exceptions import ProviderError
from src.common.logger import setup_logger
from src.common.metrics import (
    circuit_breaker_failures,
    circuit_breaker_state,
    provider_call_latency_seconds,
)
from src.common.types import ProviderRequest

logger = setup_logger(__name__)


class ClaudeProvider:
    def __init__(self, client: AsyncAnthropic, fail_max: int = 5, reset_timeout: int = 60) -> None:
        self.client = client
        self._breaker = CircuitBreaker(
            fail_max=fail_max,
            timeout_duration=timedelta(seconds=reset_timeout),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIStatusError, anthropic.APIConnectionError)),
        reraise=True,
    )
    async def generate(self, request: ProviderRequest) -> tuple[str, int, int]:
        try:
            return await self._breaker.call_async(self._do_generate, request)
        except CircuitBreakerError as e:
            circuit_breaker_failures.inc()
            circuit_breaker_state.labels(state="open").inc()
            logger.error("Circuit breaker open: %s", e)
            raise ProviderError("Circuit breaker open: too many consecutive failures") from e

    async def _do_generate(self, request: ProviderRequest) -> tuple[str, int, int]:
        logger.info("Calling Claude API: model=%s", request.model_name)
        start_time = time.time()
        try:
            response = await self.client.messages.create(
                model=request.model_name,
                max_tokens=512,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
            )

            latency = time.time() - start_time
            provider_call_latency_seconds.labels(model_name=request.model_name).observe(latency)

            # Extract token usage with defensive check
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage") and response.usage:
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            first_block = response.content[0]
            if isinstance(first_block, TextBlock):
                text: str = first_block.text
                logger.info(
                    "Claude response: %d chars, tokens: input=%d output=%d", len(text), input_tokens, output_tokens
                )
                return (text, input_tokens, output_tokens)
            raise ProviderError("Unexpected response format: no TextBlock")
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            logger.warning("Claude API error, will retry")
            raise
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling Claude: %s", e)
            raise ProviderError(f"Provider call failed: {e}") from e
