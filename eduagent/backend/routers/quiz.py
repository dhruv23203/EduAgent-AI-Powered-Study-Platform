import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.llm import AgentError
from agents.quiz_agent import generate_quiz
from agents.weakness_agent import WeaknessAgent
from db.database import get_db
from db.models import QuizAttempt, QuizQuestion as StoredQuestion, Student, StudyPlan
from models.schemas import GenerateQuizRequest, QuizQuestion, QuizSubmitRequest, QuizSubmitResponse
from utils.rewards import reward_quiz_submission

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/generate", response_model=list[QuizQuestion])
def generate(payload: GenerateQuizRequest, db: Session = Depends(get_db)) -> list[QuizQuestion]:
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if payload.plan_id is not None and db.query(StudyPlan.id).filter(StudyPlan.student_id == payload.student_id, StudyPlan.id == payload.plan_id).first() is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    try:
        return generate_quiz(db, payload)
    except AgentError as exc:
        raise HTTPException(status_code=503, detail=f"Quiz generation is temporarily unavailable: {str(exc)[:180]}")


@router.post("/submit", response_model=QuizSubmitResponse)
def submit(payload: QuizSubmitRequest, db: Session = Depends(get_db)) -> QuizSubmitResponse:
    correct = 0
    rows = []
    missing_questions = []
    quiz_run_id = uuid.uuid4().hex
    attempted_at = datetime.utcnow()
    for answer in payload.answers:
        query = db.query(StoredQuestion).filter(StoredQuestion.question_id == answer.question_id, StoredQuestion.student_id == payload.student_id)
        if payload.plan_id is not None:
            query = query.filter(StoredQuestion.plan_id == payload.plan_id)
        question = query.first()
        if question is None:
            missing_questions.append(answer.question_id)
            continue
        is_correct = question.correct_answer == answer.selected_option
        correct += int(is_correct)
        db.add(
            QuizAttempt(
                student_id=payload.student_id,
                plan_id=payload.plan_id or question.plan_id,
                quiz_run_id=quiz_run_id,
                question_id=question.question_id,
                topic=question.topic,
                subtopic=question.subtopic,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                selected_answer=answer.selected_option,
                is_correct=is_correct,
                attempted_at=attempted_at,
            )
        )
        rows.append(
            {
                "question": question.question_text,
                "selected": answer.selected_option,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "options": json.loads(question.options_json),
            }
        )
    if missing_questions:
        raise HTTPException(status_code=400, detail="Some quiz questions were not found. Please generate a fresh quiz and try again.")
    db.commit()
    if not rows:
        raise HTTPException(status_code=400, detail="No valid quiz answers were submitted.")
    total = len(rows)
    score = round((correct / total) * 100, 2)
    rewards = reward_quiz_submission(db, payload.student_id, score, correct, payload.plan_id, quiz_run_id)
    weakness = WeaknessAgent().analyse(db, payload.student_id)
    return QuizSubmitResponse(score=score, correct=correct, wrong=total - correct, explanations=rows, updated_weak_areas=weakness.weak_topics, rewards=rewards)
