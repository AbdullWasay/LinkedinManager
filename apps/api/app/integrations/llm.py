from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# After rate-limits, skip LLM for a short cooldown so bulk outreach can use templates.
_cooldown_until = 0.0


class LLMError(Exception):
    pass


def _trip_cooldown(seconds: float = 120.0) -> None:
    global _cooldown_until
    _cooldown_until = max(_cooldown_until, time.monotonic() + seconds)


def llm_in_cooldown() -> bool:
    return time.monotonic() < _cooldown_until


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def _chat_groq(system: str, user: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise LLMError("GROQ_API_KEY missing")
    payload = {
        "model": settings.groq_model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=12.0) as client:
        res = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if res.status_code == 429:
            _trip_cooldown(180.0)
            raise LLMError("groq rate limited")
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"]


def _chat_gemini(system: str, user: str) -> str:
    settings = get_settings()
    key = settings.effective_gemini_key
    if not key:
        raise LLMError("GEMINI_API_KEY missing")
    model = settings.gemini_model or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.4},
    }
    with httpx.Client(timeout=12.0) as client:
        res = client.post(url, params={"key": key}, json=payload)
        if res.status_code == 429:
            _trip_cooldown(180.0)
            raise LLMError("gemini rate limited")
        res.raise_for_status()
        data = res.json()
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _chat_openai(system: str, user: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY missing")
    payload = {
        "model": settings.openai_model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=12.0) as client:
        res = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if res.status_code == 429:
            _trip_cooldown(180.0)
            raise LLMError("openai rate limited")
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"]


def llm_available() -> bool:
    s = get_settings()
    return bool(s.groq_api_key or s.effective_gemini_key or s.openai_api_key)


def chat_completion(system: str, user: str, *, provider: Optional[str] = None) -> str:
    if llm_in_cooldown():
        raise LLMError("LLM cooldown active after rate limit")

    settings = get_settings()
    order = []
    if provider:
        order = [provider]
    else:
        if settings.groq_api_key:
            order.append("groq")
        if settings.effective_gemini_key:
            order.append("gemini")
        if settings.openai_api_key:
            order.append("openai")
    if not order:
        raise LLMError("No AI API keys configured")

    errors: list[str] = []
    for name in order:
        try:
            if name == "groq":
                return _chat_groq(system, user)
            if name == "gemini":
                return _chat_gemini(system, user)
            if name == "openai":
                return _chat_openai(system, user)
        except Exception as exc:
            logger.warning("LLM provider %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            if "rate limited" in str(exc).lower() or "429" in str(exc):
                break
    raise LLMError("; ".join(errors))


def chat_json(system: str, user: str) -> dict[str, Any]:
    content = chat_completion(
        system + "\nRespond with valid JSON only. No markdown.",
        user,
    )
    return _extract_json(content)
