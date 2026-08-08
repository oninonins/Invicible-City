import logging
from typing import Any

import requests

from app.ai.base import LLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
    ) -> None:
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = base_url or settings.OPENROUTER_BASE_URL

    def generate_narrative(self, prompt: str, **kwargs: Any) -> str | None:
        if not self.api_key:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if isinstance(content, str) else None
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning("OpenRouter narrative generation failed: %s", exc)
            return None
