import json
import re
import uuid
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from agents.fallbacks import allow_quiz_fallback, sanitize_document_text
from agents.llm import AgentError, LLMJSONClient
from db.models import QuizQuestion as StoredQuestion, Student, StudyPlan
from models.schemas import GenerateQuizRequest, QuizQuestion
from memory.store import ensure_student_material_indexed, format_results, search
from utils.subject import subjects_match

SYSTEM_PROMPT = """You generate exam-quality multiple choice quizzes.
Return only a JSON array. Each item must contain: question, options {A,B,C,D}, correct_answer, explanation, difficulty.
Questions must test the exact daily topic and subtopic content, not generic study planning.
Every question must be new, specific, and answerable from the named topic/subtopic.
Keep each question, option, and explanation concise.
If the subtopic is introductory, ask foundational definition/classification/property questions, not advanced implementation details unless the excerpts mention them.
Do not repeat wording, examples, option patterns, or concepts from the previous questions list.
All questions inside the same quiz must also be unique from each other."""

STRICT_JSON_PROMPT = f"""{SYSTEM_PROMPT}
Return minified valid JSON only. Do not include markdown, comments, trailing commas, or text before/after the array."""


def _fingerprint(value: str) -> str:
    value = re.sub(r"\bvariant\s+[a-f0-9]+\b", "", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


QUESTION_STOPWORDS = {"which", "what", "statement", "following", "about", "most", "accurate", "correct", "best", "describes", "the", "a", "an", "of", "in", "for", "is", "are", "as", "to"}


def _question_tokens(value: str) -> set[str]:
    return {word for word in _fingerprint(value).split() if len(word) > 2 and word not in QUESTION_STOPWORDS}


def _is_duplicate_question(candidate: str, existing: set[str]) -> bool:
    marker = _fingerprint(candidate)
    if not marker or marker in existing:
        return True
    candidate_tokens = _question_tokens(candidate)
    for previous in existing:
        previous_tokens = _question_tokens(previous)
        union = candidate_tokens | previous_tokens
        jaccard = len(candidate_tokens & previous_tokens) / len(union) if union else 1.0
        if jaccard >= 0.62 or SequenceMatcher(None, marker, previous).ratio() >= 0.84:
            return True
    return False


def _relevant_excerpt(text: str, topic: str, subtopic: str, limit: int = 1600) -> str:
    cleaned = sanitize_document_text(text)
    if not cleaned:
        return ""
    terms = [term.lower() for term in {topic, subtopic, *topic.split(), *subtopic.split()} if len(term.strip()) >= 4]
    lines = cleaned.splitlines()
    selected = [line for line in lines if any(term in line.lower() for term in terms)]
    # An empty match must stay empty. Falling back to the document prefix is what
    # previously leaked DBMS material into a DSA quiz.
    return "\n".join(selected[:24])[:limit]


def _matching_document_excerpt(text: str, filename: str, topic: str, subtopic: str) -> str:
    if not subjects_match(f"{topic} {subtopic}", filename, text):
        return ""
    return _relevant_excerpt(text, topic, subtopic)


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


def _clean_label(value: str) -> str:
    value = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "the selected concept"


def _make_question(payload: GenerateQuizRequest, question: str, options: dict[str, str], explanation: str) -> QuizQuestion:
    return QuizQuestion(
        id=uuid.uuid4().hex,
        question=question,
        options=options,
        correct_answer="A",
        explanation=explanation,
        difficulty=payload.difficulty,
        topic=payload.topic,
        subtopic=payload.subtopic,
    )


def _concept_bank(payload: GenerateQuizRequest) -> list[tuple[str, dict[str, str], str]]:
    topic_text = f"{payload.topic} {payload.subtopic}".lower()
    focus = _clean_label(payload.subtopic or payload.topic)
    rows: list[tuple[str, dict[str, str], str]] = []

    if "database fundamentals" in topic_text or "database management systems" in topic_text:
        rows.extend([
            ("What is the primary purpose of a DBMS?", {"A": "To store, organize, retrieve, and manage data reliably", "B": "To compile source code", "C": "To route network packets", "D": "To draw interface components"}, "A DBMS provides controlled storage, retrieval, and management of persistent data."),
            ("In a database, what does a schema define?", {"A": "The logical structure, relationships, and constraints of the data", "B": "Only the current row values", "C": "The operating system schedule", "D": "The user's hardware"}, "A schema describes how database data is structured and constrained."),
            ("What is metadata in a DBMS?", {"A": "Data describing structures, columns, types, and constraints", "B": "A copy of every record", "C": "Only encrypted passwords", "D": "CPU scheduling data"}, "Metadata is data about the database's own definitions and structures."),
            ("What does data independence allow?", {"A": "Changes at one schema level with minimal impact on higher levels", "B": "Applications to bypass the database", "C": "Data to have no structure", "D": "Queries to ignore types"}, "Data independence separates storage and logical details from application views."),
            ("Which responsibility belongs to a database administrator?", {"A": "Managing security, backup, recovery, and configuration", "B": "Replacing queries with packets", "C": "Removing access controls", "D": "Writing only style sheets"}, "A DBA administers availability, security, recovery, and configuration."),
            ("What is a database instance?", {"A": "The actual data stored at a particular time", "B": "The permanent schema definition", "C": "A compiler", "D": "A diagram that never changes"}, "An instance is the current database state, whereas the schema is its definition."),
            ("Why are integrity constraints used in a database?", {"A": "To keep stored data valid and consistent", "B": "To accept arbitrary values", "C": "To disable table relationships", "D": "To prevent authorized queries"}, "Constraints enforce validity rules such as keys, domains, and references."),
            ("Which abstraction level describes how data is physically stored?", {"A": "Internal or physical level", "B": "External view level", "C": "Presentation level", "D": "Authentication level"}, "The internal level describes files, indexes, and physical storage details."),
            ("What distinguishes a database from an uncoordinated file collection?", {"A": "Defined structure, controlled access, constraints, and query support", "B": "A database cannot persist data", "C": "Files automatically enforce relational integrity", "D": "A database has no metadata"}, "A DBMS coordinates structured data with querying, integrity, security, and concurrency services."),
            ("What is the role of a data model?", {"A": "To describe data, relationships, and constraints", "B": "To set monitor resolution", "C": "To replace backup and recovery", "D": "To assign CPU time"}, "A data model supplies concepts used to represent a database."),
            ("Which capability lets multiple users work with shared data safely?", {"A": "Concurrency control", "B": "Deleting the schema", "C": "Disabling transactions", "D": "Duplicating the database before every query"}, "Concurrency control coordinates simultaneous operations while protecting consistency."),
            ("What is the purpose of database backup and recovery?", {"A": "To restore consistent data after failure or loss", "B": "To remove the database schema", "C": "To make constraints optional", "D": "To prevent all concurrent access"}, "Backup and recovery protect database availability and durability after failures."),
        ])

    if "data structure" in topic_text:
        rows.extend(
            [
                (
                    "Which statement best defines a data structure?",
                    {
                        "A": "A way to organize and store data so operations can be performed efficiently",
                        "B": "A visual theme used to style an application's screens",
                        "C": "A secret key used only for encrypting files",
                        "D": "A command that runs every program in constant time",
                    },
                    "A data structure organizes data and supports operations such as access, insertion, deletion, search, and traversal.",
                ),
                (
                    "Which option is an example of a linear data structure?",
                    {
                        "A": "Stack",
                        "B": "Tree",
                        "C": "Graph",
                        "D": "Heap",
                    },
                    "A stack is linear because its elements are arranged in a sequence with restricted access at one end.",
                ),
                (
                    "Which option is an example of a non-linear data structure?",
                    {
                        "A": "Tree",
                        "B": "Array",
                        "C": "Queue",
                        "D": "Linked list",
                    },
                    "A tree is non-linear because elements form hierarchical parent-child relationships rather than one sequence.",
                ),
                (
                    "What does an abstract data type mainly specify?",
                    {
                        "A": "The behavior and operations of a type, independent of its implementation",
                        "B": "The exact physical memory addresses used by every element",
                        "C": "Only the color and layout of displayed output",
                        "D": "A rule that prevents algorithms from using conditions",
                    },
                    "An ADT describes what operations are supported and how they behave; arrays or linked lists can then implement those operations.",
                ),
                (
                    "Why do we compare operations such as search, insertion, and deletion for data structures?",
                    {
                        "A": "Different structures have different efficiency trade-offs for different operations",
                        "B": "All data structures perform every operation in exactly the same time",
                        "C": "Operations are compared only to rename variables",
                        "D": "Insertion and deletion are unrelated to how data is organized",
                    },
                    "Choosing a data structure depends on which operations must be fast for the problem.",
                ),
                (
                    "Which pairing correctly matches a structure with its relationship pattern?",
                    {
                        "A": "Tree - hierarchical parent-child relationships",
                        "B": "Queue - arbitrary network of edges",
                        "C": "Array - parent-child hierarchy",
                        "D": "Stack - weighted graph traversal",
                    },
                    "Trees model hierarchy, while arrays, stacks, and queues are linear structures.",
                ),
            ]
        )

    if "binary search tree" in topic_text or re.search(r"\bbst\b", topic_text):
        rows.extend(
            [
                (
                    "Which property must hold in a binary search tree?",
                    {
                        "A": "Keys in the left subtree are smaller than the node, and keys in the right subtree are larger",
                        "B": "Every node must have exactly three children",
                        "C": "All keys must be stored only at leaf nodes",
                        "D": "The right subtree must always contain smaller keys than the node",
                    },
                    "The BST ordering property is what makes directed search possible.",
                ),
                (
                    "What does an inorder traversal of a binary search tree produce?",
                    {
                        "A": "The keys in sorted order",
                        "B": "Only the root node",
                        "C": "The keys in random order",
                        "D": "Only the leaf nodes from right to left",
                    },
                    "For a BST, left-root-right traversal visits keys in sorted order.",
                ),
                (
                    "During search in a binary search tree, what should happen when the target key is smaller than the current node?",
                    {
                        "A": "Continue searching in the left subtree",
                        "B": "Continue searching in the right subtree",
                        "C": "Stop and report that the key is always present",
                        "D": "Swap the root with the target key immediately",
                    },
                    "The BST property places smaller keys in the left subtree.",
                ),
            ]
        )

    if "tree" in topic_text and "binary search tree" not in topic_text:
        rows.extend(
            [
                (
                    "Which statement correctly describes a tree data structure?",
                    {
                        "A": "It stores elements in a hierarchy of nodes connected by edges",
                        "B": "It stores every element in one fixed-size contiguous row",
                        "C": "It permits no parent-child relationships",
                        "D": "It is defined only by last-in-first-out access",
                    },
                    "A tree is a hierarchical non-linear data structure made of nodes and edges.",
                ),
                (
                    "In tree terminology, what is the root?",
                    {
                        "A": "The topmost node with no parent",
                        "B": "Any node with no children",
                        "C": "The last inserted node in every tree",
                        "D": "A duplicate copy of every leaf",
                    },
                    "The root is the starting node of the hierarchy and has no parent.",
                ),
            ]
        )

    if not rows:
        rows.extend(
            [
                (
                    f"Which statement best describes {focus} in {payload.topic}?",
                    {
                        "A": f"{focus} names a core concept, rule, or relationship used inside {payload.topic}",
                        "B": f"{focus} is unrelated to the behavior or properties of {payload.topic}",
                        "C": f"{focus} only changes labels and has no effect on the concept being studied",
                        "D": f"{focus} guarantees every case in {payload.topic} behaves identically",
                    },
                    f"The correct answer should describe {focus} as part of the actual subject matter of {payload.topic}.",
                ),
                (
                    f"In {payload.topic}, what should a correct explanation of {focus} include?",
                    {
                        "A": "The concept's definition, its key property, and where it applies",
                        "B": "Only a statement that the topic exists",
                        "C": "An unrelated property from a different subject",
                        "D": "A claim that no constraints or cases matter",
                    },
                    "Concept questions should test the definition, properties, and use of the selected topic.",
                ),
            ]
        )

    return rows


def _source_sentences(source_text: str) -> list[str]:
    cleaned = sanitize_document_text(source_text)
    chunks = re.split(r"(?<=[.!?])\s+|\n+|;", cleaned)
    rows = []
    instructional = re.compile(r"\b(complete|finish|quiz|practice|study|review|revise|revision|schedule|learning goal|focus point|master|write code|writing code|solve questions?)\b", re.I)
    for chunk in chunks:
        sentence = re.sub(r"\s+", " ", chunk).strip(" -•\t")
        words = re.findall(r"[A-Za-z]{3,}", sentence)
        if instructional.search(sentence) or "http" in sentence.lower() or any(char in sentence for char in "{}[]"):
            continue
        if 8 <= len(words) <= 34 and len(sentence) <= 240:
            rows.append(sentence)
    return rows[:8]


def _source_question_specs(payload: GenerateQuizRequest, source_text: str) -> list[tuple[str, dict[str, str], str]]:
    focus = _clean_label(payload.subtopic or payload.topic)
    specs = []
    distractors = [
        f"{focus} is unrelated to the organization, behavior, or properties discussed in this topic.",
        f"{focus} always gives the same result regardless of input, constraints, or structure.",
        f"{focus} is only a naming convention and has no conceptual effect.",
    ]
    for sentence in _source_sentences(source_text):
        key_terms = [word for word in re.findall(r"[A-Za-z]{4,}", sentence) if word.lower() not in QUESTION_STOPWORDS][:5]
        concept_hint = " ".join(key_terms) or focus
        specs.append(
            (
                f"What does the uploaded material establish about {concept_hint}?",
                {
                    "A": sentence,
                    "B": distractors[0],
                    "C": distractors[1],
                    "D": distractors[2],
                },
                f"The uploaded material states this point about {focus}: {sentence}",
            )
        )
    return specs


def _local_questions(payload: GenerateQuizRequest, used: set[str] | None = None, source_text: str = "") -> list[QuizQuestion]:
    focus = _clean_label(payload.subtopic or payload.topic)
    supplemental = [
        (f"What is the primary purpose of {focus}?", {"A": f"To represent or solve the core problem addressed by {focus}", "B": "To remove all constraints from a problem", "C": "To replace every related concept", "D": "To guarantee identical behavior for every input"}, f"The purpose follows from the definition and role of {focus}."),
        (f"Which property should be checked first when reasoning about {focus}?", {"A": "Its defining invariant or rule", "B": "The font used to write it", "C": "An unrelated subject label", "D": "Whether every input is identical"}, f"A defining invariant determines valid behavior for {focus}."),
        (f"When is {focus} an appropriate choice?", {"A": f"When the problem requirements match the properties of {focus}", "B": "Whenever constraints are unknown", "C": "Only when no data is present", "D": "For every problem without comparison"}, f"Selection should be based on how {focus} matches the problem constraints."),
        (f"What is the safest way to verify a solution involving {focus}?", {"A": "Check normal cases, boundary cases, and the defining rules", "B": "Test only one convenient example", "C": "Ignore constraints after implementation", "D": "Assume all cases behave alike"}, f"Boundary cases and invariants provide meaningful verification for {focus}."),
        (f"Which comparison gives the most useful understanding of {focus}?", {"A": "Compare its guarantees and trade-offs with a relevant alternative", "B": "Compare only the spelling of their names", "C": "Assume there are no trade-offs", "D": "Use an unrelated topic as the baseline"}, f"Comparing guarantees and trade-offs clarifies when to use {focus}."),
        (f"A learner can demonstrate understanding of {focus} by doing what?", {"A": "Explaining its rule and applying it to a new example", "B": "Repeating only its title", "C": "Avoiding all examples and edge cases", "D": "Claiming it works without constraints"}, f"Transfer to a new example demonstrates understanding of {focus}."),
        (f"What kind of mistake is most important to avoid with {focus}?", {"A": "Violating its assumptions or defining constraints", "B": "Using a different variable name", "C": "Adding a relevant test case", "D": "Explaining the expected result"}, f"A solution becomes invalid when the assumptions of {focus} are violated."),
        (f"How should a complex problem involving {focus} be approached?", {"A": "Identify the required properties, apply the rule step by step, then verify the result", "B": "Choose an answer before reading the constraints", "C": "Ignore intermediate states and edge cases", "D": "Replace the problem with an unrelated definition"}, f"A structured application and verification process is appropriate for {focus}."),
        (f"If an answer about {focus} fails on a boundary case, what is the likely issue?", {"A": "An assumption, transition, or invariant was handled incorrectly", "B": "The topic name is too short", "C": "All boundary cases are invalid", "D": "Verification is unnecessary"}, f"Boundary failures usually expose an incorrect assumption or invariant in {focus}."),
        (f"What evidence most strongly supports the correctness of a result using {focus}?", {"A": "It follows the defining rules and passes representative and edge cases", "B": "It is the first answer attempted", "C": "It uses the longest description", "D": "It avoids stating any assumptions"}, f"Correctness requires both rule-based reasoning and suitable tests for {focus}."),
        (f"How should efficiency be evaluated when applying {focus}?", {"A": "Relate the required time and space to the input size and constraints", "B": "Count only the words in the solution", "C": "Assume every method has equal cost", "D": "Ignore the size of the input"}, f"Efficiency is evaluated against input size and constraints when using {focus}."),
    ]
    # Never pad with generic study-skills questions. A quiz must test either a
    # concrete concept bank item or a clean academic statement from the upload.
    specs = _concept_bank(payload) + _source_question_specs(payload, source_text)
    rows: list[QuizQuestion] = []
    used_markers = set(used or set())
    for question, options, explanation in specs:
        marker = _fingerprint(question)
        if _is_duplicate_question(question, used_markers):
            continue
        used_markers.add(marker)
        rows.append(_make_question(payload, question, options, explanation))
        if len(rows) >= payload.count:
            break
    return rows


def generate_quiz(db: Session, payload: GenerateQuizRequest) -> list[QuizQuestion]:
    recent_query = db.query(StoredQuestion.question_text).filter(StoredQuestion.student_id == payload.student_id, StoredQuestion.topic == payload.topic)
    if payload.plan_id is not None:
        recent_query = recent_query.filter(StoredQuestion.plan_id == payload.plan_id)
    recent_rows = recent_query.order_by(StoredQuestion.created_at.desc()).limit(50).all()
    student = db.get(Student, payload.student_id)
    if student:
        ensure_student_material_indexed(db, student)
    syllabus_excerpt = _matching_document_excerpt(student.syllabus_text or "", student.syllabus_filename or "", payload.topic, payload.subtopic) if student else ""
    notes_excerpt = _matching_document_excerpt(student.notes_text or "", student.notes_filename or "", payload.topic, payload.subtopic) if student else ""
    plan_context = _plan_context(db, payload)
    matching_sources = set()
    if student and subjects_match(f"{payload.topic} {payload.subtopic}", student.syllabus_filename or "", student.syllabus_text or ""):
        matching_sources.add("syllabus")
    if student and subjects_match(f"{payload.topic} {payload.subtopic}", student.notes_filename or "", student.notes_text or ""):
        matching_sources.add("notes")
    memory_excerpt = format_results(search(db, payload.student_id, f"{payload.topic} {payload.subtopic}", limit=4, source_types=matching_sources), max_chars=4000) if matching_sources else "No subject-matching uploaded material found."
    # Plan activities/focus points are instructions, not academic evidence.
    local_source = "\n".join(item for item in [memory_excerpt, notes_excerpt, syllabus_excerpt] if item and not item.startswith("No "))
    prompt = (
        f"Student daily topic: {payload.topic}\nDaily subtopic: {payload.subtopic}\nDifficulty: {payload.difficulty}\n"
        f"Daily plan context: {plan_context or 'No matching plan context found.'}\n"
        f"Relevant syllabus excerpt:\n{syllabus_excerpt or 'No readable matching syllabus excerpt.'}\n\n"
        f"Relevant notes excerpt:\n{notes_excerpt or 'No readable matching notes excerpt.'}\n\n"
        f"Vector-retrieved study material:\n{memory_excerpt}\n\n"
        f"Fresh quiz run nonce: {uuid.uuid4().hex}\n"
        f"Count: {payload.count}\nAvoid these previous questions from this plan/topic: {[row[0] for row in recent_rows]}\n"
        "Generate exactly Count questions. Keep all questions strictly about the daily topic/subtopic. "
        "Use the syllabus/notes excerpts as the source of truth whenever they are present. "
        "Do not jump to advanced neighboring topics unless they are explicitly named in the daily topic, subtopic, syllabus excerpt, notes excerpt, or plan focus points. "
        "Each option must be plausible and each explanation must name why the correct answer is correct. "
        "Do not reuse a stem, example, answer pattern, or testing concept from the avoid list."
    )
    client = LLMJSONClient(max_tokens=3200)
    questions: list[QuizQuestion] = []
    if client.available:
        try:
            try:
                raw = client.complete_json(SYSTEM_PROMPT, prompt, temperature=0.55)
            except AgentError as exc:
                if "json" not in str(exc).lower():
                    raise
                raw = client.complete_json(STRICT_JSON_PROMPT, prompt, temperature=0.2)
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
                if marker and not _is_duplicate_question(question.question, used):
                    used.add(marker)
                    questions.append(question)
                if len(questions) >= payload.count:
                    break
        except Exception as exc:
            if allow_quiz_fallback():
                questions = _local_questions(payload, {_fingerprint(row[0]) for row in recent_rows}, local_source)
            else:
                raise
    elif allow_quiz_fallback():
        questions = _local_questions(payload, {_fingerprint(row[0]) for row in recent_rows}, local_source)
    else:
        raise AgentError("Groq API key is not configured. Quiz generation requires Groq.")
    if not questions:
        if allow_quiz_fallback():
            questions = _local_questions(payload, {_fingerprint(row[0]) for row in recent_rows}, local_source)
        else:
            raise AgentError("Groq did not return quiz questions. Please generate again.")
    elif len(questions) < payload.count and allow_quiz_fallback():
        questions.extend(_local_questions(payload, {_fingerprint(row[0]) for row in recent_rows} | {_fingerprint(question.question) for question in questions}, local_source)[: payload.count - len(questions)])
    elif len(questions) < payload.count:
        raise AgentError("Groq did not return enough unique quiz questions. Please generate again.")
    if len(questions) < payload.count:
        raise AgentError(f"Only {len(questions)} unique concept questions were available; {payload.count} are required. Please retry or move to the next topic.")
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
    return any(
        marker in text
        for marker in (
            "rate_limit",
            "rate limit",
            "rate-limited",
            "rate limited",
            "tokens per day",
            "temporarily unavailable",
            "cooling key slots",
            "try again",
        )
    )
