import streamlit as st
import streamlit.components.v1 as components
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management, profile_settings
import profit_management
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath

# --- CİHAZ ALGILAMA ---
def is_mobile_device():
    try:
        ua = st.context.headers.get("User-Agent", "").lower()
        return any(x in ua for x in ["mobile", "android", "iphone", "ipad", "windows phone"])
    except Exception:
        return False

IS_MOBILE = is_mobile_device()

st.set_page_config(
    page_title="Ersan Makine B2B Portalı",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed" if IS_MOBILE else "expanded"
)

# =====================================================================
# DİL MOTORU
# =====================================================================
if "lang" not in st.session_state:
    try:
        accept_lang = st.context.headers.get("Accept-Language", "")
        primary_lang = accept_lang.split(",")[0][:2].lower() if accept_lang else "tr"
        st.session_state.lang = primary_lang if primary_lang in ["tr", "en", "zh"] else "tr"
    except:
        st.session_state.lang = "tr"

DICTIONARY = {
    "tr": {
        "login_tab": "🔑 Giriş", "reg_tab": "📝 Kayıt", "forg_tab": "❓ Şifremi Unuttum",
        "email": "E-Posta Adresi", "pass": "Şifre", "rem": "Beni Hatırla", "login_btn": "GİRİŞ YAP",
        "sys_err": "Hatalı e-posta veya şifre!", "sys_wait": "Hesap onayı bekleniyor.",
        "reg_type": "Faaliyet Türü", "dealer": "Satıcı (Bayi)", "manuf": "Üretici",
        "comp_name": "Firma Tam Ünvanı *", "phone": "Telefon * (05XX...)", "reg_btn": "Kayıt Ol",
        "req_fields": "(*) alanlar zorunludur.", "email_in_use": "Bu e-posta zaten kullanımda!",
        "enter_code": "Mailinize Gelen Kodu Girin", "f_email": "Kayıtlı E-Posta Adresiniz",
        "send_reset": "Sıfırlama Kodu Gönder", "no_email": "Sistemde böyle bir e-posta bulunamadı.",
        "new_pass": "Yeni Şifre Belirleyin", "change_pass": "Şifremi Değiştir",
        "pass_changed": "Şifreniz değiştirildi! Giriş sekmesinden giriş yapabilirsiniz.",
        "wrong_code": "Hatalı kod girdiniz!",
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif Hazırla", "m_cust": "👥 Müşterilerim",
        "m_past": "📋 Geçmiş Tekliflerim", "m_order": "📦 Siparişler", "m_prof": "⚙️ Profil Ayarlarım",
        "m_deal": "🏢 Bayi Yönetimi", "m_model": "📦 Tüm Modelleri Yönet",
        "m_profit": "💰 Maliyet / Kârlılık",
        "logout": "🚪 Sistemi Kapat", "lang_sel": "Sistem Dili / Language",
        "role_admin": "Sistem Yöneticisi", "role_dealer": "Satıcı Bayi", "role_manuf": "Üretici"
    },
    "en": {
        "login_tab": "🔑 Login", "reg_tab": "📝 Register", "forg_tab": "❓ Forgot Password",
        "email": "Email Address", "pass": "Password", "rem": "Remember Me", "login_btn": "LOGIN",
        "sys_err": "Incorrect email or password!", "sys_wait": "Pending admin approval.",
        "reg_type": "Business Type", "dealer": "Dealer", "manuf": "Manufacturer",
        "comp_name": "Full Company Name *", "phone": "Phone *", "reg_btn": "Register",
        "req_fields": "(*) fields are required.", "email_in_use": "Email is already in use!",
        "enter_code": "Enter Code from Email", "f_email": "Registered Email Address",
        "send_reset": "Send Reset Code", "no_email": "No such email found in the system.",
        "new_pass": "Set New Password", "change_pass": "Change Password",
        "pass_changed": "Password changed! You can now log in.", "wrong_code": "Incorrect code!",
        "m_dash": "📊 Dashboard", "m_new": "📝 Create New Offer", "m_cust": "👥 My Customers",
        "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_prof": "⚙️ Profile Settings",
        "m_deal": "🏢 Dealer Management", "m_model": "📦 Manage Models",
        "m_profit": "💰 Cost / Profit",
        "logout": "🚪 Logout", "lang_sel": "System Language",
        "role_admin": "System Admin", "role_dealer": "Dealer", "role_manuf": "Manufacturer"
    },
    "zh": {
        "login_tab": "🔑 登录", "reg_tab": "📝 注册", "forg_tab": "❓ 忘记密码",
        "email": "电子邮件地址", "pass": "密码", "rem": "记住我", "login_btn": "登录",
        "sys_err": "电子邮件或密码错误！", "sys_wait": "等待管理员批准。",
        "reg_type": "业务类型", "dealer": "经销商", "manuf": "制造商",
        "comp_name": "公司全称 *", "phone": "电话 *", "reg_btn": "注册",
        "req_fields": "(*) 必填字段。", "email_in_use": "电子邮件已被使用！",
        "enter_code": "输入电子邮件验证码", "f_email": "注册的电子邮件地址",
        "send_reset": "发送重置验证码", "no_email": "系统中未找到此电子邮件。",
        "new_pass": "设置新密码", "change_pass": "更改密码",
        "pass_changed": "密码已更改！您现在可以登录。", "wrong_code": "验证码错误！",
        "m_dash": "📊 仪表板", "m_new": "📝 创建新报价", "m_cust": "👥 我的客户",
        "m_past": "📋 历史报价", "m_order": "📦 订单", "m_prof": "⚙️ 个人资料设置",
        "m_deal": "🏢 经销商管理", "m_model": "📦 管理所有型号",
        "m_profit": "💰 成本 / 利润",
        "logout": "🚪 退出系统", "lang_sel": "系统语言 (Language)",
        "role_admin": "系统管理员", "role_dealer": "经销商", "role_manuf": "制造商"
    }
}

def _(key):
    return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_code():
    return str(random.randint(100000, 999999))

def send_email(to_email, code, subject="Ersan Makine B2B"):
    SMTP_SERVER = "mail.ersanmakina.net"
    SMTP_PORT = 587
    SENDER_EMAIL = "sefa@ersanmakina.net"
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

    if not SENDER_PASSWORD:
        st.error("SMTP şifresi sunucuda tanımlı değil. SENDER_PASSWORD eksik.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"Ersan Makine B2B <{SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(f"Doğrulama Kodunuz: {code}", "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail gönderilemedi: {e}")
        return False

def get_base64_image(path):
    if not path:
        return ""
    if str(path).startswith("http"):
        return path

    base_name = posixpath.basename(ntpath.basename(str(path)))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]

    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                ext = os.path.splitext(p)[1].lower().replace(".", "")
                if not ext:
                    ext = "png"
                if ext == "jpg":
                    ext = "jpeg"
                with open(p, "rb") as f:
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except:
                pass
    return ""

def get_system_logo():
    try:
        conn = sqlite3.connect("factory_data.db", check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchone()
        conn.close()
        if res and res[0]:
            b64 = get_base64_image(res[0])
            if b64:
                return b64
    except:
        pass
    return ""

def add_col(conn, table, col, typ):
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except:
            pass

def repair_databases():
    conn = sqlite3.connect("users.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        company_name TEXT,
        role TEXT DEFAULT 'dealer',
        is_approved INTEGER DEFAULT 0,
        user_type TEXT DEFAULT 'Satıcı',
        phone TEXT,
        is_verified INTEGER DEFAULT 0,
        auth_code TEXT,
        session_token TEXT,
        logo_path TEXT,
        website TEXT,
        address_full TEXT,
        allowed_menus TEXT,
        allowed_categories TEXT,
        can_view_costs INTEGER DEFAULT 0
    )""")

    for col, typ in [
        ("allowed_menus", "TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'"),
        ("role", "TEXT DEFAULT 'dealer'"),
        ("allowed_categories", "TEXT DEFAULT ''"),
        ("logo_path", "TEXT DEFAULT ''"),
        ("website", "TEXT DEFAULT ''"),
        ("address_full", "TEXT DEFAULT ''"),
        ("session_token", "TEXT DEFAULT ''"),
        ("auth_code", "TEXT DEFAULT ''"),
        ("can_view_costs", "INTEGER DEFAULT 0"),
    ]:
        add_col(conn, "users", col, typ)

    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute(
            """INSERT INTO users
            (email, password, company_name, role, is_approved, is_verified, user_type, allowed_menus, can_view_costs)
            VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici',
            'm_dash,m_new,m_cust,m_past,m_order,m_prof,m_deal,m_model,m_profit', 1)""",
            ("admin@ersanmakina.net", hash_password("20132017"))
        )

    try:
        conn.execute("UPDATE users SET can_view_costs=1 WHERE role='admin'")
    except:
        pass

    conn.commit()
    conn.close()

    conn = sqlite3.connect("sales_data.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        model_id INTEGER,
        total_price REAL DEFAULT 0.0,
        conditions TEXT DEFAULT '',
        status TEXT DEFAULT 'Beklemede',
        user_id INTEGER DEFAULT 1,
        offer_date TEXT DEFAULT '',
        order_date TEXT DEFAULT '',
        total_cost REAL DEFAULT 0.0,
        total_profit REAL DEFAULT 0.0,
        profit_rate REAL DEFAULT 0.0
    )""")

    for col, typ in [
        ("user_id", "INTEGER DEFAULT 1"),
        ("total_price", "REAL DEFAULT 0.0"),
        ("conditions", "TEXT DEFAULT ''"),
        ("status", "TEXT DEFAULT 'Beklemede'"),
        ("offer_date", "TEXT DEFAULT ''"),
        ("order_date", "TEXT DEFAULT ''"),
        ("total_cost", "REAL DEFAULT 0.0"),
        ("total_profit", "REAL DEFAULT 0.0"),
        ("profit_rate", "REAL DEFAULT 0.0"),
    ]:
        add_col(conn, "offers", col, typ)

    conn.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        user_id INTEGER DEFAULT 1,
        country TEXT DEFAULT '',
        city TEXT DEFAULT '',
        authorized_person TEXT DEFAULT '',
        email TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        address TEXT DEFAULT '',
        address_full TEXT DEFAULT ''
    )""")

    for col, typ in [
        ("user_id", "INTEGER DEFAULT 1"),
        ("country", "TEXT DEFAULT ''"),
        ("city", "TEXT DEFAULT ''"),
        ("authorized_person", "TEXT DEFAULT ''"),
        ("email", "TEXT DEFAULT ''"),
        ("phone", "TEXT DEFAULT ''"),
        ("address", "TEXT DEFAULT ''"),
        ("address_full", "TEXT DEFAULT ''"),
    ]:
        add_col(conn, "customers", col, typ)

    conn.commit()
    conn.close()

    conn = sqlite3.connect("factory_data.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS company_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        logo_path TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        image_path TEXT DEFAULT ''
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        base_price REAL,
        image_path TEXT,
        specs TEXT,
        currency TEXT DEFAULT 'USD',
        port_discount REAL DEFAULT 0.0,
        compatible_options TEXT DEFAULT '',
        gallery_images TEXT DEFAULT '',
        category TEXT DEFAULT 'Diğer Makinalar',
        gallery_videos TEXT DEFAULT '',
        name_zh TEXT DEFAULT '',
        specs_zh TEXT DEFAULT '',
        user_id INTEGER DEFAULT 1,
        purchase_price REAL DEFAULT 0.0,
        sale_price REAL DEFAULT 0.0,
        shipping_cost REAL DEFAULT 0.0,
        customs_tax_rate REAL DEFAULT 3.0,
        extra_tax_rate REAL DEFAULT 10.0,
        port_cost REAL DEFAULT 0.0,
        document_cost REAL DEFAULT 0.0,
        installation_cost REAL DEFAULT 0.0,
        other_cost REAL DEFAULT 0.0,
        cost_note TEXT DEFAULT ''
    )""")

    for col, typ in [
        ("user_id", "INTEGER DEFAULT 1"),
        ("name_zh", "TEXT DEFAULT ''"),
        ("specs_zh", "TEXT DEFAULT ''"),
        ("compatible_options", "TEXT DEFAULT ''"),
        ("gallery_images", "TEXT DEFAULT ''"),
        ("gallery_videos", "TEXT DEFAULT ''"),
        ("category", "TEXT DEFAULT 'Diğer Makinalar'"),
        ("port_discount", "REAL DEFAULT 0.0"),
        ("purchase_price", "REAL DEFAULT 0.0"),
        ("sale_price", "REAL DEFAULT 0.0"),
        ("shipping_cost", "REAL DEFAULT 0.0"),
        ("customs_tax_rate", "REAL DEFAULT 3.0"),
        ("extra_tax_rate", "REAL DEFAULT 10.0"),
        ("port_cost", "REAL DEFAULT 0.0"),
        ("document_cost", "REAL DEFAULT 0.0"),
        ("installation_cost", "REAL DEFAULT 0.0"),
        ("other_cost", "REAL DEFAULT 0.0"),
        ("cost_note", "TEXT DEFAULT ''"),
    ]:
        add_col(conn, "models", col, typ)

    conn.execute("""CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opt_name TEXT,
        opt_desc TEXT,
        opt_price REAL,
        opt_image TEXT,
        sort_order INTEGER DEFAULT 0,
        allow_qty INTEGER DEFAULT 1,
        opt_name_zh TEXT DEFAULT '',
        opt_desc_zh TEXT DEFAULT '',
        user_id INTEGER DEFAULT 1,
        opt_suffix TEXT DEFAULT '',
        opt_variant_image TEXT DEFAULT '',
        purchase_price REAL DEFAULT 0.0,
        sale_price REAL DEFAULT 0.0,
        shipping_cost REAL DEFAULT 0.0,
        customs_tax_rate REAL DEFAULT 3.0,
        extra_tax_rate REAL DEFAULT 10.0,
        port_cost REAL DEFAULT 0.0,
        document_cost REAL DEFAULT 0.0,
        installation_cost REAL DEFAULT 0.0,
        other_cost REAL DEFAULT 0.0,
        cost_note TEXT DEFAULT ''
    )""")

    for col, typ in [
        ("user_id", "INTEGER DEFAULT 1"),
        ("opt_name_zh", "TEXT DEFAULT ''"),
        ("opt_desc_zh", "TEXT DEFAULT ''"),
        ("opt_suffix", "TEXT DEFAULT ''"),
        ("opt_variant_image", "TEXT DEFAULT ''"),
        ("sort_order", "INTEGER DEFAULT 0"),
        ("allow_qty", "INTEGER DEFAULT 1"),
        ("purchase_price", "REAL DEFAULT 0.0"),
        ("sale_price", "REAL DEFAULT 0.0"),
        ("shipping_cost", "REAL DEFAULT 0.0"),
        ("customs_tax_rate", "REAL DEFAULT 3.0"),
        ("extra_tax_rate", "REAL DEFAULT 10.0"),
        ("port_cost", "REAL DEFAULT 0.0"),
        ("document_cost", "REAL DEFAULT 0.0"),
        ("installation_cost", "REAL DEFAULT 0.0"),
        ("other_cost", "REAL DEFAULT 0.0"),
        ("cost_note", "TEXT DEFAULT ''"),
    ]:
        add_col(conn, "options", col, typ)

    conn.commit()
    conn.close()

repair_databases()

# =====================================================================
# OTURUM
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

for key in ["user_id", "user_role", "user_email", "allowed_menus", "close_sidebar", "mobile_menu_open"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.mobile_menu_open is None:
    st.session_state.mobile_menu_open = False

if "forgot_step" not in st.session_state:
    st.session_state.forgot_step = 1

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        conn = sqlite3.connect("users.db", check_same_thread=False)
        valid_user = conn.execute(
            "SELECT id, user_type, role, email, allowed_menus FROM users WHERE session_token=?",
            (current_token,)
        ).fetchone()
        conn.close()

        if valid_user:
            st.session_state.logged_in = True
            st.session_state.user_id = valid_user[0]
            st.session_state.user_role = valid_user[2] if valid_user[2] == "admin" else ("manufacturer" if valid_user[1] == "Üretici" else "dealer")
            st.session_state.user_email = valid_user[3]
            st.session_state.allowed_menus = valid_user[4]

# =====================================================================
# CSS
# =====================================================================
st.markdown("""
<style>
.stApp { background-color: #f8fafc; }
.block-container { padding-top: 1.4rem; }
header[data-testid="stHeader"] { background: transparent; }

.stTabs [data-baseweb="tab-list"] {
    justify-content: center; gap: 4px; margin-bottom: 20px;
    background: #f1f5f9; border-radius: 12px; padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 9px;
    padding: 9px 18px !important;
    font-size: 13px !important;
    font-weight: 700;
    color: #64748b;
    border: none !important;
    flex: 1;
    justify-content: center;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.12) !important;
}

/* Input alanları */
[data-testid="stTextInput"] > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #f8fafc !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #2563eb !important;
    background: #fff !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
}
[data-testid="stTextInput"] label {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #475569 !important;
    margin-bottom: 3px !important;
}

/* Buton */
[data-testid="stButton"] button[kind="primary"] {
    border-radius: 10px !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    letter-spacing: 0.3px !important;
    padding: 12px 20px !important;
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(37,99,235,.3) !important;
    transition: transform .15s, box-shadow .15s !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(37,99,235,.4) !important;
}

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] > div:first-child { padding: 22px 18px !important; }
[data-testid="stSidebar"] div[role="radiogroup"] {
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] div[role="radiogroup"] > label {
    width: 100% !important;
    min-height: 58px !important;
    padding: 0 18px !important;
    border-radius: 15px !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: #2563eb !important;
    border-color: #2563eb !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    font-size: 16px !important;
    font-weight: 800 !important;
    color: #334155 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p,
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: white !important;
}

.dash-hero {
    background: linear-gradient(135deg, #0f172a, #2563eb);
    padding: 30px;
    border-radius: 24px;
    color: white;
    margin-bottom: 24px;
}
.dash-hero h1 { margin: 0; font-size: 34px; font-weight: 900; }
.dash-hero p { margin: 8px 0 0 0; color: #dbeafe; font-size: 15px; }
.dash-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 22px;
    padding: 24px;
    box-shadow: 0 10px 24px rgba(15,23,42,.06);
    min-height: 130px;
}
.dash-label { color: #64748b; font-size: 12px; font-weight: 900; text-transform: uppercase; }
.dash-value { color: #0f172a; font-size: 36px; font-weight: 900; margin-top: 10px; }
.dash-blue { color:#2563eb; }
.dash-orange { color:#ea580c; }
.dash-green { color:#10b981; }

.mobile-topbar { display: none; }

.mobile-menu-note {
    text-align: center !important;
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
    border-radius: 15px !important;
    padding: 12px 14px !important;
    font-size: 13px !important;
    font-weight: 700;
    margin-bottom: 18px !important;
}

/* ===== LOGIN PAGE ===== */
.login-brand-panel {
    background: linear-gradient(155deg, #020617 0%, #0f172a 45%, #1e3a8a 100%);
    border-radius: 20px;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 28px 32px;
}
.login-form-welcome {
    font-size: 26px; font-weight: 900; color: #0f172a;
    margin: 0 0 6px 0; line-height: 1.2;
}
.login-form-sub {
    font-size: 14px; color: #64748b; font-weight: 500; margin: 0 0 28px 0;
}
.login-lang-bar {
    display: flex; justify-content: flex-end; margin-bottom: 18px;
}

/* Mobile header */
.mlh-wrap {
    background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #1e3a8a 100%);
    border-radius: 0 0 28px 28px;
    padding: 36px 24px 28px;
    text-align: center;
    margin: -18px -14px 0 -14px;
    position: relative; overflow: hidden;
}
.mlh-glow {
    position: absolute; width: 240px; height: 240px; border-radius: 50%;
    background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%);
    top: -80px; right: -60px; pointer-events: none;
}
.mlh-logo img { max-height: 52px; max-width: 180px; object-fit: contain; display: block; margin: 0 auto 14px; }
.mlh-icon { font-size: 42px; margin-bottom: 12px; }
.mlh-title { font-size: 22px; font-weight: 900; color: #ffffff; margin: 0 0 5px 0; }
.mlh-sub { font-size: 12px; color: #93c5fd; font-weight: 600; }
.mlh-lang { background: rgba(255,255,255,0.08); border-radius: 0 0 28px 28px; padding: 10px 24px; margin: 0 -14px; display: flex; justify-content: flex-end; }

/* Auth form styling */
.auth-form-container { padding: 8px 0; }
.auth-divider { display: flex; align-items: center; gap: 10px; margin: 14px 0; }
.auth-divider::before, .auth-divider::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
.auth-divider span { color: #94a3b8; font-size: 12px; font-weight: 700; }

@media (max-width:768px) {
    .block-container {
        padding-left: 14px !important;
        padding-right: 14px !important;
        padding-top: 18px !important;
        padding-bottom: 28px !important;
    }
    .mobile-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 12px 14px;
        margin-bottom: 16px;
    }
    .mobile-topbar-title { font-size: 16px; font-weight: 900; color: #0f172a; }
    .mobile-topbar-sub { font-size: 11px; color: #64748b; font-weight: 700; }
    section[data-testid="stSidebar"] {
        width: 88vw !important;
        min-width: 88vw !important;
        max-width: 88vw !important;
    }
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    button {
        min-height: 48px !important;
        border-radius: 14px !important;
        font-weight: 900 !important;
    }
    input, textarea { font-size: 16px !important; }
    .dash-card { text-align: center; margin-bottom: 10px; }
}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# BRAND PANEL HTML (sol kolon)
# =====================================================================
def build_brand_panel_html(mods, logo_b64, lang):
    slides_html = ""
    dots_html = ""
    for i, m in enumerate(mods[:8]):
        img_b64 = get_base64_image(m[1]) if m[1] else ""
        img_tag = f'<img src="{img_b64}" alt="">' if img_b64 else '<div style="font-size:52px;opacity:.25;">⚙️</div>'
        slides_html += f'<div class="slide" data-i="{i}">{img_tag}<div class="sname">{m[0]}</div></div>'
        dots_html += f'<div class="dot" data-d="{i}"></div>'

    if not slides_html:
        slides_html = '<div class="slide active"><div style="font-size:52px;opacity:.25;">⚙️</div><div class="sname">Ersan Makine</div></div>'
        dots_html = '<div class="dot active"></div>'

    if lang == "zh":
        feats = [("📋","快速报价创建和跟踪"),("📦","订单和生产工单管理"),("🏢","多用户经销商网络")]
        title, sub = "B2B订单门户", "Ersan机器销售和报价系统"
    elif lang == "en":
        feats = [("📋","Fast quote creation & tracking"),("📦","Order & production management"),("🏢","Multi-user dealer network")]
        title, sub = "B2B Order Portal", "Ersan Machine Sales & Quotation"
    else:
        feats = [("📋","Hızlı teklif oluşturma ve takip"),("📦","Sipariş ve üretim emri yönetimi"),("🏢","Çok kullanıcılı bayi/üretici ağı")]
        title, sub = "B2B Sipariş Portalı", "Ersan Makine Satış ve Teklif Sistemi"

    feats_html = "".join(f'<div class="feat"><div class="fi">{ic}</div><div class="ft">{tx}</div></div>' for ic, tx in feats)
    logo_html = f'<div class="logo-w"><img src="{logo_b64}"></div>' if logo_b64 else '<div class="icon-badge">⚙️</div>'

    return f"""<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:transparent;overflow:hidden}}
.panel{{
  background:linear-gradient(155deg,#020617 0%,#0f172a 45%,#1e3a8a 100%);
  border-radius:20px;position:relative;overflow:hidden;
  display:flex;flex-direction:column;align-items:center;
  padding:36px 24px 28px;height:680px;
}}
.g1{{position:absolute;width:360px;height:360px;border-radius:50%;
  background:radial-gradient(circle,rgba(37,99,235,.22) 0%,transparent 70%);
  top:-120px;right:-100px;pointer-events:none}}
.g2{{position:absolute;width:220px;height:220px;border-radius:50%;
  background:radial-gradient(circle,rgba(37,99,235,.12) 0%,transparent 70%);
  bottom:-60px;left:-70px;pointer-events:none}}
.logo-w{{margin-bottom:14px;z-index:1}}
.logo-w img{{max-height:50px;max-width:170px;object-fit:contain}}
.icon-badge{{width:64px;height:64px;background:rgba(37,99,235,.3);
  border:1px solid rgba(37,99,235,.5);border-radius:17px;
  display:flex;align-items:center;justify-content:center;
  font-size:28px;margin-bottom:14px;z-index:1}}
h1{{font-size:21px;font-weight:900;color:#fff;text-align:center;
  margin-bottom:5px;z-index:1;line-height:1.2}}
.sub{{font-size:11.5px;color:#93c5fd;text-align:center;
  margin-bottom:20px;z-index:1;font-weight:600}}
.showcase{{width:100%;max-width:380px;
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.1);
  border-radius:14px;overflow:hidden;
  height:210px;position:relative;margin-bottom:10px;z-index:1}}
.slide{{position:absolute;inset:0;display:none;flex-direction:column;
  align-items:center;justify-content:center;padding:12px}}
.slide img{{max-height:155px;max-width:90%;object-fit:contain}}
.sname{{position:absolute;bottom:0;left:0;right:0;
  background:rgba(0,0,0,.45);color:#e2e8f0;
  font-size:11px;font-weight:700;text-align:center;padding:6px 10px}}
.slide.active{{display:flex;animation:fi .5s ease}}
@keyframes fi{{from{{opacity:0;transform:translateX(10px)}}to{{opacity:1;transform:none}}}}
.dots{{display:flex;gap:5px;justify-content:center;margin-bottom:18px;z-index:1}}
.dot{{width:6px;height:6px;border-radius:50%;
  background:rgba(255,255,255,.25);transition:all .3s}}
.dot.active{{background:#60a5fa;width:18px;border-radius:3px}}
.feats{{width:100%;max-width:360px;z-index:1}}
.feat{{display:flex;align-items:center;gap:9px;
  padding:8px 11px;margin-bottom:6px;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.07);border-radius:10px}}
.fi{{font-size:15px;min-width:30px;height:30px;
  background:rgba(37,99,235,.35);border-radius:7px;
  display:flex;align-items:center;justify-content:center}}
.ft{{color:#cbd5e1;font-size:12px;font-weight:600}}
</style></head><body>
<div class="panel">
  <div class="g1"></div><div class="g2"></div>
  {logo_html}
  <h1>{title}</h1>
  <p class="sub">{sub}</p>
  <div class="showcase">{slides_html}</div>
  <div class="dots" id="dots">{dots_html}</div>
  <div class="feats">{feats_html}</div>
</div>
<script>
var idx=0,slides=document.querySelectorAll('.slide'),dots=document.querySelectorAll('.dot');
function show(i){{slides.forEach(function(s){{s.classList.remove('active')}});dots.forEach(function(d){{d.classList.remove('active')}});if(slides[i])slides[i].classList.add('active');if(dots[i])dots[i].classList.add('active');}}
show(0);
if(slides.length>1)setInterval(function(){{idx=(idx+1)%slides.length;show(idx);}},3500);
</script>
</body></html>"""

# =====================================================================
# AUTH FORM
# =====================================================================
def render_auth_form():
    t_login, t_reg, t_forg = st.tabs([_("login_tab"), _("reg_tab"), _("forg_tab")])

    with t_login:
        st.write("")
        le = st.text_input(_("email"), key="l_e", placeholder="ornek@firma.com").strip().lower()
        lp = st.text_input(_("pass"), type="password", key="l_p", placeholder="••••••••")
        rem = st.checkbox(_("rem"), value=True, key="l_r")
        st.write("")
        if st.button(_("login_btn"), type="primary", use_container_width=True):
            conn = sqlite3.connect("users.db")
            user = conn.execute(
                "SELECT id, user_type, is_approved, is_verified, role, allowed_menus FROM users WHERE email=? AND password=?",
                (le, hash_password(lp))
            ).fetchone()
            if user:
                if user[2] == 0:
                    st.warning(_("sys_wait"))
                    conn.close()
                else:
                    tok = str(uuid.uuid4())
                    conn.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0]))
                    if rem:
                        st.query_params["session_token"] = tok
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_role = "admin" if user[4] == "admin" else ("manufacturer" if user[1] == "Üretici" else "dealer")
                    st.session_state.user_email = le
                    st.session_state.allowed_menus = user[5]
                    conn.commit()
                    conn.close()
                    st.rerun()
            else:
                st.error(_("sys_err"))
                conn.close()

    with t_reg:
        rt = st.selectbox(_("reg_type"), [_("dealer"), _("manuf")], key="r_t")
        rc = st.text_input(_("comp_name"), key="r_c")
        rp = st.text_input(_("phone"), key="r_ph", placeholder="+90 5XX...")
        re = st.text_input(_("email"), key="r_e", placeholder="ornek@firma.com").strip().lower()
        rpw = st.text_input(_("pass"), type="password", key="r_p")
        if st.button(_("reg_btn"), type="primary", use_container_width=True):
            if all([rc, rp, re, rpw]):
                c = sqlite3.connect("users.db")
                if c.execute("SELECT id FROM users WHERE email=?", (re,)).fetchone():
                    st.error(_("email_in_use"))
                else:
                    c.execute(
                        "INSERT INTO users (email, password, company_name, phone, user_type, is_verified, is_approved, allowed_menus) VALUES (?,?,?,?,?,1,0,'m_dash,m_new,m_cust,m_past,m_order,m_prof')",
                        (re, hash_password(rpw), rc, rp, rt)
                    )
                    c.commit()
                    st.success("Kayıt Başarılı! Sistem yöneticisi onayladıktan sonra giriş yapabilirsiniz.")
                c.close()
            else:
                st.warning(_("req_fields"))

    with t_forg:
        if st.session_state.forgot_step == 1:
            fe = st.text_input(_("f_email"), key="f_e", placeholder="Kayıtlı e-postanız...").strip().lower()
            if st.button(_("send_reset"), type="primary", use_container_width=True):
                c = sqlite3.connect("users.db")
                user = c.execute("SELECT id FROM users WHERE email=?", (fe,)).fetchone()
                if user:
                    vc = generate_code()
                    c.execute("UPDATE users SET auth_code=? WHERE email=?", (vc, fe))
                    c.commit()
                    if send_email(fe, vc, "Sifre Sifirlama / Password Reset"):
                        st.session_state.temp_f_email = fe
                        st.session_state.forgot_step = 2
                        c.close()
                        st.rerun()
                else:
                    st.error(_("no_email"))
                c.close()
        elif st.session_state.forgot_step == 2:
            fc = st.text_input(_("enter_code"), max_chars=6, key="f_c")
            np = st.text_input(_("new_pass"), type="password", key="f_np")
            if st.button(_("change_pass"), type="primary", use_container_width=True):
                c = sqlite3.connect("users.db")
                user = c.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_f_email,)).fetchone()
                if user and user[0] == fc:
                    c.execute(
                        "UPDATE users SET password=?, auth_code=NULL WHERE email=?",
                        (hash_password(np), st.session_state.temp_f_email)
                    )
                    c.commit()
                    st.session_state.forgot_step = 1
                    st.success(_("pass_changed"))
                else:
                    st.error(_("wrong_code"))
                c.close()

# =====================================================================
# LOGIN SCREEN
# =====================================================================
if not st.session_state.logged_in:
    lang_opts = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}

    try:
        c_f = sqlite3.connect("factory_data.db")
        mods = c_f.execute("SELECT name, image_path FROM models").fetchall()
        c_f.close()
    except:
        mods = []

    system_logo = get_system_logo()

    # ---- MOBİL GİRİŞ ----
    if IS_MOBILE:
        if st.session_state.lang == "zh":
            title_txt, sub_txt = "B2B订单门户", "Ersan机器销售和报价系统"
            welcome_txt = "登录"
        elif st.session_state.lang == "en":
            title_txt, sub_txt = "B2B Order Portal", "Ersan Machine Sales & Quotation"
            welcome_txt = "Welcome Back"
        else:
            title_txt, sub_txt = "B2B Sipariş Portalı", "Ersan Makine Satış ve Teklif Sistemi"
            welcome_txt = "Hoş Geldiniz"

        logo_section = f'<div class="mlh-logo"><img src="{system_logo}"></div>' if system_logo else '<div class="mlh-icon">⚙️</div>'

        st.markdown(f"""
        <div class="mlh-wrap">
            <div class="mlh-glow"></div>
            {logo_section}
            <div class="mlh-title">{title_txt}</div>
            <div class="mlh-sub">{sub_txt}</div>
        </div>
        """, unsafe_allow_html=True)

        c_lang1, c_lang2 = st.columns([3, 1])
        with c_lang2:
            sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x],
                               index=list(lang_opts.keys()).index(st.session_state.lang),
                               key="main_lang_sel_mobile", label_visibility="collapsed")
            if sel != st.session_state.lang:
                st.session_state.lang = sel
                st.rerun()

        st.markdown(f"""
        <div style='padding: 20px 4px 8px 4px;'>
            <div style='font-size:22px; font-weight:900; color:#0f172a; margin-bottom:4px;'>{welcome_txt}</div>
            <div style='font-size:13px; color:#64748b; font-weight:500; margin-bottom:8px;'>
                {("Hesabınıza giriş yapın" if st.session_state.lang=="tr" else ("Sign in to your account" if st.session_state.lang=="en" else "登录您的账户"))}
            </div>
        </div>
        """, unsafe_allow_html=True)

        render_auth_form()
        st.stop()

    # ---- MASAÜSTÜ GİRİŞ ----
    if st.session_state.lang == "zh":
        welcome_txt = "欢迎回来"
        sub_welcome = "登录您的账户以继续"
    elif st.session_state.lang == "en":
        welcome_txt = "Welcome Back"
        sub_welcome = "Sign in to your account to continue"
    else:
        welcome_txt = "Hoş Geldiniz"
        sub_welcome = "Devam etmek için hesabınıza giriş yapın"

    # Üst bar: boşluk + dil seçici
    top_l, top_r = st.columns([9, 1])
    with top_r:
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x],
                           index=list(lang_opts.keys()).index(st.session_state.lang),
                           key="main_lang_sel", label_visibility="collapsed")
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()

    col_brand, col_form = st.columns([1.15, 1], gap="large")

    with col_brand:
        brand_html = build_brand_panel_html(mods, system_logo, st.session_state.lang)
        components.html(brand_html, height=680, scrolling=False)

    with col_form:
        st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='margin-bottom:28px;'>
            <div style='font-size:28px; font-weight:900; color:#0f172a; margin-bottom:7px; line-height:1.2;'>{welcome_txt}</div>
            <div style='font-size:14px; color:#64748b; font-weight:500;'>{sub_welcome}</div>
        </div>
        """, unsafe_allow_html=True)
        render_auth_form()

    st.stop()

# =====================================================================
# MOBİL ÜST MENÜ
# =====================================================================
if IS_MOBILE:
    top_left, top_right = st.columns([1, 5], vertical_alignment="center")
    with top_left:
        if st.button("☰", key="mobile_hamburger_btn", use_container_width=True):
            st.session_state.mobile_menu_open = not st.session_state.mobile_menu_open
            st.rerun()
    with top_right:
        st.markdown(f"""
        <div class="mobile-topbar">
            <div>
                <div class="mobile-topbar-title">Ersan Makine B2B</div>
                <div class="mobile-topbar-sub">{st.session_state.user_email}</div>
            </div>
            <div style="font-size:22px;">⚙️</div>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# SIDEBAR
# =====================================================================
show_sidebar = not (IS_MOBILE and not st.session_state.mobile_menu_open)

if show_sidebar:
    with st.sidebar:
        if IS_MOBILE:
            st.markdown("<div class='mobile-menu-note'>Menüden sayfa seçince bu panel otomatik kapanır.</div>", unsafe_allow_html=True)

        c_user = sqlite3.connect("users.db")
        user_data = c_user.execute("SELECT logo_path, company_name FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
        c_user.close()

        sidebar_logo = ""
        sidebar_text = user_data[1] if user_data and user_data[1] else "B2B Portal"
        if user_data and user_data[0]:
            sidebar_logo = get_base64_image(user_data[0])
        if not sidebar_logo:
            sidebar_logo = get_system_logo()

        if sidebar_logo and sidebar_logo.startswith("data:image"):
            st.markdown(f"<div style='text-align:center; margin-bottom:15px; padding:10px 0;'><img src='{sidebar_logo}' style='max-width:90%; max-height:55px; object-fit:contain;'></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; margin-bottom:15px; padding:10px 0; font-weight:900; font-size:18px; color:#1e293b;'>{sidebar_text}</div>", unsafe_allow_html=True)

        r_text = _("role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer"))
        st.markdown(f"""
        <div style='background-color:#f8fafc; padding:12px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:20px; display:flex; align-items:center; gap:10px;'>
            <div style='background:#2563eb; color:white; border-radius:50%; min-width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:bold;'>
                {st.session_state.user_email[0].upper()}
            </div>
            <div style='overflow:hidden; width:100%;'>
                <div style='font-size:12px; font-weight:800; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;'>{st.session_state.user_email}</div>
                <div style='font-size:11px; color:#64748b; font-weight:700;'>{r_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        pending_count_txt = ""
        if st.session_state.user_role == "admin":
            try:
                conn_p = sqlite3.connect("sales_data.db")
                p_count = conn_p.execute("SELECT COUNT(*) FROM offers WHERE status='Onay Bekliyor'").fetchone()[0]
                conn_p.close()
                if p_count > 0:
                    pending_count_txt = f" ({p_count})"
            except:
                pass

        if st.session_state.user_role == "admin":
            menu_items_labels = [
                _("m_dash"),
                _("m_new"),
                _("m_cust"),
                _("m_past") + pending_count_txt,
                _("m_order"),
                _("m_prof"),
                _("m_deal"),
                _("m_model"),
                _("m_profit"),
            ]
        else:
            allowed = st.session_state.allowed_menus.split(",") if st.session_state.allowed_menus else ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof"]
            v_keys = ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof", "m_deal", "m_model", "m_profit"]
            menu_items_labels = [_(k.strip()) for k in allowed if k.strip() in v_keys]

        if not menu_items_labels:
            menu_items_labels = [_("m_dash")]

        if "active_tab" not in st.session_state:
            st.session_state.active_tab = menu_items_labels[0]

        current_idx = 0
        for idx, label in enumerate(menu_items_labels):
            if st.session_state.active_tab in label or label in st.session_state.active_tab:
                current_idx = idx
                break

        def on_menu_change():
            st.session_state.active_tab = st.session_state.m_radio
            if IS_MOBILE:
                st.session_state.mobile_menu_open = False

        st.radio("MENÜ", menu_items_labels, index=current_idx, key="m_radio", on_change=on_menu_change, label_visibility="collapsed")

        st.markdown("<hr style='margin:15px 0; border:none; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

        lang_opts = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "zh": "🇨🇳 中文"}
        sel = st.selectbox("🌐 " + _("lang_sel"), list(lang_opts.keys()), format_func=lambda x: lang_opts[x],
                           index=list(lang_opts.keys()).index(st.session_state.lang), key="sb_lang")

        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()

        if st.button(_("logout"), use_container_width=True):
            c = sqlite3.connect("users.db")
            c.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
            c.commit()
            c.close()
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
else:
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = _("m_dash")

# =====================================================================
# SAYFA YÖNLENDİRME
# =====================================================================
act_tab = st.session_state.active_tab

if _("m_cust") in act_tab:
    customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")

elif _("m_new") in act_tab:
    offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")

elif _("m_model") in act_tab:
    model_management.show_product_management()

elif _("m_deal") in act_tab:
    dealer_management.show_dealer_management()

elif _("m_past") in act_tab:
    offer_management.show_offer_management(st.session_state.user_id, st.session_state.user_role)

elif _("m_order") in act_tab:
    orders_page.show_orders(st.session_state.user_id, st.session_state.user_role == "admin")

elif _("m_prof") in act_tab:
    profile_settings.show_profile_settings(st.session_state.user_id)

elif _("m_profit") in act_tab:
    profit_management.show_profit_management(st.session_state.user_role)

elif _("m_dash") in act_tab:
    conn_s = sqlite3.connect("sales_data.db")
    if st.session_state.user_role == "admin":
        my_offers = conn_s.execute("SELECT status, total_price FROM offers").fetchall()
    else:
        my_offers = conn_s.execute("SELECT status, total_price FROM offers WHERE user_id=?", (st.session_state.user_id,)).fetchall()
    conn_s.close()

    tot_o = len(my_offers)
    tot_v = sum([(x[1] or 0) for x in my_offers])
    ord_o = len([x for x in my_offers if x[0] in ["Onaylandı", "Siparişe Çevir"]])
    ord_v = sum([(x[1] or 0) for x in my_offers if x[0] in ["Onaylandı", "Siparişe Çevir"]])

    st.markdown("""
    <div class="dash-hero">
        <h1>📊 B2B Kontrol Paneli</h1>
        <p>Teklif, sipariş ve satış performansınızın güncel özeti.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='dash-card'><div class='dash-label'>Toplam Teklif</div><div class='dash-value'>{tot_o}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='dash-card'><div class='dash-label'>Toplam Hacim</div><div class='dash-value dash-blue'>{tot_v:,.0f} $</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='dash-card'><div class='dash-label'>Onaylanan Sipariş</div><div class='dash-value dash-orange'>{ord_o}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='dash-card'><div class='dash-label'>Sipariş Hacmi</div><div class='dash-value dash-green'>{ord_v:,.0f} $</div></div>", unsafe_allow_html=True)
