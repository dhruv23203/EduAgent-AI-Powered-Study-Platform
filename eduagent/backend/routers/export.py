import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import StudyPlan

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/studyplan/{student_id}")
def export_studyplan(student_id: str, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> Response:
    query = db.query(StudyPlan).filter(StudyPlan.student_id == student_id)
    if plan_id is not None:
        query = query.filter(StudyPlan.id == plan_id)
    plan = query.order_by(StudyPlan.created_at.desc()).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    payload = json.loads(plan.plan_json)
    text = "EduAgent Complete Day-by-Day Study Plan\n\n"
    for day in payload.get("plan", []):
        text += f"Day {day.get('day')} - {day.get('date')}\n"
        for session in day.get("sessions", []):
            text += f"- {session.get('topic')} / {session.get('subtopic')} ({session.get('hours')}h): {session.get('activity')}\n"
            focus_points = [str(point) for point in session.get("focus_points", []) if str(point).strip()]
            if focus_points:
                text += "  Focus points:\n"
                for point in focus_points:
                    text += f"  - {point}\n"
            resources = [item for item in session.get("resources", []) if isinstance(item, dict)]
            if resources:
                text += "  Resources:\n"
                for resource in resources:
                    text += f"  - {resource.get('title')}: {resource.get('url')}\n"
        text += "\n"
    return Response(text, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=complete-day-by-day-plan.txt"})


@router.get("/flashcards/{student_id}")
def export_flashcards(student_id: str, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> Response:
    query = db.query(StudyPlan).filter(StudyPlan.student_id == student_id)
    if plan_id is not None:
        query = query.filter(StudyPlan.id == plan_id)
    plan = query.order_by(StudyPlan.created_at.desc()).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Topic", "Prompt", "Answer"])
    for day in json.loads(plan.plan_json).get("plan", []):
        for session in day.get("sessions", []):
            writer.writerow([session.get("topic"), f"What is important in {session.get('subtopic')}?", "; ".join(session.get("focus_points", []))])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=flashcards.csv"})
