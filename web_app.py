import streamlit as st
import database
import customer_pages
import model_management
import offer_wizard
import datetime
import pandas as pd
import hashlib
import random
import smtplib
import sqlite3
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon="⚙️", layout="wide")

# Şifreleme Fonksiyonu
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_code():
    return str(random.randint(100000, 999999))

# Gerçek E-Posta Motoru
def send_email(to_email, code, subject="Ersan Makine - Doğrulama Kodu"):
    SMTP_SERVER = "mail.ersanmakina.net"
    SMTP_PORT = 587
    SENDER_EMAIL = "sefa@ersanmakina.net"
    SENDER_PASSWORD = "Sev32881-"

    msg = MIMEMultipart()
    msg['From'] = f"Ersan Makine B2B <{SENDER_EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = subject

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #0f172a;">Ersan Makine B2B Portalı</h2>
        <p>Merhaba,</p>
        <p>Sistem üzerinden yapılan işlem için gereken güvenlik kodunuz aşağıdadır:</p>
        <div style="background-color: #f1f5f9; padding: 15px; border-left: 5px solid #3b82f6; font-size: 24px; font-weight: bold; letter-spacing: 5px;">
            {code}
        </div>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <small style="color: #999;">Ersan Makine San. ve Tic. Ltd. Şti.</small>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail gönderilemedi. Hata: {e}")
        return False

# =====================================================================
# YENİ ÖZELLİK: BAĞIMSIZ "users.db" VERİTABANI YÖNETİMİ
# =====================================================================
def exec_user_query(query, params=()):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res

def init_advanced_b2b():
    # 1. Tamamen Bağımsız Kullanıcı Veritabanı Kurulumu (users.db)
    exec_user_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, password TEXT, company_name TEXT, 
        role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0,
        user_type TEXT DEFAULT 'Satıcı', phone TEXT, 
        is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT)""")
        
    # Yönetici (Sefa Bey) hesabını users.db içine kalıcı olarak yazıyoruz
    admin_check = get_user_query("SELECT id FROM users WHERE email='admin@ersanmakina.net'")
    if not admin_check:
        exec_user_query("""INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) 
                           VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')""", 
                        ("admin@ersanmakina.net", hash_password("20132017")))

    # 2. Mevcut Ana Veritabanı (database.db) Eksik Sütun Kontrolleri
    database.exec_query("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")

init_advanced_b2b()

# --- 2. OTURUM DURUM YÖNETİMİ VE "SAYFAYI YENİLE" (F5) KORUMASI ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "user_email" not in st.session_state: st.session_state.user_email = ""

if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1
if "temp_email" not in st.session_state: st.session_state.temp_email = ""

# Sayfa yenilendiğinde (F5) URL'deki Token'ı kontrol edip otomatik giriş yapma sistemi
if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        valid_user = get_user_query("SELECT id, user_type, is_approved, is_verified, role, email FROM users WHERE session_token=?", (current_token,))
        if valid_user:
            u_id, u_type, is_approved, is_verified, u_role, u_email = valid_user[0]
            st.session_state.logged_in = True
            st.session_state.user_id = u_id
            st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")
            st.session_state.user_email = u_email

# --- 3. CSS TASARIMI ---
st.markdown("""
    <style>
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 32px; font-weight: 900; color: #1e293b; display: block; }
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 13px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. GİRİŞ, KAYIT VE ŞİFREMİ UNUTTUM EKRANI ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: #0f172a;'>🚀 ERSAN MAKİNE B2B PORTALI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    tab_login, tab_register, tab_forgot = st.tabs(["🔑 Sisteme Giriş", "📝 Yeni Üyelik", "❓ Şifremi Unuttum"])
    
    with tab_login:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            login_email = st.text_input("E-Posta Adresi").strip().lower()
            login_pwd = st.text_input("Şifre", type="password").strip()
            
            if st.button("Giriş Yap", use_container_width=True):
                # Artık Admin dahil herkes users.db'den doğrulanıyor
                user = get_user_query("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", 
                                         (login_email, hash_password(login_pwd)))
                if user:
                    u_id, u_type, is_approved, is_verified, u_role = user[0]
                    if is_verified == 0:
                        st.warning("⚠️ E-posta adresiniz doğrulanmamış! Lütfen önce kaydınızı tamamlayın.")
                    elif is_approved == 0:
                        st.warning("⏳ Hesabınız sistem yöneticisinin onayını bekliyor.")
                    else:
                        # Oturum Başarılı -> F5 Koruması İçin Token Oluştur
                        new_token = str(uuid.uuid4())
                        exec_user_query("UPDATE users SET session_token=? WHERE id=?", (new_token, u_id))
                        st.query_params["session_token"] = new_token # Tarayıcı URL'ine kaydet
                        
                        st.session_state.logged_in = True
                        st.session_state.user_id = u_id
                        st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")
                        st.session_state.user_email = login_email
                        st.rerun()
                else:
                    st.error("Hatalı e-posta veya şifre!")

    with tab_register:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.session_state.reg_step == 1:
                st.info("Zorunlu şirket bilgilerini giriniz.")
                reg_type = st.selectbox("Faaliyet Türünüz *", ["Satıcı (Bayi)", "Üretici"])
                reg_comp = st.text_input("Firma Tam Ünvanı *")
                reg_phone = st.text_input("Firma İletişim Numarası *")
                reg_email = st.text_input("Kurumsal E-Posta *").strip().lower()
                reg_pwd = st.text_input("Sistem Şifresi Belirleyin *", type="password").strip()
                
                if st.button("Kayıt Ol ve E-Posta Doğrula", use_container_width=True):
                    if all([reg_comp, reg_phone, reg_email, reg_pwd]):
                        check_mail = get_user_query("SELECT id FROM users WHERE email=?", (reg_email,))
                        if check_mail:
                            st.error("Bu e-posta adresi zaten kayıtlı!")
                        else:
                            ver_code = generate_code()
                            # YENİ: Artık kayıtlar users.db dosyasına yapılıyor!
                            exec_user_query(
                                "INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)",
                                (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code)
                            )
                            if send_email(reg_email, ver_code, "Üyelik Doğrulama Kodu"):
                                st.session_state.temp_email = reg_email
                                st.session_state.reg_step = 2
                                st.rerun()
                    else:
                        st.warning("Lütfen (*) ile işaretli tüm zorunlu alanları doldurun.")
            
            elif st.session_state.reg_step == 2:
                st.success(f"{st.session_state.temp_email} adresine 6 haneli bir kod gönderdik.")
                entered_code = st.text_input("Doğrulama Kodunu Giriniz", max_chars=6)
                if st.button("Kodu Onayla", use_container_width=True):
                    db_code = get_user_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                    if db_code and db_code[0][0] == entered_code:
                        exec_user_query("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                        st.session_state.reg_step = 1
                        st.balloons()
                        st.success("Tebrikler! E-postanız doğrulandı. Yöneticinin onayından sonra giriş yapabilirsiniz.")
                    else:
                        st.error("Hatalı kod girdiniz.")

    with tab_forgot:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.session_state.forgot_step == 1:
                f_email = st.text_input("Sisteme kayıtlı E-Posta Adresiniz").strip().lower()
                if st.button("Şifre Sıfırlama Kodu Gönder", use_container_width=True):
                    if f_email:
                        user_exists = get_user_query("SELECT id FROM users WHERE email=?", (f_email,))
                        if user_exists:
                            reset_code = generate_code()
                            exec_user_query("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            if send_email(f_email, reset_code, "Şifre Sıfırlama Kodu"):
                                st.session_state.temp_email = f_email
                                st.session_state.forgot_step = 2
                                st.rerun()
                        else:
                            st.error("Sistemde böyle bir e-posta bulunamadı.")
            
            elif st.session_state.forgot_step == 2:
                st.info(f"{st.session_state.temp_email} adresine sıfırlama kodu gönderildi.")
                f_code = st.text_input("6 Haneli Sıfırlama Kodu", max_chars=6)
                new_pwd = st.text_input("Yeni Şifreniz", type="password")
                
                if st.button("Şifremi Değiştir", use_container_width=True):
                    valid_code = get_user_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                    if valid_code and valid_code[0][0] == f_code and len(new_pwd) > 0:
                        exec_user_query("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(new_pwd), st.session_state.temp_email))
                        st.session_state.forgot_step = 1
                        st.success("Şifreniz başarıyla değiştirildi! Giriş sekmesinden hesabınıza erişebilirsiniz.")
                    else:
                        st.error("Hatalı kod veya boş şifre!")

    st.stop()

# --- 5. ANA PANEL VE YAN MENÜ ---
with st.sidebar:
    st.image("https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png")
    
    role_text = "Yönetici" if st.session_state.user_role == "admin" else ("Satıcı Bayi" if st.session_state.user_role == "dealer" else "Üretici Firma")
    st.markdown(f"<div style='text-align:center; padding:10px; background:#1e293b; color:white; border-radius:5px; margin-bottom:15px;'>👤 {st.session_state.user_email}<br><small style='color:#cbd5e1;'>[{role_text}]</small></div>", unsafe_allow_html=True)
    
    menu_items = ["🏠 Dashboard"]
    
    if st.session_state.user_role == "admin":
        menu_items.extend(["🏢 Bayi / Üretici Yönetimi", "📋 Tüm Teklifler", "📦 Tüm Modelleri Yönet", "👥 Müşterilerim"])
    elif st.session_state.user_role == "dealer":
        menu_items.extend(["📄 Yeni Teklif Hazırla", "👥 Müşterilerim", "📋 Geçmiş Tekliflerim"])
    elif st.session_state.user_role == "manufacturer":
        menu_items.extend(["📖 Ürün Kataloğu (Teknik)"])
        
    menu = st.radio("MENÜ", menu_items)
    st.markdown("---")
    
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        # Çıkış yapıldığında veritabanından ve URL'den token'ı sil
        if st.session_state.user_id:
            exec_user_query("UPDATE users SET session_token=NULL WHERE id=?", (st.session_state.user_id,))
        st.query_params.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 6. SAYFA İÇERİKLERİ ---

if menu == "🏠 Dashboard":
    st.header("Sistem Özeti")
    if st.session_state.user_role == "admin":
        u_count = get_user_query("SELECT COUNT(*) FROM users WHERE is_approved=1 AND role!='admin'")[0][0]
        c_count = database.get_query("SELECT COUNT(*) FROM customers")[0][0]
        o_count = database.get_query("SELECT COUNT(*) FROM offers")[0][0]
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="stat-card"><span class="stat-title">Onaylı Üyeler</span><span class="stat-val">{u_count}</span></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Sistemdeki Müşteriler</span><span class="stat-val">{c_count}</span></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Kesilen Teklifler</span><span class="stat-val">{o_count}</span></div>', unsafe_allow_html=True)
    
    elif st.session_state.user_role == "dealer":
        c_count = database.get_query("SELECT COUNT(*) FROM customers WHERE user_id=?", (st.session_state.user_id,))[0][0]
        o_count = database.get_query("SELECT COUNT(*) FROM offers WHERE user_id=?", (st.session_state.user_id,))[0][0]
        col1, col2 = st.columns(2)
        col1.markdown(f'<div class="stat-card"><span class="stat-title">Kayıtlı Müşterilerim</span><span class="stat-val">{c_count}</span></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Verdiğim Teklifler</span><span class="stat-val">{o_count}</span></div>', unsafe_allow_html=True)
    
    elif st.session_state.user_role == "manufacturer":
        m_count = database.get_query("SELECT COUNT(*) FROM models")[0][0]
        st.markdown(f'<div class="stat-card"><span class="stat-title">Ersan Makine Ürün Gamı (Adet)</span><span class="stat-val">{m_count}</span></div>', unsafe_allow_html=True)
        st.info("Üretici girişi yaptığınız için fiyatlandırma ve müşteri teklif sistemleri gizlenmiştir. Sol menüden makinelerin teknik dokümanlarını inceleyebilirsiniz.")

elif menu == "👥 Müşterilerim":
    is_admin = (st.session_state.user_role == "admin")
    customer_pages.show_customer_management(st.session_state.user_id, is_admin)

elif menu == "📦 Tüm Modelleri Yönet":
    model_management.show_product_management()

elif menu == "📄 Yeni Teklif Hazırla":
    is_admin = (st.session_state.user_role == "admin")
    offer_wizard.show_offer_wizard(st.session_state.user_id, is_admin)

elif menu == "📋 Geçmiş Tekliflerim":
    st.header("📋 Geçmiş Tekliflerim")
    my_offers = database.get_query("""
        SELECT o.offer_date, c.company_name, m.name, o.total_price 
        FROM offers o JOIN customers c ON o.customer_id = c.id LEFT JOIN models m ON o.model_id = m.id
        WHERE o.user_id = ? ORDER BY o.id DESC""", (st.session_state.user_id,))
    if my_offers: 
        st.dataframe(pd.DataFrame(my_offers, columns=["Tarih", "Müşteri", "Model", "Tutar"]), use_container_width=True)
    else:
        st.info("Henüz oluşturduğunuz bir teklif bulunmuyor.")

elif menu == "📖 Ürün Kataloğu (Teknik)":
    st.header("📖 Makine Teknik Kataloğu")
    st.info("Makinelerin sadece donanım ve teknik özellikleri gösterilmektedir. Fiyat bilgisi yetkiniz dışındadır.")
    models = database.get_query("SELECT name, category, specs FROM models")
    if models:
        st.dataframe(pd.DataFrame(models, columns=["Makine Modeli", "Kategori", "Teknik Özellikler"]), use_container_width=True)
    else:
        st.write("Sistemde kayıtlı makine yok.")

elif menu == "🏢 Bayi / Üretici Yönetimi":
    st.header("🏢 Üyelik Onay ve Yönetim Sistemi")
    
    st.subheader("⏳ E-Postasını Doğrulamış, Onay Bekleyenler")
    # Artık users.db'den okuyor
    pending = get_user_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=0 AND is_verified=1 AND role!='admin'")
    if pending:
        for p_id, p_name, p_type, p_email, p_phone in pending:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**Firma:** {p_name} ({p_type}) | **Tel:** {p_phone} | **E-Posta:** {p_email}")
                with col2:
                    if st.button("✅ Sistemi Aç", key=f"app_{p_id}", use_container_width=True):
                        exec_user_query("UPDATE users SET is_approved=1 WHERE id=?", (p_id,))
                        st.rerun()
    else:
        st.info("Şu an onay bekleyen başvuru yok.")
        
    st.markdown("---")
    st.subheader("✅ Aktif Sistem Üyeleri")
    active = get_user_query("SELECT company_name, user_type, email, phone FROM users WHERE is_approved=1 AND role!='admin'")
    if active:
        st.dataframe(pd.DataFrame(active, columns=["Firma Adı", "Tür", "E-Posta", "Telefon"]), use_container_width=True)

elif menu == "📋 Tüm Teklifler":
    st.header("Sistemdeki Tüm Teklifler")
    
    # Raporlama için database.db (teklifler) ve users.db'yi (bayi adları) eşleştiriyoruz
    all_offers = database.get_query("""
        SELECT o.user_id, c.company_name, o.total_price, o.offer_date 
        FROM offers o JOIN customers c ON o.customer_id = c.id ORDER BY o.id DESC""")
        
    if all_offers: 
        # Bayi isimlerini users.db'den çek
        final_list = []
        for o_user_id, c_name, t_price, o_date in all_offers:
            u_info = get_user_query("SELECT company_name FROM users WHERE id=?", (o_user_id,))
            dealer_name = u_info[0][0] if u_info else "Bilinmeyen Bayi"
            final_list.append([dealer_name, c_name, t_price, o_date])
            
        st.dataframe(pd.DataFrame(final_list, columns=["Bayi", "Müşteri", "Tutar", "Tarih"]), use_container_width=True)
    else:
        st.info("Sistemde hiç teklif bulunmuyor.")
