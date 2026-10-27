"""Genel formlar için bot koruması: resimli doğrulama, bal küpü, IP limiti.

Kayıt ekranına her gün onlarca bot kaydı düşmesi üzerine eklendi. Dış bir
servise (reCAPTCHA vb.) bağımlı olmamak için doğrulama resmi Pillow ile
sunucuda üretilir; anahtar/abonelik gerekmez.

Durum (doğrulama soruları ve IP sayaçları) users.db içinde tutulur —
uygulama `--workers 2` ile çalıştığı için bellekte tutmak işe yaramaz.
"""

import io
import os
import random
import re
import secrets
import sqlite3
import unicodedata

from config import USERS_DB

# ─────────────────────────── veritabanı ───────────────────────────

CAPTCHA_MIN_AGE = 3        # saniye — insan formu bu kadar hızlı dolduramaz
CAPTCHA_MAX_AGE = 1800     # saniye — 30 dk sonra soru ölür


def _c():
    con = sqlite3.connect(USERS_DB, check_same_thread=False, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def init():
    with _c() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS captchas(
            cid        TEXT PRIMARY KEY,
            answer     TEXT NOT NULL,
            created_at TEXT DEFAULT(datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS form_hits(
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ip         TEXT,
            form       TEXT,
            created_at TEXT DEFAULT(datetime('now'))
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_hits ON form_hits(form,ip,created_at)")
        _gc(c)


def _gc(c):
    """Süresi geçmiş soruları ve eski IP kayıtlarını temizler."""
    c.execute("DELETE FROM captchas WHERE created_at < datetime('now','-1 hour')")
    c.execute("DELETE FROM form_hits WHERE created_at < datetime('now','-3 days')")


# ─────────────────────────── istemci IP ───────────────────────────

def client_ip(request) -> str:
    """İstemci IP'si. Ters vekil (nginx) arkasındaysa X-Forwarded-For okunur."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first[:45]
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real[:45]
    return (request.client.host if request.client else "") or "-"


# ─────────────────────── doğrulama sorusu ─────────────────────────

def new_captcha() -> str:
    """Yeni bir toplama/çıkarma sorusu üretir, kimliğini (cid) döndürür."""
    a, b = random.randint(2, 9), random.randint(1, 8)
    if random.random() < 0.5:
        question, answer = f"{a} + {b}", a + b
    else:
        # Çıkarmada sonuç hep pozitif olsun; 0 hem tuhaf görünür hem de
        # rastgele deneyen bir bot için fazla kolay bir tahmindir.
        a, b = max(a, b), min(a, b)
        if a == b:
            a += 1
        question, answer = f"{a} - {b}", a - b
    cid = secrets.token_urlsafe(16)
    with _c() as c:
        if random.random() < 0.05:      # ~20 soruda bir süpür
            _gc(c)
        c.execute("INSERT INTO captchas(cid,answer) VALUES(?,?)",
                  (cid, f"{question}|{answer}"))
    return cid


def captcha_question(cid: str) -> str | None:
    """Soru metnini ('3 + 4') döndürür; resim çizmek için kullanılır."""
    with _c() as c:
        r = c.execute(
            "SELECT answer FROM captchas WHERE cid=?"
            " AND created_at >= datetime('now',?)",
            (cid, f"-{CAPTCHA_MAX_AGE} seconds"),
        ).fetchone()
    return r[0].split("|")[0] if r else None


def check_captcha(cid: str, given: str) -> tuple[bool, str]:
    """Cevabı doğrular. Soru tek kullanımlıktır: sonuç ne olursa olsun silinir.

    Dönen ikinci değer hata nedeni: expired / wrong / too_fast / ''.
    """
    cid = (cid or "").strip()
    with _c() as c:
        row = c.execute(
            "SELECT answer, CAST((julianday('now')-julianday(created_at))*86400 AS INTEGER)"
            " FROM captchas WHERE cid=?", (cid,)
        ).fetchone()
        if row:
            c.execute("DELETE FROM captchas WHERE cid=?", (cid,))
    if not row:
        return False, "expired"
    answer, age = row[0].split("|")[1], row[1] or 0
    if age > CAPTCHA_MAX_AGE:
        return False, "expired"
    if age < CAPTCHA_MIN_AGE:
        return False, "too_fast"      # form insan eliyle dolduruldu sayılmaz
    if re.sub(r"\D", "", given or "") != answer:
        return False, "wrong"
    return True, ""


def captcha_png(question: str) -> bytes:
    """Soruyu okunaklı, iri puntolu bir PNG olarak çizer.

    Bilerek yumuşak bir gürültü uygulanır: bot süzmek için soruyu *bilmek*
    (yani sayfayı gerçekten çekmek) yeterince zor; resmi insanın okuyamaz
    hale getirmenin gözü iyi görmeyen kullanıcılara bedeli büyük olur.
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    W, H = 220, 80
    text = f"{question} = ?"
    img = Image.new("RGB", (W, H), (248, 250, 252))
    d = ImageDraw.Draw(img)

    # arka plan gürültüsü — OCR'yi zorlar, gözü yormaz
    for _ in range(7):
        d.line([(random.randint(0, W), random.randint(0, H)),
                (random.randint(0, W), random.randint(0, H))],
               fill=(203, 213, 225), width=2)
    for _ in range(220):
        d.point((random.randint(0, W), random.randint(0, H)), fill=(180, 195, 210))

    font = _font(38)
    try:
        box = d.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        x, y = (W - tw) // 2 - box[0], (H - th) // 2 - box[1]
    except Exception:
        x, y = 24, 20
    d.text((x, y), text, font=font, fill=(15, 23, 42))

    img = img.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _font(size: int):
    from PIL import ImageFont
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)      # Pillow >= 10.1
    except Exception:
        return ImageFont.load_default()


# ─────────────────────────── IP limiti ───────────────────────────

def record_hit(ip: str, form: str):
    with _c() as c:
        c.execute("INSERT INTO form_hits(ip,form) VALUES(?,?)", (ip, form))


def hits(ip: str, form: str, minutes: int) -> int:
    with _c() as c:
        r = c.execute(
            "SELECT COUNT(*) FROM form_hits WHERE ip=? AND form=?"
            " AND created_at >= datetime('now',?)",
            (ip, form, f"-{minutes} minutes"),
        ).fetchone()
    return r[0] if r else 0


def rate_ok(ip: str, form: str, limit: int, minutes: int) -> bool:
    return hits(ip, form, minutes) < limit


# ──────────────────── içerik süzgeci (spam metni) ────────────────────

_LINKISH = re.compile(
    r"(https?://|www\.|\[url|\[link|</?a\s|\.(com|net|org|ru|xyz|top|club|online|shop)\b)",
    re.I)

# Bot kayıtlarında en sık geçen kalıplar
_SPAM_WORDS = re.compile(
    r"\b(viagra|cialis|casino|porn|sex[ -]?cam|crypto[ -]?invest|bitcoin[ -]?doubl|"
    r"loan[ -]?offer|escort|bahis|kumar|seo[ -]?servis|backlink|follower)\b", re.I)


def _no_vowel_run(s: str) -> int:
    """En uzun sesli harfsiz harf dizisinin uzunluğu (rastgele isim göstergesi)."""
    best = run = 0
    for ch in s.lower():
        if ch.isalpha() and ch not in "aeıioöuüáàâéèêíóôúûy":
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def _has_foreign_script(s: str) -> bool:
    """Kiril / Çince / Arap harfleri — Türk bayi adlarında beklenmez."""
    for ch in s:
        if ch.isalpha():
            try:
                name = unicodedata.name(ch)
            except ValueError:
                continue
            if name.split()[0] in ("CYRILLIC", "ARABIC", "CJK", "HEBREW",
                                   "DEVANAGARI", "THAI", "HANGUL"):
                return True
    return False


def bad_registration_text(company_name: str, email: str) -> str:
    """Kayıt bariz spam mı? Boş dönerse kayıt geçerli sayılır.

    Kasıtlı olarak *bariz* vakalara bakar; gerçek bir bayiyi yanlışlıkla
    reddetmek, bir botu elemekten daha pahalıdır.
    """
    name = (company_name or "").strip()
    if len(name) < 2:
        return "name_short"
    # E-postanın tamamı değil yalnızca kullanıcı adı kısmı taranır:
    # normal bir adres de ".com" ile bittiği için tamamını taramak her
    # geçerli kaydı reddederdi.
    local = (email or "").split("@")[0]
    if _LINKISH.search(name) or _LINKISH.search(local):
        return "link"
    if _SPAM_WORDS.search(name):
        return "spam_word"
    letters = sum(ch.isalpha() for ch in name)
    if letters == 0:
        return "no_letters"
    return ""


# ───────────────── şüphe puanı (mevcut kayıtları ayıklamak için) ─────────────────

_THROWAWAY = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "temp-mail.org", "yopmail.com", "trashmail.com", "sharklasers.com",
    "getnada.com", "dispostable.com", "maildrop.cc", "throwawaymail.com",
    "mailnesia.com", "fakeinbox.com", "mytemp.email", "moakt.com",
    "emailondeck.com", "tempr.email", "mail.tm", "inboxkitten.com",
}


def spam_score(u: dict, ip_counts: dict | None = None) -> tuple[int, list[str]]:
    """Kullanıcının bot olma şüphesini puanlar. 3 ve üstü 'şüpheli' sayılır.

    ip_counts: {ip: aynı IP'den kaç kayıt} — toplu kayıt saldırılarını yakalar.
    """
    name = (u.get("company_name") or "").strip()
    email = (u.get("email") or "").strip().lower()
    local, _, domain = email.partition("@")
    phone_digits = re.sub(r"\D", "", u.get("phone") or "")
    reasons = []
    score = 0

    if _LINKISH.search(name):
        score += 4
        reasons.append("Firma adında bağlantı/site adresi")
    if _SPAM_WORDS.search(name) or _SPAM_WORDS.search(local):
        score += 4
        reasons.append("Spam kelimesi")
    if _has_foreign_script(name):
        score += 3
        reasons.append("Yabancı alfabe (Kiril/Çince vb.)")
    if domain in _THROWAWAY:
        score += 3
        reasons.append("Geçici e-posta servisi")
    if _no_vowel_run(name) >= 5 or _no_vowel_run(local) >= 6:
        score += 2
        reasons.append("Rastgele harf dizisi")
    digits_in_name = sum(ch.isdigit() for ch in name)
    if len(name) and digits_in_name / len(name) > 0.4:
        score += 2
        reasons.append("Adın çoğu rakam")
    if len(name) < 3:
        score += 2
        reasons.append("Firma adı çok kısa")
    if not phone_digits:
        score += 1
        reasons.append("Telefon yok")
    elif len(phone_digits) < 10:
        score += 1
        reasons.append("Telefon eksik")
    if not u.get("is_approved") and not u.get("last_login"):
        score += 1
        reasons.append("Onaysız ve hiç giriş yapmamış")
    ip = u.get("reg_ip") or ""
    if ip_counts and ip and ip_counts.get(ip, 0) >= 3:
        score += 3
        reasons.append(f"Aynı IP'den {ip_counts[ip]} kayıt ({ip})")

    return score, reasons
