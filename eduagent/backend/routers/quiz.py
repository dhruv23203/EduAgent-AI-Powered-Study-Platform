import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
    return generate_quiz(db, payload)


@router.post("/submit", response_model=QuizSubmitResponse)
def submit(payload: QuizSubmitRequest, db: Session = Depends(get_db)) -> QuizSubmitResponse:
    correct = 0
    rows = []
    for answer in payload.answers:
        query = db.query(StoredQuestion).filter(StoredQuestion.question_id == answer.question_id, StoredQuestion.student_id == payload.student_id)
        if payload.plan_id is not None:
            query = query.filter(StoredQuestion.plan_id == payload.plan_id)
        question = query.first()
        if question is None:
            continue
        is_correct = question.correct_answer == answer.selected_option
        correct += int(is_correct)
        db.add(
            QuizAttempt(
                student_id=payload.student_id,
                plan_id=payload.plan_id or question.plan_id,
                question_id=question.question_id,
                topic=question.topic,
                subtopic=question.subtopic,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                selected_answer=answer.selected_option,
                is_correct=is_correct,
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
    db.commit()
    total = len(rows) or 1
    score = round((correct / total) * 100, 2)
    rewards = reward_quiz_submission(db, payload.student_id, score, correct)
    weakness = WeaknessAgent().analyse(db, payload.student_id)
    return QuizSubmitResponse(score=score, correct=correct, wrong=total - correct, explanations=rows, updated_weak_areas=weakness.weak_topics, rewards=rewards)
