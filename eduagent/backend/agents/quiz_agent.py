import json
import uuid

from sqlalchemy.orm import Session

from agents.fallbacks import allow_quiz_fallback
from agents.llm import AgentError, LLMJSONClient
from db.models import QuizQuestion as StoredQuestion
from models.schemas import GenerateQuizRequest, QuizQuestion

SYSTEM_PROMPT = """You generate exam-quality multiple choice quizzes.
Return only a JSON array. Each item must contain: question, options {A,B,C,D}, correct_answer, explanation, difficulty.
Questions must test the actual topic content, not generic study planning."""


def _local_questions(payload: GenerateQuizRequest) -> list[QuizQuestion]:
    stems = [
        f"Which statement best describes {payload.subtopic or payload.topic}?",
        f"What is a common edge case in {payload.subtopic or payload.topic}?",
        f"Which approach is usually efficient for {payload.topic} problems?",
        f"What should be verified after solving a {payload.topic} question?",
        f"Which mistake most often causes wrong answers in {payload.subtopic or payload.topic}?",
    ]
    rows = []
    for index in range(payload.count):
        rows.append(
            QuizQuestion(
                id=uuid.uuid4().hex,
                question=stems[index % len(stems)],
                options={
                    "A": "Use the core definition and trace a solved example",
                    "B": "Ignore constraints and memorize only the answer",
                    "C": "Skip dry runs and submit immediately",
                    "D": "Study unrelated topics first",
                },
                correct_answer="A",
                explanation=f"The safest option is to connect {payload.topic} to the core rule, then verify with an example.",
                difficulty=payload.difficulty,
                topic=payload.topic,
                subtopic=payload.subtopic,
            )
        )
    return rows


def generate_quiz(db: Session, payload: GenerateQuizRequest) -> list[QuizQuestion]:
    recent_query = db.query(StoredQuestion.question_text).filter(StoredQuestion.student_id == payload.student_id, StoredQuestion.topic == payload.topic)
    if payload.plan_id is not None:
        recent_query = recent_query.filter(StoredQuestion.plan_id == payload.plan_id)
    recent_rows = recent_query.order_by(StoredQuestion.created_at.desc()).limit(15).all()
    prompt = (
        f"Topic: {payload.topic}\nSubtopic: {payload.subtopic}\nDifficulty: {payload.difficulty}\n"
        f"Count: {payload.count}\nAvoid these previous questions: {[row[0] for row in recent_rows]}\n"
        "Make every question specific, fresh, and technically meaningful."
    )
    client = LLMJSONClient(max_tokens=2500)
    questions: list[QuizQuestion] = []
    if client.available:
        try:
            raw = client.complete_json(SYSTEM_PROMPT, prompt, temperature=0.75)
            if not isinstance(raw, list):
                raise AgentError("Quiz JSON was not a list.")
            for item in raw[: payload.count]:
                item["id"] = uuid.uuid4().hex
                item["topic"] = payload.topic
                item["subtopic"] = payload.subtopic
                item["difficulty"] = item.get("difficulty") or payload.difficulty
                questions.append(QuizQuestion.model_validate(item))
        except Exception:
            if not allow_quiz_fallback():
                raise
    if not questions:
        questions = _local_questions(payload)
    for question in questions:
        db.add(
            StoredQuestion(
                student_id=payload.student_id,
                plan_id=payload.plan_id,
                question_id=question.id,
                topic=payload.topic,
                subtopic=payload.subtopic,
                question_text=question.question,
                options_json=json.dumps(question.options),
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                difficulty=question.difficulty,
            )
        )
    db.commit()
    return questions
