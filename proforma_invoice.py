import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import datetime
import base64
import json
import os

def get_db_data(db_name, query, params=()):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    res = conn.execute(query, params).fetchall()
    conn.close()
    return res

def get_image_base64(img_path):
    if not img_path: return ""
    paths = [img_path, f"images/{img_path}", f"../images/{img_path}"]
    for p in paths:
        if os.path.exists(p) and os.path.isfile(p):
            with open(p, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return ""

def show_proforma(offer_id, bayi_id):
    col1, col2 = st.columns([1, 5])
    if col1.button("🔙 Cari Sayfaya Dön"):
        st.session_state.active_tab = ":busts_in_silhouette: Müşterilerim"
        st.rerun()
    
    off = get_db_data('sales_data.db', "SELECT customer_id, model_id, total_price, conditions FROM offers WHERE id=?", (offer_id,))[0]
    cust = get_db_data('sales_data.db', "SELECT company_name, address, phone FROM customers WHERE id=?", (off[0],))[0]
    mod = get_db_data('factory_data.db', "SELECT name, currency FROM models WHERE id=?", (off[1],))[0]
    try:
        bayi = get_db_data('users.db', "SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (bayi_id,))[0]
    except:
        bayi = ["ERSAN MAKİNE", "", "www.ersanmakina.net", "Türkiye", ""]

    conds = json.loads(off[3]) if off[3] else {}

    logo_b64 = get_image_base64(bayi[1])
    if not logo_b64:
        try:
            sys_logo = get_db_data('factory_data.db', "SELECT logo_path FROM company_profile WHERE id=1")[0][0]
            logo_b64 = get_image_base64(sys_logo)
        except: pass

    header_logo = f'<img src="{logo_b64}" style="max-height:80px;">' if logo_b64 else f'<h2>{bayi[0]}</h2>'

    # Donanımları Çek
    opt_items = get_db_data('sales_data.db', "SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (offer_id,))
    opts_html = ""
    for op_id, qty in opt_items:
        o_data = get_db_data('factory_data.db', "SELECT opt_name, opt_price FROM options WHERE id=?", (op_id,))
        if o_data:
            opts_html += f"<tr><td style='padding:12px; border-bottom:1px solid #ddd;'>+ {o_data[0][0]}</td><td style='padding:12px; border-bottom:1px solid #ddd; text-align:center;'>{qty}</td><td style='padding:12px; border-bottom:1px solid #ddd; text-align:right;'>Dahil</td></tr>"

    html = f"""
    <html><body style="font-family:sans-serif; padding:30px; border:1px solid #eee; max-width:800px; margin:auto;">
        <div style="display:flex; justify-content:space-between; border-bottom:5px solid #10b981; padding-bottom:20px;">
            <div>{header_logo}</div>
            <div style="text-align:right;">
                <h1 style="color:#10b981; margin:0;">PROFORMA INVOICE</h1>
                <p>Tarih: {datetime.datetime.now().strftime("%d.%m.%Y")}<br>No: PRF-{offer_id}</p>
            </div>
        </div>
        <div style="margin:30px 0; display:flex; justify-content:space-between; gap:20px;">
            <div style="flex:1;"><b>ALICI (CUSTOMER):</b><br>{cust[0]}<br>{cust[1]}<br>Tel: {cust[2]}</div>
            <div style="flex:1; text-align:right;"><b>SATICI (SELLER):</b><br>{bayi[0]}<br>{bayi[3]}<br>Tel: {bayi[4]}<br>{bayi[2]}</div>
        </div>
        <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
            <tr style="background:#f4f4f4;">
                <th style="padding:12px; border:1px solid #ddd; text-align:left;">Açıklama</th>
                <th style="padding:12px; border:1px solid #ddd; text-align:center;">Adet</th>
                <th style="padding:12px; border:1px solid #ddd; text-align:right;">Tutar</th>
            </tr>
            <tr>
                <td style="padding:12px; border:1px solid #ddd; font-weight:bold;">{mod[0]} (Standart Donanım)</td>
                <td style="padding:12px; border:1px solid #ddd; text-align:center; font-weight:bold;">{conds.get('machine_qty',1)}</td>
                <td style="padding:12px; border:1px solid #ddd; text-align:right; font-weight:bold;">Ana Fiyat</td>
            </tr>
            {opts_html}
        </table>
        <div style="text-align:right; font-size:22px; font-weight:bold; color:#10b981;">GENEL TOPLAM: {off[2]:,.2f} {mod[1]}</div>
        <div style="margin-top:40px; font-size:12px; border-top:1px solid #ddd; padding-top:20px; color:#475569;">
            <b>Ödeme Şartı:</b> {conds.get('payment_plan_text','')}<br><br>
            <b>Teslimat Süresi:</b> {conds.get('delivery_time','')}<br><br>
            <b>Banka Bilgileri:</b><br>{conds.get('bank','')}
        </div>
        <div style="margin-top:50px; display:flex; justify-content:space-between; text-align:center;">
            <div><br><br>____________________<br><b>ALICI ONAYI</b><br>Kaşe / İmza</div>
            <div><br><br>____________________<br><b>SATICI ONAYI</b><br>Kaşe / İmza</div>
        </div>
        <button class="no-print" style="margin-top:40px; padding:15px; background:#10b981; color:white; border:none; width:100%; cursor:pointer; font-weight:bold; border-radius:5px;" onclick="window.print()">🖨️ YAZDIR / PDF KAYDET</button>
        <style>@media print {{ .no-print {{ display:none; }} }}</style>
    </body></html>
    """
    components.html(html, height=1000, scrolling=True)
