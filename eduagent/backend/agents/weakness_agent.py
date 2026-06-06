from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from agents.fallbacks import resources_for_topic
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
        rows.append(
            MistakeInsight(
                topic=attempt.topic,
                subtopic=attempt.subtopic or "",
                mistakes=sum(1 for item in wrong if (item.topic, item.subtopic or "") == key),
                last_question=attempt.question_text,
                selected_answer=attempt.selected_answer,
                correct_answer=attempt.correct_answer,
                feedback="Review the rule behind this question, dry-run one solved example, then solve five similar questions.",
                resources=resources_for_topic(attempt.topic, attempt.subtopic or ""),
            )
        )
        if len(rows) >= 5:
            break
    return rows


def feedback_items(accuracy_by_topic: dict[str, float], mistakes: list[MistakeInsight]) -> list[FeedbackItem]:
    mistake_topics = {item.topic for item in mistakes}
    rows: list[FeedbackItem] = []
    for topic, accuracy in sorted(accuracy_by_topic.items(), key=lambda item: item[1]):
        priority = "High" if accuracy < 60 or topic in mistake_topics else "Medium" if accuracy < 80 else "Low"
        rows.append(
            FeedbackItem(
                topic=topic,
                accuracy=accuracy,
                priority=priority,
                diagnosis="Needs targeted revision." if priority == "High" else "Good base; improve with mixed practice." if priority == "Medium" else "Strong area; maintain with spaced revision.",
                next_steps=[
                    "Write a one-line note for every wrong answer.",
                    "Solve five targeted problems before a new topic.",
                    "Take another short quiz tomorrow.",
                ],
                resources=resources_for_topic(topic, "practice questions"),
            )
        )
    return rows[:6]
