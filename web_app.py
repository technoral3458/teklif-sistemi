import streamlit as st
import streamlit.components.v1 as components
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management, profile_settings
import profit_management
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
try:
    import backup_management
    _HAS_BACKUP = True
except ImportError:
    _HAS_BACKUP = False
try:
    import credit_calculator
    _HAS_CREDIT = True
except ImportError:
    _HAS_CREDIT = False
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
        "m_backup": "🗄️ Yedekleme", "m_leads": "📨 Teklif Talepleri", "m_credit": "💳 Kredi Hesapla",
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
        "m_backup": "🗄️ Backup", "m_leads": "📨 Offer Requests", "m_credit": "💳 Credit Calc",
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
        "m_backup": "🗄️ 备份管理", "m_leads": "📨 询价请求", "m_credit": "💳 贷款计算",
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

.stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px; }
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 10px;
    padding: 10px 20px !important;
    font-size: 14px !important;
    font-weight: 700;
    color: #64748b;
    border: 1px solid transparent;
}
.stTabs [aria-selected="true"] {
    background-color: #2563eb !important;
    color: white !important;
    border-color: #2563eb !important;
}

.login-desktop-title {
    text-align: center;
    color: #0f172a;
    margin-bottom: 30px;
    font-weight: 900;
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

.mobile-login-shell { width: 100%; max-width: 520px; margin: 0 auto; }
.mobile-login-logo-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 22px 18px;
    margin: 16px 0 18px 0;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
    text-align: center;
}
.mobile-login-logo-card img { max-width: 78%; max-height: 82px; object-fit: contain; }
.mobile-login-icon {
    width: 76px;
    height: 76px;
    border-radius: 24px;
    background: linear-gradient(135deg, #0f172a, #2563eb);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 14px auto;
    font-size: 36px;
}
.mobile-login-title { font-size: 25px; font-weight: 950; color: #0f172a; text-align: center; }
.mobile-login-subtitle { font-size: 13px; font-weight: 700; color: #64748b; text-align: center; margin-top: 6px; }
.mobile-login-card-title { text-align: center; font-size: 22px; font-weight: 950; color: #0f172a; margin: 8px 0 18px 0; }

@media (max-width:768px) {
    .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
        padding-top: 10px !important;
        padding-bottom: 28px !important;
    }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    button { min-height: 46px !important; border-radius: 13px !important; font-weight: 900 !important; }
    input, textarea { font-size: 16px !important; }
    .dash-card { text-align: center; margin-bottom: 10px; }
}
.mob-topbar-wrap {
    display: flex; align-items: center; gap: 0;
    background: #fff; border: 1px solid #e2e8f0;
    border-radius: 16px; padding: 6px 10px 6px 6px;
    margin-bottom: 10px;
}
.mob-page-title {
    font-size: 14px; font-weight: 900; color: #0f172a;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;
}
.mob-avatar {
    width: 32px; height: 32px; border-radius: 50%;
    color: white; font-size: 13px; font-weight: 900;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.mob-menu-item-active {
    background: #2563eb; color: white; padding: 14px 18px;
    border-radius: 13px; font-size: 15px; font-weight: 900;
    margin-bottom: 6px; text-align: left;
}
.mob-menu-sep { height: 1px; background: #e2e8f0; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# AUTH FORM
# =====================================================================
def render_auth_form():
    with st.container(border=True):
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

    if IS_MOBILE:
        st.markdown("<div class='mobile-login-shell'>", unsafe_allow_html=True)
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x],
                           index=list(lang_opts.keys()).index(st.session_state.lang),
                           key="main_lang_sel_mobile", label_visibility="collapsed")
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()

        mobile_logo = get_system_logo()
        if mobile_logo and mobile_logo.startswith("data:image"):
            st.markdown(f"""
            <div class="mobile-login-logo-card">
                <img src="{mobile_logo}">
                <div class="mobile-login-title">B2B Sipariş Portalı</div>
                <div class="mobile-login-subtitle">Ersan Makine Satış ve Teklif Sistemi</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="mobile-login-logo-card">
                <div class="mobile-login-icon">⚙️</div>
                <div class="mobile-login-title">B2B Sipariş Portalı</div>
                <div class="mobile-login-subtitle">Ersan Makine Satış ve Teklif Sistemi</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='mobile-login-card-title'>Giriş Yap</div>", unsafe_allow_html=True)
        render_auth_form()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    c1, c2, c3 = st.columns([8, 1, 1])
    with c3:
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x],
                           index=list(lang_opts.keys()).index(st.session_state.lang),
                           key="main_lang_sel", label_visibility="collapsed")
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()

    st.write("")
    st.write("")

    col_slider, col_form = st.columns([1.2, 1], gap="large")

    with col_slider:
        try:
            c_f = sqlite3.connect("factory_data.db")
            mods = c_f.execute("SELECT name, image_path FROM models").fetchall()
            c_f.close()
        except:
            mods = []

        s_h = ""
        if mods:
            for m in mods:
                img_b64 = get_base64_image(m[1]) if m[1] else get_system_logo()
                img_tag = f'<img src="{img_b64}">' if img_b64 else '<div style="font-size:80px; margin-top:100px;">⚙️</div>'
                s_h += f'<div class="mySlides fade">{img_tag}<div class="slide-text">{m[0]}</div></div>'

        if s_h:
            slider_html = f"""
            <html><head><style>
            body {{ margin:0; padding:0; background:transparent; overflow:hidden; font-family:sans-serif; }}
            .slideshow-container {{ position:relative; width:100%; height:450px; border-radius:20px; display:flex; align-items:center; justify-content:center; background:#ffffff; box-shadow:0 4px 6px rgba(0,0,0,0.05); border:1px solid #e2e8f0; }}
            .mySlides {{ display:none; text-align:center; width:100%; height:100%; position:relative; }}
            img {{ max-height:380px; max-width:85%; object-fit:contain; position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); }}
            .slide-text {{ color:#0f172a; font-size:16px; font-weight:900; position:absolute; bottom:20px; left:50%; transform:translateX(-50%); background:rgba(255,255,255,0.85); padding:10px 25px; border-radius:30px; }}
            .fade {{ animation-name:fade; animation-duration:1.5s; }}
            @keyframes fade {{ from {{opacity:0.3; transform:scale(0.95);}} to {{opacity:1; transform:scale(1);}} }}
            </style></head><body>
            <div class="slideshow-container">{s_h}</div>
            <script>
            let sI=0; show();
            function show(){{
                let s=document.getElementsByClassName("mySlides");
                if(s.length===0)return;
                for(let i=0;i<s.length;i++) s[i].style.display="none";
                sI++; if(sI>s.length)sI=1;
                s[sI-1].style.display="block";
                setTimeout(show,3500);
            }}
            </script></body></html>
            """
            components.html(slider_html, height=480)
        else:
            st.info("Sistemde henüz kayıtlı makine bulunmuyor.")

    with col_form:
        st.markdown("<h2 class='login-desktop-title'>B2B Sipariş Portalı</h2>", unsafe_allow_html=True)
        render_auth_form()

    st.stop()

# =====================================================================
# MENÜ ÖĞELERİ HESAPLA
# =====================================================================
_pending_txt = ""
if st.session_state.user_role == "admin":
    try:
        _cp = sqlite3.connect("sales_data.db")
        _pc = _cp.execute("SELECT COUNT(*) FROM offers WHERE status='Onay Bekliyor'").fetchone()[0]
        _cp.close()
        if _pc > 0:
            _pending_txt = f" ({_pc})"
    except:
        pass

if st.session_state.user_role == "admin":
    _all_menu = [
        _("m_dash"), _("m_new"), _("m_cust"),
        _("m_past") + _pending_txt,
        _("m_order"), _("m_prof"), _("m_deal"),
        _("m_model"), _("m_profit"),
        _("m_backup"), _("m_leads"), _("m_credit"),
    ]
else:
    _allowed_keys = st.session_state.allowed_menus.split(",") if st.session_state.allowed_menus else ["m_dash","m_new","m_cust","m_past","m_order","m_prof"]
    _valid_keys = ["m_dash","m_new","m_cust","m_past","m_order","m_prof","m_deal","m_model","m_profit","m_backup","m_leads","m_credit"]
    _all_menu = [_(k.strip()) for k in _allowed_keys if k.strip() in _valid_keys]

if not _all_menu:
    _all_menu = [_("m_dash")]

if "active_tab" not in st.session_state:
    st.session_state.active_tab = _all_menu[0]

def _logout():
    _lc = sqlite3.connect("users.db")
    _lc.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
    _lc.commit()
    _lc.close()
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

# =====================================================================
# MOBİL MENÜ (Sidebar yok — inline render)
# =====================================================================
if IS_MOBILE:
    _rc = {"admin": "#dc2626", "manufacturer": "#d97706"}.get(st.session_state.user_role, "#2563eb")
    _ui = (st.session_state.user_email or "U")[0].upper()
    _open = bool(st.session_state.mobile_menu_open)
    _page_lbl = "― Menü" if _open else st.session_state.get("active_tab", "")

    # Top bar: hamburger | sayfa adı | avatar
    _hcol, _tcol = st.columns([1, 7])
    with _hcol:
        if st.button("✕" if _open else "☰", key="mob_ham", use_container_width=True):
            st.session_state.mobile_menu_open = not _open
    with _tcol:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:6px 0 4px 4px;'>"
            f"<span style='font-size:13px;font-weight:900;color:#0f172a;overflow:hidden;"
            f"text-overflow:ellipsis;white-space:nowrap;flex:1;'>{_page_lbl}</span>"
            f"<div style='width:32px;height:32px;border-radius:50%;background:{_rc};"
            f"color:white;font-size:13px;font-weight:900;display:flex;align-items:center;"
            f"justify-content:center;flex-shrink:0;'>{_ui}</div></div>",
            unsafe_allow_html=True
        )
    st.markdown("<hr style='margin:2px 0 8px 0;border:none;border-top:2px solid #e2e8f0;'>", unsafe_allow_html=True)

    if _open:
        # Kullanıcı kartı
        _r_lbl = _("role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer"))
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;background:#f8fafc;"
            f"border:1px solid #e2e8f0;border-radius:12px;padding:10px 12px;margin-bottom:12px;'>"
            f"<div style='background:{_rc};color:white;border-radius:50%;min-width:36px;height:36px;"
            f"display:flex;align-items:center;justify-content:center;font-weight:900;font-size:14px;'>{_ui}</div>"
            f"<div style='overflow:hidden;flex:1;'>"
            f"<div style='font-size:12px;font-weight:800;color:#0f172a;white-space:nowrap;"
            f"overflow:hidden;text-overflow:ellipsis;'>{st.session_state.user_email}</div>"
            f"<span style='background:{_rc}22;color:{_rc};padding:1px 7px;border-radius:5px;"
            f"font-size:10px;font-weight:800;'>{_r_lbl}</span></div></div>",
            unsafe_allow_html=True
        )

        # Menü butonları
        _act = st.session_state.get("active_tab", "")
        for _mi in _all_menu:
            _is_act = (_act in _mi) or (_mi in _act)
            if _is_act:
                st.markdown(
                    f"<div style='background:#2563eb;color:white;padding:14px 18px;"
                    f"border-radius:13px;font-size:15px;font-weight:900;margin-bottom:6px;'>{_mi}</div>",
                    unsafe_allow_html=True
                )
            else:
                if st.button(_mi, key=f"mob_nav_{_mi}", use_container_width=True):
                    st.session_state.active_tab = _mi
                    st.session_state.mobile_menu_open = False
                    st.rerun()

        st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

        # Dil seçimi
        _ml1, _ml2, _ml3 = st.columns(3)
        for _mc, (_lk, _lv) in zip([_ml1, _ml2, _ml3], [("tr","🇹🇷 TR"),("en","🇬🇧 EN"),("zh","🇨🇳 ZH")]):
            with _mc:
                if st.button(_lv, key=f"mob_lang_{_lk}", use_container_width=True,
                             type="primary" if st.session_state.lang == _lk else "secondary"):
                    st.session_state.lang = _lk
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button(_("logout"), key="mob_logout", use_container_width=True):
            _logout()

        st.stop()

# =====================================================================
# DESKTOP SIDEBAR
# =====================================================================
if not IS_MOBILE:
    with st.sidebar:
        _su = sqlite3.connect("users.db")
        _ud = _su.execute("SELECT logo_path, company_name FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
        _su.close()

        _sb_logo = ""
        _sb_text = _ud[1] if _ud and _ud[1] else "B2B Portal"
        if _ud and _ud[0]:
            _sb_logo = get_base64_image(_ud[0])
        if not _sb_logo:
            _sb_logo = get_system_logo()

        if _sb_logo and _sb_logo.startswith("data:image"):
            st.markdown(f"<div style='text-align:center;margin-bottom:12px;padding:8px 0;'><img src='{_sb_logo}' style='max-width:90%;max-height:52px;object-fit:contain;'></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center;margin-bottom:12px;padding:8px 0;font-weight:900;font-size:17px;color:#1e293b;'>{_sb_text}</div>", unsafe_allow_html=True)

        _sb_rc = {"admin": "#dc2626", "manufacturer": "#d97706"}.get(st.session_state.user_role, "#2563eb")
        _sb_ui = (st.session_state.user_email or "U")[0].upper()
        _sb_rt = _("role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer"))
        st.markdown(f"""
        <div style='background:#f8fafc;padding:12px;border-radius:14px;border:1px solid #e2e8f0;margin-bottom:18px;display:flex;align-items:center;gap:10px;'>
            <div style='background:{_sb_rc};color:white;border-radius:50%;min-width:38px;height:38px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:15px;flex-shrink:0;'>{_sb_ui}</div>
            <div style='overflow:hidden;flex:1;'>
                <div style='font-size:12px;font-weight:800;color:#0f172a;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;'>{st.session_state.user_email}</div>
                <div style='margin-top:3px;'><span style='background:{_sb_rc}22;color:{_sb_rc};padding:2px 8px;border-radius:6px;font-size:11px;font-weight:800;'>{_sb_rt}</span></div>
            </div>
        </div>""", unsafe_allow_html=True)

        _cur_idx = 0
        for _i, _lbl in enumerate(_all_menu):
            if st.session_state.active_tab in _lbl or _lbl in st.session_state.active_tab:
                _cur_idx = _i
                break

        def on_menu_change():
            st.session_state.active_tab = st.session_state.m_radio

        st.radio("MENÜ", _all_menu, index=_cur_idx, key="m_radio", on_change=on_menu_change, label_visibility="collapsed")

        st.markdown("<hr style='margin:14px 0;border:none;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

        _dc1, _dc2, _dc3 = st.columns(3)
        for _col, (_lk, _lv) in zip([_dc1, _dc2, _dc3], [("tr","🇹🇷 TR"),("en","🇬🇧 EN"),("zh","🇨🇳 ZH")]):
            with _col:
                if st.button(_lv, key=f"sb_lang_{_lk}", use_container_width=True,
                             type="primary" if st.session_state.lang == _lk else "secondary"):
                    st.session_state.lang = _lk
                    st.rerun()

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        if st.button(_("logout"), key="sb_logout", use_container_width=True):
            _logout()

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

elif _("m_backup") in act_tab:
    if _HAS_BACKUP:
        backup_management.show_backup_management()
    else:
        st.info("Yedekleme modülü yükleniyor...")

elif _("m_leads") in act_tab:
    st.markdown("## 📨 Teklif Talepleri")
    st.info("Teklif talepleri modülü yükleniyor...")

elif _("m_credit") in act_tab:
    if _HAS_CREDIT:
        credit_calculator.show_credit_calculator()
    else:
        st.markdown("## 💳 Kredi Hesaplama")
        st.info("Kredi hesaplama modülü yükleniyor...")

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
