import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import StudyPlan

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/studyplan/{student_id}")
def export_studyplan(student_id: str, db: Session = Depends(get_db)) -> Response:
    plan = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    payload = json.loads(plan.plan_json)
    text = "EduAgent Study Plan\n\n"
    for day in payload.get("plan", []):
        text += f"Day {day.get('day')} - {day.get('date')}\n"
        for session in day.get("sessions", []):
            text += f"- {session.get('topic')} / {session.get('subtopic')} ({session.get('hours')}h): {session.get('activity')}\n"
        text += "\n"
    return Response(text, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=study-plan.txt"})


@router.get("/flashcards/{student_id}")
def export_flashcards(student_id: str, db: Session = Depends(get_db)) -> Response:
    plan = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Topic", "Prompt", "Answer"])
    for day in json.loads(plan.plan_json).get("plan", []):
        for session in day.get("sessions", []):
            writer.writerow([session.get("topic"), f"What is important in {session.get('subtopic')}?", "; ".join(session.get("focus_points", []))])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=flashcards.csv"})
