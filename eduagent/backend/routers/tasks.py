import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agents.fallbacks import looks_like_pdf_noise, resources_for_topic
from agents.study_agent import extract_topics, is_concrete_topic
from db.database import get_db
from db.models import Student, StudyPlan, StudyTaskCompletion
from models.schemas import DailyTaskStatus, TaskCompleteRequest
from utils.rewards import completed_task_types, quiz_count_for_date
from utils.subject import infer_subject

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{student_id}/{task_date}", response_model=DailyTaskStatus)
def get_daily_task(student_id: str, task_date: date, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> DailyTaskStatus:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    session = _session_for_date(db, student_id, task_date, plan_id)
    if not _valid_session(session):
        topics = extract_topics(student.syllabus_text or "", student.notes_text or "")
        if topics:
            chosen = topics[(task_date.toordinal() - date.today().toordinal()) % len(topics)]
            subtopics = chosen.get("subtopics") or [chosen["name"]]
            session = {"topic": chosen["name"], "subtopic": subtopics[0]}
    topic = session.get("topic", "Daily revision")
    subtopic = session.get("subtopic", "")
    task_types = completed_task_types(db, student_id, task_date, plan_id)
    quiz_count = quiz_count_for_date(db, student_id, task_date, plan_id)
    completed = {"concepts", "practice"}.issubset(task_types) and quiz_count >= 3
    return DailyTaskStatus(
        date=task_date.isoformat(),
        topic=topic,
        subtopic=subtopic,
        concepts_completed="concepts" in task_types,
        practice_completed="practice" in task_types,
        quiz_count=quiz_count,
        quiz_completed=quiz_count >= 3,
        day_completed=completed,
        resources=session.get("resources") or resources_for_topic(topic, subtopic),
    )


@router.post("/complete", response_model=DailyTaskStatus)
def complete_task(payload: TaskCompleteRequest, db: Session = Depends(get_db)) -> DailyTaskStatus:
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    existing = (
        db.query(StudyTaskCompletion)
        .filter(
            StudyTaskCompletion.student_id == payload.student_id,
            StudyTaskCompletion.plan_id == payload.plan_id,
            StudyTaskCompletion.task_date == payload.task_date,
            StudyTaskCompletion.task_type == payload.task_type,
        )
        .first()
    )
    if existing:
        db.delete(existing)
    else:
        db.add(StudyTaskCompletion(student_id=payload.student_id, plan_id=payload.plan_id, task_date=payload.task_date, task_type=payload.task_type, topic=payload.topic))
    db.commit()
    return get_daily_task(payload.student_id, payload.task_date, payload.plan_id, db)


def _session_for_date(db: Session, student_id: str, task_date: date, plan_id: int | None = None) -> dict:
    query = db.query(StudyPlan).filter(StudyPlan.student_id == student_id)
    if plan_id is not None:
        query = query.filter(StudyPlan.id == plan_id)
    plan = query.order_by(StudyPlan.created_at.desc()).first()
    if plan is None:
        return {}
    payload = json.loads(plan.plan_json)
    days = payload.get("plan", [])
    for day_index, day in enumerate(days):
        if day.get("date") == task_date.isoformat() and day.get("sessions"):
            session = _first_clean_session(day.get("sessions", []))
            if session:
                return session
            repaired = _concept_session(payload, day_index)
            if repaired:
                return repaired
    repaired = _concept_session(payload, 0)
    if repaired:
        return repaired
    for day in days:
        if day.get("sessions"):
            session = _first_clean_session(day.get("sessions", []))
            if session:
                return session
    return {}


def _concept_session(payload: dict, index: int) -> dict:
    # Existing plans may contain PDF headers. Re-extract canonical concepts from
    # that plan's own snapshot so another, more recently uploaded subject cannot leak in.
    snapshot = json.dumps(payload, ensure_ascii=False)
    subject_defaults = {
        "dsa": ["Arrays", "Linked Lists", "Stacks and Queues", "Trees", "Graphs", "Sorting and Searching", "Dynamic Programming"],
        "dbms": ["Database Fundamentals", "Relational Model and Algebra", "SQL", "Normalization", "Transactions and Concurrency", "Indexing and Query Processing"],
        "math": ["Sets and Relations", "Algebra", "Trigonometry", "Calculus", "Coordinate Geometry", "Vectors and 3D Geometry", "Probability and Statistics"],
        "physics": ["Mechanics", "Thermodynamics", "Electrostatics", "Current Electricity", "Magnetism", "Optics"],
        "chemistry": ["Atomic Structure", "Chemical Bonding", "Thermodynamics", "Equilibrium", "Organic Chemistry", "Inorganic Chemistry"],
    }
    subject = infer_subject(text=snapshot)
    names = subject_defaults.get(subject or "", [])
    if names:
        name = names[index % len(names)]
        return {"topic": name, "subtopic": name}
    topics = extract_topics(snapshot, "")
    if not topics:
        return {}
    chosen = topics[index % len(topics)]
    subtopics = chosen.get("subtopics") or [chosen["name"]]
    return {"topic": chosen["name"], "subtopic": subtopics[index % len(subtopics)]}


def _first_clean_session(sessions: list[dict]) -> dict:
    for session in sessions:
        if _valid_session(session):
            return session
    return {}


def _valid_session(session: dict) -> bool:
    topic = str(session.get("topic", ""))
    subtopic = str(session.get("subtopic", ""))
    return bool(topic) and is_concrete_topic(topic) and is_concrete_topic(subtopic or topic)
