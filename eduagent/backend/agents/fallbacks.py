import os
import re
from urllib.parse import quote_plus


PDF_NOISE_TOKENS = {
    "obj", "endobj", "xref", "trailer", "startxref", "stream", "endstream", "reportlab", "catalog",
    "font", "fontdescriptor", "mediabox", "procset", "flatedecode", "type1", "helvetica", "encoding",
    "winansiencoding", "pdfdocument", "cross-reference", "resources", "pages", "page", "parent",
    "root", "info", "creator", "producer", "creationdate", "moddate", "length", "filter", "subtype",
}

CURRICULUM_HEADER_PATTERNS = {
    "b.tech", "b tech", "semester", "semest", "credits", "lectures/week", "lecture/week",
    "tutorials/week", "tutorial/week", "lab/week", "total hours", "course code", "course title",
    "contact hours", "l-t-p", "ltp", "internal marks", "external marks", "maximum marks",
    "subject code", "scheme", "department", "computer science semester",
    "exam duration", "course outcome", "course outcomes", "learning outcome", "learning outcomes",
    "course objective", "course objectives", "upon completing", "students will be able",
    "student will be able", "maximum duration", "end semester", "internal assessment",
}


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


def looks_like_pdf_noise(value: str) -> bool:
    compact = value.strip().lower()
    if not compact:
        return True
    if any(pattern in compact for pattern in CURRICULUM_HEADER_PATTERNS):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?\s*(?:hours?|hrs?)", compact):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?", compact):
        return True
    if any(token in compact for token in ("/f1", "/f2", "/type", "/font", " obj", "xref", "reportlab generated pdf")):
        return True
    words = re.findall(r"[a-zA-Z]+", compact)
    if not words:
        return True
    noise_hits = sum(1 for word in words if word in PDF_NOISE_TOKENS)
    digit_count = sum(1 for char in compact if char.isdigit())
    letter_count = sum(1 for char in compact if char.isalpha())
    symbol_count = sum(1 for char in compact if not char.isalnum() and not char.isspace())
    if noise_hits >= 2:
        return True
    if letter_count and digit_count > letter_count * 1.4:
        return True
    if symbol_count > max(8, letter_count):
        return True
    if len(compact) > 160 and noise_hits:
        return True
    return False


def sanitize_document_text(value: str) -> str:
    lines = []
    for raw_line in value.replace("\x00", " ").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if len(line) < 3:
            continue
        if looks_like_pdf_noise(line):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned[:120_000]


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
