from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    @property
    def base_url(self) -> str:
        return settings.llm_base_url.rstrip("/")

    @property
    def token(self) -> str:
        return settings.llm_api_token

    @property
    def timeout(self) -> float:
        return settings.llm_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def query(self, prompt: str, metadata: dict | None = None) -> str:
        if not self.token:
            raise RuntimeError("LLM_API_TOKEN is not configured")

        payload: dict = {"prompt": prompt}
        if metadata:
            payload["metadata"] = metadata

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/llm/query",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return _extract_text(data)


def _extract_text(data: object) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("response", "text", "content", "answer", "output", "result"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, dict):
                nested = _extract_text(value)
                if nested:
                    return nested
        content = data.get("content")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif isinstance(block, str):
                    parts.append(block)
            joined = "\n".join(p for p in parts if p).strip()
            if joined:
                return joined
    return str(data)


llm_client = LLMClient()
