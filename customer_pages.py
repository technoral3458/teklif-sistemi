import streamlit as st
import database
import pandas as pd

def show_customer_management(user_id, is_admin=False):
    # --- MODERN STİL ŞABLONU ---
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; }
        .section-header {
            color: #1e293b;
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 5px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f1f5f9;
            border-radius: 10px 10px 0px 0px;
            padding: 10px 20px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: #0f172a;'>👥 Müşteri & Cari Yönetimi</h2>", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["🔍 Müşteri Sorgula & Düzenle", "➕ Yeni Müşteri Kaydı"])

    # ==========================================================
    # SEKME 1: LİSTELEME VE DÜZENLEME
    # ==========================================================
    with tab_list:
        # Arama Motoru
        search_q = st.text_input("Firma Adı veya Yetkili İle Ara...", placeholder="Aramak istediğiniz ismi yazın...")
        
        # Veri Çekme (Dinamik)
        if is_admin:
            query = "SELECT * FROM customers WHERE company_name LIKE ?"
            params = (f"%{search_q}%",)
        else:
            query = "SELECT * FROM customers WHERE user_id=? AND company_name LIKE ?"
            params = (user_id, f"%{search_q}%")
            
        customers = database.get_query(query, params)

        if customers:
            # --- DİNAMİK SÜTUN YÖNETİMİ (ValueError ÇÖZÜMÜ) ---
            base_columns = ["ID", "Firma Ünvanı", "Vergi Dairesi", "Vergi No", "Yetkili Kişi", "Telefon", "E-Posta", "Adres", "Bayi ID"]
            actual_col_count = len(customers[0])
            
            # Eğer DB'de daha fazla sütun varsa hata vermemesi için tamamla
            if actual_col_count > len(base_columns):
                for i in range(len(base_columns), actual_col_count):
                    base_columns.append(f"Ek Bilgi {i}")
            elif actual_col_count < len(base_columns):
                base_columns = base_columns[:actual_col_count]

            # Pandas DataFrame Oluşturma
            df = pd.DataFrame(customers, columns=base_columns)
            
            # Kullanıcının göreceği sütunları filtrele (Teknik ID'leri gizle)
            display_cols = [c for c in base_columns if c not in ["ID", "Bayi ID"]]
            st.dataframe(df[display_cols], use_container_width=True)
            
            st.markdown("---")
            st.markdown("<div class='section-header'>⚙️ Kayıt Güncelleme / Silme</div>", unsafe_allow_html=True)
            
            # Seçim kutusu için etiket oluştur
            cust_options = {f"{c[0]} - {c[1]}": c for c in customers}
            selected_key = st.selectbox("İşlem yapılacak müşteriyi seçin:", ["Seçiniz..."] + list(cust_options.keys()))
            
            if selected_key != "Seçiniz...":
                c_data = cust_options[selected_key]
                c_id = c_data[0]
                
                with st.expander(f"📝 {c_data[1]} Bilgilerini Düzenle", expanded=True):
                    with st.form(f"edit_form_{c_id}"):
                        e_col1, e_col2 = st.columns(2)
                        new_name = e_col1.text_input("Firma Tam Ünvanı", value=str(c_data[1]))
                        new_auth = e_col2.text_input("Yetkili Kişi", value=str(c_data[4]) if c_data[4] else "")
                        
                        e_col3, e_col4 = st.columns(2)
                        new_tel = e_col3.text_input("Telefon", value=str(c_data[5]) if c_data[5] else "")
                        new_mail = e_col4.text_input("E-Posta", value=str(c_data[6]) if c_data[6] else "")
                        
                        new_tax_off = e_col1.text_input("Vergi Dairesi", value=str(c_data[2]) if c_data[2] else "")
                        new_tax_no = e_col2.text_input("Vergi No", value=str(c_data[3]) if c_data[3] else "")
                        
                        new_adr = st.text_area("Açık Adres", value=str(c_data[7]) if c_data[7] else "", height=100)
                        
                        btn_update = st.form_submit_button("🔄 BİLGİLERİ GÜNCELLE", use_container_width=True)
                        
                        if btn_update:
                            success = database.exec_query(
                                "UPDATE customers SET company_name=?, tax_office=?, tax_no=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
                                (new_name, new_tax_off, new_tax_no, new_auth, new_tel, new_mail, new_adr, c_id)
                            )
                            if success:
                                st.success("Müşteri bilgileri başarıyla güncellendi!")
                                st.rerun()
                            else:
                                st.error("Güncelleme sırasında bir hata oluştu.")
                    
                    st.write("")
                    if st.button("🗑️ BU MÜŞTERİYİ SİSTEMDEN SİL", type="secondary", use_container_width=True, key=f"del_btn_{c_id}"):
                        if database.exec_query("DELETE FROM customers WHERE id=?", (c_id,)):
                            st.warning("Kayıt silindi.")
                            st.rerun()
        else:
            st.info("Henüz kayıtlı bir müşteri bulunmuyor.")

    # ==========================================================
    # SEKME 2: YENİ MÜŞTERI EKLEME
    # ==========================================================
    with tab_add:
        st.markdown("""
            <div style='background:#f8fafc; padding:20px; border-radius:15px; border:1px solid #e2e8f0; margin-bottom:20px;'>
                <h4 style='margin-top:0; color:#1e40af;'>✨ Yeni Müşteri Portföyü Oluştur</h4>
                <p style='color:#64748b; font-size:14px; margin:0;'>Müşteri bilgilerini girerek teklif sürecini hızlandırabilirsiniz.</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("new_customer_form", clear_on_submit=True):
            st.markdown("<div class='section-header'>🏢 Şirket Kimliği</div>", unsafe_allow_html=True)
            col1, col2 = st.columns([2, 1])
            comp_name = col1.text_input("Firma Ünvanı *", placeholder="Örn: Ersan Makine Mobilya Ltd. Şti.")
            auth_person = col2.text_input("Görüşülen Yetkili", placeholder="Ad Soyad")
            
            st.markdown("<div class='section-header'>📞 İletişim Bilgileri</div>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            tel = col3.text_input("Telefon Numarası", placeholder="+90 5xx ...")
            mail = col4.text_input("E-Posta Adresi", placeholder="ornek@firma.com")
            
            st.markdown("<div class='section-header'>⚖️ Ticari Detaylar</div>", unsafe_allow_html=True)
            col5, col6 = st.columns(2)
            tax_off = col5.text_input("Vergi Dairesi")
            tax_no = col6.text_input("Vergi Numarası")
            
            address = st.text_area("Sevkiyat / Fatura Adresi", placeholder="Açık adres bilgilerini buraya yazınız...", height=100)
            
            st.write("")
            submit_btn = st.form_submit_button("✅ MÜŞTERİYİ PORTFÖYE EKLE", type="primary", use_container_width=True)

            if submit_btn:
                if comp_name:
                    success = database.exec_query(
                        "INSERT INTO customers (company_name, tax_office, tax_no, contact_person, phone, email, address, user_id) VALUES (?,?,?,?,?,?,?,?)",
                        (comp_name, tax_off, tax_no, auth_person, tel, mail, address, user_id)
                    )
                    if success:
                        st.balloons()
                        st.success(f"'{comp_name}' başarıyla kaydedildi!")
                    else:
                        st.error("Kayıt sırasında bir veritabanı hatası oluştu.")
                else:
                    st.warning("Lütfen (*) ile işaretli Firma Ünvanı alanını doldurunuz.")
