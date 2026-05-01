import streamlit as st
import database
import datetime
import pandas as pd
import json

def init_wizard_tables():
    # Teklifler ve detayları için gerekli tabloları kontrol et
    database.exec_query("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in database.get_query("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
        if "notes" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN notes TEXT DEFAULT ''")
    except: pass

def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    st.markdown("<h2 style='color: #0f172a;'>📄 Profesyonel Teklif Sihirbazı</h2>", unsafe_allow_html=True)
    
    # Müşterileri Çek
    if is_admin:
        my_custs = database.get_query("SELECT id, company_name FROM customers ORDER BY company_name")
    else:
        my_custs = database.get_query("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name", (user_id,))
    
    if not my_custs:
        st.warning("⚠️ Teklif hazırlamak için önce 'Müşterilerim' sekmesinden bir müşteri eklemelisiniz.")
        return

    # ==========================================================
    # 1. ADIM: FİLTRELEME VE MAKİNE SEÇİMİ
    # ==========================================================
    st.markdown("### 1. Müşteri ve Makine Seçimi")
    with st.container(border=True):
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            selected_cust_name = st.selectbox("👤 Müşteri Seçin", [c[1] for c in my_custs])
            selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]
        with col_f2:
            f_currency = st.selectbox("💵 Para Birimi Filtresi", ["USD", "EUR", "RMB", "TRY"])
        with col_f3:
            cats = database.get_query("SELECT name FROM categories ORDER BY id")
            cat_list = ["Tüm Kategoriler"] + [c[0] for c in cats] if cats else ["Tüm Kategoriler"]
            f_category = st.selectbox("🗂️ Kategori Filtresi", cat_list)

        # Filtrelere göre makineleri çek
        if f_category == "Tüm Kategoriler":
            model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount FROM models WHERE currency=?", (f_currency,))
        else:
            model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount FROM models WHERE currency=? AND category=?", (f_currency, f_category))

        if not model_data:
            st.error("Bu filtrelere uygun makine modeli bulunamadı.")
            return

        selected_model = st.selectbox("🤖 Makine Modeli", [m[1] for m in model_data])
        m_info = [m for m in model_data if m[1] == selected_model][0]
        m_id, m_price, m_currency, comp_opts_str, m_port_disc = m_info[0], m_info[2], m_info[3], m_info[4], m_info[5]

        col_q1, col_q2 = st.columns(2)
        with col_q1:
            m_qty = st.number_input("Makine Adedi", min_value=1, value=1)
        with col_q2:
            delivery_type = st.selectbox("Teslimat Şekli", ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Gümrük İşlemleri Yapılmadan Limandan Devir"])

    # Teslimat Şekline Göre Baz Fiyat Çarpanı
    multiplier = 1.0
    if delivery_type == "Gümrük İşlemleri Yapılmadan Limandan Devir" and m_port_disc:
        multiplier = 1.0 - (float(m_port_disc) / 100.0)

    # ==========================================================
    # 2. ADIM: UYUMLU EKSTRA DONANIMLAR (OPSİYONLAR)
    # ==========================================================
    st.markdown("### 2. Uyumlu Ekstra Donanımlar")
    selected_options_total = 0.0
    selected_options_list = []

    with st.container(border=True):
        if comp_opts_str:
            comp_opt_ids = [opt.strip() for opt in str(comp_opts_str).split(",") if opt.strip()]
            if comp_opt_ids:
                placeholders = ",".join("?" * len(comp_opt_ids))
                opts_query = f"SELECT id, opt_name, opt_price, currency, opt_desc FROM options WHERE id IN ({placeholders})"
                compatible_options = database.get_query(opts_query, tuple(comp_opt_ids))
                
                if compatible_options:
                    for opt in compatible_options:
                        o_id, o_name, o_price, o_curr, o_desc = opt
                        discounted_o_price = float(o_price) * multiplier
                        
                        col_opt1, col_opt2 = st.columns([4, 1])
                        with col_opt1:
                            is_selected = st.checkbox(f"**{o_name}** (+{discounted_o_price:,.2f} {o_curr}) \n\n _{o_desc}_", key=f"opt_{o_id}")
                        with col_opt2:
                            if is_selected:
                                o_qty = st.number_input("Adet", min_value=1, value=1, key=f"qty_{o_id}")
                                selected_options_total += (discounted_o_price * o_qty)
                                selected_options_list.append({"id": o_id, "qty": o_qty, "name": o_name, "price": discounted_o_price, "total": discounted_o_price * o_qty})
                else:
                    st.info("Bu makine için tanımlanmış donanım bulunmuyor.")
            else:
                st.info("Bu makine için uyumlu donanım tanımlanmamış.")
        else:
            st.info("Bu makine için uyumlu donanım tanımlanmamış.")

    # ==========================================================
    # 3. ADIM: FİYAT VE İSKONTO YÖNETİMİ
    # ==========================================================
    st.markdown("### 3. Fiyatlandırma ve İskonto")
    
    # Ara Toplam Hesaplama
    base_machine_total = (float(m_price) * multiplier) * m_qty
    sub_total = base_machine_total + selected_options_total

    with st.container(border=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.metric("Sistem Ara Toplamı", f"{sub_total:,.2f} {m_currency}")
        with col_p2:
            discount_pct = st.number_input("Özel İskonto Oranı (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
        with col_p3:
            # İskontolu fiyat
            discounted_price = sub_total * (1 - (discount_pct / 100.0))
            agreed_price = st.number_input("Anlaşılan Net Fiyat (Manuel Değiştirilebilir)", min_value=0.0, value=discounted_price, step=100.0)

    # Teklif Şartları Verisi
    conditions_data = {
        "delivery_type": delivery_type,
        "machine_qty": m_qty,
        "discount_pct": discount_pct,
        "agreed_price": agreed_price,
        "sub_total": sub_total
    }

    # ==========================================================
    # 4. ADIM: CANLI ÖNİZLEME VE KAYDETME
    # ==========================================================
    st.markdown("### 4. Teklif Özeti ve Kayıt")
    
    # HTML Önizleme Kartı (Sizin PyQt preview_engine mantığının web hali)
    preview_html = f"""
    <div style="background-color: white; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; font-family: Arial, sans-serif; color: #333;">
        <h3 style="color: #0f172a; margin-top: 0; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">ERSAN MAKİNE TEKLİF FORMU</h3>
        <p><strong>Müşteri:</strong> {selected_cust_name}</p>
        <p><strong>Makine Modeli:</strong> {selected_model} (x{m_qty} Adet)</p>
        <p><strong>Teslimat Şekli:</strong> {delivery_type}</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="background-color: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                <th style="padding: 10px; text-align: left;">Açıklama</th>
                <th style="padding: 10px; text-align: center;">Adet</th>
                <th style="padding: 10px; text-align: right;">Tutar</th>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{selected_model} (Standart Donanım)</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{m_qty}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{base_machine_total:,.2f} {m_currency}</td>
            </tr>
    """
    
    # Seçili Opsiyonları Tabloya Ekle
    for opt in selected_options_list:
        preview_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #10b981;">+ {opt['name']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{opt['qty']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{opt['total']:,.2f} {m_currency}</td>
            </tr>
        """
        
    preview_html += f"""
        </table>
        
        <div style="margin-top: 20px; text-align: right; font-size: 16px;">
            <p>Sistem Ara Toplamı: <del style="color: #ef4444;">{sub_total:,.2f} {m_currency}</del></p>
            <p style="font-size: 24px; font-weight: bold; color: #10b981;">Genel Toplam (Net): {agreed_price:,.2f} {m_currency}</p>
        </div>
    </div>
    """
    
    st.markdown(preview_html, unsafe_allow_html=True)
    st.write("")

    # Kayıt Butonu
    if st.button("💾 TEKLİFİ SİSTEME KAYDET", use_container_width=True, type="primary"):
        cond_str = json.dumps(conditions_data)
        tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        try:
            # Ana Teklifi Kaydet
            database.exec_query("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date, conditions) VALUES (?,?,?,?,?,?)",
                               (selected_cust_id, m_id, agreed_price, user_id, tarih, cond_str))
            
            # Opsiyonları Kaydet
            last_offer = database.get_query("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
            if last_offer and selected_options_list:
                offer_id = last_offer[0][0]
                for s_opt in selected_options_list:
                    database.exec_query("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", (offer_id, s_opt["id"], s_opt["qty"]))
            
            st.balloons()
            st.success("Tebrikler! Teklif başarıyla arşivlendi. 'Geçmiş Tekliflerim' sekmesinden görüntüleyebilirsiniz.")
        except Exception as e:
            st.error(f"Kayıt Hatası: {e}")
