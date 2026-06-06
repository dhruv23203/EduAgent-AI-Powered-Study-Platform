import os
import re
from urllib.parse import quote_plus


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def should_use_local_ai() -> bool:
    return env_flag("AI_DEMO_MODE", default=False)


def allow_local_fallback() -> bool:
    return env_flag("AI_ALLOW_LOCAL_FALLBACK", default=True)


def allow_quiz_fallback() -> bool:
    return env_flag("QUIZ_ALLOW_LOCAL_FALLBACK", default=False)


def clean_topic_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 +#./-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80] or "Core Concepts"


def resources_for_topic(topic: str, subtopic: str = "") -> list[dict[str, str]]:
    query = quote_plus(f"{topic} {subtopic} tutorial practice questions".strip())
    label = clean_topic_name(subtopic or topic)
    return [
        {"title": f"Learn {label}", "url": f"https://www.google.com/search?q={query}", "type": "Search"},
        {"title": f"Video lessons for {label}", "url": f"https://www.youtube.com/results?search_query={query}", "type": "Video"},
        {"title": f"Practice {label}", "url": f"https://www.google.com/search?q={query}+practice+problems", "type": "Practice"},
    ]
