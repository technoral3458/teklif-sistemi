from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
import db.users as udb
import db.factory as fdb
import auth
import security

router = APIRouter()
from tmpl import templates

# Bir IP'nin kayıt denemesi sınırı. Gerçek bir bayi bir kez kaydolur;
# saatte üçten fazla deneme insan davranışı değil.
REG_LIMIT_HOUR = 3
REG_LIMIT_DAY = 6


def _admin_ctx():
    company = fdb.get_company() or {}
    return {
        "admin_logo": company.get("logo_path") or "",
        "admin_company": company.get("company_name") or "",
    }


def _login_page(request, **extra):
    """Giriş sayfasını her zaman taze bir doğrulama sorusuyla döndürür.

    Soru tek kullanımlıktır; hata ekranında eskisini tekrar göstermek
    kullanıcıyı kesin ikinci bir hataya sürükler.
    """
    return templates.TemplateResponse(request, "login.html", {
        **_admin_ctx(),
        "captcha_id": security.new_captcha(),
        **extra,
    })


@router.get("/captcha/{cid}.png")
async def captcha_image(cid: str):
    """Doğrulama sorusunun resmi. Önbelleğe alınmamalı."""
    q = security.captcha_question(cid)
    if not q:
        return Response(status_code=404)
    return Response(
        security.captcha_png(q),
        media_type="image/png",
        headers={"Cache-Control": "no-store, must-revalidate", "Pragma": "no-cache"},
    )


@router.get("/captcha/new")
async def captcha_new():
    """Yenile düğmesi için yeni soru üretir."""
    cid = security.new_captcha()
    return {"cid": cid, "url": f"/captcha/{cid}.png"}


@router.get("/login")
async def login_page(request: Request):
    u = auth.get_user(request)
    if u and u["is_approved"] and u["is_active"]:
        return RedirectResponse("/", 303)
    return _login_page(request)


@router.post("/auth/login")
async def do_login(request: Request,
                   email: str = Form(...),
                   password: str = Form(...)):
    u = udb.by_email(email.strip().lower())
    if not u or not udb.check_pw(password, u["password"]):
        return _login_page(request,
            msg="E-posta veya şifre hatalı.",
            msg_type="danger",
            tab="login",
        )
    if not u["is_active"]:
        return _login_page(request,
            msg="Hesabınız pasif durumda. Lütfen yöneticiyle iletişime geçin.",
            msg_type="danger",
        )
    if not u["is_approved"]:
        return _login_page(request,
            msg="Hesabınız henüz onaylanmamış. Admin onayı bekleniyor.",
            msg_type="warning",
        )
    udb.touch_login(u["id"])
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
                      phone: str = Form(""),
                      captcha_id: str = Form(""),
                      captcha_answer: str = Form(""),
                      website_url: str = Form("")):
    """Yeni bayi/üretici kaydı — dört katmanlı bot koruması ile.

    Katmanlar birbirinin yedeği: biri aşılsa diğeri tutar.
      1. Bal küpü  — gizli alan doldurulmuş mu (formu dolduran göremez)
      2. Doğrulama — sayfadan alınmış, tek kullanımlık, 3 sn'den hızlı değil
      3. IP limiti — aynı adresten saatte/günde kaç deneme
      4. İçerik    — firma adında bağlantı/spam kelimesi
    """
    def fail(msg, tab="register"):
        return _login_page(request, msg=msg, msg_type="danger", tab=tab)

    ip = security.client_ip(request)

    # 1) Bal küpü: insan bu alanı göremez, bot formdaki her girdiyi doldurur.
    if (website_url or "").strip():
        security.record_hit(ip, "register")
        return fail("Kayıt doğrulanamadı. Lütfen tekrar deneyin.")

    # 3) IP limiti — doğrulamadan önce bakılır ki bot denemesi bedava olmasın
    if not security.rate_ok(ip, "register", REG_LIMIT_HOUR, 60):
        return fail("Bu bağlantıdan çok fazla kayıt denemesi yapıldı. "
                    "Lütfen bir saat sonra tekrar deneyin veya bizimle "
                    "telefonla iletişime geçin.")
    if not security.rate_ok(ip, "register", REG_LIMIT_DAY, 60 * 24):
        return fail("Bu bağlantıdan bugün çok fazla kayıt denemesi yapıldı. "
                    "Lütfen bizimle telefonla iletişime geçin.")
    security.record_hit(ip, "register")

    # 2) Doğrulama sorusu
    ok, why = security.check_captcha(captcha_id, captcha_answer)
    if not ok:
        return fail({
            "expired": "Doğrulama süresi doldu. Yeni soruyu cevaplayıp tekrar deneyin.",
            "too_fast": "Form çok hızlı gönderildi. Lütfen tekrar deneyin.",
            "wrong": "Doğrulama sorusunun cevabı yanlış. Lütfen tekrar deneyin.",
        }.get(why, "Doğrulama başarısız. Lütfen tekrar deneyin."))

    # 4) İçerik süzgeci
    clean_email = email.strip().lower()
    clean_name = company_name.strip()
    bad = security.bad_registration_text(clean_name, clean_email)
    if bad:
        return fail({
            "name_short": "Lütfen geçerli bir firma adı girin.",
            "no_letters": "Lütfen geçerli bir firma adı girin.",
            "link": "Firma adı veya e-posta geçersiz görünüyor.",
            "spam_word": "Firma adı geçersiz görünüyor.",
        }.get(bad, "Kayıt bilgileri geçersiz görünüyor."))

    ok, reason = udb.register(
        clean_email,
        password,
        clean_name,
        user_type,
        phone.strip(),
        reg_ip=ip,
    )
    if not ok:
        msg = "Bu e-posta zaten kayıtlı." if reason == "email_in_use" else "Kayıt başarısız."
        return fail(msg)
    return _login_page(
        request,
        msg="Kayıt başarılı! Admin onayından sonra giriş yapabilirsiniz.",
        msg_type="success",
        tab="login",
    )


@router.post("/auth/logout")
async def do_logout():
    resp = RedirectResponse("/login", 303)
    resp.delete_cookie("session")
    return resp


@router.post("/auth/forgot")
async def do_forgot(request: Request, email: str = Form(...)):
    from email_utils import send_reset_email, _get_smtp
    from config import ADMIN_COMPANY

    clean_email = email.strip().lower()
    tok = udb.reset_token(clean_email)
    if not tok:
        return _login_page(request,
            msg="Bu e-posta ile kayıtlı hesap bulunamadı.",
            msg_type="danger",
        )

    smtp_host, *_ = _get_smtp()
    if not smtp_host:
        return _login_page(request,
            msg="E-posta servisi yapılandırılmamış. Yönetici panelinden SMTP ayarlarını yapınız.",
            msg_type="warning",
        )

    ok, err = send_reset_email(clean_email, tok, ADMIN_COMPANY)
    if ok:
        return _login_page(request,
            show_reset=True,
            prefill_email=clean_email,
            msg=f"Sıfırlama kodu {clean_email} adresine gönderildi. E-postanızı kontrol edin.",
            msg_type="success",
        )
    else:
        return _login_page(request,
            msg=f"E-posta gönderilemedi: {err}",
            msg_type="danger",
        )


@router.post("/auth/reset")
async def do_reset(request: Request,
                   email: str = Form(...),
                   token: str = Form(...),
                   new_password: str = Form(...)):
    if not udb.verify_token(email.strip().lower(), token.strip()):
        return _login_page(request,
            msg="Geçersiz veya süresi dolmuş kod.",
            msg_type="danger",
        )
    udb.reset_pw(email.strip().lower(), new_password)
    return _login_page(request,
        msg="Şifreniz başarıyla sıfırlandı. Giriş yapabilirsiniz.",
        msg_type="success",
    )
