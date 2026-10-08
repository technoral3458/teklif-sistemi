import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import APP_NAME, ADMIN_EMAIL
import config as _cfg


def _get_smtp():
    """Return effective SMTP config: DB values when env vars are empty."""
    host = _cfg.SMTP_HOST
    port = _cfg.SMTP_PORT
    user = _cfg.SMTP_USER
    pw   = _cfg.SMTP_PASS
    frm  = _cfg.SMTP_FROM
    if not host:
        try:
            import db.factory as fdb
            c = fdb.get_company()
            host = c.get("smtp_host") or ""
            port = int(c.get("smtp_port") or 587)
            user = c.get("smtp_user") or ""
            pw   = c.get("smtp_pass") or ""
            frm  = c.get("smtp_from") or ""
        except Exception:
            pass
    return host, port, user, pw, frm


def send_reset_email(to_email: str, reset_code: str, company_name: str = "") -> tuple[bool, str]:
    host, port, user, pw, frm = _get_smtp()
    if not host:
        return False, "SMTP_HOST ayarlanmamış"
    try:
        title = company_name or APP_NAME
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Şifre Sıfırlama Kodu — {title}"
        msg["From"] = f"{title} <{frm}>"
        msg["To"] = to_email

        text = (
            f"Şifre sıfırlama kodunuz: {reset_code}\n\n"
            "Bu kod 30 dakika geçerlidir.\n\n"
            "Bu talebi siz yapmadıysanız bu e-postayı dikkate almayın."
        )
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f1f5f9;padding:30px;">
  <div style="max-width:460px;margin:0 auto;background:#fff;border-radius:10px;padding:36px;border:1px solid #e2e8f0;">
    <h2 style="margin:0 0 6px;color:#1e293b;font-size:20px;">{title}</h2>
    <p style="color:#64748b;margin:0 0 28px;font-size:14px;">Şifre sıfırlama talebiniz alındı.</p>
    <div style="background:#f8fafc;border:2px solid #3b82f6;border-radius:10px;padding:24px;text-align:center;margin-bottom:24px;">
      <p style="font-size:12px;color:#94a3b8;margin:0 0 10px;">Sıfırlama Kodunuz</p>
      <div style="font-size:40px;font-weight:900;letter-spacing:10px;color:#3b82f6;">{reset_code}</div>
      <p style="font-size:12px;color:#94a3b8;margin:10px 0 0;">30 dakika geçerlidir</p>
    </div>
    <p style="color:#94a3b8;font-size:12px;margin:0;">Bu talebi siz yapmadıysanız bu e-postayı dikkate almayın.</p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        return _do_send(host, port, user, pw, frm, to_email, msg)
    except Exception as e:
        return False, str(e)


def _do_send(host, port, user, pw, frm, to_email, msg) -> tuple[bool, str]:
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10) as s:
                s.login(user, pw)
                s.sendmail(frm, to_email, msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as s:
                s.ehlo()
                if port == 587:
                    s.starttls()
                if user and pw:
                    s.login(user, pw)
                s.sendmail(frm, to_email, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def _smtp_send(to_email: str, msg) -> tuple[bool, str]:
    host, port, user, pw, frm = _get_smtp()
    return _do_send(host, port, user, pw, frm, to_email, msg)


def send_admin_notification(event_label: str, details: dict) -> tuple[bool, str]:
    host, port, user, pw, frm = _get_smtp()
    if not host or not ADMIN_EMAIL:
        return False, "SMTP not configured"
    try:
        subject = f"[{APP_NAME}] {event_label}"
        rows_html = "".join(
            f"<tr><td style='padding:6px 12px;color:#64748b;font-size:13px;'>{k}</td>"
            f"<td style='padding:6px 12px;font-size:13px;font-weight:600;'>{v}</td></tr>"
            for k, v in details.items()
        )
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f1f5f9;padding:30px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:10px;padding:32px;border:1px solid #e2e8f0;">
    <h2 style="margin:0 0 4px;color:#1e293b;font-size:18px;">{APP_NAME}</h2>
    <p style="color:#64748b;margin:0 0 24px;font-size:13px;">Sipariş bildirimi</p>
    <div style="background:#f8fafc;border-radius:8px;padding:4px 0;margin-bottom:20px;">
      <div style="padding:10px 12px;background:#3b82f6;border-radius:8px 8px 0 0;">
        <span style="color:#fff;font-weight:700;font-size:14px;">{event_label}</span>
      </div>
      <table style="width:100%;border-collapse:collapse;">{rows_html}</table>
    </div>
    <p style="color:#94a3b8;font-size:11px;margin:0;">Bu otomatik bir bildirimdir.</p>
  </div>
</body>
</html>"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{APP_NAME} <{frm}>"
        msg["To"] = ADMIN_EMAIL
        msg.attach(MIMEText(html, "html", "utf-8"))
        return _smtp_send(ADMIN_EMAIL, msg)
    except Exception as e:
        return False, str(e)
