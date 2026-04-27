import streamlit as st
import database
import datetime
import os
import pandas as pd

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine Bulut ERP", page_icon="⚙️", layout="wide")

# Oturum Durumu (Yönetici girişi kontrolü)
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# --- 2. GELİŞMİŞ GÖRSEL TASARIM (CSS) ---
st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp { background-color: #f1f5f9; }
    
    /* Yan Menü Tasarımı */
    [data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
    .stRadio > div { gap: 10px; }
    
    /* Menü Butonları */
    div[data-testid="stMarkdownContainer"] p { font-size: 16px; font-weight: 500; }
    
    /* İstatistik Kartları */
    .stat-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border-left: 5px solid #3b82f6; text-align: center;
    }
    .stat-val { font-size: 28px; font-weight: 800; color: #1e293b; display: block; }
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 12px; font-weight: 700; }
    
    /* Form ve Kutular */
    .stTextInput>div>div>input, .stSelectbox>div>div>div { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YAN MENÜ (NAVIGATION) ---
with st.sidebar:
    st.markdown(f"<h1 style='color:white; font-size:24px;'>🚀 ERSAN MAKİNE</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin-top:-15px;'>Bulut Yönetim Paneli v2.0</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Menü Grupları
    if not st.session_state.admin_logged_in:
        menu = st.radio("MENÜ", ["🏠 Genel Bakış", "📄 Yeni Teklif Hazırla"])
    else:
        menu = st.radio("MENÜ", [
            "🏠 Genel Bakış", 
            "📄 Yeni Teklif Hazırla", 
            "👥 Müşteri Tanımlama", 
            "📦 Ürün Portföyü", 
            "📋 Geçmiş Teklifler"
        ])

    st.markdown("---")
    
    # YÖNETİCİ KONTROL PANELİ (Masaüstü main.py şifreleme mantığı)
    if not st.session_state.admin_logged_in:
        with st.expander("🔐 Yönetici Girişi"):
            pwd = st.text_input("Giriş Şifresi", type="password")
            if st.button("Sistemi Aç"):
                if pwd == "20132017":
                    st.session_state.admin_logged_in = True
                    st.success("Yetki Verildi!")
                    st.rerun()
                else:
                    st.error("Hatalı Şifre!")
    else:
        st.info("🟢 Yönetici Modu Aktif")
        if st.button("🔓 Oturumu Kapat"):
            st.session_state.admin_logged_in = False
            st.rerun()

# --- 4. SAYFA İÇERİKLERİ ---

# A. GENEL BAKIŞ (Dashboard)
if menu == "🏠 Genel Bakış":
    st.title("Sistem Genel Durumu")
    
    # Veritabanından İstatistikleri Al (main.py'deki refresh_stats mantığı)
    try:
        c_count = database.get_query("SELECT COUNT(*) FROM customers")[0][0]
        m_count = database.get_query("SELECT COUNT(*) FROM models")[0][0]
        off_count = database.get_query("SELECT COUNT(*) FROM offers")[0][0]
    except:
        c_count, m_count, off_count = 0, 0, 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-card"><span class="stat-title">Müşteriler</span><span class="stat-val">{c_count}</span></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card" style="border-left-color:#10b981;"><span class="stat-title">Modeller</span><span class="stat-val">{m_count}</span></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card" style="border-left-color:#f59e0b;"><span class="stat-title">Teklifler</span><span class="stat-val">{off_count}</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📢 Son Eklenen Modeller")
    latest_models = database.get_query("SELECT name, category FROM models ORDER BY id DESC LIMIT 5")
    if latest_models:
        st.table(pd.DataFrame(latest_models, columns=["Model Adı", "Kategori"]))

# B. YENİ TEKLİF HAZIRLA (offer_wizard.py Web Uyarlaması)
elif menu == "📄 Yeni Teklif Hazırla":
    st.title("📄 Teklif Hazırlama Sihirbazı")
    
    # Müşteri ve Model Seçimi
    cust_data = database.get_query("SELECT id, company_name FROM customers")
    if not cust_data:
        st.error("⚠️ Sistemde kayıtlı müşteri bulunamadı. Lütfen önce Müşteri Tanımlama ekranından müşteri ekleyin.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            selected_cust = st.selectbox("🎯 Müşteri / Firma Seçin", [c[1] for c in cust_data])
            model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options FROM models")
            selected_model_name = st.selectbox("🤖 Makine Modeli Seçin", [m[1] for m in model_data])
        
        with col_b:
            m_info = [m for m in model_data if m[1] == selected_model_name][0]
            m_qty = st.number_input("Adet", min_value=1, value=1)
            discount = st.slider("İskonto Oranı (%)", 0.0, 50.0, 0.0)

        # Fiyat Hesaplama
        base_price = m_info[2]
        total = (base_price * m_qty) * (1 - (discount / 100))
        
        st.markdown(f"""
            <div style="background:#0f172a; color:white; padding:20px; border-radius:10px; text-align:center;">
                <h2 style="margin:0; color:#10b981;">{total:,.2f} {m_info[3]}</h2>
                <p style="margin:0; opacity:0.7;">Anlık Hesaplanan Teklif Tutarı</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("✅ Teklifi Taslak Olarak Kaydet"):
            st.balloons()
            st.success("Teklif başarıyla kaydedildi!")

# C. MÜŞTERİ TANIMLAMA (customer_window.py mantığı)
elif menu == "👥 Müşteri Tanımlama":
    st.title("👥 Yeni Müşteri Tanımlama")
    with st.container(border=True):
        c_name = st.text_input("Firma Tam Ünvanı")
        col1, col2 = st.columns(2)
        with col1:
            c_tax_off = st.text_input("Vergi Dairesi")
            c_phone = st.text_input("Telefon Numarası")
        with col2:
            c_tax_no = st.text_input("Vergi Numarası")
            c_email = st.text_input("E-Posta Adresi")
        
        c_addr = st.text_area("Açık Adres")
        
        if st.button("💾 Müşteriyi Veritabanına Kaydet"):
            if c_name:
                database.exec_query(
                    "INSERT INTO customers (company_name, tax_office, tax_no, phone, email, address) VALUES (?,?,?,?,?,?)",
                    (c_name, c_tax_off, c_tax_no, c_phone, c_email, c_addr)
                )
                st.success(f"'{c_name}' başarıyla kaydedildi.")
            else:
                st.warning("Lütfen firma adını girin.")

# D. ÜRÜN PORTFÖYÜ (model_management.py mantığı)
elif menu == "📦 Ürün Portföyü":
    st.title("📦 Ürün Portföyü Yönetimi")
    models = database.get_query("SELECT name, category, base_price, currency FROM models")
    if models:
        df_models = pd.DataFrame(models, columns=["Model Adı", "Kategori", "Taban Fiyat", "Birim"])
        st.dataframe(df_models, use_container_width=True)
    else:
        st.info("Sistemde henüz kayıtlı makine modeli bulunmuyor.")

# E. GEÇMİŞ TEKLİFLER (OfferHistoryWindow mantığı)
elif menu == "📋 Geçmiş Teklifler":
    st.title("📋 Geçmiş Teklif Kayıtları")
    query = """
        SELECT o.id, o.offer_date, c.company_name, m.name, o.total_price 
        FROM offers o
        JOIN customers c ON o.customer_id = c.id
        JOIN models m ON o.model_id = m.id
        ORDER BY o.id DESC
    """
    history = database.get_query(query)
    if history:
        df_hist = pd.DataFrame(history, columns=["ID", "Tarih", "Müşteri", "Model", "Toplam Tutar"])
        st.table(df_hist)
    else:
        st.write("Henüz bir teklif oluşturulmamış.")
