import streamlit as st
import sqlite3
import pandas as pd

# Veritabanı bağlantı yardımcıları (Sadece bu dosya için)
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
    
    # --- 1. ONAY BEKLEYENLER BÖLÜMÜ ---
    st.subheader(":hourglass_flowing_sand: Onay Bekleyen Başvurular")
    pending = get_user_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=0 AND is_verified=1 AND role!='admin'")
    
    if pending:
        for p_id, p_name, p_type, p_email, p_phone in pending:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"**Firma:** {p_name} ({p_type}) | **Tel:** {p_phone} | **E-Posta:** {p_email}")
                if col2.button(":white_check_mark: Onayla ve Sistemi Aç", key=f"app_{p_id}", use_container_width=True):
                    exec_user_query("UPDATE users SET is_approved=1 WHERE id=?", (p_id,))
                    st.success(f"{p_name} onaylandı ve sisteme eklendi!")
                    st.rerun()
    else: 
        st.info("Şu an onay bekleyen yeni bir başvuru bulunmuyor.")
    
    st.markdown("---")
    
    # --- 2. AKTİF BAYİLER VE DÜZENLEME BÖLÜMÜ ---
    st.subheader(":white_check_mark: Aktif Bayiler ve Üreticiler")
    active = get_user_query("SELECT id, company_name, user_type, email, phone FROM users WHERE is_approved=1 AND role!='admin' ORDER BY id DESC")
    
    if active:
        # Görsel Tablo (Sadece bilgi amaçlı)
        df_active = pd.DataFrame(active, columns=["ID", "Firma", "Tür", "E-Posta", "Telefon"])
        st.dataframe(df_active.drop(columns=["ID"]), use_container_width=True)
        
        st.markdown("#### :pencil2: Bayi Bilgilerini Düzenle")
        
        # İşlem yapılacak bayiyi seçme kutusu
        user_options = {f"{row[1]} ({row[3]})": row for row in active}
        selected_user_key = st.selectbox("İşlem yapmak istediğiniz bayiyi seçin:", ["Seçiniz..."] + list(user_options.keys()))
        
        if selected_user_key != "Seçiniz...":
            u_data = user_options[selected_user_key]
            u_id = u_data[0]
            
            with st.container(border=True):
                with st.form(f"edit_dealer_{u_id}"):
                    c1, c2 = st.columns(2)
                    new_name = c1.text_input("Firma Adı", value=u_data[1])
                    
                    type_index = 0 if "Satıcı" in str(u_data[2]) else 1
                    new_type = c2.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"], index=type_index)
                    
                    new_email = c1.text_input("E-Posta Adresi", value=u_data[3])
                    new_phone = c2.text_input("Telefon", value=str(u_data[4]) if u_data[4] else "")
                    
                    st.write("")
                    btn_update = st.form_submit_button(":arrows_counterclockwise: BİLGİLERİ GÜNCELLE", type="primary", use_container_width=True)
                    
                    if btn_update:
                        # Faaliyet türüne göre yetki rolünü de güncelliyoruz
                        new_role = 'dealer' if new_type == "Satıcı (Bayi)" else 'manufacturer'
                        exec_user_query("UPDATE users SET company_name=?, user_type=?, role=?, email=?, phone=? WHERE id=?", 
                                        (new_name, new_type, new_role, new_email, new_phone, u_id))
                        st.success("Bayi bilgileri başarıyla güncellendi!")
                        st.rerun()
                
                # Form dışında tehlikeli işlemler (Askıya al / Sil)
                st.write("")
                col_suspend, col_delete = st.columns(2)
                if col_suspend.button(":no_entry_sign: Hesabı Askıya Al", use_container_width=True):
                    # Askıya alma: Onayı iptal et ve oturumu düşür
                    exec_user_query("UPDATE users SET is_approved=0, session_token=NULL WHERE id=?", (u_id,))
                    st.warning(f"{new_name} adlı kullanıcının onayı kaldırıldı. Tekrar onay bekleyenlere düştü.")
                    st.rerun()
                    
                if col_delete.button(":wastebasket: Bayiyi Tamamen Sil", use_container_width=True):
                    exec_user_query("DELETE FROM users WHERE id=?", (u_id,))
                    st.error("Bayi sistemden tamamen silindi.")
                    st.rerun()
    else:
        st.info("Sistemde henüz aktif bir bayi bulunmuyor.")
