import streamlit as st
import sqlite3
import pandas as pd

def get_db(db, query, params=()):
    try:
        conn = sqlite3.connect(db, check_same_thread=False)
        res = conn.execute(query, params).fetchall()
        conn.close()
        return res
    except: return []

def show_customer_management(user_id, is_admin=False):
    if "cust_view" not in st.session_state: st.session_state.cust_view = "list"
    
    if st.session_state.cust_view == "list":
        st.header(":busts_in_silhouette: Müşteri Rehberi ve Cari Yönetimi")
        
        with st.expander("➕ Yeni Müşteri Tanımla", expanded=False):
            with st.form("new_cust"):
                c1, c2 = st.columns(2)
                f_name = c1.text_input("Firma Adı *")
                f_cont = c2.text_input("Yetkili Kişi")
                f_pho = c1.text_input("Telefon Numarası")
                f_ema = c2.text_input("E-Posta Adresi")
                f_adr = st.text_area("Açık Adres")
                if st.form_submit_button("Müşteriyi Kaydet", type="primary") and f_name:
                    conn = sqlite3.connect('sales_data.db')
                    conn.execute("INSERT INTO customers (user_id, company_name, contact_person, phone, email, address) VALUES (?,?,?,?,?,?)", (user_id, f_name, f_cont, f_pho, f_ema, f_adr))
                    conn.commit(); conn.close()
                    st.success("Müşteri kaydedildi!")
                    st.rerun()

        st.markdown("---")
        q = "SELECT id, company_name, contact_person, phone, user_id FROM customers"
        params = ()
        if not is_admin: 
            q += " WHERE user_id=?"
            params = (user_id,)
        
        custs = get_db('sales_data.db', q + " ORDER BY id DESC", params)
        
        if custs:
            df = pd.DataFrame(custs, columns=["id", "company", "contact", "phone", "uid"])
            if is_admin:
                bayiler = {u[0]: u[1] for u in get_db('users.db', "SELECT id, company_name FROM users")}
                for b_id in df['uid'].unique():
                    bayi_adi = bayiler.get(b_id, "Bilinmeyen Bayi")
                    with st.expander(f"🏢 {bayi_adi} (Bayisi Müşterileri)", expanded=True):
                        render_cards(df[df['uid'] == b_id])
            else:
                render_cards(df)
        else:
            st.info("Kayıtlı müşteri bulunamadı.")

    else:
        render_detail(st.session_state.selected_cust_id)

def render_cards(df):
    df = df.reset_index(drop=True)
    for i in range(0, len(df), 3):
        cols = st.columns(3)
        for j in range(3):
            if i+j < len(df):
                row = df.iloc[i+j]
                with cols[j].container(border=True):
                    st.markdown(f"<h4 style='color:#0f172a; margin:0;'>{row['company']}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<small>👤 {row['contact']} | 📞 {row['phone']}</small>", unsafe_allow_html=True)
                    st.write("")
                    if st.button("📁 Cari Detay", key=f"det_{row['id']}", use_container_width=True):
                        st.session_state.selected_cust_id = row['id']
                        st.session_state.cust_view = "detail"
                        st.rerun()

def render_detail(cust_id):
    c_data = get_db('sales_data.db', "SELECT company_name, email, phone, contact_person FROM customers WHERE id=?", (cust_id,))
    if not c_data:
        st.error("Müşteri bulunamadı!")
        if st.button("Geri Dön"): st.session_state.cust_view = "list"; st.rerun()
        return
        
    c = c_data[0]
    col1, col2 = st.columns([1, 5])
    if col1.button("🔙 Rehbere Dön", use_container_width=True): 
        st.session_state.cust_view = "list"
        st.rerun()
        
    col2.header(f"🏢 {c[0]} - Cari Hareketleri")
    st.markdown(f"**Yetkili:** {c[3]} | **Tel:** {c[2]} | **E-Posta:** {c[1]}")
    st.markdown("---")
    
    offers = get_db('sales_data.db', "SELECT id, model_id, total_price, status, offer_date FROM offers WHERE customer_id=? ORDER BY id DESC", (cust_id,))
    if offers:
        for o in offers:
            try: m_name = get_db('factory_data.db', "SELECT name FROM models WHERE id=?", (o[1],))[0][0]
            except: m_name = "Bilinmeyen Model"
            
            bg_color = "#f8fafc"
            border_color = "#e2e8f0"
            if o[3] == "Siparişe Çevir": bg_color = "#ecfdf5"; border_color = "#10b981"
            elif o[3] == "Reddedildi": bg_color = "#fef2f2"; border_color = "#ef4444"
            
            with st.container(border=True):
                st.markdown(f"""
                <div style="background:{bg_color}; border:2px solid {border_color}; padding:15px; border-radius:8px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between;">
                        <div><h4 style="margin:0; color:#0f172a;">Teklif #{o[0]} - {m_name}</h4><div style="color:#64748b; font-size:12px;">Tarih: {o[4]}</div></div>
                        <div style="text-align:right;"><h3 style="margin:0; color:#ea580c;">{o[2]:,.2f}</h3></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                ca, cb = st.columns([2, 1])
                new_stat = ca.selectbox("Durum Güncelle", ["Beklemede", "Siparişe Çevir", "Reddedildi"], index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(o[3] if o[3] in ["Beklemede", "Siparişe Çevir", "Reddedildi"] else "Beklemede"), key=f"s_{o[0]}", label_visibility="collapsed")
                
                if new_stat != o[3]:
                    conn = sqlite3.connect('sales_data.db'); conn.execute("UPDATE offers SET status=? WHERE id=?", (new_stat, o[0])); conn.commit(); conn.close()
                    st.toast("Durum güncellendi!"); st.rerun()
                    
                if cb.button("📄 PROFORMA OLUŞTUR", key=f"p_{o[0]}", type="primary", use_container_width=True):
                    st.session_state.proforma_id = o[0]
                    st.session_state.active_tab = "PROFORMA"
                    st.rerun()
    else:
        st.info("Bu müşteriye ait henüz teklif bulunmuyor.")
