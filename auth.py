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

def _apply_admin_mode(u):
    """Yönetici modu açık kullanıcıyı, istek boyunca yönetici gibi davrandırır.

    Veritabanındaki rol değişmez; kullanıcı bayi/üretici kimliğini korur.
    Gerçek rol `base_role` alanında saklanır — yetki devrini sınırlamak için
    (yalnızca gerçek yönetici başkasına yönetici modu verebilir) bu alan kullanılır.
    """
    if not u:
        return u
    u["base_role"] = u.get("role")
    if u.get("is_admin") and u.get("role") != "admin":
        u["role"] = "admin"
        u["allowed_menus"] = ""      # yönetici menüsünün tamamı açılsın
    return u


def is_admin(user) -> bool:
    """Yönetici yetkisi var mı (gerçek admin rolü VEYA yönetici modu)."""
    if not user:
        return False
    return user.get("role") == "admin" or bool(user.get("is_admin"))


def is_true_admin(user) -> bool:
    """Veritabanında gerçekten admin rolünde mi (yönetici modu verilmiş değil)."""
    if not user:
        return False
    return (user.get("base_role") or user.get("role")) == "admin"


def get_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    uid = read_session(token)
    if not uid:
        return None
    return _apply_admin_mode(udb.by_id(uid))

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

def require_true_admin(request: Request):
    """Yalnızca gerçek yönetici — yetki devri gibi hassas işlemler için."""
    u = require_user(request)
    if not is_true_admin(u):
        raise HTTPException(status_code=403, detail="Bu işlem için tam yönetici yetkisi gerekir.")
    return u

def is_mfr(user) -> bool:
    """True if user has manufacturer capabilities (role=manufacturer OR is_manufacturer flag)."""
    return user.get("role") == "manufacturer" or bool(user.get("is_manufacturer"))


def get_impersonator(request: Request):
    """Returns the admin user if currently impersonating someone, else None."""
    token = request.cookies.get("admin_session")
    if not token:
        return None
    uid = read_session(token)
    if not uid:
        return None
    u = _apply_admin_mode(udb.by_id(uid))
    return u if (u and u["role"] == "admin") else None

