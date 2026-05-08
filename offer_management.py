import streamlit as st
import sqlite3
import pandas as pd
import datetime

# =====================================================================
# VERİTABANI BAĞLANTILARI
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def get_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def exec_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
    except Exception as e: st.error(f"DB Error: {e}")

def get_users(query, params=()):
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

# =====================================================================
# TEKLİF LİSTESİ VE DURUM YÖNETİMİ
# =====================================================================
def show_offer_management(user_id, user_role):
    st.header("📋 Teklif Listesi ve Durum Yönetimi")
    st.markdown("<p style='color:#64748b; margin-top:-10px; margin-bottom:20px;'>Oluşturduğunuz teklifleri takip edebilir, siparişe çevirmek için yönetici onayına gönderebilirsiniz.</p>", unsafe_allow_html=True)
    
    # 1. KULLANICI ROLÜNÜ NETLEŞTİR
    u_role = 'dealer'
    if user_role == 'admin': u_role = 'admin'
    else:
        u_type_res = get_users("SELECT user_type FROM users WHERE id=?", (user_id,))
        if u_type_res and u_type_res[0][0] == 'Üretici': u_role = 'manufacturer'

    # 2. FİLTRELER
    with st.expander("🔍 Filtreleme Seçenekleri", expanded=True):
        status_opts = ["Tümü", "Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi"]
        selected_status = st.selectbox("Durum Seçimi", status_opts, index=0)
        
    # 3. VERİLERİ ÇEK
    query = "SELECT id, customer_id, model_id, total_price, offer_date, status, user_id FROM offers"
    params = []
    conds = []
    
    if u_role != "admin":
        conds.append("user_id=?")
        params.append(user_id)
        
    if selected_status != "Tümü":
        conds.append("status=?")
        params.append(selected_status)
        
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY id DESC"
    
    offers = get_sales(query, tuple(params))
    
    if not offers:
        st.info("Bu kriterlere uygun teklif bulunamadı.")
        return
        
    st.markdown(f"<div style='font-size:13px; font-weight:bold; color:#64748b; margin-bottom:15px;'>TOPLAM {len(offers)} TEKLİF BULUNDU</div>", unsafe_allow_html=True)
    
    # 4. KARTLARI LİSTELE (MODERN TASARIM)
    for o in offers:
        o_id, c_id, m_id, t_price, o_date, status, o_user_id = o
        
        # Bozuk veriyi toparlama (Eğer eski sistemden kalan tuhaf bir durum varsa)
        if status not in ["Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi"]:
            status = "Beklemede"
            
        c_info = get_sales("SELECT company_name FROM customers WHERE id=?", (c_id,))
        c_name = c_info[0][0] if c_info else "Bilinmeyen Müşteri"
        
        m_info = get_factory("SELECT name, currency FROM models WHERE id=?", (m_id,))
        m_name = m_info[0][0] if m_info else "Bilinmeyen Makine"
        m_curr = m_info[0][1] if m_info else "USD"
        
        d_info = get_users("SELECT company_name FROM users WHERE id=?", (o_user_id,))
        d_name = d_info[0][0] if d_info else "Bilinmeyen Kullanıcı"
        
        with st.container(border=True):
            col_head, col_price = st.columns([4, 1])
            col_head.markdown(f"<h3 style='margin:0; font-size:18px; color:#0f172a;'>🏢 {c_name}</h3>", unsafe_allow_html=True)
            col_head.markdown(f"<span style='color:#64748b; font-size:13px;'><b>Satıcı:</b> {d_name} | <b>Tarih:</b> {o_date} | <b>Makine:</b> <span style='color:#2563eb;'>{m_name}</span></span>", unsafe_allow_html=True)
            
            col_price.markdown(f"<div style='text-align:right; font-size:22px; font-weight:900; color:#ea580c;'>{t_price:,.2f} {m_curr}</div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin:12px 0 15px 0; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
            
            # --- ALT KISIM: AKSİYONLAR VE BUTONLAR ---
            c_stat, c_edit, c_prof, c_del = st.columns([1.5, 1, 1, 1], vertical_alignment="center")
            
            # A. DURUM YÖNETİMİ
            with c_stat:
                if u_role == "admin":
                    # YÖNETİCİ: Tüm ipler elinde, istediği duruma alabilir.
                    new_stat = st.selectbox("Durum Değiştir:", ["Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi"], index=["Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi"].index(status), key=f"stat_adm_{o_id}", label_visibility="collapsed")
                    if new_stat != status:
                        if new_stat == "Onaylandı":
                            tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                            exec_sales("UPDATE offers SET status=?, order_date=? WHERE id=?", (new_stat, tarih, o_id))
                        else:
                            exec_sales("UPDATE offers SET status=? WHERE id=?", (new_stat, o_id))
                        st.rerun()
                else:
                    # SATICI (BAYİ) ARAYÜZÜ
                    if status == "Onaylandı":
                        st.markdown("<div style='background:#dcfce7; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>✅ ONAYLANDI (Sipariş)</div>", unsafe_allow_html=True)
                    elif status == "Onay Bekliyor":
                        new_stat = st.selectbox("Durum:", ["⏳ ONAY BEKLENİYOR", "Vazgeç (Beklemeye Al)"], key=f"stat_dlr_wait_{o_id}", label_visibility="collapsed")
                        if new_stat == "Vazgeç (Beklemeye Al)":
                            exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                            st.rerun()
                    elif status == "İptal Edildi":
                        st.markdown("<div style='background:#fee2e2; color:#ef4444; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>❌ İPTAL EDİLDİ</div>", unsafe_allow_html=True)
                    else:
                        # Teklif Beklemede ise satıcı aksiyon alabilir
                        new_stat = st.selectbox("İşlem Seç:", ["Durum: Beklemede", "🚀 Siparişe Çevir (Onaya Gönder)", "❌ İptal Et"], key=f"stat_dlr_pen_{o_id}", label_visibility="collapsed")
                        if new_stat == "🚀 Siparişe Çevir (Onaya Gönder)":
                            exec_sales("UPDATE offers SET status=? WHERE id=?", ("Onay Bekliyor", o_id))
                            st.rerun()
                        elif new_stat == "❌ İptal Et":
                            exec_sales("UPDATE offers SET status=? WHERE id=?", ("İptal Edildi", o_id))
                            st.rerun()

            # B. BUTONLAR
            # Düzenle butonu sadece Beklemede iken aktiftir. Onaya giden teklif değiştirilemez!
            if c_edit.button("✏️ Düzenle", key=f"btn_e_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor", "İptal Edildi"])):
                st.session_state.edit_offer_id = o_id
                st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
                st.rerun()
                
            if c_prof.button("📄 Proforma", key=f"btn_p_{o_id}", use_container_width=True):
                st.session_state.proforma_offer_id = o_id
                st.info("Proforma PDF hazırlık aşamasında. Çok yakında buradan çıktı alabileceksiniz.")
                
            # Silme işlemi sadece Beklemede veya İptal durumunda yapılabilir
            if c_del.button("🗑️ Sil", key=f"btn_d_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor"])):
                exec_sales("DELETE FROM offers WHERE id=?", (o_id,))
                exec_sales("DELETE FROM offer_items WHERE offer_id=?", (o_id,))
                st.rerun()
