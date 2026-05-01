import streamlit as st
import database
import datetime
import pandas as pd
import hashlib

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine Bayi Portalı", page_icon="⚙️", layout="wide")

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_b2b_system():
    database.exec_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, password TEXT, company_name TEXT, role TEXT DEFAULT 'dealer')""")
    
    cols_cust = [c[1] for c in database.get_query("PRAGMA table_info(customers)")]
    if "user_id" not in cols_cust:
        database.exec_query("ALTER TABLE customers ADD COLUMN user_id INTEGER DEFAULT 0")
        
    cols_off = [c[1] for c in database.get_query("PRAGMA table_info(offers)")]
    if "user_id" not in cols_off:
        database.exec_query("ALTER TABLE offers ADD COLUMN user_id INTEGER DEFAULT 0")

init_b2b_system()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.user_email = ""

# --- 2. GİRİŞ VE KAYIT EKRANI ---
if not st.session_state.logged_in:
    
    st.markdown("<h2 style='text-align: center; color: #0f172a;'>🚀 ERSAN MAKİNE B2B PORTALI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔑 Bayi Girişi", "📝 Yeni Bayi Başvurusu"])
    
    with tab1:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Yönetici veya Bayi hesabınızla giriş yapın.")
            
            # YENİLİK: Boşlukları silen ve küçük harfe çeviren sistem (.strip().lower())
            login_email_raw = st.text_input("E-Posta Adresiniz")
            login_pwd_raw = st.text_input("Şifreniz", type="password")
            
            if st.button("Sisteme Giriş Yap", use_container_width=True):
                login_email = login_email_raw.strip().lower()
                login_pwd = login_pwd_raw.strip()
                
                if login_email == "admin@ersanmakina.net" and login_pwd == "20132017":
                    st.session_state.logged_in = True
                    st.session_state.user_id = 0
                    st.session_state.user_role = "admin"
                    st.session_state.user_email = "Yönetici (Sefa Bey)"
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
                        st.error("Hatalı e-posta veya şifre! Lütfen bilgilerinizi kontrol edin.")

    with tab2:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.success("Kendi müşterilerinizi yönetmek ve teklif hazırlamak için kayıt olun.")
            new_email_raw = st.text_input("Kurumsal E-Posta Adresi")
            new_comp = st.text_input("Bayi / Firma Adı")
            new_pwd_raw = st.text_input("Sistem Şifresi Belirleyin", type="password")
            
            if st.button("Kayıt Ol ve Hemen Başla", use_container_width=True):
                new_email = new_email_raw.strip().lower()
                new_pwd = new_pwd_raw.strip()
                
                if new_email and new_pwd and new_comp:
                    try:
                        database.exec_query("INSERT INTO users (email, password, company_name) VALUES (?,?,?)",
                                           (new_email, hash_password(new_pwd), new_comp))
                        st.balloons()
                        st.success("Kayıt başarılı! Şimdi 'Bayi Girişi' sekmesinden sisteme girebilirsiniz.")
                    except:
                        st.error("Bu e-posta adresi zaten sistemde kayıtlı!")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")
    st.stop()

# --- 3. ANA PANEL ---
with st.sidebar:
    st.image("https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png", use_container_width=True)
    st.markdown(f"<div style='text-align:center; padding:10px; background:#1e293b; color:white; border-radius:5px; margin-bottom:15px;'>👤 {st.session_state.user_email}</div>", unsafe_allow_html=True)
    
    menu_items = ["🏠 Dashboard", "📄 Yeni Teklif Hazırla", "👥 Müşterilerim"]
    
    if st.session_state.user_role == "admin":
        menu_items.extend(["🏢 Bayi Yönetimi", "📋 Tüm Teklifler (Genel)", "📦 Modelleri Yönet"])
    else:
        menu_items.append("📋 Geçmiş Tekliflerim")
        
    menu = st.radio("MENÜ", menu_items)
    st.markdown("---")
    
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_role = None
        st.session_state.user_email = ""
        st.rerun()

# --- 4. SAYFA İÇERİKLERİ ---
if menu == "🏠 Dashboard":
    st.header("Sistem Özeti")
    u_id = st.session_state.user_id
    
    if st.session_state.user_role == "admin":
        c_count = database.get_query("SELECT COUNT(*) FROM customers")[0][0]
        off_count = database.get_query("SELECT COUNT(*) FROM offers")[0][0]
        u_count = database.get_query("SELECT COUNT(*) FROM users")[0][0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Bayi", u_count)
        col2.metric("Sistemdeki Toplam Müşteri", c_count)
        col3.metric("Kesilen Toplam Teklif", off_count)
    else:
        c_count = database.get_query("SELECT COUNT(*) FROM customers WHERE user_id=?", (u_id,))[0][0]
        off_count = database.get_query("SELECT COUNT(*) FROM offers WHERE user_id=?", (u_id,))[0][0]
        col1, col2 = st.columns(2)
        col1.metric("Kayıtlı Müşterilerim", c_count)
        col2.metric("Verdiğim Teklifler", off_count)

elif menu == "👥 Müşterilerim":
    st.header("Müşteri Yönetimi")
    with st.expander("➕ Yeni Müşteri Ekle", expanded=True):
        c_name = st.text_input("Firma Adı")
        col1, col2 = st.columns(2)
        with col1:
            c_phone = st.text_input("Telefon")
        with col2:
            c_email = st.text_input("E-Posta")
            
        if st.button("💾 Müşteriyi Kaydet", use_container_width=True):
            if c_name:
                database.exec_query("INSERT INTO customers (company_name, phone, email, user_id) VALUES (?,?,?,?)", 
                                   (c_name, c_phone, c_email, st.session_state.user_id))
                st.success(f"{c_name} müşteri listenize eklendi.")
            else:
                st.warning("Firma Adı zorunludur.")
    
    st.subheader("Kayıtlı Müşterileriniz")
    my_customers = database.get_query("SELECT company_name, phone, email FROM customers WHERE user_id=?", (st.session_state.user_id,))
    if my_customers:
        st.dataframe(pd.DataFrame(my_customers, columns=["Firma Adı", "Telefon", "E-Posta"]), use_container_width=True)
    else:
        st.info("Henüz müşteri kaydınız bulunmuyor.")

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
            st.error("Sistemde henüz makine modeli bulunmuyor. Yönetici eklemelidir.")
        else:
            selected_model = st.selectbox("Makine Seçin", [m[1] for m in model_data])
            m_info = [m for m in model_data if m[1] == selected_model][0]
            price = m_info[2]
            currency = m_info[3]
            
            discount = st.number_input("İskonto Oranı (%)", 0.0, 100.0, 0.0)
            final_price = price * (1 - (discount/100))
            
            st.markdown(f"""
                <div style="background:#0f172a; color:white; padding:20px; border-radius:10px; text-align:center; margin-top:15px;">
                    <p style="margin:0; opacity:0.8; font-size:14px;">Hesaplanan Net Tutar</p>
                    <h2 style="margin:0; color:#10b981;">{final_price:,.2f} {currency}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("💾 Teklifi Onayla ve Kaydet", use_container_width=True):
                database.exec_query("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date) VALUES (?,?,?,?,?)",
                                   (selected_cust_id, m_info[0], final_price, st.session_state.user_id, datetime.date.today().isoformat()))
                st.balloons()
                st.success("Teklifiniz başarıyla sisteme kaydedildi.")

elif menu == "📋 Geçmiş Tekliflerim":
    st.header("📋 Geçmiş Tekliflerim")
    my_offers = database.get_query("""
        SELECT o.offer_date, c.company_name, m.name, o.total_price 
        FROM offers o 
        JOIN customers c ON o.customer_id = c.id 
        LEFT JOIN models m ON o.model_id = m.id
        WHERE o.user_id = ? ORDER BY o.id DESC""", (st.session_state.user_id,))
    
    if my_offers:
        st.dataframe(pd.DataFrame(my_offers, columns=["Tarih", "Müşteri", "Model", "Tutar"]), use_container_width=True)
    else:
        st.info("Henüz oluşturduğunuz bir teklif bulunmuyor.")

elif menu == "🏢 Bayi Yönetimi":
    st.header("🏢 Bayi Listesi")
    dealers = database.get_query("SELECT id, company_name, email FROM users WHERE role='dealer'")
    if dealers:
        st.dataframe(pd.DataFrame(dealers, columns=["ID", "Bayi / Firma Adı", "E-Posta"]), use_container_width=True)
    else:
        st.info("Henüz kayıtlı bayi yok.")

elif menu == "📋 Tüm Teklifler (Genel)":
    st.header("Tüm Bayilerin Teklifleri")
    all_offers = database.get_query("""
        SELECT u.company_name as Dealer, c.company_name as Customer, o.total_price, o.offer_date 
        FROM offers o 
        JOIN users u ON o.user_id = u.id 
        JOIN customers c ON o.customer_id = c.id
        ORDER BY o.id DESC""")
    if all_offers:
        st.dataframe(pd.DataFrame(all_offers, columns=["Bayi", "Müşteri", "Tutar", "Tarih"]), use_container_width=True)
    else:
        st.info("Sistemde hiç teklif bulunmuyor.")
        
elif menu == "📦 Modelleri Yönet":
    st.header("📦 Modelleri Yönet")
    st.info("Masaüstü uygulamanızdan modelleri ekleyebilirsiniz. Veritabanınız senkronize oldukça bayileriniz burada anında görecektir.")
    models = database.get_query("SELECT name, category, base_price, currency FROM models")
    if models:
        st.dataframe(pd.DataFrame(models, columns=["Model Adı", "Kategori", "Taban Fiyat", "Birim"]), use_container_width=True)
