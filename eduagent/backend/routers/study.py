import json
import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.fallbacks import looks_like_pdf_noise
from agents.study_agent import generate_study_plan
from db.database import get_db
from db.models import QuizAttempt, QuizQuestion, Student, StudyPlan, StudyTaskCompletion
from models.schemas import GeneratePlanRequest, StudyPlanResponse, StudyPlanSummary

router = APIRouter(prefix="/api/study", tags=["study"])


def _response_from_payload(payload: dict, plan_id: int | None = None) -> StudyPlanResponse:
    raw_plan = payload.get("plan") or payload.get("study_plan") or []
    plan = _clean_plan_rows(raw_plan)
    topics = payload.get("topics") or []
    hours: dict[str, float] = payload.get("hours_per_topic") or {}
    if not hours:
        for day in plan:
            for session in day.get("sessions", []):
                hours[session.get("topic", "Topic")] = hours.get(session.get("topic", "Topic"), 0) + float(session.get("hours", 0))
    return StudyPlanResponse(id=plan_id, study_plan=plan, topics=topics, total_days=len(plan), hours_per_topic=hours)


def _clean_plan_rows(rows: list[dict]) -> list[dict]:
    clean_sessions = []
    for day in rows:
        for session in day.get("sessions", []):
            topic = str(session.get("topic", ""))
            subtopic = str(session.get("subtopic", ""))
            if not looks_like_pdf_noise(topic) and not looks_like_pdf_noise(subtopic or topic):
                clean_sessions.append(session)
    if not clean_sessions:
        return []

    cleaned = []
    for index, day in enumerate(rows):
        sessions = []
        for session in day.get("sessions", []):
            topic = str(session.get("topic", ""))
            subtopic = str(session.get("subtopic", ""))
            if looks_like_pdf_noise(topic) or looks_like_pdf_noise(subtopic or topic):
                continue
            sessions.append(session)
        if not sessions:
            sessions = [dict(clean_sessions[index % len(clean_sessions)])]
        if sessions:
            next_day = dict(day)
            next_day["sessions"] = sessions
            cleaned.append(next_day)
    return cleaned


def _summary(plan: StudyPlan) -> StudyPlanSummary:
    payload = json.loads(plan.plan_json)
    days = payload.get("plan") or []
    sessions = [session for day in days for session in day.get("sessions", [])]
    topics = []
    for session in sessions:
        topic = session.get("topic")
        if topic and topic not in topics:
            topics.append(topic)
    start = date.fromisoformat(days[0]["date"]) if days else None
    end = date.fromisoformat(days[-1]["date"]) if days else None
    today = date.today()
    status = "completed" if end and end < today else "running" if start and start <= today else "upcoming"
    return StudyPlanSummary(
        id=plan.id,
        title=", ".join(topics[:2]) or "Saved study plan",
        status=status,
        created_at=plan.created_at,
        start_date=start,
        end_date=end,
        total_days=len(days),
        total_sessions=len(sessions),
        total_hours=sum(float(item.get("hours", 0)) for item in sessions),
        daily_hours=float(sessions[0].get("hours", 0)) if sessions else 0,
        topic_count=len(topics),
        primary_topics=topics[:4],
    )


@router.post("/generate", response_model=StudyPlanResponse)
def generate(payload: GeneratePlanRequest, db: Session = Depends(get_db)) -> StudyPlanResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        student = Student(id=payload.student_id)
        db.add(student)
    student.exam_date = payload.exam_date
    student.daily_hours = payload.daily_hours
    plan_payload = generate_study_plan(
        student.syllabus_text or "",
        student.notes_text or "",
        payload.exam_date,
        payload.daily_hours,
        int(os.getenv("MAX_STUDY_PLAN_DAYS", "365")),
    )
    db.add(student)
    plan = StudyPlan(student_id=payload.student_id, plan_json=json.dumps(plan_payload))
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _response_from_payload(plan_payload, plan.id)


@router.get("/plans/{student_id}", response_model=list[StudyPlanSummary])
def list_plans(student_id: str, db: Session = Depends(get_db)) -> list[StudyPlanSummary]:
    plans = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).all()
    return [_summary(plan) for plan in plans]


@router.get("/plans/{student_id}/{plan_id}", response_model=StudyPlanResponse)
def get_plan(student_id: str, plan_id: int, db: Session = Depends(get_db)) -> StudyPlanResponse:
    plan = db.query(StudyPlan).filter(StudyPlan.student_id == student_id, StudyPlan.id == plan_id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return _response_from_payload(json.loads(plan.plan_json), plan.id)


@router.delete("/plans/{student_id}/{plan_id}")
def delete_plan(student_id: str, plan_id: int, db: Session = Depends(get_db)) -> dict[str, int | bool]:
    plan = db.query(StudyPlan).filter(StudyPlan.student_id == student_id, StudyPlan.id == plan_id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    deleted_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id, QuizAttempt.plan_id == plan_id).delete(synchronize_session=False)
    deleted_questions = db.query(QuizQuestion).filter(QuizQuestion.student_id == student_id, QuizQuestion.plan_id == plan_id).delete(synchronize_session=False)
    deleted_tasks = db.query(StudyTaskCompletion).filter(StudyTaskCompletion.student_id == student_id, StudyTaskCompletion.plan_id == plan_id).delete(synchronize_session=False)
    db.delete(plan)
    db.commit()
    return {
        "success": True,
        "deleted_plan_id": plan_id,
        "deleted_quiz_attempts": deleted_attempts,
        "deleted_quiz_questions": deleted_questions,
        "deleted_task_completions": deleted_tasks,
    }
