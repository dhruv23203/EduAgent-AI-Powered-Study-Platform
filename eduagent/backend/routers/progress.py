import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.weakness_agent import WeaknessAgent, feedback_items, mistake_insights
from db.database import get_db
from db.models import QuizAttempt, StreakRecovery, Student, StudyPlan, StudyTaskCompletion
from models.schemas import HeatmapDay, ProgressResponse
from utils.rewards import summary_for_user
from utils.timezone import local_date, local_today

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/{student_id}", response_model=ProgressResponse)
def get_progress(student_id: str, db: Session = Depends(get_db)) -> ProgressResponse:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).order_by(QuizAttempt.attempted_at.desc()).all()
    weakness = WeaknessAgent().analyse_attempts(attempts)
    total = len(attempts)
    correct = sum(int(item.is_correct) for item in attempts)
    activity = _activity_summary(db, student_id, attempts)
    streak = _streak(activity["completed_dates"], activity["recovered_dates"])
    mistakes = mistake_insights(attempts)
    return ProgressResponse(
        overall_accuracy=round((correct / total) * 100, 2) if total else 0,
        topics_covered=sorted({item.topic for item in attempts}),
        topics_remaining=[topic for topic in _plan_topics(_latest_plan(db, student_id)) if topic not in {item.topic for item in attempts}],
        weak_areas=weakness.weak_topics,
        strong_areas=weakness.strong_topics,
        streak_days=streak,
        total_questions_attempted=total,
        accuracy_by_topic=weakness.accuracy_by_topic,
        insight=weakness.insight,
        history=_history(attempts),
        heatmap=_heatmap(student, _latest_plan(db, student_id), activity),
        mistakes=mistakes,
        feedback=feedback_items(weakness.accuracy_by_topic, mistakes),
        rewards=summary_for_user(db, student_id, streak),
    )


def _latest_plan(db: Session, student_id: str) -> StudyPlan | None:
    return db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).first()


def _plan_topics(plan: StudyPlan | None) -> list[str]:
    if plan is None:
        return []
    payload = json.loads(plan.plan_json)
    topics = []
    for day in payload.get("plan", []):
        for session in day.get("sessions", []):
            topic = session.get("topic")
            if topic and topic not in topics:
                topics.append(topic)
    return topics


def _history(attempts: list[QuizAttempt]) -> list[dict[str, str | int | float]]:
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for attempt in attempts:
        key = (local_date(attempt.attempted_at).isoformat(), attempt.topic)
        grouped[key]["total"] += 1
        grouped[key]["correct"] += int(attempt.is_correct)
    return [
        {"date": d, "topic": topic, "score": round((v["correct"] / v["total"]) * 100, 2), "correct": v["correct"], "total": v["total"]}
        for (d, topic), v in sorted(grouped.items(), reverse=True)
    ]


def _activity_summary(db: Session, student_id: str, attempts: list[QuizAttempt]) -> dict[str, Any]:
    quiz_by_date: dict[date, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for attempt in attempts:
        key = local_date(attempt.attempted_at)
        quiz_by_date[key]["total"] += 1
        quiz_by_date[key]["correct"] += int(attempt.is_correct)
    task_types: dict[date, set[str]] = defaultdict(set)
    for task_date, task_type in db.query(StudyTaskCompletion.task_date, StudyTaskCompletion.task_type).filter(StudyTaskCompletion.student_id == student_id).all():
        task_types[task_date].add(task_type)
    recovered = {row[0] for row in db.query(StreakRecovery.recovered_date).filter(StreakRecovery.user_id == student_id).all()}
    candidates = set(quiz_by_date) | set(task_types)
    completed = {d for d in candidates if {"concepts", "practice"}.issubset(task_types.get(d, set())) and quiz_by_date.get(d, {"total": 0})["total"] >= 3}
    return {"quiz_by_date": quiz_by_date, "task_types": task_types, "completed_dates": completed, "recovered_dates": recovered}


def _streak(completed: set[date], recovered: set[date]) -> int:
    active = set(completed) | set(recovered)
    today = local_today()
    cursor = today if today in active else today - timedelta(days=1)
    count = 0
    while cursor in active:
        count += 1
        cursor -= timedelta(days=1)
    return count


def _heatmap(student: Student, plan: StudyPlan | None, activity: dict[str, Any]) -> list[HeatmapDay]:
    today = local_today()
    start = local_date(plan.created_at) if plan else today - timedelta(days=30)
    end = student.exam_date or today
    if end < start:
        end = today
    rows = []
    current = start
    while current <= end:
        values = activity["quiz_by_date"].get(current, {"correct": 0, "total": 0})
        tasks = activity["task_types"].get(current, set())
        count = int("concepts" in tasks) + int("practice" in tasks) + min(values["total"], 3)
        rows.append(
            HeatmapDay(
                date=current.isoformat(),
                count=count,
                accuracy=100.0 if current in activity["completed_dates"] else round((values["correct"] / values["total"]) * 100, 2) if values["total"] else 0.0,
                recovered=current in activity["recovered_dates"],
            )
        )
        current += timedelta(days=1)
    return rows
