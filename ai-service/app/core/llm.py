"""OpenAI-compatible LLM client wrapper.

Supports any provider with an OpenAI-compatible API:
  - OpenAI (https://api.openai.com/v1)
  - Ollama (http://localhost:11434/v1)
  - LM Studio (http://localhost:1234/v1)
  - Groq, Together, etc.
"""

import json
import logging
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around OpenAI client for structured JSON output."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI | None:
        if self._client is None and settings.llm_api_key:
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        return self._client

    def structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> dict[str, Any] | None:
        """Call the LLM and parse the response as JSON.

        Returns a dict on success, None on failure.
        """
        c = self.client
        if c is None:
            logger.warning("LLM not configured — skipping structured call")
            return None

        try:
            resp = c.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            if not content:
                logger.warning("LLM returned empty response")
                return None
            # Strip markdown code fences if present (common with local models)
            cleaned = content.strip()
            if cleaned.startswith("```"):
                # Remove opening fence (```json or ```)
                first_newline = cleaned.find("\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1:]
                # Remove closing fence
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            return json.loads(cleaned)
        except Exception:
            logger.warning("LLM call failed", exc_info=True)
            return None