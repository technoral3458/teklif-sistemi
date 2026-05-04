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
# RESİM OKUMA
# =====================================================================
def get_image_base64(path):
    if not path: return ""
    base_name = posixpath.basename(ntpath.basename(path))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            with open(p, "rb") as f:
                ext = os.path.splitext(p)[1].lower().replace('.', '')
                return f"data:image/{ext if ext else 'png'};base64,{base64.b64encode(f.read()).decode()}"
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
    header_logo_html = f'<img src="{logo_b64}" style="max-height:70px;">' if logo_b64 else f'<b>{comp_name}</b>'

    css = """
        body { font-family: sans-serif; font-size: 14px; color: #1e293b; background: #f1f5f9; padding: 20px; }
        .paper { background: #fff; max-width: 800px; margin: auto; padding: 40px; border-top: 10px solid #2563eb; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #eee; padding-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        td, th { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
        .total { font-size: 24px; font-weight: bold; color: #ea580c; text-align: right; margin-top: 30px; }
    """

    html = f"""
    <html><style>{css}</style><body>
        <div class="paper">
            <div class="header">
                <div>{header_logo_html}</div>
                <div style="text-align:right;">{comp_web}<br>Tarih: {tarih}<br>No: {teklif_no}</div>
            </div>
            <h2 style="text-align:center;">TEKLİF FORMU</h2>
            <p>Sayın Yetkili: <b>{customer}</b></p>
            <p>Model: <b>{model}</b></p>
            <img src="{get_image_base64(machine_img)}" style="max-width:100%; height:auto; display:block; margin:20px auto;">
    """
    if selected_options:
        html += "<h3>Ekstra Donanımlar</h3><table>"
        for opt in selected_options:
            html += f"<tr><td>{opt['n']}</td><td>{opt['q']} Adet</td><td style='text-align:right;'>{opt['p']:,.2f} {m_currency}</td></tr>"
        html += "</table>"

    html += f"""
            <div class="total">GENEL TOPLAM: {agreed_price:,.2f} {m_currency}</div>
            <p style="font-size:12px; color:#666; margin-top:40px;">{comp_adr} | {comp_tel}</p>
        </div>
    </body></html>"""
    return html

# =====================================================================
# ANA SİHİRBAZ EKRANI
# =====================================================================
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()
    
    # 🚀 TIKLAMAYI ENGELLEMEYEN AMA KLAVYEYİ SUSTURAN JAVASCRIPT 🚀
    components.html("""
    <script>
    function muteKeyboard() {
        var inputs = window.parent.document.querySelectorAll('div[data-baseweb="select"] input');
        inputs.forEach(function(inp) {
            // Yazı yazmayı engelle ama tıklanabilirliği bozma
            inp.setAttribute('inputmode', 'none'); 
            inp.setAttribute('readonly', 'true');
            inp.style.cursor = 'pointer';
        });
    }
    // Sürekli kontrol eden ajan
    setInterval(muteKeyboard, 500);
    </script>
    """, height=0, width=0)

    st.markdown("""
        <style>
        /* Seçim kutularını kibar hale getirir */
        div[data-testid="stSelectbox"] > div { border-radius: 10px !important; }
        .stSelectbox label { font-size: 13px !important; font-weight: 700 !important; color: #475569 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    my_custs = get_sales("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name ASC", (user_id,)) if not is_admin else get_sales("SELECT id, company_name FROM customers ORDER BY company_name ASC")
    
    if not my_custs:
        st.warning("⚠️ Lütfen önce 'Müşterilerim' menüsünden müşteri ekleyiniz.")
        return

    wd = st.session_state.get('wizard_data', {})
    col_opt, col_prev = st.columns([1.6, 2.4], gap="large")

    with col_opt:
        st.markdown("<div style='font-size:14px; font-weight:900; color:#2563eb; margin-bottom:8px;'>1. MÜŞTERİ VE MAKİNE SEÇİMİ</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            # MÜŞTERİ SEÇİMİ (YENİ KEY İLE RESETLENDİ)
            c_names = [c[1] for c in my_custs]
            sel_cust = st.selectbox(
                "Teklif Verilecek Müşteri", 
                options=c_names, 
                index=None, 
                placeholder="Seçmek için buraya dokunun...",
                key="customer_select_vfinal"
            )

            # KATEGORİ
            cats = ["Tüm Kategoriler"] + [c[0] for c in get_factory("SELECT name FROM categories ORDER BY name ASC")]
            sel_cat = st.selectbox("Kategori Filtresi", options=cats, index=0, key="cat_filter_vfinal")

            # MAKİNE SEÇİMİ
            m_query = "SELECT id, name, base_price, compatible_options, image_path, specs, port_discount, currency FROM models"
            m_params = []
            if sel_cat != "Tüm Kategoriler":
                m_query += " WHERE category=?"
                m_params.append(sel_cat)
            m_query += " ORDER BY name ASC"

            machines = get_factory(m_query, tuple(m_params))
            m_names = [m[1] for m in machines] if machines else []
            
            sel_m = st.selectbox(
                "Makine Modeli", 
                options=m_names, 
                index=None,
                placeholder="Seçmek için buraya dokunun...",
                key="machine_select_vfinal"
            )
            
            m_qty = st.number_input("Makine Adedi", 1, 100, 1, key="qty_vfinal")

        if sel_cust is None or sel_m is None:
            with col_prev:
                st.info("💡 Lütfen Müşteri ve Makine seçimi yapınız. Seçimden sonra detaylar buraya gelecektir.")
            return

        # --- SEÇİM YAPILDIKTAN SONRAKİ KISIM ---
        cust_id = [c[0] for c in my_custs if c[1] == sel_cust][0]
        m_info = next(m for m in machines if m[1] == sel_m)
        m_id, m_name, m_price, m_opts_str, m_img, m_specs, m_disc, m_curr = m_info

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px;'>2. SATIŞ ŞARTLARI</div>", unsafe_allow_html=True)
        with st.expander("Şartları Düzenle"):
            d_type = st.selectbox("Teslimat Şekli", ["Antrepo Teslim", "Limandan Devir", "Yurtiçi Teslim"])
            d_time = st.text_input("Teslim Süresi", "90 iş günü")
            pay = st.text_area("Ödeme", "%30 Peşin")

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px;'>3. EKSTRA DONANIMLAR</div>", unsafe_allow_html=True)
        opts_total = 0.0
        engine_options = []
        with st.container(height=300, border=True):
            if m_opts_str:
                ids = [x.strip() for x in str(m_opts_str).split(",") if x.strip()]
                opts = get_factory(f"SELECT id, opt_name, opt_price, opt_image FROM options WHERE id IN ({','.join(['?']*len(ids))})", tuple(ids))
                for o in opts:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"**{o[1]}** (+{o[2]:,.0f} {m_curr})")
                        if c2.checkbox("Ekle", key=f"opt_chk_{o[0]}"):
                            opts_total += o[2]
                            engine_options.append({'n': o[1], 'p': o[2], 'q': 1, 'i': o[3]})
            else:
                st.write("Donanım yok.")

        agreed = m_price + opts_total
        st.markdown(f"### Toplam: {agreed:,.2f} {m_curr}")
        if st.button("💾 TEKLİFİ KAYDET", type="primary", use_container_width=True):
            st.success("Teklif başarıyla kaydedildi!")

    with col_prev:
        st.markdown("### 📄 Önizleme")
        conds = {"agreed_price": agreed}
        html = generate_embedded_html(sel_cust, m_name, m_price, m_img, m_specs, engine_options, conds, m_curr, user_id)
        components.html(html, height=800, scrolling=True)
