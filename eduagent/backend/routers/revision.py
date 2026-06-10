import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agents.fallbacks import resources_for_topic
from agents.llm import LLMJSONClient
from agents.weakness_agent import WeaknessAgent, feedback_items, groq_progress_feedback, mistake_insights
from db.database import get_db
from db.models import QuizAttempt, QuizQuestion as StoredQuestion, RevisionQuizAttempt, RevisionQuizQuestion, Student, StudyPlan
from models.schemas import FeedbackItem, QuizQuestion, RevisionMistakeFeedback, RevisionQuizGenerateRequest, RevisionQuizHistoryItem, RevisionQuizSubmitRequest, RevisionQuizSubmitResponse, RevisionResponse, StudyDay
from utils.timezone import local_date, local_today

router = APIRouter(prefix="/api/revision", tags=["revision"])


@router.post("/quiz/generate", response_model=list[QuizQuestion])
def generate_revision_quiz(payload: RevisionQuizGenerateRequest, db: Session = Depends(get_db)) -> list[QuizQuestion]:
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if payload.plan_id is not None and db.query(StudyPlan.id).filter(StudyPlan.student_id == payload.student_id, StudyPlan.id == payload.plan_id).first() is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    questions = _revision_quiz_questions(db, payload.student_id, payload.plan_id, payload.count)
    if not questions:
        return []
    for question, source_feedback, source_mistake in questions:
        db.add(
            RevisionQuizQuestion(
                student_id=payload.student_id,
                plan_id=payload.plan_id,
                question_id=question.id,
                topic=question.topic,
                subtopic=question.subtopic,
                question_text=question.question,
                options_json=json.dumps(question.options),
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                source_feedback=source_feedback,
                source_mistake=source_mistake,
                difficulty=question.difficulty,
            )
        )
    db.commit()
    return [item[0] for item in questions]


@router.post("/quiz/submit", response_model=RevisionQuizSubmitResponse)
def submit_revision_quiz(payload: RevisionQuizSubmitRequest, db: Session = Depends(get_db)) -> RevisionQuizSubmitResponse:
    quiz_run_id = uuid.uuid4().hex
    attempted_at = datetime.utcnow()
    rows: list[RevisionMistakeFeedback] = []
    correct = 0
    total = 0
    missing = []
    for answer in payload.answers:
        query = db.query(RevisionQuizQuestion).filter(RevisionQuizQuestion.student_id == payload.student_id, RevisionQuizQuestion.question_id == answer.question_id)
        if payload.plan_id is not None:
            query = query.filter(RevisionQuizQuestion.plan_id == payload.plan_id)
        question = query.first()
        if question is None:
            missing.append(answer.question_id)
            continue
        is_correct = question.correct_answer == answer.selected_option
        correct += int(is_correct)
        total += 1
        feedback = _revision_answer_feedback(question, answer.selected_option, is_correct)
        db.add(
            RevisionQuizAttempt(
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
                feedback=feedback,
                source_mistake=question.source_mistake,
                attempted_at=attempted_at,
            )
        )
        if not is_correct:
            rows.append(
                RevisionMistakeFeedback(
                    question=question.question_text,
                    topic=question.topic,
                    subtopic=question.subtopic or "",
                    selected_answer=answer.selected_option,
                    correct_answer=question.correct_answer,
                    feedback=feedback,
                    source_mistake=question.source_mistake,
                )
            )
    if missing:
        raise HTTPException(status_code=400, detail="Some revision quiz questions were not found. Start a new revision quiz and try again.")
    if total == 0:
        raise HTTPException(status_code=400, detail="No valid revision answers were submitted.")
    db.commit()
    score = round((correct / total) * 100, 2)
    return RevisionQuizSubmitResponse(quiz_run_id=quiz_run_id, score=score, correct=correct, wrong=total - correct, total=total, mistakes=rows)


@router.get("/quiz/history/{student_id}", response_model=list[RevisionQuizHistoryItem])
def revision_quiz_history(student_id: str, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[RevisionQuizHistoryItem]:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    query = db.query(RevisionQuizAttempt).filter(RevisionQuizAttempt.student_id == student_id)
    if plan_id is not None:
        query = query.filter(RevisionQuizAttempt.plan_id == plan_id)
    attempts = query.order_by(RevisionQuizAttempt.attempted_at.desc()).limit(200).all()
    return _revision_history_from_attempts(attempts)


@router.get("/{student_id}", response_model=RevisionResponse)
def get_revision(student_id: str, plan_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> RevisionResponse:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if plan_id is not None and db.query(StudyPlan.id).filter(StudyPlan.student_id == student_id, StudyPlan.id == plan_id).first() is None:
        raise HTTPException(status_code=404, detail="Plan not found.")

    today = local_today()
    yesterday = today - timedelta(days=1)
    attempts_query = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        attempts_query = attempts_query.filter(QuizAttempt.plan_id == plan_id)
    attempts = attempts_query.order_by(QuizAttempt.attempted_at.desc()).all()
    past_attempts = [attempt for attempt in attempts if local_date(attempt.attempted_at) < today]
    yesterday_attempts = [attempt for attempt in past_attempts if local_date(attempt.attempted_at) == yesterday]
    source_attempts = yesterday_attempts or past_attempts

    weakness = WeaknessAgent().analyse_attempts(past_attempts)
    mistakes = mistake_insights(past_attempts)
    groq_feedback = groq_progress_feedback(past_attempts, weakness, mistakes)
    feedback = groq_feedback[1] if groq_feedback else feedback_items(weakness.accuracy_by_topic, mistakes)

    previous_plan_sessions = _previous_plan_sessions(db, student_id, yesterday, plan_id)
    if not past_attempts and not previous_plan_sessions:
        return RevisionResponse(
            priority_topics=[],
            exam_focus=["First study day"],
            revision_plan=[],
            feedback=[],
            is_first_day=True,
            message="You have nothing to revise because this is your first day. Enjoy today's learning block and come back tomorrow for a mistake-based revision plan.",
            quiz_questions=[],
            revision_percentage=0,
            quiz_accuracy=0,
            total_revision_questions=0,
        )
    revision = _groq_revision(today, yesterday, source_attempts, previous_plan_sessions, feedback)
    if revision is None:
        revision = _local_revision(today, source_attempts, previous_plan_sessions, feedback)
    return revision


def _previous_plan_sessions(db: Session, student_id: str, target_date, plan_id: int | None = None) -> list[dict[str, Any]]:
    query = db.query(StudyPlan).filter(StudyPlan.student_id == student_id)
    if plan_id is not None:
        query = query.filter(StudyPlan.id == plan_id)
    latest = query.order_by(StudyPlan.created_at.desc()).first()
    if latest is None:
        return []
    payload = json.loads(latest.plan_json)
    rows = []
    for day in payload.get("plan", []):
        if day.get("date") == target_date.isoformat():
            rows.extend(day.get("sessions", []))
    if rows:
        return rows
    for day in reversed(payload.get("plan", [])):
        try:
            day_date = local_date_from_iso(day.get("date", ""))
        except ValueError:
            continue
        if day_date < local_today() and day.get("sessions"):
            return day.get("sessions", [])
    return []


def _past_attempts_for_revision(db: Session, student_id: str, plan_id: int | None = None) -> list[QuizAttempt]:
    today = local_today()
    query = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        query = query.filter(QuizAttempt.plan_id == plan_id)
    attempts = query.order_by(QuizAttempt.attempted_at.desc()).all()
    return [attempt for attempt in attempts if local_date(attempt.attempted_at) < today]


def _revision_quiz_questions(db: Session, student_id: str, plan_id: int | None, count: int) -> list[tuple[QuizQuestion, str, str]]:
    attempts = _past_attempts_for_revision(db, student_id, plan_id)
    if not attempts:
        return []
    priority = [attempt for attempt in attempts if not attempt.is_correct] + [attempt for attempt in attempts if attempt.is_correct]
    rows: list[tuple[QuizQuestion, str, str]] = []
    seen: set[str] = set()
    for attempt in priority:
        marker = _question_key(attempt.question_text)
        if marker in seen:
            continue
        seen.add(marker)
        stored = (
            db.query(StoredQuestion)
            .filter(StoredQuestion.student_id == student_id, StoredQuestion.question_id == attempt.question_id)
            .first()
        )
        try:
            options = json.loads(stored.options_json) if stored else _letter_options()
        except json.JSONDecodeError:
            options = _letter_options()
        source_mistake = (
            f"Earlier mistake: you selected {attempt.selected_answer}, but the correct answer was {attempt.correct_answer}."
            if not attempt.is_correct
            else "Earlier correct answer: use this as spaced retrieval to keep the concept strong."
        )
        source_feedback = _specific_revision_feedback(attempt, stored.explanation if stored else "")
        question = QuizQuestion(
            id=uuid.uuid4().hex,
            question=f"Revision redo - {attempt.question_text}",
            options=options,
            correct_answer=attempt.correct_answer,  # type: ignore[arg-type]
            explanation=stored.explanation if stored else source_feedback,
            difficulty=stored.difficulty if stored else "Medium",
            topic=attempt.topic,
            subtopic=attempt.subtopic or "",
        )
        rows.append((question, source_feedback, source_mistake))
        if len(rows) >= count:
            break
    return rows


def _letter_options() -> dict[str, str]:
    return {
        "A": "Re-apply the core rule and verify with the original question details",
        "B": "Choose the answer from memory without checking the condition",
        "C": "Ignore the mistake pattern and move to a new topic",
        "D": "Skip the explanation and only record the score",
    }


def _specific_revision_feedback(attempt: QuizAttempt, explanation: str = "") -> str:
    if attempt.is_correct:
        return f"Keep {attempt.topic} active with spaced recall. Explain why {attempt.correct_answer} is correct before checking notes."
    base = (
        f"For {attempt.topic}"
        + (f" - {attempt.subtopic}" if attempt.subtopic else "")
        + f", compare your selected answer {attempt.selected_answer} with the correct answer {attempt.correct_answer}. "
        "Write the exact rule or condition that makes the correct option stronger."
    )
    if explanation:
        return f"{base} Original explanation: {explanation}"
    return base


def _revision_answer_feedback(question: RevisionQuizQuestion, selected: str, is_correct: bool) -> str:
    if is_correct:
        return f"Correct. Keep this pattern warm: {question.source_feedback}"
    return (
        f"Revise this mistake: you selected {selected}, but the correct answer is {question.correct_answer}. "
        f"{question.source_feedback}"
    )


def _revision_history_from_attempts(attempts: list[RevisionQuizAttempt]) -> list[RevisionQuizHistoryItem]:
    grouped: dict[str, list[RevisionQuizAttempt]] = defaultdict(list)
    for attempt in attempts:
        grouped[attempt.quiz_run_id].append(attempt)
    rows: list[RevisionQuizHistoryItem] = []
    for run_id, items in grouped.items():
        ordered = sorted(items, key=lambda item: item.attempted_at)
        total = len(ordered)
        correct = sum(int(item.is_correct) for item in ordered)
        mistakes = [
            RevisionMistakeFeedback(
                question=item.question_text,
                topic=item.topic,
                subtopic=item.subtopic or "",
                selected_answer=item.selected_answer,
                correct_answer=item.correct_answer,
                feedback=item.feedback,
                source_mistake=item.source_mistake,
            )
            for item in ordered
            if not item.is_correct
        ]
        rows.append(
            RevisionQuizHistoryItem(
                quiz_run_id=run_id,
                attempted_at=max(item.attempted_at for item in ordered),
                score=round((correct / total) * 100, 2) if total else 0,
                correct=correct,
                wrong=total - correct,
                total=total,
                mistakes=mistakes,
            )
        )
    return sorted(rows, key=lambda row: row.attempted_at, reverse=True)[:20]


def local_date_from_iso(value: str):
    from datetime import date

    return date.fromisoformat(value)


def _attempt_summary(attempts: list[QuizAttempt]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"correct": 0, "total": 0, "wrong_questions": []})
    for attempt in attempts:
        key = (attempt.topic, attempt.subtopic or "")
        grouped[key]["total"] += 1
        grouped[key]["correct"] += int(attempt.is_correct)
        if not attempt.is_correct and len(grouped[key]["wrong_questions"]) < 3:
            grouped[key]["wrong_questions"].append(
                {
                    "question": attempt.question_text,
                    "selected": attempt.selected_answer,
                    "correct": attempt.correct_answer,
                }
            )
    return [
        {
            "topic": topic,
            "subtopic": subtopic,
            "accuracy": round((values["correct"] / values["total"]) * 100, 2) if values["total"] else 0,
            "total": values["total"],
            "wrong_questions": values["wrong_questions"],
        }
        for (topic, subtopic), values in grouped.items()
    ]


def _groq_revision(today, yesterday, attempts: list[QuizAttempt], plan_sessions: list[dict[str, Any]], feedback: list[FeedbackItem]) -> RevisionResponse | None:
    client = LLMJSONClient(max_tokens=3200)
    if not client.available:
        return None
    system = """You are EduAgent's Groq revision strategist. Return JSON only.
Return { "priority_topics": string[], "exam_focus": string[], "self_check_questions": string[], "sessions": [ { "topic": string, "subtopic": string, "minutes": number, "activity": string, "focus_points": string[] } ] }.
Create only today's 30-minute revision plan. Use yesterday's topics/quizzes first, then older past mistakes if yesterday has no data.
Do not include future study-plan topics.
The self_check_questions array must contain exactly 10 specific questions based on past quiz mistakes or completed past concepts."""
    prompt = (
        f"Today: {today.isoformat()}\nYesterday: {yesterday.isoformat()}\n"
        f"Yesterday/past quiz summary: {_attempt_summary(attempts)}\n"
        f"Previous plan sessions: {plan_sessions}\n"
        f"Topic feedback: {[item.model_dump(mode='json') for item in feedback[:6]]}\n"
        "Build exactly 30 minutes total. Prefer 3 short sessions: recall, redo mistakes, mini-check. "
        "Make every self-check question specific to the topic, subtopic, and mistake pattern."
    )
    try:
        raw = client.complete_json(system, prompt, temperature=0.25)
        if not isinstance(raw, dict):
            return None
        return _revision_from_raw(today, raw, attempts, plan_sessions, feedback)
    except Exception:
        return None


def _revision_from_raw(today, raw: dict[str, Any], attempts: list[QuizAttempt], plan_sessions: list[dict[str, Any]], feedback: list[FeedbackItem]) -> RevisionResponse:
    sessions = []
    used_minutes = 0.0
    for item in raw.get("sessions", [])[:4]:
        if not isinstance(item, dict):
            continue
        minutes = max(5.0, float(item.get("minutes") or 10))
        used_minutes += minutes
        topic = str(item.get("topic") or (feedback[0].topic if feedback else "Yesterday's topic"))
        subtopic = str(item.get("subtopic") or topic)
        sessions.append(
            {
                "topic": topic,
                "subtopic": subtopic,
                "hours": round(minutes / 60, 2),
                "activity": str(item.get("activity") or "Focused revision"),
                "priority": "High",
                "focus_points": [str(point) for point in item.get("focus_points", []) if str(point).strip()][:4]
                or [f"Recall the key rule for {subtopic}.", "Redo one wrong answer without looking.", "Take a quick self-check."],
                "resources": resources_for_topic(topic, subtopic),
            }
        )
    if not sessions:
        return _local_revision(today, attempts, plan_sessions, feedback)
    if abs(used_minutes - 30.0) > 0.1:
        scale = 30.0 / used_minutes
        for session in sessions:
            session["hours"] = round(max(5.0 / 60, float(session["hours"]) * scale), 2)
    priority_topics = [str(topic) for topic in raw.get("priority_topics", []) if str(topic).strip()][:5] or [item.topic for item in feedback[:3]]
    exam_focus = [str(item) for item in raw.get("exam_focus", []) if str(item).strip()][:4] or ["Redo yesterday's wrong answers", "Recall key definitions", "Take one mini-check"]
    quiz_questions = _ten_revision_questions(attempts, plan_sessions, feedback, raw.get("self_check_questions", []))
    return RevisionResponse(
        priority_topics=priority_topics,
        exam_focus=exam_focus,
        revision_plan=[StudyDay.model_validate({"day": 1, "date": today.isoformat(), "sessions": sessions})],
        feedback=feedback,
        is_first_day=False,
        message="Today's revision is built only from earlier quiz mistakes and completed concepts.",
        quiz_questions=quiz_questions,
        revision_percentage=_revision_percentage(attempts),
        quiz_accuracy=_quiz_accuracy(attempts),
        total_revision_questions=len(quiz_questions),
    )


def _local_revision(today, attempts: list[QuizAttempt], plan_sessions: list[dict[str, Any]], feedback: list[FeedbackItem]) -> RevisionResponse:
    topic = (
        attempts[0].topic
        if attempts
        else plan_sessions[0].get("topic")
        if plan_sessions
        else feedback[0].topic
        if feedback
        else "Yesterday's topic"
    )
    subtopic = (
        attempts[0].subtopic
        if attempts and attempts[0].subtopic
        else plan_sessions[0].get("subtopic")
        if plan_sessions
        else topic
    )
    quiz_questions = _ten_revision_questions(attempts, plan_sessions, feedback)
    sessions = [
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.1,
            "activity": "5-minute active recall",
            "priority": "High",
            "focus_points": [f"Write the main rule for {subtopic} from memory.", "List two common traps before looking at notes.", *quiz_questions[:2]],
            "resources": resources_for_topic(topic, subtopic),
        },
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.25,
            "activity": "15-minute mistake redo",
            "priority": "High",
            "focus_points": ["Redo yesterday's wrong or uncertain quiz questions.", "Explain why each wrong option is wrong.", *quiz_questions[2:5]],
            "resources": resources_for_topic(topic, f"{subtopic} practice"),
        },
        {
            "topic": topic,
            "subtopic": subtopic,
            "hours": 0.15,
            "activity": "10-minute mini-check",
            "priority": "High",
            "focus_points": ["Answer the 10-question self-check without notes.", "Save one correction note for tomorrow.", *quiz_questions[5:8]],
            "resources": resources_for_topic(topic, f"{subtopic} quiz"),
        },
    ]
    return RevisionResponse(
        priority_topics=[item.topic for item in feedback[:3]] or [topic],
        exam_focus=["Review only topics completed before today", "Redo wrong quiz patterns", "Keep revision to 30 minutes"],
        revision_plan=[StudyDay.model_validate({"day": 1, "date": today.isoformat(), "sessions": sessions})],
        feedback=feedback,
        is_first_day=False,
        message="Today's revision is built only from earlier quiz mistakes and completed concepts.",
        quiz_questions=quiz_questions,
        revision_percentage=_revision_percentage(attempts),
        quiz_accuracy=_quiz_accuracy(attempts),
        total_revision_questions=len(quiz_questions),
    )


def _quiz_accuracy(attempts: list[QuizAttempt]) -> float:
    if not attempts:
        return 0
    return round((sum(int(item.is_correct) for item in attempts) / len(attempts)) * 100, 2)


def _revision_percentage(attempts: list[QuizAttempt]) -> float:
    if not attempts:
        return 0
    wrong = sum(int(not item.is_correct) for item in attempts)
    return round(min(100, max(0, (wrong / len(attempts)) * 100)), 2)


def _question_key(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _ten_revision_questions(
    attempts: list[QuizAttempt],
    plan_sessions: list[dict[str, Any]],
    feedback: list[FeedbackItem],
    suggested: list[Any] | None = None,
) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        text = " ".join(str(value).split()).strip()
        marker = _question_key(text)
        if text and marker and marker not in seen and len(rows) < 10:
            seen.add(marker)
            rows.append(text[:240])

    for item in suggested or []:
        add(str(item))
    for attempt in attempts:
        if not attempt.is_correct:
            add(f"Redo this without notes: {attempt.question_text} Why is option {attempt.correct_answer} stronger than option {attempt.selected_answer}?")
    for item in feedback:
        for step in item.next_steps:
            add(f"For {item.topic}, answer this revision check: {step}")
    for session in plan_sessions:
        topic = str(session.get("topic") or "the previous concept")
        subtopic = str(session.get("subtopic") or topic)
        for point in session.get("focus_points", [])[:4]:
            add(f"In {topic} - {subtopic}, explain and apply this point: {point}")
    topic = (
        attempts[0].topic
        if attempts
        else str(plan_sessions[0].get("topic"))
        if plan_sessions
        else feedback[0].topic
        if feedback
        else "the previous topic"
    )
    subtopic = (
        attempts[0].subtopic
        if attempts and attempts[0].subtopic
        else str(plan_sessions[0].get("subtopic"))
        if plan_sessions
        else topic
    )
    fillers = [
        f"Define the core rule of {subtopic} in {topic} and give one example.",
        f"Solve one medium-level question on {subtopic} and write why each wrong option is wrong.",
        f"List two edge cases that can break a solution for {subtopic}.",
        f"Compare the fastest and safest method for solving {subtopic} questions.",
        f"Create one exam-style MCQ for {subtopic}, then answer it with reasoning.",
        f"Write the mistake you are most likely to make in {subtopic} and the check that prevents it.",
        f"Explain {subtopic} to a beginner using one diagram or step trace.",
        f"Do a 2-minute memory dump of formulas, definitions, or rules for {subtopic}.",
        f"Turn the last wrong answer pattern into one corrected note for {topic}.",
        f"Finish with one timed question on {topic} and mark the exact step that caused hesitation.",
    ]
    for item in fillers:
        add(item)
    return rows[:10]
