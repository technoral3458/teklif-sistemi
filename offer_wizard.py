import streamlit as st
import streamlit.components.v1 as components
import datetime
import pandas as pd
import json
import os
import base64
import sqlite3
import ntpath
import posixpath

# =====================================================================
# VERİTABANI BAĞLANTI MOTORLARI
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
    exec_sales("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in get_sales("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
        if "status" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'Beklemede'")
        if "user_id" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass

# =====================================================================
# GELİŞMİŞ VE AKILLI RESİM OKUMA MOTORU
# =====================================================================
def get_image_base64(path):
    if not path: return ""
    if str(path).startswith("http"): return path
    base_name = posixpath.basename(ntpath.basename(path))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    ext = os.path.splitext(p)[1].lower().replace('.', '')
                    if not ext: ext = 'png'
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except: pass
    return ""

def generate_embedded_html(customer, model, base_price, machine_img, specs, selected_options, conditions, m_currency, user_id):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    m_qty = conditions.get("machine_qty", 1)
    agreed_price = conditions.get("agreed_price", 0)
    teklif_no = f"TR-{datetime.datetime.now().strftime('%y%m%d')}"

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
    header_logo_html = f'<img src="{logo_b64}" style="max-height:70px; width:auto; object-fit:contain;">' if logo_b64 else f'<div style="font-size:22px; font-weight:900; color:#1e293b;">{comp_name}</div>'

    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 14px; color: #1e293b; background: #ffffff; margin:0; padding:0; display: flex; flex-direction: column; align-items: center; }
        .paper { background: #fff; width: 100%; max-width: 794px; min-height: 1123px; padding: 40px; border: 1px solid #e2e8f0; border-top: 8px solid #2563eb; box-sizing: border-box; overflow: hidden; margin: 0 auto 40px auto; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .section-title { background: #f8fafc; color: #0f172a; padding: 10px 15px; font-weight: 800; font-size: 14px; margin-top: 30px; border-left: 5px solid #2563eb; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 12px; text-align: left; vertical-align: middle; word-wrap: break-word; }
        .price-box { background: #fffbeb; border: 1px solid #fde68a; padding: 20px; text-align: right; margin-top: 35px; border-radius: 6px; }
        .total-price { font-size: 30px; font-weight: 900; color: #ea580c; word-break: break-all; }
        .elegant-conditions { margin-top: 35px; background: #f8fafc; padding: 20px; border-left: 5px solid #eab308; }
        .print-btn-container { width: 100%; max-width: 794px; margin: 0 auto 40px auto; text-align: center; }
        .print-btn { background: #10b981; color: white; border: none; padding: 15px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        .footer-info { margin-top:30px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:15px; }
        
        @media screen and (max-width: 600px) {
            .paper { padding: 15px; border-left: none; border-right: none; margin-bottom: 20px; }
            th, td { padding: 8px 4px; font-size: 12px; }
            .section-title { font-size: 12px; padding: 8px 10px; }
            .total-price { font-size: 22px; }
        }
        
        @media print { .no-print { display: none !important; } .paper { border: none; padding: 0; margin: 0; width: 100%; max-width: 100%; min-height: auto; } body { background: #fff; padding: 0; } .page-break { page-break-before: always; } }
    """

    page_header_html = f"""
        <div class="header">
            <div>{header_logo_html}</div>
            <div style="text-align:right; font-size: 12px; color: #64748b;"><b>{comp_web}</b><br>Tarih: {tarih}<br>Teklif No: {teklif_no}</div>
        </div>
    """

    html = f"""
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{css}</style></head><body>
        <div class="paper">
            {page_header_html}
            <div style="text-align:center; padding: 15px 0;">
                <img src="{get_image_base64(machine_img)}" style="max-width:100%; max-height:350px; width:auto; height:auto; object-fit:contain; display:block; margin:0 auto;"><br>
                <h2 style="color:#0f172a; margin:15px 0; font-size:24px; font-weight:900;">MODEL: {model}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:15px; color:#475569;">
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
            img_b64 = get_image_base64(parts[2].strip() if len(parts)>2 else "")
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:80px; object-fit:contain; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">' if img_b64 else "<span style='color:#cbd5e1;'>-</span>"
            html += f'<tr><td style="width:25%; text-align:center; vertical-align:middle;">{img_tag}</td><td style="width:75%; vertical-align:middle;"><b>{t_spec}</b><br><small style="color:#64748b; font-size:13px;">{d_spec}</small></td></tr>'
        html += "</table>"

    if selected_options:
        html += f"""
            <div class="section-title">📦 SEÇİLEN EKSTRA DONANIMLAR</div>
            <table><tr style="background:#f8fafc;"><th style="width:25%; text-align:center;">Görsel</th><th style="width:40%;">Açıklama</th><th style="width:10%; text-align:center;">Adet</th><th style="width:25%; text-align:right;">Tutar</th></tr>"""
        for opt in selected_options:
            opt_img_b64 = get_image_base64(opt["i"])
            opt_img_tag = f'<img src="{opt_img_b64}" style="max-width:100%; max-height:80px; object-fit:contain; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">' if opt_img_b64 else "<span style='color:#cbd5e1;'>-</span>"
            html += f"<tr><td style='text-align:center; vertical-align:middle;'>{opt_img_tag}</td><td style='vertical-align:middle;'><b style='color:#2563eb; font-size:14px;'>+ {opt['n']}</b><br><small style='display:block; line-height:1.3; margin-top:4px; color:#475569;'>{opt['d']}</small></td><td style='text-align:center; vertical-align:middle;'>{opt['q']}</td><td style='text-align:right; font-weight:bold; font-size:15px; vertical-align:middle;'>{(opt['p']*opt['q']):,.2f} {m_currency}</td></tr>"
        html += "</table>"

    html += f"""
        </div> 
        <div class="paper page-break">
            {page_header_html}
        <div class="elegant-conditions">
            <div style="font-size: 15px; font-weight: bold; color: #1e293b; border-bottom: 2px solid #cbd5e1; padding-bottom: 8px; margin-bottom: 12px;">📌 Ticari ve Teknik Şartlar</div>
            <p style="font-size: 12px; color: #64748b; margin-bottom: 12px;">Sizlere sunmuş olduğumuz bu teklif kapsamındaki teslimat detayları:</p>
            <table>
                <tr><td style="width:35%;"><b>Teslimat Şekli:</b></td><td style="color:#ea580c; font-weight:bold;">{conditions.get('delivery_type','')}</td></tr>
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
        <div class="footer-info">{comp_adr} | {comp_tel}</div>
        </div>
        
        <div class="no-print print-btn-container"><button class="print-btn" onclick="window.print()">🖨️ PDF KAYDET</button></div>
        
        </body></html>"""
    
    return html

def get_index(lst, item, default=None):
    return lst.index(item) if item in lst else default

# =====================================================================
# ANA SİHİRBAZ EKRANI
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        .block-container {
            padding-top: 0rem !important; 
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important; 
            padding-right: 0.5rem !important; 
            max-width: 100% !important; 
        }

        /* Klavyeyi engeller */
        div[data-baseweb="select"] input { 
            caret-color: transparent !important; 
            inputmode: none !important;
        }
        
        /* Kibar Kutu Tasarımı */
        div.st-emotion-cache-1jicfl2 { 
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
            padding: 1.5rem !important;
        }
        .stSelectbox label, .stTextInput label, .stNumberInput label, .stTextArea label {
            font-size: 13px !important; font-weight: 700 !important; color: #475569 !important; margin-bottom:4px !important;
        }
        .stToggle label { font-size: 14px !important; font-weight: 800 !important; color: #2563eb !important; }
        </style>
    """, unsafe_allow_html=True)
    
    components.html("""
    <script>
    function disableMobileKeyboard() {
        var inputs = window.parent.document.querySelectorAll('div[data-baseweb="select"] input');
        inputs.forEach(function(inp) {
            inp.setAttribute('inputmode', 'none'); 
        });
    }
    setInterval(disableMobileKeyboard, 300);
    </script>
    """, height=0, width=0)

    my_custs = get_sales("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name ASC", (user_id,)) if not is_admin else get_sales("SELECT id, company_name FROM customers ORDER BY company_name ASC")
    
    if not my_custs:
        st.warning("⚠️ Lütfen önce 'Müşterilerim' menüsünden müşteri ekleyiniz.")
        return

    is_edit = 'edit_offer_id' in st.session_state
    wd = st.session_state.get('wizard_data', {})

    col_opt, col_prev = st.columns([1.6, 2.4], gap="small")

    with col_opt:
        if is_edit:
            st.info("✏️ Düzenleme Modu")
            if st.button("❌ İptal Et ve Sıfırdan Başla", use_container_width=True):
                del st.session_state.edit_offer_id
                st.session_state.wizard_data = {}
                for key in list(st.session_state.keys()):
                    if key.startswith("o_") or key.startswith("q_") or key.startswith("tgl_") or key == "temp_del_type":
                        del st.session_state[key]
                st.rerun()

        st.markdown("<div style='font-size:14px; font-weight:900; color:#2563eb; margin-bottom:8px;'>1. MÜŞTERİ VE MAKİNE SEÇİMİ</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            
            CUST_PROMPT = "Lütfen Müşteri Seçiniz..."
            MACH_PROMPT = "Lütfen Makine Modeli Seçiniz..."

            c_names = [CUST_PROMPT] + [c[1] for c in my_custs]
            idx_c = c_names.index(wd.get("cust_name")) if wd.get("cust_name") in c_names else 0
            
            sel_cust = st.selectbox("Teklif Verilecek Müşteri", c_names, index=idx_c)

            cats = ["Tüm Kategoriler"] + [c[0] for c in get_factory("SELECT name FROM categories ORDER BY name ASC")]
            idx_cat = cats.index(wd.get("category")) if wd.get("category") in cats else 0
            
            sel_cat = st.selectbox("Kategori Filtresi", cats, index=idx_cat)

            m_query = "SELECT id, name, base_price, compatible_options, image_path, specs, port_discount, currency FROM models"
            m_params = []
            if sel_cat != "Tüm Kategoriler":
                m_query += " WHERE category=?"
                m_params.append(sel_cat)
            m_query += " ORDER BY name ASC"

            machines = get_factory(m_query, tuple(m_params))
            if not machines:
                st.warning("Bu kategoride makine bulunamadı.")
                return

            m_names = [MACH_PROMPT] + [m[1] for m in machines]
            idx_m = m_names.index(wd.get("m_name")) if wd.get("m_name") in m_names else 0
            
            sel_m = st.selectbox("Makine Modeli", m_names, index=idx_m)
            
            m_qty = st.number_input("Makine Adedi", 1, 100, wd.get("qty", 1))

        if sel_cust == CUST_PROMPT or sel_m == MACH_PROMPT:
            with col_prev:
                st.info("💡 Teklif detaylarını ve A4 raporunu görmek için lütfen yandaki panelden Müşteri ve Makine seçimi yapınız.")
            return

        cust_id = [c[0] for c in my_custs if c[1] == sel_cust][0]
        m_info = next(m for m in machines if m[1] == sel_m)
        m_id, m_name, m_price, m_opts_str, m_img, m_specs, m_disc, m_curr = m_info

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px; margin-bottom:10px; border-bottom:2px solid #e2e8f0; padding-bottom:5px;'>2. SATIŞ ŞARTLARI</div>", unsafe_allow_html=True)
        with st.expander("📝 Şartları Görüntüle / Düzenle", expanded=False):
            del_types = ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Limandan Devir", "Yurtiçi Teslim (Standart)"]
            saved_del_type = st.session_state.get("temp_del_type", "Gümrük İşlemleri Yapılmış Antrepo Teslim")
            idx_d = get_index(del_types, saved_del_type, default=0)

            d_type = st.selectbox("Teslimat Şekli", del_types, index=idx_d, key="temp_del_type")
            d_time = st.text_input("Teslim Süresi", wd.get("d_time", "Sipariş onayından itibaren 90 iş günü"))
            ship = st.text_input("Nakliye / Lojistik", wd.get("ship", "Alıcıya Aittir"))
            pay = st.text_area("Ödeme Planı", wd.get("pay", "%30 Peşin, Kalanı Yükleme Öncesi"))
            bnk = st.text_area("Banka Bilgileri", wd.get("bnk", ""))
            nts = st.text_area("Özel Notlar", wd.get("nts", ""))

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px; margin-bottom:10px; border-bottom:2px solid #e2e8f0; padding-bottom:5px;'>3. EKSTRA DONANIMLAR</div>", unsafe_allow_html=True)
        multiplier = 1.0
        if "Liman" in d_type and m_disc:
            multiplier = 1.0 - (float(m_disc) / 100.0)

        selected_options_for_db, engine_options_list, opts_total = [], [], 0.0

        with st.container(height=450, border=True):
            if m_opts_str:
                ids = [x.strip() for x in str(m_opts_str).split(",") if x.strip()]
                if ids:
                    placeholders = ",".join("?" * len(ids))
                    opts = get_factory(f"SELECT id, opt_name, opt_price, opt_desc, opt_image, allow_qty FROM options WHERE id IN ({placeholders}) ORDER BY sort_order ASC, id ASC", tuple(ids))
                    
                    for o in opts:
                        o_id = o[0]; o_name = o[1]; o_price = o[2]; o_desc = o[3]; o_img = o[4]
                        allow_qty = bool(o[5]) if len(o) > 5 and o[5] is not None else True
                        d_o_p = o_price * multiplier

                        with st.container(border=True):
                            c_img, c_info, c_act = st.columns([1.5, 3, 1.5], vertical_alignment="center")
                            
                            img_b64 = get_image_base64(o_img)
                            if img_b64:
                                c_img.markdown(f'<img src="{img_b64}" style="width:100%; max-height:80px; object-fit:contain; border-radius:6px; border:1px solid #e2e8f0; padding:2px;">', unsafe_allow_html=True)
                            else:
                                c_img.markdown("<div style='width:100%; height:80px; background:#f8fafc; border-radius:6px; border:1px dashed #cbd5e1; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:11px;'>Görsel Yok</div>", unsafe_allow_html=True)

                            c_info.markdown(f"<div style='font-size:14px; font-weight:800; color:#1e293b; line-height:1.2;'>{o_name}</div>", unsafe_allow_html=True)
                            c_info.markdown(f"<div style='font-size:15px; font-weight:900; color:#ea580c; margin-top:5px;'>+{d_o_p:,.0f} {m_curr}</div>", unsafe_allow_html=True)

                            is_sel = c_act.toggle("Sepete Ekle", key=f"tgl_{o_id}")

                            if is_sel:
                                if allow_qty:
                                    q_o = c_act.number_input("Adet", 1, 100, 1, key=f"q_{o_id}", label_visibility="collapsed")
                                else:
                                    q_o = 1
                                    c_act.markdown("<div style='text-align:center; padding:6px; margin-top:8px; background:#ecfdf5; color:#10b981; border:1px solid #a7f3d0; border-radius:4px; font-weight:bold; font-size:12px;'>Sabit 1 Adet</div>", unsafe_allow_html=True)
                                    
                                opts_total += (d_o_p * q_o)
                                selected_options_for_db.append({"id": o_id, "qty": q_o})
                                engine_options_list.append({'n': o_name, 'p': d_o_p, 'q': q_o, 'i': o_img, 'd': o_desc})
                else:
                    st.info("Bu makineye tanımlı donanım bulunmuyor.")

        st.markdown("<div style='font-size:13px; font-weight:800; color:#2563eb; margin-top:15px; margin-bottom:8px;'>4. FİYATLANDIRMA VE KAYIT</div>", unsafe_allow_html=True)
        with st.container(border=True):
            sub = ((m_price * multiplier) * m_qty) + opts_total

            c_disc, c_man = st.columns(2)
            disc_p = c_disc.number_input("İskonto Oranı (%)", 0.0, 100.0, float(wd.get("disc_p", 0.0)), step=0.5)
            calc_val = sub * (1 - (disc_p/100.0))

            use_manual = c_man.checkbox("Nihai Tutarı El İle Yaz", value=wd.get("is_manual", False))

            if use_manual:
                default_agreed = float(wd.get("agreed_price", calc_val))
                if default_agreed == 0.0: default_agreed = calc_val
                agreed = st.number_input("Müşteriye Sunulacak Net Tutar", value=default_agreed, step=50.0)
            else:
                agreed = calc_val
                st.info(f"Hesaplanan Toplam: **{agreed:,.2f} {m_curr}**")

            conds = {
                "machine_qty": m_qty, "agreed_price": agreed, "subtotal_calculated": sub, 
                "delivery_type": d_type, "delivery_time": d_time, "shipping": ship, 
                "payment_plan_text": pay, "bank": bnk, "notes": nts, 
                "discount_pct": disc_p, "is_manual": use_manual
            }

            btn_txt = "💾 GÜNCELLE" if is_edit else "💾 KAYDET"
            if st.button(btn_txt, type="primary", use_container_width=True):
                try:
                    tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    if is_edit:
                        exec_sales("UPDATE offers SET customer_id=?, model_id=?, total_price=?, conditions=? WHERE id=?", 
                                   (cust_id, m_id, agreed, json.dumps(conds), st.session_state.edit_offer_id))
                        exec_sales("DELETE FROM offer_items WHERE offer_id=?", (st.session_state.edit_offer_id,))
                        for item in selected_options_for_db: 
                            exec_sales("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", 
                                       (st.session_state.edit_offer_id, item["id"], item["qty"]))
                        st.success("Teklif Başarıyla Güncellendi!")
                        del st.session_state.edit_offer_id
                    else:
                        exec_sales("INSERT INTO offers (customer_id, model_id, total_price, user_id, offer_date, status, conditions) VALUES (?,?,?,?,?,?,?)", 
                                   (cust_id, m_id, agreed, user_id, tarih, "Beklemede", json.dumps(conds)))
                        res_id = get_sales("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
                        if res_id and selected_options_for_db:
                            for item in selected_options_for_db: 
                                exec_sales("INSERT INTO offer_items (offer_id, option_id, quantity) VALUES (?,?,?)", 
                                           (res_id[0][0], item["id"], item["qty"]))
                        st.success("Başarıyla Arşivlendi!")
                    st.balloons()
                except Exception as e: st.error(f"Kayıt Hatası: {e}")

    with col_prev:
        st.markdown("<div style='font-size:16px; font-weight:800; color:#0f172a; margin-bottom:10px;'>📄 A4 RAPOR ÖNİZLEMESİ</div>", unsafe_allow_html=True)
        html = generate_embedded_html(sel_cust, m_name, m_price*multiplier, m_img, m_specs, engine_options_list, conds, m_curr, user_id)
        with st.container(border=True): 
            components.html(html, height=1200, scrolling=True)
