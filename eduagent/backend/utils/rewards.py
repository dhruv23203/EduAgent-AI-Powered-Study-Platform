import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from db.models import QuizAttempt, RewardLedger, StreakRecovery, StudyTaskCompletion, User
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
    query = db.query(QuizAttempt.quiz_run_id, QuizAttempt.attempted_at).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        query = query.filter(QuizAttempt.plan_id == plan_id)
    rows = query.all()
    runs = {
        run_id or f"legacy-{attempted_at.replace(microsecond=0).isoformat()}"
        for run_id, attempted_at in rows
        if attempted_at and local_date(attempted_at) == task_date
    }
    return len(runs)


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


def day_completed(db: Session, student_id: str, task_date: date, plan_id: int | None = None) -> bool:
    return {"concepts", "practice"}.issubset(completed_task_types(db, student_id, task_date, plan_id)) and quiz_count_for_date(db, student_id, task_date, plan_id) >= 3


def streak_days(db: Session, student_id: str, plan_id: int | None = None) -> int:
    attempts_query = db.query(QuizAttempt.attempted_at).filter(QuizAttempt.student_id == student_id)
    tasks_query = db.query(StudyTaskCompletion.task_date).filter(StudyTaskCompletion.student_id == student_id)
    if plan_id is not None:
        attempts_query = attempts_query.filter(QuizAttempt.plan_id == plan_id)
        tasks_query = tasks_query.filter(StudyTaskCompletion.plan_id == plan_id)
    rows = attempts_query.all()
    task_rows = tasks_query.all()
    starts = [local_date(row[0]) for row in rows if row[0]] + [row[0] for row in task_rows if row[0]]
    if not starts:
        return 0
    active = set(recovered_dates(db, student_id))
    cursor = min(starts)
    today = local_today()
    while cursor <= today:
        if day_completed(db, student_id, cursor, plan_id):
            active.add(cursor)
        cursor += timedelta(days=1)
    cursor = today if today in active else today - timedelta(days=1)
    streak = 0
    while cursor in active:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _coins_for_quiz(score: float, correct: int, streak: int) -> int:
    coins_earned = 10 + correct * 5 + (15 if score >= 80 else 0) + (25 if score == 100 else 0)
    if streak and streak % 3 == 0:
        coins_earned += 20
    return coins_earned


def _ledger_badges(db: Session, student_id: str, plan_id: int | None) -> list[str]:
    query = db.query(RewardLedger.new_badges_json).filter(RewardLedger.user_id == student_id)
    if plan_id is None:
        query = query.filter(RewardLedger.plan_id.is_(None))
    else:
        query = query.filter(RewardLedger.plan_id == plan_id)
    badges: list[str] = []
    for (raw,) in query.all():
        try:
            payload = json.loads(raw or "[]")
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, list):
            badges.extend(str(item) for item in payload if str(item).strip())
    return sorted(set(badges))


def _attempts_for_scope(db: Session, student_id: str, plan_id: int | None) -> list[QuizAttempt]:
    query = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id)
    if plan_id is None:
        return query.all()
    return query.filter(QuizAttempt.plan_id == plan_id).all()


def _derived_reward_summary(db: Session, student_id: str, plan_id: int | None, streak: int) -> RewardSummary:
    attempts = _attempts_for_scope(db, student_id, plan_id)
    grouped: dict[str, dict[str, int]] = {}
    for attempt in attempts:
        run_id = attempt.quiz_run_id or f"legacy-{attempt.attempted_at.replace(microsecond=0).isoformat()}"
        grouped.setdefault(run_id, {"correct": 0, "total": 0})
        grouped[run_id]["correct"] += int(attempt.is_correct)
        grouped[run_id]["total"] += 1
    coins = 0
    high_score = False
    perfect = False
    for values in grouped.values():
        total = values["total"]
        score = round((values["correct"] / total) * 100, 2) if total else 0
        coins += 10 + values["correct"] * 5 + (15 if score >= 80 else 0) + (25 if score == 100 else 0)
        high_score = high_score or score >= 80
        perfect = perfect or score == 100
    badges: list[str] = []
    if grouped:
        badges.append("First Quiz")
    if high_score:
        badges.append("Sharp Shooter")
    if perfect:
        badges.append("Perfect Run")
    if streak >= 3:
        badges.append("3 Day Flame")
    if streak >= 7:
        badges.append("Weekly Warrior")
    if coins >= 250:
        badges.append("Coin Collector")
    return RewardSummary(
        coins=coins,
        badges=sorted(set(badges)),
        streak_days=streak,
        streak_recoveries_available=coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )


def _ledger_summary(db: Session, student_id: str, plan_id: int | None, streak: int) -> RewardSummary | None:
    query = db.query(RewardLedger).filter(RewardLedger.user_id == student_id)
    if plan_id is None:
        query = query.filter(RewardLedger.plan_id.is_(None))
    else:
        query = query.filter(RewardLedger.plan_id == plan_id)
    rows = query.all()
    if not rows:
        return None
    coins = sum(row.coins_earned for row in rows)
    badges = _ledger_badges(db, student_id, plan_id)
    return RewardSummary(
        coins=coins,
        badges=badges,
        streak_days=streak,
        streak_recoveries_available=coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )


def reward_quiz_submission(db: Session, student_id: str, score: float, correct: int, plan_id: int | None = None, quiz_run_id: str | None = None) -> RewardSummary | None:
    user = db.get(User, student_id)
    if user is None:
        return None
    attempts_query = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id)
    if plan_id is not None:
        attempts_query = attempts_query.filter(QuizAttempt.plan_id == plan_id)
    total_attempts = attempts_query.count()
    streak = streak_days(db, student_id, plan_id)
    coins_earned = _coins_for_quiz(score, correct, streak)
    scoped_before_summary = summary_for_user(db, student_id, streak, plan_id)
    scope_before = set(scoped_before_summary.badges if scoped_before_summary is not None else [])
    badges = list(scope_before)
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
    scoped_coins_before = summary_for_user(db, student_id, streak, plan_id).coins if plan_id is not None else user.coins
    if scoped_coins_before + coins_earned >= 250:
        badges.append("Coin Collector")
    final_scope_badges = sorted(set(badges))
    new_badges = [badge for badge in final_scope_badges if badge not in scope_before]
    user.coins += coins_earned
    _save_badges(user, _badges(user) + new_badges)
    db.add(
        RewardLedger(
            user_id=student_id,
            plan_id=plan_id,
            quiz_run_id=quiz_run_id,
            coins_earned=coins_earned,
            new_badges_json=json.dumps(new_badges),
        )
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if plan_id is not None:
        scoped = summary_for_user(db, student_id, streak, plan_id)
        scoped.coins_earned = coins_earned
        scoped.new_badges = new_badges
        return scoped
    final_badges = _badges(user)
    return RewardSummary(
        coins=user.coins,
        coins_earned=coins_earned,
        badges=final_badges,
        new_badges=[badge for badge in final_badges if badge not in scope_before],
        streak_days=streak,
        streak_recoveries_available=user.coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )


def summary_for_user(db: Session, student_id: str, streak: int | None = None, plan_id: int | None = None) -> RewardSummary | None:
    user = db.get(User, student_id)
    if user is None:
        return None
    current_streak = streak_days(db, student_id, plan_id) if streak is None else streak
    if plan_id is not None:
        return _ledger_summary(db, student_id, plan_id, current_streak) or _derived_reward_summary(db, student_id, plan_id, current_streak)
    return RewardSummary(
        coins=user.coins,
        badges=_badges(user),
        streak_days=current_streak,
        streak_recoveries_available=user.coins // RECOVER_STREAK_COST,
        recover_streak_cost=RECOVER_STREAK_COST,
    )
