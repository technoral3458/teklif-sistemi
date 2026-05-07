import streamlit as st
import sqlite3
import pandas as pd

def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def show_customer_management(user_id, is_admin=False):
    if "cust_view" not in st.session_state:
        st.session_state.cust_view = "list"
    if "edit_cust_id" not in st.session_state:
        st.session_state.edit_cust_id = None
    if "detail_cust_id" not in st.session_state:
        st.session_state.detail_cust_id = None

    if st.session_state.cust_view == "list":
        show_list(user_id, is_admin)
    elif st.session_state.cust_view == "add":
        show_form(user_id, mode="add")
    elif st.session_state.cust_view == "edit":
        show_form(user_id, mode="edit", cust_id=st.session_state.edit_cust_id, is_admin=is_admin)
    elif st.session_state.cust_view == "detail":
        show_detail(user_id, st.session_state.detail_cust_id, is_admin)

def show_list(user_id, is_admin):
    c1, c2 = st.columns([4, 1])
    c1.header("👥 Müşterilerim")
    if c2.button("➕ YENİ MÜŞTERİ", type="primary", use_container_width=True):
        st.session_state.cust_view = "add"
        st.rerun()
        
    st.markdown("---")
    
    if is_admin:
        custs = get_sales("SELECT id, company_name, authorized_person, phone, email, city, country FROM customers ORDER BY id DESC")
    else:
        custs = get_sales("SELECT id, company_name, authorized_person, phone, email, city, country FROM customers WHERE user_id=? ORDER BY id DESC", (user_id,))
        
    if not custs:
        st.info("Henüz kayıtlı müşteriniz bulunmuyor.")
        return
        
    df = pd.DataFrame(custs, columns=["ID", "Firma Adı", "Yetkili", "Telefon", "E-Posta", "Şehir", "Ülke"])
    
    for index, row in df.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2], vertical_alignment="center")
            col1.markdown(f"**{row['Firma Adı']}**<br><small style='color:#64748b;'>{row['Yetkili']}</small>", unsafe_allow_html=True)
            col2.markdown(f"📞 {row['Telefon']}<br>✉️ {row['E-Posta']}", unsafe_allow_html=True)
            col3.markdown(f"🌍 {row['Ülke']} - {row['Şehir']}", unsafe_allow_html=True)
            
            with col4:
                bc1, bc2, bc3 = st.columns(3)
                if bc1.button("👁️", key=f"v_{row['ID']}", help="Detay"):
                    st.session_state.detail_cust_id = row['ID']
                    st.session_state.cust_view = "detail"
                    st.rerun()
                if bc2.button("✏️", key=f"e_{row['ID']}", help="Düzenle"):
                    st.session_state.edit_cust_id = row['ID']
                    st.session_state.cust_view = "edit"
                    st.rerun()
                if bc3.button("🗑️", key=f"d_{row['ID']}", help="Sil"):
                    exec_sales("DELETE FROM customers WHERE id=?", (row['ID'],))
                    st.rerun()

def show_detail(user_id, cust_id, is_admin):
    # 🚀 ADMİN İSE TÜM MÜŞTERİLERİN DETAYINI GÖREBİLME İZNİ (Hata Buradaydı) 🚀
    if is_admin:
        c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=?", (cust_id,))
    else:
        c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=? AND user_id=?", (cust_id, user_id))
        
    if not c_data:
        st.error("Müşteri bulunamadı!")
        if st.button("Geri Dön"):
            st.session_state.cust_view = "list"
            st.rerun()
        return
        
    c_info = c_data[0]
    
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.cust_view = "list"
        st.rerun()
        
    col_title.header(f"🏢 {c_info[0]}")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown(f"**Yetkili:** {c_info[1] or '-'}")
        st.markdown(f"**Telefon:** {c_info[2] or '-'}")
        st.markdown(f"**E-Posta:** {c_info[3] or '-'}")
    with c2.container(border=True):
        st.markdown(f"**Ülke / Şehir:** {c_info[5] or '-'} / {c_info[6] or '-'}")
        st.markdown(f"**Açık Adres:** {c_info[4] or '-'}")
        
    st.subheader("📋 Bu Müşteriye Ait Teklifler")
    offers = get_sales("SELECT id, total_price, status, offer_date FROM offers WHERE customer_id=? ORDER BY id DESC", (cust_id,))
    if offers:
        df_offers = pd.DataFrame(offers, columns=["Teklif No", "Tutar", "Durum", "Tarih"])
        df_offers["Teklif No"] = df_offers["Teklif No"].apply(lambda x: f"TR-{x}")
        st.dataframe(df_offers, use_container_width=True, hide_index=True)
    else:
        st.info("Bu müşteriye ait geçmiş teklif bulunmuyor.")

def show_form(user_id, mode="add", cust_id=None, is_admin=False):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.cust_view = "list"
        st.rerun()
        
    col_title.header("✏️ Müşteri Düzenle" if mode=="edit" else "➕ Yeni Müşteri")
    st.markdown("---")
    
    if mode == "edit" and cust_id:
        if is_admin:
            c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=?", (cust_id,))
        else:
            c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=? AND user_id=?", (cust_id, user_id))
        
        if not c_data:
            st.error("Müşteri bulunamadı!")
            return
        c_info = c_data[0]
    else:
        c_info = ["", "", "", "", "", "", ""]
        
    with st.form("cust_form"):
        c1, c2 = st.columns(2)
        f_comp = c1.text_input("Firma Adı *", value=c_info[0])
        f_auth = c2.text_input("Yetkili Kişi", value=c_info[1])
        f_phone = c1.text_input("Telefon", value=c_info[2])
        f_email = c2.text_input("E-Posta", value=c_info[3])
        f_country = c1.text_input("Ülke", value=c_info[5])
        f_city = c2.text_input("Şehir", value=c_info[6])
        f_addr = st.text_area("Açık Adres", value=c_info[4], height=100)
        
        if st.form_submit_button("💾 KAYDET", type="primary", use_container_width=True):
            if not f_comp.strip():
                st.error("Firma Adı zorunludur!")
            else:
                if mode == "add":
                    exec_sales("INSERT INTO customers (company_name, authorized_person, phone, email, address_full, country, city, user_id) VALUES (?,?,?,?,?,?,?,?)", 
                              (f_comp, f_auth, f_phone, f_email, f_addr, f_country, f_city, user_id))
                else:
                    exec_sales("UPDATE customers SET company_name=?, authorized_person=?, phone=?, email=?, address_full=?, country=?, city=? WHERE id=?", 
                              (f_comp, f_auth, f_phone, f_email, f_addr, f_country, f_city, cust_id))
                st.session_state.cust_view = "list"
                st.rerun()
