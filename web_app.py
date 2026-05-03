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
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine B2B Portalı", page_icon=":gear:", layout="wide")

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_code():
    return str(random.randint(100000, 999999))

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
    except: return False

# =====================================================================
# BAĞIMSIZ "users.db" VERİTABANI YÖNETİMİ
# =====================================================================
def exec_user_query(query, params=()):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res

def init_advanced_b2b():
    exec_user_query("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, password TEXT, company_name TEXT, 
        role TEXT DEFAULT 'dealer', is_approved INTEGER DEFAULT 0,
        user_type TEXT DEFAULT 'Satıcı', phone TEXT, 
        is_verified INTEGER DEFAULT 0, auth_code TEXT, session_token TEXT,
        logo_path TEXT, website TEXT, address_full TEXT)""")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "logo_path" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN logo_path TEXT")
    if "website" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN website TEXT")
    if "address_full" not in cols: cursor.execute("ALTER TABLE users ADD COLUMN address_full TEXT")
    conn.commit()
    conn.close()

    admin_check = get_user_query("SELECT id FROM users WHERE email='admin@ersanmakina.net'")
    if not admin_check:
        exec_user_query("""INSERT INTO users (email, password, company_name, role, is_approved, is_verified, user_type) 
                           VALUES (?, ?, 'Ersan Makine Merkez', 'admin', 1, 1, 'Yönetici')""", 
                        ("admin@ersanmakina.net", hash_password("20132017")))

init_advanced_b2b()

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "reg_step" not in st.session_state: st.session_state.reg_step = 1
if "forgot_step" not in st.session_state: st.session_state.forgot_step = 1

if not st.session_state.logged_in:
    current_token = st.query_params.get("session_token")
    if current_token:
        valid_user = get_user_query("SELECT id, user_type, role, email FROM users WHERE session_token=?", (current_token,))
        if valid_user:
            u_id, u_type, u_role, u_email = valid_user[0]
            st.session_state.logged_in = True
            st.session_state.user_id = u_id
            st.session_state.user_role = u_role if u_role == 'admin' else ("manufacturer" if u_type == "Üretici" else "dealer")
            st.session_state.user_email = u_email

# --- GÜÇLÜ VE MODERN CSS ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 10px 20px; font-weight: 600; color: #475569; border: 1px solid #e2e8f0; }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; border: 1px solid #2563eb; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6; text-align: center; margin-bottom: 15px;}
    .stat-val { font-size: 28px; font-weight: 900; color: #1e293b; display: block; }
    .stat-title { color: #64748b; text-transform: uppercase; font-size: 11px; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# HARİKA GİRİŞ EKRANI (LOGIN UI)
# =====================================================================
if not st.session_state.logged_in:
    
    col_left, col_main, col_right = st.columns([1, 1.2, 1])
    
    with col_main:
        st.markdown("""
            <div style='text-align: center; padding: 20px 0 10px 0;'>
                <img src="https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png" style="max-width: 220px; margin-bottom: 15px;">
                <h2 style='color: #0f172a; font-weight: 800; font-size: 24px; margin:0;'>B2B Bayi Portalı</h2>
                <p style='color: #64748b; font-size: 14px;'>Sisteme erişmek için bilgilerinizi giriniz.</p>
            </div>
        """, unsafe_allow_html=True)

        # İkonlar metin koduyla çağırıldı, Türkçe karakterler eklendi
        tab_login, tab_register, tab_forgot = st.tabs([":key: Giriş Yap", ":memo: Yeni Kayıt", ":question: Şifremi Unuttum"])
        
        with tab_login:
            with st.container(border=True):
                le = st.text_input("E-Posta Adresi", placeholder="ornek@firma.com").strip().lower()
                lp = st.text_input("Şifre", type="password", placeholder="••••••••")
                rem = st.checkbox("Beni Hatırla", value=True)
                
                st.write("")
                if st.button("SİSTEME GİRİŞ YAP", type="primary", use_container_width=True):
                    user = get_user_query("SELECT id, user_type, is_approved, is_verified, role FROM users WHERE email=? AND password=?", (le, hash_password(lp)))
                    if user:
                        uid, utype, app, ver, urole = user[0]
                        if ver == 0: st.warning(":warning: E-posta adresiniz doğrulanmamış!")
                        elif app == 0: st.warning(":hourglass_flowing_sand: Hesabınız yönetici onayı bekliyor.")
                        else:
                            tok = str(uuid.uuid4())
                            exec_user_query("UPDATE users SET session_token=? WHERE id=?", (tok, uid))
                            if rem: st.query_params["session_token"] = tok
                            st.session_state.logged_in, st.session_state.user_id, st.session_state.user_email = True, uid, le
                            st.session_state.user_role = urole if urole == 'admin' else ("manufacturer" if utype == "Üretici" else "dealer")
                            st.rerun()
                    else: 
                        st.error("Hatalı e-posta veya şifre!")

        with tab_register:
            with st.container(border=True):
                if st.session_state.reg_step == 1:
                    reg_type = st.selectbox("Faaliyet Türünüz", ["Satıcı (Bayi)", "Üretici"])
                    reg_comp = st.text_input("Firma Tam Ünvanı *", placeholder="Ersan Makine Ltd. Şti.")
                    reg_phone = st.text_input("İletişim Numarası *", placeholder="05XX XXX XX XX")
                    reg_email = st.text_input("Kurumsal E-Posta *", placeholder="ornek@firma.com").strip().lower()
                    reg_pwd = st.text_input("Sistem Şifresi Belirleyin *", type="password")
                    
                    st.write("")
                    if st.button("Kayıt Ol ve Doğrula", use_container_width=True):
                        if all([reg_comp, reg_phone, reg_email, reg_pwd]):
                            if get_user_query("SELECT id FROM users WHERE email=?", (reg_email,)):
                                st.error("Bu e-posta adresi zaten kayıtlı!")
                            else:
                                ver_code = generate_code()
                                exec_user_query(
                                    "INSERT INTO users (email, password, company_name, phone, user_type, auth_code, is_verified, is_approved) VALUES (?,?,?,?,?,?,0,0)",
                                    (reg_email, hash_password(reg_pwd), reg_comp, reg_phone, reg_type, ver_code)
                                )
                                if send_email(reg_email, ver_code, "Üyelik Doğrulama Kodu"):
                                    st.session_state.temp_email = reg_email
                                    st.session_state.reg_step = 2
                                    st.rerun()
                        else:
                            st.warning("Lütfen (*) ile işaretli alanları doldurun.")
                
                elif st.session_state.reg_step == 2:
                    st.success(f"{st.session_state.temp_email} adresine 6 haneli kod gönderildi.")
                    entered_code = st.text_input("Doğrulama Kodunu Giriniz", max_chars=6)
                    if st.button("Kodu Onayla", type="primary", use_container_width=True):
                        db_code = get_user_query("SELECT auth_code FROM users WHERE email=?", (st.session_state.temp_email,))
                        if db_code and db_code[0][0] == entered_code:
                            exec_user_query("UPDATE users SET is_verified=1, auth_code=NULL WHERE email=?", (st.session_state.temp_email,))
                            st.session_state.reg_step = 1
                            st.balloons()
                            st.success("Tebrikler! Hesabınız doğrulandı.")
                        else:
                            st.error("Hatalı kod girdiniz.")

        with tab_forgot:
            with st.container(border=True):
                if st.session_state.forgot_step == 1:
                    f_email = st.text_input("Kayıtlı E-Posta Adresiniz", placeholder="ornek@firma.com").strip().lower()
                    st.write("")
                    if st.button("Sıfırlama Kodu Gönder", use_container_width=True):
                        if f_email and get_user_query("SELECT id FROM users WHERE email=?", (f_email,)):
                            reset_code = generate_code()
                            exec_user_query("UPDATE users SET auth_code=? WHERE email=?", (reset_code, f_email))
                            if send_email(f_email, reset_code, "Şifre Sıfırlama Kodu"):
                                st.session_state.temp_email = f_email
                                st.session_state.forgot_step = 2
                                st.rerun()
                        else: st.error("Sistemde böyle bir e-posta bulunamadı.")
                
                elif st.session_state.forgot_step == 2:
                    st.info("E-postanıza gelen kodu girin.")
                    f_code = st.text_input("6 Haneli Kodu Girin", max_chars=6)
                    new_pwd = st.text_input("Yeni Şifreniz", type="password")
                    if st.button("Şifremi Değiştir", type="primary
