import streamlit as st
import sqlite3
import pandas as pd

def show_dealer_management():
    st.header("🏢 Bayi ve Üretici Yönetimi")
    
    # --- ARAMA ÇUBUĞU ---
    search_query = st.text_input("🔍 Kullanıcı Ara (Firma Adı, E-Posta veya Telefon ile)", placeholder="Aramak istediğiniz kelimeyi yazın...")
    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
    
    # --- KULLANICI VERİLERİNİ ÇEK ---
    conn = sqlite3.connect('users.db')
    # Bütün kullanıcıları çek (Kendinizi yanlışlıkla silmemeniz için küçük bir uyarı koyacağız)
    users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    # --- SATIŞ VERİLERİNİ ÇEK (İstatistikler için) ---
    conn_s = sqlite3.connect('sales_data.db')
    all_offers = conn_s.execute("SELECT user_id, status, total_price FROM offers").fetchall()
    conn_s.close()
    
    df_offers = pd.DataFrame(all_offers, columns=['user_id', 'status', 'total_price'])
    
    if not users:
        st.info("Sistemde henüz kayıtlı kullanıcı bulunmuyor.")
        return
        
    if search_query:
        search_query = search_query.lower()
        users = [u for u in users if search_query in str(u[1]).lower() or search_query in str(u[2]).lower() or search_query in str(u[3]).lower()]
        if not users:
            st.warning("Arama kriterinize uygun kullanıcı bulunamadı.")
            return

    # KULLANICILARI LİSTELE
    for u in users:
        u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role = u
        
        # --- İSTATİSTİKLERİ HESAPLA ---
        dealer_offers = df_offers[df_offers['user_id'] == u_id]
        t_count = len(dealer_offers)
        t_vol = dealer_offers['total_price'].sum()
        
        conv_offers = dealer_offers[dealer_offers['status'].isin(["Onaylandı", "Siparişe Çevir"])]
        c_count = len(conv_offers)
        c_vol = conv_offers['total_price'].sum()
        
        with st.container(border=True):
            status_color = "#10b981" if u_approved else "#ef4444"
            status_text = "Aktif" if u_approved else "Askıda / Onay Bekliyor"
            
            # Adminleri belirginleştirelim
            role_badge = "👑 YÖNETİCİ" if u_role == 'admin' else u_type
            badge_color = "#ea580c" if u_role == 'admin' else "#2563eb"
            
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#0f172a;">{u_company}</h3>
                    <span style="background-color:{status_color}15; color:{status_color}; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:800; border:1px solid {status_color}50;">{status_text}</span>
                </div>
                <div style="font-size:14px; color:#64748b; margin-top:5px; margin-bottom:15px;">
                    <b style="color:{badge_color};">{role_badge}</b> | 📧 {u_email} | 📞 {u_phone if u_phone else 'Belirtilmemiş'}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <div style="flex:1; background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; text-align:center;">
                        <div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">Toplam Teklif</div>
                        <div style="font-size:18px; color:#0f172a; font-weight:900;">{t_count}</div>
                    </div>
                    <div style="flex:1; background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; text-align:center;">
                        <div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">Toplam Hacim</div>
                        <div style="font-size:18px; color:#3b82f6; font-weight:900;">{t_vol:,.0f}</div>
                    </div>
                    <div style="flex:1; background:#ecfdf5; padding:10px; border-radius:8px; border:1px solid #a7f3d0; text-align:center;">
                        <div style="font-size:11px; color:#059669; font-weight:700; text-transform:uppercase;">Siparişe Dönen</div>
                        <div style="font-size:18px; color:#10b981; font-weight:900;">{c_count}</div>
                    </div>
                    <div style="flex:1; background:#ecfdf5; padding:10px; border-radius:8px; border:1px solid #a7f3d0; text-align:center;">
                        <div style="font-size:11px; color:#059669; font-weight:700; text-transform:uppercase;">Sipariş Hacmi</div>
                        <div style="font-size:18px; color:#10b981; font-weight:900;">{c_vol:,.0f}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # --- DÜZENLEME VE MENÜ YETKİLENDİRME ALANI ---
            with st.expander("✏️ Bilgileri Düzenle ve Yetkileri Yönet", expanded=False):
                with st.form(key=f"form_dealer_{u_id}"):
                    c1, c2 = st.columns(2)
                    new_company = c1.text_input("Firma Adı", value=u_company)
                    
                    types = ["Satıcı (Bayi)", "Üretici", "Yönetici"]
                    new_type = c2.selectbox("Faaliyet Türü / Yetki", types, index=types.index(u_type) if u_type in types else 0)
                    
                    new_email = c1.text_input("E-Posta Adresi", value=u_email)
                    new_phone = c2.text_input("Telefon", value=u_phone if u_phone else "")
                    
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<div style='font-size:13px; font-weight:800; color:#0f172a; margin-bottom:10px;'>🔑 Kullanıcının Görüntüleyebileceği Menüler:</div>", unsafe_allow_html=True)
                    
                    # Bütün Menüler Eklendi!
                    menu_options = {
                        "m_dash": "📊 Dashboard",
                        "m_new": "📝 Yeni Teklif Hazırla",
                        "m_cust": "👥 Müşterilerim",
                        "m_past": "📋 Geçmiş Tekliflerim",
                        "m_order": "📦 Siparişler",
                        "m_model": "📦 Tüm Modelleri Yönet",
                        "m_deal": "🏢 Bayi / Kullanıcı Yönetimi",
                        "m_prof": "⚙️ Profil Ayarlarım"
                    }
                    current_menus = u_menus.split(',') if u_menus is not None else list(menu_options.keys())
                    
                    selected_menus = []
                    m_cols = st.columns(3)
                    for idx, (k, v) in enumerate(menu_options.items()):
                        with m_cols[idx % 3]:
                            if st.checkbox(v, value=(k in current_menus), key=f"chk_{u_id}_{k}"):
                                selected_menus.append(k)
                    
                    new_menus_str = ",".join(selected_menus)
                    
                    # Seçilen tipe göre arka planda "role" atamasını yapıyoruz
                    new_role = "admin" if new_type == "Yönetici" else ("manufacturer" if new_type == "Üretici" else "dealer")
                    
                    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
                    submit_btn = st.form_submit_button("🔄 BİLGİLERİ VE YETKİLERİ GÜNCELLE", type="primary", use_container_width=True)
                    
                    if submit_btn:
                        conn_update = sqlite3.connect('users.db')
                        conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=? WHERE id=?", 
                                            (new_company, new_type, new_email, new_phone, new_menus_str, new_role, u_id))
                        conn_update.commit(); conn_update.close()
                        st.toast(f"{new_company} yetkileri güncellendi!")
                        st.rerun()
                        
                st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
                c3, c4 = st.columns(2)
                
                # Kendini askıya almasını veya silmesini engelleyelim
                if u_id == st.session_state.user_id:
                    st.info("💡 Kendi yönetici hesabınızı askıya alamaz veya silemezsiniz.")
                else:
                    if u_approved:
                        if c3.button("🚫 Hesabı Askıya Al", key=f"sus_{u_id}", use_container_width=True):
                            conn_act = sqlite3.connect('users.db')
                            conn_act.execute("UPDATE users SET is_approved=0 WHERE id=?", (u_id,))
                            conn_act.commit(); conn_act.close()
                            st.rerun()
                    else:
                        if c3.button("✅ Hesabı Onayla / Aktifleştir", key=f"app_{u_id}", use_container_width=True):
                            conn_act = sqlite3.connect('users.db')
                            conn_act.execute("UPDATE users SET is_approved=1 WHERE id=?", (u_id,))
                            conn_act.commit(); conn_act.close()
                            st.rerun()
                            
                    if c4.button("🗑️ Tamamen Sil", key=f"del_{u_id}", use_container_width=True):
                        conn_act = sqlite3.connect('users.db')
                        conn_act.execute("DELETE FROM users WHERE id=?", (u_id,))
                        conn_act.commit(); conn_act.close()
                        st.rerun()
