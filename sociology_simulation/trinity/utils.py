from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable


def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
        return {}


def run_async(awaitable: Awaitable[str], *, timeout: float) -> str:
    """Run an awaitable to completion with a timeout and return its string result.

    If any exception occurs (including timeout), returns an empty JSON object string.
    This synchronous helper is intended for use from non-async contexts.
    """
    try:
        return asyncio.run(asyncio.wait_for(awaitable, timeout=timeout))
    except Exception:
        return "{}"

