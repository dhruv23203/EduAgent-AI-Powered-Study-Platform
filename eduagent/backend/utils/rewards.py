import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from db.models import QuizAttempt, StreakRecovery, StudyTaskCompletion, User
from models.schemas import RewardSummary
from utils.timezone import local_date, local_today

RECOVER_STREAK_COST = 75


def _badges(user: User) -> list[str]:
    try:
        payload = json.loads(user.badges_json or "[]")
        return payload if isinstance(payload, list) else []
    except json.JSONDecodeError:
        return []


def _save_badges(user: User, badges: list[str]) -> None:
    user.badges_json = json.dumps(sorted(set(badges)))


def quiz_count_for_date(db: Session, student_id: str, task_date: date, plan_id: int | None = None) -> int:
    query = db.query(QuizAttempt.attempted_at).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        query = query.filter(QuizAttempt.plan_id == plan_id)
    rows = query.all()
    return sum(1 for row in rows if local_date(row[0]) == task_date)


def completed_task_types(db: Session, student_id: str, task_date: date, plan_id: int | None = None) -> set[str]:
    query = db.query(StudyTaskCompletion.task_type).filter(StudyTaskCompletion.student_id == student_id, StudyTaskCompletion.task_date == task_date)
    if plan_id is not None:
        query = query.filter(StudyTaskCompletion.plan_id == plan_id)
    rows = (
        query.all()
    )
    return {row[0] for row in rows}


def recovered_dates(db: Session, student_id: str) -> set[date]:
    rows = db.query(StreakRecovery.recovered_date).filter(StreakRecovery.user_id == student_id).all()
    return {row[0] for row in rows}


def day_completed(db: Session, student_id: str, task_date: date) -> bool:
    return {"concepts", "practice"}.issubset(completed_task_types(db, student_id, task_date)) and quiz_count_for_date(db, student_id, task_date) >= 3


def streak_days(db: Session, student_id: str) -> int:
    rows = db.query(QuizAttempt.attempted_at).filter(QuizAttempt.student_id == student_id).all()
    task_rows = db.query(StudyTaskCompletion.task_date).filter(StudyTaskCompletion.student_id == student_id).all()
    starts = [local_date(row[0]) for row in rows if row[0]] + [row[0] for row in task_rows if row[0]]
    if not starts:
        return 0
    active = set(recovered_dates(db, student_id))
    cursor = min(starts)
    today = local_today()
    while cursor <= today:
        if day_completed(db, student_id, cursor):
            active.add(cursor)
        cursor += timedelta(days=1)
    cursor = today if today in active else today - timedelta(days=1)
    streak = 0
    while cursor in active:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def reward_quiz_submission(db: Session, student_id: str, score: float, correct: int) -> RewardSummary | None:
    user = db.get(User, student_id)
    if user is None:
        return None
    total_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).count()
    streak = streak_days(db, student_id)
    coins_earned = 10 + correct * 5 + (15 if score >= 80 else 0) + (25 if score == 100 else 0)
    if streak and streak % 3 == 0:
        coins_earned += 20
    badges = _badges(user)
    before = set(badges)
    if total_attempts >= 1:
        badges.append("First Quiz")
    if score >= 80:
        badges.append("Sharp Shooter")
    if score == 100:
        badges.append("Perfect Run")
    if streak >= 3:
        badges.append("3 Day Flame")
    if streak >= 7:
        badges.append("Weekly Warrior")
    if user.coins + coins_earned >= 250:
        badges.append("Coin Collector")
    user.coins += coins_earned
    _save_badges(user, badges)
    db.add(user)
    db.commit()
    db.refresh(user)
    final_badges = _badges(user)
    return RewardSummary(
        coins=user.coins,
        coins_earned=coins_earned,
        badges=final_badges,
        new_badges=[badge for badge in final_badges if badge not in before],
        streak_days=streak,
        streak_recoveries_available=user.coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )


def summary_for_user(db: Session, student_id: str, streak: int | None = None) -> RewardSummary | None:
    user = db.get(User, student_id)
    if user is None:
        return None
    current_streak = streak_days(db, student_id) if streak is None else streak
    return RewardSummary(
        coins=user.coins,
        badges=_badges(user),
        streak_days=current_streak,
        streak_recoveries_available=user.coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )
