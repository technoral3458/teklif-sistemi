import streamlit as st
import sqlite3

def show_dealer_management():
    st.header("🏢 Bayi ve Üretici Yönetimi")
    
    conn = sqlite3.connect('users.db')
    # Admin hariç tüm kullanıcıları getir
    users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved FROM users WHERE role != 'admin' ORDER BY id DESC").fetchall()
    
    if not users:
        st.info("Sistemde henüz kayıtlı bayi veya üretici bulunmuyor.")
        conn.close()
        return
        
    for u in users:
        u_id, u_company, u_email, u_phone, u_type, u_approved = u
        
        with st.container(border=True):
            # 1. BAŞLIK VE TEMEL BİLGİLER
            st.markdown(f"### {u_company}")
            
            # Duruma göre renkli etiket
            status_color = "#10b981" if u_approved else "#ef4444"
            status_text = "Aktif" if u_approved else "Askıda / Onay Bekliyor"
            
            st.markdown(f"""
                <div style="font-size:14px; color:#475569; margin-bottom:15px;">
                    <b style="color:#2563eb;">{u_type}</b> | 📧 {u_email} | 📞 {u_phone} | 
                    <span style="color:{status_color}; font-weight:bold;">{status_text}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # 2. DÜZENLEME ALANI (Otomatik kapanma özelliği için expanded=False)
            with st.expander("✏️ Bilgileri Düzenle / Yönet", expanded=False):
                
                # --- GÜNCELLEME FORMU ---
                with st.form(key=f"form_dealer_{u_id}"):
                    c1, c2 = st.columns(2)
                    new_company = c1.text_input("Firma Adı", value=u_company)
                    new_type = c2.selectbox("Faaliyet Türü", ["Satıcı (Bayi)", "Üretici"], index=0 if u_type=="Satıcı (Bayi)" else 1)
                    
                    new_email = c1.text_input("E-Posta Adresi", value=u_email)
                    new_phone = c2.text_input("Telefon", value=u_phone if u_phone else "")
                    
                    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                    submit_btn = st.form_submit_button("🔄 GÜNCELLE", type="primary", use_container_width=True)
                    
                    if submit_btn:
                        conn_update = sqlite3.connect('users.db')
                        conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=? WHERE id=?", 
                                            (new_company, new_type, new_email, new_phone, u_id))
                        conn_update.commit()
                        conn_update.close()
                        st.toast(f"{new_company} bilgileri güncellendi!")
                        st.rerun() # Sayfayı yeniler ve expander'ı otomatik kapatır
                        
                # --- AKSİYON BUTONLARI (ASKIYA AL / SİL) ---
                st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
                c3, c4 = st.columns(2)
                
                if u_approved:
                    if c3.button("🚫 Hesabı Askıya Al", key=f"sus_{u_id}", use_container_width=True):
                        conn_act = sqlite3.connect('users.db')
                        conn_act.execute("UPDATE users SET is_approved=0 WHERE id=?", (u_id,))
                        conn_act.commit(); conn_act.close()
                        st.toast("Hesap askıya alındı!")
                        st.rerun()
                else:
                    if c3.button("✅ Hesabı Onayla / Aktifleştir", key=f"app_{u_id}", use_container_width=True):
                        conn_act = sqlite3.connect('users.db')
                        conn_act.execute("UPDATE users SET is_approved=1 WHERE id=?", (u_id,))
                        conn_act.commit(); conn_act.close()
                        st.toast("Hesap aktifleştirildi!")
                        st.rerun()
                        
                if c4.button("🗑️ Tamamen Sil", key=f"del_{u_id}", use_container_width=True):
                    conn_act = sqlite3.connect('users.db')
                    conn_act.execute("DELETE FROM users WHERE id=?", (u_id,))
                    conn_act.commit(); conn_act.close()
                    st.toast("Hesap sistemden silindi!")
                    st.rerun()
                    
    conn.close()
