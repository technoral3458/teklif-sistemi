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
# 🛠️ MERKEZİ VERİTABANI ONARIMI (TÜM SÜTUNLAR EKSİKSİZ EKLENDİ)
# =====================================================================
def repair_databases():
    # 1. USERS DB
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT, allowed_menus TEXT, allowed_categories TEXT)""")
    u_cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "allowed_menus" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'm_dash,m_new,m_cust,m_past,m_order,m_prof'")
    if "role" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'dealer'")
    if "allowed_categories" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
    if "logo_path" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN logo_path TEXT DEFAULT ''")
    if "website" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN website TEXT DEFAULT ''")
    if "address_full" not in u_cols: conn.execute("ALTER TABLE users ADD COLUMN address_full TEXT DEFAULT ''")
    
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
    m_cols = [c[1] for c in conn.execute("PRAGMA table_info(models)").fetchall()]
    if "name_zh" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN name_zh TEXT DEFAULT ''")
    if "specs_zh" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN specs_zh TEXT DEFAULT ''")
    if "compatible_options" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN compatible_options TEXT DEFAULT ''")
    if "port_discount" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN port_discount REAL DEFAULT 0.0")
    if "user_id" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN user_id INTEGER DEFAULT 1")
    if "gallery_images" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN gallery_images TEXT DEFAULT ''")
    if "gallery_videos" not in m_cols: conn.execute("ALTER TABLE models ADD COLUMN gallery_videos TEXT DEFAULT ''")

    conn.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)""")
    o_cols = [c[1] for c in conn.execute("PRAGMA table_info(options)").fetchall()]
    if "opt_name_zh" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN opt_name_zh TEXT DEFAULT ''")
    if "opt_desc" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN opt_desc TEXT DEFAULT ''")
    if "opt_desc_zh" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN opt_desc_zh TEXT DEFAULT ''")
    if "allow_qty" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN allow_qty INTEGER DEFAULT 1")
    if "opt_suffix" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN opt_suffix TEXT DEFAULT ''")
    if "opt_variant_image" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN opt_variant_image TEXT DEFAULT ''")
    if "user_id" not in o_cols: conn.execute("ALTER TABLE options ADD COLUMN user_id INTEGER DEFAULT 1")

    conn.commit(); conn.close()

repair_databases()

# =====================================================================
# ÇOKLU DİL MOTORU
# =====================================================================
if 'lang' not in st.session_state: st.session_state.lang = "tr"

DICTIONARY = {
    "tr": {"m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif", "m_cust": "👥 Müşteriler", "m_past": "📋 Geçmiş Teklifler", "m_order": "📦 Siparişler", "m_prof": "⚙️ Profil Ayarları", "m_deal": "🏢 Bayi Yönetimi", "m_model": "📦 Modelleri Yönet", "role_admin": "Yönetici", "role_dealer": "Bayi", "role_manuf": "Üretici"},
    "en": {"m_dash": "📊 Dashboard", "m_new": "📝 New Offer", "m_cust": "👥 Customers", "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_prof": "⚙️ Profile Settings", "m_deal": "🏢 Dealer Mgmt", "m_model": "📦 Manage Models", "role_admin": "Admin", "role_dealer": "Dealer", "role_manuf": "Producer"},
    "zh": {"m_dash": "📊 仪表板", "m_new": "📝 新报价", "m_cust": "👥 客户", "m_past": "📋 历史报价", "m_order": "📦 订单", "m_prof": "⚙️ 配置文件设置", "m_deal": "🏢 经销商管理", "m_model": "📦 管理型号", "role_admin": "管理员", "role_dealer": "经销商", "role_manuf": "制造商"}
}
def _(key): return DICTIONARY.get(st.session_state.lang, DICTIONARY["tr"]).get(key, key)

# =====================================================================
# GİRİŞ VE SİSTEM MANTIĞI
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email", "allowed_menus"]:
    if key not in st.session_state: st.session_state[key] = None

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

    col_slider, col_form = st.columns([1.2, 1], gap="large")
    with col_form:
        st.markdown(f"<h2 style='text-align:center; color:#0f172a; margin-bottom:30px; font-weight:900;'>B2B Sipariş Portalı</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            le = st.text_input("E-Posta", placeholder="ornek@firma.com").strip().lower()
            lp = st.text_input("Şifre", type="password")
            if st.button("GİRİŞ YAP", type="primary", use_container_width=True):
                conn = sqlite3.connect('users.db')
                user = conn.execute("SELECT id, user_type, is_approved, role, allowed_menus FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchone()
                if user:
                    if user[2] == 0: st.warning("Hesap onayı bekleniyor.")
                    else:
                        st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role, st.session_state.user_email, st.session_state.allowed_menus = True, user[0], ('admin' if user[3] == 'admin' else ("manufacturer" if user[1] == "Üretici" else "dealer")), le, user[4]
                        st.rerun()
                else: st.error("Hatalı e-posta veya şifre!")
                conn.close()
    st.stop()

# =====================================================================
# ANA MENÜ VE SAYFA YÖNLENDİRMELERİ
# =====================================================================
with st.sidebar:
    st.markdown(f"<div style='text-align: center; margin-bottom: 15px; padding: 10px 0; font-weight:900; font-size:18px; color:#1e293b;'>B2B Portal</div>", unsafe_allow_html=True)

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
    
    if st.button("🚪 Sistemi Kapat", use_container_width=True):
        st.session_state.clear(); st.rerun()

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
    st.info("Sisteme hoş geldiniz. Sol menüden işlem yapabilirsiniz.")
