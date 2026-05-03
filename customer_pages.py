import streamlit as st
import database
import pandas as pd

def show_customer_management(user_id, is_admin=False):
    # --- MODERN STİL ŞABLONU ---
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; }
        .customer-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            border-left: 5px solid #3b82f6;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section-header {
            color: #1e293b;
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
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
        search_q = st.text_input("Firma Adı veya Yetkili İle Ara...", placeholder="Örn: Ersan Makine")
        
        # Veri Çekme
        if is_admin:
            query = "SELECT * FROM customers WHERE company_name LIKE ?"
            params = (f"%{search_q}%",)
        else:
            query = "SELECT * FROM customers WHERE user_id=? AND company_name LIKE ?"
            params = (user_id, f"%{search_q}%")
            
        customers = database.get_query(query, params)

        if customers:
            # Pandas ile şık tablo gösterimi
            df = pd.DataFrame(customers, columns=["ID", "Firma Ünvanı", "Vergi Dairesi", "Vergi No", "Yetkili Kişi", "Telefon", "E-Posta", "Adres", "Bayi ID"])
            st.dataframe(df.drop(columns=["ID", "Bayi ID"]), use_container_width=True)
            
            st.markdown("---")
            st.markdown("<div class='section-header'>⚙️ Kayıt Güncelleme / Silme</div>", unsafe_allow_html=True)
            
            selected_cust = st.selectbox("İşlem yapılacak müşteriyi seçin:", [f"{c[0]} - {c[1]}" for c in customers])
            
            if selected_cust:
                c_id = int(selected_cust.split(" - ")[0])
                c_data = [c for c in customers if c[0] == c_id][0]
                
                with st.expander(f"📝 {c_data[1]} Bilgilerini Düzenle", expanded=True):
                    with st.form(f"edit_form_{c_id}"):
                        e_col1, e_col2 = st.columns(2)
                        new_name = e_col1.text_input("Firma Tam Ünvanı", value=c_data[1])
                        new_auth = e_col2.text_input("Yetkili Kişi", value=c_data[4])
                        
                        e_col3, e_col4 = st.columns(2)
                        new_tel = e_col3.text_input("Telefon", value=c_data[5])
                        new_mail = e_col4.text_input("E-Posta", value=c_data[6])
                        
                        new_adr = st.text_area("Açık Adres", value=c_data[7], height=100)
                        
                        btn_update = st.form_submit_button("🔄 BİLGİLERİ GÜNCELLE", use_container_width=True)
                        
                        if btn_update:
                            database.exec_query(
                                "UPDATE customers SET company_name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
                                (new_name, new_auth, new_tel, new_mail, new_adr, c_id)
                            )
                            st.success("Müşteri bilgileri başarıyla güncellendi!")
                            st.rerun()
                    
                    if st.button("🗑️ BU MÜŞTERİYİ SİSTEMDEN SİL", type="secondary", use_container_width=True):
                        database.exec_query("DELETE FROM customers WHERE id=?", (c_id,))
                        st.error("Kayıt silindi.")
                        st.rerun()
        else:
            st.info("Henüz kayıtlı bir müşteri bulunmuyor veya arama kriterine uygun sonuç yok.")

    # ==========================================================
    # SEKME 2: YENİ MÜŞTERİ EKLEME (MODERN FORM)
    # ==========================================================
    with tab_add:
        st.markdown("""
            <div style='background:#f8fafc; padding:20px; border-radius:15px; border:1px solid #e2e8f0;'>
                <h4 style='margin-top:0; color:#1e40af;'>✨ Yeni Müşteri Portföyü Oluştur</h4>
                <p style='color:#64748b; font-size:14px;'>Müşteri bilgilerini eksiksiz girmek, teklif formlarınızın profesyonel görünmesini sağlar.</p>
            </div>
        """, unsafe_allow_html=True)
        st.write("")

        with st.form("new_customer_form", clear_on_submit=True):
            # 1. GRUP: ŞİRKET KİMLİĞİ
            st.markdown("<div class='section-header'>🏢 Şirket Kimliği</div>", unsafe_allow_html=True)
            col1, col2 = st.columns([2, 1])
            comp_name = col1.text_input("Firma Ünvanı *", placeholder="Örn: Ersan Makine Mobilya Ltd. Şti.")
            auth_person = col2.text_input("Görüşülen Yetkili", placeholder="Ad Soyad")
            
            # 2. GRUP: İLETİŞİM
            st.markdown("<div class='section-header'>📞 İletişim Bilgileri</div>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            tel = col3.text_input("Telefon Numarası", placeholder="+90 5xx ...")
            mail = col4.text_input("E-Posta Adresi", placeholder="ornek@firma.com")
            
            # 3. GRUP: VERGİ VE ADRES
            st.markdown("<div class='section-header'>⚖️ Ticari Detaylar</div>", unsafe_allow_html=True)
            col5, col6 = st.columns(2)
            tax_off = col5.text_input("Vergi Dairesi")
            tax_no = col6.text_input("Vergi Numarası")
            
            address = st.text_area("Sevkiyat / Fatura Adresi", placeholder="Mahalle, Sokak, No, İlçe/İl", height=100)
            
            st.markdown("---")
            submit_btn = st.form_submit_button("✅ MÜŞTERİYİ PORTFÖYE EKLE", type="primary", use_container_width=True)

            if submit_btn:
                if comp_name:
                    try:
                        database.exec_query(
                            "INSERT INTO customers (company_name, tax_office, tax_no, contact_person, phone, email, address, user_id) VALUES (?,?,?,?,?,?,?,?)",
                            (comp_name, tax_off, tax_no, auth_person, tel, mail, address, user_id)
                        )
                        st.balloons()
                        st.success(f"'{comp_name}' başarıyla kaydedildi! Artık bu müşteriye teklif hazırlayabilirsiniz.")
                    except Exception as e:
                        st.error(f"Kayıt sırasında bir hata oluştu: {e}")
                else:
                    st.warning("Lütfen en azından 'Firma Ünvanı' alanını doldurunuz.")
