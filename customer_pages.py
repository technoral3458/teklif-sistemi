import streamlit as st
import database
import pandas as pd

def init_customer_table():
    # Masaüstündeki eksik olabilecek sütunları web veritabanına otomatik ekler (Güvenlik için)
    try:
        cols = [c[1] for c in database.get_query("PRAGMA table_info(customers)")]
        if "contact_person" not in cols: database.exec_query("ALTER TABLE customers ADD COLUMN contact_person TEXT;")
        if "description" not in cols: database.exec_query("ALTER TABLE customers ADD COLUMN description TEXT;")
    except:
        pass

def show_customer_management(user_id, is_admin=False):
    init_customer_table()
    
    st.markdown("<h2 style='color: #1e293b;'>👥 Müşteri Cari Kart Yönetimi</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Müşteri Listesi & Düzenle", "➕ Yeni Müşteri Ekle"])

    # Verileri Çekme (Yöneticiyse tümü, bayiyse sadece kendi müşterileri)
    if is_admin:
        query = "SELECT id, company_name, contact_person, phone, email, tax_office, tax_no, address, description FROM customers ORDER BY id DESC"
        params = ()
    else:
        query = "SELECT id, company_name, contact_person, phone, email, tax_office, tax_no, address, description FROM customers WHERE user_id = ? ORDER BY id DESC"
        params = (user_id,)
    
    raw_data = database.get_query(query, params)
    df = pd.DataFrame(raw_data, columns=["ID", "Firma Adı", "Yetkili", "Telefon", "E-Posta", "Vergi Dairesi", "Vergi No", "Adres", "Açıklama"])

    # ==========================================
    # 1. SEKME: MÜŞTERİ LİSTESİ VE DÜZENLEME
    # ==========================================
    with tab1:
        # Arama Çubuğu (Masaüstündeki gibi)
        search_term = st.text_input("🔍 Müşteri Ara (Firma Adı, Yetkili veya Telefon)").lower()
        
        if not df.empty:
            filtered_df = df
            if search_term:
                filtered_df = df[
                    df["Firma Adı"].str.lower().str.contains(search_term, na=False) | 
                    df["Yetkili"].str.lower().str.contains(search_term, na=False) |
                    df["Telefon"].str.lower().str.contains(search_term, na=False)
                ]
            
            # ID Sütununu gizleyerek tabloyu göster
            st.dataframe(filtered_df.drop(columns=["ID"]), use_container_width=True)
            
            st.markdown("---")
            st.subheader("📝 Seçili Müşteriyi Düzenle / Sil")
            
            # İşlem yapılacak müşteriyi seç
            cust_options = [f"{row['ID']} - {row['Firma Adı']}" for idx, row in filtered_df.iterrows()]
            selected_cust_str = st.selectbox("İşlem yapılacak müşteriyi seçin:", ["Seçiniz..."] + cust_options)
            
            if selected_cust_str != "Seçiniz...":
                selected_id = int(selected_cust_str.split(" - ")[0])
                cust_info = df[df["ID"] == selected_id].iloc[0]
                
                with st.form("edit_cust_form"):
                    e_name = st.text_input("Firma Unvanı *", value=cust_info["Firma Adı"])
                    e_contact = st.text_input("Yetkili Kişi", value=cust_info["Yetkili"] if cust_info["Yetkili"] else "")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        e_phone = st.text_input("Telefon No", value=cust_info["Telefon"] if cust_info["Telefon"] else "")
                        e_tax_off = st.text_input("Vergi Dairesi", value=cust_info["Vergi Dairesi"] if cust_info["Vergi Dairesi"] else "")
                    with col2:
                        e_email = st.text_input("E-Posta Adresi", value=cust_info["E-Posta"] if cust_info["E-Posta"] else "")
                        e_tax_no = st.text_input("Vergi Numarası", value=cust_info["Vergi No"] if cust_info["Vergi No"] else "")
                    
                    e_addr = st.text_area("Açık Adres", value=cust_info["Adres"] if cust_info["Adres"] else "")
                    e_desc = st.text_area("Açıklama", value=cust_info["Açıklama"] if cust_info["Açıklama"] else "")
                    
                    updated = st.form_submit_button("🔄 BİLGİLERİ GÜNCELLE", use_container_width=True)
                    
                if updated:
                    database.exec_query("""
                        UPDATE customers 
                        SET company_name=?, contact_person=?, phone=?, email=?, tax_office=?, tax_no=?, address=?, description=?
                        WHERE id=?""", 
                        (e_name, e_contact, e_phone, e_email, e_tax_off, e_tax_no, e_addr, e_desc, selected_id))
                    st.success("Müşteri bilgileri başarıyla güncellendi!")
                    st.rerun()
                
                # SİLME BUTONU (Formun dışında kırmızı buton)
                st.write("")
                if st.button("🗑️ BU MÜŞTERİYİ SİL", use_container_width=True):
                    database.exec_query("DELETE FROM customers WHERE id=?", (selected_id,))
                    st.error("Müşteri kaydı sistemden silindi!")
                    st.rerun()
        else:
            st.info("Sistemde henüz kayıtlı müşteri bulunmamaktadır.")

    # ==========================================
    # 2. SEKME: YENİ MÜŞTERİ EKLE (Masaüstü Formu)
    # ==========================================
    with tab2:
        st.subheader("➕ Yeni Müşteri Kaydı")
        with st.form("new_cust_form"):
            c_name = st.text_input("Firma Unvanı * (Zorunlu)")
            c_contact = st.text_input("Yetkili Kişi")
            
            col1, col2 = st.columns(2)
            with col1:
                c_phone = st.text_input("Telefon No")
                c_tax_off = st.text_input("Vergi Dairesi")
            with col2:
                c_email = st.text_input("E-Posta Adresi")
                c_tax_no = st.text_input("Vergi Numarası")
            
            c_addr = st.text_area("Açık Adres")
            c_desc = st.text_area("Açıklama")
            
            submitted = st.form_submit_button("💾 MÜŞTERİYİ KAYDET", use_container_width=True)
            
            if submitted:
                if c_name.strip():
                    database.exec_query(
                        "INSERT INTO customers (company_name, contact_person, phone, email, tax_office, tax_no, address, description, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
                        (c_name, c_contact, c_phone, c_email, c_tax_off, c_tax_no, c_addr, c_desc, user_id)
                    )
                    st.balloons()
                    st.success(f"'{c_name}' başarıyla kaydedildi!")
                    st.rerun()
                else:
                    st.error("Lütfen Firma Unvanı alanını boş bırakmayınız!")
