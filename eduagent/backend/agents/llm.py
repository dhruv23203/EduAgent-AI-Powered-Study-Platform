import hashlib
import json
import os
from datetime import date
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


class AgentError(RuntimeError):
    pass


class LLMJSONClient:
    def __init__(self, max_tokens: int = 2048) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower()
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.api_keys = self._load_api_keys()
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.max_tokens = max_tokens
        self.daily_limit = int(os.getenv("LLM_DAILY_LIMIT", "100"))
        self.cache_enabled = os.getenv("LLM_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
        self.cache_dir = Path(".llm_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.usage_file = self.cache_dir / "usage.json"
        self.key_state_file = self.cache_dir / "groq_key_state.json"

    @property
    def available(self) -> bool:
        return self.provider == "groq" and bool(self.api_keys)

    def _load_api_keys(self) -> list[str]:
        keys = []
        raw_many = os.getenv("GROQ_API_KEYS", "")
        for value in raw_many.replace("\n", ",").replace(";", ",").split(","):
            if value.strip():
                keys.append(value.strip())
        for name in ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4", "GROQ_API_KEY_5"]:
            value = os.getenv(name, "").strip()
            if value:
                keys.append(value)
        clean_keys = []
        seen = set()
        for key in keys:
            if "your_groq_api_key" in key.lower():
                continue
            if key not in seen:
                seen.add(key)
                clean_keys.append(key)
        return clean_keys

    def _key_id(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def _key_state(self) -> dict[str, Any]:
        if not self.key_state_file.exists():
            return {"active_key": 0, "cooldowns": {}}
        try:
            state = json.loads(self.key_state_file.read_text())
            return state if isinstance(state, dict) else {"active_key": 0, "cooldowns": {}}
        except json.JSONDecodeError:
            return {"active_key": 0, "cooldowns": {}}

    def _write_key_state(self, state: dict[str, Any]) -> None:
        self.key_state_file.write_text(json.dumps(state, indent=2))

    def _key_available_now(self, key: str, state: dict[str, Any]) -> bool:
        cooldown_until = (state.get("cooldowns") or {}).get(self._key_id(key))
        if not cooldown_until:
            return True
        try:
            return datetime.fromisoformat(cooldown_until) <= datetime.now(timezone.utc)
        except ValueError:
            return True

    def _mark_key_limited(self, key: str, state: dict[str, Any], minutes: int = 45) -> None:
        cooldowns = state.setdefault("cooldowns", {})
        cooldowns[self._key_id(key)] = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
        self._write_key_state(state)

    def _mark_key_active(self, index: int, state: dict[str, Any]) -> None:
        state["active_key"] = index
        self._write_key_state(state)

    def _ordered_key_indexes(self, state: dict[str, Any]) -> list[int]:
        count = len(self.api_keys)
        if count == 0:
            return []
        start = int(state.get("active_key") or 0) % count
        return list(range(start, count)) + list(range(0, start))

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
            "api_keys_configured": len(self.api_keys),
            "active_key_slot": int(self._key_state().get("active_key") or 0) + 1 if self.api_keys else 0,
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

        state = self._key_state()
        last_error = ""
        response = None
        for index in self._ordered_key_indexes(state):
            key = self.api_keys[index]
            if not self._key_available_now(key, state):
                continue
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
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
            if response.status_code < 400:
                self._mark_key_active(index, state)
                break
            last_error = response.text[:500]
            if self._is_rate_limited(response):
                self._mark_key_limited(key, state)
                continue
            raise AgentError(last_error)
        if response is None or response.status_code >= 400:
            raise AgentError(last_error or "All configured Groq API keys are temporarily unavailable or rate-limited.")
        content = response.json()["choices"][0]["message"]["content"].strip()
        if self.cache_enabled:
            cache_path.write_text(json.dumps({"content": content}))
        return content

    def _is_rate_limited(self, response: requests.Response) -> bool:
        text = response.text.lower()
        return response.status_code == 429 or "rate_limit" in text or "rate limit" in text or "tokens per day" in text

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
