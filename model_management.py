import streamlit as st
import sqlite3
import os
import base64
import uuid
from PIL import Image

FACTORY_DB = "factory_data.db"


def inject_responsive_css():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    .mobile-card-title { font-size:16px; font-weight:900; color:#0f172a; margin-bottom:6px; }
    .mobile-card-sub { font-size:12px; color:#64748b; margin-bottom:10px; }
    .product-card { border:1px solid #e2e8f0; background:#fff; border-radius:16px; padding:14px; margin-bottom:12px; box-shadow:0 2px 6px rgba(15,23,42,.04); }
    .product-price { color:#ea580c; font-size:17px; font-weight:900; }
    .cost-price { color:#16a34a; font-size:13px; font-weight:800; margin-top:4px; }
    .soft-info-box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:14px; margin-bottom:14px; }
    .cost-box { background:#fff7ed; border:1px solid #fed7aa; border-radius:14px; padding:14px; margin-bottom:14px; }

    @media (max-width:768px) {
        .block-container { padding-left:10px!important; padding-right:10px!important; padding-top:10px!important; }
        h1,h2,h3 { font-size:22px!important; line-height:1.25!important; }
        .stTabs [data-baseweb="tab-list"] { overflow-x:auto!important; white-space:nowrap!important; gap:6px!important; padding-bottom:8px!important; border-bottom:1px solid #e2e8f0!important; }
        .stTabs [data-baseweb="tab"] { min-width:max-content!important; padding:10px 14px!important; font-size:14px!important; border-radius:12px!important; background:#f8fafc!important; border:1px solid #e2e8f0!important; }
        .stTabs [aria-selected="true"] { background:#2563eb!important; color:white!important; border-color:#2563eb!important; }
        div[data-testid="column"] { width:100%!important; flex:1 1 100%!important; min-width:100%!important; }
        input,textarea { font-size:16px!important; }
        button { min-height:46px!important; border-radius:13px!important; font-weight:800!important; }
        div[data-testid="stNumberInput"], div[data-testid="stSelectbox"], div[data-testid="stFileUploader"] { width:100%!important; }
        section[data-testid="stSidebar"] { width:86vw!important; }
        .product-card { padding:12px!important; border-radius:14px!important; }
        .desktop-only { display:none!important; }
    }
    </style>
    """, unsafe_allow_html=True)


def get_connection():
    conn = sqlite3.connect(FACTORY_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def db_query(query, params=()):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Veritabanı okuma hatası: {e}")
        return []


def exec_factory(query, params=()):
    try:
        with sqlite3.connect(FACTORY_DB, check_same_thread=False) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Veritabanı işlem hatası: {e}")
        return False


def ensure_column(table_name, column_name, column_type):
    try:
        with sqlite3.connect(FACTORY_DB, check_same_thread=False) as conn:
            cur = conn.cursor()
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table_name})").fetchall()]
            if column_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                conn.commit()
    except Exception as e:
        st.error(f"Kolon onarım hatası ({table_name}.{column_name}): {e}")


def ensure_database_schema():
    with sqlite3.connect(FACTORY_DB, check_same_thread=False) as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                image_path TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                base_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0,
                image_path TEXT DEFAULT '',
                specs TEXT DEFAULT '',
                currency TEXT DEFAULT 'USD',
                port_discount REAL DEFAULT 0.0,
                compatible_options TEXT DEFAULT '',
                gallery_images TEXT DEFAULT '',
                category TEXT DEFAULT 'Diğer Makinalar',
                gallery_videos TEXT DEFAULT '',
                name_zh TEXT DEFAULT '',
                specs_zh TEXT DEFAULT '',
                user_id INTEGER DEFAULT 1,
                purchase_price REAL DEFAULT 0.0,
                shipping_cost REAL DEFAULT 0.0,
                customs_tax_rate REAL DEFAULT 3.0,
                extra_tax_rate REAL DEFAULT 10.0,
                port_cost REAL DEFAULT 0.0,
                document_cost REAL DEFAULT 0.0,
                installation_cost REAL DEFAULT 0.0,
                other_cost REAL DEFAULT 0.0,
                cost_note TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opt_name TEXT,
                opt_desc TEXT DEFAULT '',
                opt_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0,
                opt_image TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                allow_qty INTEGER DEFAULT 1,
                opt_name_zh TEXT DEFAULT '',
                opt_desc_zh TEXT DEFAULT '',
                opt_suffix TEXT DEFAULT '',
                opt_variant_image TEXT DEFAULT '',
                user_id INTEGER DEFAULT 1,
                purchase_price REAL DEFAULT 0.0,
                shipping_cost REAL DEFAULT 0.0,
                customs_tax_rate REAL DEFAULT 3.0,
                extra_tax_rate REAL DEFAULT 10.0,
                port_cost REAL DEFAULT 0.0,
                document_cost REAL DEFAULT 0.0,
                installation_cost REAL DEFAULT 0.0,
                other_cost REAL DEFAULT 0.0,
                cost_note TEXT DEFAULT ''
            )
        """)

        conn.commit()

    model_cols = [
        ("name", "TEXT DEFAULT ''"),
        ("base_price", "REAL DEFAULT 0.0"),
        ("sale_price", "REAL DEFAULT 0.0"),
        ("image_path", "TEXT DEFAULT ''"),
        ("specs", "TEXT DEFAULT ''"),
        ("currency", "TEXT DEFAULT 'USD'"),
        ("port_discount", "REAL DEFAULT 0.0"),
        ("compatible_options", "TEXT DEFAULT ''"),
        ("gallery_images", "TEXT DEFAULT ''"),
        ("category", "TEXT DEFAULT 'Diğer Makinalar'"),
        ("gallery_videos", "TEXT DEFAULT ''"),
        ("name_zh", "TEXT DEFAULT ''"),
        ("specs_zh", "TEXT DEFAULT ''"),
        ("user_id", "INTEGER DEFAULT 1"),
        ("purchase_price", "REAL DEFAULT 0.0"),
        ("shipping_cost", "REAL DEFAULT 0.0"),
        ("customs_tax_rate", "REAL DEFAULT 3.0"),
        ("extra_tax_rate", "REAL DEFAULT 10.0"),
        ("port_cost", "REAL DEFAULT 0.0"),
        ("document_cost", "REAL DEFAULT 0.0"),
        ("installation_cost", "REAL DEFAULT 0.0"),
        ("other_cost", "REAL DEFAULT 0.0"),
        ("cost_note", "TEXT DEFAULT ''"),
    ]

    option_cols = [
        ("opt_name", "TEXT DEFAULT ''"),
        ("opt_desc", "TEXT DEFAULT ''"),
        ("opt_price", "REAL DEFAULT 0.0"),
        ("sale_price", "REAL DEFAULT 0.0"),
        ("opt_image", "TEXT DEFAULT ''"),
        ("sort_order", "INTEGER DEFAULT 0"),
        ("allow_qty", "INTEGER DEFAULT 1"),
        ("opt_name_zh", "TEXT DEFAULT ''"),
        ("opt_desc_zh", "TEXT DEFAULT ''"),
        ("opt_suffix", "TEXT DEFAULT ''"),
        ("opt_variant_image", "TEXT DEFAULT ''"),
        ("user_id", "INTEGER DEFAULT 1"),
        ("purchase_price", "REAL DEFAULT 0.0"),
        ("shipping_cost", "REAL DEFAULT 0.0"),
        ("customs_tax_rate", "REAL DEFAULT 3.0"),
        ("extra_tax_rate", "REAL DEFAULT 10.0"),
        ("port_cost", "REAL DEFAULT 0.0"),
        ("document_cost", "REAL DEFAULT 0.0"),
        ("installation_cost", "REAL DEFAULT 0.0"),
        ("other_cost", "REAL DEFAULT 0.0"),
        ("cost_note", "TEXT DEFAULT ''"),
    ]

    for col, typ in model_cols:
        ensure_column("models", col, typ)

    for col, typ in option_cols:
        ensure_column("options", col, typ)

    for col, typ in [("name", "TEXT DEFAULT ''"), ("image_path", "TEXT DEFAULT ''")]:
        ensure_column("categories", col, typ)


def safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value if value is not None else default)
    except Exception:
        return default


def get_safe(row, key, default=""):
    if row and key in row and row[key] is not None:
        return row[key]
    return default


def can_view_costs():
    return st.session_state.get("user_role") == "admin"


def calculate_import_cost(purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate, port_cost, document_cost, installation_cost, other_cost):
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

    return {
        "ara_1": ara_1,
        "gumruk": gumruk,
        "ara_2": ara_2,
        "ek_vergi": ek_vergi,
        "ara_3": ara_3,
        "toplam": toplam,
    }


def ensure_images_folder():
    if not os.path.exists("images"):
        os.makedirs("images")


def get_image_base64(img_path):
    if not img_path:
        return ""

    img_path = str(img_path).strip()
    possible_paths = [
        img_path,
        os.path.join("images", img_path),
        os.path.basename(img_path),
        os.path.join("images", os.path.basename(img_path)),
    ]

    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()

                ext = os.path.splitext(path)[1].lower().replace(".", "")
                if not ext:
                    ext = "png"
                if ext == "jpg":
                    ext = "jpeg"

                return f"data:image/{ext};base64,{b64}"
            except Exception:
                return ""

    return ""


def process_image(uploaded_file, prefix="img", size=(1200, 1200), square=False):
    if uploaded_file is None:
        return ""

    ensure_images_folder()

    try:
        img = Image.open(uploaded_file)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if square:
            width, height = img.size
            crop_size = min(width, height)
            left = int((width - crop_size) / 2)
            top = int((height - crop_size) / 2)
            img = img.crop((left, top, left + crop_size, top + crop_size))
            img = img.resize(size, Image.Resampling.LANCZOS)
        else:
            img.thumbnail(size, Image.Resampling.LANCZOS)

        filename = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
        filepath = os.path.join("images", filename)
        img.save(filepath, "JPEG", quality=92)
        return filename

    except Exception as e:
        st.error(f"Görsel işleme hatası: {e}")
        return ""


def parse_specs(specs_text):
    result = []

    if not specs_text:
        return result

    for item in str(specs_text).split("||"):
        item = item.strip()
        if not item:
            continue

        parts = item.split("|")
        title = parts[0].strip() if len(parts) > 0 else ""
        detail = parts[1].strip() if len(parts) > 1 else ""
        img = parts[2].strip() if len(parts) > 2 else ""

        result.append({"title": title, "detail": detail, "img": img})

    return result


def build_specs(spec_list):
    rows = []

    for item in spec_list:
        title = str(item.get("title", "")).strip()
        detail = str(item.get("detail", "")).strip()
        img = str(item.get("img", "")).strip()

        if title or detail or img:
            rows.append(f"{title}|{detail}|{img}")

    return " || ".join(rows)


def get_category_list():
    cats = db_query("SELECT name FROM categories ORDER BY name ASC")
    result = [c["name"] for c in cats if c.get("name")]

    if "Diğer Makinalar" not in result:
        result.append("Diğer Makinalar")

    return result


def show_product_management():
    inject_responsive_css()
    ensure_database_schema()

    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "list"

    if st.session_state.view_mode == "list":
        show_list_view()
    elif st.session_state.view_mode == "model_add":
        show_model_form(mode="add")
    elif st.session_state.view_mode == "model_edit":
        show_model_form(mode="edit", model_id=st.session_state.get("edit_model_id"))
    elif st.session_state.view_mode == "option_add":
        show_option_form(mode="add")
    elif st.session_state.view_mode == "option_edit":
        show_option_form(mode="edit", option_id=st.session_state.get("edit_option_id"))
    else:
        st.session_state.view_mode = "list"
        st.rerun()


def show_list_view():
    st.header("📦 Fabrika Veritabanı Yönetimi")
    st.markdown(
        "<div class='soft-info-box'>Makine, donanım, satış fiyatı ve maliyet bilgilerini buradan yönetebilirsiniz.</div>",
        unsafe_allow_html=True,
    )

    tab_models, tab_options, tab_categories = st.tabs([
        "📦 Modeller",
        "⚙️ Donanımlar",
        "📂 Kategoriler",
    ])

    with tab_models:
        show_models_list()

    with tab_options:
        show_options_list()

    with tab_categories:
        show_categories_list()


def show_models_list():
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    col1.subheader("Kayıtlı Makineler")

    if col2.button("➕ Yeni Makine", type="primary", use_container_width=True):
        st.session_state.view_mode = "model_add"
        st.rerun()

    search = st.text_input("🔍 Makine ara", placeholder="Makine adı veya kategori yazın...")
    models = db_query("SELECT * FROM models ORDER BY id DESC")

    if search:
        s = search.lower()
        models = [
            m for m in models
            if s in str(m.get("name", "")).lower()
            or s in str(m.get("category", "")).lower()
        ]

    if not models:
        st.info("Henüz kayıtlı makine bulunmuyor.")
        return

    grouped = {}
    for model in models:
        cat = model.get("category") or "Diğer Makinalar"
        grouped.setdefault(cat, []).append(model)

    for cat_name, cat_models in grouped.items():
        with st.expander(f"📁 {cat_name} ({len(cat_models)})", expanded=True):
            for i in range(0, len(cat_models), 4):
                cols = st.columns(4)

                for j in range(4):
                    if i + j >= len(cat_models):
                        continue

                    model = cat_models[i + j]
                    model_id = safe_int(model.get("id"))

                    with cols[j]:
                        st.markdown("<div class='product-card'>", unsafe_allow_html=True)

                        img_b64 = get_image_base64(model.get("image_path"))
                        if img_b64:
                            st.markdown(
                                f"""
                                <div style="text-align:center;">
                                    <img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:10px; border-radius:12px;">
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                """
                                <div style="height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:12px; color:#94a3b8; margin-bottom:10px;">
                                    Görsel Yok
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        display_price = safe_float(model.get("sale_price")) or safe_float(model.get("base_price"))

                        st.markdown(
                            f"""
                            <div class="mobile-card-title">{model.get("name", "İsimsiz Makine")}</div>
                            <div class="mobile-card-sub">ID: {model_id} · {model.get("category", "Diğer Makinalar")}</div>
                            <div class="product-price">{display_price:,.2f} {model.get("currency", "USD")}</div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if can_view_costs():
                            cost = calculate_import_cost(
                                model.get("purchase_price"),
                                model.get("shipping_cost"),
                                model.get("customs_tax_rate"),
                                model.get("extra_tax_rate"),
                                model.get("port_cost"),
                                model.get("document_cost"),
                                model.get("installation_cost"),
                                model.get("other_cost"),
                            )
                            profit = display_price - cost["toplam"]
                            st.markdown(
                                f"<div class='cost-price'>Maliyet: {cost['toplam']:,.2f} $ · Kâr: {profit:,.2f} $</div>",
                                unsafe_allow_html=True,
                            )

                        b1, b2, b3 = st.columns(3)

                        if b1.button("✏️", key=f"edit_model_{model_id}", help="Düzenle", use_container_width=True):
                            st.session_state.edit_model_id = model_id
                            st.session_state.view_mode = "model_edit"
                            st.rerun()

                        if b2.button("📄", key=f"copy_model_{model_id}", help="Kopyala", use_container_width=True):
                            copy_model(model_id)
                            st.rerun()

                        if b3.button("🗑️", key=f"delete_model_{model_id}", help="Sil", use_container_width=True):
                            exec_factory("DELETE FROM models WHERE id=?", (model_id,))
                            st.success("Makine silindi.")
                            st.rerun()

                        st.markdown("</div>", unsafe_allow_html=True)


def show_options_list():
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    col1.subheader("Ekstra Donanımlar")

    if col2.button("➕ Yeni Donanım", type="primary", use_container_width=True):
        st.session_state.view_mode = "option_add"
        st.rerun()

    search = st.text_input("🔍 Donanım ara", placeholder="Donanım adı yazın...")
    options = db_query("SELECT * FROM options ORDER BY id DESC")

    if search:
        s = search.lower()
        options = [
            o for o in options
            if s in str(o.get("opt_name", "")).lower()
            or s in str(o.get("opt_desc", "")).lower()
        ]

    if not options:
        st.info("Henüz kayıtlı donanım bulunmuyor.")
        return

    for i in range(0, len(options), 4):
        cols = st.columns(4)

        for j in range(4):
            if i + j >= len(options):
                continue

            opt = options[i + j]
            opt_id = safe_int(opt.get("id"))

            with cols[j]:
                st.markdown("<div class='product-card'>", unsafe_allow_html=True)

                img_b64 = get_image_base64(opt.get("opt_image"))
                if img_b64:
                    st.markdown(
                        f"""
                        <div style="text-align:center;">
                            <img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px; border-radius:12px;">
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """
                        <div style="height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:12px; color:#94a3b8; margin-bottom:10px;">
                            Görsel Yok
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                display_price = safe_float(opt.get("sale_price")) or safe_float(opt.get("opt_price"))

                st.markdown(
                    f"""
                    <div class="mobile-card-title">{opt.get("opt_name", "İsimsiz Donanım")}</div>
                    <div class="mobile-card-sub">ID: {opt_id}</div>
                    <div class="product-price">+{display_price:,.2f} USD</div>
                    """,
                    unsafe_allow_html=True,
                )

                if can_view_costs():
                    cost = calculate_import_cost(
                        opt.get("purchase_price"),
                        opt.get("shipping_cost"),
                        opt.get("customs_tax_rate"),
                        opt.get("extra_tax_rate"),
                        opt.get("port_cost"),
                        opt.get("document_cost"),
                        opt.get("installation_cost"),
                        opt.get("other_cost"),
                    )
                    profit = display_price - cost["toplam"]
                    st.markdown(
                        f"<div class='cost-price'>Maliyet: {cost['toplam']:,.2f} $ · Kâr: {profit:,.2f} $</div>",
                        unsafe_allow_html=True,
                    )

                if opt.get("opt_suffix") or opt.get("opt_variant_image"):
                    st.caption("✨ Varyasyon bilgisi var")

                b1, b2, b3 = st.columns(3)

                if b1.button("✏️", key=f"edit_option_{opt_id}", help="Düzenle", use_container_width=True):
                    st.session_state.edit_option_id = opt_id
                    st.session_state.view_mode = "option_edit"
                    st.rerun()

                if b2.button("📄", key=f"copy_option_{opt_id}", help="Kopyala", use_container_width=True):
                    copy_option(opt_id)
                    st.rerun()

                if b3.button("🗑️", key=f"delete_option_{opt_id}", help="Sil", use_container_width=True):
                    exec_factory("DELETE FROM options WHERE id=?", (opt_id,))
                    st.success("Donanım silindi.")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)


def show_categories_list():
    st.subheader("Kategori Yönetimi")

    with st.container(border=True):
        new_cat = st.text_input("Yeni kategori adı", placeholder="Örn: CNC İşleme Merkezleri")

        if st.button("➕ Kategori Ekle", type="primary", use_container_width=True):
            if not new_cat.strip():
                st.warning("Kategori adı boş bırakılamaz.")
            else:
                ok = exec_factory(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                    (new_cat.strip(),),
                )
                if ok:
                    st.success("Kategori eklendi.")
                    st.rerun()

    cats = db_query("SELECT * FROM categories ORDER BY name ASC")

    if not cats:
        st.info("Henüz kategori yok.")
        return

    for cat in cats:
        cat_id = safe_int(cat.get("id"))
        cat_name = cat.get("name", "")

        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"📁 **{cat_name}**")

        if c2.button("🗑️", key=f"delete_cat_{cat_id}", use_container_width=True):
            exec_factory("DELETE FROM categories WHERE id=?", (cat_id,))
            st.success("Kategori silindi.")
            st.rerun()


def copy_model(model_id):
    rows = db_query("SELECT * FROM models WHERE id=?", (model_id,))

    if not rows:
        st.error(f"Kopyalanacak makine bulunamadı. ID: {model_id}")
        return False

    m = rows[0]

    ok = exec_factory(
        """
        INSERT INTO models (
            name, base_price, sale_price, purchase_price, shipping_cost, customs_tax_rate,
            extra_tax_rate, port_cost, document_cost, installation_cost, other_cost, cost_note,
            image_path, specs, currency, port_discount, compatible_options, gallery_images,
            category, gallery_videos, name_zh, specs_zh, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{get_safe(m, 'name', 'Makine')} (Kopya)",
            safe_float(m.get("base_price")),
            safe_float(m.get("sale_price")),
            safe_float(m.get("purchase_price")),
            safe_float(m.get("shipping_cost")),
            safe_float(m.get("customs_tax_rate"), 3),
            safe_float(m.get("extra_tax_rate"), 10),
            safe_float(m.get("port_cost")),
            safe_float(m.get("document_cost")),
            safe_float(m.get("installation_cost")),
            safe_float(m.get("other_cost")),
            get_safe(m, "cost_note"),
            get_safe(m, "image_path"),
            get_safe(m, "specs"),
            get_safe(m, "currency", "USD"),
            safe_float(m.get("port_discount")),
            get_safe(m, "compatible_options"),
            get_safe(m, "gallery_images"),
            get_safe(m, "category", "Diğer Makinalar"),
            get_safe(m, "gallery_videos"),
            get_safe(m, "name_zh"),
            get_safe(m, "specs_zh"),
            st.session_state.get("user_id", 1),
        ),
    )

    if ok:
        st.success("Makine kopyalandı.")

    return ok


def copy_option(option_id):
    rows = db_query("SELECT * FROM options WHERE id=?", (option_id,))

    if not rows:
        st.error(f"Kopyalanacak donanım bulunamadı. ID: {option_id}")
        return False

    o = rows[0]

    ok = exec_factory(
        """
        INSERT INTO options (
            opt_name, opt_desc, opt_price, sale_price, purchase_price, shipping_cost,
            customs_tax_rate, extra_tax_rate, port_cost, document_cost, installation_cost,
            other_cost, cost_note, opt_image, sort_order, allow_qty, opt_name_zh,
            opt_desc_zh, opt_suffix, opt_variant_image, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{get_safe(o, 'opt_name', 'Donanım')} (Kopya)",
            get_safe(o, "opt_desc"),
            safe_float(o.get("opt_price")),
            safe_float(o.get("sale_price")),
            safe_float(o.get("purchase_price")),
            safe_float(o.get("shipping_cost")),
            safe_float(o.get("customs_tax_rate"), 3),
            safe_float(o.get("extra_tax_rate"), 10),
            safe_float(o.get("port_cost")),
            safe_float(o.get("document_cost")),
            safe_float(o.get("installation_cost")),
            safe_float(o.get("other_cost")),
            get_safe(o, "cost_note"),
            get_safe(o, "opt_image"),
            safe_int(o.get("sort_order")),
            safe_int(o.get("allow_qty"), 1),
            get_safe(o, "opt_name_zh"),
            get_safe(o, "opt_desc_zh"),
            get_safe(o, "opt_suffix"),
            get_safe(o, "opt_variant_image"),
            st.session_state.get("user_id", 1),
        ),
    )

    if ok:
        st.success("Donanım kopyalandı.")

    return ok


def show_model_form(mode="add", model_id=None):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")

    if col_back.button("🔙", use_container_width=True):
        clear_model_form_state()
        st.session_state.view_mode = "list"
        st.rerun()

    col_title.header("✏️ Makine Düzenle" if mode == "edit" else "✨ Yeni Makine Ekle")

    model = {}

    if mode == "edit":
        if model_id is None:
            st.error("Düzenlenecek makine ID bilgisi bulunamadı.")
            st.stop()

        rows = db_query("SELECT * FROM models WHERE id=?", (safe_int(model_id),))

        if not rows:
            st.error(f"Kayıt veritabanında bulunamadı. Aranan makine ID: {model_id}")
            st.stop()

        model = rows[0]

    session_key = f"model_specs_{mode}_{model_id or 'new'}"

    if session_key not in st.session_state:
        st.session_state[session_key] = parse_specs(model.get("specs", "")) if mode == "edit" else []

    specs_list = st.session_state[session_key]

    current_name = get_safe(model, "name")
    current_category = get_safe(model, "category", "Diğer Makinalar")
    current_price = safe_float(model.get("base_price"))
    current_sale_price = safe_float(model.get("sale_price")) or current_price
    current_currency = get_safe(model, "currency", "USD")
    current_discount = safe_float(model.get("port_discount"))
    current_image = get_safe(model, "image_path")
    current_options = [x.strip() for x in str(get_safe(model, "compatible_options")).split(",") if x.strip()]

    tabs = ["📄 Genel Bilgiler", "⚙️ Teknik Özellikler", "🔌 Uyumlu Donanımlar"]
    if can_view_costs():
        tabs.append("💰 Maliyet")

    tab_objs = st.tabs(tabs)
    tab_general = tab_objs[0]
    tab_specs = tab_objs[1]
    tab_options = tab_objs[2]
    tab_cost = tab_objs[3] if can_view_costs() else None

    with tab_general:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1], gap="large")

            with c1:
                name = st.text_input("Makine Adı *", value=current_name)

                cats = get_category_list()
                if current_category not in cats:
                    cats.append(current_category)

                category = st.selectbox(
                    "Kategori",
                    options=cats,
                    index=cats.index(current_category) if current_category in cats else 0,
                )

                c_price, c_sale, c_currency, c_discount = st.columns(4)
                price = c_price.number_input("Liste Fiyatı / Eski Fiyat", value=current_price, step=100.0)
                sale_price = c_sale.number_input("Satış Fiyatı *", value=current_sale_price, step=100.0)
                currency = c_currency.selectbox(
                    "Para Birimi",
                    ["USD", "EUR", "TRY", "CNY"],
                    index=["USD", "EUR", "TRY", "CNY"].index(current_currency)
                    if current_currency in ["USD", "EUR", "TRY", "CNY"]
                    else 0,
                )
                discount = c_discount.number_input("İskonto (%)", value=current_discount, step=1.0)

                uploaded_image = st.file_uploader(
                    "Ana Görsel",
                    type=["png", "jpg", "jpeg"],
                    key=f"model_main_img_{mode}_{model_id or 'new'}",
                )

            with c2:
                st.markdown("**Görsel Önizleme**")
                if uploaded_image:
                    st.image(uploaded_image, use_container_width=True)
                else:
                    img_b64 = get_image_base64(current_image)
                    if img_b64:
                        st.markdown(f'<img src="{img_b64}" style="width:100%; border-radius:14px;">', unsafe_allow_html=True)
                    else:
                        st.caption("Görsel yok")

    with tab_specs:
        st.markdown("### Teknik Özellikler")

        if not specs_list:
            st.info("Henüz teknik özellik eklenmedi.")

        for i, spec in enumerate(specs_list):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 3, 2, 1], vertical_alignment="center")

                spec["title"] = c1.text_input("Başlık", value=spec.get("title", ""), key=f"spec_title_{session_key}_{i}")
                spec["detail"] = c2.text_input("Detay", value=spec.get("detail", ""), key=f"spec_detail_{session_key}_{i}")

                spec_upload = c3.file_uploader("Görsel", type=["png", "jpg", "jpeg"], key=f"spec_img_{session_key}_{i}")

                if spec_upload:
                    new_spec_img = process_image(spec_upload, "spec", square=True)
                    if new_spec_img:
                        spec["img"] = new_spec_img

                if spec.get("img"):
                    img_b64 = get_image_base64(spec.get("img"))
                    if img_b64:
                        c3.markdown(f'<img src="{img_b64}" style="width:55px; height:55px; object-fit:contain; border-radius:8px;">', unsafe_allow_html=True)

                if c4.button("❌", key=f"delete_spec_{session_key}_{i}", use_container_width=True):
                    specs_list.pop(i)
                    st.rerun()

        if st.button("➕ Yeni Özellik Satırı Ekle", use_container_width=True):
            specs_list.append({"title": "", "detail": "", "img": ""})
            st.rerun()

    with tab_options:
        st.markdown("### Uyumlu Donanımlar")

        all_options = db_query("SELECT * FROM options ORDER BY opt_name ASC")
        selected_options = []

        if not all_options:
            st.info("Henüz donanım eklenmedi.")
        else:
            for i in range(0, len(all_options), 3):
                cols = st.columns(3)

                for j in range(3):
                    if i + j >= len(all_options):
                        continue

                    opt = all_options[i + j]
                    opt_id = str(opt.get("id"))
                    opt_display_price = safe_float(opt.get("sale_price")) or safe_float(opt.get("opt_price"))

                    with cols[j].container(border=True):
                        img_b64 = get_image_base64(opt.get("opt_image"))

                        if img_b64:
                            st.markdown(f'<img src="{img_b64}" style="width:100%; height:90px; object-fit:contain; border-radius:10px;">', unsafe_allow_html=True)

                        checked = st.checkbox(
                            f"{opt.get('opt_name', 'Donanım')} (+{opt_display_price:,.0f})",
                            value=opt_id in current_options,
                            key=f"model_opt_{mode}_{model_id or 'new'}_{opt_id}",
                        )

                        if checked:
                            selected_options.append(opt_id)

    purchase_price = safe_float(model.get("purchase_price"))
    shipping_cost = safe_float(model.get("shipping_cost"))
    customs_tax_rate = safe_float(model.get("customs_tax_rate"), 3)
    extra_tax_rate = safe_float(model.get("extra_tax_rate"), 10)
    port_cost = safe_float(model.get("port_cost"))
    document_cost = safe_float(model.get("document_cost"))
    installation_cost = safe_float(model.get("installation_cost"))
    other_cost = safe_float(model.get("other_cost"))
    cost_note = get_safe(model, "cost_note")

    if can_view_costs() and tab_cost is not None:
        with tab_cost:
            st.markdown("<div class='cost-box'>Bu alan sadece yönetici tarafından kullanılır. Bayi / üretici maliyetleri görmez.</div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)

            with c1:
                purchase_price = st.number_input("Üretici Alış Fiyatı", value=purchase_price, step=100.0)
                shipping_cost = st.number_input("Nakliye", value=shipping_cost, step=100.0)
                customs_tax_rate = st.number_input("Gümrük Vergisi %", value=customs_tax_rate, step=0.1)
                extra_tax_rate = st.number_input("Ek Vergi %", value=extra_tax_rate, step=0.1)

            with c2:
                port_cost = st.number_input("Liman / Kıyı Gideri", value=port_cost, step=100.0)
                document_cost = st.number_input("Belge Gideri", value=document_cost, step=100.0)
                installation_cost = st.number_input("Kurulum Gideri", value=installation_cost, step=100.0)
                other_cost = st.number_input("Diğer Giderler", value=other_cost, step=100.0)

            cost_note = st.text_area("Maliyet Notu", value=cost_note)

            cost = calculate_import_cost(
                purchase_price,
                shipping_cost,
                customs_tax_rate,
                extra_tax_rate,
                port_cost,
                document_cost,
                installation_cost,
                other_cost,
            )

            profit = sale_price - cost["toplam"]
            profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Maliyet", f"{cost['toplam']:,.2f} $")
            m2.metric("Net Kâr", f"{profit:,.2f} $")
            m3.metric("Kâr Oranı", f"%{profit_rate:.2f}")

            with st.expander("Hesaplama Detayı"):
                st.write(f"Alış + Nakliye: {cost['ara_1']:,.2f} $")
                st.write(f"Gümrük Vergisi: {cost['gumruk']:,.2f} $")
                st.write(f"Gümrük Sonrası: {cost['ara_2']:,.2f} $")
                st.write(f"Ek Vergi: {cost['ek_vergi']:,.2f} $")
                st.write(f"Vergiler Sonrası: {cost['ara_3']:,.2f} $")
                st.write(f"Toplam Maliyet: {cost['toplam']:,.2f} $")

    st.markdown("---")
    button_label = "💾 Değişiklikleri Kaydet" if mode == "edit" else "💾 Sisteme Ekle"

    if st.button(button_label, type="primary", use_container_width=True):
        if not str(name).strip():
            st.error("Makine adı boş bırakılamaz.")
            return

        final_image = current_image

        if uploaded_image:
            processed = process_image(uploaded_image, "machine", square=False)
            if processed:
                final_image = processed

        specs_text = build_specs(specs_list)
        compatible_options = ",".join(selected_options)
        user_id = st.session_state.get("user_id", 1)

        if mode == "edit":
            ok = exec_factory(
                """
                UPDATE models
                SET name=?, category=?, base_price=?, sale_price=?, currency=?, port_discount=?,
                    image_path=?, specs=?, compatible_options=?,
                    purchase_price=?, shipping_cost=?, customs_tax_rate=?, extra_tax_rate=?,
                    port_cost=?, document_cost=?, installation_cost=?, other_cost=?, cost_note=?
                WHERE id=?
                """,
                (
                    name.strip(),
                    category,
                    price,
                    sale_price,
                    currency,
                    discount,
                    final_image,
                    specs_text,
                    compatible_options,
                    purchase_price,
                    shipping_cost,
                    customs_tax_rate,
                    extra_tax_rate,
                    port_cost,
                    document_cost,
                    installation_cost,
                    other_cost,
                    cost_note,
                    safe_int(model_id),
                ),
            )
        else:
            ok = exec_factory(
                """
                INSERT INTO models (
                    name, category, base_price, sale_price, currency, port_discount,
                    image_path, specs, compatible_options, user_id,
                    purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate,
                    port_cost, document_cost, installation_cost, other_cost, cost_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    category,
                    price,
                    sale_price,
                    currency,
                    discount,
                    final_image,
                    specs_text,
                    compatible_options,
                    user_id,
                    purchase_price,
                    shipping_cost,
                    customs_tax_rate,
                    extra_tax_rate,
                    port_cost,
                    document_cost,
                    installation_cost,
                    other_cost,
                    cost_note,
                ),
            )

        if ok:
            clear_model_form_state()
            st.session_state.view_mode = "list"
            st.success("Makine başarıyla kaydedildi.")
            st.rerun()


def clear_model_form_state():
    keys_to_delete = []

    for key in st.session_state.keys():
        if str(key).startswith("model_specs_"):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        st.session_state.pop(key, None)


def show_option_form(mode="add", option_id=None):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")

    if col_back.button("🔙", use_container_width=True):
        st.session_state.view_mode = "list"
        st.rerun()

    col_title.header("✏️ Donanım Düzenle" if mode == "edit" else "✨ Yeni Donanım Ekle")

    option = {}

    if mode == "edit":
        if option_id is None:
            st.error("Düzenlenecek donanım ID bilgisi bulunamadı.")
            st.stop()

        rows = db_query("SELECT * FROM options WHERE id=?", (safe_int(option_id),))

        if not rows:
            st.error(f"Donanım kaydı veritabanında bulunamadı. Aranan ID: {option_id}")
            st.stop()

        option = rows[0]

    current_name = get_safe(option, "opt_name")
    current_desc = get_safe(option, "opt_desc")
    current_price = safe_float(option.get("opt_price"))
    current_sale_price = safe_float(option.get("sale_price")) or current_price
    current_image = get_safe(option, "opt_image")
    current_allow_qty = bool(safe_int(option.get("allow_qty"), 1))
    current_suffix = get_safe(option, "opt_suffix")
    current_variant_img = get_safe(option, "opt_variant_image")

    tabs = ["📄 Genel Bilgiler"]
    if can_view_costs():
        tabs.append("💰 Maliyet")

    tab_objs = st.tabs(tabs)
    tab_general = tab_objs[0]
    tab_cost = tab_objs[1] if can_view_costs() else None

    with tab_general:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1], gap="large")

            with c1:
                name = st.text_input("Donanım Adı *", value=current_name)
                c_price, c_sale = st.columns(2)
                price = c_price.number_input("Liste Fiyatı / Eski Fiyat", value=current_price, step=50.0)
                sale_price = c_sale.number_input("Satış Fiyatı *", value=current_sale_price, step=50.0)

                allow_qty = st.checkbox("Bu donanım için adet seçilebilir", value=current_allow_qty)
                desc = st.text_area("Açıklama", value=current_desc, height=120)

                st.markdown("---")
                suffix = st.text_input("Model Adı Eki / Suffix", value=current_suffix, placeholder="Örn: L, PRO, PLUS")

                main_img_upload = st.file_uploader("Donanım Görseli", type=["png", "jpg", "jpeg"], key=f"option_main_img_{mode}_{option_id or 'new'}")
                variant_img_upload = st.file_uploader("Varyasyon Ana Resmi", type=["png", "jpg", "jpeg"], key=f"option_variant_img_{mode}_{option_id or 'new'}")

            with c2:
                st.markdown("**Donanım Görseli**")

                if main_img_upload:
                    st.image(main_img_upload, use_container_width=True)
                else:
                    img_b64 = get_image_base64(current_image)
                    if img_b64:
                        st.markdown(f'<img src="{img_b64}" style="width:100%; border-radius:14px;">', unsafe_allow_html=True)
                    else:
                        st.caption("Görsel yok")

                st.markdown("**Varyasyon Görseli**")

                if variant_img_upload:
                    st.image(variant_img_upload, use_container_width=True)
                else:
                    var_b64 = get_image_base64(current_variant_img)
                    if var_b64:
                        st.markdown(f'<img src="{var_b64}" style="width:100%; border-radius:14px;">', unsafe_allow_html=True)
                    else:
                        st.caption("Varyasyon görseli yok")

    purchase_price = safe_float(option.get("purchase_price"))
    shipping_cost = safe_float(option.get("shipping_cost"))
    customs_tax_rate = safe_float(option.get("customs_tax_rate"), 3)
    extra_tax_rate = safe_float(option.get("extra_tax_rate"), 10)
    port_cost = safe_float(option.get("port_cost"))
    document_cost = safe_float(option.get("document_cost"))
    installation_cost = safe_float(option.get("installation_cost"))
    other_cost = safe_float(option.get("other_cost"))
    cost_note = get_safe(option, "cost_note")

    if can_view_costs() and tab_cost is not None:
        with tab_cost:
            st.markdown("<div class='cost-box'>Bu alan sadece yönetici tarafından görülmelidir.</div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)

            with c1:
                purchase_price = st.number_input("Alış Fiyatı", value=purchase_price, step=50.0)
                shipping_cost = st.number_input("Nakliye", value=shipping_cost, step=50.0)
                customs_tax_rate = st.number_input("Gümrük Vergisi %", value=customs_tax_rate, step=0.1)
                extra_tax_rate = st.number_input("Ek Vergi %", value=extra_tax_rate, step=0.1)

            with c2:
                port_cost = st.number_input("Liman / Kıyı Gideri", value=port_cost, step=50.0)
                document_cost = st.number_input("Belge Gideri", value=document_cost, step=50.0)
                installation_cost = st.number_input("Kurulum Gideri", value=installation_cost, step=50.0)
                other_cost = st.number_input("Diğer Giderler", value=other_cost, step=50.0)

            cost_note = st.text_area("Maliyet Notu", value=cost_note)

            cost = calculate_import_cost(
                purchase_price,
                shipping_cost,
                customs_tax_rate,
                extra_tax_rate,
                port_cost,
                document_cost,
                installation_cost,
                other_cost,
            )

            profit = sale_price - cost["toplam"]
            profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Maliyet", f"{cost['toplam']:,.2f} $")
            m2.metric("Net Kâr", f"{profit:,.2f} $")
            m3.metric("Kâr Oranı", f"%{profit_rate:.2f}")

    st.markdown("---")
    button_label = "💾 Değişiklikleri Kaydet" if mode == "edit" else "💾 Sisteme Ekle"

    if st.button(button_label, type="primary", use_container_width=True):
        if not str(name).strip():
            st.error("Donanım adı boş bırakılamaz.")
            return

        final_img = current_image
        final_variant_img = current_variant_img

        if main_img_upload:
            processed = process_image(main_img_upload, "option", square=True)
            if processed:
                final_img = processed

        if variant_img_upload:
            processed_variant = process_image(variant_img_upload, "variant", square=False)
            if processed_variant:
                final_variant_img = processed_variant

        user_id = st.session_state.get("user_id", 1)
        allow_qty_int = 1 if allow_qty else 0

        if mode == "edit":
            ok = exec_factory(
                """
                UPDATE options
                SET opt_name=?, opt_desc=?, opt_price=?, sale_price=?, opt_image=?,
                    allow_qty=?, opt_suffix=?, opt_variant_image=?,
                    purchase_price=?, shipping_cost=?, customs_tax_rate=?, extra_tax_rate=?,
                    port_cost=?, document_cost=?, installation_cost=?, other_cost=?, cost_note=?
                WHERE id=?
                """,
                (
                    name.strip(),
                    desc,
                    price,
                    sale_price,
                    final_img,
                    allow_qty_int,
                    suffix,
                    final_variant_img,
                    purchase_price,
                    shipping_cost,
                    customs_tax_rate,
                    extra_tax_rate,
                    port_cost,
                    document_cost,
                    installation_cost,
                    other_cost,
                    cost_note,
                    safe_int(option_id),
                ),
            )
        else:
            ok = exec_factory(
                """
                INSERT INTO options (
                    opt_name, opt_desc, opt_price, sale_price, opt_image,
                    allow_qty, opt_suffix, opt_variant_image, user_id,
                    purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate,
                    port_cost, document_cost, installation_cost, other_cost, cost_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    desc,
                    price,
                    sale_price,
                    final_img,
                    allow_qty_int,
                    suffix,
                    final_variant_img,
                    user_id,
                    purchase_price,
                    shipping_cost,
                    customs_tax_rate,
                    extra_tax_rate,
                    port_cost,
                    document_cost,
                    installation_cost,
                    other_cost,
                    cost_note,
                ),
            )

        if ok:
            st.session_state.view_mode = "list"
            st.success("Donanım başarıyla kaydedildi.")
            st.rerun()