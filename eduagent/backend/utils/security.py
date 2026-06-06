import base64
import hashlib
import hmac
import json
import os
import time
import uuid

from db.models import User


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(check, digest)


def _secret() -> bytes:
    return os.getenv("AUTH_SECRET", "dev-only-eduagent-secret").encode()


def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "iat": int(time.time())}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def read_token(token: str) -> str | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        return payload.get("sub")
    except Exception:
        return None


def user_profile(user: User) -> dict:
    try:
        badges = json.loads(user.badges_json or "[]")
    except json.JSONDecodeError:
        badges = []
    return {"id": user.id, "name": user.name, "email": user.email, "coins": user.coins, "badges": badges}


def new_user_id() -> str:
    return uuid.uuid4().hex
