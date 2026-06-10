from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.users as udb
import auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(request: Request):
    u = auth.get_user(request)
    if u and u["is_approved"] and u["is_active"]:
        return RedirectResponse("/", 303)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/auth/login")
async def do_login(request: Request,
                   email: str = Form(...),
                   password: str = Form(...)):
    u = udb.by_email(email.strip().lower())
    if not u or not udb.check_pw(password, u["password"]):
        return templates.TemplateResponse(request, "login.html", {
            "msg": "E-posta veya şifre hatalı.",
            "msg_type": "danger",
            "tab": "login",
        })
    if not u["is_active"]:
        return templates.TemplateResponse(request, "login.html", {
            "msg": "Hesabınız pasif durumda. Lütfen yöneticiyle iletişime geçin.",
            "msg_type": "danger",
        })
    if not u["is_approved"]:
        return templates.TemplateResponse(request, "login.html", {
            "msg": "Hesabınız henüz onaylanmamış. Admin onayı bekleniyor.",
            "msg_type": "warning",
        })
    resp = RedirectResponse("/", 303)
    resp.set_cookie(
        "session",
        auth.make_session(u["id"]),
        max_age=86400 * 30,
        httponly=True,
        samesite="lax",
    )
    return resp


@router.post("/auth/register")
async def do_register(request: Request,
                      email: str = Form(...),
                      password: str = Form(...),
                      company_name: str = Form(...),
                      user_type: str = Form("dealer"),
                      phone: str = Form("")):
    ok, reason = udb.register(
        email.strip().lower(),
        password,
        company_name.strip(),
        user_type,
        phone.strip(),
    )
    if not ok:
        msg = "Bu e-posta zaten kayıtlı." if reason == "email_in_use" else "Kayıt başarısız."
        return templates.TemplateResponse(request, "login.html", {
            "msg": msg,
            "msg_type": "danger",
            "tab": "register",
        })
    return templates.TemplateResponse(request, "login.html", {
        "msg": "Kayıt başarılı! Admin onayından sonra giriş yapabilirsiniz.",
        "msg_type": "success",
        "tab": "login",
    })


@router.post("/auth/logout")
async def do_logout():
    resp = RedirectResponse("/login", 303)
    resp.delete_cookie("session")
    return resp


@router.post("/auth/forgot")
async def do_forgot(request: Request, email: str = Form(...)):
    tok = udb.reset_token(email.strip().lower())
    if tok:
        return templates.TemplateResponse(request, "login.html", {
            "msg": f"Sıfırlama kodu: {tok}  (Geliştirme modu — gerçek sistemde e-posta gönderilir)",
            "msg_type": "info",
        })
    return templates.TemplateResponse(request, "login.html", {
        "msg": "Bu e-posta ile kayıtlı hesap bulunamadı.",
        "msg_type": "danger",
    })


@router.post("/auth/reset")
async def do_reset(request: Request,
                   email: str = Form(...),
                   token: str = Form(...),
                   new_password: str = Form(...)):
    if not udb.verify_token(email.strip().lower(), token.strip()):
        return templates.TemplateResponse(request, "login.html", {
            "msg": "Geçersiz veya süresi dolmuş kod.",
            "msg_type": "danger",
        })
    udb.reset_pw(email.strip().lower(), new_password)
    return templates.TemplateResponse(request, "login.html", {
        "msg": "Şifreniz başarıyla sıfırlandı. Giriş yapabilirsiniz.",
        "msg_type": "success",
    })
