import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import datetime
import os
import base64
import json

def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def get_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def get_user_query(query, params=()):
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def get_image_base64(img_path):
    if not img_path: return ""
    paths_to_try = [img_path, f"images/{img_path}", f"../images/{img_path}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                    ext = os.path.splitext(p)[1].lower().replace('.', '')
                    return f"data:image/{ext if ext else 'png'};base64,{b64}"
            except: pass
    return ""

def show_proforma(offer_id, user_id):
    col1, col2 = st.columns([1, 5])
    if col1.button("🔙 Cari Sayfaya Dön", use_container_width=True):
        st.session_state.active_tab = ":busts_in_silhouette: Müşterilerim"
        st.rerun()
    
    col2.header("📄 Proforma Fatura Görüntüleyici")
    st.markdown("---")

    # Verileri Topla
    off_data = get_sales("SELECT customer_id, model_id, total_price, conditions, offer_date FROM offers WHERE id=?", (offer_id,))[0]
    cust_id, mod_id, total_price, conditions_str, offer_date = off_data
    conds = json.loads(conditions_str) if conditions_str else {}
    
    c_name = get_sales("SELECT company_name FROM customers WHERE id=?", (cust_id,))[0][0]
    
    m_data = get_factory("SELECT name, currency, image_path, base_price FROM models WHERE id=?", (mod_id,))[0]
    m_name, m_curr, m_img, m_base_price = m_data

    # Bayi Bilgileri
    try: u_info = get_user_query("SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (user_id,))[0]
    except: u_info = ["ERSAN MAKİNE", "", "www.ersanmakina.net", "Türkiye", ""]
    
    if not u_info[1]:
        try: u_info = list(u_info); u_info[1] = get_factory("SELECT logo_path FROM company_profile WHERE id=1")[0][0]
        except: pass

    logo_b64 = get_image_base64(u_info[1])
    header_logo = f'<img src="{logo_b64}" style="max-height:80px;">' if logo_b64 else f'<div style="font-size:24px; font-weight:900;">{u_info[0]}</div>'

    # Donanımları Çek
    opt_items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (offer_id,))
    opts_html = ""
    for op_id, qty in opt_items:
        o_data = get_factory("SELECT opt_name, opt_price FROM options WHERE id=?", (op_id,))
        if o_data:
            opts_html += f"<tr><td style='padding:8px; border-bottom:1px solid #e2e8f0;'>+ {o_data[0][0]}</td><td style='text-align:center; border-bottom:1px solid #e2e8f0;'>{qty}</td></tr>"

    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
        body { font-family: 'Inter', sans-serif; background: #cbd5e1; padding: 20px; display: flex; justify-content: center; margin:0;}
        .paper { background: white; width: 100%; max-width: 800px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-top: 10px solid #10b981; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px; }
        .title { color: #10b981; font-size: 28px; font-weight: 900; letter-spacing: 2px; }
        .info-box { display: flex; justify-content: space-between; background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th { background: #0f172a; color: white; padding: 12px; text-align: left; }
        .total-box { border: 2px solid #10b981; background: #ecfdf5; padding: 20px; text-align: right; font-size: 24px; font-weight: 900; color: #065f46; border-radius: 8px; }
        .bank-box { margin-top: 30px; padding: 20px; border: 1px dashed #94a3b8; border-radius: 8px; font-size: 12px; color: #475569; }
        .print-btn { background: #0f172a; color: white; border: none; padding: 15px; width: 100%; max-width: 800px; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 6px; margin-bottom: 20px; }
        @media print { .no-print { display: none !important; } .paper { box-shadow: none; border: none; padding: 0; width: 100%; max-width: 100%; } body { background: white; padding: 0; } }
    """

    html = f"""
    <html><head><style>{css}</style></head><body>
        <div style="width:100%; display:flex; flex-direction:column; align-items:center;">
        <button class="print-btn no-print" onclick="window.print()">🖨️ PDF OLARAK KAYDET / YAZDIR</button>
        <div class="paper">
            <div class="header">
                <div>{header_logo}</div>
                <div style="text-align:right;">
                    <div class="title">PROFORMA INVOICE</div>
                    <div style="color:#64748b; margin-top:5px;">Tarih: {datetime.datetime.now().strftime("%d.%m.%Y")}</div>
                    <div style="color:#64748b;">Belge No: PRF-{offer_id}{datetime.datetime.now().strftime("%y%m")}</div>
                </div>
            </div>
            
            <div class="info-box">
                <div>
                    <h4 style="margin:0 0 10px 0; color:#0f172a;">ALICI (MÜŞTERİ)</h4>
                    <b style="font-size:16px;">{c_name}</b><br>
                </div>
                <div style="text-align:right;">
                    <h4 style="margin:0 0 10px 0; color:#0f172a;">SATICI (BAYİ)</h4>
                    <b>{u_info[0]}</b><br>
                    <small>{u_info[3]}<br>{u_info[4]}</small>
                </div>
            </div>

            <table>
                <tr><th>Ürün Açıklaması</th><th style="text-align:center;">Adet</th></tr>
                <tr><td style="padding:12px; border-bottom:1px solid #e2e8f0; font-weight:bold; font-size:16px;">{m_name} (Standart Donanım)</td><td style="text-align:center; border-bottom:1px solid #e2e8f0; font-weight:bold; font-size:16px;">{conds.get('machine_qty', 1)}</td></tr>
                {opts_html}
            </table>

            <div class="total-box">
                GENEL TOPLAM: {total_price:,.2f} {m_curr}
            </div>

            <div class="bank-box">
                <b style="color:#0f172a;">TİCARİ ŞARTLAR VE BANKA BİLGİLERİ</b><br><br>
                <b>Ödeme Şekli:</b> {conds.get('payment_plan_text', 'Belirtilmedi')}<br>
                <b>Teslimat Süresi:</b> {conds.get('delivery_time', 'Belirtilmedi')}<br>
                <b>Banka Hesap Bilgileri:</b><br>
                {conds.get('bank', 'Banka bilgisi teklif aşamasında belirtilmemiştir.')}
            </div>
            
            <div style="margin-top:50px; display:flex; justify-content:space-between; text-align:center; padding:0 40px;">
                <div><br><br>____________________<br><b>ALICI ONAYI</b><br>Kaşe / İmza</div>
                <div><br><br>____________________<br><b>SATICI ONAYI</b><br>Kaşe / İmza</div>
            </div>
        </div>
        </div>
    </body></html>
    """
    
    with st.container(border=True):
        components.html(html, height=1000, scrolling=True)
