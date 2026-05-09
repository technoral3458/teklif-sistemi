import streamlit as st
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice, orders_page, offer_management, profile_settings
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath

# --- SİSTEM AYARLARI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()
def generate_code(): return str(random.randint(100000, 999999))

# =====================================================================
# 🛠️ MERKEZİ VERİTABANI OTO-ONARIM (TÜM SÜTUNLAR EKSİKSİZ)
# =====================================================================
def repair_databases():
    # 1. USERS DB
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT, allowed_menus TEXT, allowed_categories TEXT)""")
    try: conn.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'dealer'")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN logo_path TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN website TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN address_full TEXT DEFAULT ''")
    except: pass
    
    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchone():
        conn.execute("INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type, allowed_menus) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici', 'm_dash,m_new,m_cust,m_past,m_order,m_prof,m_deal,m_model')", ("admin@ersanmakina.net", hash_password("20132017")))
    conn.commit(); conn.close()
    
    # 2. SALES DB
    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER, total_price REAL DEFAULT 0.0, conditions TEXT DEFAULT '', status TEXT DEFAULT 'Beklemede', user_id INTEGER DEFAULT 1, offer_date TEXT DEFAULT '', order_date TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS offer_items (id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT, user_id INTEGER DEFAULT 1, country TEXT DEFAULT '', city TEXT DEFAULT '', authorized_person TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', address TEXT DEFAULT '', address_full TEXT DEFAULT '', tax_office TEXT DEFAULT '', tax_id TEXT DEFAULT '')""")
    conn.commit(); conn.close()

    # 3. FACTORY DB (KRİTİK ONARIM: MODELLER VE OPSİYONLAR TABLOLARI EKSİKSİZ)
    conn = sqlite3.connect('factory_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)""")
    
    conn.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', category TEXT DEFAULT 'Diğer Makinalar')""")
    try: conn.execute("ALTER TABLE models ADD COLUMN name_zh TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN specs_zh TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN compatible_options TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN port_discount REAL DEFAULT 0.0")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN gallery_images TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE models ADD COLUMN gallery_videos TEXT DEFAULT ''")
    except: pass

    conn.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)""")
    try: conn.execute("ALTER TABLE options ADD COLUMN opt_name_zh TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN opt_desc TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN opt_desc_zh TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN allow_qty INTEGER DEFAULT 1")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN opt_suffix TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN opt_variant_image TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE options ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass

    conn.commit(); conn.close()

repair_databases()

# =====================================================================
# ÇOKLU DİL MOTORU VE YARDIMCILAR
# =====================================================================
if 'lang' not in st.session_state: st.session_state.lang = "tr"

DICTIONARY = {
    "tr": {"m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif", "m_cust": "👥 Müşteriler", "m_past": "📋 Geçmiş Teklifler", "m_order": "📦 Siparişler", "m_prof": "⚙️ Profil Ayarları", "m_deal": "🏢 Bayi Yönetimi", "m_model": "📦 Modelleri Yönet", "role_admin": "Yönetici", "role_dealer": "Bayi", "role_manuf": "Üretici"},
    "en": {"m_dash": "📊 Dashboard", "m_new": "📝 New Offer", "m_cust": "👥 Customers", "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_prof": "⚙️ Profile Settings", "m_deal": "🏢 Dealer Mgmt", "m_model": "📦 Manage Models", "role_admin": "Admin", "role_dealer": "Dealer", "role_manuf": "Producer"},
    "zh": {"m_dash": "📊 仪表板", "m_new": "📝 新报价", "m_cust": "👥 客户", "m_past": "📋 历史报价", "m_order": "📦 订单", "m_prof": "⚙️ 配置文件设置", "m_deal": "🏢 经销商管理", "m_model": "📦 管理型号", "role_admin": "管理员", "role_dealer": "经销商", "role_manuf": "制造商"}
}
def _(key): return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)

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

# =====================================================================
# GİRİŞ VE SİSTEM MANTIĞI
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
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, valid_user[0], ('admin' if valid_user[2] == 'admin' else ("manufacturer" if valid_user[1] == "Üretici" else "dealer")), valid_user[3], valid_user[4]

st.markdown("""<style>.stApp { background-color: #f8fafc; } .stTabs [data-baseweb="tab"] { font-weight: 600; color: #64748b; }</style>""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([8, 1, 1]); lang_opts = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}
    with c3:
        sel = st.selectbox("🌍", list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), label_visibility="collapsed")
        if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()

    st.write("") 
    st.write("")
    
    col_slider, col_form = st.columns([1.2, 1], gap="large")
    
    with col_slider:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        c_f = sqlite3.connect('factory_data.db')
        try: mods = c_f.execute("SELECT name, image_path FROM models").fetchall()
        except: mods = []
        c_f.close()
        
        s_h = ""
        if mods:
            for m in mods:
                img_b64 = get_base64_image(m[1]) if m[1] else ""
                if not img_b64: img_b64 = get_system_logo()
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
        st.markdown(f"<h2 style='text-align:center; color:#0f172a; margin-bottom:30px; font-weight:900;'>B2B Sipariş Portalı</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            t_login, t_reg = st.tabs(["🔑 Giriş", "📝 Kayıt"])
            
            with t_login:
                st.write("") 
                le = st.text_input("E-Posta", placeholder="ornek@firma.com").strip().lower()
                lp = st.text_input("Şifre", type="password")
                rem = st.checkbox("Beni Hatırla", value=True)
                if st.button("GİRİŞ YAP", type="primary", use_container_width=True):
                    conn = sqlite3.connect('users.db')
                    user = conn.execute("SELECT id, user_type, is_approved, role, allowed_menus FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchone()
                    if user:
                        if user[2] == 0: st.warning("Hesap onayı bekleniyor.")
                        else:
                            tok = str(uuid.uuid4())
                            conn.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0]))
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, user[0], ('admin' if user[3] == 'admin' else ("manufacturer" if user[1] == "Üretici" else "dealer")), le, user[4]
                            conn.commit(); conn.close(); st.rerun()
                    else: 
                        st.error("Hatalı e-posta veya şifre!")
                        conn.close()
                        
            with t_reg:
                st.write("")
                rt = st.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"])
                rc = st.text_input("Firma Tam Ünvanı *")
                rp = st.text_input("Telefon *")
                re = st.text_input("Kayıt E-Posta *").strip().lower()
                rpw = st.text_input("Şifre Belirleyin *", type="password")
                if st.button("Kayıt Ol", type="primary", use_container_width=True):
                    if all([rc, rp, re, rpw]):
                        c = sqlite3.connect('users.db')
                        if c.execute("SELECT id FROM users WHERE email=?", (re,)).fetchone(): st.error("Bu e-posta kullanımda!")
                        else:
                            c.execute("INSERT INTO users (email, password, company_name, phone, user_type, is_verified, is_approved, allowed_menus) VALUES (?,?,?,?,?,1,0,'m_dash,m_new,m_cust,m_past,m_order,m_prof')", (re, hash_password(rpw), rc, rp, rt))
                            c.commit(); st.success("Kayıt Başarılı! Yönetici onayından sonra giriş yapabilirsiniz.")
                        c.close()
                    else: st.warning("Lütfen yıldızlı alanları doldurun.")
    st.stop()

# =====================================================================
# ANA MENÜ VE SAYFA YÖNLENDİRMELERİ
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

    if st.session_state.user_role == "admin": 
        menu_items_labels = [_("m_dash"), _("m_new"), _("m_cust"), _("m_past"), _("m_order"), _("m_prof"), _("m_deal"), _("m_model")]
    else:
        allowed = st.session_state.allowed_menus.split(',') if st.session_state.allowed_menus else ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof"]
        v_keys = ["m_dash", "m_new", "m_cust", "m_past", "m_order", "m_prof", "m_deal", "m_model"]
        menu_items_labels = [_(k.strip()) for k in allowed if k.strip() in v_keys]

    if "active_tab" not in st.session_state: st.session_state.active_tab = menu_items_labels[0]
    
    current_idx = 0
    for idx, label in enumerate(menu_items_labels):
        if st.session_state.active_tab in label or label in st.session_state.active_tab:
            current_idx = idx; break

    st.radio("MENÜ", menu_items_labels, index=current_idx, key="m_radio", on_change=lambda: st.session_state.update(active_tab=st.session_state.m_radio), label_visibility="collapsed")
    
    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    lang_opts = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "zh": "🇨🇳 中文"}
    sel = st.selectbox("🌐", list(lang_opts.keys()), format_func=lambda x: lang_opts[x], index=list(lang_opts.keys()).index(st.session_state.lang), key="sb_lang")
    if sel != st.session_state.lang: st.session_state.lang = sel; st.rerun()
    if st.button("🚪 Çıkış", use_container_width=True):
        c = sqlite3.connect('users.db'); c.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,)); c.commit(); c.close(); st.query_params.clear(); st.session_state.clear(); st.rerun()

act_tab = st.session_state.active_tab

if _("m_cust") in act_tab: customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_new") in act_tab: offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_model") in act_tab: model_management.show_product_management()
elif _("m_deal") in act_tab: dealer_management.show_dealer_management()
elif _("m_past") in act_tab: offer_management.show_offer_management(st.session_state.user_id, st.session_state.user_role)
elif _("m_order") in act_tab: orders_page.show_orders(st.session_state.user_id, st.session_state.user_role == "admin")
elif _("m_prof") in act_tab: profile_settings.show_profile_settings(st.session_state.user_id)
elif _("m_dash") in act_tab:
    st.header(_("m_dash"))
    st.markdown("<p style='color:#64748b; margin-top:-10px; margin-bottom:20px;'>Sisteme hoş geldiniz.</p>", unsafe_allow_html=True)
    
    conn_s = sqlite3.connect('sales_data.db')
    if st.session_state.user_role == "admin": my_offers = conn_s.execute("SELECT status, total_price FROM offers").fetchall()
    else: my_offers = conn_s.execute("SELECT status, total_price FROM offers WHERE user_id=?", (st.session_state.user_id,)).fetchall()
    conn_s.close()
    
    tot_o = len(my_offers); tot_v = sum([x[1] for x in my_offers])
    ord_o = len([x for x in my_offers if x[0] in ['Onaylandı','Siparişe Çevir']]); ord_v = sum([x[1] for x in my_offers if x[0] in ['Onaylandı','Siparişe Çevir']])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div style='background:#fff; padding:20px; border-radius:12px; border:1px solid #f1f5f9; box-shadow:0 2px 4px rgba(0,0,0,0.02); text-align:center;'><div style='font-size:12px; font-weight:800; color:#64748b; margin-bottom:5px;'>TOPLAM TEKLİF</div><div style='font-size:26px; font-weight:900; color:#0f172a;'>{tot_o}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div style='background:#fff; padding:20px; border-radius:12px; border:1px solid #f1f5f9; box-shadow:0 2px 4px rgba(0,0,0,0.02); text-align:center;'><div style='font-size:12px; font-weight:800; color:#64748b; margin-bottom:5px;'>TOPLAM HACİM</div><div style='font-size:26px; font-weight:900; color:#3b82f6;'>{tot_v:,.0f} $</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div style='background:#fff; padding:20px; border-radius:12px; border:1px solid #f1f5f9; box-shadow:0 2px 4px rgba(0,0,0,0.02); text-align:center;'><div style='font-size:12px; font-weight:800; color:#64748b; margin-bottom:5px;'>SİPARİŞ (ONAYLANAN)</div><div style='font-size:26px; font-weight:900; color:#ea580c;'>{ord_o}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div style='background:#fff; padding:20px; border-radius:12px; border:1px solid #f1f5f9; box-shadow:0 2px 4px rgba(0,0,0,0.02); text-align:center;'><div style='font-size:12px; font-weight:800; color:#64748b; margin-bottom:5px;'>SİPARİŞ HACMİ</div><div style='font-size:26px; font-weight:900; color:#10b981;'>{ord_v:,.0f} $</div></div>", unsafe_allow_html=True)
