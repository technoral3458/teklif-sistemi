import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
import base64
import ntpath
import posixpath
import datetime
import uuid
import html
import math

# =====================================================================
# BAYİ / ÜRETİCİ YÖNETİMİ
# dealer_management.py
# =====================================================================

USERS_DB = "users.db"
FACTORY_DB = "factory_data.db"

MENU_OPTIONS = [
    ("m_dash", "📊 Dashboard"),
    ("m_new", "📝 Yeni Teklif Hazırla"),
    ("m_cust", "👥 Müşterilerim"),
    ("m_past", "📋 Geçmiş Tekliflerim"),
    ("m_order", "📦 Siparişler"),
    ("m_prof", "⚙️ Profil Ayarlarım"),
    ("m_deal", "🏢 Bayi Yönetimi"),
    ("m_model", "📦 Tüm Modelleri Yönet"),
]

DEFAULT_DEALER_MENUS = "m_dash,m_new,m_cust,m_past,m_order,m_prof"
DEFAULT_MANUFACTURER_MENUS = "m_dash,m_model,m_prof"


# =====================================================================
# TEMEL YARDIMCI FONKSİYONLAR
# =====================================================================
def get_conn(db_path):
    return sqlite3.connect(db_path, check_same_thread=False)


def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()


def safe_text(value):
    return html.escape(str(value or ""))


def get_base64_image(path):
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
                ext = os.path.splitext(p)[1].lower().replace(".", "")
                if not ext:
                    ext = "png"
                if ext == "jpg":
                    ext = "jpeg"

                with open(p, "rb") as f:
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except Exception:
                pass

    return ""


# =====================================================================
# VERİTABANI HAZIRLIK
# =====================================================================
def ensure_users_table():
    conn = get_conn(USERS_DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            company_name TEXT,
            role TEXT DEFAULT 'dealer',
            is_approved INTEGER DEFAULT 0,
            user_type TEXT DEFAULT 'Satıcı',
            phone TEXT,
            is_verified INTEGER DEFAULT 0,
            auth_code TEXT,
            session_token TEXT,
            logo_path TEXT,
            website TEXT,
            address_full TEXT,
            allowed_menus TEXT,
            allowed_categories TEXT
        )
    """)

    cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]

    add_cols = {
        "email": "TEXT UNIQUE",
        "password": "TEXT",
        "company_name": "TEXT",
        "role": "TEXT DEFAULT 'dealer'",
        "is_approved": "INTEGER DEFAULT 0",
        "user_type": "TEXT DEFAULT 'Satıcı'",
        "phone": "TEXT",
        "is_verified": "INTEGER DEFAULT 0",
        "auth_code": "TEXT",
        "session_token": "TEXT",
        "logo_path": "TEXT DEFAULT ''",
        "website": "TEXT DEFAULT ''",
        "address_full": "TEXT DEFAULT ''",
        "allowed_menus": f"TEXT DEFAULT '{DEFAULT_DEALER_MENUS}'",
        "allowed_categories": "TEXT DEFAULT ''",
    }

    for col, col_type in add_cols.items():
        if col not in cols:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            admin_email TEXT,
            target_user_id INTEGER,
            target_email TEXT,
            target_company TEXT,
            token TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def ensure_factory_tables():
    conn = get_conn(FACTORY_DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            image_path TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            base_price REAL,
            image_path TEXT,
            specs TEXT,
            currency TEXT DEFAULT 'USD',
            port_discount REAL DEFAULT 0.0,
            compatible_options TEXT DEFAULT '',
            gallery_images TEXT DEFAULT '',
            category TEXT DEFAULT 'Diğer Makinalar',
            gallery_videos TEXT DEFAULT '',
            name_zh TEXT DEFAULT '',
            specs_zh TEXT DEFAULT '',
            user_id INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


# =====================================================================
# URL / ADMIN OLARAK HESABA GİRİŞ
# =====================================================================
def get_app_base_url():
    try:
        host = st.context.headers.get("Host", "")
        proto = st.context.headers.get("X-Forwarded-Proto", "")

        if not proto:
            proto = "https"

        if host:
            return f"{proto}://{host}"
    except Exception:
        pass

    return ""


def create_admin_login_token(target_user_id):
    ensure_users_table()

    token = str(uuid.uuid4())

    admin_id = st.session_state.get("user_id")
    admin_email = st.session_state.get("user_email", "")

    conn = get_conn(USERS_DB)

    target = conn.execute("""
        SELECT email, company_name
        FROM users
        WHERE id=? AND IFNULL(role, '') != 'admin'
    """, (target_user_id,)).fetchone()

    if not target:
        conn.close()
        return ""

    target_email = target[0] or ""
    target_company = target[1] or ""

    conn.execute("""
        UPDATE users
        SET session_token=?
        WHERE id=? AND IFNULL(role, '') != 'admin'
    """, (token, target_user_id))

    conn.execute("""
        INSERT INTO admin_login_logs (
            admin_id,
            admin_email,
            target_user_id,
            target_email,
            target_company,
            token,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        admin_id,
        admin_email,
        target_user_id,
        target_email,
        target_company,
        token,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return token


def get_admin_login_url(target_user_id, refresh=False):
    key = f"admin_login_token_{target_user_id}"

    if refresh or key not in st.session_state or not st.session_state[key]:
        st.session_state[key] = create_admin_login_token(target_user_id)

    token = st.session_state.get(key, "")

    if not token:
        return ""

    base_url = get_app_base_url()

    if base_url:
        return f"{base_url}/?session_token={token}&admin_login=1"

    return f"/?session_token={token}&admin_login=1"


def render_link_button(label, url):
    if not url:
        st.error("Giriş linki oluşturulamadı.")
        return

    if hasattr(st, "link_button"):
        st.link_button(label, url, use_container_width=True)
    else:
        st.markdown(
            f"""
            <a class="dm-link-button" href="{safe_text(url)}" target="_blank" rel="noopener noreferrer">
                {safe_text(label)}
            </a>
            """,
            unsafe_allow_html=True
        )


# =====================================================================
# VERİ OKUMA
# =====================================================================
def get_all_categories():
    ensure_factory_tables()

    conn = get_conn(FACTORY_DB)

    categories = []

    try:
        rows = conn.execute("""
            SELECT name
            FROM categories
            WHERE name IS NOT NULL AND TRIM(name) != ''
            ORDER BY name
        """).fetchall()

        categories.extend([r[0] for r in rows if r and r[0]])
    except Exception:
        pass

    try:
        rows = conn.execute("""
            SELECT DISTINCT category
            FROM models
            WHERE category IS NOT NULL AND TRIM(category) != ''
            ORDER BY category
        """).fetchall()

        categories.extend([r[0] for r in rows if r and r[0]])
    except Exception:
        pass

    conn.close()

    clean_categories = []

    for c in categories:
        c = str(c).strip()
        if c and c not in clean_categories:
            clean_categories.append(c)

    return clean_categories


def get_users(search_text="", status_filter="Tümü", type_filter="Tümü"):
    ensure_users_table()

    conn = get_conn(USERS_DB)

    query = """
        SELECT
            id,
            company_name,
            email,
            phone,
            user_type,
            role,
            is_approved,
            is_verified,
            website,
            address_full,
            allowed_menus,
            allowed_categories,
            logo_path
        FROM users
        WHERE IFNULL(role, '') != 'admin'
    """

    params = []

    if search_text:
        query += """
            AND (
                LOWER(IFNULL(company_name, '')) LIKE ?
                OR LOWER(IFNULL(email, '')) LIKE ?
                OR LOWER(IFNULL(phone, '')) LIKE ?
            )
        """
        s = f"%{search_text.lower().strip()}%"
        params.extend([s, s, s])

    if status_filter == "Aktif":
        query += " AND IFNULL(is_approved, 0) = 1"
    elif status_filter == "Onay Bekliyor":
        query += " AND IFNULL(is_approved, 0) = 0"
    elif status_filter == "Askıda":
        query += " AND IFNULL(is_approved, 0) = -1"

    if type_filter == "Satıcı":
        query += " AND IFNULL(user_type, '') LIKE '%Satıcı%'"
    elif type_filter == "Üretici":
        query += " AND IFNULL(user_type, '') LIKE '%Üretici%'"

    query += " ORDER BY company_name COLLATE NOCASE ASC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return rows


def get_user_by_id(user_id):
    ensure_users_table()

    conn = get_conn(USERS_DB)

    row = conn.execute("""
        SELECT
            id,
            company_name,
            email,
            phone,
            user_type,
            role,
            is_approved,
            is_verified,
            website,
            address_full,
            allowed_menus,
            allowed_categories,
            logo_path
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    conn.close()

    return row


# =====================================================================
# VERİ YAZMA
# =====================================================================
def update_user_info(
    user_id,
    company_name,
    email,
    phone,
    user_type,
    role,
    is_approved,
    is_verified,
    website,
    address_full,
    allowed_menus,
    allowed_categories,
    logo_path,
):
    ensure_users_table()

    conn = get_conn(USERS_DB)

    try:
        conn.execute("""
            UPDATE users
            SET
                company_name=?,
                email=?,
                phone=?,
                user_type=?,
                role=?,
                is_approved=?,
                is_verified=?,
                website=?,
                address_full=?,
                allowed_menus=?,
                allowed_categories=?,
                logo_path=?
            WHERE id=?
        """, (
            company_name,
            email,
            phone,
            user_type,
            role,
            is_approved,
            is_verified,
            website,
            address_full,
            allowed_menus,
            allowed_categories,
            logo_path,
            user_id,
        ))

        conn.commit()
        conn.close()

        return True, "Bilgiler başarıyla güncellendi."

    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu e-posta adresi başka bir kullanıcıda kayıtlı."

    except Exception as e:
        conn.close()
        return False, f"Güncelleme sırasında hata oluştu: {e}"


def create_user(company_name, email, phone, password, user_type):
    ensure_users_table()

    role = "manufacturer" if user_type == "Üretici" else "dealer"
    allowed_menus = DEFAULT_MANUFACTURER_MENUS if user_type == "Üretici" else DEFAULT_DEALER_MENUS

    conn = get_conn(USERS_DB)

    try:
        conn.execute("""
            INSERT INTO users (
                company_name,
                email,
                phone,
                password,
                user_type,
                role,
                is_approved,
                is_verified,
                allowed_menus,
                allowed_categories,
                logo_path,
                website,
                address_full
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, '', '', '', '')
        """, (
            company_name,
            email,
            phone,
            hash_password(password),
            user_type,
            role,
            allowed_menus,
        ))

        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        return True, "Yeni bayi / üretici başarıyla oluşturuldu.", new_id

    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu e-posta adresi zaten kayıtlı.", None

    except Exception as e:
        conn.close()
        return False, f"Kayıt oluşturulamadı: {e}", None


def suspend_user(user_id):
    ensure_users_table()

    conn = get_conn(USERS_DB)
    conn.execute("UPDATE users SET is_approved=-1, session_token=NULL WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def activate_user(user_id):
    ensure_users_table()

    conn = get_conn(USERS_DB)
    conn.execute("UPDATE users SET is_approved=1, is_verified=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def delete_user(user_id):
    ensure_users_table()

    conn = get_conn(USERS_DB)
    conn.execute("DELETE FROM users WHERE id=? AND IFNULL(role, '') != 'admin'", (user_id,))
    conn.commit()
    conn.close()


def change_user_password(user_id, new_password):
    ensure_users_table()

    conn = get_conn(USERS_DB)
    conn.execute(
        "UPDATE users SET password=? WHERE id=?",
        (hash_password(new_password), user_id)
    )
    conn.commit()
    conn.close()


# =====================================================================
# FORMAT / DÖNÜŞÜM
# =====================================================================
def normalize_allowed_menus(selected_codes):
    clean_codes = []

    valid_codes = [x[0] for x in MENU_OPTIONS]

    for code in selected_codes:
        if code in valid_codes and code not in clean_codes:
            clean_codes.append(code)

    return ",".join(clean_codes)


def allowed_menu_codes(allowed_menus):
    if not allowed_menus:
        return []

    return [x.strip() for x in str(allowed_menus).split(",") if x.strip()]


def allowed_category_list(allowed_categories, all_categories):
    if not allowed_categories:
        return all_categories

    allowed = [x.strip() for x in str(allowed_categories).split(",") if x.strip()]
    return [x for x in all_categories if x in allowed]


def status_text(value):
    try:
        value = int(value)
    except Exception:
        value = 0

    if value == 1:
        return "Aktif"
    if value == -1:
        return "Askıda"

    return "Onay Bekliyor"


def status_icon(value):
    try:
        value = int(value)
    except Exception:
        value = 0

    if value == 1:
        return "🟢"
    if value == -1:
        return "🔴"

    return "🟡"


def status_badge_class(value):
    try:
        value = int(value)
    except Exception:
        value = 0

    if value == 1:
        return "dm-badge-active"
    if value == -1:
        return "dm-badge-suspended"

    return "dm-badge-wait"


def user_type_icon(user_type):
    if str(user_type).strip() == "Üretici":
        return "🏭"
    return "🏪"


def go_list():
    st.session_state.dm_view = "list"
    st.session_state.dm_selected_user_id = None


def go_detail(user_id):
    st.session_state.dm_view = "detail"
    st.session_state.dm_selected_user_id = user_id


def go_new():
    st.session_state.dm_view = "new"
    st.session_state.dm_selected_user_id = None


# =====================================================================
# CSS
# =====================================================================
def inject_css():
    st.markdown("""
    <style>
    .dm-hero {
        background: linear-gradient(135deg, #111827, #dc2626);
        color: white;
        padding: 22px;
        border-radius: 22px;
        margin-bottom: 16px;
        box-shadow: 0 12px 28px rgba(15,23,42,.15);
    }

    .dm-hero h1 {
        margin: 0;
        font-size: 30px;
        font-weight: 950;
        line-height: 1.1;
        letter-spacing: -0.4px;
    }

    .dm-hero p {
        margin: 8px 0 0 0;
        color: #fee2e2;
        font-size: 14px;
        font-weight: 650;
        line-height: 1.45;
    }

    .dm-top-actions {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 8px 22px rgba(15,23,42,.05);
    }

    .dm-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 14px;
        margin-bottom: 10px;
        box-shadow: 0 6px 18px rgba(15,23,42,.045);
    }

    .dm-card-title {
        color: #111827;
        font-size: 16px;
        font-weight: 950;
        line-height: 1.25;
        margin-bottom: 5px;
    }

    .dm-card-sub {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.45;
        word-break: break-word;
    }

    .dm-badges {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 10px;
    }

    .dm-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 900;
        line-height: 1;
    }

    .dm-badge-active {
        background: #dcfce7;
        color: #166534;
    }

    .dm-badge-wait {
        background: #fef3c7;
        color: #92400e;
    }

    .dm-badge-suspended {
        background: #fee2e2;
        color: #991b1b;
    }

    .dm-badge-type {
        background: #eff6ff;
        color: #1d4ed8;
    }

    .dm-detail-head {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 8px 22px rgba(15,23,42,.055);
    }

    .dm-detail-name {
        font-size: 22px;
        font-weight: 950;
        color: #111827;
        line-height: 1.15;
        margin-bottom: 6px;
    }

    .dm-detail-meta {
        color: #64748b;
        font-size: 13px;
        font-weight: 750;
        line-height: 1.5;
        word-break: break-word;
    }

    .dm-section {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 8px 22px rgba(15,23,42,.045);
    }

    .dm-section-title {
        font-size: 19px;
        font-weight: 950;
        color: #111827;
        margin-bottom: 12px;
        line-height: 1.2;
    }

    .dm-help {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        padding: 11px 13px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 800;
        line-height: 1.45;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .dm-warning {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        color: #9a3412;
        padding: 11px 13px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 800;
        line-height: 1.45;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .dm-link-button {
        display: flex;
        width: 100%;
        min-height: 48px;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 12px 16px;
        border-radius: 14px;
        background: linear-gradient(135deg, #0f172a, #2563eb);
        color: #ffffff !important;
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 950;
        text-align: center;
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.22);
        margin-bottom: 10px;
    }

    @media (max-width: 768px) {
        .dm-hero {
            padding: 18px;
            border-radius: 20px;
            margin-bottom: 12px;
        }

        .dm-hero h1 {
            font-size: 25px;
        }

        .dm-hero p {
            font-size: 13px;
        }

        .dm-card {
            padding: 13px;
            border-radius: 17px;
        }

        .dm-card-title {
            font-size: 15px;
        }

        .dm-detail-name {
            font-size: 20px;
        }

        .dm-section {
            padding: 14px;
            border-radius: 18px;
        }

        .dm-section-title {
            font-size: 18px;
        }

        [data-testid="stCheckbox"] label {
            min-height: 40px !important;
            display: flex !important;
            align-items: center !important;
        }

        [data-testid="stCheckbox"] p {
            font-size: 15px !important;
            font-weight: 750 !important;
        }

        button {
            min-height: 46px !important;
            border-radius: 13px !important;
            font-weight: 900 !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            font-size: 16px !important;
            border-radius: 13px !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 48px !important;
            border-radius: 13px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# =====================================================================
# BİLDİRİM
# =====================================================================
def render_flash_messages():
    if st.session_state.get("dealer_flash_success"):
        msg = st.session_state.dealer_flash_success
        st.success(msg)

        try:
            st.toast(msg, icon="✅")
        except Exception:
            pass

        st.session_state.dealer_flash_success = ""

    if st.session_state.get("dealer_flash_error"):
        msg = st.session_state.dealer_flash_error
        st.error(msg)

        try:
            st.toast(msg, icon="❌")
        except Exception:
            pass

        st.session_state.dealer_flash_error = ""


# =====================================================================
# LİSTE SAYFASI
# =====================================================================
def render_list_page():
    st.markdown("""
    <div class="dm-hero">
        <h1>🏢 Bayi Yönetimi</h1>
        <p>Bayileri ve üreticileri listeden seçin. Düzenleme ekranı yalnızca seçilen kayıt için açılır.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='dm-top-actions'>", unsafe_allow_html=True)

        c1, c2 = st.columns([2, 1])

        with c1:
            search_text = st.text_input(
                "🔎 Bayi / üretici ara",
                placeholder="Firma adı, e-posta veya telefon...",
                key="dm_search_text"
            )

        with c2:
            if st.button("➕ Yeni Kayıt", type="primary", use_container_width=True):
                go_new()
                st.rerun()

        f1, f2 = st.columns(2)

        with f1:
            status_filter = st.selectbox(
                "Durum",
                ["Tümü", "Aktif", "Onay Bekliyor", "Askıda"],
                key="dm_status_filter"
            )

        with f2:
            type_filter = st.selectbox(
                "Tür",
                ["Tümü", "Satıcı", "Üretici"],
                key="dm_type_filter"
            )

        st.markdown("</div>", unsafe_allow_html=True)

    users = get_users(search_text, status_filter, type_filter)

    total_count = len(users)

    if total_count == 0:
        st.info("Aramaya uygun bayi veya üretici bulunamadı.")
        return

    st.caption(f"Toplam {total_count} kayıt listeleniyor.")

    page_size = 12

    if "dm_page" not in st.session_state:
        st.session_state.dm_page = 1

    total_pages = max(1, math.ceil(total_count / page_size))

    if st.session_state.dm_page > total_pages:
        st.session_state.dm_page = total_pages

    start = (st.session_state.dm_page - 1) * page_size
    end = start + page_size
    visible_users = users[start:end]

    for u in visible_users:
        user_id = u[0]
        company_name = u[1] or "İsimsiz Firma"
        email = u[2] or ""
        phone = u[3] or ""
        user_type = u[4] or "Satıcı"
        is_approved = u[6]
        allowed_menus = u[10] or ""

        menu_count = len(allowed_menu_codes(allowed_menus))
        type_label = "Üretici" if str(user_type).strip() == "Üretici" else "Bayi"

        st.markdown(f"""
        <div class="dm-card">
            <div class="dm-card-title">{user_type_icon(user_type)} {safe_text(company_name)}</div>
            <div class="dm-card-sub">{safe_text(email)}</div>
            <div class="dm-card-sub">{safe_text(phone)}</div>
            <div class="dm-badges">
                <span class="dm-badge {status_badge_class(is_approved)}">{status_icon(is_approved)} {safe_text(status_text(is_approved))}</span>
                <span class="dm-badge dm-badge-type">{safe_text(type_label)}</span>
                <span class="dm-badge dm-badge-type">🔑 {menu_count} menü</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        b1, b2 = st.columns(2)

        with b1:
            if st.button("✏️ Düzenle", key=f"dm_open_{user_id}", use_container_width=True):
                go_detail(user_id)
                st.rerun()

        with b2:
            login_url = get_admin_login_url(user_id)
            login_label = "🔑 Üretici Olarak Gir" if str(user_type).strip() == "Üretici" else "🔑 Bayi Olarak Gir"
            render_link_button(login_label, login_url)

    if total_pages > 1:
        st.markdown("---")

        p1, p2, p3 = st.columns([1, 2, 1])

        with p1:
            if st.button("⬅️ Önceki", use_container_width=True, disabled=st.session_state.dm_page <= 1):
                st.session_state.dm_page -= 1
                st.rerun()

        with p2:
            st.markdown(
                f"<div style='text-align:center; font-weight:900; padding-top:10px;'>Sayfa {st.session_state.dm_page} / {total_pages}</div>",
                unsafe_allow_html=True
            )

        with p3:
            if st.button("Sonraki ➡️", use_container_width=True, disabled=st.session_state.dm_page >= total_pages):
                st.session_state.dm_page += 1
                st.rerun()


# =====================================================================
# DETAY SAYFASI
# =====================================================================
def render_detail_page(user_id):
    user = get_user_by_id(user_id)

    if not user:
        st.session_state.dealer_flash_error = "Seçili bayi / üretici bulunamadı."
        go_list()
        st.rerun()

    (
        user_id,
        company_name,
        email,
        phone,
        user_type,
        role,
        is_approved,
        is_verified,
        website,
        address_full,
        allowed_menus,
        allowed_categories,
        logo_path,
    ) = user

    back_col, title_col = st.columns([1, 3])

    with back_col:
        if st.button("⬅️ Liste", use_container_width=True):
            go_list()
            st.rerun()

    with title_col:
        st.markdown(
            "<div style='font-size:20px; font-weight:950; padding-top:9px;'>Bayi / Üretici Detayı</div>",
            unsafe_allow_html=True
        )

    st.markdown(f"""
    <div class="dm-detail-head">
        <div class="dm-detail-name">{user_type_icon(user_type)} {safe_text(company_name or "İsimsiz Firma")}</div>
        <div class="dm-detail-meta">{safe_text(email)}</div>
        <div class="dm-detail-meta">{safe_text(phone)}</div>
        <div class="dm-badges">
            <span class="dm-badge {status_badge_class(is_approved)}">{status_icon(is_approved)} {safe_text(status_text(is_approved))}</span>
            <span class="dm-badge dm-badge-type">{safe_text(user_type or "Satıcı")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    detail_tabs = st.tabs(["📌 Bilgiler", "🔑 İzinler", "⚙️ İşlemler"])

    # =================================================================
    # BİLGİLER
    # =================================================================
    with detail_tabs[0]:
        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">📌 Firma Bilgileri</div>
        </div>
        """, unsafe_allow_html=True)

        company_name_input = st.text_input(
            "Firma Adı",
            value=company_name or "",
            key=f"dm_company_name_{user_id}"
        )

        email_input = st.text_input(
            "E-posta",
            value=email or "",
            key=f"dm_email_{user_id}"
        )

        phone_input = st.text_input(
            "Telefon",
            value=phone or "",
            key=f"dm_phone_{user_id}"
        )

        type_values = ["Satıcı", "Üretici"]
        current_type = "Üretici" if str(user_type).strip() == "Üretici" else "Satıcı"

        user_type_input = st.selectbox(
            "Kullanıcı Türü",
            type_values,
            index=type_values.index(current_type),
            key=f"dm_user_type_{user_id}"
        )

        status_values = ["Aktif", "Onay Bekliyor", "Askıda"]

        if int(is_approved or 0) == 1:
            current_status = "Aktif"
        elif int(is_approved or 0) == -1:
            current_status = "Askıda"
        else:
            current_status = "Onay Bekliyor"

        status_input = st.selectbox(
            "Hesap Durumu",
            status_values,
            index=status_values.index(current_status),
            key=f"dm_status_{user_id}"
        )

        is_verified_input = st.checkbox(
            "E-posta doğrulanmış kabul edilsin",
            value=bool(is_verified),
            key=f"dm_verified_{user_id}"
        )

        website_input = st.text_input(
            "Web Sitesi",
            value=website or "",
            placeholder="https://www.firma.com",
            key=f"dm_website_{user_id}"
        )

        address_input = st.text_area(
            "Adres",
            value=address_full or "",
            height=110,
            key=f"dm_address_{user_id}"
        )

        logo_path_input = st.text_input(
            "Logo Dosya Yolu",
            value=logo_path or "",
            placeholder="images/logo.png",
            key=f"dm_logo_path_{user_id}"
        )

        logo_preview = get_base64_image(logo_path_input)

        if logo_preview and logo_preview.startswith("data:image"):
            st.image(logo_preview, caption="Logo Önizleme", width=220)

        st.markdown("""
        <div class="dm-help">
            Kaydet dediğinizde bilgiler güncellenir ve otomatik olarak bayi listesine dönülür.
        </div>
        """, unsafe_allow_html=True)

        if st.button("💾 BİLGİLERİ KAYDET VE LİSTEYE DÖN", type="primary", use_container_width=True, key=f"dm_save_info_{user_id}"):
            save_user_detail(
                user_id=user_id,
                company_name_input=company_name_input,
                email_input=email_input,
                phone_input=phone_input,
                user_type_input=user_type_input,
                status_input=status_input,
                is_verified_input=is_verified_input,
                website_input=website_input,
                address_input=address_input,
                logo_path_input=logo_path_input,
                allowed_menus=allowed_menus,
                allowed_categories=allowed_categories,
                go_back=True
            )

    # =================================================================
    # İZİNLER
    # =================================================================
    with detail_tabs[1]:
        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">🔑 Menü İzinleri</div>
        </div>
        """, unsafe_allow_html=True)

        current_menu_codes = allowed_menu_codes(allowed_menus)
        selected_menu_codes = []

        for code, label in MENU_OPTIONS:
            checked = code in current_menu_codes

            if st.checkbox(label, value=checked, key=f"dm_menu_{user_id}_{code}"):
                selected_menu_codes.append(code)

        if not selected_menu_codes:
            st.markdown("""
            <div class="dm-warning">
                En az bir menü izni seçilmelidir.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">🗂️ Kategori İzinleri</div>
        </div>
        """, unsafe_allow_html=True)

        all_categories = get_all_categories()

        selected_categories = []

        if all_categories:
            current_categories = allowed_category_list(allowed_categories, all_categories)

            allow_all_categories = st.checkbox(
                "Tüm kategorilere izin ver",
                value=(not allowed_categories),
                key=f"dm_all_categories_{user_id}"
            )

            if allow_all_categories:
                selected_categories = []
                st.info("Bu kullanıcı tüm mevcut ve gelecekte eklenecek kategorileri görebilir.")
            else:
                for cat in all_categories:
                    checked = cat in current_categories

                    if st.checkbox(cat, value=checked, key=f"dm_cat_{user_id}_{cat}"):
                        selected_categories.append(cat)
        else:
            st.info("Sistemde kategori bulunmadığı için kategori izni seçilemiyor.")

        if st.button("💾 İZİNLERİ KAYDET VE LİSTEYE DÖN", type="primary", use_container_width=True, key=f"dm_save_permissions_{user_id}"):
            if not selected_menu_codes:
                st.session_state.dealer_flash_error = "En az bir menü izni seçmelisiniz."
                st.rerun()

            company_name_input = st.session_state.get(f"dm_company_name_{user_id}", company_name or "")
            email_input = st.session_state.get(f"dm_email_{user_id}", email or "")
            phone_input = st.session_state.get(f"dm_phone_{user_id}", phone or "")
            user_type_input = st.session_state.get(f"dm_user_type_{user_id}", user_type or "Satıcı")
            status_input = st.session_state.get(f"dm_status_{user_id}", status_text(is_approved))
            is_verified_input = st.session_state.get(f"dm_verified_{user_id}", bool(is_verified))
            website_input = st.session_state.get(f"dm_website_{user_id}", website or "")
            address_input = st.session_state.get(f"dm_address_{user_id}", address_full or "")
            logo_path_input = st.session_state.get(f"dm_logo_path_{user_id}", logo_path or "")

            new_allowed_menus = normalize_allowed_menus(selected_menu_codes)
            new_allowed_categories = "" if not selected_categories else ",".join(selected_categories)

            save_user_detail(
                user_id=user_id,
                company_name_input=company_name_input,
                email_input=email_input,
                phone_input=phone_input,
                user_type_input=user_type_input,
                status_input=status_input,
                is_verified_input=is_verified_input,
                website_input=website_input,
                address_input=address_input,
                logo_path_input=logo_path_input,
                allowed_menus=new_allowed_menus,
                allowed_categories=new_allowed_categories,
                go_back=True
            )

    # =================================================================
    # İŞLEMLER
    # =================================================================
    with detail_tabs[2]:
        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">🔑 Hesaba Gir</div>
        </div>
        """, unsafe_allow_html=True)

        login_url = get_admin_login_url(user_id)
        login_label = "🔑 Bu Üretici Olarak Sisteme Gir" if str(user_type).strip() == "Üretici" else "🔑 Bu Bayi Olarak Sisteme Gir"

        render_link_button(login_label, login_url)

        st.markdown("""
        <div class="dm-help">
            Bu buton yeni sekme açar. Seçili bayi / üretici hesabıyla otomatik giriş yapılır.
            Yönetici ekranınız kapanmaz.
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Giriş Linkini Yenile", use_container_width=True, key=f"dm_refresh_login_{user_id}"):
            get_admin_login_url(user_id, refresh=True)
            st.session_state.dealer_flash_success = "Yeni giriş linki oluşturuldu."
            st.rerun()

        st.markdown("---")

        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">⚙️ Hesap Durumu</div>
        </div>
        """, unsafe_allow_html=True)

        a1, a2 = st.columns(2)

        with a1:
            if st.button("✅ Aktif Et / Onayla", use_container_width=True, key=f"dm_activate_{user_id}"):
                activate_user(user_id)
                get_admin_login_url(user_id, refresh=True)
                st.session_state.dealer_flash_success = "Hesap aktif edildi."
                go_list()
                st.rerun()

        with a2:
            if st.button("🚫 Askıya Al", use_container_width=True, key=f"dm_suspend_{user_id}"):
                suspend_user(user_id)
                st.session_state.dealer_flash_success = "Hesap askıya alındı."
                go_list()
                st.rerun()

        st.markdown("---")

        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">🔐 Şifre Değiştir</div>
        </div>
        """, unsafe_allow_html=True)

        new_password = st.text_input(
            "Yeni Şifre",
            type="password",
            key=f"dm_password_{user_id}",
            placeholder="Yeni şifre girin"
        )

        if st.button("🔐 ŞİFREYİ GÜNCELLE", use_container_width=True, key=f"dm_change_password_{user_id}"):
            if len(new_password.strip()) < 4:
                st.session_state.dealer_flash_error = "Şifre en az 4 karakter olmalıdır."
                st.rerun()

            change_user_password(user_id, new_password.strip())
            get_admin_login_url(user_id, refresh=True)
            st.session_state.dealer_flash_success = "Şifre başarıyla güncellendi."
            go_list()
            st.rerun()

        st.markdown("---")

        st.markdown("""
        <div class="dm-section">
            <div class="dm-section-title">🗑️ Kaydı Sil</div>
        </div>
        """, unsafe_allow_html=True)

        confirm_delete = st.checkbox(
            "Bu kaydı silmek istediğimi onaylıyorum",
            key=f"dm_confirm_delete_{user_id}"
        )

        if st.button("🗑️ KAYDI SİL", use_container_width=True, key=f"dm_delete_{user_id}"):
            if not confirm_delete:
                st.session_state.dealer_flash_error = "Silmek için önce onay kutusunu işaretleyin."
                st.rerun()

            delete_user(user_id)
            st.session_state.dealer_flash_success = "Kayıt silindi."
            go_list()
            st.rerun()


def save_user_detail(
    user_id,
    company_name_input,
    email_input,
    phone_input,
    user_type_input,
    status_input,
    is_verified_input,
    website_input,
    address_input,
    logo_path_input,
    allowed_menus,
    allowed_categories,
    go_back=True
):
    if not str(company_name_input).strip():
        st.session_state.dealer_flash_error = "Firma adı boş bırakılamaz."
        st.rerun()

    if not str(email_input).strip():
        st.session_state.dealer_flash_error = "E-posta boş bırakılamaz."
        st.rerun()

    new_role = "manufacturer" if user_type_input == "Üretici" else "dealer"

    if status_input == "Aktif":
        new_status = 1
    elif status_input == "Askıda":
        new_status = -1
    else:
        new_status = 0

    ok, msg = update_user_info(
        user_id=user_id,
        company_name=str(company_name_input).strip(),
        email=str(email_input).strip().lower(),
        phone=str(phone_input).strip(),
        user_type=user_type_input,
        role=new_role,
        is_approved=new_status,
        is_verified=1 if is_verified_input else 0,
        website=str(website_input).strip(),
        address_full=str(address_input).strip(),
        allowed_menus=allowed_menus,
        allowed_categories=allowed_categories,
        logo_path=str(logo_path_input).strip(),
    )

    if ok:
        get_admin_login_url(user_id, refresh=True)
        st.session_state.dealer_flash_success = "Bilgiler kaydedildi."
        if go_back:
            go_list()
    else:
        st.session_state.dealer_flash_error = msg

    st.rerun()


# =====================================================================
# YENİ KAYIT SAYFASI
# =====================================================================
def render_new_page():
    back_col, title_col = st.columns([1, 3])

    with back_col:
        if st.button("⬅️ Liste", use_container_width=True):
            go_list()
            st.rerun()

    with title_col:
        st.markdown(
            "<div style='font-size:20px; font-weight:950; padding-top:9px;'>Yeni Bayi / Üretici</div>",
            unsafe_allow_html=True
        )

    st.markdown("""
    <div class="dm-section">
        <div class="dm-section-title">➕ Yeni Kayıt Oluştur</div>
        <div class="dm-help">Yeni kayıt aktif ve doğrulanmış olarak oluşturulur. Sonrasında listeden düzenleyebilirsiniz.</div>
    </div>
    """, unsafe_allow_html=True)

    new_company = st.text_input("Firma Adı *", key="dm_new_company")
    new_email = st.text_input("E-posta *", key="dm_new_email")
    new_phone = st.text_input("Telefon", key="dm_new_phone")
    new_type = st.selectbox("Kullanıcı Türü", ["Satıcı", "Üretici"], key="dm_new_type")
    new_password = st.text_input("Geçici Şifre *", type="password", key="dm_new_password")
    new_password_again = st.text_input("Geçici Şifre Tekrar *", type="password", key="dm_new_password_again")

    if st.button("➕ KAYDI OLUŞTUR VE LİSTEYE DÖN", type="primary", use_container_width=True):
        if not new_company.strip():
            st.session_state.dealer_flash_error = "Firma adı zorunludur."
            st.rerun()

        if not new_email.strip():
            st.session_state.dealer_flash_error = "E-posta zorunludur."
            st.rerun()

        if not new_password.strip():
            st.session_state.dealer_flash_error = "Şifre zorunludur."
            st.rerun()

        if new_password != new_password_again:
            st.session_state.dealer_flash_error = "Şifreler eşleşmiyor."
            st.rerun()

        ok, msg, new_id = create_user(
            company_name=new_company.strip(),
            email=new_email.strip().lower(),
            phone=new_phone.strip(),
            password=new_password.strip(),
            user_type=new_type
        )

        if ok:
            if new_id:
                get_admin_login_url(new_id, refresh=True)

            st.session_state.dealer_flash_success = "Yeni kayıt oluşturuldu."
            go_list()
        else:
            st.session_state.dealer_flash_error = msg

        st.rerun()


# =====================================================================
# ANA GİRİŞ
# =====================================================================
def show_dealer_management():
    ensure_users_table()
    ensure_factory_tables()
    inject_css()

    if st.session_state.get("user_role") != "admin":
        st.error("Bu sayfaya yalnızca sistem yöneticisi erişebilir.")
        return

    if "dm_view" not in st.session_state:
        st.session_state.dm_view = "list"

    if "dm_selected_user_id" not in st.session_state:
        st.session_state.dm_selected_user_id = None

    render_flash_messages()

    if st.session_state.dm_view == "new":
        render_new_page()
        return

    if st.session_state.dm_view == "detail" and st.session_state.dm_selected_user_id:
        render_detail_page(st.session_state.dm_selected_user_id)
        return

    render_list_page()