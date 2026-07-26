import re
from datetime import date, timedelta

from agents.fallbacks import clean_topic_name, looks_like_pdf_noise, resources_for_topic, sanitize_document_text
from agents.llm import LLMJSONClient
from models.schemas import StudyDay, Topic


DEFAULT_TOPICS = [
    ("Arrays and Strings", ["Two pointers", "Sliding window", "Hash maps"]),
    ("Trees and Binary Search Trees", ["Binary Trees", "Traversals", "BST operations"]),
    ("Hashing and Graphs", ["Hash functions", "Graph traversal", "Shortest paths"]),
    ("Dynamic Programming", ["Recurrence", "Memoization", "Tabulation"]),
    ("Operating Systems", ["Processes", "Scheduling", "Memory management"]),
    ("DBMS and SQL", ["Normalization", "Joins", "Transactions"]),
]

CONCEPT_CATALOG: list[tuple[str, list[str]]] = [
    ("Arrays", ["array", "arrays", "two pointer", "sliding window"]),
    ("Linked Lists", ["linked list", "singly linked", "doubly linked"]),
    ("Stacks and Queues", ["stack", "stacks", "queue", "queues"]),
    ("Trees", ["binary tree", "binary search tree", "tree traversal", "trees"]),
    ("Graphs", ["graph traversal", "breadth first", "depth first", "graphs"]),
    ("Sorting and Searching", ["sorting", "searching", "binary search", "merge sort", "quick sort"]),
    ("Dynamic Programming", ["dynamic programming", "memoization", "tabulation"]),
    ("Algorithm Complexity", ["time complexity", "space complexity", "big o", "complexity analysis"]),
    ("Database Fundamentals", ["database management", "dbms architecture", "data models"]),
    ("Relational Model and Algebra", ["relational model", "relational algebra", "relational calculus"]),
    ("SQL", [" sql ", "structured query language", "ddl", "dml", "subqueries"]),
    ("Normalization", ["normalization", "normalisation", "functional dependency", "normal form"]),
    ("Transactions and Concurrency", ["transaction", "acid", "concurrency control", "serializability", "locking"]),
    ("Indexing and Query Processing", ["indexing", "b tree", "b+ tree", "query processing", "query optimization"]),
    ("Sets and Relations", ["sets", "relations", "functions"]),
    ("Algebra", ["quadratic", "sequence", "series", "binomial", "permutation", "combination"]),
    ("Calculus", ["limits", "continuity", "differentiation", "integration", "derivative"]),
    ("Coordinate Geometry", ["coordinate geometry", "straight line", "circle", "parabola", "ellipse", "hyperbola"]),
    ("Vectors and 3D Geometry", ["vectors", "three dimensional", "3d geometry"]),
    ("Probability and Statistics", ["probability", "statistics", "random variable"]),
]

SYSTEM_PLAN_PROMPT = """You create practical exam study plans as JSON only.
Return one JSON object with keys: topics, plan.
topics is an array of objects with name, subtopics, weightage, difficulty, estimated_hours.
plan is an array of days. Each day has day, date, sessions. Each session has topic, subtopic, hours, activity, priority, focus_points.
Use the learner's syllabus and notes. Ignore PDF object syntax, page metadata, font names, broken encodings, headers, footers, and duplicated extraction artifacts.
Every day should contain a concrete daily topic, important concepts, most-asked practice, and quiz revision."""

SYSTEM_TOPIC_PROMPT = """Extract academic topics from the supplied document text.
Return only a JSON array of objects with: name, subtopics, weightage, difficulty, estimated_hours.
Names must be concrete concepts explicitly supported by the document, such as Arrays, Trees, Normalization, or Transactions.
Never use Easy, Medium, Hard, Beginner, Intermediate, Advanced, Unit, Module, or Day as a topic name.
Put difficulty only in the difficulty field. Do not invent a different academic subject."""

INVALID_TOPIC_NAMES = {"easy", "medium", "hard", "beginner", "intermediate", "advanced", "unit", "module", "day"}
GENERIC_SUBJECT_NAMES = {
    "data structures algorithms", "data structures and algorithms", "database management systems",
    "dbms", "jee mathematics", "mathematics", "computer science", "course syllabus",
}


def _meaningful_topic_name(value: str) -> bool:
    clean = clean_topic_name(value).strip().lower()
    numbered_intro = bool(re.match(r"^(?:unit\s*)?\d+(?:\.\d+)*\s+(?:introduction|overview)\b", clean))
    return len(clean) >= 3 and not numbered_intro and clean not in INVALID_TOPIC_NAMES and clean not in GENERIC_SUBJECT_NAMES and not looks_like_pdf_noise(clean)


def is_concrete_topic(value: str) -> bool:
    return _meaningful_topic_name(value)


def extract_topics_with_llm(syllabus: str, notes: str) -> list[dict]:
    """Use Groq once per unique document (the LLM client cache avoids repeat cost)."""
    source = sanitize_document_text(f"{syllabus}\n{notes}")
    client = LLMJSONClient(max_tokens=2500)
    if not source or not client.available:
        return extract_topics(syllabus, notes)
    prompt = f"Document text:\n{source[:12000]}\n\nExtract at most 12 meaningful topics in document order."
    try:
        raw = client.complete_json(SYSTEM_TOPIC_PROMPT, prompt, temperature=0.1)
        if not isinstance(raw, list):
            return extract_topics(syllabus, notes)
        normalized = _normalize_topic_rows(raw, daily_hours=2)
        return normalized or extract_topics(syllabus, notes)
    except Exception:
        return extract_topics(syllabus, notes)


def _normalize_topic_rows(rows: list, daily_hours: int) -> list[dict]:
    normalized = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = clean_topic_name(str(item.get("name") or ""))
        if not _meaningful_topic_name(name):
            continue
        subtopics = [clean_topic_name(str(value)) for value in item.get("subtopics", []) if _meaningful_topic_name(str(value))]
        normalized.append({
            "name": name,
            "subtopics": subtopics or [name],
            "weightage": float(item.get("weightage") or 10),
            "difficulty": item.get("difficulty") if item.get("difficulty") in {"Easy", "Medium", "Hard"} else "Medium",
            "estimated_hours": max(0.5, float(item.get("estimated_hours") or daily_hours)),
        })
        if len(normalized) >= 12:
            break
    return normalized


def extract_topics(syllabus: str, notes: str) -> list[dict]:
    text = sanitize_document_text(f"{syllabus}\n{notes}")
    catalog_topics = _catalog_topics(text)
    if catalog_topics:
        return catalog_topics
    candidates: list[str] = []
    for line in text.splitlines():
        line = clean_topic_name(line)
        line = re.sub(r"\s+\d+(?:\.\d+)?(?:\s+\d+(?:\.\d+)?){1,}\s*$", "", line).strip()
        if 4 <= len(line) <= 80 and not line.lower().startswith(("page", "http")) and not looks_like_pdf_noise(line):
            candidates.append(line)
    if not candidates:
        for topic, subs in DEFAULT_TOPICS:
            candidates.append(topic)
            candidates.extend(subs)

    topics: list[dict] = []
    seen: set[str] = set()
    for item in candidates:
        parts = re.split(r"[:,-]", item, maxsplit=1)
        topic = clean_topic_name(parts[0])
        if topic.lower() in seen or not _meaningful_topic_name(topic):
            continue
        seen.add(topic.lower())
        subtopic = clean_topic_name(parts[1]) if len(parts) > 1 else topic
        if looks_like_pdf_noise(subtopic):
            subtopic = topic
        topics.append(
            {
                "name": topic,
                "subtopics": [subtopic],
                "weightage": max(5, 100 / max(1, len(candidates[:12]))),
                "difficulty": "Medium",
                "estimated_hours": 2,
            }
        )
        if len(topics) >= 12:
            break
    return topics or [{"name": topic, "subtopics": subs, "weightage": 10, "difficulty": "Medium", "estimated_hours": 2} for topic, subs in DEFAULT_TOPICS]


def _catalog_topics(text: str) -> list[dict]:
    haystack = f" {text.lower()} "
    matches = []
    for name, keywords in CONCEPT_CATALOG:
        hits = [keyword.strip() for keyword in keywords if keyword in haystack]
        if hits:
            matches.append({
                "name": name,
                "subtopics": [hit.title() for hit in hits[:4]],
                "weightage": 10,
                "difficulty": "Medium",
                "estimated_hours": 2,
            })
    if matches:
        weight = 100 / len(matches)
        for item in matches:
            item["weightage"] = weight
    return matches[:12]


def generate_study_plan(syllabus: str, notes: str, exam_date: date, daily_hours: int, max_days: int = 365) -> dict:
    today = date.today()
    days_until_exam = max(1, (exam_date - today).days + 1)
    total_days = days_until_exam if max_days <= 0 else min(max_days, days_until_exam)
    syllabus = sanitize_document_text(syllabus)
    notes = sanitize_document_text(notes)
    extracted_topics = extract_topics_with_llm(syllabus, notes)
    groq_payload = _generate_groq_plan(syllabus, notes, exam_date, daily_hours, total_days, extracted_topics)
    if groq_payload:
        return groq_payload
    return _generate_local_plan(syllabus, notes, today, daily_hours, total_days)


def _generate_groq_plan(syllabus: str, notes: str, exam_date: date, daily_hours: int, total_days: int, extracted_topics: list[dict] | None = None) -> dict | None:
    client = LLMJSONClient(max_tokens=6000)
    if not client.available:
        return None
    today = date.today()
    model_days = min(total_days, 30)
    prompt = (
        f"Today: {today.isoformat()}\nExam date: {exam_date.isoformat()}\n"
        f"Total plan days in the app: {total_days}\nDaily rows to generate now: {model_days}\nDaily study hours: {daily_hours}\n\n"
        f"Cleaned syllabus text:\n{syllabus[:7000] or 'No readable syllabus uploaded.'}\n\n"
        f"Cleaned notes text:\n{notes[:7000] or 'No readable notes uploaded.'}\n\n"
        f"Validated extracted topics (use these for daily topic names):\n{extracted_topics or []}\n\n"
        "Rules:\n"
        "- Generate exactly Daily rows to generate now, dated consecutively from Today.\n"
        "- Keep each day focused on one main topic/subtopic from the syllabus or notes.\n"
        "- Include enough topics/subtopics for the server to continue the daily pattern if Total plan days is larger.\n"
        "- Do not invent topics outside the cleaned syllabus/notes unless both are empty.\n"
        "- Do not use raw PDF tokens such as /F1, obj, ReportLab, xref, stream, catalog, font, resource, or metadata as topics.\n"
        "- focus_points must include specific concept targets and practice goals.\n"
        "- Do not include resources; the server will attach links."
    )
    try:
        raw = client.complete_json(SYSTEM_PLAN_PROMPT, prompt, temperature=0.35)
        if not isinstance(raw, dict):
            return None
        return _normalize_plan_payload(raw, today, daily_hours, total_days, extracted_topics or extract_topics(syllabus, notes))
    except Exception:
        return None


def _normalize_plan_payload(raw: dict, today: date, daily_hours: int, total_days: int, fallback_topics: list[dict] | None = None) -> dict:
    topics = raw.get("topics") if isinstance(raw.get("topics"), list) else []
    normalized_topics = _normalize_topic_rows(topics, daily_hours)
    if not normalized_topics:
        normalized_topics = fallback_topics or extract_topics("", "")

    plan_rows = raw.get("plan") if isinstance(raw.get("plan"), list) else []
    plan = []
    for index in range(total_days):
        source_day = plan_rows[index] if index < len(plan_rows) and isinstance(plan_rows[index], dict) else {}
        source_sessions = source_day.get("sessions") if isinstance(source_day.get("sessions"), list) else []
        source_session = source_sessions[0] if source_sessions and isinstance(source_sessions[0], dict) else {}
        topic = clean_topic_name(str(source_session.get("topic") or normalized_topics[index % len(normalized_topics)]["name"]))
        subtopic = clean_topic_name(str(source_session.get("subtopic") or topic))
        if not _meaningful_topic_name(topic):
            topic = normalized_topics[index % len(normalized_topics)]["name"]
        if not _meaningful_topic_name(subtopic):
            subtopic = topic
        focus_points = source_session.get("focus_points") if isinstance(source_session.get("focus_points"), list) else []
        focus = [str(point).strip() for point in focus_points if str(point).strip()][:4]
        if len(focus) < 3:
            focus.extend(
                [
                    f"Master the core definitions and examples for {subtopic}.",
                    f"Solve important practice problems from {topic}.",
                    "Finish quizzes and review every wrong answer before ending the day.",
                ][: 3 - len(focus)]
            )
        session = {
            "topic": topic,
            "subtopic": subtopic,
            "hours": float(source_session.get("hours") or daily_hours),
            "activity": str(source_session.get("activity") or "Concept review, practice problems, and quiz revision"),
            "priority": source_session.get("priority") if source_session.get("priority") in {"High", "Medium", "Low"} else ("High" if index < 7 else "Medium"),
            "focus_points": focus,
            "resources": resources_for_topic(topic, subtopic),
        }
        plan.append({"day": index + 1, "date": (today + timedelta(days=index)).isoformat(), "sessions": [session]})

    hours_per_topic: dict[str, float] = {}
    for day in plan:
        for session in day["sessions"]:
            hours_per_topic[session["topic"]] = hours_per_topic.get(session["topic"], 0) + float(session["hours"])
    return {
        "plan": [StudyDay.model_validate(day).model_dump(mode="json") for day in plan],
        "topics": [Topic.model_validate(topic).model_dump(mode="json") for topic in normalized_topics],
        "total_days": total_days,
        "hours_per_topic": hours_per_topic,
    }


def _generate_local_plan(syllabus: str, notes: str, today: date, daily_hours: int, total_days: int) -> dict:
    topics = extract_topics(syllabus, notes)
    plan = []
    for index in range(total_days):
        topic = topics[index % len(topics)]
        subtopics = topic.get("subtopics") or [topic["name"]]
        subtopic = subtopics[index % len(subtopics)]
        day_date = today + timedelta(days=index)
        plan.append(
            {
                "day": index + 1,
                "date": day_date.isoformat(),
                "sessions": [
                    {
                        "topic": topic["name"],
                        "subtopic": subtopic,
                        "hours": float(daily_hours),
                        "activity": "Concept review, most-asked practice, and quiz revision",
                        "priority": "High" if index < 7 else "Medium",
                        "focus_points": [
                            f"Master the definitions and patterns for {subtopic}.",
                            f"Solve the most repeated interview/exam questions from {topic['name']}.",
                            "Finish 3 quizzes and review each wrong answer before ending the day.",
                        ],
                        "resources": resources_for_topic(topic["name"], subtopic),
                    }
                ],
            }
        )
    hours_per_topic: dict[str, float] = {}
    for day in plan:
        for session in day["sessions"]:
            hours_per_topic[session["topic"]] = hours_per_topic.get(session["topic"], 0) + float(session["hours"])
    return {"plan": plan, "topics": topics, "total_days": total_days, "hours_per_topic": hours_per_topic}
