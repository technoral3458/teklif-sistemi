import streamlit as st
import streamlit.components.v1 as components
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management, profile_settings
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath


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

st.markdown("""
<style>
.stApp { background:#f8fafc; }
.block-container { padding-top:1.5rem; }

[data-testid="stSidebar"] {
    background:#ffffff;
    border-right:1px solid #e2e8f0;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
    display:none !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] {
    gap:7px !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label {
    padding:13px 15px;
    border-radius:12px;
    transition:all .2s ease;
    cursor:pointer;
    color:#475569;
    background:#f8fafc;
    border:1px solid #eef2f7;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background-color:#e2e8f0;
    color:#0f172a;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
    background-color:#2563eb !important;
    box-shadow:0 6px 14px rgba(37,99,235,.25);
    border-color:#2563eb !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p {
    color:white !important;
    font-weight:800 !important;
}

.stTabs [data-baseweb="tab-list"] {
    justify-content:center;
    gap:8px;
    margin-bottom:20px;
}

.stTabs [data-baseweb="tab"] {
    background-color:transparent;
    border-radius:10px;
    padding:10px 20px !important;
    font-size:14px !important;
    font-weight:700;
    color:#64748b;
    border:1px solid transparent;
    transition:all .2s ease;
}

.stTabs [aria-selected="true"] {
    background-color:#2563eb !important;
    color:white !important;
    border-color:#2563eb !important;
}

.mobile-topbar {
    display:none;
}

.dash-hero {
    background:linear-gradient(135deg,#0f172a,#2563eb);
    padding:30px;
    border-radius:24px;
    color:white;
    margin-bottom:24px;
    box-shadow:0 14px 32px rgba(15,23,42,.18);
}

.dash-hero h1 {
    margin:0;
    font-size:34px;
    font-weight:900;
}

.dash-hero p {
    margin:8px 0 0 0;
    color:#dbeafe;
    font-size:15px;
}

.dash-card {
    background:#ffffff;
    border:1px solid #e2e8f0;
    border-radius:22px;
    padding:24px;
    box-shadow:0 10px 24px rgba(15,23,42,.06);
    text-align:left;
    min-height:130px;
}

.dash-label {
    color:#64748b;
    font-size:12px;
    font-weight:900;
    letter-spacing:.5px;
    text-transform:uppercase;
}

.dash-value {
    color:#0f172a;
    font-size:36px;
    font-weight:900;
    margin-top:10px;
    line-height:1;
}

.dash-blue { color:#2563eb; }
.dash-orange { color:#ea580c; }
.dash-green { color:#10b981; }

@media (max-width:768px) {
    .block-container {
        padding-left:14px !important;
        padding-right:14px !important;
        padding-top:70px !important;
    }

    h1 { font-size:28px !important; line-height:1.2 !important; }
    h2, h3 { font-size:22px !important; line-height:1.25 !important; }

    .mobile-topbar {
        display:flex;
        align-items:center;
        justify-content:space-between;
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:18px;
        padding:12px 14px;
        margin-bottom:16px;
        box-shadow:0 8px 22px rgba(15,23,42,.06);
    }

    .mobile-topbar-title {
        font-size:16px;
        font-weight:900;
        color:#0f172a;
        line-height:1.2;
    }

    .mobile-topbar-sub {
        font-size:11px;
        color:#64748b;
        font-weight:700;
    }

    .mobile-menu-note {
        background:#eff6ff;
        color:#1e40af;
        border:1px solid #bfdbfe;
        border-radius:14px;
        padding:10px 12px;
        font-size:12px;
        font-weight:700;
        margin-bottom:12px;
    }

    section[data-testid="stSidebar"] {
        width:86vw !important;
        min-width:86vw !important;
        max-width:86vw !important;
        box-shadow:0 0 45px rgba(15,23,42,.28);
    }

    .stTabs [data-baseweb="tab-list"] {
        overflow-x:auto !important;
        white-space:nowrap !important;
        justify-content:flex-start !important;
        gap:6px !important;
        padding-bottom:8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        min-width:max-content !important;
        padding:10px 14px !important;
        font-size:14px !important;
        border-radius:12px !important;
    }

    div[data-testid="column"] {
        width:100% !important;
        flex:1 1 100% !important;
        min-width:100% !important;
    }

    button {
        min-height:46px !important;
        border-radius:13px !important;
        font-weight:800 !important;
    }

    input, textarea { font-size:16px !important; }

    .dash-hero {
        padding:22px;
        border-radius:22px;
        margin-bottom:18px;
    }

    .dash-hero h1 { font-size:28px !important; }
    .dash-hero p { font-size:14px !important; line-height:1.5 !important; }

    .dash-card {
        padding:24px;
        border-radius:20px;
        text-align:center;
        min-height:125px;
        margin-bottom:10px;
    }

    .dash-value { font-size:38px; }
}
</style>
""", unsafe_allow_html=True)


if 'lang' not in st.session_state:
    try:
        accept_lang = st.context.headers.get("Accept-Language", "")
        if accept_lang:
            primary_lang = accept_lang.split(',')[0][:2].lower()
            st.session_state.lang = primary_lang if primary_lang in ["tr", "en", "zh"] else "tr"
        else:
            st.session_state.lang = "tr"
    except Exception:
        st.session_state.lang = "tr"


DICTIONARY = {
    "tr": {
        "login_tab": "🔑 Giriş", "reg_tab": "📝 Kayıt", "forg_tab": "❓ Şifremi Unuttum",
        "email": "E-Posta Adresi", "pass": "Şifre", "rem": "Beni Hatırla", "login_btn": "GİRİŞ YAP",
        "sys_err": "Hatalı e-posta veya şifre!", "sys_unver": "Hesabınız henüz doğrulanmamış!", "sys_wait": "Hesap onayı bekleniyor.",
        "reg_type": "Faaliyet Türü", "dealer": "Satıcı (Bayi)", "manuf": "Üretici",
        "comp_name": "Firma Tam Ünvanı *", "phone": "Telefon * (05XX...)", "reg_btn": "Kayıt Ol",
        "req_fields": "(*) alanlar zorunludur.", "email_in_use": "Bu e-posta zaten kullanımda!",
        "enter_code": "Mailinize Gelen Kodu Girin", "verify_btn": "Doğrula ve Şifreyi Sıfırla",
        "ver_success": "Doğrulandı! Yönetici onayı sonrası giriş yapabilirsiniz.", "wrong_code": "Hatalı kod girdiniz!",
        "f_email": "Kayıtlı E-Posta Adresiniz", "send_reset": "Sıfırlama Kodu Gönder",
        "no_email": "Sistemde böyle bir e-posta bulunamadı.", "new_pass": "Yeni Şifre Belirleyin",
        "change_pass": "Şifremi Değiştir", "pass_changed": "Şifreniz değiştirildi! Giriş sekmesinden giriş yapabilirsiniz.",
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif Hazırla", "m_cust": "👥 Müşterilerim",
        "m_past": "📋 Geçmiş Tekliflerim", "m_order": "📦 Siparişler", "m_prof": "⚙️ Profil Ayarlarım",
        "m_deal": "🏢 Bayi Yönetimi", "m_model": "📦 Tüm Modelleri Yönet", "logout": "🚪 Sistemi Kapat",
        "lang_sel": "Sistem Dili / Language", "role_admin": "Sistem Yöneticisi", "role_dealer": "Satıcı Bayi",
        "role_manuf": "Üretici"
    },
    "en": {
        "login_tab": "🔑 Login", "reg_tab": "📝 Register", "forg_tab": "❓ Forgot Password",
        "email": "Email Address", "pass": "Password", "rem": "Remember Me", "login_btn": "LOGIN",
        "sys_err": "Incorrect email or password!", "sys_unver": "Account not verified!", "sys_wait": "Pending admin approval.",
        "reg_type": "Business Type", "dealer": "Dealer", "manuf": "Manufacturer",
        "comp_name": "Full Company Name *", "phone": "Phone *", "reg_btn": "Register",
        "req_fields": "(*) fields are required.", "email_in_use": "Email is already in use!",
        "enter_code": "Enter Code from Email", "verify_btn": "Verify & Reset",
        "ver_success": "Verified! Wait for admin approval.", "wrong_code": "Incorrect code!",
        "f_email": "Registered Email Address", "send_reset": "Send Reset Code",
        "no_email": "No such email found in the system.", "new_pass": "Set New Password",
        "change_pass": "Change Password", "pass_changed": "Password changed! You can now log in.",
        "m_dash": "📊 Dashboard", "m_new": "📝 Create New Offer", "m_cust": "👥 My Customers",
        "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_prof": "⚙️ Profile Settings",
        "m_deal": "🏢 Dealer Management", "m_model": "📦 Manage Models", "logout": "🚪 Logout",
        "lang_sel": "System Language", "role_admin": "System Admin", "role_dealer": "Dealer",
        "role_manuf": "Manufacturer"
    },
    "zh": {
        "login_tab": "🔑 登录", "reg_tab": "📝 注册", "forg_tab": "❓ 忘记密码",
        "email": "电子邮件地址", "pass": "密码", "rem": "记住我", "login_btn": "登录",
        "sys_err": "电子邮件或密码错误！", "sys_unver": "帐户未验证！", "sys_wait": "等待管理员批准。",
        "reg_type": "业务类型", "dealer": "经销商", "manuf": "制造商",
        "comp_name": "公司全称 *", "phone": "电话 *", "reg_btn": "注册",
        "req_fields": "(*) 必填字段。", "email_in_use": "电子邮件已被使用！",
        "enter_code": "输入电子邮件验证码", "verify_btn": "验证并重置",
        "ver_success": "已验证！等待管理员批准。", "wrong_code": "验证码错误！",
        "f_email": "注册的电子邮件地址", "send_reset": "发送重置验证码",
        "no_email": "系统中未找到此电子邮件。", "new_pass": "设置新密码",
        "change_pass": "更改密码", "pass_changed": "密码已更改！您现在可以登录。",
        "m_dash": "📊 仪表板", "m_new": "📝 创建新报价", "m_cust": "👥 我的客户",
        "m_past": "📋 历史报价", "m_order": "📦 订单", "m_prof": "⚙️ 个人资料设置",
        "m_deal": "🏢 经销商管理", "m_model": "📦 管理所有型号", "logout": "🚪 退出系统",
        "lang_sel": "系统语言 (Language)", "role_admin": "系统管理员", "role_dealer": "经销商",
        "role_manuf": "制造商"
    }
}


def _(key):
    return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)


def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def generate_code():
    return str(random.randint(100000, 999999))


def send_email(to_email, code, subject="Ersan Makine B2B"):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.ersanmakina.net")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "sefa@ersanmakina.net")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

    if not SENDER_PASSWORD:
        st.error("SMTP şifresi tanımlı değil. Sunucuya SENDER_PASSWORD ortam değişkeni eklenmeli.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Ersan Makine B2B <{SENDER_EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(f"Doğrulama Kodunuz: {code}", 'plain'))

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
            except Exception:
                pass

    return ""


def get_system_logo():
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchone()
        conn.close()

        if res and res[0]:
            b64 = get_base64_image(res[0])
            if b64:
                return b64
    except Exception:
        pass

    return ""


def repair_databases():
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT, allowed_menus TEXT, allowed_categories TEXT)""")
    u_cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]

    if "allowed_menus" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'")
    if "role" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'dealer'")
    if "allowed_categories" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
    if "logo_path" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN logo_path TEXT DEFAULT ''")
    if "website" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN website TEXT DEFAULT ''")
    if "address_full" not in u_cols:
        conn.execute("ALTER TABLE users ADD COLUMN address_full TEXT DEFAULT ''")

    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute(
            "INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type, allowed_menus) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici', 'm_dash,m_new,m_cust,m_past,m_order,m_prof,m_deal,m_model')",
            ("admin@ersanmakina.net", hash_password("20132017"))
        )

    conn.commit()
    conn.close()

    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER, total_price REAL DEFAULT 0.0, conditions TEXT DEFAULT '', status TEXT DEFAULT 'Bekle