import streamlit as st
import streamlit.components.v1 as components
import database
import customer_pages
import model_management
import offer_wizard
import dealer_management
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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()
def generate_code(): return str(random.randint(100000, 999999))

def get_base64_image(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return "https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png"

def get_system_logo():
    try:
        res = database.get_query("SELECT logo_path FROM company_profile WHERE id=1")
        if res and res[0][0]:
            path = res[0][0]
            if path.startswith("http"): return path
            return get_base64_image(path)
    except: pass
    return "https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png"

def send_email(to_email, code, subject="Ersan Makine - Doğrulama Kodu"):
    SMTP_SERVER = "mail.ersanmakina.net"; SMTP_PORT = 587
    SENDER_EMAIL = "sefa@ersanmakina.net"; SENDER_PASSWORD = "Sev32881-"
    msg = MIMEMultipart(); msg['From'] = f"Ersan Makine B2B <{SENDER_EMAIL}>"; msg['To'] = to_email; msg['Subject'] = subject
    msg.attach(MIMEText(f"Doğrulama Kodunuz: {code}", 'plain'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(); server.login(SENDER_EMAIL, SENDER_PASSWORD); server.send_message(msg); server.quit()
        return True
    except: return False

# =====================================================================
# VERİTABANI İNŞASI
# =====================================================================
def exec_user_query(query, params=()):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute(query, params); conn.commit(); conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False); c = conn.cursor()
    c.execute(query, params); res = c.fetchall(); conn.close(); return res

def init_advanced_b2b():
    exec_user_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, 
        role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, 
        is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT)""")
    conn = sqlite3.connect('users.db'); cursor = conn.cursor()
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "logo_path" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN logo_path TEXT")
    if "website" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN website TEXT")
    if "address_full" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN address_full TEXT")
    conn.commit(); conn.close()
    database.exec_query("""CREATE TABLE IF NOT EXISTS company_profile (id INTEGER PRIMARY KEY CHECK (id = 1), company_name TEXT, logo_path TEXT)""")
    if not database.get_query("SELECT id FROM company_profile WHERE id=1"):
        database.exec_query("INSERT INTO company_profile (id, logo_path) VALUES (1, 'https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png')")
    if not get_user_query("SELECT id FROM users WHERE email='admin@ersanmakina.net'"):
        exec_user_query("""INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')""", ("admin@ersanmakina.net", hash_password("20132017")))
init_advanced_b2b()

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
for key in ["user_id", "user_role", "user_email"]:
    if key not in st.session_state: st.session_state[key] = None
if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1

# HATA ÇÖZÜMÜ: Ana Menü Değişkeni Değiştirildi
if "active_tab" not in st.session_state: st.session_state.active_tab = ":house: Dashboard"

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        valid_user = get_user_query("SELECT id, user_type, role, email FROM users WHERE session_token=?", (current_token,))
        if valid_user:
            u_id, u_type, u_role, u_email = valid_user[0]
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, u_id, u_email
            st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")

# --- GÜÇLÜ VE MOBİL UYUMLU CSS ---
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
        st.markdown(f"""<div style='text-align: center; padding: 20px 0 10px 0;'><img src="{sys_logo}" style="max-width: 100%; height: auto; max-height: 80px; margin-bottom: 15px; object-fit: contain;"><p style='color: #64748b; font-size: 14px;'>Sisteme erişmek için bilgilerinizi giriniz.</p></div>""", unsafe_allow_html=True)
        t_login, t_reg, t_forg = st.tabs([":key: Giriş", ":memo: Kayıt", ":question: Şifre"])
        with t_login:
            with st.container(border=True):
                le = st.text_input("E-Posta Adresi").strip().lower()
                lp = st.text_input("Şifre", type="password")
                rem = st.checkbox("Beni Hatırla", value=True)
                if st.button("SİSTEME GİRİŞ YAP", type="primary", use_container_width=True):
                    user = get_user_query("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", (le, hash_password(lp)))
                    if user:
                        if user[0][3] == 0: st.warning(":warning: E-posta doğrulanmamış!")
                        elif user[0][2] == 0: st.warning(":hourglass_flowing_sand: Hesap onayı bekleniyor.")
                        else:
                            tok = str(uuid.uuid4())
                            exec_user_query("UPDATE users SET session_token=? WHERE id=?", (tok, user[0][0]))
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, user[0][0], le
                            st.session_state.user_role = user[0][4] if user[0][4] == 'admin' else ("manufacturer" if user[0][1] == "Üretici" else "dealer")
                            st.rerun()
                    else: st.error("Hatalı e-posta veya şifre!")
        with t_reg:
            with st.container(border=True):
                if st.session_state.reg_step == 1:
                    reg_type = st.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"])
                    reg_comp = st.text_input("Firma Tam Ünvanı *")
                    reg_phone = st.text_input("Telefon *")
                    reg_email = st.text_input("E-Posta *").strip().lower()
                    reg_pwd = st.text_input("Şifre *", type="password")
                    if st.button("Kayıt Ol", use_container_width=True):
                        if all([reg_comp, reg_phone, reg_email, reg_pwd]):
                            if get_user_query("SELECT id FROM users WHERE email=?", (reg_email,)): st.error("E-posta kullanımda!")
                            else:
                                ver_code = generate_code()
                                exec_user_query("INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)", (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code))
                                if send_email(reg_email, ver_code, "Doğrulama Kodu"):
                                    st.session_state.temp_email, st.session_state.reg_step = reg_email, 2; st.rerun()
                        else: st.warning("(*) alanlar zorunludur.")
                elif st.session_state.reg_step == 2:
                    entered_code = st.text_input("Kodu Girin", max_chars=6)
                    if st.button("Onayla", type="primary", use_container_width=True):
                        db_code = get_user_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                        if db_code and db_code[0][0] == entered_code:
                            exec_user_query("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                            st.session_state.reg_step = 1; st.success("Doğrulandı! Onay sonrası giriş yapabilirsiniz.")
                        else: st.error("Hatalı kod!")
        with t_forg:
            with st.container(border=True):
                if st.session_state.forgot_step == 1:
                    f_email = st.text_input("E-Posta Adresiniz").strip().lower()
                    if st.button("Sıfırlama Kodu Gönder", use_container_width=True):
                        if f_email and get_user_query("SELECT id FROM users WHERE email=?", (f_email,)):
                            reset_code = generate_code()
                            exec_user_query("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            if send_email(f_email, reset_code, "Sıfırlama Kodu"):
                                st.session_state.temp_email, st.session_state.forgot_step = f_email, 2; st.rerun()
                        else: st.error("E-posta bulunamadı.")
                elif st.session_state.forgot_step == 2:
                    f_code = st.text_input("6 Haneli Kod", max_chars=6)
                    new_pwd = st.text_input("Yeni Şifre", type="password")
                    if st.button("Şifre Değiştir", type="primary", use_container_width=True):
                        valid_code = get_user_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                        if valid_code and valid_code[0][0] == f_code and len(new_pwd) > 0:
                            exec_user_query("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(new_pwd), st.session_state.temp_email))
                            st.session_state.forgot_step = 1; st.success("Şifreniz değiştirildi!")
                        else: st.error("Hata!")
    st.stop()

# =====================================================================
# GÜVENLİ YAN MENÜ (HATA ÇÖZÜMÜ)
# =====================================================================
with st.sidebar:
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><img src='{get_system_logo()}' style='max-height: 60px; object-fit: contain;'></div>", unsafe_allow_html=True)
    r_text = {"admin": "Yönetici", "dealer": "Satıcı Bayi", "manufacturer": "Üretici"}.get(st.session_state.user_role, "Kullanıcı")
    st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:8px; text-align:center; color:white; margin-bottom:20px;'><div style='font-size:14px; font-weight:bold;'>&#128100; {st.session_state.user_email}</div><div style='font-size:12px; color:#94a3b8;'>[{r_text}]</div></div>", unsafe_allow_html=True)
    
    menu_items = [":house: Dashboard", ":page_facing_up: Yeni Teklif Hazırla", ":busts_in_silhouette: Müşterilerim", ":clipboard: Geçmiş Tekliflerim", ":gear: Profil Ayarlarım"]
    if st.session_state.user_role == "admin": menu_items.extend([":office: Bayi Yönetimi", ":package: Tüm Modelleri Yönet"])
    
    # HATA ÇÖZÜMÜ: Yönlendirme güvenli hale getirildi
    try: m_idx = menu_items.index(st.session_state.active_tab)
    except: m_idx = 0
        
    def _on_menu_change():
        st.session_state.active_tab = st.session_state._menu_radio
        
    menu = st.radio("SİSTEM MENÜSÜ", menu_items, index=m_idx, key="_menu_radio", on_change=_on_menu_change, label_visibility="collapsed")
    
    # Mobilde menü gizleme kodu
    components.html("""<script>const doc=window.parent.document;doc.querySelectorAll('div[data-testid="stSidebar"] .stRadio label').forEach(r=>{r.addEventListener('click',()=>{if(window.parent.innerWidth<=768){setTimeout(()=>{let b=doc.querySelector('div[data-testid="stSidebar"] + div');if(b)b.click();doc.dispatchEvent(new KeyboardEvent('keydown',{'key':'Escape'}));},100);}});});</script>""", height=0, width=0)
    
    st.markdown("---")
    if st.button(":door: Oturumu Kapat", use_container_width=True):
        exec_user_query("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
        st.query_params.clear(); st.session_state.clear(); st.rerun()

# =====================================================================
# SAYFA İÇERİKLERİ VE YÖNLENDİRMELER
# =====================================================================
if st.session_state.active_tab == ":house: Dashboard":
    st.header(":bar_chart: Analiz Paneli")
    if st.session_state.user_role == "admin":
        offers_raw = database.get_query("SELECT total_price, status, offer_date FROM offers")
        df_dash = pd.DataFrame(offers_raw, columns=["Tutar", "Durum", "Tarih"])
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><span class="stat-title">Toplam Hacim</span><span class="stat-val">{df_dash["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Bekleyen</span><span class="stat-val">{df_dash[df_dash["Durum"]=="Beklemede"]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Satış</span><span class="stat-val">{df_dash[df_dash["Durum"]=="Onaylandı"]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color:#6366f1;"><span class="stat-title">Bayi Sayısı</span><span class="stat-val">{get_user_query("SELECT COUNT(*) FROM users WHERE role=\'dealer\'")[0][0]}</span></div>', unsafe_allow_html=True)

        st.subheader("🔄 Son Tekliflerin Durumu")
        recent_offers = database.get_query("SELECT o.id, c.company_name, m.name, o.total_price, o.status FROM offers o JOIN customers c ON o.customer_id = c.id JOIN models m ON o.model_id = m.id ORDER BY o.id DESC LIMIT 10")
        if recent_offers:
            for oid, cust, mod, price, stat in recent_offers:
                with st.container(border=True):
                    ca, cb, cc = st.columns([3, 1, 1])
                    ca.markdown(f"**{cust}**<br><small>{mod} | {price:,.2f}</small>", unsafe_allow_html=True)
                    new_stat = cb.selectbox("Durum", ["Beklemede", "Onaylandı", "Reddedildi"], index=["Beklemede", "Onaylandı", "Reddedildi"].index(stat if stat in ["Beklemede", "Onaylandı", "Reddedildi"] else "Beklemede"), key=f"stat_{oid}", label_visibility="collapsed")
                    if cc.button("Güncelle", key=f"btn_{oid}", use_container_width=True):
                        database.exec_query("UPDATE offers SET status=? WHERE id=?", (new_stat, oid))
                        st.toast(f"Teklif #{oid} güncellendi!"); st.rerun()

# ---------------- TEKLİF DÜZENLEME MOTORU ----------------
elif st.session_state.active_tab == ":clipboard: Geçmiş Tekliflerim":
    st.header(":clipboard: Geçmiş Tekliflerim")
    offers = database.get_query("""SELECT o.id, c.company_name, m.name, o.offer_date, o.total_price, o.status FROM offers o JOIN customers c ON o.customer_id = c.id JOIN models m ON o.model_id = m.id WHERE o.user_id=? ORDER BY o.id DESC""", (st.session_state.user_id,))
    
    if offers:
        df = pd.DataFrame(offers, columns=["Kayıt No", "Müşteri", "Model", "Tarih", "Tutar", "Durum"])
        st.dataframe(df.set_index("Kayıt No"), use_container_width=True)
        
        st.markdown("---")
        st.subheader(":gear: Teklif İşlemleri (Düzenle / Sil)")
        
        offer_dict = {f"Teklif #{o[0]} - {o[1]} ({o[2]})": o[0] for o in offers}
        sel_off = st.selectbox("İşlem yapılacak teklifi seçin:", ["Seçiniz..."] + list(offer_dict.keys()))
        
        if sel_off != "Seçiniz...":
            off_id = offer_dict[sel_off]
            c1, c2, c3 = st.columns([2, 2, 1])
            
            if c1.button(":pencil2: Bu Teklifi Geri Çağır ve Düzenle", type="primary", use_container_width=True):
                # 1. Eski donanım ve şart belleklerini temizle
                for key in list(st.session_state.keys()):
                    if key.startswith("o_") or key.startswith("q_") or key == "temp_del_type": del st.session_state[key]
                
                # 2. Verileri DB'den topla
                off_data = database.get_query("SELECT customer_id, model_id, conditions FROM offers WHERE id=?", (off_id,))[0]
                conds = json.loads(off_data[2]) if off_data[2] else {}
                m_data = database.get_query("SELECT name, base_price, currency, compatible_options, image_path, specs, port_discount FROM models WHERE id=?", (off_data[1],))[0]
                c_name = database.get_query("SELECT company_name FROM customers WHERE id=?", (off_data[0],))[0][0]
                
                # 3. Sihirbazı Doldur
                st.session_state.wizard_data = {
                    "cust_id": off_data[0], "cust_name": c_name, "m_id": off_data[1], "m_name": m_data[0],
                    "m_price": m_data[1], "m_curr": m_data[2], "m_opts": m_data[3], "m_img": m_data[4], "m_specs": m_data[5], "m_disc": m_data[6], 
                    "qty": conds.get("machine_qty", 1), "d_time": conds.get("delivery_time", ""), "ship": conds.get("shipping", ""),
                    "pay": conds.get("payment_plan_text", ""), "bnk": conds.get("bank", ""), "nts": conds.get("notes", ""), "disc_p": conds.get("discount_pct", 0.0)
                }
                
                # 4. Seçili Opsiyonları Geri Getir
                opt_items = database.get_query("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (off_id,))
                for op_id, o_qty in opt_items:
                    st.session_state[f"o_{op_id}"] = True
                    st.session_state[f"q_{op_id}"] = o_qty
                    
                st.session_state["temp_del_type"] = conds.get("delivery_type", "Gümrük İşlemleri Yapılmış Antrepo Teslim")
                st.session_state.edit_offer_id = off_id
                st.session_state.wizard_step = 2
                
                # 5. SİHİRBAZA GÜVENLİ YÖNLENDİR (Hata veren yer burasıydı)
                st.session_state.active_tab = ":page_facing_up: Yeni Teklif Hazırla"
                if "_menu_radio" in st.session_state:
                    del st.session_state["_menu_radio"]
                st.rerun()
                
            if c2.button(":wastebasket: Teklifi Sistemden Sil", use_container_width=True):
                database.exec_query("DELETE FROM offers WHERE id=?", (off_id,))
                database.exec_query("DELETE FROM offer_items WHERE offer_id=?", (off_id,))
                st.error("Teklif silindi!"); st.rerun()
    else:
        st.info("Henüz geçmiş bir teklifiniz bulunmuyor.")

elif st.session_state.active_tab == ":gear: Profil Ayarlarım":
    st.header(":gear: Kurumsal Profil Ayarları")
    u_data = get_user_query("SELECT company_name, email, phone, website, address_full, logo_path FROM users WHERE id=?", (st.session_state.user_id,))[0]
    with st.expander("👤 Bayi / Kişisel Bilgilerim", expanded=True):
        with st.form("p_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Firma Adı", value=u_data[0])
            p_web = c2.text_input("Web Sitesi", value=u_data[3] if u_data[3] else "")
            p_phone = c1.text_input("Telefon", value=u_data[2] if u_data[2] else "")
            p_adr = st.text_area("Açık Adres", value=u_data[4] if u_data[4] else "")
            up_logo = st.file_uploader("Tekliflerde Görünecek Logonuz", type=['png','jpg','jpeg'])
            if st.form_submit_button(":white_check_mark: PROFİLİ GÜNCELLE", type="primary"):
                f_logo = u_data[5]
                if up_logo:
                    if not os.path.exists("images"): os.makedirs("images")
                    f_logo = f"images/logo_user_{st.session_state.user_id}.png"
                    with open(f_logo, "wb") as f: f.write(up_logo.getbuffer())
                exec_user_query("UPDATE users SET company_name=?, website=?, phone=?, address_full=?, logo_path=? WHERE id=?", (p_name, p_web, p_phone, p_adr, f_logo, st.session_state.user_id))
                st.success("Profiliniz başarıyla güncellendi!"); st.rerun()
    if st.session_state.user_role == "admin":
        with st.expander("🚀 SİSTEM GENEL AYARLARI (Sadece Yönetici)", expanded=True):
            with st.form("sys_form"):
                new_sys_logo = st.file_uploader("Yeni Sistem Logosu Seçin", type=['png','jpg','jpeg'])
                if st.form_submit_button(":rocket: SİSTEM LOGOSUNU DEĞİŞTİR"):
                    if new_sys_logo:
                        if not os.path.exists("images"): os.makedirs("images")
                        sys_path = f"images/system_logo_main.png"
                        with open(sys_path, "wb") as f: f.write(new_sys_logo.getbuffer())
                        database.exec_query("UPDATE company_profile SET logo_path=? WHERE id=1", (sys_path,))
                        st.success("Sistem logosu başarıyla değiştirildi!"); st.rerun()

elif st.session_state.active_tab == ":page_facing_up: Yeni Teklif Hazırla":
    offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == ":busts_in_silhouette: Müşterilerim":
    customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == ":package: Tüm Modelleri Yönet":
    model_management.show_product_management()
elif st.session_state.active_tab == ":office: Bayi Yönetimi":
    dealer_management.show_dealer_management()
