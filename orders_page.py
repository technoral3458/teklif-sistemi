import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
import os
import base64
import ntpath
import posixpath

# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================
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

# =====================================================================
# ÜRETİM EMRİ PDF OLUŞTURUCU (ÇİNCE DESTEKLİ)
# =====================================================================
def generate_mfg_pdf(order_id, date, m_name, m_img, specs, opts, qty, lang="tr"):
    # Dil Etiketleri
    labels = {
        "tr": {"title": "ÜRETİM EMRİ", "m_name": "MAKİNE MODELİ", "qty": "Adet", "specs": "TEKNİK ÖZELLİKLER", "opts": "EKLENEN DONANIMLAR", "print": "🖨️ PDF YAZDIR", "no_opt": "Ekstra donanım seçilmedi."},
        "en": {"title": "PRODUCTION ORDER", "m_name": "MACHINE MODEL", "qty": "Qty", "specs": "TECHNICAL SPECS", "opts": "ADDED OPTIONS", "print": "🖨️ PRINT PDF", "no_opt": "No extra options selected."},
        "zh": {"title": "生产订单", "m_name": "机器型号", "qty": "数量", "specs": "技术规格", "opts": "附加选项", "print": "🖨️ 打印 PDF", "no_opt": "未选择任何额外选项。"}
    }
    lbl = labels.get(lang, labels["tr"])

    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 14px; color: #1e293b; background: #ffffff; margin:0; padding:0; display: flex; flex-direction: column; align-items: center; }
        .paper { background: #fff; width: 100%; max-width: 794px; min-height: 1123px; padding: 40px; border: 1px solid #e2e8f0; border-top: 8px solid #ea580c; box-sizing: border-box; overflow: hidden; margin: 0 auto 40px auto; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
        .section-title { background: #f8fafc; color: #0f172a; padding: 10px 15px; font-weight: 800; font-size: 14px; margin-top: 30px; border-left: 5px solid #ea580c; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 12px; text-align: left; vertical-align: middle; word-wrap: break-word; }
        .print-btn-container { width: 100%; max-width: 794px; margin: 0 auto 40px auto; text-align: center; }
        .print-btn { background: #10b981; color: white; border: none; padding: 15px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        @media print { .no-print { display: none !important; } .paper { border: none; padding: 0; margin: 0; width: 100%; max-width: 100%; min-height: auto; } body { background: #fff; padding: 0; } }
    """

    page_header_html = f"""<div class="header">
        <div style="font-size:24px; font-weight:900; color:#ea580c;">{lbl['title']}</div>
        <div style="text-align:right; font-size: 12px; color: #64748b;">Tarih/Date: {date}<br>No: TR-{order_id:04d}</div>
    </div>"""

    html = f"""
    <html><head><meta charset="utf-8"><style>{css}</style></head><body>
        <div class="paper">
            {page_header_html}
            <div style="text-align:center; padding: 15px 0;">
                <img src="{get_image_base64(m_img)}" style="max-width:100%; max-height:300px; object-fit:contain; display:block; margin:0 auto;"><br>
                <div style="font-size:12px; color:#64748b; font-weight:bold; letter-spacing:2px; margin-bottom:5px;">{lbl['m_name']}</div>
                <h2 style="color:#0f172a; margin:0 0 15px 0; font-size:26px; font-weight:900;">{m_name}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:15px; color:#475569; font-weight:bold;">
                    {lbl['qty']}: <span style="color:#ea580c;">{qty}</span>
                </div>
            </div>
    """

    # TEKNİK ÖZELLİKLER
    if specs:
        html += f'<div class="section-title">🔍 {lbl["specs"]}</div><table>'
        for s in specs:
            img_b64 = get_image_base64(s['img'])
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:60px; object-fit:contain; border-radius:4px;">' if img_b64 else "-"
            html += f'<tr><td style="width:20%; text-align:center;">{img_tag}</td><td><b>{s["title"]}</b><br><small style="color:#64748b;">{s["detail"]}</small></td></tr>'
        html += "</table>"

    # DONANIMLAR
    html += f'<div class="section-title">📦 {lbl["opts"]}</div>'
    if opts:
        html += f'<table><tr style="background:#f8fafc;"><th style="width:20%; text-align:center;">IMG</th><th>Detail</th><th style="width:15%; text-align:center;">{lbl["qty"]}</th></tr>'
        for o in opts:
            img_b64 = get_image_base64(o['img'])
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:60px; object-fit:contain; border-radius:4px;">' if img_b64 else "-"
            html += f'<tr><td style="text-align:center;">{img_tag}</td><td><b style="color:#2563eb;">+ {o["name"]}</b></td><td style="text-align:center; font-weight:bold;">{o["qty"]}</td></tr>'
        html += "</table>"
    else:
        html += f'<div style="padding:20px; text-align:center; color:#94a3b8; font-style:italic;">{lbl["no_opt"]}</div>'

    html += f"""
        </div>
        <div class="no-print print-btn-container"><button class="print-btn" onclick="window.print()">{lbl['print']}</button></div>
        </body></html>"""
    
    return html

# =====================================================================
# SİPARİŞLER ANA EKRANI
# =====================================================================
def show_orders(user_id, is_admin=False):
    st.header("📦 Sipariş Yönetimi")
    st.markdown("<p style='color:#64748b; margin-top:-10px; margin-bottom:20px;'>Onaylanan siparişleri ve üretim emirlerini buradan takip edebilirsiniz.</p>", unsafe_allow_html=True)
    
    # KULLANICI DİLİNİ AL (ÇİNCE KONTROLÜ İÇİN)
    sys_lang = st.session_state.get('lang', 'tr').lower()
    
    # 1. KULLANICI ROLÜNÜ TESPİT ET
    u_role = 'dealer'
    if is_admin:
        u_role = 'admin'
    else:
        u_type_res = get_users("SELECT user_type FROM users WHERE id=?", (user_id,))
        if u_type_res and u_type_res[0][0] == 'Üretici':
            u_role = 'manufacturer'

    # 2. SİPARİŞLERİ ÇEK
    offers = []
    if u_role == 'manufacturer':
        my_models = get_factory("SELECT id FROM models WHERE user_id=?", (user_id,))
        my_model_ids = [str(m[0]) for m in my_models]
        if my_model_ids:
            placeholders = ",".join(my_model_ids)
            offers = get_sales(f"SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') AND model_id IN ({placeholders}) ORDER BY id DESC")
    elif u_role == 'admin':
        offers = get_sales("SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') ORDER BY id DESC")
    else:
        offers = get_sales("SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') AND user_id=? ORDER BY id DESC", (user_id,))

    if not offers:
        st.info("Sistemde henüz onaylanmış bir sipariş bulunmuyor.")
        return

    st.markdown("<div style='font-size:13px; font-weight:bold; color:#64748b; margin-bottom:15px;'>TOPLAM " + str(len(offers)) + " SİPARİŞ BULUNDU</div>", unsafe_allow_html=True)
    
    # 3. KARTLARI ÇİZ
    for o in offers:
        o_id, c_id, m_id, t_price, o_date, ord_date, status, conds_str, dealer_id = o
        
        # JSON Çözümleme
        try: conds = json.loads(conds_str)
        except: conds = {}
        qty = conds.get("machine_qty", 1)
        
        # MAKİNE BİLGİLERİNİ ÇEK
        m_info = get_factory("SELECT name, name_zh, specs, specs_zh, image_path, currency FROM models WHERE id=?", (m_id,))
        if not m_info: continue
        
        m_name_tr, m_name_zh, m_specs_tr, m_specs_zh, m_img, m_curr = m_info[0]
        
        # DİLE GÖRE İSİM VE ÖZELLİK SEÇİMİ
        final_m_name = m_name_zh if sys_lang == 'zh' and m_name_zh else m_name_tr
        raw_specs = m_specs_zh if sys_lang == 'zh' and m_specs_zh else m_specs_tr
        
        parsed_specs = []
        if raw_specs:
            for item in str(raw_specs).split("||"):
                if item.strip():
                    parts = item.split("|")
                    parsed_specs.append({"title": parts[0].strip() if len(parts)>0 else "", "detail": parts[1].strip() if len(parts)>1 else "", "img": parts[2].strip() if len(parts)>2 else ""})
                    
        # EKLENEN DONANIMLARI ÇEK
        parsed_opts = []
        items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (o_id,))
        if items:
            for opt_id, o_qty in items:
                opt_info = get_factory("SELECT opt_name, opt_name_zh, opt_image FROM options WHERE id=?", (opt_id,))
                if opt_info:
                    o_n_tr, o_n_zh, o_img = opt_info[0]
                    final_o_name = o_n_zh if sys_lang == 'zh' and o_n_zh else o_n_tr
                    parsed_opts.append({"name": final_o_name, "qty": o_qty, "img": o_img})

        # =====================================================
        # ÜRETİCİ EKRANI (Fiyat, Bayi, Müşteri YOK!)
        # =====================================================
        if u_role == 'manufacturer':
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 4, 1], vertical_alignment="center")
                
                # Sipariş Numarası
                c1.markdown(f"""<div style='background:#fff7ed; padding:15px 5px; border-radius:8px; text-align:center; border:1px solid #ffedd5;'>
                    <b style='color:#ea580c; font-size:16px;'>TR-{o_id:04d}</b><br>
                    <span style='color:#64748b; font-size:12px; font-weight:600;'>{ord_date or o_date}</span>
                </div>""", unsafe_allow_html=True)
                
                # Makine Bilgisi
                c2.markdown(f"""<div style='line-height:1.4;'>
                    <b style='color:#0f172a; font-size:18px;'>{final_m_name}</b><br>
                    <span style='color:#475569; font-size:14px;'><b>{'数量 (Adet)' if sys_lang=='zh' else 'Adet'}:</b> {qty}</span><br>
                    <span style='display:inline-block; margin-top:5px; padding:3px 10px; background:#dcfce7; color:#10b981; border-radius:4px; font-size:12px; font-weight:bold;'>{status}</span>
                </div>""", unsafe_allow_html=True)
                
                # Açılır Kutu ve PDF
                with st.expander("📌 " + ("技术细节和生产订单" if sys_lang=='zh' else "Üretim Emri & Teknik Detaylar")):
                    pdf_html = generate_mfg_pdf(o_id, (ord_date or o_date), final_m_name, m_img, parsed_specs, parsed_opts, qty, sys_lang)
                    components.html(pdf_html, height=800, scrolling=True)

        # =====================================================
        # ADMİN VE BAYİ EKRANI (Standart Görünüm)
        # =====================================================
        else:
            c_info = get_sales("SELECT company_name FROM customers WHERE id=?", (c_id,))
            c_name = c_info[0][0] if c_info else "Bilinmeyen Müşteri"
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 2.5, 1.5], vertical_alignment="center")
                c1.markdown(f"""<div style='background:#f1f5f9; padding:15px 5px; border-radius:8px; text-align:center; border:1px solid #e2e8f0;'>
                    <b style='color:#2563eb; font-size:16px;'>TR-{o_id:04d}</b><br>
                    <span style='color:#64748b; font-size:12px; font-weight:600;'>{ord_date or o_date}</span>
                </div>""", unsafe_allow_html=True)
                
                c2.markdown(f"""<div style='line-height:1.4;'>
                    <b style='color:#0f172a; font-size:15px;'>{final_m_name}</b><br>
                    <span style='color:#475569; font-size:13px;'><b>Adet:</b> {qty} Takım</span><br>
                    <span style='display:inline-block; margin-top:5px; padding:2px 8px; background:#dcfce7; color:#10b981; border-radius:4px; font-size:12px; font-weight:bold;'>{status}</span>
                </div>""", unsafe_allow_html=True)
                
                c3.markdown(f"""<div style='line-height:1.4; border-left:3px solid #cbd5e1; padding-left:10px;'>
                    <span style='color:#64748b; font-size:11px; font-weight:bold;'>NİHAİ MÜŞTERİ</span><br>
                    <b style='color:#0f172a; font-size:14px;'>🏢 {c_name}</b>
                </div>""", unsafe_allow_html=True)
                
                c4.markdown(f"""<div style='text-align:right; background:#fffbeb; padding:15px 10px; border-radius:8px; border:1px solid #fde68a;'>
                    <span style='font-size:11px; color:#b45309; font-weight:bold; text-transform:uppercase;'>NİHAİ TUTAR</span><br>
                    <span style='font-size:18px; font-weight:900; color:#ea580c;'>{t_price:,.2f} {m_curr}</span>
                </div>""", unsafe_allow_html=True)
