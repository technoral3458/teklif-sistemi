import streamlit as st
import sqlite3
import pandas as pd
import html

# =====================================================================
# SABİT LİSTELER
# =====================================================================
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


# =====================================================================
# CSS
# =====================================================================
def inject_customer_css():
    st.markdown("""
    <style>
    .crm-hero {
        background: linear-gradient(135deg, #0f172a, #2563eb);
        color: white;
        border-radius: 24px;
        padding: 24px;
        margin-bottom: 18px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.16);
    }

    .crm-hero h1 {
        margin: 0;
        font-size: 30px;
        font-weight: 900;
        letter-spacing: -0.5px;
    }

    .crm-hero p {
        margin: 8px 0 0 0;
        color: #dbeafe;
        font-size: 14px;
        line-height: 1.5;
    }

    .crm-filter-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }

    .crm-count {
        color: #94a3b8;
        font-size: 13px;
        text-align: right;
        font-weight: 700;
        margin: 8px 0 12px 0;
    }

    .crm-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }

    .crm-company {
        font-size: 18px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.2;
        word-break: break-word;
    }

    .crm-person {
        font-size: 13px;
        font-weight: 800;
        color: #64748b;
        margin-top: 5px;
    }

    .crm-line {
        font-size: 13px;
        color: #334155;
        font-weight: 650;
        line-height: 1.55;
    }

    .crm-badge {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        font-size: 12px;
        font-weight: 900;
        margin-top: 8px;
    }

    .crm-section-title {
        font-size: 13px;
        font-weight: 900;
        color: #64748b;
        letter-spacing: .4px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .crm-detail-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
        margin-bottom: 14px;
    }

    .crm-detail-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .crm-detail-value {
        color: #0f172a;
        font-size: 15px;
        font-weight: 750;
        margin-bottom: 14px;
        word-break: break-word;
    }

    @media (max-width: 768px) {
        .crm-hero {
            padding: 20px;
            border-radius: 22px;
        }

        .crm-hero h1 {
            font-size: 25px !important;
        }

        .crm-filter-box {
            padding: 16px;
            border-radius: 18px;
        }

        .crm-card {
            padding: 18px;
            border-radius: 18px;
        }

        .crm-company {
            font-size: 20px;
        }

        .crm-count {
            text-align: left;
            margin-top: 10px;
        }

        div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }

        button {
            min-height: 46px !important;
            border-radius: 14px !important;
            font-weight: 800 !important;
        }

        input, textarea {
            font-size: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# =====================================================================
# VERİTABANI
# =====================================================================
def ensure_customer_schema():
    conn = sqlite3.connect("sales_data.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            user_id INTEGER DEFAULT 1,
            country TEXT DEFAULT '',
            city TEXT DEFAULT '',
            authorized_person TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            address_full TEXT DEFAULT '',
            tax_office TEXT DEFAULT '',
            tax_id TEXT DEFAULT ''
        )
    """)

    cols = [c[1] for c in conn.execute("PRAGMA table_info(customers)").fetchall()]
    required_cols = {
        "company_name": "TEXT DEFAULT ''",
        "user_id": "INTEGER DEFAULT 1",
        "country": "TEXT DEFAULT ''",
        "city": "TEXT DEFAULT ''",
        "authorized_person": "TEXT DEFAULT ''",
        "email": "TEXT DEFAULT ''",
        "phone": "TEXT DEFAULT ''",
        "address": "TEXT DEFAULT ''",
        "address_full": "TEXT DEFAULT ''",
        "tax_office": "TEXT DEFAULT ''",
        "tax_id": "TEXT DEFAULT ''",
    }

    for col, typ in required_cols.items():
        if col not in cols:
            try:
                conn.execute(f"ALTER TABLE customers ADD COLUMN {col} {typ}")
            except Exception:
                pass

    conn.commit()
    conn.close()


def get_sales(query, params=()):
    try:
        conn = sqlite3.connect("sales_data.db", check_same_thread=False)
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return res
    except Exception as e:
        st.error(f"Veritabanı okuma hatası: {e}")
        return []


def exec_sales(query, params=()):
    try:
        conn = sqlite3.connect("sales_data.db", check_same_thread=False)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Veritabanı işlem hatası: {e}")
        return False


def esc(value):
    return html.escape(str(value if value is not None else ""))


# =====================================================================
# ANA FONKSİYON
# =====================================================================
def show_customer_management(user_id, is_admin=False):
    inject_customer_css()
    ensure_customer_schema()

    if "cust_view" not in st.session_state:
        st.session_state.cust_view = "list"
    if "edit_cust_id" not in st.session_state:
        st.session_state.edit_cust_id = None
    if "detail_cust_id" not in st.session_state:
        st.session_state.detail_cust_id = None

    if st.session_state.cust_view == "list":
        show_list(user_id, is_admin)
    elif st.session_state.cust_view == "add":
        show_form(user_id, mode="add", is_admin=is_admin)
    elif st.session_state.cust_view == "edit":
        show_form(user_id, mode="edit", cust_id=st.session_state.edit_cust_id, is_admin=is_admin)
    elif st.session_state.cust_view == "detail":
        show_detail(user_id, st.session_state.detail_cust_id, is_admin)


# =====================================================================
# LİSTE SAYFASI
# =====================================================================
def show_list(user_id, is_admin):
    st.markdown("""
    <div class="crm-hero">
        <h1>👥 Müşteri Yönetimi</h1>
        <p>Müşterilerinizi daha sade, hızlı ve mobil uyumlu kart yapısıyla yönetin.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("➕ YENİ MÜŞTERİ EKLE", type="primary", use_container_width=True):
        st.session_state.cust_view = "add"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if is_admin:
        custs = get_sales("""
            SELECT id, company_name, authorized_person, phone, email, city, country
            FROM customers
            ORDER BY id DESC
        """)
    else:
        custs = get_sales("""
            SELECT id, company_name, authorized_person, phone, email, city, country
            FROM customers
            WHERE user_id=?
            ORDER BY id DESC
        """, (user_id,))

    if not custs:
        st.info("Henüz kayıtlı müşteri bulunmuyor. Yeni müşteri ekleyerek başlayabilirsiniz.")
        return

    df = pd.DataFrame(custs, columns=["ID", "Firma Adı", "Yetkili", "Telefon", "E-Posta", "Şehir", "Ülke"])

    st.markdown("<div class='crm-filter-box'>", unsafe_allow_html=True)
    st.markdown("<div class='crm-section-title'>Hızlı Filtreleme</div>", unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    search_term = f1.text_input("🔍 Kelime ile ara", placeholder="Firma, yetkili, telefon veya e-posta...")
    unique_countries = ["Tümü"] + sorted([str(c) for c in df["Ülke"].dropna().unique() if str(c).strip()])
    unique_cities = ["Tümü"] + sorted([str(c) for c in df["Şehir"].dropna().unique() if str(c).strip()])
    selected_country = f2.selectbox("🌍 Ülke", options=unique_countries)
    selected_city = f3.selectbox("🏙️ Şehir", options=unique_cities)

    st.markdown("</div>", unsafe_allow_html=True)

    if search_term:
        s = search_term.lower().strip()
        df = df[
            df["Firma Adı"].astype(str).str.lower().str.contains(s, na=False) |
            df["Yetkili"].astype(str).str.lower().str.contains(s, na=False) |
            df["Telefon"].astype(str).str.lower().str.contains(s, na=False) |
            df["E-Posta"].astype(str).str.lower().str.contains(s, na=False)
        ]

    if selected_country != "Tümü":
        df = df[df["Ülke"] == selected_country]

    if selected_city != "Tümü":
        df = df[df["Şehir"] == selected_city]

    st.markdown(f"<div class='crm-count'>Toplam <b>{len(df)}</b> müşteri listeleniyor.</div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Seçtiğiniz filtrelere uygun müşteri bulunamadı.")
        return

    for _, row in df.iterrows():
        cust_id = int(row["ID"])
        comp = esc(row["Firma Adı"] or "İsimsiz Firma")
        auth = esc(row["Yetkili"] or "-")
        phone = esc(row["Telefon"] or "-")
        email = esc(row["E-Posta"] or "-")
        country = esc(row["Ülke"] or "-")
        city = esc(row["Şehir"] or "-")

        st.markdown("<div class='crm-card'>", unsafe_allow_html=True)

        c1, c2 = st.columns([3, 1], vertical_alignment="center")

        with c1:
            st.markdown(f"""
                <div class="crm-company">🏢 {comp}</div>
                <div class="crm-person">👤 {auth}</div>
                <div class="crm-badge">🌍 {country} / {city}</div>
                <div style="height:10px;"></div>
                <div class="crm-line">📞 {phone}</div>
                <div class="crm-line">✉️ {email}</div>
            """, unsafe_allow_html=True)

        with c2:
            b1, b2, b3 = st.columns(3)
            if b1.button("👁️", key=f"view_customer_{cust_id}", help="Detay", use_container_width=True):
                st.session_state.detail_cust_id = cust_id
                st.session_state.cust_view = "detail"
                st.rerun()

            if b2.button("✏️", key=f"edit_customer_{cust_id}", help="Düzenle", use_container_width=True):
                st.session_state.edit_cust_id = cust_id
                st.session_state.cust_view = "edit"
                st.rerun()

            if b3.button("🗑️", key=f"delete_customer_{cust_id}", help="Sil", use_container_width=True):
                exec_sales("DELETE FROM customers WHERE id=?", (cust_id,))
                st.success("Müşteri silindi.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# DETAY SAYFASI
# =====================================================================
def show_detail(user_id, cust_id, is_admin):
    if is_admin:
        c_data = get_sales("""
            SELECT company_name, authorized_person, phone, email, address_full,
                   country, city, tax_office, tax_id
            FROM customers
            WHERE id=?
        """, (cust_id,))
    else:
        c_data = get_sales("""
            SELECT company_name, authorized_person, phone, email, address_full,
                   country, city, tax_office, tax_id
            FROM customers
            WHERE id=? AND user_id=?
        """, (cust_id, user_id))

    if not c_data:
        st.error("Müşteri bulunamadı.")
        if st.button("🔙 Listeye Dön", type="primary"):
            st.session_state.cust_view = "list"
            st.rerun()
        return

    c_info = c_data[0]

    if st.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.cust_view = "list"
        st.rerun()

    company = esc(c_info[0] or "İsimsiz Firma")

    st.markdown(f"""
    <div class="crm-hero">
        <h1>🏢 {company}</h1>
        <p>Müşteri bilgi kartı ve geçmiş teklif kayıtları.</p>
    </div>
    """, unsafe_allow_html=True)

    d1, d2 = st.columns(2)

    with d1:
        st.markdown("<div class='crm-detail-card'>", unsafe_allow_html=True)
        detail_item("Yetkili Kişi", f"👤 {c_info[1] or '-'}")
        detail_item("Telefon", f"📞 {c_info[2] or '-'}")
        detail_item("E-Posta", f"✉️ {c_info[3] or '-'}")
        detail_item("Vergi Bilgileri", f"🏢 {c_info[7] or '-'} / {c_info[8] or '-'}")
        st.markdown("</div>", unsafe_allow_html=True)

    with d2:
        st.markdown("<div class='crm-detail-card'>", unsafe_allow_html=True)
        detail_item("Lokasyon", f"🌍 {c_info[5] or '-'} / {c_info[6] or '-'}")
        detail_item("Açık Adres", c_info[4] or "Adres girilmemiş.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='crm-section-title'>📋 Bu müşteriye ait teklifler</div>", unsafe_allow_html=True)

    offers = get_sales("""
        SELECT id, total_price, status, offer_date
        FROM offers
        WHERE customer_id=?
        ORDER BY id DESC
    """, (cust_id,))

    if offers:
        df_offers = pd.DataFrame(offers, columns=["Teklif No", "Tutar", "Durum", "Tarih"])
        df_offers["Teklif No"] = df_offers["Teklif No"].apply(lambda x: f"TR-{x}")
        st.dataframe(df_offers, use_container_width=True, hide_index=True)
    else:
        st.info("Bu müşteriye ait geçmiş teklif veya sipariş kaydı bulunmuyor.")


def detail_item(label, value):
    st.markdown(f"""
        <div class="crm-detail-label">{esc(label)}</div>
        <div class="crm-detail-value">{esc(value)}</div>
    """, unsafe_allow_html=True)


# =====================================================================
# EKLE / DÜZENLE FORMU
# =====================================================================
def show_form(user_id, mode="add", cust_id=None, is_admin=False):
    if st.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.cust_view = "list"
        st.rerun()

    title = "✏️ Müşteri Kartını Düzenle" if mode == "edit" else "➕ Yeni Müşteri Ekle"

    st.markdown(f"""
    <div class="crm-hero">
        <h1>{title}</h1>
        <p>Firma, iletişim, vergi ve lokasyon bilgilerini düzenleyin.</p>
    </div>
    """, unsafe_allow_html=True)

    if mode == "edit" and cust_id:
        if is_admin:
            c_data = get_sales("""
                SELECT company_name, authorized_person, phone, email, address_full,
                       country, city, tax_office, tax_id
                FROM customers
                WHERE id=?
            """, (cust_id,))
        else:
            c_data = get_sales("""
                SELECT company_name, authorized_person, phone, email, address_full,
                       country, city, tax_office, tax_id
                FROM customers
                WHERE id=? AND user_id=?
            """, (cust_id, user_id))

        if not c_data:
            st.error("Müşteri bulunamadı.")
            return

        c_info = list(c_data[0])
    else:
        c_info = ["", "", "", "", "", "", "", "", ""]

    with st.form("customer_form"):
        st.markdown("<div class='crm-section-title'>Firma Bilgileri</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        f_comp = c1.text_input("Firma Adı *", value=c_info[0] or "", placeholder="Örn: ABC Makine Ltd. Şti.")
        f_auth = c2.text_input("Yetkili Kişi *", value=c_info[1] or "", placeholder="Ad Soyad")

        c3, c4 = st.columns(2)
        f_tax_office = c3.text_input("Vergi Dairesi", value=c_info[7] or "", placeholder="Örn: İlyasbey V.D.")
        f_tax_id = c4.text_input("Vergi Numarası / TC", value=c_info[8] or "", placeholder="Örn: 1234567890")

        st.markdown("<div class='crm-section-title'>İletişim Bilgileri</div>", unsafe_allow_html=True)

        c5, c6 = st.columns(2)
        f_phone = c5.text_input("Telefon", value=c_info[2] or "", placeholder="+90 5XX...")
        f_email = c6.text_input("E-Posta", value=c_info[3] or "", placeholder="info@firma.com")

        st.markdown("<div class='crm-section-title'>Lokasyon Bilgileri</div>", unsafe_allow_html=True)

        country_options = list(COUNTRIES)
        city_options = list(CITIES)

        if c_info[5] and c_info[5] not in country_options:
            country_options.insert(0, c_info[5])

        if c_info[6] and c_info[6] not in city_options:
            city_options.insert(0, c_info[6])

        country_index = country_options.index(c_info[5]) if c_info[5] in country_options else 0
        city_index = city_options.index(c_info[6]) if c_info[6] in city_options else 0

        c7, c8 = st.columns(2)
        f_country = c7.selectbox("Ülke *", options=country_options, index=country_index)
        f_city = c8.selectbox("Şehir *", options=city_options, index=city_index)

        f_addr = st.text_area("Açık Adres", value=c_info[4] or "", height=110, placeholder="Faturada görünecek tam adres...")

        submitted = st.form_submit_button("💾 BİLGİLERİ KAYDET", type="primary", use_container_width=True)

        if submitted:
            if not f_comp.strip() or not f_auth.strip() or not f_country or not f_city:
                st.error("Firma, yetkili, ülke ve şehir alanları zorunludur.")
                return

            if mode == "add":
                ok = exec_sales("""
                    INSERT INTO customers (
                        company_name, authorized_person, phone, email, address_full,
                        country, city, tax_office, tax_id, user_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f_comp.strip(), f_auth.strip(), f_phone.strip(), f_email.strip(),
                    f_addr.strip(), f_country, f_city, f_tax_office.strip(),
                    f_tax_id.strip(), user_id
                ))

                if ok:
                    st.success("Müşteri başarıyla eklendi.")

            else:
                ok = exec_sales("""
                    UPDATE customers
                    SET company_name=?, authorized_person=?, phone=?, email=?,
                        address_full=?, country=?, city=?, tax_office=?, tax_id=?
                    WHERE id=?
                """, (
                    f_comp.strip(), f_auth.strip(), f_phone.strip(), f_email.strip(),
                    f_addr.strip(), f_country, f_city, f_tax_office.strip(),
                    f_tax_id.strip(), cust_id
                ))

                if ok:
                    st.success("Müşteri bilgileri güncellendi.")

            st.session_state.cust_view = "list"
            st.rerun()