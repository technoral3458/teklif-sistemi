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


# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================
def get_conn(db_path):
    return sqlite3.connect(db_path, check_same_thread=False)


def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()


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


def get_or_create_admin_login_url(target_user_id):
    key = f"admin_login_token_{target_user_id}"

    if key not in st.session_state or not st.session_state[key]:
        st.session_state[key] = create_admin_login_token(target_user_id)

    token = st.session_state.get(key, "")

    if not token:
        return ""

    base_url = get_app_base_url()

    if base_url:
        return f"{base_url}/?session_token={token}&admin_login=1"

    return f"/?session_token={token}&admin_login=1"


def refresh_admin_login_token(target_user_id):
    key = f"admin_login_token_{target_user_id}"
    st.session_state[key] = create_admin_login_token(target_user_id)


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

    query += " ORDER BY id DESC"

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
            DEFAULT_DEALER_MENUS,
        ))

        conn.commit()
        conn.close()

        return True, "Yeni bayi / üretici başarıyla oluşturuldu."

    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu e-posta adresi zaten kayıtlı."

    except Exception as e:
        conn.close()
        return False, f"Kayıt oluşturulamadı: {e}"


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


def normalize_allowed_menus(selected_labels):
    selected_codes = []

    for code, label in MENU_OPTIONS:
        if label in selected_labels:
            selected_codes.append(code)

    return ",".join(selected_codes)


def labels_from_allowed_menus(allowed_menus):
    allowed_codes = []

    if allowed_menus:
        allowed_codes = [x.strip() for x in str(allowed_menus).split(",") if x.strip()]

    labels = []

    for code, label in MENU_OPTIONS:
        if code in allowed_codes:
            labels.append(label)

    return labels


def categories_from_allowed(allowed_categories, all_categories):
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
        return "✅ Aktif"
    if value == -1:
        return "⛔ Askıda"

    return "⏳ Onay Bekliyor"


def status_plain(value):
    try:
        value = int(value)
    except Exception:
        value = 0

    if value == 1:
        return "Aktif"
    if value == -1:
        return "Askıda"

    return "Onay Bekliyor"


def inject_css():
    st.markdown("""
    <style>
    .dealer-hero {
        background: linear-gradient(135deg, #0f172a, #dc2626);
        color: white;
        padding: 28px;
        border-radius: 24px;
        margin-bottom: 24px;
        box-shadow: 0 14px 32px rgba(15,23,42,.16);
    }

    .dealer-hero h1 {
        margin: 0;
        font-size: 34px;
        font-weight: 950;
        letter-spacing: -0.5px;
    }

    .dealer-hero p {
        margin: 8px 0 0 0;
        color: #fee2e2;
        font-size: 14px;
        font-weight: 600;
    }

    .dealer-version {
        background: #ecfeff;
        color: #155e75;
        border: 1px solid #a5f3fc;
        border-radius: 14px;
        padding: 10px 14px;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 16px;
    }

    .dealer-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 22px;
        padding: 20px;
        box-shadow: 0 10px 24px rgba(15,23,42,.06);
        margin-bottom: 18px;
    }

    .dealer-section-title {
        font-size: 19px;
        font-weight: 950;
        color: #0f172a;
        margin: 0 0 14px 0;
    }

    .dealer-small-text {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        margin-top: -5px;
        margin-bottom: 14px;
    }

    .dealer-user-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .dealer-user-name {
        color: #0f172a;
        font-size: 16px;
        font-weight: 950;
        margin-bottom: 4px;
    }

    .dealer-user-meta {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.5;
    }

    .dealer-status-active {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 900;
        margin-top: 8px;
    }

    .dealer-status-wait {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 900;
        margin-top: 8px;
    }

    .dealer-status-suspended {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 900;
        margin-top: 8px;
    }

    .dealer-preview {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 18px;
        padding: 16px;
        margin-top: 8px;
        margin-bottom: 14px;
    }

    .dealer-preview-title {
        color: #0f172a;
        font-size: 15px;
        font-weight: 950;
        margin-bottom: 5px;
    }

    .dealer-preview-line {
        color: #475569;
        font-size: 13px;
        font-weight: 700;
        line-height: 1.55;
    }

    .impersonate-link {
        display: flex;
        width: 100%;
        min-height: 52px;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 13px 18px;
        border-radius: 15px;
        background: linear-gradient(135deg, #0f172a, #2563eb);
        color: #ffffff !important;
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 950;
        text-align: center;
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.24);
        margin-bottom: 10px;
    }

    .impersonate-link:hover {
        filter: brightness(1.05);
        transform: translateY(-1px);
    }

    .impersonate-note {
        background: #eff6ff;
        color: #1e40af;
        border: 1px solid #bfdbfe;
        border-radius: 14px;
        padding: 11px 13px;
        font-size: 12px;
        font-weight: 750;
        line-height: 1.45;
        margin-bottom: 14px;
    }

    @media (max-width: 768px) {
        .dealer-hero {
            padding: 22px;
            border-radius: 22px;
            margin-bottom: 18px;
        }

        .dealer-hero h1 {
            font-size: 27px;
            line-height: 1.15;
        }

        .dealer-hero p {
            font-size: 13px;
            line-height: 1.45;
        }

        .dealer-card {
            padding: 16px;
            border-radius: 20px;
        }

        .dealer-section-title {
            font-size: 18px;
        }

        [data-testid="stCheckbox"] label {
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            font-size: 17px !important;
        }

        [data-testid="stCheckbox"] p {
            font-size: 18px !important;
            font-weight: 700 !important;
        }

        button {
            min-height: 48px !important;
            border-radius: 14px !important;
            font-weight: 900 !important;
        }

        .impersonate-link {
            min-height: 54px;
            font-size: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def render_flash_messages():
    if "dealer_flash_success" in st.session_state and st.session_state.dealer_flash_success:
        msg = st.session_state.dealer_flash_success
        st.success(msg)

        try:
            st.toast(msg, icon="✅")
        except Exception:
            pass

        st.session_state.dealer_flash_success = ""

    if "dealer_flash_error" in st.session_state and st.session_state.dealer_flash_error:
        msg = st.session_state.dealer_flash_error
        st.error(msg)

        try:
            st.toast(msg, icon="❌")
        except Exception:
            pass

        st.session_state.dealer_flash_error = ""


# =====================================================================
# ANA SAYFA
# =====================================================================
def show_dealer_management():
    ensure_users_table()
    ensure_factory_tables()
    inject_css()

    if st.session_state.get("user_role") != "admin":
        st.error("Bu sayfaya yalnızca sistem yöneticisi erişebilir.")
        return

    render_flash_messages()

    st.markdown("""
    <div class="dealer-hero">
        <h1>🏢 Bayi Yönetimi</h1>
        <p>Bayi ve üretici bilgilerini, menü izinlerini, kategori yetkilerini ve yönetici girişlerini yönetin.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="dealer-version">
        ✅ Güncel dealer_management.py çalışıyor. Bu sürümde “Bu Bayi / Üretici Olarak Sisteme Gir” butonu vardır.
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["👥 Bayi / Üretici Listesi", "➕ Yeni Kayıt"])

    # =================================================================
    # BAYİ / ÜRETİCİ LİSTESİ
    # =================================================================
    with tabs[0]:
        filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])

        with filter_col1:
            search_text = st.text_input(
                "🔎 Ara",
                placeholder="Firma adı, e-posta veya telefon ara...",
                key="dealer_search_text"
            )

        with filter_col2:
            status_filter = st.selectbox(
                "Durum",
                ["Tümü", "Aktif", "Onay Bekliyor", "Askıda"],
                key="dealer_status_filter"
            )

        with filter_col3:
            type_filter = st.selectbox(
                "Tür",
                ["Tümü", "Satıcı", "Üretici"],
                key="dealer_type_filter"
            )

        users = get_users(search_text, status_filter, type_filter)

        if not users:
            st.info("Kayıtlı bayi veya üretici bulunamadı.")
            return

        user_options = {}

        for u in users:
            user_id = u[0]
            company = u[1] or "İsimsiz Firma"
            email = u[2] or "E-posta yok"
            user_type = u[4] or "Satıcı"
            approved = u[6]
            label = f"{company} | {email} | {user_type} | {status_plain(approved)}"
            user_options[label] = user_id

        if "selected_dealer_id" not in st.session_state:
            st.session_state.selected_dealer_id = users[0][0]

        available_ids = [u[0] for u in users]

        if st.session_state.selected_dealer_id not in available_ids:
            st.session_state.selected_dealer_id = users[0][0]

        current_label = None

        for label, user_id in user_options.items():
            if user_id == st.session_state.selected_dealer_id:
                current_label = label
                break

        if current_label is None:
            current_label = list(user_options.keys())[0]

        selected_label = st.selectbox(
            "Düzenlenecek bayi / üretici",
            list(user_options.keys()),
            index=list(user_options.keys()).index(current_label),
            key="dealer_select_box"
        )

        selected_user_id = user_options[selected_label]

        if selected_user_id != st.session_state.selected_dealer_id:
            st.session_state.selected_dealer_id = selected_user_id
            st.rerun()

        selected_user = get_user_by_id(st.session_state.selected_dealer_id)

        if not selected_user:
            st.error("Seçili kayıt bulunamadı.")
            return

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
        ) = selected_user

        status_css = "dealer-status-active"

        if int(is_approved or 0) == 0:
            status_css = "dealer-status-wait"
        elif int(is_approved or 0) == -1:
            status_css = "dealer-status-suspended"

        st.markdown(f"""
        <div class="dealer-user-box">
            <div class="dealer-user-name">{html.escape(company_name or "İsimsiz Firma")}</div>
            <div class="dealer-user-meta">{html.escape(email or "")}</div>
            <div class="dealer-user-meta">{html.escape(phone or "")}</div>
            <div class="{status_css}">{status_text(is_approved)}</div>
        </div>
        """, unsafe_allow_html=True)

        edit_col, action_col = st.columns([2, 1], gap="large")

        # =============================================================
        # SOL TARAF: BİLGİ DÜZENLEME
        # =============================================================
        with edit_col:
            st.markdown("""
            <div class="dealer-card">
                <div class="dealer-section-title">📌 Bayi / Üretici Bilgileri</div>
                <div class="dealer-small-text">Buradaki bilgiler güncellendiğinde veritabanına kaydedilir ve ekran yenilenir.</div>
            </div>
            """, unsafe_allow_html=True)

            company_name_input = st.text_input(
                "Firma Adı",
                value=company_name or "",
                key=f"company_name_{user_id}"
            )

            email_input = st.text_input(
                "E-posta",
                value=email or "",
                key=f"email_{user_id}"
            )

            phone_input = st.text_input(
                "Telefon",
                value=phone or "",
                key=f"phone_{user_id}"
            )

            type_values = ["Satıcı", "Üretici"]
            current_type = "Üretici" if str(user_type).strip() == "Üretici" else "Satıcı"

            user_type_input = st.selectbox(
                "Kullanıcı Türü",
                type_values,
                index=type_values.index(current_type),
                key=f"user_type_{user_id}"
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
                key=f"status_{user_id}"
            )

            is_verified_input = st.checkbox(
                "E-posta doğrulanmış kabul edilsin",
                value=bool(is_verified),
                key=f"verified_{user_id}"
            )

            website_input = st.text_input(
                "Web Sitesi",
                value=website or "",
                placeholder="https://www.firma.com",
                key=f"website_{user_id}"
            )

            address_input = st.text_area(
                "Adres",
                value=address_full or "",
                height=110,
                key=f"address_{user_id}"
            )

            logo_path_input = st.text_input(
                "Logo Dosya Yolu",
                value=logo_path or "",
                placeholder="images/logo.png",
                key=f"logo_path_{user_id}"
            )

            logo_preview = get_base64_image(logo_path_input)

            if logo_preview and logo_preview.startswith("data:image"):
                st.image(logo_preview, caption="Logo Önizleme", width=220)

            st.markdown("""
            <div class="dealer-preview">
                <div class="dealer-preview-title">Anlık Bilgi Önizleme</div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="dealer-preview-line"><b>Firma:</b> {html.escape(company_name_input or "-")}</div>
                <div class="dealer-preview-line"><b>E-posta:</b> {html.escape(email_input or "-")}</div>
                <div class="dealer-preview-line"><b>Telefon:</b> {html.escape(phone_input or "-")}</div>
                <div class="dealer-preview-line"><b>Tür:</b> {html.escape(user_type_input)}</div>
                <div class="dealer-preview-line"><b>Durum:</b> {html.escape(status_input)}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 🔑 Menü İzinleri")

            current_menu_labels = labels_from_allowed_menus(allowed_menus)
            selected_menu_labels = []

            menu_cols = st.columns(2)

            for i, (code, label) in enumerate(MENU_OPTIONS):
                with menu_cols[i % 2]:
                    checked = label in current_menu_labels

                    if st.checkbox(label, value=checked, key=f"menu_{user_id}_{code}"):
                        selected_menu_labels.append(label)

            if not selected_menu_labels:
                st.warning("En az bir menü izni seçilmelidir.")

            st.markdown("### 🗂️ Kategori İzinleri")

            all_categories = get_all_categories()
            selected_categories = []

            if all_categories:
                current_categories = categories_from_allowed(allowed_categories, all_categories)

                cat_all = st.checkbox(
                    "Tüm kategorilere izin ver",
                    value=(not allowed_categories or len(current_categories) == len(all_categories)),
                    key=f"all_categories_{user_id}"
                )

                if cat_all:
                    selected_categories = all_categories
                    st.info("Bu kullanıcı tüm ürün kategorilerini görebilir.")
                else:
                    cat_cols = st.columns(2)

                    for i, cat in enumerate(all_categories):
                        with cat_cols[i % 2]:
                            checked = cat in current_categories

                            if st.checkbox(cat, value=checked, key=f"cat_{user_id}_{cat}"):
                                selected_categories.append(cat)
            else:
                st.info("Sistemde kategori bulunmadığı için kategori izni seçilemiyor.")

            save_clicked = st.button(
                "💾 BİLGİLERİ GÜNCELLE",
                type="primary",
                use_container_width=True,
                key=f"save_dealer_{user_id}"
            )

            if save_clicked:
                if not company_name_input.strip():
                    st.session_state.dealer_flash_error = "Firma adı boş bırakılamaz."
                    st.rerun()

                if not email_input.strip():
                    st.session_state.dealer_flash_error = "E-posta boş bırakılamaz."
                    st.rerun()

                if not selected_menu_labels:
                    st.session_state.dealer_flash_error = "En az bir menü izni seçmelisiniz."
                    st.rerun()

                new_role = "manufacturer" if user_type_input == "Üretici" else "dealer"

                if status_input == "Aktif":
                    new_status = 1
                elif status_input == "Askıda":
                    new_status = -1
                else:
                    new_status = 0

                new_allowed_menus = normalize_allowed_menus(selected_menu_labels)
                new_allowed_categories = ",".join(selected_categories) if selected_categories else ""

                ok, msg = update_user_info(
                    user_id=user_id,
                    company_name=company_name_input.strip(),
                    email=email_input.strip().lower(),
                    phone=phone_input.strip(),
                    user_type=user_type_input,
                    role=new_role,
                    is_approved=new_status,
                    is_verified=1 if is_verified_input else 0,
                    website=website_input.strip(),
                    address_full=address_input.strip(),
                    allowed_menus=new_allowed_menus,
                    allowed_categories=new_allowed_categories,
                    logo_path=logo_path_input.strip(),
                )

                if ok:
                    st.session_state.selected_dealer_id = user_id
                    refresh_admin_login_token(user_id)
                    st.session_state.dealer_flash_success = "✅ Bilgiler güncellendi ve kayıt ekranda yenilendi."
                else:
                    st.session_state.dealer_flash_error = msg

                st.rerun()

        # =============================================================
        # SAĞ TARAF: HIZLI İŞLEMLER
        # =============================================================
        with action_col:
            st.markdown("""
            <div class="dealer-card">
                <div class="dealer-section-title">⚙️ Hızlı İşlemler</div>
                <div class="dealer-small-text">Hesabı onaylayabilir, askıya alabilir, silebilir veya bu hesapla sisteme giriş yapabilirsiniz.</div>
            </div>
            """, unsafe_allow_html=True)

            if int(is_approved or 0) == 1:
                st.success("Bu hesap aktif.")
            elif int(is_approved or 0) == -1:
                st.error("Bu hesap askıda.")
            else:
                st.warning("Bu hesap onay bekliyor.")

            st.markdown("#### 🔑 Hesaba Gir")

            admin_login_url = get_or_create_admin_login_url(user_id)

            if admin_login_url:
                login_label = "Bu Üretici Olarak Sisteme Gir" if str(user_type).strip() == "Üretici" else "Bu Bayi Olarak Sisteme Gir"

                st.markdown(f"""
                <a
                    class="impersonate-link"
                    href="{html.escape(admin_login_url)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    🔑 {html.escape(login_label)}
                </a>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div class="impersonate-note">
                    Bu buton yeni sekme açar. Açılan sekmede seçili bayi / üretici hesabıyla otomatik giriş yapılır.
                    Mevcut yönetici ekranınız kapanmaz.
                </div>
                """, unsafe_allow_html=True)

                if st.button("🔄 Giriş Linkini Yenile", use_container_width=True, key=f"refresh_admin_login_{user_id}"):
                    refresh_admin_login_token(user_id)
                    st.session_state.dealer_flash_success = "🔄 Yeni giriş linki oluşturuldu."
                    st.rerun()
            else:
                st.error("Bu kullanıcı için giriş linki oluşturulamadı.")

            st.markdown("---")

            if st.button("✅ Aktif Et / Onayla", use_container_width=True, key=f"activate_{user_id}"):
                activate_user(user_id)
                refresh_admin_login_token(user_id)
                st.session_state.dealer_flash_success = "✅ Hesap aktif edildi."
                st.rerun()

            if st.button("🚫 Askıya Al", use_container_width=True, key=f"suspend_{user_id}"):
                suspend_user(user_id)
                st.session_state.dealer_flash_success = "🚫 Hesap askıya alındı."
                st.rerun()

            st.markdown("---")

            st.markdown("#### 🔐 Şifre Değiştir")

            new_password = st.text_input(
                "Yeni Şifre",
                type="password",
                key=f"password_{user_id}",
                placeholder="Yeni şifre girin"
            )

            if st.button("🔐 ŞİFREYİ GÜNCELLE", use_container_width=True, key=f"change_password_{user_id}"):
                if len(new_password.strip()) < 4:
                    st.session_state.dealer_flash_error = "Şifre en az 4 karakter olmalıdır."
                else:
                    change_user_password(user_id, new_password.strip())
                    refresh_admin_login_token(user_id)
                    st.session_state.dealer_flash_success = "🔐 Şifre başarıyla güncellendi."

                st.rerun()

            st.markdown("---")

            confirm_delete = st.checkbox(
                "Bu kaydı silmek istediğimi onaylıyorum",
                key=f"confirm_delete_{user_id}"
            )

            if st.button("🗑️ Sil", use_container_width=True, key=f"delete_{user_id}"):
                if confirm_delete:
                    delete_user(user_id)
                    st.session_state.selected_dealer_id = None
                    st.session_state.dealer_flash_success = "🗑️ Kayıt silindi."
                    st.rerun()
                else:
                    st.session_state.dealer_flash_error = "Silmek için önce onay kutusunu işaretleyin."
                    st.rerun()

        # =============================================================
        # TABLO ÖZETİ
        # =============================================================
        st.markdown("---")
        st.markdown("### 📋 Kayıt Özeti")

        refreshed_users = get_users(search_text, status_filter, type_filter)

        table_rows = []

        for u in refreshed_users:
            table_rows.append({
                "ID": u[0],
                "Firma": u[1] or "",
                "E-posta": u[2] or "",
                "Telefon": u[3] or "",
                "Tür": u[4] or "",
                "Durum": status_plain(u[6]),
                "Web": u[8] or "",
            })

        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # =================================================================
    # YENİ KAYIT
    # =================================================================
    with tabs[1]:
        st.markdown("""
        <div class="dealer-card">
            <div class="dealer-section-title">➕ Yeni Bayi / Üretici Oluştur</div>
            <div class="dealer-small-text">Yeni kayıt aktif ve doğrulanmış olarak oluşturulur.</div>
        </div>
        """, unsafe_allow_html=True)

        new_col1, new_col2 = st.columns(2)

        with new_col1:
            new_company = st.text_input("Firma Adı *", key="new_dealer_company")
            new_email = st.text_input("E-posta *", key="new_dealer_email")
            new_phone = st.text_input("Telefon", key="new_dealer_phone")

        with new_col2:
            new_type = st.selectbox("Kullanıcı Türü", ["Satıcı", "Üretici"], key="new_dealer_type")
            new_password = st.text_input("Geçici Şifre *", type="password", key="new_dealer_password")
            new_password_again = st.text_input("Geçici Şifre Tekrar *", type="password", key="new_dealer_password_again")

        if st.button("➕ YENİ KAYIT OLUŞTUR", type="primary", use_container_width=True):
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

            ok, msg = create_user(
                company_name=new_company.strip(),
                email=new_email.strip().lower(),
                phone=new_phone.strip(),
                password=new_password.strip(),
                user_type=new_type
            )

            if ok:
                st.session_state.dealer_flash_success = "✅ Yeni kayıt oluşturuldu."
            else:
                st.session_state.dealer_flash_error = msg

            st.rerun()