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
    # Üst Başlık ve Ekleme Butonu
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    c1.header("👥 Müşteri Yönetimi (CRM)")
    if c2.button("➕ YENİ MÜŞTERİ", type="primary", use_container_width=True):
        st.session_state.cust_view = "add"
        st.rerun()
        
    st.markdown("---")
    
    # Verileri Çekme
    if is_admin:
        custs = get_sales("SELECT id, company_name, authorized_person, phone, email, city, country FROM customers ORDER BY id DESC")
    else:
        custs = get_sales("SELECT id, company_name, authorized_person, phone, email, city, country FROM customers WHERE user_id=? ORDER BY id DESC", (user_id,))
        
    if not custs:
        st.info("Sistemde henüz kayıtlı müşteriniz bulunmuyor. Sağ üstten yeni müşteri ekleyebilirsiniz.")
        return
        
    df = pd.DataFrame(custs, columns=["ID", "Firma Adı", "Yetkili", "Telefon", "E-Posta", "Şehir", "Ülke"])
    
    # 🚀 DİNAMİK ARAMA VE İSTATİSTİK BÖLÜMÜ 🚀
    col_stat, col_search = st.columns([1, 3], vertical_alignment="center")
    col_stat.metric(label="Toplam Müşteri", value=len(df))
    search_term = col_search.text_input("🔍 Müşteri Ara (Firma Adı veya Yetkili ismine göre hızlı arama yapın...)", "")
    
    # Filtreleme İşlemi
    if search_term:
        df = df[df['Firma Adı'].str.contains(search_term, case=False, na=False) | 
                df['Yetkili'].str.contains(search_term, case=False, na=False)]
        if df.empty:
            st.warning(f"'{search_term}' aramasına uygun müşteri bulunamadı.")
            return

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # 🎨 ŞIK VE DÜZENLİ KART TASARIMI 🎨
    for index, row in df.iterrows():
        # Veri Temizliği (Boş verileri şık göster)
        comp = row['Firma Adı'] if row['Firma Adı'] else "İsimsiz Firma"
        auth = row['Yetkili'] if row['Yetkili'] else "Yetkili Belirtilmedi"
        phone = row['Telefon'] if row['Telefon'] else "-"
        email = row['E-Posta'] if row['E-Posta'] else "-"
        country = row['Ülke'] if row['Ülke'] else "Bilinmiyor"
        city = row['Şehir'] if row['Şehir'] else "-"

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2.5, 2, 1.5], vertical_alignment="center")
            
            # Firma ve Yetkili Sütunu
            col1.markdown(f"""
                <div style='line-height:1.4;'>
                    <div style='font-size:16px; font-weight:800; color:#0f172a;'>🏢 {comp}</div>
                    <div style='font-size:13px; font-weight:600; color:#64748b; margin-top:4px;'>👤 {auth}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # İletişim Sütunu
            col2.markdown(f"""
                <div style='line-height:1.6; font-size:13px; color:#475569;'>
                    <b>📞 Tel:</b> {phone}<br>
                    <b>✉️ Mail:</b> {email}
                </div>
            """, unsafe_allow_html=True)
            
            # Konum Sütunu
            col3.markdown(f"""
                <div style='line-height:1.4; text-align:center; padding:8px; background:#f8fafc; border-radius:8px;'>
                    <div style='font-size:18px;'>🌍</div>
                    <div style='font-size:13px; font-weight:700; color:#334155; margin-top:2px;'>{country}</div>
                    <div style='font-size:11px; color:#94a3b8;'>{city}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Aksiyon Butonları Sütunu
            with col4:
                bc1, bc2, bc3 = st.columns(3)
                if bc1.button("👁️", key=f"v_{row['ID']}", help="Müşteri Detayına Git"):
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
    # ADMİN İSE TÜM MÜŞTERİLERİN DETAYINI GÖREBİLME İZNİ
    if is_admin:
        c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=?", (cust_id,))
    else:
        c_data = get_sales("SELECT company_name, authorized_person, phone, email, address_full, country, city FROM customers WHERE id=? AND user_id=?", (cust_id, user_id))
        
    if not c_data:
        st.error("Müşteri bulunamadı!")
        if st.button("🔙 Listeye Dön", type="primary"):
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
    
    # 🎨 ŞIK PROFİL KARTI
    st.markdown("<div style='font-size:14px; font-weight:800; color:#2563eb; margin-bottom:10px;'>MÜŞTERİ BİLGİ KARTI</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold;'>YETKİLİ KİŞİ</div><div style='font-size:16px; font-weight:700; color:#0f172a; margin-bottom:15px;'>{c_info[1] or '-'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold;'>TELEFON</div><div style='font-size:15px; color:#1e293b; margin-bottom:15px;'>📞 {c_info[2] or '-'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold;'>E-POSTA</div><div style='font-size:15px; color:#1e293b;'>✉️ {c_info[3] or '-'}</div>", unsafe_allow_html=True)
    with c2.container(border=True):
        st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold;'>LOKASYON</div><div style='font-size:15px; font-weight:700; color:#0f172a; margin-bottom:15px;'>🌍 {c_info[5] or '-'} / {c_info[6] or '-'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold;'>AÇIK ADRES</div><div style='font-size:14px; color:#334155; line-height:1.5;'>{c_info[4] or 'Adres girilmemiş.'}</div>", unsafe_allow_html=True)
        
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:14px; font-weight:800; color:#ea580c; margin-bottom:10px;'>📋 BU MÜŞTERİYE AİT TEKLİFLER</div>", unsafe_allow_html=True)
    
    offers = get_sales("SELECT id, total_price, status, offer_date FROM offers WHERE customer_id=? ORDER BY id DESC", (cust_id,))
    if offers:
        df_offers = pd.DataFrame(offers, columns=["Teklif No", "Tutar (USD/EUR/TL)", "Durum", "Tarih"])
        df_offers["Teklif No"] = df_offers["Teklif No"].apply(lambda x: f"TR-{x}")
        
        # Duruma göre renkli tablo
        st.dataframe(df_offers, use_container_width=True, hide_index=True)
    else:
        st.info("Bu müşteriye ait geçmiş teklif veya sipariş kaydı bulunmuyor.")

def show_form(user_id, mode="add", cust_id=None, is_admin=False):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.cust_view = "list"
        st.rerun()
        
    col_title.header("✏️ Müşteri Kartını Düzenle" if mode=="edit" else "➕ Sisteme Yeni Müşteri Ekle")
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
        st.markdown("<div style='font-size:14px; font-weight:800; color:#2563eb; margin-bottom:15px;'>MÜŞTERİ İLETİŞİM BİLGİLERİ</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        f_comp = c1.text_input("Firma Adı (Zorunlu) *", value=c_info[0], placeholder="Örn: Ersan Makine A.Ş.")
        f_auth = c2.text_input("Yekili Kişi Adı Soyadı", value=c_info[1], placeholder="Örn: Sefa Bey")
        f_phone = c1.text_input("Telefon Numarası", value=c_info[2], placeholder="+90 5XX XXX XX XX")
        f_email = c2.text_input("E-Posta Adresi", value=c_info[3], placeholder="info@firma.com")
        
        st.markdown("<div style='font-size:14px; font-weight:800; color:#2563eb; margin-top:20px; margin-bottom:15px;'>LOKASYON BİLGİLERİ</div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        f_country = c3.text_input("Ülke", value=c_info[5], placeholder="Örn: Türkiye")
        f_city = c4.text_input("Şehir", value=c_info[6], placeholder="Örn: İstanbul")
        f_addr = st.text_area("Açık Adres", value=c_info[4], height=100, placeholder="Faturada görünecek tam adres...")
        
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        if st.form_submit_button("💾 BİLGİLERİ KAYDET", type="primary", use_container_width=True):
            if not f_comp.strip():
                st.error("Lütfen Firma Adını giriniz. Bu alan zorunludur!")
            else:
                if mode == "add":
                    exec_sales("INSERT INTO customers (company_name, authorized_person, phone, email, address_full, country, city, user_id) VALUES (?,?,?,?,?,?,?,?)", 
                              (f_comp.strip(), f_auth.strip(), f_phone.strip(), f_email.strip(), f_addr.strip(), f_country.strip(), f_city.strip(), user_id))
                    st.success("Müşteri başarıyla eklendi!")
                else:
                    exec_sales("UPDATE customers SET company_name=?, authorized_person=?, phone=?, email=?, address_full=?, country=?, city=? WHERE id=?", 
                              (f_comp.strip(), f_auth.strip(), f_phone.strip(), f_email.strip(), f_addr.strip(), f_country.strip(), f_city.strip(), cust_id))
                    st.success("Müşteri bilgileri güncellendi!")
                st.session_state.cust_view = "list"
                st.rerun()
