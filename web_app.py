import streamlit as st
import database
import datetime
import os

# --- 1. SİSTEM AYARLARI VE OTURUM YÖNETİMİ ---
st.set_page_config(page_title="Ersan Makine ERP", page_icon="⚙️", layout="wide")

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# --- 2. GÖRSEL TASARIM (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0f172a; }
    .stat-card {
        background: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.title("🚀 ERSAN MAKİNE")
    st.caption("Bulut Yönetim Sistemi")
    st.markdown("---")
    
    # Menü Seçenekleri
    menu_options = ["🏠 Genel Bakış", "📄 Yeni Teklif Hazırla"]
    
    # Yönetici Girişi Yapılmışsa Ek Menüleri Göster
    if st.session_state.admin_logged_in:
        menu_options.extend(["👥 Müşteri Tanımlama", "📦 Ürün Portföyü", "📋 Geçmiş Teklifler"])
    
    menu = st.radio("Menü", menu_options)
    
    st.markdown("---")
    
    # YÖNETİCİ GİRİŞİ BUTONU
    if not st.session_state.admin_logged_in:
        with st.expander("🔐 Yönetici Girişi"):
            password = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap"):
                if password == "20132017":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı Şifre!")
    else:
        if st.button("🔓 Çıkış Yap"):
            st.session_state.admin_logged_in = False
            st.rerun()

# --- 4. SAYFA İÇERİKLERİ ---

# A. GENEL BAKIŞ
if menu == "🏠 Genel Bakış":
    st.title("Sistem Özeti")
    c_count = database.get_query("SELECT COUNT(*) FROM customers")[0][0]
    m_count = database.get_query("SELECT COUNT(*) FROM models")[0][0]
    off_count = database.get_query("SELECT COUNT(*) FROM offers")[0][0]
    
    col1, col2, col3 = st.columns(3)
    col1.markdown(f'<div class="stat-card"><b>Müşteriler</b><br><span style="font-size:25px;">{c_count}</span></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><b>Modeller</b><br><span style="font-size:25px;">{m_count}</span></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><b>Teklifler</b><br><span style="font-size:25px;">{off_count}</span></div>', unsafe_allow_html=True)

# B. MÜŞTERİ TANIMLAMA (Yöneticiye Özel)
elif menu == "👥 Müşteri Tanımlama":
    st.title("👥 Yeni Müşteri Tanımlama")
    with st.form("customer_form"):
        c_name = st.text_input("Firma Adı")
        c_phone = st.text_input("Telefon")
        c_email = st.text_input("E-posta")
        c_tax_off = st.text_input("Vergi Dairesi")
        c_tax_no = st.text_input("Vergi Numarası")
        c_address = st.text_area("Adres")
        
        if st.form_submit_button("💾 Müşteriyi Kaydet"):
            if c_name:
                database.exec_query(
                    "INSERT INTO customers (company_name, phone, email, tax_office, tax_no, address) VALUES (?,?,?,?,?,?)",
                    (c_name, c_phone, c_email, c_tax_off, c_tax_no, c_address)
                )
                st.success(f"{c_name} başarıyla sisteme eklendi!")
            else:
                st.error("Firma adı boş bırakılamaz!")

# C. ÜRÜN PORTFÖYÜ (Yöneticiye Özel)
elif menu == "📦 Ürün Portföyü":
    st.title("📦 Ürün Portföyü ve Modeller")
    models = database.get_query("SELECT name, category, base_price, currency FROM models")
    if models:
        import pandas as pd
        df = pd.DataFrame(models, columns=["Model Adı", "Kategori", "Fiyat", "Para Birimi"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Henüz model eklenmemiş.")

# D. YENİ TEKLİF HAZIRLA
elif menu == "📄 Yeni Teklif Hazırla":
    st.title("📄 Yeni Teklif Hazırlama")
    # Müşteri Listesi
    cust_data = database.get_query("SELECT id, company_name FROM customers")
    if not cust_data:
        st.warning("Önce 'Müşteri Tanımlama' menüsünden müşteri eklemelisiniz!")
    else:
        customers = {c[1]: c[0] for c in cust_data}
        selected_cust = st.selectbox("Müşteri Seçin", list(customers.keys()))
        
        # Model Listesi
        model_data = database.get_query("SELECT id, name, base_price, currency FROM models")
        models = {m[1]: m for m in model_data}
        selected_model = st.selectbox("Makine Seçin", list(models.keys()))
        
        if selected_model:
            m_price = models[selected_model][2]
            m_curr = models[selected_model][3]
            st.info(f"Seçilen Makine Taban Fiyatı: {m_price:,.2f} {m_curr}")
            
            discount = st.number_input("İskonto (%)", 0.0, 100.0, 0.0)
            final = m_price * (1 - (discount/100))
            st.success(f"Teklif Tutarı: {final:,.2f} {m_curr}")
            
            if st.button("Teklifi Onayla ve Kaydet"):
                st.balloons()
                st.success("Teklif kaydedildi!")

# E. GEÇMİŞ TEKLİFLER
elif menu == "📋 Geçmiş Teklifler":
    st.title("📋 Geçmiş Teklif Kayıtları")
    # Basit liste formatı
    offers = database.get_query("""
        SELECT o.id, c.company_name, o.total_price, o.offer_date 
        FROM offers o 
        JOIN customers c ON o.customer_id = c.id
    """)
    if offers:
        st.table(offers)
    else:
        st.write("Kayıt bulunamadı.")

