from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import StreakRecovery, User
from models.schemas import RewardSummary, StreakRecoveryRequest
from utils.rewards import RECOVER_STREAK_COST, summary_for_user
from utils.timezone import local_today

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.post("/recover-streak", response_model=RewardSummary)
def recover_streak(payload: StreakRecoveryRequest, db: Session = Depends(get_db)) -> RewardSummary:
    user = db.get(User, payload.student_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.coins < RECOVER_STREAK_COST:
        raise HTTPException(status_code=400, detail="Not enough coins to recover streak.")
    target_date = local_today() - timedelta(days=1)
    exists = db.query(StreakRecovery).filter(StreakRecovery.user_id == payload.student_id, StreakRecovery.recovered_date == target_date).first()
    if exists:
        raise HTTPException(status_code=400, detail="That missed day is already recovered.")
    user.coins -= RECOVER_STREAK_COST
    db.add(user)
    db.add(StreakRecovery(user_id=payload.student_id, recovered_date=target_date, spent_coins=RECOVER_STREAK_COST))
    db.commit()
    return summary_for_user(db, payload.student_id) or RewardSummary()
