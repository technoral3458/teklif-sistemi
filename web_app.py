import streamlit as st
import database
import datetime
import pandas as pd
import hashlib

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine Bayi Portalı", page_icon="⚙️", layout="wide")

# Şifreleri güvenli tutmak için basit hash fonksiyonu
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Veritabanı Tablolarını Güncelleme (B2B Hazırlığı)
def init_b2b_system():
    # Kullanıcılar tablosu (Bayiler)
    database.exec_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer')""")
    
    # Mevcut tablolara user_id (Sahiplik) sütunu ekleme
    cols_cust = [c[1] for c in database.get_query("PRAGMA table_info(customers)")]
    if "user_id" not in cols_cust:
        database.exec_query("ALTER TABLE customers ADD COLUMN user_id INTEGER DEFAULT 0")
        
    cols_off = [c[1] for c in database.get_query("PRAGMA table_info(offers)")]
    if "user_id" not in cols_off:
        database.exec_query("ALTER TABLE offers ADD COLUMN user_id INTEGER DEFAULT 0")

init_b2b_system()

# Oturum Durumu
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.user_email = ""

# --- 2. GİRİŞ VE KAYIT EKRANI ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔑 Oturum Aç", "📝 Bayi Kaydı Oluştur"])
    
    with tab1:
        st.subheader("Bayi Girişi")
        login_email = st.text_input("E-Posta")
        login_pwd = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            # Admin kontrolü (Sizin girişiniz)
            if login_email == "admin@ersanmakina.com" and login_pwd == "20132017":
                st.session_state.logged_in = True
                st.session_state.user_id = 0
                st.session_state.user_role = "admin"
                st.rerun()
            else:
                user = database.get_query("SELECT id, role FROM users WHERE email=? AND password=?", 
                                         (login_email, hash_password(login_pwd)))
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0][0]
                    st.session_state.user_role = user[0][1]
                    st.session_state.user_email = login_email
                    st.rerun()
                else:
                    st.error("Hatalı e-posta veya şifre!")

    with tab2:
        st.subheader("Yeni Bayi Başvurusu")
        new_email = st.text_input("E-Posta Adresi (Oturum açmak için)")
        new_comp = st.text_input("Firma Adı")
        new_pwd = st.text_input("Şifre Belirleyin", type="password")
        if st.button("Kayıt Ol ve Üye Girişi Yap", use_container_width=True):
            if new_email and new_pwd:
                try:
                    database.exec_query("INSERT INTO users (email, password, company_name) VALUES (?,?,?)",
                                       (new_email, hash_password(new_pwd), new_comp))
                    st.success("Kaydınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.")
                except:
                    st.error("Bu e-posta adresi zaten kayıtlı!")
    st.stop()

# --- 3. ANA PANEL (Giriş Yapıldıktan Sonra) ---
with st.sidebar:
    st.image("https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png", use_container_width=True)
    st.write(f"👤 **Hoş Geldin:** {st.session_state.user_email}")
    st.markdown("---")
    
    menu_items = ["🏠 Dashboard", "📄 Yeni Teklif Hazırla", "👥 Müşterilerim"]
    if st.session_state.user_role == "admin":
        menu_items.extend(["🏢 Bayi Yönetimi", "📋 Tüm Teklifler", "📦 Modelleri Yönet"])
    else:
        menu_items.append("📋 Geçmiş Tekliflerim")
        
    menu = st.radio("MENÜ", menu_items)
    
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. SAYFA İÇERİKLERİ ---

# A. DASHBOARD (Bayiye Özel / Adminde Genel)
if menu == "🏠 Dashboard":
    st.header("Sistem Özeti")
    u_id = st.session_state.user_id
    
    if st.session_state.user_role == "admin":
        c_count = database.get_query("SELECT COUNT(*) FROM customers")[0][0]
        off_count = database.get_query("SELECT COUNT(*) FROM offers")[0][0]
        u_count = database.get_query("SELECT COUNT(*) FROM users")[0][0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Bayi", u_count)
        col2.metric("Toplam Müşteri", c_count)
        col3.metric("Toplam Teklif", off_count)
    else:
        c_count = database.get_query("SELECT COUNT(*) FROM customers WHERE user_id=?", (u_id,))[0][0]
        off_count = database.get_query("SELECT COUNT(*) FROM offers WHERE user_id=?", (u_id,))[0][0]
        col1, col2 = st.columns(2)
        col1.metric("Müşterilerim", c_count)
        col2.metric("Verdiğim Teklifler", off_count)

# B. MÜŞTERİ TANIMLAMA (Bayiye Özel)
elif menu == "👥 Müşterilerim":
    st.header("Müşteri Yönetimi")
    with st.expander("➕ Yeni Müşteri Ekle"):
        c_name = st.text_input("Firma Adı")
        if st.button("Kaydet"):
            database.exec_query("INSERT INTO customers (company_name, user_id) VALUES (?,?)", 
                               (c_name, st.session_state.user_id))
            st.success("Müşteri listenize eklendi.")
    
    # Sadece kendi müşterilerini gör
    my_customers = database.get_query("SELECT company_name, phone FROM customers WHERE user_id=?", (st.session_state.user_id,))
    st.table(pd.DataFrame(my_customers, columns=["Firma Adı", "Telefon"]))

# C. YENİ TEKLİF HAZIRLA (Masaüstü Mantığı)
elif menu == "📄 Yeni Teklif Hazırla":
    st.header("Teklif Hazırlama")
    my_custs = database.get_query("SELECT id, company_name FROM customers WHERE user_id=?", (st.session_state.user_id,))
    if not my_custs:
        st.warning("Teklif hazırlamak için önce müşteri eklemelisiniz.")
    else:
        selected_cust = st.selectbox("Müşteri Seçin", [c[1] for c in my_custs])
        model_data = database.get_query("SELECT id, name, base_price, currency FROM models")
        selected_model = st.selectbox("Makine Seçin", [m[1] for m in model_data])
        
        m_info = [m for m in model_data if m[1] == selected_model][0]
        price = m_info[2]
        st.metric("Birim Fiyat", f"{price:,.2f} {m_info[3]}")
        
        if st.button("Teklifi Kaydet"):
            # Teklif kaydetme (Bayi ID'si ile)
            database.exec_query("INSERT INTO offers (customer_id, total_price, user_id, offer_date) VALUES (?,?,?,?)",
                               (my_custs[0][0], price, st.session_state.user_id, datetime.date.today().isoformat()))
            st.balloons()
            st.success("Teklifiniz başarıyla kaydedildi.")

# D. GEÇMİŞ TEKLİFLERİM (Bayi Kendi Kayıtlarını Görür - Şifresiz)
elif menu == "📋 Geçmiş Tekliflerim":
    st.header("Geçmiş Tekliflerim")
    my_offers = database.get_query("""
        SELECT o.offer_date, c.company_name, o.total_price 
        FROM offers o 
        JOIN customers c ON o.customer_id = c.id 
        WHERE o.user_id = ?""", (st.session_state.user_id,))
    st.dataframe(pd.DataFrame(my_offers, columns=["Tarih", "Müşteri", "Tutar"]), use_container_width=True)

# E. ADMIN PANELİ (Sadece Sefa Bey Görür)
elif menu == "🏢 Bayi Yönetimi":
    st.header("Bayi Listesi ve Performans")
    dealers = database.get_query("SELECT id, company_name, email FROM users WHERE role='dealer'")
    st.table(pd.DataFrame(dealers, columns=["ID", "Bayi Adı", "E-Posta"]))

elif menu == "📋 Tüm Teklifler":
    st.header("Tüm Bayilerin Teklifleri")
    all_offers = database.get_query("""
        SELECT u.company_name as Dealer, c.company_name as Customer, o.total_price, o.offer_date 
        FROM offers o 
        JOIN users u ON o.user_id = u.id 
        JOIN customers c ON o.customer_id = c.id""")
    st.dataframe(pd.DataFrame(all_offers, columns=["Bayi", "Müşteri", "Tutar", "Tarih"]), use_container_width=True)
