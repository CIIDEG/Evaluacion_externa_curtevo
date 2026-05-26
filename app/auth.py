"""Autenticación + autorización con roles (BD)."""
import os
import secrets
import bcrypt
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status

from .database import SessionLocal
from . import models

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
COOKIE_NAME = "cutervo_sess"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 días
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="cutervo-auth")


# ---------------------- password hashing ----------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------- sessions ----------------------
def create_session(user_id: int, username: str) -> str:
    return serializer.dumps({"id": user_id, "u": username, "ts": datetime.utcnow().isoformat()})


def read_session(token: str):
    try:
        return serializer.loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def current_user(request: Request):
    tok = request.cookies.get(COOKIE_NAME)
    if not tok:
        return None
    data = read_session(tok)
    if not data:
        return None
    db = SessionLocal()
    try:
        return db.query(models.User).filter_by(id=data.get("id"), is_active=True).first()
    finally:
        db.close()


# ---------------------- guards ----------------------
def require_user(request: Request):
    u = current_user(request)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={request.url.path}"},
        )
    return u


def can(user, action: str) -> bool:
    if user is None:
        return False
    perms = {
        "evaluador": {"manage_users","fill_qual","view_admin","download_db","view_results","ai_run"},
        "equipo":    {"fill_qual","view_admin","view_results"},
        "lector":    {"view_results"},
    }
    return action in perms.get(user.role, set())


# ---------------------- bootstrap ----------------------
def bootstrap_admin():
    """Si no hay usuarios, crear el primero con ADMIN_USER/ADMIN_PASS del .env."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            username = os.getenv("ADMIN_USER", "admin")
            password = os.getenv("ADMIN_PASS", "cambia-esto")
            u = models.User(
                username=username,
                full_name="Dr. Segundo Santos Pérez Pérez",
                email=os.getenv("ADMIN_EMAIL", ""),
                password_hash=hash_password(password),
                role="evaluador",
                is_active=True,
                must_change_password=False,
            )
            db.add(u); db.commit()
            return u
    finally:
        db.close()


# ---------------------- token público de resultados ----------------------
def public_results_token() -> str:
    return serializer.dumps("resultados-publico")[:24]


def verify_public_results_token(token: str) -> bool:
    if not token:
        return False
    return secrets.compare_digest(token, public_results_token())
