import streamlit as st
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath

# --- SİSTEM AYARLARI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 🌍 ÇOKLU DİL MOTORU VE OTOMATİK DİL ALGILAYICI (TR - EN - ZH)
# =====================================================================
if 'lang' not in st.session_state:
    try:
        accept_lang = st.context.headers.get("Accept-Language", "")
        if accept_lang:
            primary_lang = accept_lang.split(',')[0][:2].lower()
            st.session_state.lang = primary_lang if primary_lang in ["tr", "en", "zh"] else "en"
        else:
            st.session_state.lang = "tr"
    except:
        st.session_state.lang = "tr"

DICTIONARY = {
    "tr": {
        "login_tab": "🔑 Giriş", "reg_tab": "📝 Kayıt", "forg_tab": "❓ Şifremi Unuttum",
        "email": "E-Posta Adresi", "pass": "Şifre", "rem": "Beni Hatırla", "login_btn": "SİSTEME GİRİŞ YAP",
        "sys_err": "Hatalı e-posta veya şifre!", "sys_unver": "E-posta doğrulanmamış!", "sys_wait": "Hesap onayı bekleniyor.",
        "reg_type": "Faaliyet Türü", "dealer": "Satıcı (Bayi)", "manuf": "Üretici",
        "comp_name": "Firma Tam Ünvanı *", "phone": "Telefon *", "reg_btn": "Kayıt Ol",
        "req_fields": "(*) alanlar zorunludur.", "email_in_use": "E-posta kullanımda!",
        "code_sent": "Doğrulama Kodu Gönderildi", "mail_err": "E-posta gönderilemedi.",
        "enter_code": "Mailinize Gelen Kodu Girin", "verify_btn": "Onayla",
        "ver_success": "Doğrulandı! Yönetici onayı sonrası giriş yapabilirsiniz.", "wrong_code": "Hatalı kod!",
        "f_email": "Kayıtlı E-Posta Adresiniz", "send_reset": "Sıfırlama Kodu Gönder",
        "no_email": "Sistemde böyle bir e-posta bulunamadı.", "new_pass": "Yeni Şifre Belirleyin",
        "change_pass": "Şifremi Değiştir", "pass_changed": "Şifreniz değiştirildi! Giriş sekmesinden giriş yapabilirsiniz.",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif Hazırla", "m_cust": "👥 Müşterilerim", 
        "m_past": "📋 Geçmiş Tekliflerim", "m_order": "📦 Siparişler", "m_prof": "⚙️ Profil Ayarlarım",
        "m_deal": "🏢 Bayi Yönetimi", "m_model": "📦 Tüm Modelleri Yönet", "logout": "🚪 Sistemi Kapat",
        
        "role_admin": "Sistem Yöneticisi", "role_dealer": "Satıcı Bayi", "role_manuf": "Üretici",
        
        "d_top_deal": "En Çok Teklif Veren Bayi", "d_last_deal": "Son İşlem Yapan Bayi",
        "d_top_country": "En Popüler Ülke", "d_top_city": "En Popüler Şehir",
        "d_tot_offer": "Toplam Teklifim", "d_pend": "Bekleyen Teklifler", "d_appr": "Satışa Dönen (Sipariş)",
        "d_last_date": "Son İşlem Tarihi", "d_title": "📊 Performans Özeti ve Vitrin", "d_showcase": "🌟 Makine Vitrini",
        "no_record": "Kayıt Yok", "unknown": "Bilinmiyor", "none_yet": "Henüz Yok", "no_image": "Vitrin resmi bulunmuyor."
    },
    "en": {
        "login_tab": "🔑 Login", "reg_tab": "📝 Register", "forg_tab": "❓ Forgot Password",
        "email": "Email Address", "pass": "Password", "rem": "Remember Me", "login_btn": "LOGIN TO SYSTEM",
        "sys_err": "Incorrect email or password!", "sys_unver": "Email not verified!", "sys_wait": "Pending account approval.",
        "reg_type": "Business Type", "dealer": "Dealer", "manuf": "Manufacturer",
        "comp_name": "Full Company Name *", "phone": "Phone *", "reg_btn": "Register",
        "req_fields": "(*) fields are required.", "email_in_use": "Email is already in use!",
        "code_sent": "Verification Code Sent", "mail_err": "Could not send email.",
        "enter_code": "Enter the Code from your Email", "verify_btn": "Verify",
        "ver_success": "Verified! You can log in after admin approval.", "wrong_code": "Incorrect code!",
        "f_email": "Registered Email Address", "send_reset": "Send Reset Code",
        "no_email": "No such email found in the system.", "new_pass": "Set New Password",
        "change_pass": "Change Password", "pass_changed": "Password changed! You can now log in.",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Create New Offer", "m_cust": "👥 My Customers", 
        "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_prof": "⚙️ Profile Settings",
        "m_deal": "🏢 Dealer Management", "m_model": "📦 Manage Models", "logout": "🚪 Logout",
        
        "role_admin": "System Admin", "role_dealer": "Dealer", "role_manuf": "Manufacturer",
        
        "d_top_deal": "Top Quoting Dealer", "d_last_deal": "Last Active Dealer",
        "d_top_country": "Top Country", "d_top_city": "Top City",
        "d_tot_offer": "My Total Offers", "d_pend": "Pending Offers", "d_appr": "Converted to Order",
        "d_last_date": "Last Activity Date", "d_title": "📊 Performance & Showcase", "d_showcase": "🌟 Machine Showcase",
        "no_record": "No Record", "unknown": "Unknown", "none_yet": "None Yet", "no_image": "No showcase images found."
    },
    "zh": {
        "login_tab": "🔑 登录", "reg_tab": "📝 注册", "forg_tab": "❓ 忘记密码",
        "email": "电子邮件地址", "pass": "密码", "rem": "记住我", "login_btn": "登录系统",
        "sys_err": "电子邮件或密码错误！", "sys_unver": "电子邮件未验证！", "sys_wait": "等待帐户批准。",
        "reg_type": "业务类型", "dealer": "经销商", "manuf": "制造商",
        "comp_name": "公司全称 *", "phone": "电话 *", "reg_btn": "注册",
        "req_fields": "(*) 必填字段。", "email_in_use": "电子邮件已被使用！",
        "code_sent": "验证码已发送", "mail_err": "无法发送电子邮件。",
        "enter_code": "输入您电子邮件中的验证码", "verify_btn": "验证",
        "ver_success": "已验证！管理员批准后即可登录。", "wrong_code": "验证码错误！",
        "f_email": "注册的电子邮件地址", "send_reset": "发送重置验证码",
        "no_email": "系统中未找到此电子邮件。", "new_pass": "设置新密码",
        "change_pass": "更改密码", "pass_changed": "密码已更改！您现在可以登录。",
        
        "m_dash": "📊 仪表板", "m_new": "📝 创建新报价", "m_cust": "👥 我的客户", 
        "m_past": "📋 历史报价", "m_order": "📦 订单", "m_prof": "⚙️ 个人资料设置",
        "m_deal": "🏢 经销商管理", "m_model": "📦 管理所有型号", "logout": "🚪 退出系统",
        
        "role_admin": "系统管理员", "role_dealer": "经销商", "role_manuf": "制造商",
        
        "d_top_deal": "报价最多的经销商", "d_last_deal": "最近活跃的经销商",
        "d_top_country": "热门国家", "d_top_city": "热门城市",
        "d_tot_offer": "我的总报价", "d_pend": "待处理报价", "d_appr": "转换为订单",
        "d_last_date": "最后活动日期", "d_title": "📊 绩效与展示", "d_showcase": "🌟 机器展示",
        "no_record": "无记录", "unknown": "未知", "none_yet": "暂无", "no_image": "未找到展示图片。"
    }
}

def _(key): return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)

# Çakışmayı önlemek için key_suffix eklendi
def lang_selector(key_suffix):
    c1, c2 = st.columns([8.5, 1.5])
    with c2:
        lang_opts = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}
        current_idx = list(lang_opts.keys()).index(st.session_state.lang) if st.session_state.lang in lang_opts else 0
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=current_idx, key=f"lang_sel_{key_suffix}", label_visibility="collapsed")
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()

# =====================================================================
# GÜVENLİK VE MAİL FONKSİYONLARI
# =====================================================================
def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()
def generate_code(): return str(random.randint(100000, 999999))

def send_email(to_email, code, subject="Ersan Makine"):
    SMTP_SERVER = "mail.ersanmakina.net"; SMTP_PORT = 587
    SENDER_EMAIL = "sefa@ersanmakina.net"; SENDER_PASSWORD = "Sev32881-"
    msg = MIMEMultipart(); msg['From'] = f"Ersan Makine B2B <{SENDER_EMAIL}>"; msg['To'] = to_email; msg['Subject'] = subject
    msg.attach(MIMEText(f"Kod / Code / 代码: {code}", 'plain'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT); server.starttls(); server.login(SENDER_EMAIL, SENDER_PASSWORD); server.send_message(msg); server.quit()
        return True
    except: return False

def get_base64_image(path):
    if not path: return ""
    if str(path).startswith("http"): return path
    base_name = posixpath.basename(ntpath.basename(path))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
            except: pass
    return ""

def get_system_logo():
    fallback_url = "https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png"
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchone()
        conn.close()
        if res and res[0]:
            b64 = get_base64_image(res[0])
            if b64: return b64
    except: pass
    return fallback_url

# =====================================================================
# VERİTABANI TAMİRCİSİ
# =====================================================================
def repair_databases():
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT)""")
    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute("INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')", ("admin@ersanmakina.net", hash_password("20132017")))
    conn.commit(); conn.close()

    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER, total_price REAL DEFAULT 0.0, conditions TEXT DEFAULT '', status TEXT DEFAULT 'Beklemede', user_id INTEGER DEFAULT 1, offer_date TEXT DEFAULT '', order_date TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT, user_id INTEGER, country TEXT DEFAULT '', city TEXT DEFAULT '')""")
    
    o_cols = [c[1] for c in conn.execute("PRAGMA table_info(offers)").fetchall()]
    if "order_date" not in o_cols: conn.execute("ALTER TABLE offers ADD COLUMN order_date TEXT DEFAULT ''")
    
    c_cols = [c[1] for c in conn.execute("PRAGMA table_info(customers)").fetchall()]
    if "country" not in c_cols: conn.execute("ALTER TABLE customers ADD COLUMN country TEXT DEFAULT ''")
    if "city" not in c_cols: conn.execute("ALTER TABLE customers ADD COLUMN city TEXT DEFAULT ''")
    conn.commit(); conn.close()

repair_databases()

# =====================================================================
# OTURUM YÖNETİMİ
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email"]:
    if key not in st.session_state: st.session_state[key] = None
if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1

if "active_tab" not in st.session_state: 
    st.session_state.active_tab = _("m_dash")

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        valid_user = conn.execute("SELECT id, user_type, role, email FROM users WHERE session_token=?", (current_token,)).fetchone()
        conn.close()
        if valid_user:
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, valid_user[0], valid_user[3]
            st.session_state.user_role = valid_user[2] if valid_user[2] == 'admin' else ("manufacturer" if valid_user[1] == "Üretici" else "dealer")

# --- MODERN ARAYÜZ CSS ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 10px 20px; font-weight: 600; color: #475569; border: 1px solid #e2e8f0; white-space: nowrap;}
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; border: 1px solid #2563eb; }
    
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 20px; font-weight: 900; color: #1e293b; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; margin-bottom:5px; display:block;}
    
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 12px 15px; border-radius: 8px; transition: all 0.2s; cursor: pointer; color: #475569; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background-color: #e2e8f0; color: #0f172a; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] { background-color: #2563eb !important; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3); }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p { color: white !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size: 15px !important; font-weight: 600; margin: 0;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# GİRİŞ, KAYIT VE ŞİFRE EKRANLARI (Hata Çözümlü)
# =====================================================================
if not st.session_state.logged_in:
    lang_selector("login_screen") # Key eklendi
    
    col_left, col_main, col_right = st.columns([1, 1.2, 1])
    with col_main:
        st.markdown(f"""<div style='text-align: center; padding: 20px 0 10px 0;'><img src="{get_system_logo()}" style="max-height: 80px; margin-bottom: 15px; object-fit: contain;"></div>""", unsafe_allow_html=True)
        
        t_login, t_reg, t_forg = st.tabs([_("login_tab"), _("reg_tab"), _("forg_tab")])
        
        with t_login:
            with st.container(border=True):
                # KEY EKLENDİ
                le = st.text_input(_("email"), key="login_email_inp").strip().lower()
                lp = st.text_input(_("pass"), type="password", key="login_pass_inp")
                rem = st.checkbox(_("rem"), value=True, key="login_rem_chk")
                if st.button(_("login_btn"), type="primary", use_container_width=True, key="login_submit"):
                    conn = sqlite3.connect('users.db')
                    user = conn.execute("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchone()
                    if user:
                        if user[3] == 0: st.warning(_("sys_unver"))
                        elif user[2] == 0: st.warning(_("sys_wait"))
                        else:
                            tok = str(uuid.uuid4())
                            conn.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0]))
                            conn.commit()
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, user[0], le
                            st.session_state.user_role = user[4] if user[4] == 'admin' else ("manufacturer" if user[1] == "Üretici" else "dealer")
                            st.rerun()
                    else: st.error(_("sys_err"))
                    conn.close()

        with t_reg:
            with st.container(border=True):
                if st.session_state.reg_step == 1:
                    # KEY EKLENDİ
                    reg_type = st.selectbox(_("reg_type"), [_("dealer"), _("manuf")], key="reg_type_sel")
                    reg_comp = st.text_input(_("comp_name"), key="reg_comp_inp")
                    reg_phone = st.text_input(_("phone"), key="reg_phone_inp")
                    reg_email = st.text_input(_("email"), key="reg_email_inp").strip().lower()
                    reg_pwd = st.text_input(_("pass"), type="password", key="reg_pass_inp")
                    if st.button(_("reg_btn"), use_container_width=True, key="reg_submit"):
                        if all([reg_comp, reg_phone, reg_email, reg_pwd]):
                            conn = sqlite3.connect('users.db')
                            if conn.execute("SELECT id FROM users WHERE email=?", (reg_email,)).fetchone(): st.error(_("email_in_use"))
                            else:
                                ver_code = generate_code()
                                conn.execute("INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)", (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code))
                                conn.commit()
                                if send_email(reg_email, ver_code, "Doğrulama / Verification / 验证"):
                                    st.session_state.temp_email, st.session_state.reg_step = reg_email, 2; st.rerun()
                                else: st.error(_("mail_err"))
                            conn.close()
                        else: st.warning(_("req_fields"))
                elif st.session_state.reg_step == 2:
                    # KEY EKLENDİ
                    entered_code = st.text_input(_("enter_code"), max_chars=6, key="reg_code_inp")
                    if st.button(_("verify_btn"), type="primary", use_container_width=True, key="verify_submit"):
                        conn = sqlite3.connect('users.db')
                        db_code = conn.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,)).fetchone()
                        if db_code and db_code[0] == entered_code:
                            conn.execute("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                            conn.commit()
                            st.session_state.reg_step = 1; st.success(_("ver_success"))
                        else: st.error(_("wrong_code"))
                        conn.close()

        with t_forg:
            with st.container(border=True):
                if st.session_state.forgot_step == 1:
                    # KEY EKLENDİ
                    f_email = st.text_input(_("f_email"), key="forg_email_inp").strip().lower()
                    if st.button(_("send_reset"), use_container_width=True, key="forg_send_btn"):
                        conn = sqlite3.connect('users.db')
                        if conn.execute("SELECT id FROM users WHERE email=?", (f_email,)).fetchone():
                            reset_code = generate_code()
                            conn.execute("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            conn.commit()
                            if send_email(f_email, reset_code, "Sıfırlama / Reset / 重置"):
                                st.session_state.temp_email = f_email; st.session_state.forgot_step = 2; st.rerun()
                            else: st.error(_("mail_err"))
                        else: st.error(_("no_email"))
                        conn.close()
                elif st.session_state.forgot_step == 2:
                    # KEY EKLENDİ
                    f_code = st.text_input(_("enter_code"), max_chars=6, key="forg_code_inp")
                    new_pwd = st.text_input(_("new_pass"), type="password", key="forg_pass_inp")
                    if st.button(_("change_pass"), type="primary", use_container_width=True, key="forg_submit_btn"):
                        conn = sqlite3.connect('users.db')
                        valid_code = conn.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,)).fetchone()
                        if valid_code and valid_code[0] == f_code and len(new_pwd) > 3:
                            conn.execute("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(new_pwd), st.session_state.temp_email))
                            conn.commit()
                            st.session_state.forgot_step = 1
                            st.success(_("pass_changed"))
                        else: st.error(_("wrong_code"))
                        conn.close()
    st.stop()

# =====================================================================
# GÜVENLİ YAN MENÜ
# =====================================================================
with st.sidebar:
    lang_selector("sidebar_menu") # Key eklendi
    st.markdown(f"<div style='text-align: center; margin-bottom: 25px; margin-top: 10px;'><img src='{get_system_logo()}' style='max-height: 65px; object-fit: contain;'></div>", unsafe_allow_html=True)
    
    r_text_key = "role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer")
    r_text = _(r_text_key)
    
    st.markdown(f"""
        <div style='background-color:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:25px; display:flex; align-items:center; gap:10px;'>
            <div style='background:#2563eb; color:white; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:16px;'>{st.session_state.user_email[0].upper()}</div>
            <div style='overflow:hidden;'>
                <div style='font-size:13px; font-weight:700; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;'>{st.session_state.user_email}</div>
                <div style='font-size:11px; color:#64748b; font-weight:600;'>{r_text}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    menu_items = [
        _("m_dash"), _("m_new"), _("m_cust"), _("m_past"), _("m_order"), _("m_prof")
    ]
    if st.session_state.user_role == "admin": 
        menu_items.extend([_("m_deal"), _("m_model")])
    
    if st.session_state.active_tab not in menu_items:
        st.session_state.active_tab = menu_items[0]
        
    idx = menu_items.index(st.session_state.active_tab)
    def sync_menu(): st.session_state.active_tab = st.session_state.m_radio
    st.radio("MENÜ", menu_items, index=idx, key="m_radio", on_change=sync_menu, label_visibility="collapsed")

    st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    if st.button(_("logout"), use_container_width=True):
        conn = sqlite3.connect('users.db')
        conn.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
        conn.commit(); conn.close()
        st.query_params.clear(); st.session_state.clear(); st.rerun()

# =====================================================================
# SAYFA YÖNLENDİRİCİ MOTORU
# =====================================================================
if st.session_state.active_tab == "PROFORMA":
    proforma_invoice.show_proforma(st.session_state.proforma_id, st.session_state.user_id)
elif st.session_state.active_tab == _("m_cust"):
    customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == _("m_new"):
    offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == _("m_model"):
    model_management.show_product_management()
elif st.session_state.active_tab == _("m_deal"):
    dealer_management.show_dealer_management()
elif st.session_state.active_tab == _("m_past"):
    offer_management.show_offer_management(st.session_state.user_id, st.session_state.user_role)
elif st.session_state.active_tab == _("m_order"):
    orders_page.show_orders(st.session_state.user_id, st.session_state.user_role == "admin")

# =====================================================================
# DASHBOARD (ANA SAYFA)
# =====================================================================
elif st.session_state.active_tab == _("m_dash"):
    st.header(_("d_title"))
    
    if st.session_state.user_role == "admin":
        conn_u = sqlite3.connect('users.db')
        users_raw = conn_u.execute("SELECT id, company_name FROM users").fetchall()
        user_dict = {u[0]: u[1] for u in users_raw}
        conn_u.close()

        conn_s = sqlite3.connect('sales_data.db')
        
        top_dealer_row = conn_s.execute("SELECT user_id, COUNT(*) as cnt FROM offers GROUP BY user_id ORDER BY cnt DESC LIMIT 1").fetchone()
        top_dealer = user_dict.get(top_dealer_row[0], _("no_record")) if top_dealer_row else _("no_record")
        
        last_dealer_row = conn_s.execute("SELECT user_id FROM offers ORDER BY id DESC LIMIT 1").fetchone()
        last_dealer = user_dict.get(last_dealer_row[0], _("no_record")) if last_dealer_row else _("no_record")
        
        top_country = _("unknown")
        tc = conn_s.execute("SELECT country, COUNT(id) as cnt FROM customers WHERE country IS NOT NULL AND country != '' GROUP BY country ORDER BY cnt DESC LIMIT 1").fetchone()
        if tc and tc[0]: top_country = tc[0]
            
        top_city = _("unknown")
        tci = conn_s.execute("SELECT city, COUNT(id) as cnt FROM customers WHERE city IS NOT NULL AND city != '' GROUP BY city ORDER BY cnt DESC LIMIT 1").fetchone()
        if tci and tci[0]: top_city = tci[0]
            
        conn_s.close()

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card" style="border-left-color:#3b82f6;"><span class="stat-title">{_("d_top_deal")}</span><span class="stat-val" title="{top_dealer}">{top_dealer}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">{_("d_last_deal")}</span><span class="stat-val" title="{last_dealer}">{last_dealer}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">{_("d_top_country")}</span><span class="stat-val" title="{top_country}">{top_country}</span></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color:#8b5cf6;"><span class="stat-title">{_("d_top_city")}</span><span class="stat-val" title="{top_city}">{top_city}</span></div>', unsafe_allow_html=True)

    else:
        conn = sqlite3.connect('sales_data.db')
        dealer_stats = conn.execute("SELECT status FROM offers WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        last_offer = conn.execute("SELECT offer_date FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (st.session_state.user_id,)).fetchone()
        conn.close()
        
        df_stats = pd.DataFrame(dealer_stats, columns=["Durum"])
        total_count = len(df_stats)
        pending_count = len(df_stats[df_stats["Durum"] == "Beklemede"])
        approved_count = len(df_stats[df_stats["Durum"].isin(["Onaylandı", "Siparişe Çevir"])])
        l_date = last_offer[0] if last_offer else _("none_yet")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><span class="stat-title">{_("d_tot_offer")}</span><span class="stat-val">{total_count}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">{_("d_pend")}</span><span class="stat-val">{pending_count}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">{_("d_appr")}</span><span class="stat-val">{approved_count}</span></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color:#6366f1;"><span class="stat-title">{_("d_last_date")}</span><span class="stat-val" style="font-size:16px; line-height:35px;">{l_date}</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(_("d_showcase"))
    
    conn_f = sqlite3.connect('factory_data.db')
    models_for_slider = conn_f.execute("SELECT name, image_path FROM models WHERE image_path IS NOT NULL AND image_path != ''").fetchall()
    conn_f.close()

    slides_html = ""
    for m_name, m_img in models_for_slider:
        b64 = get_base64_image(m_img)
        if b64:
            slides_html += f"""
            <div class="mySlides fade">
                <div class="text">{m_name}</div>
                <img src="{b64}">
            </div>
            """
            
    if slides_html:
        carousel_code = f"""
        <html>
        <head>
        <style>
          body {{ margin: 0; font-family: sans-serif; background: transparent; display:flex; justify-content:center; align-items:center; height: 100vh; overflow:hidden;}}
          .slideshow-container {{ width: 100%; max-width: 900px; position: relative; margin: auto; border-radius: 12px; border: 1px solid #e2e8f0; background: #fff; height: 450px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05);}}
          .mySlides {{ display: none; text-align: center; width: 100%; height: 100%; position: relative; }}
          img {{ max-height: 400px; max-width: 90%; object-fit: contain; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);}}
          .text {{ color: #0f172a; font-size: 18px; font-weight: 800; padding: 10px 20px; position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(255,255,255,0.9); border-radius: 20px; border: 1px solid #cbd5e1; box-shadow: 0 2px 5px rgba(0,0,0,0.1); z-index: 10; white-space:nowrap;}}
          .fade {{ animation-name: fade; animation-duration: 2s; }}
          @keyframes fade {{ from {{opacity: .2}} to {{opacity: 1}} }}
        </style>
        </head>
        <body>
        <div class="slideshow-container">
          {slides_html}
        </div>
        <script>
        let slideIndex = 0;
        showSlides();
        function showSlides() {{
          let i;
          let slides = document.getElementsByClassName("mySlides");
          if(slides.length === 0) return;
          for (i = 0; i < slides.length; i++) {{ slides[i].style.display = "none"; }}
          slideIndex++;
          if (slideIndex > slides.length) {{slideIndex = 1}}
          slides[slideIndex-1].style.display = "block";
          setTimeout(showSlides, 3500); 
        }}
        </script>
        </body>
        </html>
        """
        import streamlit.components.v1 as components
        components.html(carousel_code, height=480)
    else:
        st.info(_("no_image"))

# =====================================================================
# PROFİL AYARLARI
# =====================================================================
elif st.session_state.active_tab == _("m_prof"):
    st.header(_("m_prof"))
    conn = sqlite3.connect('users.db')
    u_data = conn.execute("SELECT company_name, email, phone, website, address_full, logo_path FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    conn.close()
    with st.expander("👤", expanded=True):
        with st.form("p_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Firma Adı / Company Name / 公司名称", value=u_data[0] if u_data else "")
            p_web = c2.text_input("Web Sitesi / Website / 网站", value=u_data[3] if u_data and u_data[3] else "")
            p_phone = c1.text_input("Telefon / Phone / 电话", value=u_data[2] if u_data and u_data[2] else "")
            p_adr = st.text_area("Açık Adres / Full Address / 详细地址", value=u_data[4] if u_data and u_data[4] else "")
            up_logo = st.file_uploader("Logonuz / Your Logo / 您的标志", type=['png','jpg','jpeg'])
            if st.form_submit_button("💾 GÜNCELLE / UPDATE / 更新", type="primary"):
                f_logo = u_data[5] if u_data else ""
                if up_logo:
                    if not os.path.exists("images"): os.makedirs("images")
                    f_logo = f"images/logo_user_{st.session_state.user_id}.png"
                    with open(f_logo, "wb") as f: f.write(up_logo.getbuffer())
                conn = sqlite3.connect('users.db')
                conn.execute("UPDATE users SET company_name=?, website=?, phone=?, address_full=?, logo_path=? WHERE id=?", (p_name, p_web, p_phone, p_adr, f_logo, st.session_state.user_id))
                conn.commit(); conn.close()
                st.success("Güncellendi / Updated / 已更新！"); st.rerun()
                
    if st.session_state.user_role == 'admin':
        with st.expander("🚀 SİSTEM GENEL AYARLARI / SYSTEM SETTINGS / 系统设置", expanded=True):
            with st.form("sys_form"):
                new_sys_logo = st.file_uploader("Sistem Logosu Seç / Select System Logo / 选择系统标志", type=['png','jpg','jpeg'])
                if st.form_submit_button("SİSTEM LOGOSUNU DEĞİŞTİR / CHANGE LOGO / 更改系统标志"):
                    if new_sys_logo:
                        if not os.path.exists("images"): os.makedirs("images")
                        sys_path = f"images/system_logo_main.png"
                        with open(sys_path, "wb") as f: f.write(new_sys_logo.getbuffer())
                        conn = sqlite3.connect('factory_data.db')
                        conn.execute("UPDATE company_profile SET logo_path=? WHERE id=1", (sys_path,))
                        conn.commit(); conn.close()
                        st.success("Sistem logosu güncellendi / System logo updated / 系统标志已更新！"); st.rerun()
