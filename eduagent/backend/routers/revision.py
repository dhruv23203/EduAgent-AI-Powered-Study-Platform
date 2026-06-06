import json
from collections import defaultdict
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.fallbacks import resources_for_topic
from agents.llm import LLMJSONClient
from agents.weakness_agent import WeaknessAgent, feedback_items, groq_progress_feedback, mistake_insights
from db.database import get_db
from db.models import QuizAttempt, Student, StudyPlan
from models.schemas import FeedbackItem, RevisionResponse, StudyDay
from utils.timezone import local_date, local_today

router = APIRouter(prefix="/api/revision", tags=["revision"])


@router.get("/{student_id}", response_model=RevisionResponse)
def get_revision(student_id: str, db: Session = Depends(get_db)) -> RevisionResponse:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    today = local_today()
    yesterday = today - timedelta(days=1)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).order_by(QuizAttempt.attempted_at.desc()).all()
    past_attempts = [attempt for attempt in attempts if local_date(attempt.attempted_at) < today]
    yesterday_attempts = [attempt for attempt in past_attempts if local_date(attempt.attempted_at) == yesterday]
    source_attempts = yesterday_attempts or past_attempts

    weakness = WeaknessAgent().analyse_attempts(past_attempts)
    mistakes = mistake_insights(past_attempts)
    groq_feedback = groq_progress_feedback(past_attempts, weakness, mistakes)
    feedback = groq_feedback[1] if groq_feedback else feedback_items(weakness.accuracy_by_topic, mistakes)

    previous_plan_sessions = _previous_plan_sessions(db, student_id, yesterday)
    revision = _groq_revision(today, yesterday, source_attempts, previous_plan_sessions, feedback)
    if revision is None:
        revision = _local_revision(today, source_attempts, previous_plan_sessions, feedback)
    return revision


def _previous_plan_sessions(db: Session, student_id: str, target_date) -> list[dict[str, Any]]:
    latest = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).first()
    if latest is None:
        return []
    payload = json.loads(latest.plan_json)
    rows = []
    for day in payload.get("plan", []):
        if day.get("date") == target_date.isoformat():
            rows.extend(day.get("sessions", []))
    if rows:
        return rows
    for day in reversed(payload.get("plan", [])):
        try:
            day_date = local_date_from_iso(day.get("date", ""))
        except ValueError:
            continue
        if day_date < local_today() and day.get("sessions"):
            return day.get("sessions", [])
    return []


def local_date_from_iso(value: str):
    from datetime import date

    return date.fromisoformat(value)


def _attempt_summary(attempts: list[QuizAttempt]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"correct": 0, "total": 0, "wrong_questions": []})
    for attempt in attempts:
        key = (attempt.topic, attempt.subtopic or "")
        grouped[key]["total"] += 1
        grouped[key]["correct"] += int(attempt.is_correct)
        if not attempt.is_correct and len(grouped[key]["wrong_questions"]) < 3:
            grouped[key]["wrong_questions"].append(
                {
                    "question": attempt.question_text,
                    "selected": attempt.selected_answer,
                    "correct": attempt.correct_answer,
                }
            )
    return [
        {
            "topic": topic,
            "subtopic": subtopic,
            "accuracy": round((values["correct"] / values["total"]) * 100, 2) if values["total"] else 0,
            "total": values["total"],
            "wrong_questions": values["wrong_questions"],
        }
        for (topic, subtopic), values in grouped.items()
    ]


def _groq_revision(today, yesterday, attempts: list[QuizAttempt], plan_sessions: list[dict[str, Any]], feedback: list[FeedbackItem]) -> RevisionResponse | None:
    client = LLMJSONClient(max_tokens=3200)
    if not client.available:
        return None
    system = """You are EduAgent's Groq revision strategist. Return JSON only.
Return { "priority_topics": string[], "exam_focus": string[], "sessions": [ { "topic": string, "subtopic": string, "minutes": number, "activity": string, "focus_points": string[] } ] }.
Create only today's 30-minute revision plan. Use yesterday's topics/quizzes first, then older past mistakes if yesterday has no data.
Do not include future study-plan topics."""
    prompt = (
        f"Today: {today.isoformat()}\nYesterday: {yesterday.isoformat()}\n"
        f"Yesterday/past quiz summary: {_attempt_summary(attempts)}\n"
        f"Previous plan sessions: {plan_sessions}\n"
        f"Topic feedback: {[item.model_dump(mode='json') for item in feedback[:6]]}\n"
        "Build exactly 30 minutes total. Prefer 3 short sessions: recall, redo mistakes, mini-check."
    )
    try:
        raw = client.complete_json(system, prompt, temperature=0.25)
        if not isinstance(raw, dict):
            return None
        return _revision_from_raw(today, raw, feedback)
    except Exception:
        return None


def _revision_from_raw(today, raw: dict[str, Any], feedback: list[FeedbackItem]) -> RevisionResponse:
    sessions = []
    used_minutes = 0.0
    for item in raw.get("sessions", [])[:4]:
        if not isinstance(item, dict):
            continue
        minutes = max(5.0, float(item.get("minutes") or 10))
        used_minutes += minutes
        topic = str(item.get("topic") or (feedback[0].topic if feedback else "Yesterday's topic"))
        subtopic = str(item.get("subtopic") or topic)
        sessions.append(
            {
                "topic": topic,
                "subtopic": subtopic,
                "hours": round(minutes / 60, 2),
                "activity": str(item.get("activity") or "Focused revision"),
                "priority": "High",
                "focus_points": [str(point) for point in item.get("focus_points", []) if str(point).strip()][:4]
                or [f"Recall the key rule for {subtopic}.", "Redo one wrong answer without looking.", "Take a quick self-check."],
                "resources": resources_for_topic(topic, subtopic),
            }
        )
    if not sessions:
        return _local_revision(today, [], [], feedback)
    if abs(used_minutes - 30.0) > 0.1:
        scale = 30.0 / used_minutes
        for session in sessions:
            session["hours"] = round(max(5.0 / 60, float(session["hours"]) * scale), 2)
    priority_topics = [str(topic) for topic in raw.get("priority_topics", []) if str(topic).strip()][:5] or [item.topic for item in feedback[:3]]
    exam_focus = [str(item) for item in raw.get("exam_focus", []) if str(item).strip()][:4] or ["Redo yesterday's wrong answers", "Recall key definitions", "Take one mini-check"]
    return RevisionResponse(
        priority_topics=priority_topics,
        exam_focus=exam_focus,
        revision_plan=[StudyDay.model_validate({"day": 1, "date": today.isoformat(), "sessions": sessions})],
        feedback=feedback,
    )


def _local_revision(today, attempts: list[QuizAttempt], plan_sessions: list[dict[str, Any]], feedback: list[FeedbackItem]) -> RevisionResponse:
    topic = (
        attempts[0].topic
        if attempts
        else plan_sessions[0].get("topic")
        if plan_sessions
        else feedback[0].topic
        if feedback
        else "Yesterday's topic"
    )
    subtopic = (
        attempts[0].subtopic
        if attempts and attempts[0].subtopic
        else plan_sessions[0].get("subtopic")
        if plan_sessions
        else topic
    )
    sessions = [
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.1,
            "activity": "5-minute active recall",
            "priority": "High",
            "focus_points": [f"Write the main rule for {subtopic} from memory.", "List two common traps before looking at notes."],
            "resources": resources_for_topic(topic, subtopic),
        },
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.25,
            "activity": "15-minute mistake redo",
            "priority": "High",
            "focus_points": ["Redo yesterday's wrong or uncertain quiz questions.", "Explain why each wrong option is wrong."],
            "resources": resources_for_topic(topic, f"{subtopic} practice"),
        },
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.15,
            "activity": "10-minute mini-check",
            "priority": "High",
            "focus_points": ["Answer three quick questions without notes.", "Save one correction note for tomorrow."],
            "resources": resources_for_topic(topic, f"{subtopic} quiz"),
        },
    ]
    return RevisionResponse(
        priority_topics=[item.topic for item in feedback[:3]] or [topic],
        exam_focus=["Review only topics completed before today", "Redo wrong quiz patterns", "Keep revision to 30 minutes"],
        revision_plan=[StudyDay.model_validate({"day": 1, "date": today.isoformat(), "sessions": sessions})],
        feedback=feedback,
    )
