import streamlit as st
import sqlite3
import json
import streamlit.components.v1 as components
from offer_wizard import generate_embedded_html

# =====================================================================
# VERİTABANI MOTORLARI
# =====================================================================
def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_factory(query, params=()):
    conn = sqlite3.connect('factory_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

# =====================================================================
# ANA SİPARİŞ LİSTESİ MODÜLÜ
# =====================================================================
def show_orders(user_id, is_admin=False):
    st.header("📦 Siparişlerim" if not is_admin else "📦 Tüm Siparişler (Komuta Merkezi)")
    
    # -------------------------------------------------------------
    # SİPARİŞ (PDF) GÖRÜNTÜLEME MODU (SALT OKUNUR)
    # -------------------------------------------------------------
    if 'view_order_id' in st.session_state and st.session_state.view_order_id:
        if st.button("🔙 Sipariş Listesine Dön", type="primary"):
            st.session_state.view_order_id = None
            st.rerun()
        
        order_id = st.session_state.view_order_id
        
        o_data = get_sales("SELECT customer_id, model_id, total_price, conditions, user_id FROM offers WHERE id=?", (order_id,))
        if o_data:
            c_id, m_id, t_price, conds_str, o_user_id = o_data[0]
            conds = json.loads(conds_str) if conds_str else {}
            
            try: c_name = get_sales("SELECT company_name FROM customers WHERE id=?", (c_id,))[0][0]
            except: c_name = "Bilinmeyen Müşteri"
            
            try:
                m_info = get_factory("SELECT name, image_path, specs, currency, base_price FROM models WHERE id=?", (m_id,))[0]
                m_name, m_img, m_specs, m_curr, m_base_price = m_info
            except:
                m_name, m_img, m_specs, m_curr, m_base_price = "Bilinmeyen", "", "", "USD", 0.0
            
            items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (order_id,))
            engine_options_list = []
            for item in items:
                o_id, qty = item
                opt_info = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image FROM options WHERE id=?", (o_id,))
                if opt_info:
                    opt_name, opt_price, opt_desc, opt_img = opt_info[0]
                    # PDF görüntüleme için o anki fiyatı çekiyoruz
                    engine_options_list.append({'n': opt_name, 'p': opt_price, 'q': qty, 'i': opt_img, 'd': opt_desc})
            
            st.info("📌 **BİLGİ:** Bu sayfa mühürlü bir sipariş formudur. Üzerinde değişiklik yapılamaz, sadece incelenebilir ve yazdırılabilir.")
            
            html = generate_embedded_html(c_name, m_name, m_base_price, m_img, m_specs, engine_options_list, conds, m_curr, o_user_id)
            with st.container(border=True):
                components.html(html, height=850, scrolling=True)
        return

    # -------------------------------------------------------------
    # SİPARİŞ LİSTESİ (TABLO GÖRÜNÜMÜ)
    # -------------------------------------------------------------
    q = "SELECT o.id, c.company_name, o.model_id, o.offer_date, o.total_price, o.status, o.conditions, o.order_date, o.user_id FROM offers o JOIN customers c ON o.customer_id = c.id WHERE o.status IN ('Siparişe Çevir', 'Onaylandı')"
    if not is_admin:
        q += f" AND o.user_id={user_id}"
    q += " ORDER BY o.id DESC"
    
    orders_raw = get_sales(q)
    
    if orders_raw:
        for row in orders_raw:
            o_id, c_name, m_id, o_date, t_price, o_status, conds_str, order_date, o_user_id = row
            conds = json.loads(conds_str) if conds_str else {}
            delivery_time = conds.get('delivery_time', 'Sözleşmede Belirtilmemiş')
            
            try: m_name = get_factory("SELECT name FROM models WHERE id=?", (m_id,))[0][0]
            except: m_name = "Bilinmeyen Model"
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2.5, 2.5, 1], vertical_alignment="center")
                
                dealer_text = ""
                if is_admin:
                    try:
                        d_name = sqlite3.connect('users.db').execute("SELECT company_name FROM users WHERE id=?", (o_user_id,)).fetchone()[0]
                        dealer_text = f" | Bayi: <b style='color:#2563eb;'>{d_name}</b>"
                    except: pass

                c1.markdown(f"<h4 style='margin:0; color:#0f172a;'>{c_name}</h4><div style='font-size:13px; color:#64748b;'>Model: <b style='color:#0f172a;'>{m_name}</b>{dealer_text}</div>", unsafe_allow_html=True)
                
                o_time = order_date if order_date else "Eski Kayıt (Zaman Yok)"
                c2.markdown(f"<div style='font-size:13px; background:#f8fafc; padding:8px; border-radius:6px; border:1px solid #e2e8f0;'>🕒 <b>Siparişe Dönüşme:</b> {o_time}<br>🚚 <b>Hedef Teslimat:</b> <span style='color:#ea580c; font-weight:bold;'>{delivery_time}</span></div>", unsafe_allow_html=True)
                
                if c3.button("📄 Görüntüle / PDF", key=f"view_{o_id}", use_container_width=True):
                    st.session_state.view_order_id = o_id
                    st.rerun()
    else:
        st.info("Sistemde henüz siparişe dönmüş ve onaylanmış bir kayıt bulunmuyor.")
