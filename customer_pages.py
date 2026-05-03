import streamlit as st
import sqlite3
import pandas as pd

def get_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db')
    c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()

def get_user_query(query, params=()):
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def show_customer_management(user_id, is_admin=False):
    if "cust_view_mode" not in st.session_state: st.session_state.cust_view_mode = "list"
    if "selected_cust_id" not in st.session_state: st.session_state.selected_cust_id = None

    if st.session_state.cust_view_mode == "list":
        show_list(user_id, is_admin)
    elif st.session_state.cust_view_mode == "detail":
        show_customer_detail(st.session_state.selected_cust_id, is_admin)

def show_list(user_id, is_admin):
    st.header(":busts_in_silhouette: Müşteri Rehberi ve Cari Yönetimi")
    exec_sales("""CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, company_name TEXT, contact_person TEXT, phone TEXT, email TEXT, address TEXT)""")

    with st.expander("➕ Yeni Müşteri Tanımla", expanded=False):
        with st.form("new_cust"):
            c1, c2 = st.columns(2)
            c_comp = c1.text_input("Firma Adı *")
            c_cont = c2.text_input("Yetkili Kişi")
            c_pho = c1.text_input("Telefon Numarası")
            c_ema = c2.text_input("E-Posta Adresi")
            c_adr = st.text_area("Açık Adres")
            if st.form_submit_button("Müşteriyi Kaydet", type="primary"):
                if c_comp:
                    exec_sales("INSERT INTO customers (user_id, company_name, contact_person, phone, email, address) VALUES (?,?,?,?,?,?)", (user_id, c_comp, c_cont, c_pho, c_ema, c_adr))
                    st.success("Müşteri kaydedildi!"); st.rerun()
                else: st.error("Firma adı zorunludur!")

    st.markdown("---")
    
    c_query = "SELECT id, company_name, contact_person, phone, user_id FROM customers ORDER BY id DESC" if is_admin else "SELECT id, company_name, contact_person, phone, user_id FROM customers WHERE user_id=? ORDER BY id DESC"
    c_params = () if is_admin else (user_id,)
    custs = get_sales(c_query, c_params)

    if custs:
        user_dict = {}
        if is_admin:
            users_raw = get_user_query("SELECT id, company_name FROM users")
            user_dict = {u[0]: u[1] for u in users_raw}

        df = pd.DataFrame(custs, columns=["id", "company", "contact", "phone", "user_id"])
        
        if is_admin:
            for bayi_id in df['user_id'].unique():
                bayi_adi = user_dict.get(bayi_id, "Bilinmeyen Bayi")
                with st.expander(f"🏢 {bayi_adi} Bayisi Müşterileri", expanded=True):
                    draw_customer_cards(df[df['user_id'] == bayi_id])
        else:
            draw_customer_cards(df)
    else: st.info("Kayıtlı müşteri bulunamadı.")

def draw_customer_cards(df_custs):
    for i in range(0, len(df_custs), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(df_custs):
                row = df_custs.iloc[i+j]
                with cols[j].container(border=True):
                    st.markdown(f"**{row['company']}**")
                    st.markdown(f"<small>📞 {row['phone']}</small>", unsafe_allow_html=True)
                    if st.button("📁 Cari Detay", key=f"c_{row['id']}", use_container_width=True):
                        st.session_state.selected_cust_id = int(row['id'])
                        st.session_state.cust_view_mode = "detail"
                        st.rerun()

def show_customer_detail(cust_id, is_admin):
    c_data = get_sales("SELECT company_name, contact_person, phone, email, address FROM customers WHERE id=?", (cust_id,))[0]
    
    col1, col2 = st.columns([1, 5])
    if col1.button("🔙 Rehbere Dön"):
        st.session_state.cust_view_mode = "list"
        st.rerun()
    
    col2.header(f"🏢 {c_data[0]}")
    st.markdown(f"**Yetkili:** {c_data[1]} | **E-Posta:** {c_data[3]}")
    st.markdown("---")
    
    st.subheader("📋 Verilen Teklifler")
    offers = get_sales("SELECT id, model_id, total_price, offer_date, status FROM offers WHERE customer_id=? ORDER BY id DESC", (cust_id,))
    
    if offers:
        for off in offers:
            o_id, m_id, price, o_date, status = off
            try: m_name = get_factory("SELECT name FROM models WHERE id=?", (m_id,))[0][0]
            except: m_name = "Bilinmeyen Model"
            
            with st.container(border=True):
                ca, cb = st.columns([3, 1])
                ca.markdown(f"**Teklif #{o_id} - {m_name}**")
                ca.markdown(f"<small>Tarih: {o_date} | Tutar: {price:,.2f}</small>", unsafe_allow_html=True)
                
                # Durum Güncelleme
                new_stat = cb.selectbox("Durum", ["Beklemede", "Siparişe Çevir", "Reddedildi"], 
                                      index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(status), 
                                      key=f"stat_{o_id}", label_visibility="collapsed")
                if new_stat != status:
                    exec_sales("UPDATE offers SET status=? WHERE id=?", (new_stat, o_id))
                    st.rerun()

                # PROFORMA BUTONU (HER ZAMAN AKTİF)
                if st.button(f"📄 Teklif #{o_id} için Proforma Oluştur", key=f"prof_{o_id}", use_container_width=True):
                    st.session_state.proforma_offer_id = o_id
                    st.session_state.active_tab = "PROFORMA_VIEW"
                    st.rerun()
    else: st.info("Geçmiş teklif bulunamadı.")
