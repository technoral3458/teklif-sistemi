import streamlit as st
import streamlit.components.v1 as components
import datetime
import pandas as pd
import json
import os
import base64
import sqlite3

# =====================================================================
# VERİTABANI BAĞLANTI MOTORLARI (Kullanıcının DB Yapısına Özel)
# =====================================================================
def get_factory(query, params=()):
    conn = sqlite3.connect('factory_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db')
    c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def init_wizard_tables():
    # Sales DB içindeki tabloları kontrol et ve yoksa oluştur
    exec_sales("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in get_sales("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
        if "status" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'Beklemede'")
    except: pass

# =====================================================================
# HTML VE PDF ÖNİZLEME MOTORU (A4 STANDARTLI)
# =====================================================================
def get_image_base64(img_path):
    if not img_path or not os.path.exists(img_path): return ""
    try:
        with open(img_path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(img_path)[1].lower().replace('.', '')
        return f"data:image/{ext if ext else 'png'};base64,{b64}"
    except: return ""

def generate_embedded_html(customer, model, base_price, machine_img, specs, selected_options, conditions, m_currency, user_id):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    m_qty = conditions.get("machine_qty", 1)
    agreed_price = conditions.get("agreed_price", 0)

    # Bayi Bilgilerini Çek
    try: u_info = get_user_query("SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (user_id,))[0]
    except: u_info = None
    
    comp_name = u_info[0] if u_info and u_info[0] else "ERSAN MAKİNE"
    comp_logo = u_info[1] if u_info and u_info[1] else ""
    comp_web = u_info[2] if u_info and u_info[2] else "www.ersanmakina.net"
    comp_adr = u_info[3] if u_info and u_info[3] else "Ersan Makine San. Tic. Ltd. Şti."
    comp_tel = u_info[4] if u_info and u_info[4] else ""

    if not comp_logo:
        try: comp_logo = get_factory("SELECT logo_path FROM company_profile WHERE id=1")[0][0]
        except: pass

    logo_b64 = get_image_base64(comp_logo)
    header_logo_html = f'<img src="{logo_b64}" style="max-height:70px;">' if logo_b64 else f'<div style="font-size:24px; font-weight:900; color:#1e293b;">{comp_name}</div>'

    # SIKIŞMAYAN, GERÇEK A4 CSS KODLARI
    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 13px; color: #1e293b; background: #cbd5e1; margin:0; padding:20px; }
        .scroll-wrapper { width: 100%; overflow-x: auto; background: #cbd5e1; padding: 10px; box-sizing: border-box; }
        .paper { background: #fff; width: 210mm; min-height: 297mm; padding: 15mm; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.15); border-top: 8px solid #2563eb; box-sizing: border-box; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
        .section-title { background: #f8fafc; color: #0f172a; padding: 8px 15px; font-weight: 800; font-size: 14px; margin-top: 30px; border-left: 4px solid #2563eb; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 10px; text-align: left; vertical-align: middle; }
        .price-box { background: #fffbeb; border: 1px solid #fde68a; padding: 20px; text-align: right; margin-top: 30px; border-radius: 4px; }
        .total-price { font-size: 28px; font-weight: 800; color: #ea580c; }
        .elegant-conditions { margin-top: 30px; background: #f8fafc; padding: 15px; border-left: 4px solid #eab308; }
        .print-btn { background: #10b981; color: white; border: none; padding: 15px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; max-width: 210mm; margin: 0 auto 20px auto; display: block; font-weight: bold; }
        @media print { .no-print { display: none !important; } .scroll-wrapper { padding: 0; background: none; } .paper { box-shadow: none; border: none; padding: 0; margin: 0; width: 100%; } body { background: #fff; padding: 0; } }
    """

    html = f"""
    <html><head><meta charset="utf-8"><style>{css}</style></head><body>
        <div class="no-print"><button class="print-btn" onclick="window.print()">🖨️ PDF OLARAK KAYDET / YAZDIR</button></div>
        <div class="scroll-wrapper">
        <div class="paper">
            <div class="header">
                <div>{header_logo_html}</div>
                <div style="text-align:right; font-size: 12px; color: #64748b;"><b>{comp_web}</b><br>Tarih: {tarih}<br>Teklif No: TR-{datetime.datetime.now().strftime("%y%m%d")}</div>
            </div>
            <div style="text-align:center; padding: 15px 0;">
                <img src="{get_image_base64(machine_img)}" style="max-height:250px; object-fit:contain;"><br>
                <h2 style="color:#0f172a; margin:10px 0;">MODEL: {model}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:14px; color:#475569;">
                    Sayın Yetkili: <b style="color:#0f172a;">{customer}</b>
                </div>
            </div>
    """

    if specs and str(specs).strip():
        html += '<div class="section-title">🔍 MAKİNE STANDART ÖZELLİKLERİ</div><table>'
        for item in [x for x in str(specs).split("||") if x.strip()]:
            parts = item.split("|")
            t_spec = parts[0].strip() if len(parts) > 0 else ""
            d_spec = parts[1].strip() if len(parts) > 1 else ""
            img_tag = f'<img src="{get_image_base64(parts[2].strip() if len(parts)>2 else "")}" style="max-width:60px; max-height:40px; border-radius:4px;">' if (len(parts)>2 and parts[2].strip()) else ""
            html += f'<tr><td width="10%" style="text-align:center;">{img_tag}</td><td width="90%"><b>{t_spec}</b><br><small style="color:#64748b;">{d_spec}</small></td></tr>'
        html += "</table>"

    html += f"""
        <div class="section-title">📦 SEÇİLEN EKSTRA DONANIMLAR</div>
        <table><tr style="background:#f8fafc;"><th>Açıklama</th><th style="text-align:center;">Adet</th><th style="text-align:right;">Tutar</th></tr>
        <tr><td><b>{model} (Standart Donanım)</b></td><td style="text-align:center;">{m_qty}</td><td style="text-align:right;">{base_price*m_qty:,.2f} {m_currency}</td></tr>"""
    for opt in selected_options:
        html += f"<tr><td><b style='color:#2563eb;'>+ {opt['n']}</b><br><small>{opt['d']}</small></td><td style='text-align:center;'>{opt['q']}</td><td style='text-align:right; font-weight:bold;'>{(opt['p']*opt['q']):,.2f} {m_currency}</td></tr>"
    html += "</table>"

    html += f"""
        <div class="elegant-conditions">
            <div style="font-size: 14px; font-weight: bold; color: #1e293b; border-bottom: 1px solid #cbd5e1; padding-bottom: 5px; margin-bottom: 10px;">📌 Ticari ve Teknik Şartlar</div>
            <p style="font-size: 11px; color: #64748b; margin-bottom: 10px;">Değerli müşterimiz, sizlere sunmuş olduğumuz bu teklif kapsamındaki teslimat ve ödeme detayları aşağıdadır:</p>
            <table>
                <tr><td width="30%"><b>Teslimat Şekli:</b></td><td style="color:#ea580c; font-weight:bold;">{conditions.get('delivery_type','')}</td></tr>
                <tr><td><b>Teslim Süresi:</b></td><td>{conditions.get('delivery_time','')}</td></tr>
                <tr><td><b>Nakliye / Lojistik:</b></td><td>{conditions.get('shipping','')}</td></tr>
                <tr><td><b>Ödeme Planı:</b></td><td>{conditions.get('payment_plan_text','')}</td></tr>
                <tr><td><b>Banka Bilgileri:</b></td><td>{conditions.get('bank','')}</td></tr>
            </table>
        </div>
        <div class="price-box">
            <div style="font-size:14px; font-weight:bold; color:#ea580c; text-transform:uppercase;">Genel Toplam (KDV Hariç)</div>
            <div class="total-price">{agreed_price:,.2f} {m_currency}</div>
        </div>
        <div style="margin-top:30px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:10px;">{comp_adr} | {comp_tel}</div>
        </div></div></body></html>"""
    return html

# =====================================================================
# ANA SİHİRBAZ YÖNETİCİSİ (Eksiksiz Kopyalanmalıdır!)
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
        st.session_state.wizard_data = {}

    my_custs = get_sales("SELECT id, company_name FROM customers WHERE user_id=?", (user_id,)) if not is_admin else get_sales("SELECT id, company_name FROM customers")
    if not my_custs:
        st.warning(":warning: Lütfen önce 'Müşterilerim' menüsünden bir müşteri ekleyiniz.")
        return

    # ADIM 1: TEMEL BİLGİLER
    if st.session_state.wizard_step == 1:
        if 'edit_offer_id' in st.session_state: del st.session_state.edit_offer_id
        for key in list(st.session_state.keys()):
            if key.startswith("o_") or key.startswith("q_") or key == "temp_del_type": del st.session_state[key]

        st.markdown("### :sparkles: Yeni Teklif Başlat")
        with st.container(border=True):
            sc_name = st.selectbox("Müşteri Seçimi", [c[1] for c in my_custs])
            f_curr = st.selectbox("Para Birimi", ["USD", "EUR", "TRY"])
            cats = get_factory("SELECT name FROM categories")
            f_cat = st.selectbox("Kategori", ["Tüm Kategoriler"] + [c[0] for c in cats])
            
            m_query = "SELECT id, name, base_price, compatible_options, image_path, specs, port_discount FROM models WHERE currency=?"
            m_params = [f_curr]
            if f_cat != "Tüm Kategoriler": m_query += " AND category=?"; m_params.append(f_cat)
            model_data = get_factory(m_query, tuple(m_params))

            if model_data:
                sel_m_name = st.selectbox("Makine Modeli", [m[1] for m in model_data])
                m_qty = st.number_input("Makine Adedi", min_value=1, value=1)
                
                if st.button("Sonraki Adım: Donanım ve Şartlar", type="primary", use_container_width=True):
                    m_info = [m for m in model_data if m[1] == sel_m_name][0]
                    st.session_state.wizard_data = {
                        "cust_id": [c[0] for c in my_custs if c[1] == sc_name][0], "cust_name": sc_name, 
                        "m_id": m_info[0], "m_name": sel_m_name, "m_price": m_info[2], "m_curr": f_curr, 
                        "m_opts": m_info[3], "m_img": m_info[4], "m_specs": m_info[5], "m_disc": m_info[6], "qty": m_qty
                    }
                    st.session_state.wizard_step = 2; st.rerun()
            else: st.error("Bu kriterlerde makine bulunamadı.")

    # ADIM 2: DÜZENLEME VE MANUEL FİYAT
    elif st.session_state.wizard_step == 2:
        wd = st.session_state.wizard_data
        col_opt, col_prev = st.columns([1.5, 2.5], gap="large")
        
        with col_opt:
            if 'edit_offer_id' in st.session_state:
                st.info("✏️ **DÜZENLEME MODU:** Şu an geçmiş bir teklifi güncelliyorsunuz.")
                if st.button("❌ İptal Et ve Sıfırdan Başla"): st.session_state.wizard_step = 1; st.rerun()
            else:
                if st.button("Makine Değiştir"): st.session_state.wizard_step = 1; st.rerun()
            
            with st.expander("SATIŞ ŞARTLARINI DÜZENLE", expanded=False):
                d_type = st.selectbox("Teslimat Şekli", ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Limandan Devir", "Yurtiçi Teslim (Standart)"], key="temp_del_type")
                d_time = st.text_input("Teslim Süresi", wd.get("d_time", "Sipariş onayından itibaren 90 iş günü"))
                ship = st.text_input("Nakliye / Lojistik", wd.get("ship", "Alıcıya Aittir"))
                pay = st.text_area("Ödeme Planı", wd.get("pay", "%30 Peşin, Kalanı Yükleme Öncesi"))
                bnk = st.text_area("Banka Bilgileri", wd.get("bnk", ""))
                nts = st.text_area("Özel Notlar", wd.get("nts", ""))

            st.markdown("🔌 **UYUMLU DONANIMLAR**")
            multiplier = 1.0
            if "Liman" in d_type and wd["m_disc"]: multiplier = 1.0 - (float(wd["m_disc"]) / 100.0)
            
            selected_options_for_db, engine_options_list, opts_total = [], [], 0.0
            
            with st.container(height=350):
                if wd["m_opts"]:
                    ids = [x.strip() for x in str(wd["m_opts"]).split(",") if x.strip()]
                    if ids:
                        placeholders = ",".join("?" * len(ids))
                        for o in get_factory(f"SELECT id, opt_name, opt_price, opt_desc, opt_image FROM options WHERE id IN ({placeholders}) ORDER BY sort_order ASC, id ASC", tuple(ids)):
                            d_o_p = o[2] * multiplier
                            with st.container(border=True):
                                c_chk, c_qty = st.columns([3, 1])
                                is_sel = c_chk.checkbox(f"{o[1]} (+{d_o_p:,.0f})", key=f"o_{o[0]}")
                                if is_sel:
                                    q_o = c_qty.number_input("Adet", 1, 100, 1, key=f"q_{o[0]}", label_visibility="collapsed")
                                    opts_total += (d_o_p * q_o)
                                    selected_options_for_db.append({"id": o[0], "qty": q_o})
                                    engine_options_list.append({'n': o[1], 'p': d_o_p, 'q': q_o, 'i': o[4], 'd': o[3]})

            # -------------------------------------------------------------
            # MANUEL FİYAT VE İSKONTO MOTORU
            # -------------------------------------------------------------
            st.markdown("---")
            sub = ((wd["m_price"] * multiplier) * wd["qty"]) + opts_total
            
            c_disc, c_man = st.columns(2)
            disc_p = c_disc.number_input("İskonto Oranı (%)", 0.0, 100.0, float(wd.get("disc_p", 0.0)), step=0.5)
            calc_val = sub * (1 - (disc_p/100.0))
            
            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
            use_manual = st.checkbox("⚙️ Nihai Tutarı Manuel Belirle (İskontoyu Ezer)", value=wd.get("is_manual", False))
            
            if use_manual:
                default_agreed = float(wd.get("agreed_price", calc_val))
                if default_agreed == 0.0: default_agreed = calc_val
                agreed = st.number_input("Müşteriye Sunulacak Net Tutar", value=default_agreed, step=50.0)
            else:
                agreed = calc_val
                st.info(f"Hesaplanan Toplam: {agreed:,.2f} {wd['m_curr']}")
            
            conds = {
                "machine_qty": wd["qty"], "agreed_price": agreed, "subtotal_calculated": sub, 
                "delivery_type": d_type, "delivery_time": d_time, "shipping": ship, 
                "payment_plan_text": pay, "bank": bnk, "notes": nts, 
                "discount_pct": disc_p, "is_manual": use_manual
            }

            btn_txt = "💾 TEKLİFİ GÜNCELLE (ÜZERİNE YAZ)" if 'edit_offer_id' in st.session_state else "💾 TEKLİFİ ARŞİVE KAYDET"
            if st.button(btn_txt, type="primary", use_container_width=True):
                try:
                    tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    if 'edit_offer_id' in st.session_state:
                        exec_sales("UPDATE offers SET total_price=?, conditions=? WHERE id=?", (agreed, json.dumps(conds), st.session_state.edit_offer_id))
                        exec_sales("DELETE FROM offer_items WHERE offer_id=?", (st.session_state.edit_offer_id,))
                        for item in selected_options_for_db: exec_sales("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", (st.session_state.edit_offer_id, item["id"], item["qty"]))
                        st.success("Teklif Başarıyla Güncellendi!"); del st.session_state.edit_offer_id
                    else:
                        exec_sales("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date, status, conditions) VALUES (?,?,?,?,?,?,?)", (wd["cust_id"], wd["m_id"], agreed, user_id, tarih, "Beklemede", json.dumps(conds)))
                        res_id = get_sales("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
                        if res_id and selected_options_for_db:
                            for item in selected_options_for_db: exec_sales("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", (res_id[0][0], item["id"], item["qty"]))
                        st.success("Başarıyla Arşivlendi!")
                    st.balloons()
                except Exception as e: st.error(f"Kayıt Hatası: {e}")

        # CANLI ÖNİZLEME BÖLÜMÜ
        with col_prev:
            st.markdown("<div style='font-size:16px; font-weight:800; color:#0f172a; margin-bottom:10px;'>📄 A4 RAPOR ÖNİZLEMESİ</div>", unsafe_allow_html=True)
            html = generate_embedded_html(wd["cust_name"], wd["m_name"], wd["m_price"]*multiplier, wd["m_img"], wd["m_specs"], engine_options_list, conds, wd["m_curr"], user_id)
            with st.container(border=True): components.html(html, height=850, scrolling=True)
