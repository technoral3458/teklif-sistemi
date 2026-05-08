import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import datetime
import json
import os
import base64
import ntpath
import posixpath

# =====================================================================
# YARDIMCI FONKSİYONLAR VE VERİTABANI
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

def exec_sales(query, params=()):
    try:
        conn = sqlite3.connect('sales_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
    except Exception as e: st.error(f"DB Error: {e}")

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
# A4 PROFORMA ÖNİZLEME OLUŞTURUCU VE YAZDIRMA (HTML)
# =====================================================================
def generate_proforma_html(offer_id, date, c_name, m_name, m_img, specs, opts, t_price, curr, conds, dealer_id):
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

    if specs:
        html += '<div class="section-title">🔍 MAKİNE STANDART ÖZELLİKLERİ</div><table>'
        for s in specs:
            img_b64 = get_image_base64(s['img'])
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:80px; object-fit:contain; border-radius:6px;">' if img_b64 else "-"
            html += f'<tr><td style="width:25%; text-align:center;">{img_tag}</td><td><b>{s["title"]}</b><br><small style="color:#64748b;">{s["detail"]}</small></td></tr>'
        html += "</table>"

    if opts:
        html += f"""<div class="section-title">📦 SEÇİLEN EKSTRA DONANIMLAR</div><table><tr style="background:#f8fafc;"><th style="width:25%; text-align:center;">Görsel</th><th style="width:40%;">Açıklama</th><th style="width:10%; text-align:center;">Adet</th><th style="width:25%; text-align:right;">Tutar</th></tr>"""
        for o in opts:
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
    return html

# =====================================================================
# TEKLİF LİSTESİ VE DURUM YÖNETİMİ
# =====================================================================
def show_offer_management(user_id, user_role):
    st.header("📋 Teklif Listesi ve Durum Yönetimi")
    st.markdown("<p style='color:#64748b; margin-top:-10px; margin-bottom:20px;'>Oluşturduğunuz teklifleri takip edebilir, siparişe çevirmek için yönetici onayına gönderebilirsiniz.</p>", unsafe_allow_html=True)
    
    u_role = 'dealer'
    if user_role == 'admin': u_role = 'admin'
    else:
        u_type_res = get_users("SELECT user_type FROM users WHERE id=?", (user_id,))
        if u_type_res and u_type_res[0][0] == 'Üretici': u_role = 'manufacturer'

    with st.expander("🔍 Filtreleme Seçenekleri", expanded=True):
        status_opts = ["Tümü", "Beklemede", "Onay Bekliyor", "Onaylandı", "İptal Edildi / Reddedildi"]
        selected_status = st.selectbox("Durum Seçimi", status_opts, index=0)
        
    query = "SELECT id, customer_id, model_id, total_price, offer_date, status, user_id, conditions FROM offers"
    params = []
    conds_query = []
    
    if u_role != "admin":
        conds_query.append("user_id=?")
        params.append(user_id)
        
    if selected_status != "Tümü":
        if selected_status == "İptal Edildi / Reddedildi":
            conds_query.append("status IN ('İptal Edildi', 'Reddedildi')")
        else:
            conds_query.append("status=?")
            params.append(selected_status)
        
    if conds_query: query += " WHERE " + " AND ".join(conds_query)
    query += " ORDER BY id DESC"
    
    offers = get_sales(query, tuple(params))
    
    if not offers:
        st.info("Bu kriterlere uygun teklif bulunamadı.")
        return
        
    st.markdown(f"<div style='font-size:13px; font-weight:bold; color:#64748b; margin-bottom:15px;'>TOPLAM {len(offers)} TEKLİF BULUNDU</div>", unsafe_allow_html=True)
    
    for o in offers:
        o_id, c_id, m_id, t_price, o_date, status, o_user_id, conds_str = o
        
        try: conds_json = json.loads(conds_str) if conds_str else {}
        except: conds_json = {}
        
        c_info = get_sales("SELECT company_name FROM customers WHERE id=?", (c_id,))
        c_name = c_info[0][0] if c_info else "Bilinmeyen Müşteri"
        
        m_info = get_factory("SELECT name, currency FROM models WHERE id=?", (m_id,))
        m_name = m_info[0][0] if m_info else "Bilinmeyen Makine"
        m_curr = m_info[0][1] if m_info else "USD"
        
        d_info = get_users("SELECT company_name FROM users WHERE id=?", (o_user_id,))
        d_name = d_info[0][0] if d_info else "Bilinmeyen Kullanıcı"
        
        with st.container(border=True):
            col_head, col_price = st.columns([4, 1])
            col_head.markdown(f"<h3 style='margin:0; font-size:18px; color:#0f172a;'>🏢 {c_name}</h3>", unsafe_allow_html=True)
            col_head.markdown(f"<span style='color:#64748b; font-size:13px;'><b>Satıcı:</b> {d_name} | <b>Tarih:</b> {o_date} | <b>Makine:</b> <span style='color:#2563eb;'>{m_name}</span></span>", unsafe_allow_html=True)
            col_price.markdown(f"<div style='text-align:right; font-size:22px; font-weight:900; color:#ea580c;'>{t_price:,.2f} {m_curr}</div>", unsafe_allow_html=True)
            
            rejection_note = conds_json.get("rejection_note", "")
            if (status in ["İptal Edildi", "Reddedildi"]) and rejection_note:
                st.markdown(f"<div style='margin-top:10px; padding:10px; background-color:#fef2f2; border-left:4px solid #ef4444; color:#991b1b; font-size:13px;'><b>Yönetici Notu:</b> {rejection_note}</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin:12px 0 15px 0; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
            
            act = st.session_state.get(f"adm_act_{o_id}")
            
            # YÖNETİCİ ARAYÜZÜ (Önizleme veya Ret Ekranı)
            if u_role == "admin" and act in ["approve", "reject"]:
                if act == "approve":
                    st.markdown("<div style='background:#eff6ff; padding:15px; border-radius:8px; border:1px solid #bfdbfe;'><h4 style='color:#1e40af; margin-top:0;'>🔍 Ayrıntılı Teklif Formu Önizlemesi</h4>", unsafe_allow_html=True)
                    
                    m_info_full = get_factory("SELECT image_path, specs FROM models WHERE id=?", (m_id,))
                    m_img = m_info_full[0][0] if m_info_full else ""
                    raw_specs = m_info_full[0][1] if m_info_full else ""
                    
                    parsed_specs = []
                    if raw_specs:
                        for item in str(raw_specs).split("||"):
                            if item.strip():
                                parts = item.split("|")
                                parsed_specs.append({"title": parts[0].strip() if len(parts)>0 else "", "detail": parts[1].strip() if len(parts)>1 else "", "img": parts[2].strip() if len(parts)>2 else ""})
                    
                    parsed_opts = []
                    items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (o_id,))
                    if items:
                        for opt_id, o_qty in items:
                            opt_info = get_factory("SELECT opt_name, opt_price, opt_image FROM options WHERE id=?", (opt_id,))
                            if opt_info: parsed_opts.append({"name": opt_info[0][0], "price": opt_info[0][1], "qty": o_qty, "img": opt_info[0][2]})

                    html_content = generate_proforma_html(o_id, o_date, c_name, m_name, m_img, parsed_specs, parsed_opts, t_price, m_curr, conds_json, o_user_id)
                    components.html(html_content, height=600, scrolling=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.write("")
                    
                    cc1, cc2 = st.columns([1, 1])
                    if cc1.button("🚀 KESİN ONAYLA VE SİPARİŞLERE AKTAR", key=f"btn_conf_app_{o_id}", type="primary", use_container_width=True):
                        tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                        exec_sales("UPDATE offers SET status=?, order_date=? WHERE id=?", ("Onaylandı", tarih, o_id))
                        del st.session_state[f"adm_act_{o_id}"]
                        st.rerun()
                    if cc2.button("Vazgeç (Geri Dön)", key=f"btn_canc_app_{o_id}", use_container_width=True):
                        del st.session_state[f"adm_act_{o_id}"]
                        st.rerun()
                        
                elif act == "reject":
                    with st.container(border=True):
                        st.markdown("<b style='color:#ef4444;'>❌ Reddetme Sebebi (Satıcıya İletilecek):</b>", unsafe_allow_html=True)
                        rej_note = st.text_area("Notunuzu girin:", key=f"txt_rej_{o_id}", label_visibility="collapsed")
                        
                        cr1, cr2 = st.columns([1, 1])
                        if cr1.button("💾 Kaydet ve Reddet", key=f"btn_conf_rej_{o_id}", type="primary", use_container_width=True):
                            conds_json["rejection_note"] = rej_note
                            updated_conds = json.dumps(conds_json)
                            exec_sales("UPDATE offers SET status=?, conditions=? WHERE id=?", ("Reddedildi", updated_conds, o_id))
                            del st.session_state[f"adm_act_{o_id}"]
                            st.rerun()
                        if cr2.button("Vazgeç", key=f"btn_canc_rej_{o_id}", use_container_width=True):
                            del st.session_state[f"adm_act_{o_id}"]
                            st.rerun()
                            
            # NORMAL BUTONLAR
            else:
                c_stat, c_edit, c_prof, c_del = st.columns([2.5, 1, 1, 1], vertical_alignment="center")
                
                with c_stat:
                    if u_role == "admin":
                        if status in ["Beklemede", "Onay Bekliyor"]:
                            ca1, ca2 = st.columns(2)
                            if ca1.button("✅ Onayla", key=f"btn_app_{o_id}", type="primary", use_container_width=True):
                                st.session_state[f"adm_act_{o_id}"] = "approve"
                                st.rerun()
                            if ca2.button("❌ Reddet", key=f"btn_rej_{o_id}", use_container_width=True):
                                st.session_state[f"adm_act_{o_id}"] = "reject"
                                st.rerun()
                        elif status == "Onaylandı":
                            ca1, ca2 = st.columns([2.5, 1.5])
                            ca1.markdown("<div style='background:#dcfce7; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px; white-space:nowrap;'>✅ ONAYLANDI</div>", unsafe_allow_html=True)
                            if ca2.button("↩️ Geri", key=f"btn_rev_{o_id}", help="Onayı iptal edip beklemeye al", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                        else:
                            ca1, ca2 = st.columns([2.5, 1.5])
                            ca1.markdown("<div style='background:#fee2e2; color:#ef4444; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px; white-space:nowrap;'>❌ RED / İPTAL</div>", unsafe_allow_html=True)
                            if ca2.button("↩️ Geri", key=f"btn_rev2_{o_id}", help="Reddi iptal edip beklemeye al", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                    else:
                        if status == "Onaylandı":
                            st.markdown("<div style='background:#dcfce7; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>✅ ONAYLANDI (Siparişe Dönüştü)</div>", unsafe_allow_html=True)
                        elif status == "Onay Bekliyor":
                            cb1, cb2 = st.columns([2, 1])
                            cb1.markdown("<div style='background:#fef08a; color:#b45309; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>⏳ YÖNETİCİ ONAYI BEKLENİYOR</div>", unsafe_allow_html=True)
                            if cb2.button("Geri Çek", key=f"btn_dlr_pull_{o_id}", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Beklemede", o_id))
                                st.rerun()
                        elif status in ["İptal Edildi", "Reddedildi"]:
                            st.markdown("<div style='background:#fee2e2; color:#ef4444; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:13px;'>❌ REDDEDİLDİ / İPTAL</div>", unsafe_allow_html=True)
                        else:
                            cd1, cd2 = st.columns(2)
                            if cd1.button("🚀 Onaya Gönder", key=f"btn_dlr_snd_{o_id}", type="primary", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("Onay Bekliyor", o_id))
                                st.rerun()
                            if cd2.button("❌ İptal Et", key=f"btn_dlr_cncl_{o_id}", use_container_width=True):
                                exec_sales("UPDATE offers SET status=? WHERE id=?", ("İptal Edildi", o_id))
                                st.rerun()

                if c_edit.button("✏️ Düzenle", key=f"btn_e_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor"])):
                    st.session_state.edit_offer_id = o_id
                    st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
                    st.rerun()
                    
                # PROFORMA BUTONU MANTIĞI
                if c_prof.button("📄 Proforma", key=f"btn_p_{o_id}", use_container_width=True):
                    st.session_state[f"show_prof_{o_id}"] = not st.session_state.get(f"show_prof_{o_id}", False)
                    # Proforma açılıyorsa admin onay panelini kapa (çakışma olmasın)
                    if f"adm_act_{o_id}" in st.session_state: del st.session_state[f"adm_act_{o_id}"]
                    st.rerun()
                    
                if c_del.button("🗑️ Sil", key=f"btn_d_{o_id}", use_container_width=True, disabled=(status in ["Onaylandı", "Onay Bekliyor"])):
                    exec_sales("DELETE FROM offers WHERE id=?", (o_id,))
                    exec_sales("DELETE FROM offer_items WHERE offer_id=?", (o_id,))
                    st.rerun()
            
            # --- BAĞIMSIZ PROFORMA GÖSTERİCİ ---
            if st.session_state.get(f"show_prof_{o_id}", False):
                st.markdown("<div style='background:#f8fafc; padding:15px; border-radius:8px; border:1px solid #e2e8f0; margin-top:15px;'>", unsafe_allow_html=True)
                
                c_p1, c_p2 = st.columns([5, 1])
                c_p1.markdown("<h4 style='color:#0f172a; margin-top:0;'>📄 Proforma Teklif Formu</h4>", unsafe_allow_html=True)
                if c_p2.button("❌ Kapat", key=f"close_prof_{o_id}", use_container_width=True):
                    st.session_state[f"show_prof_{o_id}"] = False
                    st.rerun()
                    
                m_info_full = get_factory("SELECT image_path, specs FROM models WHERE id=?", (m_id,))
                m_img = m_info_full[0][0] if m_info_full else ""
                raw_specs = m_info_full[0][1] if m_info_full else ""
                
                parsed_specs = []
                if raw_specs:
                    for item in str(raw_specs).split("||"):
                        if item.strip():
                            parts = item.split("|")
                            parsed_specs.append({"title": parts[0].strip() if len(parts)>0 else "", "detail": parts[1].strip() if len(parts)>1 else "", "img": parts[2].strip() if len(parts)>2 else ""})
                
                parsed_opts = []
                items = get_sales("SELECT option_id, quantity FROM offer_items WHERE offer_id=?", (o_id,))
                if items:
                    for opt_id, o_qty in items:
                        opt_info = get_factory("SELECT opt_name, opt_price, opt_image FROM options WHERE id=?", (opt_id,))
                        if opt_info: parsed_opts.append({"name": opt_info[0][0], "price": opt_info[0][1], "qty": o_qty, "img": opt_info[0][2]})

                html_content = generate_proforma_html(o_id, o_date, c_name, m_name, m_img, parsed_specs, parsed_opts, t_price, m_curr, conds_json, o_user_id)
                components.html(html_content, height=800, scrolling=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
