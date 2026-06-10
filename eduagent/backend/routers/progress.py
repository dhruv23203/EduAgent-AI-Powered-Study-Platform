import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agents.weakness_agent import WeaknessAgent, feedback_items, groq_progress_feedback, mistake_insights
from db.database import get_db
from db.models import QuizAttempt, StreakRecovery, Student, StudyPlan, StudyTaskCompletion
from models.schemas import HeatmapDay, ProgressResponse
from utils.rewards import summary_for_user
from utils.timezone import local_date, local_today

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/{student_id}", response_model=ProgressResponse)
def get_progress(student_id: str, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> ProgressResponse:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    plan = _latest_plan(db, student_id, plan_id)
    if plan_id is not None and plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    attempts_query = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        attempts_query = attempts_query.filter(QuizAttempt.plan_id == plan_id)
    attempts = attempts_query.order_by(QuizAttempt.attempted_at.desc()).all()
    weakness = WeaknessAgent().analyse_attempts(attempts)
    total = len(attempts)
    correct = sum(int(item.is_correct) for item in attempts)
    activity = _activity_summary(db, student_id, attempts, plan_id)
    streak = _streak(activity["completed_dates"], activity["recovered_dates"])
    mistakes = mistake_insights(attempts)
    groq_feedback = groq_progress_feedback(attempts, weakness, mistakes)
    insight = groq_feedback[0] if groq_feedback else weakness.insight
    feedback = groq_feedback[1] if groq_feedback else feedback_items(weakness.accuracy_by_topic, mistakes)
    return ProgressResponse(
        overall_accuracy=round((correct / total) * 100, 2) if total else 0,
        topics_covered=sorted({item.topic for item in attempts}),
        topics_remaining=[topic for topic in _plan_topics(plan) if topic not in {item.topic for item in attempts}],
        weak_areas=weakness.weak_topics,
        strong_areas=weakness.strong_topics,
        streak_days=streak,
        total_questions_attempted=total,
        accuracy_by_topic=weakness.accuracy_by_topic,
        insight=insight,
        history=_history(attempts),
        heatmap=_heatmap(student, plan, activity),
        mistakes=mistakes,
        feedback=feedback,
        rewards=summary_for_user(db, student_id, streak, plan_id),
    )


def _latest_plan(db: Session, student_id: str, plan_id: int | None = None) -> StudyPlan | None:
    query = db.query(StudyPlan).filter(StudyPlan.student_id == student_id)
    if plan_id is not None:
        query = query.filter(StudyPlan.id == plan_id)
    return query.order_by(StudyPlan.created_at.desc()).first()


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


def _activity_summary(db: Session, student_id: str, attempts: list[QuizAttempt], plan_id: int | None = None) -> dict[str, Any]:
    quiz_by_date: dict[date, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    quiz_runs_by_date: dict[date, set[str]] = defaultdict(set)
    for attempt in attempts:
        key = local_date(attempt.attempted_at)
        quiz_by_date[key]["total"] += 1
        quiz_by_date[key]["correct"] += int(attempt.is_correct)
        run_id = attempt.quiz_run_id or f"legacy-{attempt.attempted_at.replace(microsecond=0).isoformat()}"
        quiz_runs_by_date[key].add(run_id)
    task_types: dict[date, set[str]] = defaultdict(set)
    tasks_query = db.query(StudyTaskCompletion.task_date, StudyTaskCompletion.task_type).filter(StudyTaskCompletion.student_id == student_id)
    if plan_id is not None:
        tasks_query = tasks_query.filter(StudyTaskCompletion.plan_id == plan_id)
    for task_date, task_type in tasks_query.all():
        task_types[task_date].add(task_type)
    recovered = {row[0] for row in db.query(StreakRecovery.recovered_date).filter(StreakRecovery.user_id == student_id).all()}
    candidates = set(quiz_by_date) | set(task_types)
    completed = {d for d in candidates if {"concepts", "practice"}.issubset(task_types.get(d, set())) and len(quiz_runs_by_date.get(d, set())) >= 3}
    return {"quiz_by_date": quiz_by_date, "quiz_runs_by_date": quiz_runs_by_date, "task_types": task_types, "completed_dates": completed, "recovered_dates": recovered}


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
        quiz_count = len(activity["quiz_runs_by_date"].get(current, set()))
        tasks = activity["task_types"].get(current, set())
        count = int("concepts" in tasks) + int("practice" in tasks) + min(quiz_count, 3)
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
