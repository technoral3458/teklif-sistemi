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
# SİZİN ORİJİNAL PREVIEW ENGINE MOTORUNUZ (WEB'E VE PDF'E UYARLANDI)
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
    
    m_symbol = m_currency
    
    # Şirket bilgilerini çek
    try:
        res = database.get_query("SELECT company_name, logo_path, website, footer_text FROM company_profile WHERE id=1")
        if res: comp_name, comp_logo, comp_web, comp_footer = res[0]
        else: comp_name, comp_logo, comp_web, comp_footer = "ERSAN MAKİNE", "", "www.ersanmakina.net", "Ersan Makine San. ve Tic. Ltd. Şti."
    except:
        comp_name, comp_logo, comp_web, comp_footer = "ERSAN MAKİNE", "", "www.ersanmakina.net", "Ersan Makine San. ve Tic. Ltd. Şti."

    machine_qty = conditions.get("machine_qty", 1)
    hide_specs = conditions.get("hide_specs", False)

    logo_b64 = get_image_base64(comp_logo)
    header_logo_html = f'<img src="{logo_b64}" style="max-height:60px;">' if logo_b64 else f'<div style="font-size:24px; font-weight:900; color:#2c3e50;">{comp_name}</div>'

    # HER SAYFANIN BAŞINDAKİ ANTET VE LOGO
    page_header = f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 10px; border-bottom: 2px solid #e67e22; padding-bottom: 5px;">
        <tr>
            <td align="left" valign="middle" width="50%">
                {header_logo_html}
            </td>
            <td align="right" valign="middle" width="50%" style="color: #64748b; font-size: 11px;">
                {comp_web}<br>{comp_footer}
            </td>
        </tr>
    </table>
    """
    
    m_img_b64 = get_image_base64(machine_img)
    m_img_html = f'<img src="{m_img_b64}" style="max-width:100%; max-height:350px; object-fit:contain; margin: 10px 0;">' if m_img_b64 else f'<div style="padding:40px; text-align:center; color:#94a3b8; border:1px dashed #cbd5e1; margin:10px 0;">Makine Görseli Yok</div>'

    css = """
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; font-size: 13px; }
        .paper { background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 1000px; margin: 0 auto; }
        .thumb { max-width: 140px; max-height: 90px; border-radius: 6px; border: 1px solid #e2e8f0; object-fit: cover; }
        h3 { background-color: #1e293b; color: white; padding: 8px 15px; font-size: 15px; border-radius: 4px; margin-top: 0; margin-bottom: 10px; }
        .price-box { border-left: 8px solid #e67e22; background-color: #f8fafc; padding: 25px; text-align: right; margin-top: 20px; border-radius: 8px; }
        .print-btn { background: #10b981; color: white; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; text-transform: uppercase; float: right; }
        .print-btn:hover { background: #059669; }
        @media print {
            body { background: #fff; padding: 0; }
            .paper { box-shadow: none; padding: 0; margin: 0; max-width: 100%; border: none; }
            .no-print { display: none !important; }
            .page-break { page-break-before: always; }
        }
    """

    payment_html = ""
    payment_plan = conditions.get('payment_plan', [])
    if payment_plan:
        payment_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 0; padding: 0;">
            <tr>
                <th width="60%" style="border-bottom: 1px solid #e2e8f0; padding: 8px 0; text-align: left; color: #475569;">Açıklama / Vade</th>
                <th width="40%" align="right" style="border-bottom: 1px solid #e2e8f0; padding: 8px 0; text-align: right; color: #475569;">Tutar</th>
            </tr>
        """
        for row in payment_plan:
            amt_display = f"{row[2]} {m_symbol}" if len(row) > 2 and str(row[2]).strip() else "-"
            payment_html += f"<tr><td style='padding:8px 0; border-bottom:1px dashed #f1f5f9;'>{row[0]}</td><td align='right' style='padding:8px 0; border-bottom:1px dashed #f1f5f9; text-align: right;'><b>{amt_display}</b></td></tr>"
        payment_html += '</table>'
    else:
        payment_html = f"<i>Belirtilmedi</i>"

    subtotal_calculated = conditions.get('subtotal_calculated', float(base_price) * machine_qty)
    discount_pct = conditions.get('discount_pct', 0.0)
    agreed_price = conditions.get('agreed_price', subtotal_calculated)
    
    if machine_qty > 1: base_price_display = f'{float(base_price):,.2f} {m_symbol} x {machine_qty} Adet = {float(base_price) * machine_qty:,.2f} {m_symbol}'
    else: base_price_display = f'{float(base_price):,.2f} {m_symbol}'

    if discount_pct > 0:
        price_summary_html = f"""
        <div class="price-box">
            <div style="font-size: 15px; color: #64748b; font-weight: 600;">Makine Baz Fiyatı: {base_price_display}</div>
            <div style="margin-top:10px; font-size: 15px; color: #94a3b8;">Sistem Liste Toplamı: <span style="text-decoration: line-through;">{subtotal_calculated:,.2f} {m_symbol}</span></div>
            <div style="font-size: 15px; color: #ef4444; font-weight: bold; margin-top:5px;">Uygulanan Özel İskonto: %{discount_pct:,.2f}</div>
            <div style="font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 15px;">NET FİYAT (KDV Hariç)</div>
            <div style="font-size: 42px; font-weight: 900; color: #e67e22; margin-top: 5px;">{agreed_price:,.2f} {m_symbol}</div>
        </div>
        """
    else:
        price_summary_html = f"""
        <div class="price-box">
            <div style="font-size: 15px; color: #64748b; font-weight: 600;">Makine Baz Fiyatı: {base_price_display}</div>
            <div style="font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 15px;">GENEL TOPLAM (KDV Hariç)</div>
            <div style="font-size: 42px; font-weight: 900; color: #e67e22; margin-top: 5px;">{agreed_price:,.2f} {m_symbol}</div>
        </div>
        """

    bank_info = conditions.get('bank', '').replace('\n', '<br>')
    notes_info = conditions.get('notes', '').replace('\n', '<br>')
    cond_html = f"""
    <div style="margin-top: 30px;">
        <h4 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-bottom: 10px; font-size: 16px;">📝 SATIŞ VE TESLİMAT ŞARTLARI</h4>
        <table width="100%" style="border-collapse: collapse;">
            <tr>
                <td width="200" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>Teslimat Şekli:</b></td>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; color:#e67e22; font-weight:bold; font-size: 14px;">{delivery_type}</td>
            </tr>
            <tr>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>Teslim Süresi:</b></td>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{conditions.get('delivery_time', '')}</td>
            </tr>
            <tr>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>Nakliye / Lojistik:</b></td>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{conditions.get('shipping', '')}</td>
            </tr>
            <tr>
                <td valign="top" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>Ödeme Planı:</b></td>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1;">{payment_html}</td>
            </tr>
            <tr>
                <td valign="top" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>Banka Bilgileri:</b></td>
                <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{bank_info}</td>
            </tr>
        </table>
    """
    if notes_info.strip():
        cond_html += f'<div style="margin-top:15px; padding-top:15px; font-size:13px; color:#475569;"><b>Özel Notlar:</b><br>{notes_info}</div>'
    cond_html += "</div>"

    pages = []
    qty_title_addon = f' <span style="color:#e67e22;">(x{machine_qty} Adet)</span>' if machine_qty > 1 else ""

    # =========================================================
    # SAYFA 1: KAPAK
    # =========================================================
    page1 = f"""
    <div>
        {page_header}
        <div style="text-align:center; margin-top:20px;">
            {m_img_html}
            <div style="font-size: 32px; font-weight: 800; margin: 20px 0; color: #0f172a;">MODEL: {model}{qty_title_addon}</div>
        </div>
        <table width="100%" cellpadding="15" style="border: 1px solid #e2e8f0; background-color: #f8fafc; border-radius: 8px; margin-top: 30px; border-collapse: collapse;">
            <tr><td width="150" style="color:#64748b; border-bottom:1px solid #e2e8f0;">Sayın Yetkili:</td><td style="font-size:18px; font-weight:bold; border-bottom:1px solid #e2e8f0;">{customer}</td></tr>
            <tr><td style="color:#64748b; border-bottom:1px solid #e2e8f0;">Tarih:</td><td style="border-bottom:1px solid #e2e8f0;">{tarih}</td></tr>
            <tr><td style="color:#64748b;">Teklif No:</td><td style="font-weight:bold;">TR-{datetime.datetime.now().strftime("%y%m%d")}</td></tr>
        </table>
    </div>
    """
    pages.append(page1)

    # =========================================================
    # SAYFA 2+: STANDART ÖZELLİKLER (Tam 5 Adet)
    # =========================================================
    if not hide_specs and specs:
        specs_list = [item for item in specs.split("||") if item.strip()]
        chunk_size = 5 
        for i in range(0, len(specs_list), chunk_size):
            chunk = specs_list[i:i + chunk_size]
            devam_txt = f" <span style='font-size:12px; font-weight:normal;'>(Devamı {i//chunk_size + 1})</span>" if i > 0 else ""
            
            spec_page = f"""
            <div>
                {page_header}
                <h3>🔍 MAKİNE STANDART ÖZELLİKLERİ{devam_txt}</h3>
            """
            for item in chunk:
                parts = item.split("|")
                title = parts[0].strip() if len(parts) > 0 else ""
                desc = parts[1].strip() if len(parts) > 1 else ""
                img_name = parts[2].strip() if len(parts) > 2 else ""
                
                desc = desc.replace("\n", "<br>")
                img_b64 = get_image_base64(img_name)
                img_t = f'<img src="{img_b64}" class="thumb">' if img_b64 else ''
                
                spec_page += f"""
                <table width="100%" style="border-collapse: collapse; page-break-inside: avoid; margin-bottom: 0;">
                    <tr>
                        <td width="20%" align="center" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">{img_t}</td>
                        <td width="80%" align="left" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">
                            <b style="font-size:15px; color:#0f172a;">{title}</b><br>
                            <div style='color:#64748b; font-size:13px; margin-top:4px;'>{desc}</div>
                        </td>
                    </tr>
                </table>
                """
            spec_page += "</div>"
            pages.append(spec_page)

    # =========================================================
    # SAYFA X+: OPSİYONLAR (Tam 5 Adet)
    # =========================================================
    if selected_options:
        chunk_size = 5
        for i in range(0, len(selected_options), chunk_size):
            chunk = selected_options[i:i + chunk_size]
            devam_txt = f" <span style='font-size:12px; font-weight:normal;'>(Devamı {i//chunk_size + 1})</span>" if i > 0 else ""
            
            opt_page = f"""
            <div>
                {page_header}
                <h3>📦 SEÇİLEN OPSİYONLAR{devam_txt}</h3>
                <table width="100%" style="border-collapse: collapse; background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; margin-bottom: 0;">
                    <tr>
                        <th width="20%" align="center" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: center;">Görsel</th>
                        <th width="55%" align="left" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: left;">Donanım Açıklaması</th>
                        <th width="25%" align="right" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: right;">Fiyat</th>
                    </tr>
                </table>
            """
            for opt in chunk:
                img_b64 = get_image_base64(opt["i"])
                img_t = f'<img src="{img_b64}" class="thumb">' if img_b64 else ''
                qty = int(opt.get('q', 1))
                unit_p = float(opt['p'])
                sym = opt.get('s', '$')
                qty_badge = f" <span style='color:#e67e22; font-size:12px; font-weight:bold;'>({qty} Adet)</span>" if qty > 1 else ""
                
                if qty > 1: 
                    price_display = f"<span style='font-size:11px; color:#94a3b8; font-weight:normal;'>{qty} x {unit_p:,.2f} {sym}</span><br>{unit_p * qty:,.2f} {sym}"
                else: 
                    price_display = f"{unit_p * qty:,.2f} {sym}"
                
                desc = opt['d'].replace('\n', '<br>')
                
                opt_page += f"""
                <table width="100%" style="border-collapse: collapse; page-break-inside: avoid; margin-bottom: 0;">
                    <tr>
                        <td width="20%" align="center" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">{img_t}</td>
                        <td width="55%" align="left" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">
                            <b style="font-size:15px; color:#0f172a;">{opt['n']}</b>{qty_badge}<br>
                            <div style='color:#64748b; font-size:13px; margin-top:4px;'>{desc}</div>
                        </td>
                        <td width="25%" align="right" valign="middle" style="padding: 10px; border-bottom: 1px solid #f1f5f9; font-weight: bold; font-size: 14px; color: #e67e22; text-align: right;">
                            {price_display}
                        </td>
                    </tr>
                </table>
                """
            opt_page += "</div>"
            pages.append(opt_page)

    # =========================================================
    # SON SAYFA: FİNAL VE ŞARTLAR 
    # =========================================================
    final_page = f"""
    <div style="position: relative; height: 260mm;">
        {page_header}
        {price_summary_html}
        {cond_html}
        <div style="position:absolute; bottom:0; width:100%; text-align:center; color:#94a3b8; font-size:12px; padding-top:15px; border-top: 1px solid #f1f5f9;">
            * Bu teklif {tarih} tarihinde oluşturulmuştur.
        </div>
    </div>
    """
    pages.append(final_page)

    page_separator = '<div class="page-break" style="height: 1px; margin: 0; padding: 0;"></div>'
    full_html_content = page_separator.join(pages)

    final_html = f"""
    <!DOCTYPE html><html><head><meta charset='UTF-8'><style>{css}</style></head>
    <body>
        <div class="no-print">
            <button class="print-btn" onclick="window.print()">🖨️ PDF OLARAK İNDİR / YAZDIR</button>
            <div style="clear:both;"></div>
        </div>
        <div class="paper">
            {full_html_content}
        </div>
    </body></html>
    """
    return final_html

# =====================================================================
# ANA TEKLİF SİHİRBAZI YÖNETİCİSİ (UI)
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    st.markdown("""
    <style>
    .block-container { padding-top: 1rem; max-width: 98%; }
    .stSelectbox label, .stNumberInput label { color: #475569 !important; font-size: 13px !important; font-weight: 600 !important; }
    .opt-card { padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; background: white; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .opt-price { color: #ea580c; font-weight: 800; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)
    
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
        st.session_state.wizard_data = {}

    if is_admin:
        my_custs = database.get_query("SELECT id, company_name FROM customers ORDER BY company_name")
    else:
        my_custs = database.get_query("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name", (user_id,))
    
    if not my_custs:
        st.warning("⚠️ Lütfen 'Müşterilerim' menüsünden müşteri ekleyiniz.")
        return

    # -----------------------------------------------------------------
    # ADIM 1: SİHİRBAZ BAŞLANGICI 
    # -----------------------------------------------------------------
    if st.session_state.wizard_step == 1:
        st.markdown("<h3 style='text-align:center; color:#0f172a; margin-bottom: 30px;'>✨ Yeni Teklif Sihirbazı</h3>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                st.markdown("<div style='background:#f8fafc; padding:10px; border-radius:8px; margin-bottom:15px; text-align:center; font-weight:bold; color:#3b82f6; border:1px solid #e2e8f0;'>1. ADIM: TEMEL BİLGİLER</div>", unsafe_allow_html=True)
                
                selected_cust_name = st.selectbox("👤 Müşteri Seçimi", [c[1] for c in my_custs])
                f_currency = st.selectbox("💵 Para Birimi", ["USD", "EUR", "RMB", "TRY"])
                
                cats = database.get_query("SELECT name FROM categories ORDER BY id")
                cat_list = ["Tüm Kategoriler"] + [c[0] for c in cats] if cats else ["Tüm Kategoriler"]
                f_category = st.selectbox("🗂️ Makine Kategorisi", cat_list)

                model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=?", (f_currency,)) if f_category == "Tüm Kategoriler" else database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=? AND category=?", (f_currency, f_category))

                if not model_data:
                    st.error("Bu kriterlere uygun makine bulunamadı.")
                else:
                    selected_model = st.selectbox("🤖 Makine Modeli", [m[1] for m in model_data])
                    cc1, cc2 = st.columns(2)
                    m_qty = cc1.number_input("Adet", min_value=1, value=1)
                    delivery_type = cc2.selectbox("Teslimat", ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Gümrük İşlemleri Yapılmadan Limandan Devir"])
                    
                    st.write("")
                    if st.button("Sonraki Adım: Donanım Seçimi ➡️", type="primary", use_container_width=True):
                        selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]
                        m_info = [m for m in model_data if m[1] == selected_model][0]
                        
                        st.session_state.wizard_data = {
                            "cust_id": selected_cust_id, "cust_name": selected_cust_name,
                            "m_id": m_info[0], "m_name": selected_model, "m_price": m_info[2],
                            "m_curr": m_info[3], "m_opts": m_info[4], "m_disc": m_info[5],
                            "m_img": m_info[6], "m_specs": m_info[7],
                            "qty": m_qty, "delivery": delivery_type
                        }
                        st.session_state.wizard_step = 2
                        st.rerun()

    # -----------------------------------------------------------------
    # ADIM 2: DİNAMİK 2 KOLONLU ÇALIŞMA ALANI
    # -----------------------------------------------------------------
    elif st.session_state.wizard_step == 2:
        wd = st.session_state.wizard_data
        
        col_back, col_info = st.columns([1, 5], vertical_alignment="center")
        if col_back.button("🔙 Ayarlara Dön"):
            st.session_state.wizard_step = 1
            st.rerun()
        col_info.markdown(f"<div style='background:#eff6ff; padding:10px 20px; border-radius:8px; border:1px solid #bfdbfe; color:#1e40af; font-size:14px;'><b>Müşteri:</b> {wd['cust_name']} &nbsp;|&nbsp; <b>Model:</b> {wd['m_name']} (x{wd['qty']})</div>", unsafe_allow_html=True)
        st.write("")

        col_opt, col_prev = st.columns([1.5, 2.5], gap="large")
        
        engine_options_list = []
        selected_options_for_db = []
        selected_options_total = 0.0

        multiplier = 1.0
        if "Liman" in wd["delivery"] and wd["m_disc"]:
            multiplier = 1.0 - (float(wd["m_disc"]) / 100.0)

        with col_opt:
            st.markdown("<div style='font-size:16px; font-weight:800; color:#0f172a; margin-bottom:10px;'>🔌 UYUMLU DONANIMLAR</div>", unsafe_allow_html=True)
            
            with st.container(height=500):
                if wd["m_opts"]:
                    comp_opt_ids = [opt.strip() for opt in str(wd["m_opts"]).split(",") if opt.strip()]
                    if comp_opt_ids:
                        placeholders = ",".join("?" * len(comp_opt_ids))
                        opts_query = f"SELECT id, opt_name, opt_price, currency, opt_desc, opt_image FROM options WHERE id IN ({placeholders}) ORDER BY sort_order ASC, id ASC"
                        compatible_options = database.get_query(opts_query, tuple(comp_opt_ids))
                        
                        for opt in compatible_options:
                            o_id, o_name, o_price, o_curr, o_desc, o_img = opt
                            d_o_price = float(o_price) * multiplier
                            
                            with st.container(border=True):
                                cc_img, cc_text, cc_chk = st.columns([1, 4, 1.5], vertical_alignment="center")
                                
                                with cc_img:
                                    if o_img and os.path.isfile(o_img):
                                        try:
                                            with open(o_img, "rb") as f: st.image(f.read())
                                        except: st.markdown("📷")
                                    else: st.markdown("📷")
                                        
                                with cc_text:
                                    st.markdown(f"<b style='font-size:13px; color:#1e293b;'>{o_name}</b><br><span class='opt-price'>+ {d_o_price:,.0f} {o_curr}</span>", unsafe_allow_html=True)
                                
                                with cc_chk:
                                    is_selected = st.checkbox("Ekle", key=f"c_{o_id}")
                                
                                if is_selected:
                                    o_qty = st.number_input("Adet", min_value=1, value=1, key=f"q_{o_id}")
                                    selected_options_total += (d_o_price * o_qty)
                                    selected_options_for_db.append({"id": o_id, "qty": o_qty})
                                    engine_options_list.append({'n': o_name, 'p': d_o_price, 'q': o_qty, 'i': o_img, 'd': o_desc, 's': o_curr})
                else:
                    st.info("Donanım bulunmuyor.")
            
            st.markdown("---")
            sub_total = ((float(wd["m_price"]) * multiplier) * wd["qty"]) + selected_options_total
            
            with st.container(border=True):
                st.markdown(f"<div style='font-size:14px; color:#64748b; margin-bottom:10px;'>Sistem Toplamı: <b style='color:#0f172a;'>{sub_total:,.2f} {wd['m_curr']}</b></div>", unsafe_allow_html=True)
                
                c_disc, c_net = st.columns(2)
                discount_pct = c_disc.number_input("Özel İskonto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                final_price = sub_total * (1 - (discount_pct / 100.0))
                agreed_price = c_net.number_input("Anlaşılan Net Fiyat", min_value=0.0, value=final_price, step=100.0)

            conditions_data = {
                "machine_qty": wd["qty"], "discount_pct": discount_pct, "subtotal_calculated": sub_total,
                "agreed_price": agreed_price, "hide_specs": False, "delivery_type": wd["delivery"]
            }

            st.write("")
            if st.button("💾 TEKLİFİ ARŞİVE KAYDET", use_container_width=True, type="primary"):
                try:
                    tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    cond_str = json.dumps(conditions_data)
                    database.exec_query("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date, conditions) VALUES (?,?,?,?,?,?)",
                                       (wd['cust_id'], wd['m_id'], agreed_price, user_id, tarih, cond_str))
                    res_id = database.get_query("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
                    if res_id and selected_options_for_db:
                        new_id = res_id[0][0]
                        for item in selected_options_for_db:
                            database.exec_query("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", (new_id, item["id"], item["qty"]))
                    st.success("Sisteme Başarıyla Kaydedildi! Müşterilerim sekmesinden inceleyebilirsiniz.")
                    st.balloons()
                except Exception as e: st.error(f"Kayıt Hatası: {e}")

        with col_prev:
            st.markdown("<div style='font-size:16px; font-weight:800; color:#0f172a; margin-bottom:10px;'>📄 CANLI RAPOR VE PDF</div>", unsafe_allow_html=True)
            
            html_preview = generate_embedded_html(
                customer=wd['cust_name'], model=wd['m_name'], 
                base_price=float(wd['m_price']) * multiplier, machine_img=wd['m_img'],
                specs=wd['m_specs'], selected_options=engine_options_list, 
                conditions=conditions_data, delivery_type=wd['delivery'], m_currency=wd['m_curr']
            )
            
            with st.container(border=True):
                components.html(html_preview, height=850, scrolling=True)
