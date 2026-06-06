import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import requests


class AgentError(RuntimeError):
    pass


class LLMJSONClient:
    def __init__(self, max_tokens: int = 2048) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower()
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.max_tokens = max_tokens
        self.daily_limit = int(os.getenv("LLM_DAILY_LIMIT", "100"))
        self.cache_enabled = os.getenv("LLM_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
        self.cache_dir = Path(".llm_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.usage_file = self.cache_dir / "usage.json"

    @property
    def available(self) -> bool:
        return self.provider == "groq" and bool(self.api_key)

    def _cache_key(self, system_prompt: str, user_prompt: str, temperature: float) -> Path:
        payload = json.dumps(
            {"model": self.model, "system": system_prompt, "user": user_prompt, "temperature": temperature},
            sort_keys=True,
        )
        return self.cache_dir / f"{hashlib.sha256(payload.encode()).hexdigest()}.json"

    def _usage(self) -> dict[str, Any]:
        today = date.today().isoformat()
        if self.usage_file.exists():
            try:
                usage = json.loads(self.usage_file.read_text())
            except json.JSONDecodeError:
                usage = {}
        else:
            usage = {}
        if usage.get("date") != today:
            usage = {"date": today, "requests_used": 0}
        return usage

    def _write_usage(self, usage: dict[str, Any]) -> None:
        self.usage_file.write_text(json.dumps(usage, indent=2))

    def usage_status(self) -> dict[str, Any]:
        usage = self._usage()
        return {
            "date": usage["date"],
            "provider": self.provider.upper(),
            "model": self.model,
            "daily_limit": self.daily_limit,
            "requests_used": int(usage.get("requests_used", 0)),
            "requests_remaining": max(0, self.daily_limit - int(usage.get("requests_used", 0))),
        }

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.25) -> str:
        if not self.available:
            raise AgentError("Groq API key is not configured.")

        cache_path = self._cache_key(system_prompt, user_prompt, temperature)
        if self.cache_enabled and cache_path.exists():
            try:
                return json.loads(cache_path.read_text())["content"]
            except Exception:
                pass

        usage = self._usage()
        if int(usage.get("requests_used", 0)) >= self.daily_limit:
            raise AgentError("Daily Groq request budget exhausted.")

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": self.max_tokens,
            },
            timeout=45,
        )
        usage["requests_used"] = int(usage.get("requests_used", 0)) + 1
        self._write_usage(usage)
        if response.status_code >= 400:
            raise AgentError(response.text[:500])
        content = response.json()["choices"][0]["message"]["content"].strip()
        if self.cache_enabled:
            cache_path.write_text(json.dumps({"content": content}))
        return content

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.25) -> Any:
        content = self.complete(system_prompt, user_prompt, temperature)
        start = content.find("{")
        arr = content.find("[")
        if arr != -1 and (start == -1 or arr < start):
            start = arr
        end = max(content.rfind("}"), content.rfind("]"))
        if start == -1 or end == -1:
            raise AgentError("Model did not return JSON.")
        return json.loads(content[start : end + 1])


def get_usage_status() -> dict[str, Any]:
    return LLMJSONClient().usage_status()
