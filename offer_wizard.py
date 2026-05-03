import streamlit as st
import streamlit.components.v1 as components
import database
import datetime
import pandas as pd
import json
import os
import base64

def init_wizard_tables():
    database.exec_query("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in database.get_query("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: database.exec_query("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
    except: pass

# =====================================================================
# GÖMÜLÜ ÖNİZLEME MOTORU (Başka dosyaya ihtiyaç duymaz)
# =====================================================================
def get_image_base64(img_path):
    if not img_path or not os.path.exists(img_path): return ""
    try:
        with open(img_path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(img_path)[1].lower().replace('.', '')
        return f"data:image/{ext if ext else 'png'};base64,{b64}"
    except: return ""

def generate_embedded_html(customer, model, base_price, machine_img, specs, selected_options, conditions, delivery_type, m_currency):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    m_qty = conditions.get("machine_qty", 1)
    agreed_price = conditions.get("agreed_price", 0)
    
    m_img_b64 = get_image_base64(machine_img)

    css = """
        body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #333; background: #fff; margin:0; padding:15px;}
        .header { border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-bottom: 20px; }
        .section-title { background: #1e293b; color: white; padding: 6px 12px; font-weight: bold; margin-top: 20px; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 10px; text-align: left; vertical-align: middle; }
        th { color: #475569; }
        .price-box { background: #f8fafc; border-left: 5px solid #e67e22; padding: 15px; text-align: right; margin-top: 20px; border-radius: 6px; }
        .total-price { font-size: 32px; font-weight: 900; color: #e67e22; margin-top:5px; }
    """

    html = f"""
    <html><head><style>{css}</style></head><body>
        <div class="header">
            <table style="border:none; margin:0; padding:0;">
                <tr>
                    <td style="border:none; padding:0;"><h2 style="margin:0; color:#0f172a;">ERSAN MAKİNE</h2></td>
                    <td align="right" style="border:none; padding:0; color:#64748b;">Tarih: {tarih}<br>Teklif No: TR-{datetime.datetime.now().strftime("%y%m%d")}</td>
                </tr>
            </table>
        </div>

        <div style="text-align:center; padding: 20px 0;">
            <img src="{m_img_b64}" style="max-height:280px; object-fit:contain;"><br>
            <h2 style="margin:15px 0 5px 0; color:#0f172a;">MODEL: {model}</h2>
            <p style="font-size:16px; color:#475569; margin:0;">Sayın Yetkili: <b style="color:#0f172a;">{customer}</b></p>
        </div>

        <div class="section-title">🔍 MAKİNE ÖZELLİKLERİ VE DONANIMLAR</div>
        <table>
            <tr style="background:#f8fafc;">
                <th>Görsel / Açıklama</th>
                <th style="text-align:center;">Adet</th>
                <th style="text-align:right;">Tutar</th>
            </tr>
            <tr>
                <td><b style="font-size:14px; color:#0f172a;">{model} (Standart Donanım)</b></td>
                <td style="text-align:center; font-weight:bold;">{m_qty}</td>
                <td style="text-align:right; font-weight:bold;">{base_price*m_qty:,.2f} {m_currency}</td>
            </tr>
    """
    
    for opt in selected_options:
        opt_img = get_image_base64(opt['i'])
        img_tag = f'<img src="{opt_img}" style="max-width:50px; max-height:50px; border-radius:4px; margin-right:10px; float:left; object-fit:cover;">' if opt_img else ''
        html += f"""
            <tr>
                <td>
                    {img_tag}
                    <b style="color:#10b981; font-size:14px;">+ {opt['n']}</b><br>
                    <span style="font-size:11px; color:#64748b;">{opt['d']}</span>
                </td>
                <td style="text-align:center; font-weight:bold;">{opt['q']}</td>
                <td style="text-align:right; font-weight:bold; color:#e67e22;">{(opt['p']*opt['q']):,.2f} {m_currency}</td>
            </tr>
        """

    html += f"""
        </table>

        <div class="price-box">
            <div style="font-size:14px; color:#64748b; font-weight:bold;">Teslimat: <span style="color:#e67e22;">{delivery_type}</span></div>
            <div style="margin-top:15px; font-size:16px; font-weight:bold; color:#0f172a;">TOPLAM NET TUTAR (KDV Hariç)</div>
            <div class="total-price">{agreed_price:,.2f} {m_currency}</div>
        </div>
        
        <div style="margin-top:40px; font-size:11px; color:#94a3b8; text-align:center; border-top:1px solid #f1f5f9; padding-top:10px;">
            Ersan Makine San. ve Tic. Ltd. Şti. | www.ersanmakina.net
        </div>
    </body></html>
    """
    return html

# =====================================================================
# ANA TEKLİF SİHİRBAZI FONKSİYONU
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    st.markdown("""
    <style>
    .block-container { padding-top: 1rem; max-width: 99%; }
    .opt-title { font-size: 12px !important; font-weight: 700; color: #1e293b; line-height: 1.2; }
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

    col_left, col_mid, col_right = st.columns([1.1, 1.2, 2.7], gap="small")

    engine_options_list = []
    selected_options_for_db = []
    selected_options_total = 0.0

    # ----------------------------------------------------------
    # SOL KOLON: AYARLAR
    # ----------------------------------------------------------
    with col_left:
        st.markdown("<h6 style='font-weight:800; margin-bottom:0px;'>⚙️ AYARLAR</h6>", unsafe_allow_html=True)
        with st.container(border=True):
            f_currency = st.selectbox("Birim", ["USD", "EUR", "RMB", "TRY"], label_visibility="collapsed")
            cats = database.get_query("SELECT name FROM categories ORDER BY id")
            cat_list = ["Tüm Kategoriler"] + [c[0] for c in cats] if cats else ["Tüm Kategoriler"]
            f_category = st.selectbox("Kategori", cat_list, label_visibility="collapsed")
            selected_cust_name = st.selectbox("Müşteri", [c[1] for c in my_custs])
            selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]

            if f_category == "Tüm Kategoriler":
                model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=?", (f_currency,))
            else:
                model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=? AND category=?", (f_currency, f_category))

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
        st.markdown("<h6 style='color:#1d4ed8; font-weight:800; margin-bottom:0px;'>🔌 DONANIMLAR</h6>", unsafe_allow_html=True)
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
                            c_img, c_main = st.columns([1.2, 4])
                            with c_img:
                                if o_img and os.path.isfile(o_img):
                                    try:
                                        with open(o_img, "rb") as f: st.image(f.read(), use_container_width=True)
                                    except: st.markdown("📷")
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
    # HESAPLAMALAR VE ÖNİZLEME (SOL ALT VE SAĞ)
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

        # GÖMÜLÜ MOTOR İLE HTML ÜRETİMİ
        html_preview = generate_embedded_html(
            customer=selected_cust_name, model=selected_model, 
            base_price=float(m_price) * multiplier, machine_img=m_img_path,
            specs=m_specs, selected_options=engine_options_list, 
            conditions=conditions_data, delivery_type=delivery_type, m_currency=m_currency
        )

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
            
        st.info("💡 **PDF Almak İçin:** Sağdaki teklif raporunun herhangi bir yerine tıklayıp **CTRL+P** (Mac'te CMD+P) tuşuna basarak 'PDF Olarak Kaydet' diyebilirsiniz.")

    # SAĞ KOLON: ÖNİZLEME
    with col_right:
        st.markdown("<h6 style='font-weight:800; margin-bottom:0px;'>📄 CANLI ÖNİZLEME</h6>", unsafe_allow_html=True)
        components.html(html_preview, height=800, scrolling=True)
