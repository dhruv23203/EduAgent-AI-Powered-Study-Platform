from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from agents.fallbacks import resources_for_topic
from agents.llm import LLMJSONClient
from db.models import QuizAttempt
from models.schemas import FeedbackItem, MistakeInsight, WeaknessResponse
from utils.rewards import streak_days as reward_streak_days


class WeaknessAgent:
    def analyse(self, db: Session, student_id: str) -> WeaknessResponse:
        attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
        return self.analyse_attempts(attempts)

    def analyse_attempts(self, attempts: list[QuizAttempt]) -> WeaknessResponse:
        performance = self.calculate_performance(attempts)
        return WeaknessResponse(insight=self._insight(performance), **performance)

    def calculate_performance(self, attempts: list[QuizAttempt]) -> dict[str, Any]:
        totals: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        for attempt in attempts:
            totals[attempt.topic]["total"] += 1
            totals[attempt.topic]["correct"] += int(attempt.is_correct)
        accuracy = {topic: round((v["correct"] / v["total"]) * 100, 2) for topic, v in totals.items() if v["total"]}
        return {
            "weak_topics": [topic for topic, score in accuracy.items() if score < 60],
            "strong_topics": [topic for topic, score in accuracy.items() if score >= 80],
            "accuracy_by_topic": accuracy,
        }

    def streak_days(self, db: Session, student_id: str) -> int:
        return reward_streak_days(db, student_id)

    def _insight(self, performance: dict[str, Any]) -> str:
        if not performance["accuracy_by_topic"]:
            return "Take your first quiz after today's study block so EduAgent can identify weak areas and tune revision."
        weak = performance["weak_topics"][0] if performance["weak_topics"] else "your newest topic"
        strong = ", ".join(performance["strong_topics"]) or "your consistent areas"
        return f"You are building momentum in {strong}. Spend one focused session reviewing mistakes in {weak}, then retake a short quiz."


def mistake_insights(attempts: list[QuizAttempt]) -> list[MistakeInsight]:
    wrong = [attempt for attempt in attempts if not attempt.is_correct]
    seen: set[tuple[str, str]] = set()
    rows: list[MistakeInsight] = []
    for attempt in wrong:
        key = (attempt.topic, attempt.subtopic or "")
        if key in seen:
            continue
        seen.add(key)
        related_wrong = [item for item in wrong if (item.topic, item.subtopic or "") == key]
        selected_counts: dict[str, int] = defaultdict(int)
        for item in related_wrong:
            selected_counts[item.selected_answer] += 1
        common_choice = max(selected_counts.items(), key=lambda item: item[1])[0] if selected_counts else attempt.selected_answer
        feedback = (
            f"You have {len(related_wrong)} missed question(s) in {attempt.topic}"
            f"{f' / {attempt.subtopic}' if attempt.subtopic else ''}. "
            f"The latest miss was option {attempt.selected_answer}, but the correct answer was {attempt.correct_answer}. "
            f"Your most repeated wrong choice here is {common_choice}, so compare that distractor with the correct rule before reattempting."
        )
        rows.append(
            MistakeInsight(
                topic=attempt.topic,
                subtopic=attempt.subtopic or "",
                mistakes=len(related_wrong),
                last_question=attempt.question_text,
                selected_answer=attempt.selected_answer,
                correct_answer=attempt.correct_answer,
                feedback=feedback,
                resources=resources_for_topic(attempt.topic, attempt.subtopic or ""),
            )
        )
        if len(rows) >= 5:
            break
    return rows


def feedback_items(accuracy_by_topic: dict[str, float], mistakes: list[MistakeInsight]) -> list[FeedbackItem]:
    mistakes_by_topic: dict[str, list[MistakeInsight]] = defaultdict(list)
    for mistake in mistakes:
        mistakes_by_topic[mistake.topic].append(mistake)
    rows: list[FeedbackItem] = []
    for topic, accuracy in sorted(accuracy_by_topic.items(), key=lambda item: item[1]):
        topic_mistakes = mistakes_by_topic.get(topic, [])
        priority = "High" if accuracy < 60 or topic_mistakes else "Medium" if accuracy < 80 else "Low"
        repeated = sum(item.mistakes for item in topic_mistakes)
        subtopics = ", ".join(sorted({item.subtopic for item in topic_mistakes if item.subtopic})) or "mixed subtopics"
        if priority == "High":
            diagnosis = f"{topic} needs targeted repair: {accuracy}% accuracy with {repeated} recent miss(es), mainly around {subtopics}."
        elif priority == "Medium":
            diagnosis = f"{topic} is partly stable at {accuracy}%, but mixed practice is still exposing gaps."
        else:
            diagnosis = f"{topic} is strong at {accuracy}%; keep it warm with spaced revision."
        rows.append(
            FeedbackItem(
                topic=topic,
                accuracy=accuracy,
                priority=priority,
                diagnosis=diagnosis,
                next_steps=[
                    f"Write the exact rule tested by the latest wrong {topic} question.",
                    f"Solve five {topic} problems focused on {subtopics}.",
                    f"Retake a short {topic} quiz and compare each distractor before submitting.",
                ],
                resources=resources_for_topic(topic, "practice questions"),
            )
        )
    return rows[:6]


def groq_progress_feedback(attempts: list[QuizAttempt], weakness: WeaknessResponse, mistakes: list[MistakeInsight]) -> tuple[str, list[FeedbackItem]] | None:
    client = LLMJSONClient(max_tokens=3500)
    if not client.available or not attempts:
        return None
    topic_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"correct": 0, "total": 0, "subtopics": defaultdict(lambda: {"correct": 0, "total": 0})})
    for attempt in attempts:
        stat = topic_stats[attempt.topic]
        stat["total"] += 1
        stat["correct"] += int(attempt.is_correct)
        sub = attempt.subtopic or "General"
        stat["subtopics"][sub]["total"] += 1
        stat["subtopics"][sub]["correct"] += int(attempt.is_correct)
    compact_stats = []
    for topic, stat in topic_stats.items():
        compact_stats.append(
            {
                "topic": topic,
                "accuracy": round((stat["correct"] / stat["total"]) * 100, 2) if stat["total"] else 0,
                "total": stat["total"],
                "subtopics": {
                    sub: round((values["correct"] / values["total"]) * 100, 2) if values["total"] else 0
                    for sub, values in stat["subtopics"].items()
                },
            }
        )
    wrong_samples = [
        {
            "topic": item.topic,
            "subtopic": item.subtopic,
            "question": item.last_question,
            "selected": item.selected_answer,
            "correct": item.correct_answer,
            "mistakes": item.mistakes,
        }
        for item in mistakes[:8]
    ]
    system = """You are EduAgent's Groq progress analyst. Return JSON only.
Return { "insight": string, "feedback": [ { "topic": string, "accuracy": number, "priority": "High|Medium|Low", "diagnosis": string, "next_steps": string[] } ] }.
Feedback must be specific to the topic, mention observed mistake patterns, and give concrete next actions."""
    prompt = (
        f"Accuracy by topic: {weakness.accuracy_by_topic}\nWeak topics: {weakness.weak_topics}\nStrong topics: {weakness.strong_topics}\n"
        f"Detailed stats: {compact_stats}\nRecent wrong samples: {wrong_samples}\n"
        "Create at most 6 feedback items. Do not give generic advice."
    )
    try:
        raw = client.complete_json(system, prompt, temperature=0.25)
        if not isinstance(raw, dict):
            return None
        rows = []
        for item in raw.get("feedback", [])[:6]:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic") or "").strip()
            if not topic:
                continue
            rows.append(
                FeedbackItem(
                    topic=topic,
                    accuracy=float(item.get("accuracy") if item.get("accuracy") is not None else weakness.accuracy_by_topic.get(topic, 0)),
                    priority=item.get("priority") if item.get("priority") in {"High", "Medium", "Low"} else "Medium",
                    diagnosis=str(item.get("diagnosis") or f"Review recent mistakes in {topic}."),
                    next_steps=[str(step) for step in item.get("next_steps", []) if str(step).strip()][:4]
                    or [f"Redo wrong questions from {topic}.", f"Take one fresh {topic} quiz."],
                    resources=resources_for_topic(topic, "targeted practice"),
                )
            )
        return str(raw.get("insight") or weakness.insight), rows or feedback_items(weakness.accuracy_by_topic, mistakes)
    except Exception:
        return None
