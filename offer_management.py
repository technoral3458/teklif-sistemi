import streamlit as st
import sqlite3
import pandas as pd
import datetime
import json
import proforma_invoice # <--- YENİ MODÜLÜMÜZÜ İÇERİ ALIYORUZ

# =====================================================================
# YARDIMCI FONKSİYONLAR VE VERİTABANI
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
    
    u_role = 'dealer'
    if user_role == 'admin': u_role = 'admin'
    else:
        u_type_res = get_users("SELECT user_type FROM users WHERE id=?", (user_id,))
        if u_type_res and u_type_res[0][0] == 'Üretici': u_role = 'manufacturer'

    with st.expander("🔍 Filtreleme Seçenekleri", expanded=True):
        status_opts = ["Tümü", "Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi / Reddedildi"]
        selected_status = st.selectbox("Durum Seçimi", status_opts, index=0)
        
    query = "SELECT id, customer_id, model_id, total_price, offer_date, status, user_id, conditions FROM offers"
    params = []
    conds_query = []
    
    if u_role != "admin":
        conds_query.append("user_id=?")
        params.append(user_id)
        
    if selected_status != "Tümü":
        if selected_status == "İptal Edildi / Reddedildi":
            conds_query.append("status IN ('İptal Edildi', 'Reddedildi')")
        else:
            conds_query.append("status=?")
            params.append(selected_status)
        
    if conds_query: query += " WHERE " + " AND ".join(conds_query)
    query += " ORDER BY id DESC"
    
    offers = get_sales(query, tuple(params))
    
    if not offers:
        st.info("Bu kriterlere uygun teklif bulunamadı.")
        return
        
    st.markdown(f"<div style='font-size:13px; font-weight:bold; color:#64748b; margin-bottom:15px;'>TOPLAM {len(offers)} TEKLİF BULUNDU</div>", unsafe_allow_html=True)
    
    for o in offers:
        o_id, c_id, m_id, t_price, o_date, status, o_user_id, conds_str = o
        
        try: conds_json = json.loads(conds_str) if conds_str else {}
        except: conds_json = {}
        
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
            
            rejection_note = conds_json.get("rejection_note", "")
            if (status in ["İptal Edildi", "Reddedildi"]) and rejection_note:
                st.markdown(f"<div style='margin-top:10px; padding:10px; background-color:#fef2f2; border-left:4px solid #ef4444; color:#991b1b; font-size:13px;'><b>Yönetici Notu:</b> {rejection_note}</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin:12px 0 15px 0; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
            
            act = st.session_state.get(f"adm_act_{o_id}")
            
            # YÖNETİCİ ARAYÜZÜ (Önizleme veya Ret Ekranı)
            if u_role == "admin" and act in ["approve", "reject"]:
                if act == "approve":
                    st.markdown("<div style='background:#eff6ff; padding:15px; border-radius:8px; border:1px solid #bfdbfe;'><h4 style='color:#1e40af; margin-top:0;'>🔍 Ayrıntılı Teklif Formu Önizlemesi</h4>", unsafe_allow_html=True)
                    
                    # BAĞIMSIZ MODÜLÜ ÇAĞIRIYORUZ
                    proforma_invoice.render_proforma(o_id, o_date, c_name, m_id, m_name, t_price, m_curr, conds_json, o_user_id)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.write("")
                    
                    cc1, cc2 = st.columns([1, 1])
                    if cc1.button("🚀 KESİN ONAYLA VE SİPARİŞLERE AKTAR", key=f"btn_conf_app_{o_id}", type="primary", use_container_width=True):
                        tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                        exec_sales("UPDATE offers SET status=?, order_date=? WHERE id=?", ("Onaylandı", tarih, o_id))
                        del st.session_state[f"adm_act_{o_id}"]
                        st.rerun()
                    if cc2.button("Vazgeç (Geri Dön)", key=f"btn_canc_app_{o_id}", use_container_width=True):
                        del st.session_state[f"adm_act_{o_id}"]
                        st.rerun()
                        
                elif act == "reject":
                    with st.container(border=True):
                        st.markdown("<b style='color:#ef4444;'>❌ Reddetme Sebebi (Satıcıya İletilecek):</b>", unsafe_allow_html=True)
                        rej_note = st.text_area("Notunuzu girin:", key=f"txt_rej_{o_id}", label_visibility="collapsed")
                        
                        cr1, cr2 = st.columns([1, 1])
                        if cr1.button("💾 Kaydet ve Reddet", key=f"btn_conf_rej_{o_id}", type="primary", use_container_width=True):
                            conds_json["rejection_note"] = rej_note
                            updated_conds = json.dumps(conds_json)
                            exec_sales("UPDATE offers SET status=?, conditions=? WHERE id=?", ("Reddedildi", updated_conds, o_id))
                            del st.session_state[f"adm_act_{o_id}"]
                            st.rerun()
                        if cr2.button("Vazgeç", key=f"btn_canc_rej_{o_id}", use_container_width=True):
                            del st.session_state[f"adm_act_{o_id}"]
                            st.rerun()
                            
            # NORMAL BUTONLAR
            else:
                c_stat, c_edit, c_prof, c_del = st.columns([2.5, 1, 1, 1], vertical_alignment="center")
                
                with c_stat:
                    if u_role == "admin":
                        if status in ["Beklemede", "Onay Bekliyor"]:
                            ca1, ca2 = st.columns(2)
                            if ca1.button("✅ Onayla", key=f"btn_app_{o_id}", type="primary", use_container_width=True):
                                st.session_state[f"adm_act_{o_id}"] = "approve"
                                st.rerun()
                            if ca2.button("❌ Reddet", key=f"btn_rej_{o_id}", use_container_width=True):
                                st.session_state[f"adm_act_{o_id}"] = "reject"
                                st.rerun()
                        elif status == "Onaylandı":
                            ca1, ca2 = st.columns([2.5, 1.5])
                            ca1.markdown("<div style='background:#dcfce7; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px; white-space:nowrap;'>✅ ONAYLANDI</div>", unsafe_allow_html=True)
                            if ca2.button("↩️ Geri", key=f"btn_rev_{o_id}", help="Onayı iptal edip beklemeye al", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                        else:
                            ca1, ca2 = st.columns([2.5, 1.5])
                            ca1.markdown("<div style='background:#fee2e2; color:#ef4444; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px; white-space:nowrap;'>❌ RED / İPTAL</div>", unsafe_allow_html=True)
                            if ca2.button("↩️ Geri", key=f"btn_rev2_{o_id}", help="Reddi iptal edip beklemeye al", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                    else:
                        if status == "Onaylandı":
                            st.markdown("<div style='background:#dcfce7; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>✅ ONAYLANDI (Siparişe Dönüştü)</div>", unsafe_allow_html=True)
                        elif status == "Onay Bekliyor":
                            cb1, cb2 = st.columns([2, 1])
                            cb1.markdown("<div style='background:#fef08a; color:#b45309; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>⏳ YÖNETİCİ ONAYI BEKLENİYOR</div>", unsafe_allow_html=True)
                            if cb2.button("Geri Çek", key=f"btn_dlr_pull_{o_id}", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                        elif status in ["İptal Edildi", "Reddedildi"]:
                            st.markdown("<div style='background:#fee2e2; color:#ef4444; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>❌ REDDEDİLDİ / İPTAL</div>", unsafe_allow_html=True)
                        else:
                            cd1, cd2 = st.columns(2)
                            if cd1.button("🚀 Onaya Gönder", key=f"btn_dlr_snd_{o_id}", type="primary", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Onay Bekliyor", o_id))
                                st.rerun()
                            if cd2.button("❌ İptal Et", key=f"btn_dlr_cncl_{o_id}", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("İptal Edildi", o_id))
                                st.rerun()

                if c_edit.button("✏️ Düzenle", key=f"btn_e_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor"])):
                    st.session_state.edit_offer_id = o_id
                    st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
                    st.rerun()
                    
                # PROFORMA BUTONU MANTIĞI
                if c_prof.button("📄 Proforma", key=f"btn_p_{o_id}", use_container_width=True):
                    st.session_state[f"show_prof_{o_id}"] = not st.session_state.get(f"show_prof_{o_id}", False)
                    # Proforma açılıyorsa admin onay panelini kapa (çakışma olmasın)
                    if f"adm_act_{o_id}" in st.session_state: del st.session_state[f"adm_act_{o_id}"]
                    st.rerun()
                    
                if c_del.button("🗑️ Sil", key=f"btn_d_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor"])):
                    exec_sales("DELETE FROM offers WHERE id=?", (o_id,))
                    exec_sales("DELETE FROM offer_items WHERE offer_id=?", (o_id,))
                    st.rerun()
            
            # --- BAĞIMSIZ PROFORMA GÖSTERİCİ MANTIĞI ---
            if st.session_state.get(f"show_prof_{o_id}", False):
                st.markdown("<div style='background:#f8fafc; padding:15px; border-radius:8px; border:1px solid #e2e8f0; margin-top:15px;'>", unsafe_allow_html=True)
                
                c_p1, c_p2 = st.columns([5, 1])
                c_p1.markdown("<h4 style='color:#0f172a; margin-top:0;'>📄 Proforma Teklif Formu</h4>", unsafe_allow_html=True)
                if c_p2.button("❌ Kapat", key=f"close_prof_{o_id}", use_container_width=True):
                    st.session_state[f"show_prof_{o_id}"] = False
                    st.rerun()
                
                # BAĞIMSIZ MODÜLÜ ÇAĞIRIYORUZ
                proforma_invoice.render_proforma(o_id, o_date, c_name, m_id, m_name, t_price, m_curr, conds_json, o_user_id)
                
                st.markdown("</div>", unsafe_allow_html=True)
