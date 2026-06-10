import streamlit as st
import sqlite3
import os
import uuid
import hashlib
from PIL import Image

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_user_data(user_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    res = c.execute("SELECT company_name, email, phone, website, address_full, logo_path, password FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return res

def update_user_data(user_id, company, phone, website, address, logo_path):
    conn = sqlite3.connect('users.db')
    conn.execute("UPDATE users SET company_name=?, phone=?, website=?, address_full=?, logo_path=? WHERE id=?", (company, phone, website, address, logo_path, user_id))
    conn.commit()
    conn.close()

def update_password(user_id, new_pass):
    conn = sqlite3.connect('users.db')
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_pass), user_id))
    conn.commit()
    conn.close()

def process_logo(uploaded_file):
    if not os.path.exists("images"): os.makedirs("images")
    try:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((500, 500), Image.Resampling.LANCZOS)
        filename = f"logo_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join("images", filename)
        img.save(filepath, "JPEG", quality=90)
        return filename
    except Exception as e:
        return ""

def show_profile_settings(user_id):
    st.header("⚙️ Profil Ayarlarım")
    st.markdown("<p style='color:#64748b;'>Firma bilgilerinizi, logonuzu ve güvenlik ayarlarınızı buradan yönetebilirsiniz. <b>Buraya girdiğiniz bilgiler PDF Teklif Formlarınızda (Proforma) kullanılacaktır.</b></p>", unsafe_allow_html=True)

    user_data = get_user_data(user_id)
    if not user_data:
        st.error("Kullanıcı bilgileri bulunamadı."); return

    company, email, phone, website, address, logo, current_hash = user_data

    t1, t2 = st.tabs(["🏢 Firma Bilgileri & Kurumsal Kimlik", "🔒 Güvenlik & Şifre Değişimi"])

    with t1:
        with st.container(border=True):
            c_logo, c_info = st.columns([1, 2.5], gap="large")
            with c_logo:
                st.markdown("<b>Firma Logosu (PDF İçin)</b>", unsafe_allow_html=True)
                if logo and os.path.exists(os.path.join("images", logo)): st.image(os.path.join("images", logo), use_container_width=True)
                else: st.markdown("<div style='height:150px; background:#f8fafc; display:flex; align-items:center; justify-content:center; border:1px solid #cbd5e1;'>Logo Yok</div>", unsafe_allow_html=True)
                new_logo = st.file_uploader("Logo Değiştir", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")

            with c_info:
                new_company = st.text_input("Firma Tam Ünvanı *", value=company if company else "")
                st.text_input("Kayıtlı E-Posta Adresi (Değiştirilemez)", value=email, disabled=True)
                c_tel, c_web = st.columns(2)
                new_phone = c_tel.text_input("Telefon Numarası", value=phone if phone else "")
                new_website = c_web.text_input("Web Sitesi", value=website if website else "", placeholder="www.firmaniz.com")

            new_address = st.text_area("Açık Adres (Proforma Alt Bilgisi İçin)", value=address if address else "", height=100)
            if st.button("💾 BİLGİLERİ VE LOGOYU KAYDET", type="primary", use_container_width=True):
                final_logo = logo
                if new_logo:
                    uploaded_path = process_logo(new_logo)
                    if uploaded_path: final_logo = uploaded_path
                update_user_data(user_id, new_company, new_phone, new_website, new_address, final_logo)
                st.success("✅ Bilgileriniz başarıyla güncellendi!"); st.rerun()

    with t2:
        with st.container(border=True):
            c_pass1, c_pass2 = st.columns(2)
            old_p = c_pass1.text_input("Mevcut Şifreniz", type="password")
            new_p = c_pass1.text_input("Yeni Şifre", type="password")
            new_p2 = c_pass2.text_input("Yeni Şifre (Tekrar)", type="password")
            if st.button("🔄 ŞİFREYİ GÜNCELLE", type="primary"):
                if not old_p or not new_p or not new_p2: st.warning("Tüm alanları doldurun.")
                elif hash_password(old_p) != current_hash: st.error("Mevcut şifre yanlış!")
                elif new_p != new_p2: st.error("Şifreler uyuşmuyor!")
                elif len(new_p) < 6: st.error("Şifre en az 6 karakter olmalı.")
                else: update_password(user_id, new_p); st.success("✅ Şifre değiştirildi!")
