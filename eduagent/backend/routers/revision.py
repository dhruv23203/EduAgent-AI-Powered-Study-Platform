import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.weakness_agent import WeaknessAgent, feedback_items, mistake_insights
from db.database import get_db
from db.models import QuizAttempt, Student, StudyPlan
from models.schemas import RevisionResponse, StudyDay

router = APIRouter(prefix="/api/revision", tags=["revision"])


@router.get("/{student_id}", response_model=RevisionResponse)
def get_revision(student_id: str, db: Session = Depends(get_db)) -> RevisionResponse:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).order_by(QuizAttempt.attempted_at.desc()).all()
    weakness = WeaknessAgent().analyse_attempts(attempts)
    mistakes = mistake_insights(attempts)
    latest = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).first()
    plan_rows = []
    if latest:
        covered = {attempt.topic for attempt in attempts}
        for day in json.loads(latest.plan_json).get("plan", []):
            sessions = [session for session in day.get("sessions", []) if session.get("topic") in covered or session.get("topic") in weakness.weak_topics]
            if sessions:
                plan_rows.append({"day": day.get("day"), "date": day.get("date"), "sessions": sessions})
            if len(plan_rows) >= 7:
                break
    return RevisionResponse(
        priority_topics=weakness.weak_topics or list(weakness.accuracy_by_topic.keys())[:3],
        exam_focus=["Review wrong answers", "Retake quizzes", "Practice most-asked problems"],
        revision_plan=[StudyDay.model_validate(row) for row in plan_rows],
        feedback=feedback_items(weakness.accuracy_by_topic, mistakes),
    )
