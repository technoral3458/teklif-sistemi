import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, APP_NAME


def send_reset_email(to_email: str, reset_code: str, company_name: str = "") -> tuple[bool, str]:
    """Send password reset code via email. Returns (success, error_message)."""
    if not SMTP_HOST:
        return False, "SMTP_HOST ayarlanmamış"
    try:
        title = company_name or APP_NAME
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Şifre Sıfırlama Kodu — {title}"
        msg["From"] = f"{title} <{SMTP_FROM}>"
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

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_FROM, to_email, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
                s.ehlo()
                if SMTP_PORT == 587:
                    s.starttls()
                if SMTP_USER and SMTP_PASS:
                    s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)
