import streamlit as st
import streamlit.components.v1 as components
import database
import datetime
import pandas as pd
import json
import os
import preview_engine
from io import BytesIO
from xhtml2pdf import pisa

def init_wizard_tables():
    database.exec_query("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in database.get_query("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
    except: pass

def create_pdf(html_content):
    """HTML içeriğini PDF byte verisine dönüştürür."""
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    # --- JİLET GİBİ SIKI TASARIM ---
    st.markdown("""
    <style>
    .block-container { padding-top: 1rem; max-width: 99%; }
    .opt-title { font-size: 12px !important; font-weight: 700; color: #1e293b; }
    .opt-price { font-size: 12px !important; font-weight: 800; color: #d97706; text-align: right; }
    </style>
    """, unsafe_allow_html=True)
    
    if is_admin:
        my_custs = database.get_query("SELECT id, company_name FROM customers ORDER BY company_name")
    else:
        my_custs = database.get_query("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name", (user_id,))
    
    if not my_custs:
        st.warning("⚠️ Önce müşteri eklemelisiniz.")
        return

    # 3 KOLONLU YERLEŞİM
    col_left, col_mid, col_right = st.columns([1.1, 1.2, 2.7], gap="small")

    engine_options_list = []
    selected_options_for_db = []
    selected_options_total = 0.0

    # ----------------------------------------------------------
    # SOL KOLON: AYARLAR
    # ----------------------------------------------------------
    with col_left:
        st.markdown("<h6 style='font-weight:800;'>⚙️ AYARLAR</h6>", unsafe_allow_html=True)
        with st.container(border=True):
            f_currency = st.selectbox("Birim", ["USD", "EUR", "RMB", "TRY"], label_visibility="collapsed")
            cats = database.get_query("SELECT name FROM categories ORDER BY id")
            cat_list = ["Tüm Kategoriler"] + [c[0] for c in cats] if cats else ["Tüm Kategoriler"]
            f_category = st.selectbox("Kategori", cat_list, label_visibility="collapsed")
            selected_cust_name = st.selectbox("Müşteri", [c[1] for c in my_custs])
            selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]

            model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=?", (f_currency,)) if f_category == "Tüm Kategoriler" else database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=? AND category=?", (f_currency, f_category))

            if not model_data:
                st.error("Model yok.")
                return

            selected_model = st.selectbox("Makine Seçin", [m[1] for m in model_data])
            m_info = [m for m in model_data if m[1] == selected_model][0]
            m_id, m_price, m_currency, comp_opts_str, m_port_disc, m_img_path, m_specs = m_info[0], m_info[2], m_info[3], m_info[4], m_info[5], m_info[6], m_info[7]
            m_qty = st.number_input("Adet", min_value=1, value=1)
            delivery_type = st.selectbox("Teslimat", ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Gümrük İşlemleri Yapılmadan Limandan Devir"])

        multiplier = 1.0
        if "Liman" in delivery_type and m_port_disc:
            multiplier = 1.0 - (float(m_port_disc) / 100.0)

    # ----------------------------------------------------------
    # ORTA KOLON: DONANIMLAR
    # ----------------------------------------------------------
    with col_mid:
        st.markdown("<h6 style='color:#1d4ed8; font-weight:800;'>🔌 DONANIMLAR</h6>", unsafe_allow_html=True)
        hide_specs = st.checkbox("Özellikleri Gizle", value=False)
        with st.container(height=550):
            if comp_opts_str:
                comp_opt_ids = [opt.strip() for opt in str(comp_opts_str).split(",") if opt.strip()]
                if comp_opt_ids:
                    placeholders = ",".join("?" * len(comp_opt_ids))
                    opts_query = f"SELECT id, opt_name, opt_price, currency, opt_desc, opt_image FROM options WHERE id IN ({placeholders}) ORDER BY sort_order ASC, id ASC"
                    compatible_options = database.get_query(opts_query, tuple(comp_opt_ids))
                    for opt in compatible_options:
                        o_id, o_name, o_price, o_curr, o_desc, o_img = opt
                        d_o_price = float(o_price) * multiplier
                        with st.container(border=True):
                            c_img, c_main = st.columns([1, 4], vertical_alignment="center")
                            with c_img:
                                if o_img and os.path.isfile(o_img):
                                    with open(o_img, "rb") as f: st.image(f.read(), use_container_width=True)
                                else: st.markdown("📷")
                            with c_main:
                                st.markdown(f"<div class='opt-title'>{o_name}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div class='opt-price'>+ {d_o_price:,.0f} {o_curr}</div>", unsafe_allow_html=True)
                                c_qty, c_chk = st.columns([2, 1])
                                with c_chk: is_sel = st.checkbox("", key=f"c_{o_id}")
                                with c_qty:
                                    if is_sel:
                                        o_qty = st.number_input("Adet", min_value=1, value=1, key=f"q_{o_id}", label_visibility="collapsed")
                                        selected_options_total += (d_o_price * o_qty)
                                        selected_options_for_db.append({"id": o_id, "qty": o_qty})
                                        engine_options_list.append({'n': o_name, 'p': d_o_price, 'q': o_qty, 'i': o_img, 'd': o_desc, 's': o_curr})

    # ----------------------------------------------------------
    # HESAPLAMALAR VE ÖNİZLEME HAZIRLIĞI
    # ----------------------------------------------------------
    sub_total = ((float(m_price) * multiplier) * m_qty) + selected_options_total
    
    with col_left:
        with st.container(border=True):
            st.caption(f"Liste: {sub_total:,.2f} {m_currency}")
            discount_pct = st.number_input("İskonto %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            final_price = sub_total * (1 - (discount_pct / 100.0))
            agreed_price = st.number_input("Net Fiyat", min_value=0.0, value=final_price, step=100.0)

        conditions_data = {
            "machine_qty": m_qty, "discount_pct": discount_pct, "subtotal_calculated": sub_total,
            "agreed_price": agreed_price, "hide_specs": hide_specs, "delivery_type": delivery_type
        }

        # ÖNİZLEME HTML OLUŞTURMA
        html_preview = preview_engine.PreviewEngine.generate_html(
            customer=selected_cust_name, model=selected_model, 
            base_price=float(m_price) * multiplier, machine_img=m_img_path,
            specs=m_specs, selected_options=engine_options_list, 
            conditions=conditions_data, delivery_type=delivery_type
        )

        # KAYIT VE PDF BUTONLARI
        st.write("")
        if st.button("💾 TEKLİFİ KAYDET", use_container_width=True, type="primary"):
            try:
                tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                cond_str = json.dumps(conditions_data)
                database.exec_query("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date, conditions) VALUES (?,?,?,?,?,?)",
                                   (selected_cust_id, m_id, agreed_price, user_id, tarih, cond_str))
                res_id = database.get_query("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
                if res_id and selected_options_for_db:
                    new_id = res_id[0][0]
                    for item in selected_options_for_db:
                        database.exec_query("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", (new_id, item["id"], item["qty"]))
                st.success("Sisteme Kaydedildi!")
                st.balloons()
            except Exception as e: st.error(f"Kayıt Hatası: {e}")

        # PDF İNDİRME BUTONU
        pdf_data = create_pdf(html_preview)
        if pdf_data:
            st.download_button(
                label="📄 PDF OLARAK İNDİR",
                data=pdf_data,
                file_name=f"Ersan_Makine_Teklif_{selected_cust_name.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # SAĞ KOLON: ÖNİZLEME
    with col_right:
        st.markdown("<h6 style='font-weight:800;'>📄 CANLI ÖNİZLEME</h6>", unsafe_allow_html=True)
        components.html(html_preview, height=800, scrolling=True)
