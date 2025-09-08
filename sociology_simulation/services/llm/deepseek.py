from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from typing import Any

from ...trinity.contracts import ModelCfg, Msg
from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek chat completions provider (networked, with safe fallbacks)."""

    _ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return "{}"

        model = cfg.get("model", "deepseek-chat")  # type: ignore[assignment]
        temperature = float(cfg.get("temperature", 0.0))
        timeout = float(cfg.get("timeout", 8.0))

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "max_tokens": 256,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        def _do_request() -> str:
            req = urllib.request.Request(self._ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    try:
                        data = json.loads(raw)
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content", "")
                            return str(content) if content is not None else "{}"
                    except Exception:
                        pass
                    return raw or "{}"
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
                return "{}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _do_request)
