import streamlit as st
import streamlit.components.v1 as components
import customer_pages
import model_management
import offer_wizard
import dealer_management
import proforma_invoice # YENİ EKLENEN PROFORMA MODÜLÜ
import datetime
import pandas as pd
import hashlib
import random
import smtplib
import sqlite3
import uuid
import os
import base64
import json

st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()
def generate_code(): return str(random.randint(100000, 999999))

def get_base64_image(path):
    if not img_path and not os.path.exists(path): return ""
    try:
        with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(path)[1].lower().replace('.', '')
        return f"data:image/{ext if ext else 'png'};base64,{b64}"
    except: return ""

def get_system_logo():
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchall()
        conn.close()
        if res and res[0][0]:
            path = res[0][0]
            if path.startswith("http"): return path
            return get_base64_image(path)
    except: pass
    return "https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png"

# =====================================================================
# VERİTABANI BAĞLANTILARI
# =====================================================================
def exec_user_query(query, params=()):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute(query, params); conn.commit(); conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False); c = conn.cursor()
    c.execute(query, params); res = c.fetchall(); conn.close(); return res

def get_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db'); c = conn.cursor()
    c.execute(query, params); conn.commit(); conn.close()

def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def init_advanced_b2b():
    exec_user_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, 
        role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, 
        is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT)""")
    if not get_user_query("SELECT id FROM users WHERE email='admin@ersanmakina.net'"):
        exec_user_query("""INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')""", ("admin@ersanmakina.net", hash_password("20132017")))

init_advanced_b2b()

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email"]:
    if key not in st.session_state: st.session_state[key] = None

if "active_tab" not in st.session_state: st.session_state.active_tab = ":house: Dashboard"
if "main_menu_radio" not in st.session_state: st.session_state.main_menu_radio = ":house: Dashboard"

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        valid_user = get_user_query("SELECT id, user_type, role, email FROM users WHERE session_token=?", (current_token,))
        if valid_user:
            u_id, u_type, u_role, u_email = valid_user[0]
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, u_id, u_email
            st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")

# --- CSS ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 10px 20px; font-weight: 600; color: #475569; border: 1px solid #e2e8f0; white-space: nowrap;}
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; border: 1px solid #2563eb; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 28px; font-weight: 900; color: #1e293b; display: block; }
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; }
    @media (max-width: 768px) { .stTabs [data-baseweb="tab"] { padding: 8px 6px; font-size: 12px; white-space: normal; text-align: center; } .stTabs [data-baseweb="tab-list"] { gap: 4px; } }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# GİRİŞ EKRANI
# =====================================================================
if not st.session_state.logged_in:
    col_left, col_main, col_right = st.columns([1, 1.2, 1])
    with col_main:
        sys_logo = get_system_logo()
        st.markdown(f"""<div style='text-align: center; padding: 20px 0 10px 0;'><img src="{sys_logo}" style="max-height: 80px; margin-bottom: 15px; object-fit: contain;"></div>""", unsafe_allow_html=True)
        t_login, t_reg = st.tabs([":key: Giriş", ":memo: Kayıt"])
        with t_login:
            le = st.text_input("E-Posta Adresi").strip().lower()
            lp = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİRİŞ YAP", type="primary", use_container_width=True):
                user = get_user_query("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", (le, hash_password(lp)))
                if user:
                    if user[0][3] == 0: st.warning("E-posta doğrulanmamış!")
                    elif user[0][2] == 0: st.warning("Hesap onayı bekleniyor.")
                    else:
                        tok = str(uuid.uuid4())
                        exec_user_query("UPDATE users SET session_token=? WHERE id=?", (tok, user[0][0]))
                        st.query_params["session_token"] = tok
                        st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, user[0][0], le
                        st.session_state.user_role = user[0][4] if user[0][4] == 'admin' else ("manufacturer" if user[0][1] == "Üretici" else "dealer")
                        st.rerun()
                else: st.error("Hatalı e-posta veya şifre!")
    st.stop()

# =====================================================================
# GÜVENLİ YAN MENÜ
# =====================================================================
with st.sidebar:
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><img src='{get_system_logo()}' style='max-height: 60px; object-fit: contain;'></div>", unsafe_allow_html=True)
    r_text = {"admin": "Yönetici", "dealer": "Satıcı Bayi", "manufacturer": "Üretici"}.get(st.session_state.user_role, "Kullanıcı")
    st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:8px; text-align:center; color:white; margin-bottom:20px;'><div style='font-size:14px; font-weight:bold;'>&#128100; {st.session_state.user_email}</div><div style='font-size:12px; color:#94a3b8;'>[{r_text}]</div></div>", unsafe_allow_html=True)
    
    menu_items = [":house: Dashboard", ":page_facing_up: Yeni Teklif Hazırla", ":busts_in_silhouette: Müşterilerim", ":clipboard: Geçmiş Tekliflerim", ":gear: Profil Ayarlarım"]
    if st.session_state.user_role == "admin": menu_items.extend([":office: Bayi Yönetimi", ":package: Tüm Modelleri Yönet"])
    
    # PROFORMA VIEW GİZLİ MENÜ DURUMU
    idx = 0
    try: idx = menu_items.index(st.session_state.active_tab)
    except: pass

    def _on_menu_change(): st.session_state.active_tab = st.session_state.main_menu_radio
    menu = st.radio("SİSTEM MENÜSÜ", menu_items, index=idx, key="main_menu_radio", on_change=_on_menu_change, label_visibility="collapsed")
    
    if st.button(":door: Oturumu Kapat", use_container_width=True):
        exec_user_query("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
        st.query_params.clear(); st.session_state.clear(); st.rerun()

# =====================================================================
# SAYFA YÖNLENDİRMELERİ
# =====================================================================

# YENİ PROFORMA EKRANI YÖNLENDİRMESİ
if st.session_state.active_tab == "PROFORMA_VIEW":
    proforma_invoice.show_proforma(st.session_state.get("proforma_offer_id"), st.session_state.user_id)

elif st.session_state.active_tab == ":house: Dashboard":
    st.header(":bar_chart: Analiz Paneli")
    if st.session_state.user_role == "admin":
        offers_raw = get_sales("SELECT total_price, status, offer_date FROM offers")
        df_dash = pd.DataFrame(offers_raw, columns=["Tutar", "Durum", "Tarih"])
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><span class="stat-title">Toplam Hacim</span><span class="stat-val">{df_dash["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Bekleyen</span><span class="stat-val">{df_dash[df_dash["Durum"]=="Beklemede"]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Satış</span><span class="stat-val">{df_dash[df_dash["Durum"].isin(["Onaylandı", "Siparişe Çevir"])]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color:#6366f1;"><span class="stat-title">Bayi Sayısı</span><span class="stat-val">{get_user_query("SELECT COUNT(*) FROM users WHERE role=\'dealer\'")[0][0]}</span></div>', unsafe_allow_html=True)

        st.subheader("🔄 Tüm Bayilerin Son Teklifleri")
        
        # Admin Bayi İsimlerini Çeker
        users_raw = get_user_query("SELECT id, company_name FROM users")
        user_dict = {u[0]: u[1] for u in users_raw}

        recent_offers_raw = get_sales("SELECT o.id, c.company_name, o.model_id, o.total_price, o.status, o.user_id FROM offers o JOIN customers c ON o.customer_id = c.id ORDER BY o.id DESC LIMIT 15")
        
        if recent_offers_raw:
            for oid, cust, mid, price, stat, uid in recent_offers_raw:
                m_name_res = get_factory("SELECT name FROM models WHERE id=?", (mid,))
                mod = m_name_res[0][0] if m_name_res else "Bilinmeyen Model"
                bayi_ismi = user_dict.get(uid, "Bilinmeyen Bayi")
                
                with st.container(border=True):
                    ca, cb, cc = st.columns([3, 1, 1])
                    ca.markdown(f"**{cust}** (Bayi: <span style='color:#2563eb;'>{bayi_ismi}</span>)<br><small>{mod} | {price:,.2f}</small>", unsafe_allow_html=True)
                    new_stat = cb.selectbox("Durum", ["Beklemede", "Siparişe Çevir", "Reddedildi"], index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(stat if stat in ["Beklemede", "Siparişe Çevir", "Reddedildi"] else "Beklemede"), key=f"stat_{oid}", label_visibility="collapsed")
                    if cc.button("Güncelle", key=f"btn_{oid}", use_container_width=True):
                        exec_sales("UPDATE offers SET status=? WHERE id=?", (new_stat, oid))
                        st.toast(f"Teklif #{oid} güncellendi!"); st.rerun()

elif st.session_state.active_tab == ":clipboard: Geçmiş Tekliflerim":
    st.header(":clipboard: Geçmiş Tekliflerim")
    # Admin tüm teklifleri görür
    q = "SELECT o.id, c.company_name, o.model_id, o.offer_date, o.total_price, o.status FROM offers o JOIN customers c ON o.customer_id = c.id ORDER BY o.id DESC" if st.session_state.user_role == 'admin' else "SELECT o.id, c.company_name, o.model_id, o.offer_date, o.total_price, o.status FROM offers o JOIN customers c ON o.customer_id = c.id WHERE o.user_id=? ORDER BY o.id DESC"
    p = () if st.session_state.user_role == 'admin' else (st.session_state.user_id,)
    offers_raw = get_sales(q, p)
    
    if offers_raw:
        for off in offers_raw:
            off_id, c_name, m_id, o_date, t_price, o_status = off
            status_color = "#10b981" if o_status in ["Onaylandı", "Siparişe Çevir"] else ("#ef4444" if o_status == "Reddedildi" else "#f59e0b")
            m_name_res = get_factory("SELECT name FROM models WHERE id=?", (m_id,))
            m_name = m_name_res[0][0] if m_name_res else "Bilinmeyen Model"
            
            with st.container(border=True):
                st.markdown(f"<h4 style='margin:0; color:#0f172a;'>{c_name}</h4>", unsafe_allow_html=True)
                st.markdown(f"**Model:** {m_name} | **Tarih:** {o_date} | **Durum:** <span style='color:{status_color}; font-weight:bold;'>{o_status}</span>", unsafe_allow_html=True)
                st.write("")
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                if btn_col1.button("✏️ Düzenle", key=f"ed_{off_id}", use_container_width=True):
                    offer_wizard.load_offer_to_wizard(off_id) # Fonksiyonu offer_wizard'ın içine taşıdık
                    st.session_state.edit_offer_id = off_id
                    st.session_state.active_tab = ":page_facing_up: Yeni Teklif Hazırla"
                    st.rerun()
                if btn_col3.button("🗑️ Sil", key=f"rm_{off_id}", use_container_width=True):
                    exec_sales("DELETE FROM offers WHERE id=?", (off_id,))
                    exec_sales("DELETE FROM offer_items WHERE offer_id=?", (off_id,))
                    st.rerun()
    else: st.info("Geçmiş teklif bulunmuyor.")

elif st.session_state.active_tab == ":page_facing_up: Yeni Teklif Hazırla":
    offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == ":busts_in_silhouette: Müşterilerim":
    customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == ":package: Tüm Modelleri Yönet":
    model_management.show_product_management()
elif st.session_state.active_tab == ":office: Bayi Yönetimi":
    dealer_management.show_dealer_management()
elif st.session_state.active_tab == ":gear: Profil Ayarlarım":
    st.info("Profil ayarları modülü buradadır.")
