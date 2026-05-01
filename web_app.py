import streamlit as st
import database
import customer_pages
import model_management
import datetime
import pandas as pd
import hashlib
import random

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon="⚙️", layout="wide")

# Şifreleme Fonksiyonu (SHA-256)
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Rastgele 6 Haneli Kod Üretici
def generate_code():
    return str(random.randint(100000, 999999))

# E-posta Gönderme Simülasyonu
def send_email(to_email, code, subject="Doğrulama Kodu"):
    st.info(f"📧 **[SİSTEM MESAJI]** Normalde '{to_email}' adresine gidecek olan {subject}: **{code}**")
    return True

# Veritabanı Tabloları ve Yeni Sütunlar
def init_advanced_b2b():
    database.exec_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, password TEXT, company_name TEXT, 
        role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0)""")
    
    try:
        cols = [c[1] for c in database.get_query("PRAGMA table_info(users)")]
        if "user_type" not in cols: database.exec_query("ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT 'Satıcı'")
        if "phone" not in cols: database.exec_query("ALTER TABLE users ADD COLUMN phone TEXT")
        if "is_verified" not in cols: database.exec_query("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        if "auth_code" not in cols: database.exec_query("ALTER TABLE users ADD COLUMN auth_code TEXT")
        
        # Admin hesabını garantile
        database.exec_query("UPDATE users SET is_approved=1, is_verified=1 WHERE role='admin'")
    except: pass

init_advanced_b2b()

# --- 2. OTURUM DURUM YÖNETİMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "user_email" not in st.session_state: st.session_state.user_email = ""

if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1
if "temp_email" not in st.session_state: st.session_state.temp_email = ""

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
    
    # --- GİRİŞ YAP ---
    with tab_login:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            login_email = st.text_input("E-Posta Adresi").strip().lower()
            login_pwd = st.text_input("Şifre", type="password").strip()
            
            if st.button("Giriş Yap", use_container_width=True):
                if login_email == "admin@ersanmakina.net" and login_pwd == "20132017":
                    st.session_state.logged_in, st.session_state.user_id, st.session_state.user_role = True, 0, "admin"
                    st.session_state.user_email = "Yönetici (Sefa Bey)"
                    st.rerun()
                else:
                    user = database.get_query("SELECT id, user_type, is_approved, is_verified FROM users WHERE email=? AND password=?", 
                                             (login_email, hash_password(login_pwd)))
                    if user:
                        u_id, u_type, is_approved, is_verified = user[0]
                        if is_verified == 0:
                            st.warning("⚠️ E-posta adresiniz doğrulanmamış! Lütfen önce kaydınızı tamamlayın.")
                        elif is_approved == 0:
                            st.warning("⏳ Hesabınız sistem yöneticisinin onayını bekliyor.")
                        else:
                            st.session_state.logged_in = True
                            st.session_state.user_id = u_id
                            st.session_state.user_role = "manufacturer" if u_type == "Üretici" else "dealer"
                            st.session_state.user_email = login_email
                            st.rerun()
                    else:
                        st.error("Hatalı e-posta veya şifre!")

    # --- YENİ ÜYELİK ---
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
                        check_mail = database.get_query("SELECT id FROM users WHERE email=?", (reg_email,))
                        if check_mail:
                            st.error("Bu e-posta adresi zaten kayıtlı!")
                        else:
                            ver_code = generate_code()
                            database.exec_query(
                                "INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)",
                                (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code)
                            )
                            send_email(reg_email, ver_code, "Üyelik Doğrulama Kodu")
                            st.session_state.temp_email = reg_email
                            st.session_state.reg_step = 2
                            st.rerun()
                    else:
                        st.warning("Lütfen (*) ile işaretli tüm zorunlu alanları doldurun.")
            
            elif st.session_state.reg_step == 2:
                st.success(f"{st.session_state.temp_email} adresine 6 haneli bir kod gönderdik.")
                entered_code = st.text_input("Doğrulama Kodunu Giriniz", max_chars=6)
                if st.button("Kodu Onayla", use_container_width=True):
                    db_code = database.get_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                    if db_code and db_code[0][0] == entered_code:
                        database.exec_query("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                        st.session_state.reg_step = 1
                        st.balloons()
                        st.success("Tebrikler! E-postanız doğrulandı. Yöneticinin onayından sonra giriş yapabilirsiniz.")
                    else:
                        st.error("Hatalı kod girdiniz.")

    # --- ŞİFREMİ UNUTTUM ---
    with tab_forgot:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.session_state.forgot_step == 1:
                f_email = st.text_input("Sisteme kayıtlı E-Posta Adresiniz").strip().lower()
                if st.button("Şifre Sıfırlama Kodu Gönder", use_container_width=True):
                    if f_email:
                        user_exists = database.get_query("SELECT id FROM users WHERE email=?", (f_email,))
                        if user_exists:
                            reset_code = generate_code()
                            database.exec_query("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            send_email(f_email, reset_code, "Şifre Sıfırlama Kodu")
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
                    valid_code = database.get_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                    if valid_code and valid_code[0][0] == f_code and len(new_pwd) > 0:
                        database.exec_query("UPDATE users SET password=?, auth_code=NULL WHERE email=?", (hash_password(new_pwd), st.session_state.temp_email))
                        st.session_state.forgot_step = 1
                        st.success("Şifreniz başarıyla değiştirildi! Giriş sekmesinden hesabınıza erişebilirsiniz.")
                    else:
                        st.error("Hatalı kod veya boş şifre!")

    st.stop()

# --- 5. ANA PANEL VE YAN MENÜ (ROLA GÖRE) ---
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
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 6. SAYFA İÇERİKLERİ VE YÖNLENDİRMELER ---

if menu == "🏠 Dashboard":
    st.header("Sistem Özeti")
    
    if st.session_state.user_role == "admin":
        u_count = database.get_query("SELECT COUNT(*) FROM users WHERE is_approved=1")[0][0]
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
    # MASAÜSTÜ Orijinali ile eşleştirdiğimiz model yönetim modülü çağrılıyor
    model_management.show_product_management()

elif menu == "📄 Yeni Teklif Hazırla":
    st.header("📄 Teklif Hazırlama Sihirbazı")
    my_custs = database.get_query("SELECT id, company_name FROM customers WHERE user_id=?", (st.session_state.user_id,))
    
    if not my_custs:
        st.warning("Teklif hazırlamak için önce 'Müşterilerim' sekmesinden bir müşteri eklemelisiniz.")
    else:
        selected_cust_name = st.selectbox("Müşteri Seçin", [c[1] for c in my_custs])
        selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]
        
        model_data = database.get_query("SELECT id, name, base_price, currency FROM models")
        if not model_data:
            st.error("Sistemde henüz makine modeli bulunmuyor.")
        else:
            selected_model = st.selectbox("Makine Seçin", [m[1] for m in model_data])
            m_info = [m for m in model_data if m[1] == selected_model][0]
            price, currency = m_info[2], m_info[3]
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_qty = st.number_input("Adet", min_value=1, value=1)
            with col_m2:
                discount = st.number_input("İskonto Oranı (%)", 0.0, 100.0, 0.0)
            
            final_price = (price * m_qty) * (1 - (discount/100))
            
            st.markdown(f"""
                <div style="background:#0f172a; color:white; padding:20px; border-radius:10px; text-align:center; margin-top:15px;">
                    <p style="margin:0; opacity:0.8;">Hesaplanan Net Tutar</p>
                    <h2 style="margin:0; color:#10b981;">{final_price:,.2f} {currency}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("💾 Teklifi Kaydet", use_container_width=True):
                database.exec_query("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date) VALUES (?,?,?,?,?)",
                                   (selected_cust_id, m_info[0], final_price, st.session_state.user_id, datetime.date.today().isoformat()))
                st.balloons()
                st.success("Teklif kaydedildi.")

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
    pending = database.get_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=0 AND is_verified=1")
    if pending:
        for p_id, p_name, p_type, p_email, p_phone in pending:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**Firma:** {p_name} ({p_type}) | **Tel:** {p_phone} | **E-Posta:** {p_email}")
                with col2:
                    if st.button("✅ Sistemi Aç", key=f"app_{p_id}", use_container_width=True):
                        database.exec_query("UPDATE users SET is_approved=1 WHERE id=?", (p_id,))
                        st.rerun()
    else:
        st.info("Şu an onay bekleyen başvuru yok.")
        
    st.markdown("---")
    st.subheader("✅ Aktif Sistem Üyeleri")
    active = database.get_query("SELECT company_name, user_type, email, phone FROM users WHERE is_approved=1 AND role!='admin'")
    if active:
        st.dataframe(pd.DataFrame(active, columns=["Firma Adı", "Tür", "E-Posta", "Telefon"]), use_container_width=True)

elif menu == "📋 Tüm Teklifler":
    st.header("Sistemdeki Tüm Teklifler")
    all_offers = database.get_query("""
        SELECT u.company_name, c.company_name, o.total_price, o.offer_date 
        FROM offers o JOIN users u ON o.user_id = u.id JOIN customers c ON o.customer_id = c.id ORDER BY o.id DESC""")
    if all_offers: 
        st.dataframe(pd.DataFrame(all_offers, columns=["Bayi", "Müşteri", "Tutar", "Tarih"]), use_container_width=True)
    else:
        st.info("Sistemde hiç teklif bulunmuyor.")
