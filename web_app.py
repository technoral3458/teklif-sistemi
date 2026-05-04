import streamlit as st
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath
from streamlit_javascript import st_javascript

# --- SİSTEM AYARLARI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 🌍 OTOMATİK CİHAZ/TARAYICI DİLİ ALGILAMA & ÇOKLU DİL MOTORU
# =====================================================================
if 'lang' not in st.session_state:
    # 1. Aşama: Tarayıcıdan gizlice cihaz dilini soruyoruz (Örn: 'tr-TR', 'zh-CN')
    browser_lang = st_javascript("window.navigator.userLanguage || window.navigator.language;")
    
    # st_javascript ilk salisede 0 döner, cevap gelince string(metin) olur.
    # Eğer JS'den cevap gelmişse, onu alıp kilitliyoruz.
    if browser_lang and isinstance(browser_lang, str):
        lang_code = browser_lang.lower()
        if "zh" in lang_code:
            st.session_state.lang = "zh"
        elif "tr" in lang_code:
            st.session_state.lang = "tr"
        else:
            st.session_state.lang = "en"
        st.rerun() # Dili sabitlemek için sayfayı 1 kez hissettirmeden yeniler.
        
    # 2. Aşama: Eğer JS çalışmazsa (bazı eski telefonlarda), yedek olarak HTTP Header kontrolü yap
    else:
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
        "lang_sel": "Sistem Dili / Language", "role_admin": "Sistem Yöneticisi", "role_dealer": "Satıcı Bayi", 
        "role_manuf": "Üretici", "d_top_deal": "En Çok Teklif Veren Bayi", "d_last_deal": "Son İşlem Yapan Bayi",
        "d_top_country": "En Popüler Ülke", "d_top_city": "En Popüler Şehir", "d_tot_offer": "Toplam Teklifim", 
        "d_pend": "Bekleyen Teklifler", "d_appr": "Satışa Dönen (Sipariş)", "d_last_date": "Son İşlem Tarihi", 
        "d_title": "📊 Performans Özeti ve Vitrin", "d_showcase": "🌟 Makine Vitrini", "no_record": "Kayıt Yok", 
        "unknown": "Bilinmiyor", "none_yet": "Henüz Yok", "no_image": "Vitrin resmi bulunmuyor."
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
        "lang_sel": "System Language", "role_admin": "System Admin", "role_dealer": "Dealer", 
        "role_manuf": "Manufacturer", "d_top_deal": "Top Quoting Dealer", "d_last_deal": "Last Active Dealer",
        "d_top_country": "Top Country", "d_top_city": "Top City", "d_tot_offer": "My Total Offers", 
        "d_pend": "Pending Offers", "d_appr": "Converted to Order", "d_last_date": "Last Activity Date", 
        "d_title": "📊 Performance & Showcase", "d_showcase": "🌟 Machine Showcase", "no_record": "No Record", 
        "unknown": "Unknown", "none_yet": "None Yet", "no_image": "No showcase images found."
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
        "lang_sel": "系统语言 (Language)", "role_admin": "系统管理员", "role_dealer": "经销商", 
        "role_manuf": "制造商", "d_top_deal": "报价最多的经销商", "d_last_deal": "最近活跃的经销商",
        "d_top_country": "热门国家", "d_top_city": "热门城市", "d_tot_offer": "我的总报价", 
        "d_pend": "待处理报价", "d_appr": "转换为订单", "d_last_date": "最后活动日期", 
        "d_title": "📊 绩效与展示", "d_showcase": "🌟 机器展示", "no_record": "无记录", 
        "unknown": "未知", "none_yet": "暂无", "no_image": "未找到展示图片。"
    }
}

def _(key): return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)

# =====================================================================
# YARDIMCI FONKSİYONLAR VE VERİTABANI
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

def repair_databases():
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT, allowed_menus TEXT)""")
    u_cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "allowed_menus" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'")
    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute("INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type, allowed_menus) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici', 'm_dash,m_new,m_cust,m_past,m_order,m_prof,m_deal,m_model')", ("admin@ersanmakina.net", hash_password("20132017")))
    conn.commit(); conn.close()
    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER, total_price REAL DEFAULT 0.0, conditions TEXT DEFAULT '', status TEXT DEFAULT 'Beklemede', user_id INTEGER DEFAULT 1, offer_date TEXT DEFAULT '', order_date TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT, user_id INTEGER DEFAULT 1, country TEXT DEFAULT '', city TEXT DEFAULT '', authorized_person TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', address TEXT DEFAULT '')""")
    conn.commit(); conn.close()

repair_databases()

# =====================================================================
# OTURUM VE MODERN CSS
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email", "allowed_menus", "close_sidebar"]:
    if key not in st.session_state: st.session_state[key] = None
if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        valid_user = conn.execute("SELECT id, user_type, role, email, allowed_menus FROM users WHERE session_token=?", (current_token,)).fetchone()
        conn.close()
        if valid_user:
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, valid_user[0], (valid_user[2] if valid_user[2] == 'admin' else ("manufacturer" if valid_user[1] == "Üretici" else "dealer")), valid_user[3], valid_user[4]

st.markdown("""
    <style>
    /* MOBİL SEKMELER (TABS) DÜZENLEMESİ - TAŞMAYI ÖNLER */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 5px; margin-bottom: 20px; flex-wrap: wrap !important; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f5f9; border-radius: 8px; padding: 10px 15px !important; font-size: 14px !important;
        font-weight: 600; color: #475569; border: 1px solid #e2e8f0; white-space: normal !important; text-align: center; flex: 1 1 auto;
    }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; }
    
    /* SIDEBAR MODERNİZASYONU */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 12px 15px; border-radius: 8px; transition: all 0.2s; cursor: pointer; color: #475569; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background-color: #e2e8f0; color: #0f172a; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] { background-color: #2563eb !important; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3); }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p { color: white !important; font-weight: 700 !important; }
    
    /* STAT KARTLARI */
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 20px; font-weight: 900; color: #1e293b; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; margin-bottom:5px; display:block;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# GİRİŞ / KAYIT EKRANLARI
# =====================================================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([7, 2, 1.5]); lang_opts = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}
    with c3:
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), key="main_lang_sel", label_visibility="collapsed")
        if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()
    
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown(f"<div style='text-align:center; padding:10px 0 20px 0;'><img src='{get_system_logo()}' style='max-width:100%; max-height:80px; object-fit:contain;'></div>", unsafe_allow_html=True)
        t_login, t_reg, t_forg = st.tabs([_("login_tab"), _("reg_tab"), _("forg_tab")])
        with t_login:
            with st.container(border=True):
                le = st.text_input(_("email"), key="l_e").strip().lower(); lp = st.text_input(_("pass"), type="password", key="l_p"); rem = st.checkbox(_("rem"), value=True, key="l_r")
                if st.button(_("login_btn"), type="primary", use_container_width=True):
                    conn = sqlite3.connect('users.db'); user = conn.execute("SELECT id, user_type, is_approved, is_verified, role, allowed_menus FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchone(); conn.close()
                    if user:
                        if user[3] == 0: st.warning(_("sys_unver"))
                        elif user[2] == 0: st.warning(_("sys_wait"))
                        else:
                            tok = str(uuid.uuid4()); c = sqlite3.connect('users.db'); c.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0])); c.commit(); c.close()
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, user[0], (user[4] if user[4]=='admin' else ("manufacturer" if user[1]=="Üretici" else "dealer")), le, user[5]
                            st.rerun()
                    else: st.error(_("sys_err"))
        with t_reg:
            with st.container(border=True):
                if st.session_state.reg_step == 1:
                    rt = st.selectbox(_("reg_type"), [_("dealer"), _("manuf")], key="r_t"); rc = st.text_input(_("comp_name"), key="r_c"); rp = st.text_input(_("phone"), key="r_ph"); re = st.text_input(_("email"), key="r_e").strip().lower(); rpw = st.text_input(_("pass"), type="password", key="r_p")
                    if st.button(_("reg_btn"), use_container_width=True):
                        if all([rc, rp, re, rpw]):
                            c = sqlite3.connect('users.db')
                            if c.execute("SELECT id FROM users WHERE email=?", (re,)).fetchone(): st.error(_("email_in_use"))
                            else:
                                vc = generate_code(); c.execute("INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved, allowed_menus) VALUES (?,?,?,?,?,?,0,0,'m_dash,m_new,m_cust,m_past,m_order,m_prof')", (re, hash_password(rpw), rc, rp, rt, vc)); c.commit()
                                if send_email(re, vc, "Code / 验证"): st.session_state.temp_email, st.session_state.reg_step = re, 2; st.rerun()
                            c.close()
                        else: st.warning(_("req_fields"))
                elif st.session_state.reg_step == 2:
                    ec = st.text_input(_("enter_code"), max_chars=6, key="r_code")
                    if st.button(_("verify_btn"), type="primary", use_container_width=True):
                        c = sqlite3.connect('users.db'); db_c = c.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,)).fetchone()
                        if db_c and db_c[0] == ec: c.execute("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,)); c.commit(); st.session_state.reg_step = 1; st.success(_("ver_success"))
                        else: st.error(_("wrong_code"))
                        c.close()
    st.stop()

# =====================================================================
# GÜVENLİ VE GARANTİLİ OTOMATİK KAPANAN YAN MENÜ
# =====================================================================
with st.sidebar:
    st.markdown(f"<div style='text-align: center; margin-bottom: 15px; padding: 10px 0;'><img src='{get_system_logo()}' style='max-width: 90%; max-height: 55px; object-fit: contain;'></div>", unsafe_allow_html=True)
    r_text = _("role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer"))
    st.markdown(f"<div style='background-color:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px; display:flex; align-items:center; gap:10px; overflow-wrap: anywhere;'><div style='background:#2563eb; color:white; border-radius:50%; min-width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:bold;'>{st.session_state.user_email[0].upper()}</div><div style='overflow:hidden; width:100%;'><div style='font-size:12px; font-weight:700; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;'>{st.session_state.user_email}</div><div style='font-size:11px; color:#64748b; font-weight:600;'>{r_text}</div></div></div>", unsafe_allow_html=True)
    
    if st.session_state.user_role == "admin": menu_items = [_("m_dash"), _("m_new"), _("m_cust"), _("m_past"), _("m_order"), _("m_prof"), _("m_deal"), _("m_model")]
    else:
        allowed = st.session_state.allowed_menus.split(',') if st.session_state.allowed_menus else ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof"]
        v_keys = ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof", "m_deal", "m_model"]
        menu_items = [_(k.strip()) for k in allowed if k.strip() in v_keys]
    
    if "active_tab" not in st.session_state or st.session_state.active_tab not in menu_items: st.session_state.active_tab = menu_items[0]
    
    def on_menu_change():
        st.session_state.active_tab = st.session_state.m_radio
        st.session_state.close_sidebar = True # Kapatma sinyalini etkinleştir
        
    st.radio("MENÜ", menu_items, index=menu_items.index(st.session_state.active_tab), key="m_radio", on_change=on_menu_change, label_visibility="collapsed")
    
    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    lang_opts = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "zh": "🇨🇳 中文"}
    sel = st.selectbox("🌐 " + _("lang_sel"), list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), key="sb_lang")
    if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()
    if st.button(_("logout"), use_container_width=True):
        c = sqlite3.connect('users.db'); c.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,)); c.commit(); c.close(); st.query_params.clear(); st.session_state.clear(); st.rerun()

# =====================================================================
# GARANTİLİ MOBİL MENÜ KAPATICI (DYNAMIC ID İLE)
# =====================================================================
if st.session_state.get("close_sidebar", False):
    st.session_state.close_sidebar = False
    import streamlit.components.v1 as components
    
    components.html(f"""
        <script id="trigger-{uuid.uuid4().hex}">
        setTimeout(function() {{
            var isMobile = window.parent.innerWidth <= 768;
            if (isMobile) {{
                // Escape tuşu yolla
                window.parent.document.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Escape', 'bubbles': true }}));
                // Çarpı butonuna tıkla
                var closeBtn = window.parent.document.querySelector('button[kind="headerNoPadding"]');
                if (closeBtn) {{ closeBtn.click(); }}
                // Karanlık arkaplana tıkla
                var backdrop = window.parent.document.querySelector('[data-testid="stSidebar"] + div');
                if (backdrop) {{ backdrop.click(); }}
            }}
        }}, 100);
        </script>
    """, height=0, width=0)

# =====================================================================
# SAYFA YÖNLENDİRİCİSİ
# =====================================================================
if st.session_state.active_tab == "PROFORMA": proforma_invoice.show_proforma(st.session_state.proforma_id, st.session_state.user_id)
elif st.session_state.active_tab == _("m_cust"): customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == _("m_new"): offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == _("m_model"): model_management.show_product_management()
elif st.session_state.active_tab == _("m_deal"): dealer_management.show_dealer_management()
elif st.session_state.active_tab == _("m_past"): offer_management.show_offer_management(st.session_state.user_id, st.session_state.user_role)
elif st.session_state.active_tab == _("m_order"): orders_page.show_orders(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == _("m_dash"):
    st.header(_("d_title"))
    if st.session_state.user_role == "admin":
        c_u = sqlite3.connect('users.db'); u_raw = c_u.execute("SELECT id, company_name FROM users").fetchall(); u_dict = {u[0]: u[1] for u in u_raw}; c_u.close()
        c_s = sqlite3.connect('sales_data.db'); t_d_r = c_s.execute("SELECT user_id, COUNT(*) as cnt FROM offers GROUP BY user_id ORDER BY cnt DESC LIMIT 1").fetchone(); t_d = u_dict.get(t_d_r[0], _("no_record")) if t_d_r else _("no_record")
        l_d_r = c_s.execute("SELECT user_id FROM offers ORDER BY id DESC LIMIT 1").fetchone(); l_d = u_dict.get(l_d_r[0], _("no_record")) if l_d_r else _("no_record")
        tc = c_s.execute("SELECT country FROM customers WHERE country!='' GROUP BY country ORDER BY COUNT(id) DESC LIMIT 1").fetchone(); t_country = tc[0] if tc else _("unknown")
        tci = c_s.execute("SELECT city FROM customers WHERE city!='' GROUP BY city ORDER BY COUNT(id) DESC LIMIT 1").fetchone(); t_city = tci[0] if tci else _("unknown"); c_s.close()
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="stat-card"><span class="stat-title">{_("d_top_deal")}</span><span class="stat-val">{t_d}</span></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">{_("d_last_deal")}</span><span class="stat-val">{l_d}</span></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">{_("d_top_country")}</span><span class="stat-val">{t_country}</span></div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="stat-card" style="border-left-color:#8b5cf6;"><span class="stat-title">{_("d_top_city")}</span><span class="stat-val">{t_city}</span></div>', unsafe_allow_html=True)
    else:
        c = sqlite3.connect('sales_data.db'); d_s = c.execute("SELECT status FROM offers WHERE user_id=?", (st.session_state.user_id,)).fetchall(); l_o = c.execute("SELECT offer_date FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (st.session_state.user_id,)).fetchone(); c.close()
        df_s = pd.DataFrame(d_s, columns=["D"]); t_c = len(df_s); p_c = len(df_s[df_s["D"]=="Beklemede"]); a_c = len(df_s[df_s["D"].isin(["Onaylandı","Siparişe Çevir"])]); ld = l_o[0] if l_o else _("none_yet")
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="stat-card"><span class="stat-title">{_("d_tot_offer")}</span><span class="stat-val">{t_c}</span></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">{_("d_pend")}</span><span class="stat-val">{p_c}</span></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">{_("d_appr")}</span><span class="stat-val">{a_c}</span></div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="stat-card" style="border-left-color:#6366f1;"><span class="stat-title">{_("d_last_date")}</span><span class="stat-val" style="font-size:15px;">{ld}</span></div>', unsafe_allow_html=True)
    st.markdown("---"); st.subheader(_("d_showcase"))
    c_f = sqlite3.connect('factory_data.db'); mods = c_f.execute("SELECT name, image_path FROM models WHERE image_path!=''").fetchall(); c_f.close()
    s_h = "".join([f'<div class="mySlides fade"><div class="text">{m[0]}</div><img src="{get_base64_image(m[1])}"></div>' for m in mods if get_base64_image(m[1])])
    if s_h:
        import streamlit.components.v1 as components
        components.html(f'<html><head><style>body{{margin:0;}} .slideshow-container{{width:100%; max-width:900px; position:relative; margin:auto; border-radius:12px; border:1px solid #e2e8f0; background:#fff; height:450px; display:flex; align-items:center; justify-content:center;}} .mySlides{{display:none; text-align:center; width:100%; height:100%; position:relative;}} img{{max-height:400px; max-width:90%; object-fit:contain; position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);}} .text{{color:#0f172a; font-size:18px; font-weight:800; padding:10px 20px; position:absolute; bottom:20px; left:50%; transform:translateX(-50%); background:rgba(255,255,255,0.9); border-radius:20px; border:1px solid #cbd5e1;}} .fade{{animation-name:fade; animation-duration:2s;}} @keyframes fade{{from{{opacity:.2}} to{{opacity:1}}}}</style></head><body><div class="slideshow-container">{s_h}</div><script>let sI=0; show(); function show(){{let i; let s=document.getElementsByClassName("mySlides"); if(s.length===0)return; for(i=0;i<s.length;i++)s[i].style.display="none"; sI++; if(sI>s.length)sI=1; s[sI-1].style.display="block"; setTimeout(show,3500);}}</script></body></html>', height=480)
    else: st.info(_("no_image"))
elif st.session_state.active_tab == _("m_prof"):
    st.header(_("m_prof")); c = sqlite3.connect('users.db'); u = c.execute("SELECT company_name, email, phone, website, address_full, logo_path FROM users WHERE id=?", (st.session_state.user_id,)).fetchone(); c.close()
    with st.expander("👤", expanded=True):
        with st.form("p_f"):
            cc1, cc2 = st.columns(2); pn = cc1.text_input("Company", value=u[0] if u else ""); pw = cc2.text_input("Web", value=u[3] if u and u[3] else ""); pp = cc1.text_input("Phone", value=u[2] if u and u[2] else ""); pa = st.text_area("Address", value=u[4] if u and u[4] else ""); ul = st.file_uploader("Logo", type=['png','jpg','jpeg'])
            if st.form_submit_button("💾 UPDATE"):
                fl = u[5] if u else ""
                if ul:
                    if not os.path.exists("images"): os.makedirs("images")
                    fl = f"images/logo_user_{st.session_state.user_id}.png"
                    with open(fl, "wb") as f: f.write(ul.getbuffer())
                c = sqlite3.connect('users.db'); c.execute("UPDATE users SET company_name=?, website=?, phone=?, address_full=?, logo_path=? WHERE id=?", (pn, pw, pp, pa, fl, st.session_state.user_id)); c.commit(); c.close(); st.success("Updated!"); st.rerun()
