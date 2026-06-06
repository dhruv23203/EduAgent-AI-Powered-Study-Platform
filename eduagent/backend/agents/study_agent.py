import re
from datetime import date, timedelta

from agents.fallbacks import clean_topic_name, resources_for_topic


DEFAULT_TOPICS = [
    ("Arrays and Strings", ["Two pointers", "Sliding window", "Hash maps"]),
    ("Trees and Binary Search Trees", ["Binary Trees", "Traversals", "BST operations"]),
    ("Hashing and Graphs", ["Hash functions", "Graph traversal", "Shortest paths"]),
    ("Dynamic Programming", ["Recurrence", "Memoization", "Tabulation"]),
    ("Operating Systems", ["Processes", "Scheduling", "Memory management"]),
    ("DBMS and SQL", ["Normalization", "Joins", "Transactions"]),
]


def extract_topics(syllabus: str, notes: str) -> list[dict]:
    text = f"{syllabus}\n{notes}"
    candidates: list[str] = []
    for line in text.splitlines():
        line = clean_topic_name(line)
        if 4 <= len(line) <= 80 and not line.lower().startswith(("page", "http")):
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
        if topic.lower() in seen or len(topic) < 3:
            continue
        seen.add(topic.lower())
        subtopic = clean_topic_name(parts[1]) if len(parts) > 1 else topic
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


def generate_study_plan(syllabus: str, notes: str, exam_date: date, daily_hours: int, max_days: int = 365) -> dict:
    today = date.today()
    days_until_exam = max(1, (exam_date - today).days + 1)
    total_days = days_until_exam if max_days <= 0 else min(max_days, days_until_exam)
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
