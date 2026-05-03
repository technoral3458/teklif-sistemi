import streamlit as st
import customer_pages, model_management, offer_wizard, dealer_management, proforma_invoice
import sqlite3, pandas as pd, hashlib, random, smtplib, uuid, os, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ntpath, posixpath

st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# GÜVENLİK VE MAİL FONKSİYONLARI
# =====================================================================
def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()
def generate_code(): return str(random.randint(100000, 999999))

def send_email(to_email, code, subject="Ersan Makine - Doğrulama Kodu"):
    SMTP_SERVER = "mail.ersanmakina.net"; SMTP_PORT = 587
    SENDER_EMAIL = "sefa@ersanmakina.net"; SENDER_PASSWORD = "Sev32881-"
    msg = MIMEMultipart(); msg['From'] = f"Ersan Makine B2B <{SENDER_EMAIL}>"; msg['To'] = to_email; msg['Subject'] = subject
    msg.attach(MIMEText(f"Sistem Doğrulama Kodunuz: {code}", 'plain'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(); server.login(SENDER_EMAIL, SENDER_PASSWORD); server.send_message(msg); server.quit()
        return True
    except: return False

# =====================================================================
# GELİŞMİŞ LOGO OKUMA MOTORU 
# =====================================================================
def get_base64_image(path):
    if not path: return ""
    if str(path).startswith("http"): return path
    base_name = posixpath.basename(ntpath.basename(path))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    ext = os.path.splitext(p)[1].lower().replace('.', '')
                    if not ext: ext = 'png'
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except: pass
    return ""

def get_system_logo():
    fallback_url = "https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png"
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        res = conn.execute("SELECT logo_path FROM company_profile WHERE id=1").fetchall()
        conn.close()
        if res and res[0][0]:
            b64 = get_base64_image(res[0][0])
            if b64: return b64
    except: pass
    return fallback_url

# =====================================================================
# VERİTABANI TAMİRCİSİ
# =====================================================================
def repair_databases():
    conn = sqlite3.connect('users.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0, user_type TEXT DEFAULT 'Satıcı', phone TEXT, is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT, logo_path TEXT, website TEXT, address_full TEXT)""")
    if not conn.execute("SELECT id FROM users WHERE email='admin@ersanmakina.net'").fetchall():
        conn.execute("""INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')""", ("admin@ersanmakina.net", hash_password("20132017")))
    conn.commit(); conn.close()

    conn = sqlite3.connect('sales_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, model_id INTEGER)""")
    cols = [c[1] for c in conn.execute("PRAGMA table_info(offers)").fetchall()]
    if "total_price" not in cols: conn.execute("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
    if "conditions" not in cols: conn.execute("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
    if "status" not in cols: conn.execute("ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'Beklemede'")
    if "user_id" not in cols: conn.execute("ALTER TABLE offers ADD COLUMN user_id INTEGER DEFAULT 1")
    if "offer_date" not in cols: conn.execute("ALTER TABLE offers ADD COLUMN offer_date TEXT DEFAULT ''")
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
if "active_tab" not in st.session_state: st.session_state.active_tab = ":house: Dashboard"

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        valid_user = conn.execute("SELECT id, user_type, role, email FROM users WHERE session_token=?", (current_token,)).fetchall()
        conn.close()
        if valid_user:
            u_id, u_type, u_role, u_email = valid_user[0]
            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, u_id, u_email
            st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")

# --- GELİŞMİŞ ARAYÜZ VE MODERN MENÜ CSS ---
st.markdown("""
    <style>
    /* Genel Panel Sekmeleri (Tabs) */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 10px 20px; font-weight: 600; color: #475569; border: 1px solid #e2e8f0; white-space: nowrap;}
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; border: 1px solid #2563eb; }
    
    /* Dashboard İstatistik Kartları */
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 28px; font-weight: 900; color: #1e293b; display: block; }
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; }
    
    /* =========================================
       MODERN YAN MENÜ SİHİRBAZLIĞI (CSS)
       ========================================= */
    /* 1. Orijinal yuvarlak seçim kutularını tamamen gizle */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    /* 2. Menü elemanlarının arasındaki boşlukları daralt */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 6px !important;
    }
    
    /* 3. Menü elemanlarını şık butonlara/bloklara çevir */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 12px 15px;
        margin-bottom: 0px;
        border-radius: 8px;
        background-color: transparent;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
        width: 100%;
        color: #475569;
    }
    
    /* 4. Mouse ile üzerine gelindiğinde (Hover) */
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: #e2e8f0;
        color: #0f172a;
    }
    
    /* 5. Aktif olan (Seçili) menü elemanı */
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #2563eb !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
    }
    
    /* 6. Aktif elemanın yazı rengini beyaz yap */
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Menü içi yazı font ayarı */
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        font-size: 15px !important;
        font-weight: 600;
    }
    
    @media (max-width: 768px) { .stTabs [data-baseweb="tab"] { padding: 8px 6px; font-size: 12px; white-space: normal; text-align: center; } .stTabs [data-baseweb="tab-list"] { gap: 4px; } }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# GİRİŞ, KAYIT VE ŞİFRE EKRANLARI
# =====================================================================
if not st.session_state.logged_in:
    col_left, col_main, col_right = st.columns([1, 1.2, 1])
    with col_main:
        sys_logo = get_system_logo()
        st.markdown(f"""<div style='text-align: center; padding: 20px 0 10px 0;'><img src="{sys_logo}" style="max-height: 80px; margin-bottom: 15px; object-fit: contain;"></div>""", unsafe_allow_html=True)
        
        t_login, t_reg, t_forg = st.tabs([":key: Giriş", ":memo: Kayıt", ":question: Şifremi Unuttum"])
        
        with t_login:
            with st.container(border=True):
                le = st.text_input("E-Posta Adresi").strip().lower()
                lp = st.text_input("Şifre", type="password")
                rem = st.checkbox("Beni Hatırla", value=True)
                if st.button("SİSTEME GİRİŞ YAP", type="primary", use_container_width=True):
                    conn = sqlite3.connect('users.db')
                    user = conn.execute("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", (le, hash_password(lp))).fetchall()
                    if user:
                        if user[0][3] == 0: st.warning("E-posta doğrulanmamış!")
                        elif user[0][2] == 0: st.warning("Hesap onayı bekleniyor.")
                        else:
                            tok = str(uuid.uuid4())
                            conn.execute("UPDATE users SET session_token=? WHERE id=?", (tok, user[0][0]))
                            conn.commit()
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, user[0][0], le
                            st.session_state.user_role = user[0][4] if user[0][4] == 'admin' else ("manufacturer" if user[0][1] == "Üretici" else "dealer")
                            st.rerun()
                    else: st.error("Hatalı e-posta veya şifre!")
                    conn.close()

        with t_reg:
            with st.container(border=True):
                if st.session_state.reg_step == 1:
                    reg_type = st.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"])
                    reg_comp = st.text_input("Firma Tam Ünvanı *")
                    reg_phone = st.text_input("Telefon *")
                    reg_email = st.text_input("Kayıt E-Posta *").strip().lower()
                    reg_pwd = st.text_input("Kayıt Şifre *", type="password")
                    if st.button("Kayıt Ol", use_container_width=True):
                        if all([reg_comp, reg_phone, reg_email, reg_pwd]):
                            conn = sqlite3.connect('users.db')
                            if conn.execute("SELECT id FROM users WHERE email=?", (reg_email,)).fetchall(): st.error("E-posta kullanımda!")
                            else:
                                ver_code = generate_code()
                                conn.execute("INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)", (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code))
                                conn.commit()
                                if send_email(reg_email, ver_code, "Kayıt Doğrulama Kodu"):
                                    st.session_state.temp_email, st.session_state.reg_step = reg_email, 2; st.rerun()
                                else: st.error("E-posta gönderilemedi.")
                            conn.close()
                        else: st.warning("(*) alanlar zorunludur.")
                elif st.session_state.reg_step == 2:
                    entered_code = st.text_input("Mailinize Gelen Kodu Girin", max_chars=6)
                    if st.button("Onayla", type="primary", use_container_width=True):
                        conn = sqlite3.connect('users.db')
                        db_code = conn.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,)).fetchall()
                        if db_code and db_code[0][0] == entered_code:
                            conn.execute("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                            conn.commit()
                            st.session_state.reg_step = 1; st.success("Doğrulandı! Yönetici onayı sonrası giriş yapabilirsiniz.")
                        else: st.error("Hatalı kod!")
                        conn.close()

        with t_forg:
            with st.container(border=True):
                if st.session_state.forgot_step == 1:
                    f_email = st.text_input("Kayıtlı E-Posta Adresiniz").strip().lower()
                    if st.button("Sıfırlama Kodu Gönder", use_container_width=True):
                        conn = sqlite3.connect('users.db')
                        if conn.execute("SELECT id FROM users WHERE email=?", (f_email,)).fetchone():
                            reset_code = generate_code()
                            conn.execute("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            conn.commit()
                            if send_email(f_email, reset_code, "Şifre Sıfırlama Kodu"):
                                st.session_state.temp_email = f_email; st.session_state.forgot_step = 2; st.rerun()
                            else: st.error("E-posta gönderilemedi.")
                        else: st.error("Sistemde böyle bir e-posta bulunamadı.")
                        conn.close()
                elif st.session_state.forgot_step == 2:
                    f_code = st.text_input("Mailinize Gelen 6 Haneli Kod", max_chars=6)
                    new_pwd = st.text_input("Yeni Şifre Belirleyin", type="password")
                    if st.button("Şifremi Değiştir", type="primary", use_container_width=True):
                        conn = sqlite3.connect('users.db')
                        valid_code = conn.execute("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,)).fetchone()
                        if valid_code and valid_code[0] == f_code and len(new_pwd) > 3:
                            conn.execute("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(new_pwd), st.session_state.temp_email))
                            conn.commit()
                            st.session_state.forgot_step = 1
                            st.success("Şifreniz değiştirildi! Giriş sekmesinden giriş yapabilirsiniz.")
                        else: st.error("Hatalı kod veya çok kısa şifre!")
                        conn.close()
    st.stop()

# =====================================================================
# GÜVENLİ VE MODERN YAN MENÜ
# =====================================================================
with st.sidebar:
    st.markdown(f"<div style='text-align: center; margin-bottom: 25px; margin-top: 10px;'><img src='{get_system_logo()}' style='max-height: 65px; object-fit: contain;'></div>", unsafe_allow_html=True)
    
    # Modern Profil Kartı
    r_text = {"admin": "Sistem Yöneticisi", "dealer": "Satıcı Bayi", "manufacturer": "Üretici"}.get(st.session_state.user_role, "Kullanıcı")
    st.markdown(f"""
        <div style='background-color:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:25px; display:flex; align-items:center; gap:10px;'>
            <div style='background:#2563eb; color:white; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:16px;'>
                {st.session_state.user_email[0].upper()}
            </div>
            <div style='overflow:hidden;'>
                <div style='font-size:13px; font-weight:700; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;'>{st.session_state.user_email}</div>
                <div style='font-size:11px; color:#64748b; font-weight:600;'>{r_text}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Menü Öğeleri
    menu_items = [
        "📊 Dashboard", 
        "📝 Yeni Teklif Hazırla", 
        "👥 Müşterilerim", 
        "📋 Geçmiş Tekliflerim", 
        "⚙️ Profil Ayarlarım"
    ]
    if st.session_state.user_role == "admin": 
        menu_items.extend(["🏢 Bayi Yönetimi", "📦 Tüm Modelleri Yönet"])
    
    idx = menu_items.index(st.session_state.active_tab) if st.session_state.active_tab in menu_items else 0
    
    def sync_menu(): 
        st.session_state.active_tab = st.session_state.m_radio

    # CSS ile gizlenen gizli radyolar
    st.radio("MENÜ", menu_items, index=idx, key="m_radio", on_change=sync_menu, label_visibility="collapsed")

    st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    
    # Çıkış Butonu
    if st.button("🚪 Sistemi Kapat", use_container_width=True):
        conn = sqlite3.connect('users.db')
        conn.execute("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
        conn.commit(); conn.close()
        st.query_params.clear(); st.session_state.clear(); st.rerun()

# =====================================================================
# SAYFA YÖNLENDİRİCİ MOTORU
# =====================================================================
if st.session_state.active_tab == "PROFORMA":
    proforma_invoice.show_proforma(st.session_state.proforma_id, st.session_state.user_id)
elif st.session_state.active_tab == "👥 Müşterilerim":
    customer_pages.show_customer_management(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == "📝 Yeni Teklif Hazırla":
    offer_wizard.show_offer_wizard(st.session_state.user_id, st.session_state.user_role == "admin")
elif st.session_state.active_tab == "📦 Tüm Modelleri Yönet":
    model_management.show_product_management()
elif st.session_state.active_tab == "🏢 Bayi Yönetimi":
    dealer_management.show_dealer_management()

# =====================================================================
# GELİŞMİŞ DASHBOARD (ANALİZ PANELİ VE BAYİ TAKİBİ)
# =====================================================================
elif st.session_state.active_tab == "📊 Dashboard":
    st.header("📊 Analiz ve Bayi Takip Paneli")
    
    if st.session_state.user_role == "admin":
        conn_u = sqlite3.connect('users.db')
        users_raw = conn_u.execute("SELECT id, company_name FROM users").fetchall()
        user_dict = {u[0]: u[1] for u in users_raw}
        d_count = conn_u.execute("SELECT COUNT(*) FROM users WHERE role='dealer'").fetchone()[0]
        conn_u.close()

        conn_s = sqlite3.connect('sales_data.db')
        offers_raw = conn_s.execute("SELECT id, customer_id, model_id, total_price, status, user_id, offer_date FROM offers").fetchall()
        conn_s.close()

        if offers_raw:
            df_offers = pd.DataFrame(offers_raw, columns=["id", "customer_id", "model_id", "total_price", "status", "user_id", "offer_date"])
            df_offers['Bayi'] = df_offers['user_id'].map(user_dict).fillna("Bilinmeyen Bayi")
            
            # --- 1. KPI KARTLARI ---
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="stat-card"><span class="stat-title">Toplam Teklif Hacmi</span><span class="stat-val">{df_offers["total_price"].sum():,.2f}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Bekleyen Hacim</span><span class="stat-val">{df_offers[df_offers["status"]=="Beklemede"]["total_price"].sum():,.2f}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Satışa Dönen (Sipariş)</span><span class="stat-val">{df_offers[df_offers["status"].isin(["Onaylandı", "Siparişe Çevir"])]["total_price"].sum():,.2f}</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="stat-card" style="border-left-color:#6366f1;"><span class="stat-title">Kayıtlı Bayiler</span><span class="stat-val">{d_count}</span></div>', unsafe_allow_html=True)
            st.markdown("---")

            # --- 2. GRAFİK VE LİDERLİK TABLOSU ---
            col_chart, col_leader = st.columns([2, 1])
            
            with col_chart:
                st.subheader("📈 Bayi Bazlı Satış Performansı")
                df_sales = df_offers[df_offers["status"].isin(["Onaylandı", "Siparişe Çevir"])]
                if not df_sales.empty:
                    sales_by_dealer = df_sales.groupby('Bayi')['total_price'].sum().reset_index()
                    st.bar_chart(sales_by_dealer.set_index('Bayi'), color="#10b981")
                else:
                    st.info("Henüz 'Siparişe Çevir' durumunda olan bir satış bulunmuyor.")

            with col_leader:
                st.subheader("🏆 Bayi Liderlik Tablosu")
                leaderboard = df_offers.groupby('Bayi').agg(Toplam_Teklif=('id', 'count'), Toplam_Hacim=('total_price', 'sum')).reset_index().sort_values(by='Toplam_Hacim', ascending=False)
                leaderboard['Toplam_Hacim'] = leaderboard['Toplam_Hacim'].apply(lambda x: f"{x:,.2f}")
                st.dataframe(leaderboard, use_container_width=True, hide_index=True)

            st.markdown("---")

            # --- 3. FİLTRELENEBİLİR SON TEKLİFLER LİSTESİ ---
            st.subheader("🔄 Teklif Listesi ve Durum Yönetimi")
            
            f_col1, f_col2 = st.columns(2)
            bayi_filtresi = f_col1.selectbox("Bayiye Göre Filtrele", ["Tümü"] + list(df_offers['Bayi'].unique()))
            durum_filtresi = f_col2.selectbox("Duruma Göre Filtrele", ["Tümü", "Beklemede", "Siparişe Çevir", "Reddedildi"])

            filtered_df = df_offers.copy()
            if bayi_filtresi != "Tümü": filtered_df = filtered_df[filtered_df['Bayi'] == bayi_filtresi]
            if durum_filtresi != "Tümü": filtered_df = filtered_df[filtered_df['status'] == durum_filtresi]
            filtered_df = filtered_df.sort_values(by='id', ascending=False)

            if filtered_df.empty:
                st.warning("Bu kriterlere uygun teklif bulunamadı.")
            else:
                for _, row in filtered_df.iterrows():
                    oid = row['id']
                    stat = row['status']
                    
                    try:
                        conn_s = sqlite3.connect('sales_data.db')
                        cust_name = conn_s.execute("SELECT company_name FROM customers WHERE id=?", (row['customer_id'],)).fetchone()[0]
                        conn_s.close()
                    except: cust_name = "Bilinmeyen Müşteri"

                    try:
                        conn_f = sqlite3.connect('factory_data.db')
                        m_name = conn_f.execute("SELECT name FROM models WHERE id=?", (row['model_id'],)).fetchone()[0]
                        conn_f.close()
                    except: m_name = "Bilinmeyen Model"

                    with st.container(border=True):
                        ca, cb, cc = st.columns([3, 1, 1], vertical_alignment="center")
                        ca.markdown(f"**{cust_name}** (Bayi: <span style='color:#2563eb;'>{row['Bayi']}</span>)<br><small>{m_name} | {row['total_price']:,.2f}</small>", unsafe_allow_html=True)
                        
                        new_stat = cb.selectbox("Durum", ["Beklemede", "Siparişe Çevir", "Reddedildi"], index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(stat if stat in ["Beklemede", "Siparişe Çevir", "Reddedildi"] else "Beklemede"), key=f"stat_{oid}", label_visibility="collapsed")
                        
                        if cc.button("Güncelle", key=f"btn_{oid}", use_container_width=True):
                            conn = sqlite3.connect('sales_data.db')
                            conn.execute("UPDATE offers SET status=? WHERE id=?", (new_stat, oid))
                            conn.commit(); conn.close()
                            st.toast(f"Teklif #{oid} başarıyla güncellendi!"); st.rerun()
        else:
            st.info("Sistemde henüz kayıtlı bir teklif bulunmuyor.")

    else:
        # --- BAYİ ÖZEL DASHBOARD ---
        conn = sqlite3.connect('sales_data.db')
        offers_raw = conn.execute("SELECT total_price, status FROM offers WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        conn.close()
        df_dash = pd.DataFrame(offers_raw, columns=["Tutar", "Durum"])
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="stat-card"><span class="stat-title">Toplam Hacmim</span><span class="stat-val">{df_dash["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Bekleyen Tekliflerim</span><span class="stat-val">{df_dash[df_dash["Durum"]=="Beklemede"]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Satışa Dönen (Siparişler)</span><span class="stat-val">{df_dash[df_dash["Durum"].isin(["Onaylandı", "Siparişe Çevir"])]["Tutar"].sum():,.2f}</span></div>', unsafe_allow_html=True)
        
        st.info("💡 Sol menüden 'Yeni Teklif Hazırla' diyerek müşterilerinize teklif sunmaya başlayabilirsiniz.")

# =====================================================================
# GEÇMİŞ TEKLİFLER VE PROFİL AYARLARI
# =====================================================================
elif st.session_state.active_tab == "📋 Geçmiş Tekliflerim":
    st.header("📋 Geçmiş Tekliflerim")
    conn = sqlite3.connect('sales_data.db')
    q = "SELECT o.id, c.company_name, o.model_id, o.offer_date, o.total_price, o.status FROM offers o JOIN customers c ON o.customer_id = c.id"
    if st.session_state.user_role != 'admin': q += f" WHERE o.user_id={st.session_state.user_id}"
    offers_raw = conn.execute(q + " ORDER BY o.id DESC").fetchall()
    conn.close()
    
    if offers_raw:
        for off in offers_raw:
            off_id, c_name, m_id, o_date, t_price, o_status = off
            status_color = "#10b981" if o_status in ["Onaylandı", "Siparişe Çevir"] else ("#ef4444" if o_status == "Reddedildi" else "#f59e0b")
            try: 
                conn_f = sqlite3.connect('factory_data.db')
                m_name = conn_f.execute("SELECT name FROM models WHERE id=?", (m_id,)).fetchone()[0]
                conn_f.close()
            except: m_name = "Bilinmeyen Model"
            
            with st.container(border=True):
                st.markdown(f"<h4 style='margin:0; color:#0f172a;'>{c_name}</h4>", unsafe_allow_html=True)
                st.markdown(f"**Model:** {m_name} | **Tarih:** {o_date} | **Durum:** <span style='color:{status_color}; font-weight:bold;'>{o_status}</span>", unsafe_allow_html=True)
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                if btn_col1.button("✏️ Düzenle", key=f"ed_{off_id}", use_container_width=True):
                    st.session_state.edit_offer_id = off_id
                    st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
                    st.rerun()
                if btn_col2.button("📄 Proforma", key=f"pr_{off_id}", use_container_width=True):
                    st.session_state.proforma_id = off_id
                    st.session_state.active_tab = "PROFORMA"
                    st.rerun()
                if btn_col3.button("🗑️ Sil", key=f"rm_{off_id}", use_container_width=True):
                    conn = sqlite3.connect('sales_data.db')
                    conn.execute("DELETE FROM offers WHERE id=?", (off_id,))
                    conn.execute("DELETE FROM offer_items WHERE offer_id=?", (off_id,))
                    conn.commit(); conn.close()
                    st.rerun()
    else: st.info("Geçmiş teklif bulunmuyor.")

elif st.session_state.active_tab == "⚙️ Profil Ayarlarım":
    st.header("⚙️ Kurumsal Profil Ayarları")
    conn = sqlite3.connect('users.db')
    u_data = conn.execute("SELECT company_name, email, phone, website, address_full, logo_path FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    conn.close()
    with st.expander("👤 Bayi / Kişisel Bilgilerim", expanded=True):
        with st.form("p_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Firma Adı", value=u_data[0] if u_data else "")
            p_web = c2.text_input("Web Sitesi", value=u_data[3] if u_data and u_data[3] else "")
            p_phone = c1.text_input("Telefon", value=u_data[2] if u_data and u_data[2] else "")
            p_adr = st.text_area("Açık Adres", value=u_data[4] if u_data and u_data[4] else "")
            up_logo = st.file_uploader("Tekliflerde Görünecek Logonuz", type=['png','jpg','jpeg'])
            if st.form_submit_button(":white_check_mark: PROFİLİ GÜNCELLE", type="primary"):
                f_logo = u_data[5] if u_data else ""
                if up_logo:
                    if not os.path.exists("images"): os.makedirs("images")
                    f_logo = f"images/logo_user_{st.session_state.user_id}.png"
                    with open(f_logo, "wb") as f: f.write(up_logo.getbuffer())
                conn = sqlite3.connect('users.db')
                conn.execute("UPDATE users SET company_name=?, website=?, phone=?, address_full=?, logo_path=? WHERE id=?", (p_name, p_web, p_phone, p_adr, f_logo, st.session_state.user_id))
                conn.commit(); conn.close()
                st.success("Profiliniz güncellendi!"); st.rerun()
                
    if st.session_state.user_role == 'admin':
        with st.expander("🚀 SİSTEM GENEL AYARLARI (Yönetici)", expanded=True):
            with st.form("sys_form"):
                new_sys_logo = st.file_uploader("Yeni Sistem Logosu Seçin", type=['png','jpg','jpeg'])
                if st.form_submit_button("SİSTEM LOGOSUNU DEĞİŞTİR"):
                    if new_sys_logo:
                        if not os.path.exists("images"): os.makedirs("images")
                        sys_path = f"images/system_logo_main.png"
                        with open(sys_path, "wb") as f: f.write(new_sys_logo.getbuffer())
                        conn = sqlite3.connect('factory_data.db')
                        conn.execute("UPDATE company_profile SET logo_path=? WHERE id=1", (sys_path,))
                        conn.commit(); conn.close()
                        st.success("Sistem logosu güncellendi!"); st.rerun()
