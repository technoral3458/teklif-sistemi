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
# GÖMÜLÜ ÖNİZLEME VE PDF YAZDIRMA MOTORU
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

    # Modern ve Temiz Tasarım + CSS Yazdırma (Print) Kuralları
    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 13px; color: #1e293b; background: #f8fafc; margin:0; padding:20px; }
        .paper { background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 1000px; margin: 0 auto; }
        .header { border-bottom: 3px solid #3b82f6; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-end; }
        .section-title { background: #0f172a; color: white; padding: 8px 15px; font-weight: 600; font-size: 14px; margin-top: 30px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border-bottom: 1px solid #e2e8f0; padding: 12px 10px; text-align: left; vertical-align: middle; }
        th { color: #64748b; font-size: 12px; text-transform: uppercase; }
        .price-box { background: #eff6ff; border: 2px solid #bfdbfe; padding: 20px; text-align: right; margin-top: 30px; border-radius: 8px; }
        .total-price { font-size: 36px; font-weight: 800; color: #1d4ed8; margin-top:5px; }
        
        .print-btn { background: #10b981; color: white; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .print-btn:hover { background: #059669; }
        
        @media print {
            body { background: #fff; padding: 0; }
            .paper { box-shadow: none; padding: 0; margin: 0; max-width: 100%; }
            .no-print { display: none !important; }
        }
    """

    html = f"""
    <html><head><style>{css}</style></head><body>
        
        <div class="no-print" style="text-align:right; margin-bottom: 20px;">
            <button class="print-btn" onclick="window.print()">🖨️ YAZDIR / PDF OLARAK İNDİR</button>
        </div>

        <div class="paper">
            <div class="header">
                <div><h1 style="margin:0; color:#0f172a; font-size: 28px;">ERSAN MAKİNE</h1></div>
                <div style="text-align:right; color:#64748b; font-size: 12px;">
                    <b>Tarih:</b> {tarih}<br>
                    <b>Teklif No:</b> TR-{datetime.datetime.now().strftime("%y%m%d")}
                </div>
            </div>

            <div style="text-align:center; padding: 10px 0;">
                <img src="{m_img_b64}" style="max-height:280px; object-fit:contain;"><br>
                <h2 style="margin:15px 0 5px 0; color:#0f172a; font-size: 24px;">MODEL: {model}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:14px; color:#475569; margin-top:10px;">
                    Sayın Yetkili: <b style="color:#0f172a;">{customer}</b>
                </div>
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
        img_tag = f'<img src="{opt_img}" style="max-width:50px; max-height:50px; border-radius:6px; margin-right:15px; float:left; object-fit:cover; border:1px solid #e2e8f0;">' if opt_img else ''
        html += f"""
            <tr>
                <td>
                    {img_tag}
                    <div style="overflow:hidden;">
                        <b style="color:#2563eb; font-size:14px;">+ {opt['n']}</b><br>
                        <span style="font-size:11px; color:#64748b; line-height:1.4; display:block; margin-top:4px;">{opt['d']}</span>
                    </div>
                </td>
                <td style="text-align:center; font-weight:bold; color:#0f172a;">{opt['q']}</td>
                <td style="text-align:right; font-weight:bold; color:#e67e22;">{(opt['p']*opt['q']):,.2f} {m_currency}</td>
            </tr>
        """

    html += f"""
            </table>

            <div class="price-box">
                <div style="font-size:14px; color:#64748b; font-weight:600;">Teslimat Şartı: <span style="color:#0f172a;">{delivery_type}</span></div>
                <div style="margin-top:15px; font-size:15px; font-weight:bold; color:#3b82f6; text-transform:uppercase;">Genel Toplam (KDV Hariç)</div>
                <div class="total-price">{agreed_price:,.2f} {m_currency}</div>
            </div>
            
            <div style="margin-top:40px; font-size:11px; color:#94a3b8; text-align:center; padding-top:15px;">
                Ersan Makine San. ve Tic. Ltd. Şti. | www.ersanmakina.net
            </div>
        </div>
    </body></html>
    """
    return html

# =====================================================================
# ANA TEKLİF SİHİRBAZI YÖNETİCİSİ
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    # Modern ve Sıkı CSS
    st.markdown("""
    <style>
    .block-container { padding-top: 1rem; max-width: 98%; }
    .stSelectbox label, .stNumberInput label { color: #475569 !important; font-size: 13px !important; font-weight: 600 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { padding: 15px !important; border-radius: 12px !important; border-color: #e2e8f0 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # State (Durum) Başlatma
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
    # ADIM 1: POPUP HİSSİYATLI BAŞLANGIÇ AYARLARI
    # -----------------------------------------------------------------
    if st.session_state.wizard_step == 1:
        st.markdown("<h3 style='text-align:center; color:#0f172a; margin-bottom: 30px;'>✨ Yeni Teklif Başlat</h3>", unsafe_allow_html=True)
        
        # Ekranı ortalamak için boş kolonlar (Mobil uyumlu)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                st.markdown("<div style='background:#f1f5f9; padding:10px; border-radius:8px; margin-bottom:15px; text-align:center; font-weight:bold; color:#3b82f6;'>1. Adım: Temel Ayarlar</div>", unsafe_allow_html=True)
                
                selected_cust_name = st.selectbox("👤 Müşteri Seçimi", [c[1] for c in my_custs])
                f_currency = st.selectbox("💵 Para Birimi", ["USD", "EUR", "RMB", "TRY"])
                
                cats = database.get_query("SELECT name FROM categories ORDER BY id")
                cat_list = ["Tüm Kategoriler"] + [c[0] for c in cats] if cats else ["Tüm Kategoriler"]
                f_category = st.selectbox("🗂️ Makine Kategorisi", cat_list)

                # Modele göre çekim
                if f_category == "Tüm Kategoriler":
                    model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=?", (f_currency,))
                else:
                    model_data = database.get_query("SELECT id, name, base_price, currency, compatible_options, port_discount, image_path, specs FROM models WHERE currency=? AND category=?", (f_currency, f_category))

                if not model_data:
                    st.error("Bu kategoride makine bulunamadı.")
                else:
                    selected_model = st.selectbox("🤖 Makine Modeli", [m[1] for m in model_data])
                    
                    cc1, cc2 = st.columns(2)
                    m_qty = cc1.number_input("Adet", min_value=1, value=1)
                    delivery_type = cc2.selectbox("Teslimat", ["Gümrük İşlemleri Yapılmış Antrepo Teslim", "Gümrük İşlemleri Yapılmadan Limandan Devir"])
                    
                    st.write("")
                    if st.button("Devam Et ➡️", type="primary", use_container_width=True):
                        selected_cust_id = [c[0] for c in my_custs if c[1] == selected_cust_name][0]
                        m_info = [m for m in model_data if m[1] == selected_model][0]
                        
                        # Verileri State'e kaydet
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
    # ADIM 2: DİNAMİK DONANIM SEÇİMİ VE CANLI ÖNİZLEME
    # -----------------------------------------------------------------
    elif st.session_state.wizard_step == 2:
        wd = st.session_state.wizard_data
        
        # Üst Bar (Geri Dön ve Özet)
        col_back, col_info = st.columns([1, 5], vertical_alignment="center")
        if col_back.button("🔙 Ayarlara Dön"):
            st.session_state.wizard_step = 1
            st.rerun()
        col_info.markdown(f"<div style='background:#eff6ff; padding:8px 15px; border-radius:8px; border:1px solid #bfdbfe; color:#1e40af;'><b>Müşteri:</b> {wd['cust_name']} &nbsp;|&nbsp; <b>Model:</b> {wd['m_name']} (x{wd['qty']})</div>", unsafe_allow_html=True)
        st.write("")

        # MOBİL UYUMLU DİNAMİK TASARIM (Sol: Donanımlar, Sağ: Önizleme)
        col_opt, col_prev = st.columns([1.2, 2.5], gap="medium")
        
        engine_options_list = []
        selected_options_for_db = []
        selected_options_total = 0.0

        multiplier = 1.0
        if "Liman" in wd["delivery"] and wd["m_disc"]:
            multiplier = 1.0 - (float(wd["m_disc"]) / 100.0)

        # SOL: DONANIMLAR
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
                                st.checkbox(f"**{o_name}** (+{d_o_price:,.0f} {o_curr})", key=f"c_{o_id}")
                                if st.session_state.get(f"c_{o_id}", False):
                                    o_qty = st.number_input("Adet:", min_value=1, value=1, key=f"q_{o_id}")
                                    selected_options_total += (d_o_price * o_qty)
                                    selected_options_for_db.append({"id": o_id, "qty": o_qty})
                                    engine_options_list.append({'n': o_name, 'p': d_o_price, 'q': o_qty, 'i': o_img, 'd': o_desc, 's': o_curr})
            
            # FİYAT HESAPLAMA VE KAYIT (Sol Alt)
            st.markdown("---")
            sub_total = ((float(wd["m_price"]) * multiplier) * wd["qty"]) + selected_options_total
            
            with st.container(border=True):
                st.markdown(f"<div style='font-size:12px; color:#64748b;'>Sistem Toplamı: <b>{sub_total:,.2f} {wd['m_curr']}</b></div>", unsafe_allow_html=True)
                discount_pct = st.number_input("Özel İskonto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                final_price = sub_total * (1 - (discount_pct / 100.0))
                agreed_price = st.number_input("Anlaşılan Net Fiyat", min_value=0.0, value=final_price, step=100.0)

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
                    st.success("Sisteme Başarıyla Kaydedildi!")
                    st.balloons()
                except Exception as e: st.error(f"Kayıt Hatası: {e}")

        # SAĞ: CANLI ÖNİZLEME VE PDF 
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
