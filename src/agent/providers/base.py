from typing import Protocol

from src.common.types import ProviderRequest


class ModelProvider(Protocol):
    async def generate(self, request: ProviderRequest) -> tuple[str, int, int]: ...
