"""Sistema de autenticación basado en cookies (sesión firmada)."""
import os
import secrets
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
COOKIE_NAME = "cutervo_sess"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 días
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="cutervo-auth")


def create_session(username: str) -> str:
    return serializer.dumps({"u": username, "ts": datetime.utcnow().isoformat()})


def read_session(token: str):
    try:
        data = serializer.loads(token, max_age=COOKIE_MAX_AGE)
        return data
    except (BadSignature, SignatureExpired):
        return None


def get_user(request: Request):
    tok = request.cookies.get(COOKIE_NAME)
    if not tok:
        return None
    data = read_session(tok)
    return data["u"] if data else None


def require_login(request: Request):
    u = get_user(request)
    if not u:
        # redirección al login preservando la URL original
        next_url = str(request.url.path)
        if request.url.query:
            next_url += "?" + request.url.query
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="login required",
            headers={"Location": f"/login?next={next_url}"},
        )
    return u


def verify_password(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USER", "admin")
    expected_pass = os.getenv("ADMIN_PASS", "admin")
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_pass)


def public_results_token() -> str:
    """Token estable para enlace público de resultados, derivado de SECRET_KEY."""
    return serializer.dumps("resultados-publico")[:24]


def verify_public_results_token(token: str) -> bool:
    if not token:
        return False
    return secrets.compare_digest(token, public_results_token())
