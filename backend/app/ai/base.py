from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def generate_narrative(self, prompt: str, **kwargs: Any) -> str | None:
        raise NotImplementedError
