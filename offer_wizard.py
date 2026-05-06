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
    exec_sales("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT, authorized_person TEXT, phone TEXT, email TEXT, address_full TEXT, user_id INTEGER DEFAULT 1)""")
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
# RESİM OKUMA MOTORU VE A4 PDF TASARIMI
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
    agreed_price = conditions.get("agreed_price", 0)
    teklif_no = f"TR-{datetime.datetime.now().strftime('%y%m%d')}"

    try: u_info = get_user_query("SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (user_id,))[0]
    except: u_info = None
    
    comp_name = u_info[0] if u_info and u_info[0] else "ERSAN MAKİNE"
    comp_logo = u_info[1] if u_info and u_info[1] else ""
    comp_web = u_info[2] if u_info and u_info[2] else "www.ersanmakina.net"
    comp_adr = u_info[3] if u_info and u_info[3] else "Ersan Makine San. Tic. Ltd. Şti."
    comp_tel = u_info[4] if u_info and u_info[4] else ""

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
# ANA SİHİRBAZ EKRANI (TAMAMEN SADELEŞTİRİLDİ)
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    # Tüm o bozuk, dokunmayı engelleyen HİLELİ JS kodları SİLİNDİ!
    # CSS sadeleştirildi, sadece görünüm için tutuldu.
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
        div.st-emotion-cache-1jicfl2 { 
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
            padding: 1.5rem !important;
        }
        .stSelectbox label, .stTextInput label, .stNumberInput label, .stTextArea label {
            font-size: 13px !important; font-weight: 700 !important; color: #475569 !important; margin-bottom:4px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    my_custs = get_sales("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name ASC", (user_id,)) if not is_admin else get_sales("SELECT id, company_name FROM customers ORDER BY company_name ASC")
    if my_custs is None: my_custs = []

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
                    if key.startswith("o_") or key.startswith("q_") or key == "temp_del_type":
                        del st.session_state[key]
                st.rerun()

        st.markdown("<div style='font-size:14px; font-weight:900; color:#2563eb; margin-bottom:8px;'>1. MÜŞTERİ VE MAKİNE SEÇİMİ</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            
            # 🔥 EN SAĞLAM YÖNTEM: STANDART CHECKBOX KULLANILDI 🔥
            # Toggle bazen telefonlarda görünmez olur, checkbox her zaman çalışır.
            is_new_customer = st.checkbox("➕ Sistemde Kayıtlı Değilse Yeni Müşteri Ekle", key="chk_add_new_cust_pure")
            
            if is_new_customer:
                st.markdown("<div style='font-size:14px; font-weight:900; color:#ea580c; margin-top:10px; margin-bottom:10px;'>🆕 HIZLI MÜŞTERİ KAYDI</div>", unsafe_allow_html=True)
                
                nc_comp = st.text_input("Firma Adı (Zorunlu) *", placeholder="Örn: ABC Makine Ltd. Şti.")
                nc_auth = st.text_input("Yetkili Kişi", placeholder="Örn: Ahmet Yılmaz")
                
                c_tel, c_mail = st.columns(2)
                nc_phone = c_tel.text_input("Telefon", placeholder="05XX XXX XX XX")
                nc_email = c_mail.text_input("E-Posta", placeholder="info@firma.com")
                
                nc_addr = st.text_area("Açık Adres", height=80)
                
                if st.button("💾 MÜŞTERİYİ KAYDET VE DEVAM ET", type="primary", use_container_width=True):
                    if not nc_comp.strip():
                        st.error("Lütfen Firma Adını giriniz!")
                    else:
                        try:
                            exec_sales("INSERT INTO customers (company_name, authorized_person, phone, email, address_full, user_id) VALUES (?,?,?,?,?,?)", 
                                       (nc_comp.strip(), nc_auth.strip(), nc_phone.strip(), nc_email.strip(), nc_addr.strip(), user_id))
                            
                            st.session_state.new_added_cust = nc_comp.strip()
                            st.session_state.chk_add_new_cust_pure = False # Kayıt bitince Checkbox'ı kapat
                            st.rerun()
                        except Exception as e:
                            st.error(f"Kayıt Hatası: {e}")
                
                with col_prev:
                    st.info("💡 Lütfen yandaki formu doldurarak müşteriyi kaydedin.")
                return

            # --- CHECKBOX KAPALIYSA NORMAL LİSTE ÇALIŞIR ---
            CUST_PROMPT = "Lütfen Müşteri Seçiniz..."
            MACH_PROMPT = "Lütfen Makine Modeli Seçiniz..."

            c_names = [CUST_PROMPT] + [c[1] for c in my_custs]
            
            if "new_added_cust" in st.session_state and st.session_state.new_added_cust in c_names:
                idx_c = c_names.index(st.session_state.new_added_cust)
                del st.session_state.new_added_cust
            else:
                idx_c = c_names.index(wd.get("cust_name")) if wd.get("cust_name") in c_names else 0
            
            sel_cust = st.selectbox("Teklif Verilecek Müşteri", c_names, index=idx_c, key="pure_cust_sel")

            cats = ["Tüm Kategoriler"] + [c[0] for c in get_factory("SELECT name FROM categories ORDER BY name ASC")]
            idx_cat = cats.index(wd.get("category")) if wd.get("category") in cats else 0
            
            sel_cat = st.selectbox("Kategori Filtresi", cats, index=idx_cat, key="pure_cat_sel")

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
            
            sel_m = st.selectbox("Makine Modeli", m_names, index=idx_m, key="pure_mach_sel")
            
            m_qty = st.number_input("Makine Adedi", 1, 100, wd.get("qty", 1), key="pure_qty_sel")

        if sel_cust == CUST_PROMPT or sel_m == MACH_PROMPT:
            with col_prev:
                st.info("💡 Teklif detaylarını ve A4 raporunu görmek için lütfen yandaki panelden Müşteri ve Makine seçimi yapınız.")
            return

        cust_id = [c[0] for c in my_custs if c[1] == sel_cust][0]
        m_info = next(m for m in machines if m[1] == sel_m)
        m_id, m
