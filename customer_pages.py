import streamlit as st
import sqlite3
import pandas as pd

# DOĞRUDAN SİZİN SATIŞ VERİTABANINIZA BAĞLANIR
def get_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return res
    except: return []

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def show_customer_management(user_id, is_admin=False):
    st.header(":busts_in_silhouette: Müşteri Rehberi")
    
    # Eksikse oluştur (Güvenlik)
    exec_sales("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
        company_name TEXT, contact_person TEXT, phone TEXT, email TEXT, address TEXT)""")

    # --- MÜŞTERİ LİSTESİ ---
    st.subheader("Mevcut Müşterilerim")
    
    c_query = "SELECT id, company_name, contact_person, phone, email FROM customers WHERE user_id=?" if not is_admin else "SELECT id, company_name, contact_person, phone, email FROM customers"
    c_params = (user_id,) if not is_admin else ()
    
    custs = get_sales(c_query, c_params)
    
    if custs:
        df = pd.DataFrame(custs, columns=["ID", "Firma Adı", "Yetkili", "Telefon", "E-Posta"])
        st.dataframe(df.set_index("ID"), use_container_width=True)
    else:
        st.info("Kayıtlı müşteriniz bulunmuyor. Lütfen aşağıdan ekleyin.")

    # --- YENİ MÜŞTERİ EKLEME ---
    st.markdown("---")
    with st.expander("➕ Yeni Müşteri Ekle", expanded=False):
        with st.form("new_cust"):
            c1, c2 = st.columns(2)
            c_comp = c1.text_input("Firma Adı *")
            c_cont = c2.text_input("Yetkili Kişi")
            c_pho = c1.text_input("Telefon Numarası")
            c_ema = c2.text_input("E-Posta Adresi")
            c_adr = st.text_area("Açık Adres")
            
            if st.form_submit_button("Müşteriyi Kaydet", type="primary", use_container_width=True):
                if c_comp:
                    exec_sales("INSERT INTO customers (user_id, company_name, contact_person, phone, email, address) VALUES (?,?,?,?,?,?)",
                               (user_id, c_comp, c_cont, c_pho, c_ema, c_adr))
                    st.success("Müşteri rehbere eklendi!")
                    st.rerun()
                else: 
                    st.error("Firma adı zorunludur!")
