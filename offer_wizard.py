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

COUNTRIES = [
    "Türkiye", "Almanya", "Amerika Birleşik Devletleri", "Azerbaycan",
    "Birleşik Arap Emirlikleri", "Birleşik Krallık", "Bulgaristan", "Çin",
    "Fransa", "Gürcistan", "Irak", "İngiltere", "İran", "İspanya", "İtalya",
    "Japonya", "Katar", "Kosova", "Kuzey Makedonya", "Mısır", "Özbekistan",
    "Romanya", "Rusya", "Sırbistan", "Suudi Arabistan", "Yunanistan",
    "Yurtdışı (Diğer)"
]

CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya",
    "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın",
    "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
    "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır",
    "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir",
    "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır",
    "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman",
    "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir",
    "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin",
    "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye",
    "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa",
    "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van",
    "Yalova", "Yozgat", "Zonguldak", "Yurtdışı Şehri (Diğer)"
]


def get_factory(query, params=()):
    conn = sqlite3.connect("factory_data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res


def get_sales(query, params=()):
    conn = sqlite3.connect("sales_data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res


def exec_sales(query, params=()):
    conn = sqlite3.connect("sales_data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()


def get_user_query(query, params=()):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall()
    conn.close()
    return res


def add_column_if_missing(db_path, table_name, column_name, column_type):
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cur = conn.cursor()
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table_name})").fetchall()]
        if column_name not in cols:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            conn.commit()
        conn.close()
    except Exception:
        pass


def init_wizard_tables():
    exec_sales("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            authorized_person TEXT,
            phone TEXT,
            email TEXT,
            address_full TEXT,
            user_id INTEGER DEFAULT 1,
            country TEXT DEFAULT '',
            city TEXT DEFAULT '',
            tax_office TEXT DEFAULT '',
            tax_id TEXT DEFAULT ''
        )
    """)

    exec_sales("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            model_id INTEGER,
            total_price REAL DEFAULT 0.0,
            conditions TEXT DEFAULT '',
            status TEXT DEFAULT 'Beklemede',
            user_id INTEGER DEFAULT 1,
            offer_date TEXT DEFAULT '',
            order_date TEXT DEFAULT '',
            total_cost REAL DEFAULT 0.0,
            total_profit REAL DEFAULT 0.0,
            profit_rate REAL DEFAULT 0.0
        )
    """)

    exec_sales("""
        CREATE TABLE IF NOT EXISTS offer_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER,
            option_id INTEGER,
            quantity INTEGER DEFAULT 1,
            sale_price REAL DEFAULT 0.0,
            total_sale_price REAL DEFAULT 0.0,
            total_cost REAL DEFAULT 0.0,
            total_profit REAL DEFAULT 0.0
        )
    """)

    for col, typ in [
        ("total_price", "REAL DEFAULT 0.0"),
        ("conditions", "TEXT DEFAULT ''"),
        ("status", "TEXT DEFAULT 'Beklemede'"),
        ("user_id", "INTEGER DEFAULT 1"),
        ("offer_date", "TEXT DEFAULT ''"),
        ("order_date", "TEXT DEFAULT ''"),
        ("total_cost", "REAL DEFAULT 0.0"),
        ("total_profit", "REAL DEFAULT 0.0"),
        ("profit_rate", "REAL DEFAULT 0.0"),
    ]:
        add_column_if_missing("sales_data.db", "offers", col, typ)

    for col, typ in [
        ("user_id", "INTEGER DEFAULT 1"),
        ("country", "TEXT DEFAULT ''"),
        ("city", "TEXT DEFAULT ''"),
        ("tax_office", "TEXT DEFAULT ''"),
        ("tax_id", "TEXT DEFAULT ''"),
        ("address_full", "TEXT DEFAULT ''"),
        ("authorized_person", "TEXT DEFAULT ''"),
    ]:
        add_column_if_missing("sales_data.db", "customers", col, typ)

    for col, typ in [
        ("sale_price", "REAL DEFAULT 0.0"),
        ("total_sale_price", "REAL DEFAULT 0.0"),
        ("total_cost", "REAL DEFAULT 0.0"),
        ("total_profit", "REAL DEFAULT 0.0"),
    ]:
        add_column_if_missing("sales_data.db", "offer_items", col, typ)

    for col, typ in [
        ("sale_price", "REAL DEFAULT 0.0"),
        ("purchase_price", "REAL DEFAULT 0.0"),
        ("shipping_cost", "REAL DEFAULT 0.0"),
        ("customs_tax_rate", "REAL DEFAULT 3.0"),
        ("extra_tax_rate", "REAL DEFAULT 10.0"),
        ("port_cost", "REAL DEFAULT 0.0"),
        ("document_cost", "REAL DEFAULT 0.0"),
        ("installation_cost", "REAL DEFAULT 0.0"),
        ("other_cost", "REAL DEFAULT 0.0"),
        ("cost_note", "TEXT DEFAULT ''"),
    ]:
        add_column_if_missing("factory_data.db", "models", col, typ)
        add_column_if_missing("factory_data.db", "options", col, typ)


def safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def calculate_import_cost(
    purchase_price=0,
    shipping_cost=0,
    customs_tax_rate=3,
    extra_tax_rate=10,
    port_cost=0,
    document_cost=0,
    installation_cost=0,
    other_cost=0
):
    purchase_price = safe_float(purchase_price)
    shipping_cost = safe_float(shipping_cost)
    customs_tax_rate = safe_float(customs_tax_rate)
    extra_tax_rate = safe_float(extra_tax_rate)
    port_cost = safe_float(port_cost)
    document_cost = safe_float(document_cost)
    installation_cost = safe_float(installation_cost)
    other_cost = safe_float(other_cost)

    ara_1 = purchase_price + shipping_cost
    gumruk = ara_1 * customs_tax_rate / 100
    ara_2 = ara_1 + gumruk
    ek_vergi = ara_2 * extra_tax_rate / 100
    ara_3 = ara_2 + ek_vergi
    toplam = ara_3 + port_cost + document_cost + installation_cost + other_cost

    return toplam


def get_image_base64(path):
    if not path:
        return ""

    if str(path).startswith("http"):
        return path

    base_name = posixpath.basename(ntpath.basename(str(path)))
    paths_to_try = [
        path,
        f"images/{path}",
        f"../images/{path}",
        base_name,
        f"images/{base_name}",
    ]

    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    ext = os.path.splitext(p)[1].lower().replace(".", "")
                    if not ext:
                        ext = "png"
                    if ext == "jpg":
                        ext = "jpeg"
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except Exception:
                pass

    return ""


def get_index(lst, item, default=0):
    return lst.index(item) if item in lst else default
def generate_embedded_html(customer, model, base_price, machine_img, specs, selected_options, conditions, m_currency, user_id):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    agreed_price = conditions.get("agreed_price", 0)
    teklif_no = f"TR-{datetime.datetime.now().strftime('%y%m%d')}"

    try:
        u_info = get_user_query(
            "SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?",
            (user_id,)
        )[0]
    except Exception:
        u_info = None

    comp_name = u_info[0] if u_info and u_info[0] else "ERSAN MAKİNE"
    comp_logo = u_info[1] if u_info and u_info[1] else ""
    comp_web = u_info[2] if u_info and u_info[2] else "www.ersanmakina.net"
    comp_adr = u_info[3] if u_info and u_info[3] else "Ersan Makine San. Tic. Ltd. Şti."
    comp_tel = u_info[4] if u_info and u_info[4] else ""

    if not comp_logo:
        try:
            comp_logo = get_factory("SELECT logo_path FROM company_profile WHERE id=1")[0][0]
        except Exception:
            pass

    logo_b64 = get_image_base64(comp_logo)
    header_logo_html = (
        f'<img src="{logo_b64}" style="max-height:70px; width:auto; object-fit:contain;">'
        if logo_b64 else
        f'<div style="font-size:22px; font-weight:900; color:#1e293b;">{comp_name}</div>'
    )

    css = """
    body { font-family: Arial, sans-serif; font-size:14px; color:#1e293b; background:#fff; margin:0; padding:0; display:flex; flex-direction:column; align-items:center; }
    .paper { background:#fff; width:100%; max-width:794px; min-height:1123px; padding:40px; border:1px solid #e2e8f0; border-top:8px solid #2563eb; box-sizing:border-box; margin:0 auto 40px auto; }
    .header { border-bottom:2px solid #e2e8f0; padding-bottom:15px; margin-bottom:25px; display:flex; justify-content:space-between; align-items:center; gap:10px; }
    .section-title { background:#f8fafc; color:#0f172a; padding:10px 15px; font-weight:800; font-size:14px; margin-top:30px; border-left:5px solid #2563eb; }
    table { width:100%; border-collapse:collapse; margin-top:15px; }
    th, td { border-bottom:1px solid #f1f5f9; padding:12px; text-align:left; vertical-align:middle; }
    .price-box { background:#fffbeb; border:1px solid #fde68a; padding:20px; text-align:right; margin-top:35px; border-radius:6px; }
    .total-price { font-size:30px; font-weight:900; color:#ea580c; }
    .elegant-conditions { margin-top:35px; background:#f8fafc; padding:20px; border-left:5px solid #eab308; }
    .print-btn-container { width:100%; max-width:794px; margin:0 auto 40px auto; text-align:center; }
    .print-btn { background:#10b981; color:white; border:none; padding:15px; font-size:16px; border-radius:8px; cursor:pointer; width:100%; font-weight:bold; }
    .footer-info { margin-top:30px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:15px; }
    @media print { .no-print { display:none!important; } .paper { border:none; padding:0; margin:0; width:100%; max-width:100%; min-height:auto; } body { background:#fff; padding:0; } .page-break { page-break-before:always; } }
    """

    page_header_html = f"""
    <div class="header">
        <div>{header_logo_html}</div>
        <div style="text-align:right; font-size:12px; color:#64748b;">
            <b>{comp_web}</b><br>Tarih: {tarih}<br>Teklif No: {teklif_no}
        </div>
    </div>
    """

    html = f"""
    <html><head><meta charset="utf-8"><style>{css}</style></head><body>
    <div class="paper">
        {page_header_html}
        <div style="text-align:center; padding:15px 0;">
            <img src="{get_image_base64(machine_img)}" style="max-width:100%; max-height:350px; object-fit:contain;"><br>
            <h2 style="color:#0f172a; margin:15px 0; font-size:24px; font-weight:900;">MODEL: {model}</h2>
            <div style="display:inline-block; background:#f1f5f9; padding:8px 20px; border-radius:20px;">
                Sayın Yetkili: <b>{customer}</b>
            </div>
        </div>
    """

    if specs and str(specs).strip():
        html += '<div class="section-title">🔍 MAKİNE STANDART ÖZELLİKLERİ</div><table>'
        for item in [x for x in str(specs).split("||") if x.strip()]:
            parts = item.split("|")
            t_spec = parts[0].strip() if len(parts) > 0 else ""
            d_spec = parts[1].strip() if len(parts) > 1 else ""
            img_b64 = get_image_base64(parts[2].strip() if len(parts) > 2 else "")
            img_tag = f'<img src="{img_b64}" style="max-width:100%; max-height:80px; object-fit:contain;">' if img_b64 else "-"
            html += f"<tr><td style='width:25%; text-align:center;'>{img_tag}</td><td><b>{t_spec}</b><br><small>{d_spec}</small></td></tr>"
        html += "</table>"

    if selected_options:
        html += """
        <div class="section-title">📦 SEÇİLEN EKSTRA DONANIMLAR</div>
        <table>
        <tr style="background:#f8fafc;">
            <th style="width:25%; text-align:center;">Görsel</th>
            <th style="width:40%;">Açıklama</th>
            <th style="width:10%; text-align:center;">Adet</th>
            <th style="width:25%; text-align:right;">Tutar</th>
        </tr>
        """

        for opt in selected_options:
            opt_img_b64 = get_image_base64(opt["i"])
            opt_img_tag = f'<img src="{opt_img_b64}" style="max-width:100%; max-height:80px; object-fit:contain;">' if opt_img_b64 else "-"
            html += f"""
            <tr>
                <td style="text-align:center;">{opt_img_tag}</td>
                <td><b style="color:#2563eb;">+ {opt['n']}</b><br><small>{opt['d']}</small></td>
                <td style="text-align:center;">{opt['q']}</td>
                <td style="text-align:right; font-weight:bold;">{(opt['p'] * opt['q']):,.2f} {m_currency}</td>
            </tr>
            """
        html += "</table>"

    html += f"""
    </div>
    <div class="paper page-break">
        {page_header_html}
        <div class="elegant-conditions">
            <div style="font-size:15px; font-weight:bold; border-bottom:2px solid #cbd5e1; padding-bottom:8px; margin-bottom:12px;">📌 Ticari ve Teknik Şartlar</div>
            <table>
                <tr><td style="width:35%;"><b>Teslimat Şekli:</b></td><td style="color:#ea580c; font-weight:bold;">{conditions.get('delivery_type','')}</td></tr>
                <tr><td><b>Teslim Süresi:</b></td><td>{conditions.get('delivery_time','')}</td></tr>
                <tr><td><b>Nakliye / Lojistik:</b></td><td>{conditions.get('shipping','')}</td></tr>
                <tr><td><b>Ödeme Planı:</b></td><td>{conditions.get('payment_plan_text','')}</td></tr>
                <tr><td><b>Banka Bilgileri:</b></td><td>{conditions.get('bank','')}</td></tr>
            </table>
        </div>
        <div class="price-box">
            <div style="font-size:14px; font-weight:bold; color:#ea580c;">Genel Toplam (KDV Hariç)</div>
            <div class="total-price">{agreed_price:,.2f} {m_currency}</div>
        </div>
        <div class="footer-info">{comp_adr} | {comp_tel}</div>
    </div>
    <div class="no-print print-btn-container">
        <button class="print-btn" onclick="window.print()">🖨️ PDF KAYDET</button>
    </div>
    </body></html>
    """

    return html
def show_offer_wizard(user_id, is_admin=False):
    init_wizard_tables()

    st.markdown("""
    <style>
    .block-container { padding-top:1rem!important; padding-bottom:2rem!important; padding-left:.5rem!important; padding-right:.5rem!important; max-width:100%!important; }
    div[data-baseweb="select"] input { caret-color:transparent!important; }
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stTextArea label {
        font-size:13px!important; font-weight:700!important; color:#475569!important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_b1, col_b2, col_b3 = st.columns([1, 6, 1])
    if col_b1.button("☰ Menü", use_container_width=True):
        st.session_state.active_tab = "📊 Dashboard"
        if "m_radio" in st.session_state:
            del st.session_state["m_radio"]
        st.rerun()

    st.markdown("<hr style='margin-top:5px; margin-bottom:15px;'>", unsafe_allow_html=True)

    u_role = "Admin" if is_admin else "Dealer"
    u_allowed_cats = []

    if not is_admin:
        try:
            u_data = get_user_query("SELECT role, allowed_categories FROM users WHERE id=?", (user_id,))
            if u_data:
                u_role = u_data[0][0] or "Dealer"
                cats_str = u_data[0][1] or ""
                u_allowed_cats = [x.strip() for x in cats_str.split(",") if x.strip()]
        except Exception:
            pass

    if is_admin:
        my_custs = get_sales("SELECT id, company_name FROM customers ORDER BY company_name ASC")
    else:
        my_custs = get_sales("SELECT id, company_name FROM customers WHERE user_id=? ORDER BY company_name ASC", (user_id,))

    if my_custs is None:
        my_custs = []

    is_edit = "edit_offer_id" in st.session_state
    wd = st.session_state.get("wizard_data", {})

    col_opt, col_prev = st.columns([1.6, 2.4], gap="small")

    with col_opt:
        if is_edit:
            st.info("✏️ Düzenleme Modu")
            if st.button("❌ İptal Et", use_container_width=True):
                del st.session_state.edit_offer_id
                st.session_state.wizard_data = {}
                st.rerun()

        st.markdown("<div style='font-size:14px; font-weight:900; color:#2563eb; margin-bottom:8px;'>1. MÜŞTERİ VE MAKİNE SEÇİMİ</div>", unsafe_allow_html=True)

        with st.container(border=True):
            is_new_customer = st.toggle("➕ Yeni Müşteri Ekle", key="toggle_new_cust")

            if is_new_customer:
                st.markdown("<div style='font-size:14px; font-weight:900; color:#ea580c; margin-top:10px; margin-bottom:10px;'>🆕 HIZLI MÜŞTERİ KAYDI</div>", unsafe_allow_html=True)

                nc_comp = st.text_input("Firma Adı *", placeholder="Örn: ABC Makine Ltd. Şti.")
                c_tax1, c_tax2 = st.columns(2)
                nc_tax_office = c_tax1.text_input("Vergi Dairesi", placeholder="Örn: İlyasbey V.D.")
                nc_tax_id = c_tax2.text_input("Vergi Numarası / TC", placeholder="Örn: 1234567890")
                nc_auth = st.text_input("Yetkili Kişi *", placeholder="Ad Soyad giriniz...")

                c_tel, c_mail = st.columns(2)
                nc_phone = c_tel.text_input("Telefon", placeholder="+90 5XX...")
                nc_email = c_mail.text_input("E-Posta", placeholder="info@firma.com")

                c_ulke, c_sehir = st.columns(2)
                nc_country = c_ulke.selectbox("Ülke *", options=COUNTRIES, index=None, placeholder="Aramak için yazın...")
                nc_city = c_sehir.selectbox("Şehir *", options=CITIES, index=None, placeholder="Aramak için yazın...")

                nc_addr = st.text_area("Açık Adres", height=80, placeholder="Fatura adresi...")

                if st.button("💾 MÜŞTERİYİ KAYDET VE DEVAM ET", type="primary", use_container_width=True):
                    if not nc_comp.strip() or not nc_auth.strip() or not nc_country or not nc_city:
                        st.error("Lütfen Firma, Yetkili, Ülke ve Şehir alanlarını doldurun.")
                    else:
                        exec_sales("""
                            INSERT INTO customers
                            (company_name, authorized_person, phone, email, address_full, country, city, tax_office, tax_id, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            nc_comp.strip(), nc_auth.strip(), nc_phone.strip(), nc_email.strip(),
                            nc_addr.strip(), nc_country, nc_city, nc_tax_office.strip(), nc_tax_id.strip(), user_id
                        ))
                        st.session_state.new_added_cust = nc_comp.strip()
                        if "toggle_new_cust" in st.session_state:
                            del st.session_state["toggle_new_cust"]
                        st.rerun()
                return

            CUST_PROMPT = "Lütfen Müşteri Seçiniz..."
            MACH_PROMPT = "Lütfen Makine Modeli Seçiniz..."

            c_names = [CUST_PROMPT] + [c[1] for c in my_custs]

            if "new_added_cust" in st.session_state and st.session_state.new_added_cust in c_names:
                idx_c = c_names.index(st.session_state.new_added_cust)
                del st.session_state.new_added_cust
            else:
                idx_c = c_names.index(wd.get("cust_name")) if wd.get("cust_name") in c_names else 0

            sel_cust = st.selectbox("Teklif Verilecek Müşteri", c_names, index=idx_c, key="wiz_customer")

            all_cats_db = [c[0] for c in get_factory("SELECT name FROM categories ORDER BY name ASC")]
            cats = ["Tüm Kategoriler"]

            if u_role == "Admin":
                cats.extend(all_cats_db)
            elif u_role == "Producer":
                try:
                    cats.extend(sorted([c[0] for c in get_factory(
                        "SELECT DISTINCT category FROM models WHERE user_id=? AND category IS NOT NULL",
                        (user_id,)
                    )]))
                except Exception:
                    cats.extend(all_cats_db)
            elif u_role == "Dealer":
                if u_allowed_cats:
                    cats.extend([c for c in all_cats_db if c in u_allowed_cats])
                else:
                    cats.extend(all_cats_db)

            idx_cat = cats.index(wd.get("category")) if wd.get("category") in cats else 0
            sel_cat = st.selectbox("Kategori Filtresi", cats, index=idx_cat, key="wiz_category")

            m_query = """
                SELECT id, name, base_price, sale_price, compatible_options, image_path, specs,
                       port_discount, currency, purchase_price, shipping_cost, customs_tax_rate,
                       extra_tax_rate, port_cost, document_cost, installation_cost, other_cost
                FROM models
                WHERE 1=1
            """
            m_params = []

            if u_role == "Producer":
                m_query += " AND user_id=?"
                m_params.append(user_id)
            elif u_role == "Dealer" and u_allowed_cats:
                placeholders = ",".join(["?"] * len(u_allowed_cats))
                m_query += f" AND category IN ({placeholders})"
                m_params.extend(u_allowed_cats)

            if sel_cat != "Tüm Kategoriler":
                m_query += " AND category=?"
                m_params.append(sel_cat)

            m_query += " ORDER BY name ASC"

            machines = get_factory(m_query, tuple(m_params))

            if not machines:
                st.warning("Seçili kritere veya yetkinize uygun makine bulunamadı.")
                return

            m_names = [MACH_PROMPT] + [m[1] for m in machines]
            idx_m = m_names.index(wd.get("m_name")) if wd.get("m_name") in m_names else 0
            sel_m = st.selectbox("Makine Modeli", m_names, index=idx_m, key="wiz_machine")
            m_qty = st.number_input("Makine Adedi", 1, 100, wd.get("qty", 1), key="wiz_qty")

        if sel_cust == CUST_PROMPT or sel_m == MACH_PROMPT:
            with col_prev:
                st.info("💡 Teklif detaylarını görmek için Müşteri ve Makine seçiniz.")
            return
cust_id = [c[0] for c in my_custs if c[1] == sel_cust][0]
        m_info = next(m for m in machines if m[1] == sel_m)

        (
            m_id, m_name, m_base_price, m_sale_price, m_opts_str, m_img, m_specs,
            m_disc, m_curr, m_purchase, m_ship_cost, m_customs_rate,
            m_extra_rate, m_port_cost, m_doc_cost, m_install_cost, m_other_cost
        ) = m_info

        m_price = safe_float(m_sale_price) or safe_float(m_base_price)
        m_cost = calculate_import_cost(
            m_purchase, m_ship_cost, m_customs_rate, m_extra_rate,
            m_port_cost, m_doc_cost, m_install_cost, m_other_cost
        )

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px; margin-bottom:10px; border-bottom:2px solid #e2e8f0; padding-bottom:5px;'>2. SATIŞ ŞARTLARI</div>", unsafe_allow_html=True)

        with st.expander("📝 Şartları Görüntüle / Düzenle", expanded=False):
            del_types = [
                "Gümrük İşlemleri Yapılmış Antrepo Teslim",
                "Limandan Devir",
                "Yurtiçi Teslim (Standart)"
            ]

            d_type = st.selectbox(
                "Teslimat Şekli",
                del_types,
                index=get_index(del_types, st.session_state.get("temp_del_type", "Gümrük İşlemleri Yapılmış Antrepo Teslim"), 0),
                key="temp_del_type"
            )

            d_time = st.text_input("Teslim Süresi", wd.get("d_time", "Sipariş onayından itibaren 90 iş günü"))
            ship = st.text_input("Nakliye / Lojistik", wd.get("ship", "Alıcıya Aittir"))
            pay = st.text_area("Ödeme Planı", wd.get("pay", "%30 Peşin, Kalanı Yükleme Öncesi"))
            bnk = st.text_area("Banka Bilgileri", wd.get("bnk", ""))
            nts = st.text_area("Özel Notlar", wd.get("nts", ""))

        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-top:20px; margin-bottom:10px; border-bottom:2px solid #e2e8f0; padding-bottom:5px;'>3. EKSTRA DONANIMLAR</div>", unsafe_allow_html=True)

        multiplier = 1.0 - (float(m_disc or 0) / 100.0) if "Liman" in d_type and m_disc else 1.0

        selected_options_for_db = []
        engine_options_list = []
        opts_total = 0.0
        opts_cost_total = 0.0

        current_dynamic_m_name = m_name
        current_dynamic_m_img = m_img

        with st.container(height=450, border=True):
            if m_opts_str:
                ids = [x.strip() for x in str(m_opts_str).split(",") if x.strip()]

                if ids:
                    placeholders = ",".join(["?"] * len(ids))

                    opts = get_factory(f"""
                        SELECT id, opt_name, opt_price, sale_price, opt_desc, opt_image,
                               allow_qty, opt_suffix, opt_variant_image,
                               purchase_price, shipping_cost, customs_tax_rate,
                               extra_tax_rate, port_cost, document_cost,
                               installation_cost, other_cost
                        FROM options
                        WHERE id IN ({placeholders})
                    """, tuple(ids))

                    for o in opts:
                        o_id = o[0]
                        o_name = o[1]
                        o_list_price = safe_float(o[2])
                        o_sale_price = safe_float(o[3]) or o_list_price
                        o_desc = o[4]
                        o_img = o[5]
                        allow_qty = bool(o[6]) if o[6] is not None else True
                        o_suffix = o[7] or ""
                        o_v_img = o[8] or ""

                        o_cost = calculate_import_cost(
                            o[9], o[10], o[11], o[12],
                            o[13], o[14], o[15], o[16]
                        )

                        d_o_p = o_sale_price * multiplier

                        with st.container(border=True):
                            c_img, c_info, c_act = st.columns([1.5, 3, 1.5], vertical_alignment="center")

                            img_b64 = get_image_base64(o_img)
                            if img_b64:
                                c_img.markdown(
                                    f'<img src="{img_b64}" style="width:100%; max-height:80px; object-fit:contain; border-radius:6px; border:1px solid #e2e8f0; padding:2px;">',
                                    unsafe_allow_html=True
                                )
                            else:
                                c_img.markdown(
                                    "<div style='width:100%; height:80px; background:#f8fafc; border-radius:6px; border:1px dashed #cbd5e1; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:11px;'>Görsel Yok</div>",
                                    unsafe_allow_html=True
                                )

                            c_info.markdown(f"<div style='font-size:14px; font-weight:800; color:#1e293b;'>{o_name}</div>", unsafe_allow_html=True)
                            c_info.markdown(f"<div style='font-size:15px; font-weight:900; color:#ea580c; margin-top:5px;'>+{d_o_p:,.0f} {m_curr}</div>", unsafe_allow_html=True)

                            is_sel = c_act.checkbox("Sepete Ekle", key=f"chk_o_{o_id}")

                            if is_sel:
                                q_o = c_act.number_input("Adet", 1, 100, 1, key=f"q_{o_id}", label_visibility="collapsed") if allow_qty else 1

                                opts_total += d_o_p * q_o
                                opts_cost_total += o_cost * q_o

                                selected_options_for_db.append({
                                    "id": o_id,
                                    "qty": q_o,
                                    "sale_price": d_o_p,
                                    "total_sale_price": d_o_p * q_o,
                                    "total_cost": o_cost * q_o,
                                    "total_profit": (d_o_p * q_o) - (o_cost * q_o)
                                })

                                engine_options_list.append({
                                    "n": o_name,
                                    "p": d_o_p,
                                    "q": q_o,
                                    "i": o_img,
                                    "d": o_desc
                                })

                                if o_suffix:
                                    current_dynamic_m_name += f" {o_suffix}"
                                if o_v_img:
                                    current_dynamic_m_img = o_v_img
                else:
                    st.info("Bu makineye tanımlı donanım bulunmuyor.")

        st.markdown("<div style='font-size:13px; font-weight:800; color:#2563eb; margin-top:15px; margin-bottom:8px;'>4. FİYATLANDIRMA VE KAYIT</div>", unsafe_allow_html=True)

        with st.container(border=True):
            sub = ((m_price * multiplier) * m_qty) + opts_total

            c_disc, c_man = st.columns(2)
            disc_p = c_disc.number_input("İskonto Oranı (%)", 0.0, 100.0, float(wd.get("disc_p", 0.0)), step=0.5)
            calc_val = sub * (1 - (disc_p / 100.0))
            use_manual = c_man.checkbox("Nihai Tutarı El İle Yaz", value=wd.get("is_manual", False))

            if use_manual:
                default_agreed = float(wd.get("agreed_price", calc_val))
                if default_agreed == 0.0:
                    default_agreed = calc_val
                agreed = st.number_input("Müşteriye Sunulacak Net Tutar", value=default_agreed, step=50.0)
            else:
                agreed = calc_val
                st.info(f"Hesaplanan Toplam: **{agreed:,.2f} {m_curr}**")

            total_cost = (m_cost * m_qty) + opts_cost_total
            total_profit = agreed - total_cost
            profit_rate = (total_profit / agreed * 100) if agreed > 0 else 0

            if is_admin:
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Maliyet", f"{total_cost:,.2f} {m_curr}")
                c2.metric("Tahmini Kâr", f"{total_profit:,.2f} {m_curr}")
                c3.metric("Kâr Oranı", f"%{profit_rate:.2f}")

            conds = {
                "machine_qty": m_qty,
                "agreed_price": agreed,
                "subtotal_calculated": sub,
                "delivery_type": d_type,
                "delivery_time": d_time,
                "shipping": ship,
                "payment_plan_text": pay,
                "bank": bnk,
                "notes": nts,
                "discount_pct": disc_p,
                "is_manual": use_manual
            }

            btn_txt = "💾 GÜNCELLE" if is_edit else "💾 KAYDET"

            if st.button(btn_txt, type="primary", use_container_width=True):
                try:
                    tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

                    if is_edit:
                        offer_id = st.session_state.edit_offer_id

                        exec_sales("""
                            UPDATE offers
                            SET customer_id=?, model_id=?, total_price=?, conditions=?,
                                total_cost=?, total_profit=?, profit_rate=?
                            WHERE id=?
                        """, (
                            cust_id, m_id, agreed, json.dumps(conds, ensure_ascii=False),
                            total_cost, total_profit, profit_rate, offer_id
                        ))

                        exec_sales("DELETE FROM offer_items WHERE offer_id=?", (offer_id,))

                        for item in selected_options_for_db:
                            exec_sales("""
                                INSERT INTO offer_items
                                (offer_id, option_id, quantity, sale_price, total_sale_price, total_cost, total_profit)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                offer_id,
                                item["id"],
                                item["qty"],
                                item["sale_price"],
                                item["total_sale_price"],
                                item["total_cost"],
                                item["total_profit"]
                            ))

                        st.success("Teklif Başarıyla Güncellendi!")
                        del st.session_state.edit_offer_id

                    else:
                        exec_sales("""
                            INSERT INTO offers
                            (customer_id, model_id, total_price, user_id, offer_date, status, conditions,
                             total_cost, total_profit, profit_rate)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cust_id, m_id, agreed, user_id, tarih, "Beklemede",
                            json.dumps(conds, ensure_ascii=False),
                            total_cost, total_profit, profit_rate
                        ))

                        res_id = get_sales("SELECT id FROM offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))

                        if res_id and selected_options_for_db:
                            offer_id = res_id[0][0]

                            for item in selected_options_for_db:
                                exec_sales("""
                                    INSERT INTO offer_items
                                    (offer_id, option_id, quantity, sale_price, total_sale_price, total_cost, total_profit)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    offer_id,
                                    item["id"],
                                    item["qty"],
                                    item["sale_price"],
                                    item["total_sale_price"],
                                    item["total_cost"],
                                    item["total_profit"]
                                ))

                        st.success("Başarıyla Arşivlendi!")

                    st.balloons()

                except Exception as e:
                    st.error(f"Kayıt Hatası: {e}")

    with col_prev:
        st.markdown("<div style='font-size:16px; font-weight:800; color:#0f172a; margin-bottom:10px;'>📄 A4 RAPOR ÖNİZLEMESİ</div>", unsafe_allow_html=True)

        html = generate_embedded_html(
            sel_cust,
            current_dynamic_m_name,
            m_price * multiplier,
            current_dynamic_m_img,
            m_specs,
            engine_options_list,
            conds,
            m_curr,
            user_id
        )

        with st.container(border=True):
            components.html(html, height=1200, scrolling=True)