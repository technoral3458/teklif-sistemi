from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse
import db.users as udb
from config import SECRET_KEY

_s = URLSafeTimedSerializer(SECRET_KEY)

def make_session(user_id: int) -> str:
    return _s.dumps(user_id, salt="session")

def read_session(token: str) -> int | None:
    try:
        return _s.loads(token, salt="session", max_age=86400 * 30)
    except (BadSignature, SignatureExpired):
        return None

def get_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    uid = read_session(token)
    if not uid:
        return None
    return udb.by_id(uid)

def require_user(request: Request):
    u = get_user(request)
    if not u:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if not u["is_approved"] or not u["is_active"]:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return u

def require_admin(request: Request):
    u = require_user(request)
    if u["role"] != "admin":
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    return u
