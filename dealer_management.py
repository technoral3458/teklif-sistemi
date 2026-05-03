import streamlit as st
import sqlite3

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

def show_dealer_management():
    st.header(":office: Üyelik Onay ve Yönetim Sistemi")
    
    # --- 1. ONAY BEKLEYENLER ---
    st.subheader(":hourglass_flowing_sand: Onay Bekleyen Başvurular")
    pending = get_user_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=0 AND is_verified=1 AND role!='admin'")
    
    if pending:
        for p_id, p_name, p_type, p_email, p_phone in pending:
            with st.container(border=True):
                st.markdown(f"**{p_name}** ({p_type})")
                st.markdown(f"📧 {p_email} | 📞 {p_phone}")
                if st.button(":white_check_mark: Onayla ve Sistemi Aç", key=f"app_{p_id}", use_container_width=True):
                    exec_user_query("UPDATE users SET is_approved=1 WHERE id=?", (p_id,))
                    st.success(f"{p_name} onaylandı!")
                    st.rerun()
    else: 
        st.info("Şu an onay bekleyen başvuru bulunmuyor.")
    
    st.markdown("---")
    
    # --- 2. AKTİF BAYİLER (KART SİSTEMİ) ---
    st.subheader(":white_check_mark: Aktif Bayiler ve Üreticiler")
    active = get_user_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=1 AND role!='admin' ORDER BY id DESC")
    
    if active:
        for row in active:
            u_id, u_comp, u_type, u_email, u_phone = row
            with st.container(border=True):
                # Üst Kısım: Bayi Bilgileri
                st.markdown(f"<h4 style='margin:0; color:#0f172a;'>{u_comp}</h4>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:#3b82f6; font-weight:bold;'>{u_type}</span> | 📧 {u_email} | 📞 {u_phone if u_phone else '-'}", unsafe_allow_html=True)
                
                st.write("")
                # Alt Kısım: Aksiyon Butonları (Düzenle ve Sil)
                with st.expander(":pencil2: Bilgileri Düzenle / Yönet"):
                    with st.form(f"edit_{u_id}"):
                        c1, c2 = st.columns(2)
                        new_name = c1.text_input("Firma Adı", value=u_comp)
                        new_type = c2.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"], index=0 if "Satıcı" in str(u_type) else 1)
                        new_email = c1.text_input("E-Posta Adresi", value=u_email)
                        new_phone = c2.text_input("Telefon", value=str(u_phone) if u_phone else "")
                        
                        st.write("")
                        if st.form_submit_button(":arrows_counterclockwise: GÜNCELLE", type="primary", use_container_width=True):
                            new_role = 'dealer' if new_type == "Satıcı (Bayi)" else 'manufacturer'
                            exec_user_query("UPDATE users SET company_name=?, user_type=?, role=?, email=?, phone=? WHERE id=?", 
                                            (new_name, new_type, new_role, new_email, new_phone, u_id))
                            st.success("Güncellendi!")
                            st.rerun()
                    
                    # Form Dışı Tehlikeli İşlemler
                    st.write("")
                    col_suspend, col_del = st.columns(2)
                    if col_suspend.button(":no_entry_sign: Hesabı Askıya Al", key=f"susp_{u_id}", use_container_width=True):
                        exec_user_query("UPDATE users SET is_approved=0, session_token=NULL WHERE id=?", (u_id,))
                        st.rerun()
                    if col_del.button(":wastebasket: Tamamen Sil", key=f"del_{u_id}", use_container_width=True):
                        exec_user_query("DELETE FROM users WHERE id=?", (u_id,))
                        st.rerun()
    else:
        st.info("Sistemde aktif bir bayi bulunmuyor.")
