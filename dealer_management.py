import streamlit as st
import sqlite3
import pandas as pd

def show_dealer_management():
    st.header("🏢 Bayi ve Üretici Yönetimi")
    
    # --- ARAMA ÇUBUĞU ---
    search_query = st.text_input("🔍 Kullanıcı Ara (Firma Adı, E-Posta veya Telefon ile)", placeholder="Aramak istediğiniz kelimeyi yazın...")
    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
    
    # --- KATEGORİ LİSTESİNİ ÇEK (Sadece satıcıları yetkilendirmek için factory_data.db'den okuyoruz) ---
    try:
        conn_fact = sqlite3.connect('factory_data.db')
        c_cats = conn_fact.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()
        all_categories = [c[0] for c in c_cats]
        conn_fact.close()
    except Exception as e:
        all_categories = []
        st.warning("Kategori listesi okunamadı, factory_data.db kontrol edilmeli.")

    # --- KULLANICI VERİLERİNİ ÇEK ---
    conn = sqlite3.connect('users.db')
    # Bütün kullanıcıları çek (allowed_categories sütununu da dahil ettik)
    try:
        users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role, allowed_categories FROM users ORDER BY id DESC").fetchall()
    except:
        # Eğer allowed_categories sütunu eski kodda yoksa, sistemi çökertmeden okusun
        users_old = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role FROM users ORDER BY id DESC").fetchall()
        users = [(*u, "") for u in users_old] # allowed_categories yerine boş değer bas
    conn.close()
    
    # --- SATIŞ VERİLERİNİ ÇEK (İstatistikler için) ---
    conn_s = sqlite3.connect('sales_data.db')
    try:
        all_offers = conn_s.execute("SELECT user_id, status, total_price FROM offers").fetchall()
    except:
        all_offers = []
    conn_s.close()
    
    df_offers = pd.DataFrame(all_offers, columns=['user_id', 'status', 'total_price']) if all_offers else pd.DataFrame(columns=['user_id', 'status', 'total_price'])
    
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
        u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role, u_allowed_cats = u
        
        # --- İSTATİSTİKLERİ HESAPLA ---
        dealer_offers = df_offers[df_offers['user_id'] == u_id] if not df_offers.empty else pd.DataFrame()
        t_count = len(dealer_offers)
        t_vol = dealer_offers['total_price'].sum() if t_count > 0 else 0
        
        conv_offers = dealer_offers[dealer_offers['status'].isin(["Onaylandı", "Siparişe Çevir"])] if t_count > 0 else pd.DataFrame()
        c_count = len(conv_offers)
        c_vol = conv_offers['total_price'].sum() if c_count > 0 else 0
        
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

                    # 🚀 YENİ: SADECE BAYİLER İÇİN KATEGORİ SEÇİMİ 🚀
                    new_cats_str = ""
                    if new_type == "Satıcı (Bayi)":
                        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                        st.markdown("<div style='font-size:13px; font-weight:800; color:#ea580c; margin-bottom:5px;'>📦 Satıcının Teklif Verebileceği Kategoriler (Filtre):</div>", unsafe_allow_html=True)
                        
                        current_cats = [x.strip() for x in str(u_allowed_cats).split(",")] if u_allowed_cats else all_categories
                        # Multiselect ile satıcının göreceği kategorileri kısıtla
                        selected_cats = st.multiselect(
                            "Satış yapmasına izin verilen makine kategorilerini seçin:", 
                            options=all_categories,
                            default=[c for c in current_cats if c in all_categories],
                            help="Eğer hiçbirini seçmezseniz bayi hiçbir makineyi göremez!"
                        )
                        new_cats_str = ",".join(selected_cats)
                    elif new_type == "Yönetici":
                        st.info("💡 Yönetici tüm kategorileri görebilir, yetki kısıtlamasına gerek yoktur.")
                        new_cats_str = ""
                    elif new_type == "Üretici":
                        st.info("💡 Üretici sadece kendi eklediği makineleri görebilir, kategori kısıtlamasına gerek yoktur.")
                        new_cats_str = ""
                    
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<div style='font-size:13px; font-weight:800; color:#0f172a; margin-bottom:10px;'>🔑 Kullanıcının Görüntüleyebileceği Sayfa Menüleri:</div>", unsafe_allow_html=True)
                    
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
                    # (Satıcı -> Dealer, Üretici -> Producer, Yönetici -> Admin)
                    new_role = "admin" if new_type == "Yönetici" else ("Producer" if new_type == "Üretici" else "Dealer")
                    
                    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
                    submit_btn = st.form_submit_button("🔄 BİLGİLERİ VE YETKİLERİ GÜNCELLE", type="primary", use_container_width=True)
                    
                    if submit_btn:
                        conn_update = sqlite3.connect('users.db')
                        try:
                            conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", 
                                                (new_company, new_type, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                        except:
                            # Sütun veritabanında henüz yoksa zorla ekle (Sadece 1 kere çalışır)
                            conn_update.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
                            conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", 
                                                (new_company, new_type, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                            
                        conn_update.commit(); conn_update.close()
                        st.toast(f"{new_company} yetkileri güncellendi!")
                        st.rerun()
                        
                st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
                c3, c4 = st.columns(2)
                
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
