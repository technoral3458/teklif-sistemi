import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import os
import base64
import ntpath
import posixpath

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

def get_users(query, params=()):
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

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

def render_proforma(offer_id, date, c_name, m_id, m_name, t_price, curr, conds, dealer_id):
    # 1. Makine Özelliklerini Çek
    m_info_full = get_factory("SELECT image_path, specs FROM models WHERE id=?", (m_id,))
    m_img = m_info_full[0][0] if m_info_full else ""
    raw_specs = m_info_full[0][1] if m_info_full else ""
    
    parsed_specs = []
    if raw_specs:
        for item in str(raw_specs).split("||"):
            if item.strip():
                parts = item.split("|")
                parsed_specs.append({"title": parts[0].strip() if len(parts)>0 else "", "detail": parts[1].strip() if len(parts)>1 else "", "img": parts[2].strip() if len(parts)>2 else ""})
    
    # 2. Ekstra Donanımları Çek
    parsed_opts = []
    items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (offer_id,))
    if items:
        for opt_id, o_qty in items:
            opt_info = get_factory("SELECT opt_name, opt_price, opt_image FROM options WHERE id=?", (opt_id,))
            if opt_info: parsed_opts.append({"name": opt_info[0][0], "price": opt_info[0][1], "qty": o_qty, "img": opt_info[0][2]})

    # 3. Bayi/Satıcı Bilgilerini Çek
    u_info = get_users("SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (dealer_id,))
    comp_name = u_info[0][0] if u_info and u_info[0][0] else "ERSAN MAKİNE"
    comp_logo = u_info[0][1] if u_info and u_info[0][1] else ""
    comp_web = u_info[0][2] if u_info and u_info[0][2] else "www.ersanmakina.net"
    comp_adr = u_info[0][3] if u_info and u_info[0][3] else ""
    comp_tel = u_info[0][4] if u_info and u_info[0][4] else ""

    if not comp_logo:
        fac_logo = get_factory("SELECT logo_path FROM company_profile WHERE id=1")
        if fac_logo and fac_logo[0][0]: comp_logo = fac_logo[0][0]

    logo_b64 = get_image_base64(comp_logo)
    header_logo_html = f'<img src="{logo_b64}" style="max-height:70px; width:auto; object-fit:contain;">' if logo_b64 else f'<div style="font-size:22px; font-weight:900; color:#1e293b;">{comp_name}</div>'

    qty = conds.get("machine_qty", 1)

    # 4. Tasarım (CSS)
    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 14px; color: #1e293b; background: #f8fafc; margin:0; padding:10px; display: flex; flex-direction: column; align-items: center; }
        .paper { background: #fff; width: 100%; max-width: 794px; padding: 40px; border: 1px solid #e2e8f0; border-top: 8px solid #2563eb; box-sizing: border-box; overflow: hidden; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .section-title { background: #f8fafc; color: #0f172a; padding: 10px 15px; font-weight: 800; font-size: 14px; margin-top: 30px; border-left: 5px solid #2563eb; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 12px; text-align: left; vertical-align: middle; word-wrap: break-word; }
        .price-box { background: #fffbeb; border: 1px solid #fde68a; padding: 20px; text-align: right; margin-top: 35px; border-radius: 6px; }
        .total-price { font-size: 30px; font-weight: 900; color: #ea580c; word-break: break-all; }
        .elegant-conditions { margin-top: 35px; background: #f8fafc; padding: 20px; border-left: 5px solid #eab308; }
        .footer-info { margin-top:30px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:15px; }
        .print-btn-container { width: 100%; max-width: 794px; margin: 20px auto 0 auto; text-align: center; }
        .print-btn { background: #ea580c; color: white; border: none; padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer; font-weight: bold; width:100%; transition: 0.2s;}
        .print-btn:hover { background: #c2410c; }
        @media print {
            .no-print { display: none !important; }
            .paper { border: none; padding: 0; margin: 0; width: 100%; max-width: 100%; box-shadow: none; border-top: 8px solid #2563eb; }
            body { background: #fff; padding: 0; }
        }
    """

    # 5. HTML İçerik
    html = f"""
    <html><head><meta charset="utf-8"><style>{css}</style></head><body>
        <div class="paper">
            <div class="header"><div>{header_logo_html}</div><div style="text-align:right; font-size: 12px; color: #64748b;"><b>{comp_web}</b><br>Tarih: {date}<br>Teklif No: TR-{offer_id:04d}</div></div>
            <div style="text-align:center; padding: 15px 0;">
                <img src="{get_image_base64(m_img)}" style="max-width:100%; max-height:300px; object-fit:contain; display:block; margin:0 auto;"><br>
                <h2 style="color:#0f172a; margin:15px 0; font-size:24px; font-weight:900;">MODEL: {m_name}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:15px; color:#475569;">
                    Sayın Yetkili: <b style="color:#0f172a;">{c_name}</b> | Adet: <b style="color:#ea580c;">{qty}</b>
                </div>
            </div>
    """

    if parsed_specs:
        html += '<div class="section-title">🔍 MAKİNE STANDART ÖZELLİKLERİ</div><table>'
        for s in parsed_specs:
            img_b64 = get_image_base64(s['img'])
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:80px; object-fit:contain; border-radius:6px;">' if img_b64 else "-"
            html += f'<tr><td style="width:25%; text-align:center;">{img_tag}</td><td><b>{s["title"]}</b><br><small style="color:#64748b;">{s["detail"]}</small></td></tr>'
        html += "</table>"

    if parsed_opts:
        html += f"""<div class="section-title">📦 SEÇİLEN EKSTRA DONANIMLAR</div><table><tr style="background:#f8fafc;"><th style="width:25%; text-align:center;">Görsel</th><th style="width:40%;">Açıklama</th><th style="width:10%; text-align:center;">Adet</th><th style="width:25%; text-align:right;">Tutar</th></tr>"""
        for o in parsed_opts:
            opt_img_b64 = get_image_base64(o["img"])
            opt_img_tag = f'<img src="{opt_img_b64}" style="max-width:100%; max-height:80px; object-fit:contain; border-radius:6px;">' if opt_img_b64 else "-"
            html += f"<tr><td style='text-align:center;'>{opt_img_tag}</td><td><b style='color:#2563eb;'>+ {o['name']}</b></td><td style='text-align:center; font-weight:bold;'>{o['qty']}</td><td style='text-align:right; font-weight:bold;'>{(o['price']*o['qty']):,.2f} {curr}</td></tr>"
        html += "</table>"

    html += f"""
        <div class="elegant-conditions">
            <div style="font-size: 15px; font-weight: bold; color: #1e293b; border-bottom: 2px solid #cbd5e1; padding-bottom: 8px; margin-bottom: 12px;">📌 Ticari ve Teknik Şartlar</div>
            <table>
                <tr><td style="width:35%;"><b>Teslimat Şekli:</b></td><td style="color:#ea580c; font-weight:bold;">{conds.get('delivery_type','')}</td></tr>
                <tr><td><b>Teslim Süresi:</b></td><td>{conds.get('delivery_time','')}</td></tr>
                <tr><td><b>Nakliye:</b></td><td>{conds.get('shipping','')}</td></tr>
                <tr><td><b>Ödeme Planı:</b></td><td>{conds.get('payment_plan_text','')}</td></tr>
            </table>
        </div>
        <div class="price-box">
            <div style="font-size:14px; font-weight:bold; color:#ea580c;">GENEL TOPLAM (Nihai Fiyat)</div>
            <div class="total-price">{t_price:,.2f} {curr}</div>
        </div>
        <div class="footer-info">{comp_adr} | {comp_tel}</div>
        </div>
        <div class="no-print print-btn-container"><button class="print-btn" onclick="window.print()">🖨️ PDF YAZDIR / İNDİR</button></div>
        </body></html>"""
    
    components.html(html, height=800, scrolling=True)
