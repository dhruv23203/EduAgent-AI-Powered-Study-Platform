import base64
import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Student, User
from models.schemas import AuthRequest, AuthResponse, GoogleAuthRequest, SignupRequest, UserProfile
from utils.security import create_token, hash_password, new_user_id, read_token, user_profile, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _ensure_student(db: Session, user_id: str) -> None:
    if db.get(Student, user_id) is None:
        db.add(Student(id=user_id))
        db.commit()


def _auth_response(db: Session, user: User) -> AuthResponse:
    _ensure_student(db, user.id)
    return AuthResponse(token=create_token(user.id), user=UserProfile(**user_profile(user)))


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = User(id=new_user_id(), name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), coins=0, badges_json="[]")
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(db, user)


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _auth_response(db, user)


def _decode_google_payload(credential: str) -> dict:
    try:
        part = credential.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part.encode()))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google credential.")


@router.post("/google", response_model=AuthResponse)
def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    data = _decode_google_payload(payload.credential)
    email = str(data.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google credential does not include an email.")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(id=new_user_id(), name=data.get("name") or email.split("@")[0], email=email, password_hash=hash_password(new_user_id()), coins=0, badges_json="[]")
        db.add(user)
        db.commit()
        db.refresh(user)
    return _auth_response(db, user)


@router.get("/me", response_model=UserProfile)
def me(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> UserProfile:
    token = authorization.removeprefix("Bearer").strip()
    user_id = read_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserProfile(**user_profile(user))
