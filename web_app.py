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
    
    st.markdown("<h2 style='text-align: center; color: #0f172a;'>🚀 ERSAN MAKİNE B2B PORTALI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔑 Bayi Girişi", "📝 Yeni Bayi Başvurusu"])
    
    with tab1:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Yönetici veya Bayi hesabınızla giriş yapın.")
            login_email = st.text_input("E-Posta Adresiniz")
            login_pwd = st.text_input("Şifreniz", type="password")
            
            if st.button("Sisteme Giriş Yap", use_container_width=True):
                # YÖNETİCİ GİRİŞİ (Sizin girişiniz - Güncellendi!)
                if login_email == "admin@ersanmakina.net" and login_pwd == "20132017":
                    st.session_state.logged_in = True
                    st.session_state.user_id = 0
                    st.session_state.user_role = "admin"
                    st.session_state.user_email = "Yönetici (Sefa Bey)"
                    st.rerun()
                else:
                    # BAYİ GİRİŞİ KONTROLÜ
                    user = database.get_query("SELECT id, role FROM users WHERE email=? AND password=?", 
                                             (login_email, hash_password(login_pwd
