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
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.api_keys = self._load_api_keys()
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.max_tokens = max_tokens
        # One application-wide budget applies to every subscription tier. The
        # legacy name remains a fallback so existing deployments keep working.
        self.daily_limit = int(os.getenv("AI_DAILY_REQUEST_BUDGET", os.getenv("LLM_DAILY_LIMIT", "100")))
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

    def _cooldown_minutes(self, response: requests.Response) -> int:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                seconds = max(1, int(float(retry_after)))
                return max(1, min(60, (seconds + 59) // 60))
            except ValueError:
                pass
        return 45

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
        state = self._key_state()
        cooldowns = state.get("cooldowns") or {}
        limited_slots = []
        for index, key in enumerate(self.api_keys):
            cooldown_until = cooldowns.get(self._key_id(key))
            if cooldown_until and not self._key_available_now(key, state):
                limited_slots.append(index + 1)
        return {
            "date": usage["date"],
            "provider": self.provider.upper(),
            "model": self.model,
            "vision_model": os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b"),
            "daily_limit": self.daily_limit,
            "requests_used": int(usage.get("requests_used", 0)),
            "requests_remaining": max(0, self.daily_limit - int(usage.get("requests_used", 0))),
            "budget_scope": "all_plans",
            "counter_scope": "groq_http_requests_today",
            "api_keys_configured": len(self.api_keys),
            "active_key_slot": int(state.get("active_key") or 0) + 1 if self.api_keys else 0,
            "limited_key_slots": limited_slots,
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

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        content = self._complete_payload(payload)
        if self.cache_enabled:
            cache_path.write_text(json.dumps({"content": content}))
        return content

    def complete_with_images(self, prompt: str, images: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self.available:
            raise AgentError("Groq API key is not configured.")
        if not images:
            return self.complete("You are EduAgent's academic solver.", prompt, temperature)
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images[:5]:
            mime_type = image.get("mime_type") or "image/png"
            data = image.get("base64") or ""
            if data:
                content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{data}"}})
        payload = {
            "model": os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b"),
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        return self._complete_payload(payload)

    def _complete_payload(self, payload: dict[str, Any]) -> str:
        usage = self._usage()
        if int(usage.get("requests_used", 0)) >= self.daily_limit:
            raise AgentError("Daily Groq request budget exhausted.")

        state = self._key_state()
        last_error = ""
        response = None
        attempted_slots: list[int] = []
        limited_slots: list[int] = []
        skipped_slots: list[int] = []
        for index in self._ordered_key_indexes(state):
            key = self.api_keys[index]
            if not self._key_available_now(key, state):
                skipped_slots.append(index + 1)
                continue
            attempted_slots.append(index + 1)
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
                timeout=45,
            )
            usage["requests_used"] = int(usage.get("requests_used", 0)) + 1
            self._write_usage(usage)
            if response.status_code < 400:
                self._mark_key_active(index, state)
                break
            last_error = response.text[:500]
            if self._is_rate_limited(response):
                limited_slots.append(index + 1)
                self._mark_key_limited(key, state, self._cooldown_minutes(response))
                continue
            raise AgentError(last_error)
        if response is None or response.status_code >= 400:
            tried = sorted(set(attempted_slots + skipped_slots + limited_slots))
            detail = f"Tried {len(tried) or len(self.api_keys)} configured Groq API key(s)."
            if limited_slots or skipped_slots:
                detail += f" Limited/cooling key slots: {sorted(set(limited_slots + skipped_slots))}."
            detail += " EduAgent automatically moves to the next configured key when one is rate-limited."
            last = f" Last Groq response: {last_error}" if last_error else ""
            raise AgentError(f"All configured Groq API keys are temporarily unavailable or rate-limited. {detail}{last}")
        content = response.json()["choices"][0]["message"]["content"].strip()
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
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AgentError("Model returned malformed JSON.") from exc


def get_usage_status() -> dict[str, Any]:
    return LLMJSONClient().usage_status()
