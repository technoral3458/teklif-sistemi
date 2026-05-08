import streamlit as st
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath

# --- SİSTEM AYARLARI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 🌍 ÇOKLU DİL MOTORU
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
        "role_manuf": "Üretici", "d_top_deal": "En Çok Teklif Veren Bayi", "d_last_deal": "Son İşlem Yapan Bayi",
        "d_top_country": "En Popüler Ülke", "d_top_city": "En Popüler Şehir", "d_tot_offer": "Toplam Teklifim", 
        "d_pend": "Bekleyen Teklifler", "d_appr": "Satışa Dönen (Sipariş)", "d_last_date": "Son İşlem Tarihi", 
        "d_title": "📊 Performans Özeti ve Vitrin", "d_showcase": "🌟 Makine Vitrini", "no_record": "Kayıt Yok", 
        "unknown": "Bilinmiyor", "none_yet": "Henüz Yok", "no_image": "Vitrin resmi bulunmuyor."
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
        "role_manuf": "Manufacturer", "d_top_deal": "Top Quoting Dealer", "d_last_deal": "Last Active Dealer",
        "d_top_country": "Top Country", "d_top_city": "Top City", "d_tot_offer": "My Total Offers", 
        "d_pend": "Pending Offers", "d_appr": "Converted to Order", "d_last_date": "Last Activity Date", 
        "d_title": "📊 Performance & Showcase", "d_showcase": "🌟 Machine Showcase", "no_record": "No Record", 
        "unknown": "Unknown", "none_yet": "None Yet", "no_image": "No showcase images found."
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
    msg.attach(MIMEText(f"Doğrulama Kodunuz: {code}", 'plain'))
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
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchone()
        conn.close()
        if res and res[0]:
            b64 = get_base64_image(res[0])
            if b64: return b64
    except: pass
    return ""

def repair_databases():
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT, allowed_menus TEXT, allowed_categories TEXT)""")
    u_cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "allowed_menus" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'")
    if "role" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'dealer'")
    if "allowed_categories" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
    
    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute("INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type, allowed_menus) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici', 'm_dash,m_new,m_cust,m_past,m_order,m_prof,m_deal,m_model')", ("admin@ersanmakina.net", hash_password("20132017")))
    conn.commit(); conn.close()
    
    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER, total_price REAL DEFAULT 0.0, conditions TEXT DEFAULT '', status TEXT DEFAULT 'Beklemede', user_id INTEGER DEFAULT 1, offer_date TEXT DEFAULT '', order_date TEXT DEFAULT '')""")
    s_cols = [c[1] for c in conn.execute("PRAGMA table_info(offers)").fetchall()]
    for col in ["user_id", "total_price", "conditions", "status", "offer_date", "order_date"]:
        if col not in s_cols:
            try:
                typ = "TEXT DEFAULT ''"
                if col == "total_price": typ = "REAL DEFAULT 0.0"
                elif col == "user_id": typ = "INTEGER DEFAULT 1"
                elif col == "status": typ = "TEXT DEFAULT 'Beklemede'"
                conn.execute(f"ALTER TABLE offers ADD COLUMN {col} {typ}")
            except: pass
            
    conn.execute("""CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT, user_id INTEGER DEFAULT 1, country TEXT DEFAULT '', city TEXT DEFAULT '', authorized_person TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', address TEXT DEFAULT '', address_full TEXT DEFAULT '')""")
    c_cols = [c[1] for c in conn.execute("PRAGMA table_info(customers)").fetchall()]
    for col in ["user_id", "country", "city", "authorized_person", "email", "phone", "address", "address_full", "tax_office", "tax_id"]:
        if col not in c_cols:
            try:
                typ = "INTEGER DEFAULT 1" if col == "user_id" else "TEXT DEFAULT ''"
                conn.execute(f"ALTER TABLE customers ADD COLUMN {col} {typ}")
            except: pass
    conn.commit(); conn.close()

    conn = sqlite3.connect('factory_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', port_discount REAL DEFAULT 0.0, compatible_options TEXT DEFAULT '', gallery_images TEXT DEFAULT '', category TEXT DEFAULT 'Diğer Makinalar', gallery_videos TEXT DEFAULT '', name_zh TEXT DEFAULT '', specs_zh TEXT DEFAULT '', user_id INTEGER DEFAULT 1)""")
    f_cols = [c[1] for c in conn.execute("PRAGMA table_info(models)").fetchall()]
    for col, col_type in [("user_id", "INTEGER DEFAULT 1"), ("name_zh", "TEXT DEFAULT ''"), ("specs_zh", "TEXT DEFAULT ''")]:
        if col not in f_cols:
            try: conn.execute(f"ALTER TABLE models ADD COLUMN {col} {col_type}")
            except: pass
    
    conn.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_desc TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0, allow_qty INTEGER DEFAULT 1, opt_name_zh TEXT DEFAULT '', opt_desc_zh TEXT DEFAULT '', user_id INTEGER DEFAULT 1)""")
    o_cols = [c[1] for c in conn.execute("PRAGMA table_info(options)").fetchall()]
    for col, col_type in [("user_id", "INTEGER DEFAULT 1"), ("opt_name_zh", "TEXT DEFAULT ''"), ("opt_desc_zh", "TEXT DEFAULT ''")]:
        if col not in o_cols:
            try: conn.execute(f"ALTER TABLE options ADD COLUMN {col} {col_type}")
            except: pass
    conn.commit(); conn.close()

repair_databases()

# =====================================================================
# OTURUM VE MODERN CSS
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email", "allowed_menus", "close_sidebar"]:
    if key not in st.session_state: st.session_state[key] = None
    
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
    .stApp { background-color: #f8fafc; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; border-radius: 6px; padding: 10px 20px !important; font-size: 14px !important; font-weight: 600; color: #64748b; border: 1px solid transparent; transition: all 0.2s ease; }
    .stTabs [data-baseweb="tab"]:hover { color: #0f172a; background-color: #f1f5f9; }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; border-color: #2563eb !important; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 12px 15px; border-radius: 8px; transition: all 0.2s; cursor: pointer; color: #475569; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background-color: #e2e8f0; color: #0f172a; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] { background-color: #2563eb !important; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3); }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p { color: white !important; font-weight: 700 !important; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 20px; font-weight: 900; color: #1e293b; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; margin-bottom:5px; display:block;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# ŞIK VE PROFESYONEL SAAS GİRİŞ EKRANI (BEMBEYAZ SLİDER ARKA PLANI)
# =====================================================================
if not st.session_state.logged_in:
    
    c1, c2, c3 = st.columns([8, 1, 1]); lang_opts = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}
    with c3:
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), key="main_lang_sel", label_visibility="collapsed")
        if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()

    st.write("") 
    st.write("")
    
    col_slider, col_form = st.columns([1.2, 1], gap="large")
    
    with col_slider:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        c_f = sqlite3.connect('factory_data.db')
        mods = c_f.execute("SELECT name, image_path FROM models").fetchall()
        c_f.close()
        
        s_h = ""
        if mods:
            for m in mods:
                img_b64 = get_base64_image(m[1]) if m[1] else ""
                if not img_b64:
                    img_b64 = get_system_logo()
                
                img_tag = f'<img src="{img_b64}">' if img_b64 else '<div style="font-size:80px; margin-top:100px;">⚙️</div>'
                s_h += f'<div class="mySlides fade">{img_tag}<div class="slide-text">{m[0]}</div></div>'

        if s_h:
            slider_html = f"""
            <html><head><style>
            body {{ margin:0; padding:0; background: transparent; overflow:hidden; font-family:sans-serif; }}
            .slideshow-container {{ position:relative; width:100%; height:450px; border-radius:20px; display:flex; align-items:center; justify-content:center; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
            .mySlides {{ display:none; text-align:center; width:100%; height:100%; position:relative; }}
            img {{ max-height:380px; max-width:85%; object-fit:contain; position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); filter: drop-shadow(0 15px 20px rgba(0,0,0,0.1)); }}
            .slide-text {{ color:#0f172a; font-size:16px; font-weight:900; position:absolute; bottom:20px; left:50%; transform:translateX(-50%); background:rgba(255,255,255,0.85); padding:10px 25px; border-radius:30px; backdrop-filter:blur(8px); border:1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 6px rgba(0,0,0,0.05); white-space:nowrap; }}
            .fade {{ animation-name:fade; animation-duration:1.5s; }}
            @keyframes fade {{ from {{opacity:0.3; transform: scale(0.95);}} to {{opacity:1; transform: scale(1);}} }}
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
            </script>
            </body></html>
            """
            import streamlit.components.v1 as components
            components.html(slider_html, height=480)
        else:
            st.info("Sistemde henüz kayıtlı makine bulunmuyor.")

    with col_form:
        st.markdown(f"<h2 style='text-align:center; color:#0f172a; margin-bottom:30px; font-weight:900;'>Erşan Makina Sanayi</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            t_login, t_reg, t_forg = st.tabs([_("login_tab"), _("reg_tab"), _("forg_tab")])
            
            # --- GİRİŞ (DİREKT) ---
            with t_login:
                st.write("") 
                le = st.text_input(_("email"), key="l_e", placeholder="ornek@firma.com").strip().lower()
                lp = st.text_input(_("pass"), type="password", key="l_p", placeholder="••••••••")
                rem = st.checkbox(_("rem"), value=True, key="l_r")
                
                st.write("")
                if st.button(_("login_btn"), type="primary", use_container_width=True):
                    conn = sqlite3.connect('users.db')
                    user = conn.execute("SELECT id, user_type, is_approved, is_verified, role, allowed_menus FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchone()
                    
                    if user:
                        if user[2] == 0: 
                            st.warning(_("sys_wait"))
                        else:
                            tok = str(uuid.uuid4())
                            conn.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0]))
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, user[0], ('admin' if user[4] == 'admin' else ("manufacturer" if user[1] == "Üretici" else "dealer")), le, user[5]
                            conn.commit(); conn.close()
                            st.rerun()
                    else: 
                        st.error(_("sys_err"))
                        conn.close()

            # --- KAYIT (DİREKT) ---
            with t_reg:
                st.write("")
                rt = st.selectbox(_("reg_type"), [_("dealer"), _("manuf")], key="r_t")
                rc = st.text_input(_("comp_name"), key="r_c")
                rp = st.text_input(_("phone"), key="r_ph", placeholder="+90 5XX...")
                re = st.text_input(_("email"), key="r_e", placeholder="ornek@firma.com").strip().lower()
                rpw = st.text_input(_("pass"), type="password", key="r_p")
                
                st.write("")
                if st.button(_("reg_btn"), type="primary", use_container_width=True):
                    if all([rc, rp, re, rpw]):
                        c = sqlite3.connect('users.db')
                        if c.execute("SELECT id FROM users WHERE email=?", (re,)).fetchone(): 
                            st.error(_("email_in_use"))
                        else:
                            c.execute("INSERT INTO users (email, password, company_name, phone, user_type, is_verified, is_approved, allowed_menus) VALUES (?,?,?,?,?,1,0,'m_dash,m_new,m_cust,m_past,m_order,m_prof')", (re, hash_password(rpw), rc, rp, rt))
                            c.commit()
                            st.success("Kayıt Başarılı! Sistem yöneticisi onayladıktan sonra giriş yapabilirsiniz.")
                        c.close()
                    else: 
                        st.warning(_("req_fields"))
                        
            # --- ŞİFRE UNUTTUM ---
            with t_forg:
                st.write("")
                if st.session_state.forgot_step == 1:
                    fe = st.text_input(_("f_email"), key="f_e", placeholder="Kayıtlı e-postanız...").strip().lower()
                    st.write("")
                    if st.button(_("send_reset"), type="primary", use_container_width=True):
                        c = sqlite3.connect('users.db'); user = c.execute("SELECT id FROM users WHERE email=?", (fe,)).fetchone()
                        if user:
                            vc = generate_code(); c.execute("UPDATE users SET auth_code=? WHERE email=?", (vc, fe)); c.commit()
                            if send_email(fe, vc, "Sifre Sifirlama / Password Reset"): st.session_state.temp_f_email, st.session_state.forgot_step = 2; st.rerun()
                        else: st.error(_("no_email"))
                        c.close()
                elif st.session_state.forgot_step == 2:
                    fc = st.text_input(_("enter_code"), max_chars=6, key="f_c"); np = st.text_input(_("new_pass"), type="password", key="f_np")
                    st.write("")
                    if st.button(_("change_pass"), type="primary", use_container_width=True):
                        c = sqlite3.connect('users.db'); user = c.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_f_email,)).fetchone()
                        if user and user[0] == fc: c.execute("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(np), st.session_state.temp_f_email)); c.commit(); st.session_state.forgot_step = 1; st.success(_("pass_changed"))
                        else: st.error(_("wrong_code"))
                        c.close()
    st.stop()

# =====================================================================
# ANA MENÜ VE SAYFA YÖNETİMİ (ONAY RAKAMI EKLENDİ)
# =====================================================================
with st.sidebar:
    c_user = sqlite3.connect('users.db')
    user_data = c_user.execute("SELECT logo_path, company_name FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    c_user.close()
    
    sidebar_logo = ""
    sidebar_text = user_data[1] if user_data and user_data[1] else "B2B Portal"
    if user_data and user_data[0]: sidebar_logo = get_base64_image(user_data[0])
    if not sidebar_logo: sidebar_logo = get_system_logo() 
        
    if sidebar_logo and sidebar_logo.startswith("data:image"):
        st.markdown(f"<div style='text-align: center; margin-bottom: 15px; padding: 10px 0;'><img src='{sidebar_logo}' style='max-width: 90%; max-height: 55px; object-fit: contain;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align: center; margin-bottom: 15px; padding: 10px 0; font-weight:900; font-size:18px; color:#1e293b;'>{sidebar_text}</div>", unsafe_allow_html=True)

    r_text = _("role_admin" if st.session_state.user_role == "admin" else ("role_manuf" if st.session_state.user_role == "manufacturer" else "role_dealer"))
    st.markdown(f"<div style='background-color:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px; display:flex; align-items:center; gap:10px; overflow-wrap: anywhere;'><div style='background:#2563eb; color:white; border-radius:50%; min-width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:bold;'>{st.session_state.user_email[0].upper()}</div><div style='overflow:hidden; width:100%;'><div style='font-size:12px; font-weight:700; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;'>{st.session_state.user_email}</div><div style='font-size:11px; color:#64748b; font-weight:600;'>{r_text}</div></div></div>", unsafe_allow_html=True)
    
    # 🚀 ONAY BEKLEYEN RAKAMI HESAPLAMA MOTORU 🚀
    pending_count_txt = ""
    if st.session_state.user_role == "admin":
        try:
            conn_p = sqlite3.connect('sales_data.db')
            p_count = conn_p.execute("SELECT COUNT(*) FROM offers WHERE status='Onay Bekliyor'").fetchone()[0]
            conn_p.close()
            if p_count > 0:
                pending_count_txt = f" ({p_count})"
        except: pass

    # Menü Öğelerini Tanımla
    if st.session_state.user_role == "admin": 
        # Admin için rakamlı menü
        menu_items_labels = [
            _("m_dash"), _("m_new"), _("m_cust"), 
            _("m_past") + pending_count_txt, # 👈 Rakam buraya eklendi
            _("m_order"), _("m_prof"), _("m_deal"), _("m_model")
        ]
    else:
        allowed = st.session_state.allowed_menus.split(',') if st.session_state.allowed_menus else ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof"]
        v_keys = ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof", "m_deal", "m_model"]
        menu_items_labels = [_(k.strip()) for k in allowed if k.strip() in v_keys]

    if "active_tab" not in st.session_state: st.session_state.active_tab = menu_items_labels[0]
    
    # Rakam değişse bile seçili sayfayı bulmak için akıllı eşleştirme
    current_idx = 0
    for idx, label in enumerate(menu_items_labels):
        if st.session_state.active_tab in label or label in st.session_state.active_tab:
            current_idx = idx
            break

    def on_menu_change():
        st.session_state.active_tab = st.session_state.m_radio
        st.session_state.close_sidebar = True
        
    st.radio("MENÜ", menu_items_labels, index=current_idx, key="m_radio", on_change=on_menu_change, label_visibility="collapsed")
    
    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    lang_opts = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "zh": "🇨🇳 中文"}
    sel = st.selectbox("🌐 " + _("lang_sel"), list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), key="sb_lang")
    if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()
    if st.button(_("logout"), use_container_width=True):
        c = sqlite3.connect('users.db'); c.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,)); c.commit(); c.close(); st.query_params.clear(); st.session_state.clear(); st.rerun()

# --- SAYFA YÖNLENDİRMELERİ ---
act_tab = st.session_state.active_tab
if _("m_cust") in act_tab: customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_new") in act_tab: offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_model") in act_tab: model_management.show_product_management()
elif _("m_deal") in act_tab: dealer_management.show_dealer_management()
elif _("m_past") in act_tab: offer_management.show_offer_management(st.session_state.user_id, st.session_state.user_role)
elif _("m_order") in act_tab: orders_page.show_orders(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_prof") in act_tab: # Profil sayfası içeriği... (Dosyadaki mevcut kod devamı)
    st.header(_("m_prof"))
    # ... profil kodu ...
elif _("m_dash") in act_tab:
    st.header(_("d_title"))
    # ... dashboard kodu ...
