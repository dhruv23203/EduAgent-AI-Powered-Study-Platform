import json
import re
import uuid

from sqlalchemy.orm import Session

from agents.fallbacks import allow_quiz_fallback, sanitize_document_text
from agents.llm import AgentError, LLMJSONClient
from db.models import QuizQuestion as StoredQuestion, Student, StudyPlan
from models.schemas import GenerateQuizRequest, QuizQuestion

SYSTEM_PROMPT = """You generate exam-quality multiple choice quizzes.
Return only a JSON array. Each item must contain: question, options {A,B,C,D}, correct_answer, explanation, difficulty.
Questions must test the exact daily topic and subtopic content, not generic study planning.
Every question must be new, specific, and answerable from the named topic/subtopic.
Do not repeat wording, examples, option patterns, or concepts from the previous questions list.
All questions inside the same quiz must also be unique from each other."""


def _fingerprint(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _relevant_excerpt(text: str, topic: str, subtopic: str, limit: int = 1600) -> str:
    cleaned = sanitize_document_text(text)
    if not cleaned:
        return ""
    terms = [term.lower() for term in {topic, subtopic, *topic.split(), *subtopic.split()} if len(term.strip()) >= 4]
    lines = cleaned.splitlines()
    selected = [line for line in lines if any(term in line.lower() for term in terms)]
    excerpt = "\n".join(selected[:24]) or cleaned[:limit]
    return excerpt[:limit]


def _plan_context(db: Session, payload: GenerateQuizRequest) -> str:
    if payload.plan_id is None:
        return ""
    plan = db.query(StudyPlan).filter(StudyPlan.id == payload.plan_id, StudyPlan.student_id == payload.student_id).first()
    if plan is None:
        return ""
    try:
        data = json.loads(plan.plan_json)
    except json.JSONDecodeError:
        return ""
    matches = []
    for day in data.get("plan", []):
        for session in day.get("sessions", []):
            topic = str(session.get("topic", ""))
            subtopic = str(session.get("subtopic", ""))
            if topic == payload.topic or subtopic == payload.subtopic:
                matches.append(
                    {
                        "date": day.get("date"),
                        "topic": topic,
                        "subtopic": subtopic,
                        "activity": session.get("activity"),
                        "focus_points": session.get("focus_points", []),
                    }
                )
    return json.dumps(matches[:3], ensure_ascii=False)


def _local_questions(payload: GenerateQuizRequest, used: set[str] | None = None) -> list[QuizQuestion]:
    focus = payload.subtopic or payload.topic
    stems = [
        f"In {payload.topic}, which statement most accurately explains {focus}?",
        f"While solving a {payload.topic} problem on {focus}, which edge case must be checked first?",
        f"Which practice approach best builds accuracy for {focus} in {payload.topic}?",
        f"After completing a {focus} question, what verification step best catches mistakes?",
        f"Which error pattern most often causes wrong answers in {focus}?",
        f"Which example would best prove that you understand {focus}?",
        f"What should be compared when two answer choices both mention {focus}?",
        f"Which revision note is most useful after missing a {payload.topic} question about {focus}?",
        f"When {focus} appears in an exam stem, which clue should guide the first step?",
        f"Which reason best explains why a direct memorized answer can fail for {focus}?",
        f"In a timed quiz on {payload.topic}, what is the safest way to validate a {focus} answer?",
        f"Which misconception about {focus} would most likely produce a wrong option choice?",
        f"How should a solved example for {focus} be traced before selecting an answer?",
        f"Which constraint must be preserved while applying {focus} in {payload.topic}?",
        f"What is the best final check before submitting a {focus} answer?",
    ]
    rows = []
    used_markers = set(used or set())
    for index, stem in enumerate(stems):
        marker = _fingerprint(stem)
        if marker in used_markers:
            continue
        used_markers.add(marker)
        rows.append(
            QuizQuestion(
                id=uuid.uuid4().hex,
                question=stem,
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
        if len(rows) >= payload.count:
            break
    while len(rows) < payload.count:
        stem = f"In a fresh applied scenario for {focus}, which reasoning step best proves the answer for {payload.topic}?"
        stem = f"{stem} Variant {uuid.uuid4().hex[:6]}."
        used_markers.add(_fingerprint(stem))
        rows.append(
            QuizQuestion(
                id=uuid.uuid4().hex,
                question=stem,
                options={
                    "A": "State the rule, apply it to the scenario, and verify the result",
                    "B": "Choose the longest option without checking the concept",
                    "C": "Skip the scenario details and rely on memory only",
                    "D": "Switch to an unrelated topic before answering",
                },
                correct_answer="A",
                explanation=f"The reliable method is to apply the {focus} rule to the exact scenario and verify the result.",
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
    recent_rows = recent_query.order_by(StoredQuestion.created_at.desc()).limit(50).all()
    student = db.get(Student, payload.student_id)
    syllabus_excerpt = _relevant_excerpt(student.syllabus_text or "", payload.topic, payload.subtopic) if student else ""
    notes_excerpt = _relevant_excerpt(student.notes_text or "", payload.topic, payload.subtopic) if student else ""
    plan_context = _plan_context(db, payload)
    prompt = (
        f"Student daily topic: {payload.topic}\nDaily subtopic: {payload.subtopic}\nDifficulty: {payload.difficulty}\n"
        f"Daily plan context: {plan_context or 'No matching plan context found.'}\n"
        f"Relevant syllabus excerpt:\n{syllabus_excerpt or 'No readable matching syllabus excerpt.'}\n\n"
        f"Relevant notes excerpt:\n{notes_excerpt or 'No readable matching notes excerpt.'}\n\n"
        f"Fresh quiz run nonce: {uuid.uuid4().hex}\n"
        f"Count: {payload.count}\nAvoid these previous questions from this plan/topic: {[row[0] for row in recent_rows]}\n"
        "Generate exactly Count questions. Keep all questions strictly about the daily topic/subtopic. "
        "Use the syllabus/notes excerpts as the source of truth whenever they are present. "
        "Each option must be plausible and each explanation must name why the correct answer is correct. "
        "Do not reuse a stem, example, answer pattern, or testing concept from the avoid list."
    )
    client = LLMJSONClient(max_tokens=1700)
    questions: list[QuizQuestion] = []
    if client.available:
        try:
            raw = client.complete_json(SYSTEM_PROMPT, prompt, temperature=0.75)
            if not isinstance(raw, list):
                raise AgentError("Quiz JSON was not a list.")
            used = {_fingerprint(row[0]) for row in recent_rows}
            for item in raw:
                item["id"] = uuid.uuid4().hex
                item["topic"] = payload.topic
                item["subtopic"] = payload.subtopic
                item["difficulty"] = item.get("difficulty") or payload.difficulty
                question = QuizQuestion.model_validate(item)
                marker = _fingerprint(question.question)
                if marker and marker not in used:
                    used.add(marker)
                    questions.append(question)
                if len(questions) >= payload.count:
                    break
        except Exception as exc:
            if _is_rate_limited(exc) or allow_quiz_fallback():
                questions = _local_questions(payload, {_fingerprint(row[0]) for row in recent_rows})
            else:
                raise
    elif not allow_quiz_fallback():
        raise AgentError("Groq API key is not configured. Quiz generation requires Groq.")
    if not questions:
        questions = _local_questions(payload, {_fingerprint(row[0]) for row in recent_rows})
    elif len(questions) < payload.count and allow_quiz_fallback():
        questions.extend(_local_questions(payload, {_fingerprint(row[0]) for row in recent_rows} | {_fingerprint(question.question) for question in questions})[: payload.count - len(questions)])
    elif len(questions) < payload.count:
        raise AgentError("Groq did not return enough unique quiz questions. Please generate again.")
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


def _is_rate_limited(exc: Exception) -> bool:
    text = str(exc).lower()
    return "rate_limit" in text or "rate limit" in text or "tokens per day" in text or "try again" in text
