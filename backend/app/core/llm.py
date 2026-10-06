import json
import logging
import re
import time
from functools import lru_cache

import httpx

from app.core.config import settings

log = logging.getLogger("app.llm")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 20


class LLMUnavailable(Exception):
    pass


def _post(provider: str, url: str, headers: dict, payload: dict) -> dict:
    last = "unknown error"
    for attempt in range(2):
        started = time.time()
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except httpx.HTTPError as e:
            last = type(e).__name__
        else:
            ms = int((time.time() - started) * 1000)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"status {r.status_code}"
            elif r.status_code >= 400:
                log.warning("llm provider=%s status=%s latency_ms=%s", provider, r.status_code, ms)
                raise LLMUnavailable(f"{provider} returned {r.status_code}")
            else:
                log.info("llm provider=%s status=%s latency_ms=%s", provider, r.status_code, ms)
                return r.json()
        if attempt == 0:
            time.sleep(1)
    raise LLMUnavailable(f"{provider} failed: {last}")


def _groq(system: str, user: str, json_mode: bool, temperature: float) -> str:
    payload = {
        "model": settings.groq_model,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = _post("groq", GROQ_URL, {"Authorization": f"Bearer {settings.groq_api_key}"}, payload)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise LLMUnavailable("groq malformed response")


def _gemini(system: str, user: str, json_mode: bool, temperature: float) -> str:
    gen = {"temperature": temperature}
    if json_mode:
        gen["responseMimeType"] = "application/json"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    url = GEMINI_URL.format(model=settings.gemini_model)
    data = _post("gemini", url, {"x-goog-api-key": settings.gemini_api_key}, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except (KeyError, IndexError, TypeError):
        raise LLMUnavailable("gemini malformed response")


def _call(system: str, user: str, json_mode: bool, temperature: float) -> str:
    errors = []
    for name, key, fn in (("groq", settings.groq_api_key, _groq), ("gemini", settings.gemini_api_key, _gemini)):
        if not key:
            continue
        try:
            return fn(system, user, json_mode, temperature)
        except LLMUnavailable as e:
            errors.append(str(e))
    raise LLMUnavailable("; ".join(errors) or "no LLM provider configured")


@lru_cache(maxsize=256)
def _cached(system: str, user: str, json_mode: bool, temperature: float) -> str:
    return _call(system, user, json_mode, temperature)


def complete(system: str, user: str, json_mode: bool = False, temperature: float = 0.2, cache: bool = True) -> str:
    if settings.llm_mock:
        return "[mock] " + user[:80]
    if not (settings.groq_api_key or settings.gemini_api_key):
        raise LLMUnavailable("no LLM provider configured")
    if cache and temperature <= 0.3:
        return _cached(system, user, json_mode, temperature)
    return _call(system, user, json_mode, temperature)


def _parse(raw: str):
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def complete_json(system: str, user: str) -> dict:
    if settings.llm_mock:
        raise LLMUnavailable("LLM_MOCK enabled")
    data = _parse(complete(system, user, json_mode=True))
    if data is not None:
        return data
    data = _parse(complete(system, user + "\n\nReturn valid JSON only.", json_mode=True, cache=False))
    if data is None:
        raise LLMUnavailable("LLM returned invalid JSON")
    return data
