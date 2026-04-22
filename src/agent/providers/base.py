from typing import Protocol

from src.common.types import ProviderRequest


class ModelProvider(Protocol):
    def generate(self, request: ProviderRequest) -> str: ...
