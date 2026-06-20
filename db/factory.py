import sqlite3
import json
from config import FACTORY_DB


def _c():
    return sqlite3.connect(FACTORY_DB, check_same_thread=False)


def _acol(cur, tbl, col, typ):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")


def init():
    with _c() as c:
        cur = c.cursor()

        cur.execute("""CREATE TABLE IF NOT EXISTS company_profile(
            id INTEGER PRIMARY KEY CHECK(id=1),
            company_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            website TEXT DEFAULT '',
            tax_id TEXT DEFAULT '',
            email TEXT DEFAULT '',
            logo_path TEXT DEFAULT ''
        )""")
        if not cur.execute("SELECT id FROM company_profile WHERE id=1").fetchone():
            cur.execute("INSERT INTO company_profile(id) VALUES(1)")

        cur.execute("""CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS models(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER DEFAULT NULL,
            description TEXT DEFAULT '',
            base_price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            specs TEXT DEFAULT '',
            purchase_price REAL DEFAULT 0,
            purchase_currency TEXT DEFAULT 'USD',
            shipping_cost REAL DEFAULT 0,
            customs_pct REAL DEFAULT 0,
            extra_tax_pct REAL DEFAULT 0,
            port_cost REAL DEFAULT 0,
            document_cost REAL DEFAULT 0,
            installation_cost REAL DEFAULT 0,
            other_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            image_path TEXT DEFAULT '',
            compatible_options TEXT DEFAULT '[]',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            scope TEXT DEFAULT 'GLOBAL',
            category_id INTEGER DEFAULT NULL,
            qty_type TEXT DEFAULT 'MANUAL',
            conflict_group TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            country TEXT DEFAULT '',
            currency TEXT DEFAULT 'USD',
            notes TEXT DEFAULT '',
            dealer_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS offers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_no TEXT DEFAULT '',
            customer_id INTEGER DEFAULT NULL,
            model_id INTEGER DEFAULT NULL,
            machine_count INTEGER DEFAULT 1,
            currency TEXT DEFAULT 'USD',
            base_price REAL DEFAULT 0,
            options_total REAL DEFAULT 0,
            discount_pct REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            status TEXT DEFAULT 'Beklemede',
            notes TEXT DEFAULT '',
            validity_date TEXT DEFAULT '',
            dealer_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS offer_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            option_id INTEGER NOT NULL,
            qty INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0,
            line_total REAL DEFAULT 0
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS customer_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            txn_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            description TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            txn_date TEXT DEFAULT(date('now')),
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS manufacturer_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_name TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            description TEXT DEFAULT '',
            txn_date TEXT DEFAULT(date('now')),
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Option image columns
        _acol(cur, "options", "image_path",           "TEXT DEFAULT ''")
        _acol(cur, "options", "image_priority",       "INTEGER DEFAULT 0")
        _acol(cur, "options", "variation_image_path", "TEXT DEFAULT ''")
        _acol(cur, "options", "video_url",            "TEXT DEFAULT ''")
        _acol(cur, "options", "category_ids",         "TEXT DEFAULT ''")
        _acol(cur, "options", "created_by",            "INTEGER DEFAULT NULL")
        _acol(cur, "options", "manufacturer_id",       "INTEGER DEFAULT NULL")
        _acol(cur, "options", "requires_option_ids",   "TEXT DEFAULT ''")
        # Migrate old single category_id to category_ids
        cur.execute("""
            UPDATE options SET category_ids = CAST(category_id AS TEXT)
            WHERE (category_ids IS NULL OR category_ids = '')
              AND category_id IS NOT NULL AND category_id != 0
        """)

        # Hat (line) machine support
        _acol(cur, "models", "image_path",      "TEXT DEFAULT ''")
        _acol(cur, "models", "is_line",         "INTEGER DEFAULT 0")
        _acol(cur, "models", "line_configs",    "TEXT DEFAULT '2,3,4'")
        _acol(cur, "models", "manufacturer_id", "INTEGER DEFAULT NULL")
        _acol(cur, "models", "catalog_sort",    "INTEGER DEFAULT 999")
        cur.execute("""CREATE TABLE IF NOT EXISTS model_line_images(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            line_count INTEGER NOT NULL,
            image_path TEXT DEFAULT '',
            priority INTEGER DEFAULT 0
        )""")

        # New columns on offers for order workflow
        for col, typ in [
            ("manufacturer_id", "INTEGER DEFAULT NULL"),
            ("admin_status",    "TEXT DEFAULT ''"),
            ("admin_notes",     "TEXT DEFAULT ''"),
            ("termin_date",     "TEXT DEFAULT ''"),
            ("mfr_status",      "TEXT DEFAULT ''"),
            ("mfr_notes",       "TEXT DEFAULT ''"),
        ]:
            _acol(cur, "offers", col, typ)

        # SMTP config stored in company_profile
        for col, typ in [
            ("smtp_host", "TEXT DEFAULT ''"),
            ("smtp_port", "INTEGER DEFAULT 587"),
            ("smtp_user", "TEXT DEFAULT ''"),
            ("smtp_pass", "TEXT DEFAULT ''"),
            ("smtp_from", "TEXT DEFAULT ''"),
        ]:
            _acol(cur, "company_profile", col, typ)

        # Translation columns
        for col in ["name_en", "name_zh"]:
            _acol(cur, "categories", col, "TEXT DEFAULT ''")
        _acol(cur, "categories", "is_line_capable", "INTEGER DEFAULT 0")
        for col in ["name_en", "description_en", "name_zh", "description_zh"]:
            _acol(cur, "options", col, "TEXT DEFAULT ''")
        for col in ["name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh"]:
            _acol(cur, "models", col, "TEXT DEFAULT ''")

        # Delivery / payment terms on offers
        for col, typ in [
            ("delivery_method", "TEXT DEFAULT ''"),
            ("delivery_time",   "TEXT DEFAULT ''"),
            ("logistics",       "TEXT DEFAULT ''"),
            ("payment_notes",   "TEXT DEFAULT ''"),
        ]:
            _acol(cur, "offers", col, typ)

        # Add order_id to manufacturer_transactions
        _acol(cur, "manufacturer_transactions", "order_id", "INTEGER DEFAULT NULL")

        # Production stage log
        cur.execute("""CREATE TABLE IF NOT EXISTS order_stages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            stage_name TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            stage_date TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Dealer ledger
        cur.execute("""CREATE TABLE IF NOT EXISTS dealer_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dealer_id INTEGER NOT NULL,
            txn_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            description TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            txn_date TEXT DEFAULT(date('now')),
            order_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Manufacturer user ledger (user-id based, for per-user hakediş tracking)
        cur.execute("""CREATE TABLE IF NOT EXISTS manufacturer_user_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_id INTEGER NOT NULL,
            txn_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            description TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            txn_date TEXT DEFAULT(date('now')),
            order_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        _init_membrane(cur)
        _init_loan_rates(cur)

        # Deletion requests from manufacturers
        cur.execute("""CREATE TABLE IF NOT EXISTS deletion_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            requested_by INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT(datetime('now')),
            resolved_at TEXT DEFAULT NULL
        )""")

        # Delivery terms (Incoterms presets with automatic discount rates)
        cur.execute("""CREATE TABLE IF NOT EXISTS delivery_terms(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            discount_pct REAL DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )""")
        # Seed defaults if empty
        _cnt = cur.execute("SELECT COUNT(*) FROM delivery_terms").fetchone()[0]
        if _cnt == 0:
            cur.execute("INSERT INTO delivery_terms(name,discount_pct,sort_order) VALUES(?,?,?)", ("Antrepo Teslim (DDP)", 0, 1))
            cur.execute("INSERT INTO delivery_terms(name,discount_pct,sort_order) VALUES(?,?,?)", ("Liman Teslim (FOB)", 10, 2))

        # delivery_term_id + delivery_term_discount on offers
        _acol(cur, "offers", "delivery_term_id",       "INTEGER DEFAULT NULL")
        _acol(cur, "offers", "delivery_term_discount",  "REAL DEFAULT 0")

        # Production steps table
        cur.execute("""CREATE TABLE IF NOT EXISTS production_steps(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label_tr TEXT DEFAULT '',
            label_en TEXT DEFAULT '',
            label_zh TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )""")
        # Pre-populate only if empty
        existing = cur.execute("SELECT COUNT(*) FROM production_steps").fetchone()[0]
        if existing == 0:
            cur.executemany(
                "INSERT INTO production_steps(code,label_tr,label_en,label_zh,sort_order) VALUES(?,?,?,?,?)",
                [
                    ('in_production', 'Üretimde', 'In Production', '生产中', 1),
                    ('completed', 'Tamamlandı', 'Completed', '已完成', 2),
                    ('delivered', 'Teslim Edildi', 'Delivered', '已交付', 3),
                ]
            )
        # Add mfr_status_date to offers
        _acol(cur, "offers", "mfr_status_date", "TEXT DEFAULT ''")

        # Stage photo
        _acol(cur, "order_stages", "photo", "TEXT DEFAULT ''")

        # Dealer order workflow columns
        _acol(cur, "offers", "cancel_reason",   "TEXT DEFAULT ''")
        _acol(cur, "offers", "contract_notes",  "TEXT DEFAULT ''")
        _acol(cur, "offers", "contract_photo",  "TEXT DEFAULT ''")

        # Dealer change requests
        cur.execute("""CREATE TABLE IF NOT EXISTS change_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            dealer_id INTEGER NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            admin_notes TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Purchase price tracking for options (set by manufacturers)
        _acol(cur, "options", "purchase_price",    "REAL DEFAULT 0")
        _acol(cur, "options", "purchase_currency", "TEXT DEFAULT 'USD'")

        # Price change requests from manufacturers
        cur.execute("""CREATE TABLE IF NOT EXISTS price_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_name TEXT NOT NULL,
            manufacturer_id INTEGER NOT NULL,
            current_price REAL DEFAULT 0,
            new_price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            admin_note TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now')),
            resolved_at TEXT DEFAULT NULL
        )""")

        # Serial number on offers
        _acol(cur, "offers", "serial_number", "TEXT DEFAULT ''")
        _acol(cur, "offers", "final_price",   "REAL DEFAULT 0")

        # Proforma invoices per order
        cur.execute("""CREATE TABLE IF NOT EXISTS order_proformas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            uploaded_by INTEGER DEFAULT NULL,
            uploaded_at TEXT DEFAULT(datetime('now'))
        )""")

        # Machine documents per order
        cur.execute("""CREATE TABLE IF NOT EXISTS order_documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            doc_type TEXT DEFAULT '',
            uploaded_by INTEGER DEFAULT NULL,
            uploaded_at TEXT DEFAULT(datetime('now'))
        )""")

        c.commit()


def _init_loan_rates(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS loan_rates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name    TEXT DEFAULT 'Standart',
        grace_months INTEGER DEFAULT 0,
        term_months  INTEGER NOT NULL,
        rate_tl      REAL DEFAULT 0,
        rate_usd     REAL DEFAULT 0,
        rate_eur     REAL DEFAULT 0,
        file_fee_pct REAL DEFAULT 0.5,
        is_active    INTEGER DEFAULT 1,
        updated_at   TEXT DEFAULT(datetime('now'))
    )""")
    # Seed default rates if table is empty
    count = cur.execute("SELECT COUNT(*) FROM loan_rates").fetchone()[0]
    if count == 0:
        rows = [
            # Standart plan
            ("Standart", 0, 12, 19.61, 4.16, 3.67, 0.5),
            ("Standart", 0, 18, 26.60, 6.09, 5.39, 0.5),
            ("Standart", 0, 24, 32.24, 7.91, 7.01, 0.5),
            ("Standart", 0, 36, 41.90, 12.03, 10.78, 0.5),
            ("Standart", 0, 48, 49.34, 15.51, 14.53, 0.5),
            ("Standart", 0, 60, 54.94, 18.80, 17.65, 0.5),
            # 3 Ay Ödemesiz plan
            ("3 Ay Ödemesiz", 3, 12, 27.72, 6.40, 5.66, 0.5),
            ("3 Ay Ödemesiz", 3, 18, 33.21, 8.21, 7.28, 0.5),
            ("3 Ay Ödemesiz", 3, 24, 37.90, 10.52, 9.42, 0.5),
            ("3 Ay Ödemesiz", 3, 36, 46.17, 14.08, 13.19, 0.5),
            ("3 Ay Ödemesiz", 3, 48, 52.39, 17.45, 16.37, 0.5),
        ]
        cur.executemany(
            "INSERT INTO loan_rates(plan_name,grace_months,term_months,rate_tl,rate_usd,rate_eur,file_fee_pct) VALUES(?,?,?,?,?,?,?)",
            rows
        )


# ── Loan Rates ────────────────────────────────────────────────────────────────

_LR_KEYS = ["id","plan_name","grace_months","term_months","rate_tl","rate_usd","rate_eur","file_fee_pct","is_active","updated_at"]
_LR_COLS = ",".join(_LR_KEYS)

def _rl(r): return dict(zip(_LR_KEYS, r)) if r else None

def get_loan_rates(active_only=True):
    q = f"SELECT {_LR_COLS} FROM loan_rates"
    if active_only:
        q += " WHERE is_active=1"
    q += " ORDER BY plan_name, term_months"
    with _c() as c:
        return [_rl(r) for r in c.execute(q).fetchall()]

def get_loan_rate(rid):
    with _c() as c:
        return _rl(c.execute(f"SELECT {_LR_COLS} FROM loan_rates WHERE id=?", (rid,)).fetchone())

def save_loan_rate(id=None, **kw):
    allowed = ["plan_name","grace_months","term_months","rate_tl","rate_usd","rate_eur","file_fee_pct","is_active"]
    f = {k: v for k, v in kw.items() if k in allowed}
    f["updated_at"] = "datetime('now')"
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f if k != "updated_at")
            vals = [v for k, v in f.items() if k != "updated_at"]
            c.execute(f"UPDATE loan_rates SET {sets}, updated_at=datetime('now') WHERE id=?", vals + [id])
        else:
            cols = ",".join(k for k in f if k != "updated_at")
            phs  = ",".join("?" for k in f if k != "updated_at")
            vals = [v for k, v in f.items() if k != "updated_at"]
            c.execute(f"INSERT INTO loan_rates({cols},updated_at) VALUES({phs},datetime('now'))", vals)
        c.commit()

def del_loan_rate(rid):
    with _c() as c:
        c.execute("DELETE FROM loan_rates WHERE id=?", (rid,))
        c.commit()


# ── Company ───────────────────────────────────────────────────────────────────

def get_company():
    with _c() as c:
        r = c.execute(
            "SELECT company_name,address,phone,website,tax_id,email,logo_path,"
            "smtp_host,smtp_port,smtp_user,smtp_pass,smtp_from FROM company_profile WHERE id=1"
        ).fetchone()
    if not r:
        return {}
    return dict(zip(["company_name","address","phone","website","tax_id","email","logo_path",
                     "smtp_host","smtp_port","smtp_user","smtp_pass","smtp_from"], r))


def save_company(**kw):
    allowed = ["company_name", "address", "phone", "website", "tax_id", "email", "logo_path",
               "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE company_profile SET {sets} WHERE id=1", list(f.values()))


# ── Categories ────────────────────────────────────────────────────────────────

def get_cats():
    with _c() as c:
        rows = c.execute("SELECT id,name,description,name_en,name_zh,is_line_capable FROM categories ORDER BY name").fetchall()
    return [dict(zip(["id","name","description","name_en","name_zh","is_line_capable"], r)) for r in rows]


def add_cat(name, description="", name_en="", name_zh="", is_line_capable=0):
    with _c() as c:
        c.execute("INSERT OR IGNORE INTO categories(name,description,name_en,name_zh,is_line_capable) VALUES(?,?,?,?,?)", (name, description, name_en, name_zh, is_line_capable))


def upd_cat(cid, name, description="", name_en="", name_zh="", is_line_capable=0):
    with _c() as c:
        c.execute("UPDATE categories SET name=?,description=?,name_en=?,name_zh=?,is_line_capable=? WHERE id=?", (name, description, name_en, name_zh, is_line_capable, cid))


def del_cat(cid):
    with _c() as c:
        c.execute("DELETE FROM categories WHERE id=?", (cid,))


# ── Models ────────────────────────────────────────────────────────────────────

_MCOLS = ("id,name,category_id,description,base_price,currency,specs,"
          "purchase_price,purchase_currency,shipping_cost,customs_pct,extra_tax_pct,"
          "port_cost,document_cost,installation_cost,other_cost,total_cost,"
          "image_path,compatible_options,"
          "name_en,description_en,name_zh,description_zh,specs_en,specs_zh,created_at,"
          "is_line,line_configs,manufacturer_id,catalog_sort")

_MKEYS = ["id", "name", "category_id", "description", "base_price", "currency", "specs",
          "purchase_price", "purchase_currency", "shipping_cost", "customs_pct", "extra_tax_pct",
          "port_cost", "document_cost", "installation_cost", "other_cost", "total_cost",
          "image_path", "compatible_options",
          "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh",
          "created_at", "is_line", "line_configs", "manufacturer_id", "catalog_sort"]


def _rm(r):
    return dict(zip(_MKEYS, r))


def get_models(category_id=None):
    q = f"SELECT {_MCOLS} FROM models WHERE 1=1"
    p = []
    if category_id:
        q += " AND category_id=?"
        p.append(category_id)
    q += " ORDER BY COALESCE(catalog_sort,999) ASC, name ASC"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [_rm(r) for r in rows]


def get_model(mid):
    with _c() as c:
        r = c.execute(f"SELECT {_MCOLS} FROM models WHERE id=?", (mid,)).fetchone()
    return _rm(r) if r else None


def add_model(**kw):
    allowed = ["name", "category_id", "description", "base_price", "currency", "specs",
               "purchase_price", "purchase_currency", "shipping_cost", "customs_pct",
               "extra_tax_pct", "port_cost", "document_cost", "installation_cost",
               "other_cost", "total_cost", "image_path", "compatible_options",
               "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh",
               "is_line", "line_configs", "manufacturer_id", "catalog_sort"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO models({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_model(mid, **kw):
    allowed = ["name", "category_id", "description", "base_price", "currency", "specs",
               "purchase_price", "purchase_currency", "shipping_cost", "customs_pct",
               "extra_tax_pct", "port_cost", "document_cost", "installation_cost",
               "other_cost", "total_cost", "image_path", "compatible_options",
               "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh",
               "is_line", "line_configs", "manufacturer_id", "catalog_sort"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE models SET {sets} WHERE id=?", list(f.values()) + [mid])


def del_model(mid):
    with _c() as c:
        c.execute("DELETE FROM models WHERE id=?", (mid,))


def get_model_line_images(model_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,model_id,line_count,image_path,priority FROM model_line_images WHERE model_id=? ORDER BY line_count",
            (model_id,)
        ).fetchall()
    return [{"id": r[0], "model_id": r[1], "line_count": r[2], "image_path": r[3], "priority": r[4]} for r in rows]


def save_model_line_image(model_id, line_count, image_path, priority=0):
    with _c() as c:
        existing = c.execute(
            "SELECT id FROM model_line_images WHERE model_id=? AND line_count=?",
            (model_id, line_count)
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE model_line_images SET image_path=?,priority=? WHERE id=?",
                (image_path, priority, existing[0])
            )
        else:
            c.execute(
                "INSERT INTO model_line_images(model_id,line_count,image_path,priority) VALUES(?,?,?,?)",
                (model_id, line_count, image_path, priority)
            )


def del_model_line_image(image_id):
    with _c() as c:
        c.execute("DELETE FROM model_line_images WHERE id=?", (image_id,))


# ── Options ───────────────────────────────────────────────────────────────────

_OCOLS = "id,name,description,price,currency,scope,category_id,qty_type,conflict_group,image_path,image_priority,variation_image_path,video_url,name_en,description_en,name_zh,description_zh,created_at,category_ids,created_by,manufacturer_id,requires_option_ids,purchase_price,purchase_currency"
_OKEYS = ["id", "name", "description", "price", "currency", "scope",
          "category_id", "qty_type", "conflict_group", "image_path", "image_priority",
          "variation_image_path", "video_url", "name_en", "description_en", "name_zh", "description_zh",
          "created_at", "category_ids", "created_by", "manufacturer_id", "requires_option_ids",
          "purchase_price", "purchase_currency"]


def _ro(r):
    return dict(zip(_OKEYS, r))


def get_options(category_id=None, manufacturer_filter=None):
    q = f"SELECT {_OCOLS} FROM options WHERE 1=1"
    p = []
    if category_id:
        q += " AND (',' || category_ids || ',' LIKE ? OR category_ids=?)"
        p += [f"%,{category_id},%", str(category_id)]
    if manufacturer_filter is not None:
        if isinstance(manufacturer_filter, (list, set, frozenset)):
            ids = list(manufacturer_filter)
            ph = ",".join("?" * len(ids))
            q += f" AND (manufacturer_id IN ({ph}) OR created_by IN ({ph}))"
            p += ids + ids
        else:
            q += " AND (manufacturer_id=? OR created_by=?)"
            p += [manufacturer_filter, manufacturer_filter]
    q += " ORDER BY name"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [_ro(r) for r in rows]


def get_option(oid):
    with _c() as c:
        r = c.execute(f"SELECT {_OCOLS} FROM options WHERE id=?", (oid,)).fetchone()
    return _ro(r) if r else None


def add_option(**kw):
    allowed = ["name", "description", "price", "currency", "scope",
               "category_ids", "qty_type", "conflict_group", "image_path", "image_priority",
               "variation_image_path", "video_url", "name_en", "description_en", "name_zh", "description_zh",
               "created_by", "manufacturer_id", "requires_option_ids",
               "purchase_price", "purchase_currency"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO options({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_option(oid, **kw):
    allowed = ["name", "description", "price", "currency", "scope",
               "category_ids", "qty_type", "conflict_group", "image_path", "image_priority",
               "variation_image_path", "video_url", "name_en", "description_en", "name_zh", "description_zh",
               "created_by", "manufacturer_id", "requires_option_ids",
               "purchase_price", "purchase_currency"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE options SET {sets} WHERE id=?", list(f.values()) + [oid])


def del_option(oid):
    with _c() as c:
        c.execute("DELETE FROM options WHERE id=?", (oid,))


# ── Customers ─────────────────────────────────────────────────────────────────

_CCOLS = "id,name,contact_person,email,phone,address,city,country,currency,notes,dealer_id,created_at"
_CKEYS = ["id", "name", "contact_person", "email", "phone", "address",
          "city", "country", "currency", "notes", "dealer_id", "created_at"]


def _rc(r):
    return dict(zip(_CKEYS, r))


def get_customers(dealer_id=None):
    q = f"SELECT {_CCOLS} FROM customers WHERE 1=1"
    p = []
    if dealer_id:
        q += " AND dealer_id=?"
        p.append(dealer_id)
    q += " ORDER BY name"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [_rc(r) for r in rows]


def get_customer(cid):
    with _c() as c:
        r = c.execute(f"SELECT {_CCOLS} FROM customers WHERE id=?", (cid,)).fetchone()
    return _rc(r) if r else None


def add_customer(**kw):
    allowed = ["name", "contact_person", "email", "phone", "address",
               "city", "country", "currency", "notes", "dealer_id"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO customers({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_customer(cid, **kw):
    allowed = ["name", "contact_person", "email", "phone", "address",
               "city", "country", "currency", "notes"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE customers SET {sets} WHERE id=?", list(f.values()) + [cid])


def del_customer(cid):
    with _c() as c:
        c.execute("DELETE FROM customers WHERE id=?", (cid,))


# ── Offers ────────────────────────────────────────────────────────────────────

_OFCOLS = ("id,offer_no,customer_id,model_id,machine_count,currency,"
           "base_price,options_total,discount_pct,total_price,status,"
           "notes,validity_date,dealer_id,manufacturer_id,admin_status,"
           "admin_notes,termin_date,mfr_status,mfr_notes,mfr_status_date,"
           "delivery_method,delivery_time,logistics,payment_notes,created_at,"
           "delivery_term_id,delivery_term_discount,"
           "cancel_reason,contract_notes,contract_photo,serial_number")
_OFKEYS = ["id","offer_no","customer_id","model_id","machine_count","currency",
           "base_price","options_total","discount_pct","total_price","status",
           "notes","validity_date","dealer_id","manufacturer_id","admin_status",
           "admin_notes","termin_date","mfr_status","mfr_notes","mfr_status_date",
           "delivery_method","delivery_time","logistics","payment_notes","created_at",
           "delivery_term_id","delivery_term_discount",
           "cancel_reason","contract_notes","contract_photo","serial_number"]


def _rof(r):
    return dict(zip(_OFKEYS, r))


def get_offers(status=None, customer_id=None, dealer_id=None):
    q = f"SELECT {_OFCOLS} FROM offers WHERE 1=1"
    p = []
    if status:
        q += " AND status=?"
        p.append(status)
    if customer_id:
        q += " AND customer_id=?"
        p.append(customer_id)
    if dealer_id:
        q += " AND dealer_id=?"
        p.append(dealer_id)
    q += " ORDER BY id DESC"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [_rof(r) for r in rows]


def get_recent_offers(limit=10, dealer_id=None, manufacturer_id=None):
    with _c() as c:
        if manufacturer_id:
            rows = c.execute(
                f"SELECT {_OFCOLS} FROM offers WHERE manufacturer_id=? ORDER BY id DESC LIMIT ?",
                (manufacturer_id, limit)
            ).fetchall()
        elif dealer_id:
            rows = c.execute(
                f"SELECT {_OFCOLS} FROM offers WHERE dealer_id=? ORDER BY id DESC LIMIT ?",
                (dealer_id, limit)
            ).fetchall()
        else:
            rows = c.execute(
                f"SELECT {_OFCOLS} FROM offers ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    return [_rof(r) for r in rows]


def get_offer(oid):
    with _c() as c:
        r = c.execute(f"SELECT {_OFCOLS} FROM offers WHERE id=?", (oid,)).fetchone()
    return _rof(r) if r else None


def get_delivery_terms(active_only=False):
    q = "SELECT id,name,discount_pct,sort_order,is_active FROM delivery_terms"
    if active_only:
        q += " WHERE is_active=1"
    q += " ORDER BY sort_order,id"
    with _c() as c:
        rows = c.execute(q).fetchall()
    return [dict(id=r[0], name=r[1], discount_pct=r[2], sort_order=r[3], is_active=r[4]) for r in rows]


def add_delivery_term(name, discount_pct=0, sort_order=0):
    with _c() as c:
        c.execute("INSERT INTO delivery_terms(name,discount_pct,sort_order) VALUES(?,?,?)",
                  (name, discount_pct, sort_order))


def upd_delivery_term(tid, name, discount_pct, sort_order, is_active):
    with _c() as c:
        c.execute("UPDATE delivery_terms SET name=?,discount_pct=?,sort_order=?,is_active=? WHERE id=?",
                  (name, discount_pct, sort_order, is_active, tid))


def del_delivery_term(tid):
    with _c() as c:
        c.execute("DELETE FROM delivery_terms WHERE id=?", (tid,))


def get_delivery_term(tid):
    with _c() as c:
        r = c.execute("SELECT id,name,discount_pct,sort_order,is_active FROM delivery_terms WHERE id=?", (tid,)).fetchone()
    return dict(id=r[0], name=r[1], discount_pct=r[2], sort_order=r[3], is_active=r[4]) if r else None


def create_offer(**kw):
    allowed = ["offer_no", "customer_id", "model_id", "machine_count", "currency",
               "base_price", "options_total", "discount_pct", "total_price",
               "status", "notes", "validity_date", "dealer_id",
               "delivery_method", "delivery_time", "logistics", "payment_notes",
               "delivery_term_id", "delivery_term_discount"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO offers({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_offer_status(oid, status):
    with _c() as c:
        c.execute("UPDATE offers SET status=? WHERE id=?", (status, oid))


def cancel_offer(oid, reason):
    with _c() as c:
        c.execute("UPDATE offers SET status='İptal', cancel_reason=? WHERE id=?", (reason, oid))


def dealer_approve_offer(oid, notes="", photo=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET status='Sipariş Verildi', contract_notes=?, contract_photo=? WHERE id=?",
            (notes, photo, oid)
        )


def save_change_request(offer_id, dealer_id, description):
    with _c() as c:
        c.execute(
            "INSERT INTO change_requests(offer_id, dealer_id, description) VALUES(?,?,?)",
            (offer_id, dealer_id, description)
        )
        return c.lastrowid


def get_change_requests(offer_id=None, status=None):
    with _c() as c:
        q = "SELECT id, offer_id, dealer_id, description, status, admin_notes, created_at FROM change_requests WHERE 1=1"
        p = []
        if offer_id:
            q += " AND offer_id=?"
            p.append(offer_id)
        if status:
            q += " AND status=?"
            p.append(status)
        q += " ORDER BY id DESC"
        rows = c.execute(q, p).fetchall()
    keys = ["id", "offer_id", "dealer_id", "description", "status", "admin_notes", "created_at"]
    return [dict(zip(keys, r)) for r in rows]


def resolve_change_request(req_id, status, admin_notes=""):
    with _c() as c:
        c.execute(
            "UPDATE change_requests SET status=?, admin_notes=? WHERE id=?",
            (status, admin_notes, req_id)
        )


def upd_offer(oid, **kw):
    allowed = ["customer_id", "model_id", "machine_count", "currency",
               "base_price", "options_total", "discount_pct", "total_price",
               "status", "notes", "validity_date",
               "delivery_method", "delivery_time", "logistics", "payment_notes",
               "delivery_term_id", "delivery_term_discount"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE offers SET {sets} WHERE id=?", list(f.values()) + [oid])


def del_offer(oid):
    with _c() as c:
        c.execute("DELETE FROM offers WHERE id=?", (oid,))
        c.execute("DELETE FROM offer_items WHERE offer_id=?", (oid,))


# ── Offer Items ───────────────────────────────────────────────────────────────

def save_offer_items(offer_id, items):
    with _c() as c:
        c.execute("DELETE FROM offer_items WHERE offer_id=?", (offer_id,))
        for it in items:
            c.execute(
                "INSERT INTO offer_items(offer_id,option_id,qty,unit_price,line_total) VALUES(?,?,?,?,?)",
                (offer_id, it.get("option_id", 0), it.get("qty", 1),
                 it.get("unit_price", 0), it.get("line_total", 0)),
            )


def get_offer_items(offer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,offer_id,option_id,qty,unit_price,line_total FROM offer_items WHERE offer_id=?",
            (offer_id,),
        ).fetchall()
    return [{"id": r[0], "offer_id": r[1], "option_id": r[2],
             "qty": r[3], "unit_price": r[4], "line_total": r[5]} for r in rows]


# ── Customer Ledger ───────────────────────────────────────────────────────────

def add_ctxn(customer_id, txn_type, amount, currency="USD",
             description="", payment_method="", txn_date=""):
    with _c() as c:
        cur = c.execute(
            "INSERT INTO customer_transactions(customer_id,txn_type,amount,currency,description,payment_method,txn_date) VALUES(?,?,?,?,?,?,?)",
            (customer_id, txn_type, amount, currency, description, payment_method, txn_date),
        )
        return cur.lastrowid


def get_ctxns(customer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,customer_id,txn_type,amount,currency,description,payment_method,txn_date,created_at FROM customer_transactions WHERE customer_id=? ORDER BY txn_date DESC,id DESC",
            (customer_id,),
        ).fetchall()
    return [{"id": r[0], "customer_id": r[1], "txn_type": r[2], "amount": r[3],
             "currency": r[4], "description": r[5], "payment_method": r[6],
             "txn_date": r[7], "created_at": r[8]} for r in rows]


def del_ctxn(tid):
    with _c() as c:
        c.execute("DELETE FROM customer_transactions WHERE id=?", (tid,))


def cust_balance(customer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT txn_type,SUM(amount) FROM customer_transactions WHERE customer_id=? GROUP BY txn_type",
            (customer_id,),
        ).fetchall()
    totals = {"debit": 0.0, "credit": 0.0}
    for txn_type, total in rows:
        if txn_type in totals:
            totals[txn_type] = float(total or 0)
    return totals["debit"] - totals["credit"]


def all_cust_balances():
    with _c() as c:
        rows = c.execute(
            "SELECT customer_id,txn_type,SUM(amount) FROM customer_transactions GROUP BY customer_id,txn_type"
        ).fetchall()
    balances = {}
    for cid, txn_type, total in rows:
        if cid not in balances:
            balances[cid] = {"debit": 0.0, "credit": 0.0}
        if txn_type in balances[cid]:
            balances[cid][txn_type] = float(total or 0)
    return {cid: v["debit"] - v["credit"] for cid, v in balances.items()}


# ── Manufacturer Ledger ───────────────────────────────────────────────────────

def add_mtxn(manufacturer_name, txn_type, amount, currency="USD",
             description="", txn_date=""):
    with _c() as c:
        cur = c.execute(
            "INSERT INTO manufacturer_transactions(manufacturer_name,txn_type,amount,currency,description,txn_date) VALUES(?,?,?,?,?,?)",
            (manufacturer_name, txn_type, amount, currency, description, txn_date),
        )
        return cur.lastrowid


def get_mtxns(manufacturer_name=None):
    q = "SELECT id,manufacturer_name,txn_type,amount,currency,description,txn_date,created_at FROM manufacturer_transactions WHERE 1=1"
    p = []
    if manufacturer_name:
        q += " AND manufacturer_name=?"
        p.append(manufacturer_name)
    q += " ORDER BY txn_date DESC,id DESC"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [{"id": r[0], "manufacturer_name": r[1], "txn_type": r[2], "amount": r[3],
             "currency": r[4], "description": r[5], "txn_date": r[6], "created_at": r[7]}
            for r in rows]


def del_mtxn(tid):
    with _c() as c:
        c.execute("DELETE FROM manufacturer_transactions WHERE id=?", (tid,))


def mfr_balance(manufacturer_name):
    with _c() as c:
        rows = c.execute(
            "SELECT txn_type,SUM(amount) FROM manufacturer_transactions WHERE manufacturer_name=? GROUP BY txn_type",
            (manufacturer_name,),
        ).fetchall()
    totals = {"purchase": 0.0, "payment": 0.0}
    for txn_type, total in rows:
        if txn_type in totals:
            totals[txn_type] = float(total or 0)
    return totals["purchase"] - totals["payment"]


# ── Order Workflow ────────────────────────────────────────────────────────────

def approve_order(oid, manufacturer_id, admin_notes=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET admin_status='approved', manufacturer_id=?, admin_notes=?, status='Admin Onaylı' WHERE id=?",
            (manufacturer_id, admin_notes, oid)
        )

def reassign_order_manufacturer(oid, manufacturer_id):
    with _c() as c:
        c.execute("UPDATE offers SET manufacturer_id=? WHERE id=?", (manufacturer_id, oid))

def reject_order(oid, admin_notes=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET admin_status='rejected', admin_notes=?, status='İptal' WHERE id=?",
            (admin_notes, oid)
        )

def mfr_confirm_order(oid, termin_date, mfr_notes="", serial_number=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET mfr_status='confirmed', termin_date=?, mfr_notes=?, serial_number=?, status='Üretimde' WHERE id=?",
            (termin_date, mfr_notes, serial_number, oid)
        )

def update_mfr_status(oid, mfr_status, mfr_status_date=""):
    steps = get_production_steps(active_only=False)
    step = next((s for s in steps if s["code"] == mfr_status), None)
    status_tr = step["label_tr"] if step else mfr_status
    with _c() as c:
        c.execute(
            "UPDATE offers SET mfr_status=?, status=?, mfr_status_date=? WHERE id=?",
            (mfr_status, status_tr, mfr_status_date, oid)
        )


def get_production_steps(active_only=True):
    q = "SELECT id,code,label_tr,label_en,label_zh,sort_order,is_active FROM production_steps"
    if active_only:
        q += " WHERE is_active=1"
    q += " ORDER BY sort_order,id"
    try:
        with _c() as c:
            rows = c.execute(q).fetchall()
        keys = ["id","code","label_tr","label_en","label_zh","sort_order","is_active"]
        return [dict(zip(keys,r)) for r in rows]
    except Exception:
        return []

def save_production_step(id, code, label_tr, label_en, label_zh, sort_order, is_active=1):
    with _c() as c:
        if id:
            c.execute(
                "UPDATE production_steps SET code=?,label_tr=?,label_en=?,label_zh=?,sort_order=?,is_active=? WHERE id=?",
                (code, label_tr, label_en, label_zh, sort_order, is_active, id)
            )
        else:
            c.execute(
                "INSERT INTO production_steps(code,label_tr,label_en,label_zh,sort_order,is_active) VALUES(?,?,?,?,?,?)",
                (code, label_tr, label_en, label_zh, sort_order, is_active)
            )

def del_production_step(id):
    with _c() as c:
        c.execute("DELETE FROM production_steps WHERE id=?", (id,))


# ── Order Stages ─────────────────────────────────────────────────────────────

def add_order_stage(order_id, stage_name, notes, stage_date, photo=""):
    with _c() as c:
        c.execute(
            "INSERT INTO order_stages(order_id,stage_name,notes,stage_date,photo) VALUES(?,?,?,?,?)",
            (order_id, stage_name, notes, stage_date, photo)
        )

def get_order_stages(order_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,order_id,stage_name,notes,stage_date,created_at,photo FROM order_stages WHERE order_id=? ORDER BY stage_date DESC,id DESC",
            (order_id,)
        ).fetchall()
    return [{"id":r[0],"order_id":r[1],"stage_name":r[2],"notes":r[3],"stage_date":r[4],"created_at":r[5],"photo":r[6] or ""} for r in rows]

def del_order_stage(sid):
    with _c() as c:
        c.execute("DELETE FROM order_stages WHERE id=?", (sid,))


# ── Dealer Ledger ─────────────────────────────────────────────────────────────

def add_dealer_txn(dealer_id, txn_type, amount, currency="USD",
                   description="", payment_method="", txn_date="", order_id=None):
    with _c() as c:
        c.execute(
            "INSERT INTO dealer_ledger(dealer_id,txn_type,amount,currency,description,payment_method,txn_date,order_id) VALUES(?,?,?,?,?,?,?,?)",
            (dealer_id, txn_type, amount, currency, description, payment_method, txn_date, order_id)
        )

def get_dealer_txns(dealer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,dealer_id,txn_type,amount,currency,description,payment_method,txn_date,order_id,created_at FROM dealer_ledger WHERE dealer_id=? ORDER BY txn_date DESC,id DESC",
            (dealer_id,)
        ).fetchall()
    return [{"id":r[0],"dealer_id":r[1],"txn_type":r[2],"amount":r[3],"currency":r[4],
             "description":r[5],"payment_method":r[6],"txn_date":r[7],"order_id":r[8],"created_at":r[9]} for r in rows]

def del_dealer_txn(tid):
    with _c() as c:
        c.execute("DELETE FROM dealer_ledger WHERE id=?", (tid,))

def dealer_balance(dealer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT txn_type,SUM(amount) FROM dealer_ledger WHERE dealer_id=? GROUP BY txn_type",
            (dealer_id,)
        ).fetchall()
    totals = {"debit": 0.0, "credit": 0.0}
    for txn_type, total in rows:
        if txn_type in totals:
            totals[txn_type] = float(total or 0)
    return totals["debit"] - totals["credit"]

def all_dealer_balances():
    with _c() as c:
        rows = c.execute(
            "SELECT dealer_id,txn_type,SUM(amount) FROM dealer_ledger GROUP BY dealer_id,txn_type"
        ).fetchall()
    balances = {}
    for did, txn_type, total in rows:
        if did not in balances:
            balances[did] = {"debit": 0.0, "credit": 0.0}
        if txn_type in balances[did]:
            balances[did][txn_type] = float(total or 0)
    return {did: v["debit"] - v["credit"] for did, v in balances.items()}


# ── Manufacturer User Ledger ──────────────────────────────────────────────────

def add_mfr_user_txn(manufacturer_id, txn_type, amount, currency="USD",
                     description="", payment_method="", txn_date="", order_id=None):
    with _c() as c:
        c.execute(
            "INSERT INTO manufacturer_user_ledger(manufacturer_id,txn_type,amount,currency,description,payment_method,txn_date,order_id) VALUES(?,?,?,?,?,?,?,?)",
            (manufacturer_id, txn_type, amount, currency, description, payment_method, txn_date, order_id)
        )

def get_mfr_user_txns(manufacturer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,manufacturer_id,txn_type,amount,currency,description,payment_method,txn_date,order_id,created_at FROM manufacturer_user_ledger WHERE manufacturer_id=? ORDER BY txn_date DESC,id DESC",
            (manufacturer_id,)
        ).fetchall()
    return [{"id":r[0],"manufacturer_id":r[1],"txn_type":r[2],"amount":r[3],"currency":r[4],
             "description":r[5],"payment_method":r[6],"txn_date":r[7],"order_id":r[8],"created_at":r[9]} for r in rows]

def del_mfr_user_txn(tid):
    with _c() as c:
        c.execute("DELETE FROM manufacturer_user_ledger WHERE id=?", (tid,))

def mfr_user_balance(manufacturer_id):
    with _c() as c:
        rows = c.execute(
            "SELECT txn_type,SUM(amount) FROM manufacturer_user_ledger WHERE manufacturer_id=? GROUP BY txn_type",
            (manufacturer_id,)
        ).fetchall()
    totals = {"debit": 0.0, "credit": 0.0}
    for txn_type, total in rows:
        if txn_type in totals:
            totals[txn_type] = float(total or 0)
    return totals["debit"] - totals["credit"]

def all_mfr_user_balances():
    with _c() as c:
        rows = c.execute(
            "SELECT manufacturer_id,txn_type,SUM(amount) FROM manufacturer_user_ledger GROUP BY manufacturer_id,txn_type"
        ).fetchall()
    balances = {}
    for mid, txn_type, total in rows:
        if mid not in balances:
            balances[mid] = {"debit": 0.0, "credit": 0.0}
        if txn_type in balances[mid]:
            balances[mid][txn_type] = float(total or 0)
    return {mid: v["debit"] - v["credit"] for mid, v in balances.items()}


# ── Stats ─────────────────────────────────────────────────────────────────────


def get_stats(dealer_id=None, manufacturer_id=None):
    with _c() as c:
        if manufacturer_id:
            customer_count = c.execute(
                "SELECT COUNT(DISTINCT customer_id) FROM offers WHERE manufacturer_id=?", (manufacturer_id,)
            ).fetchone()[0]
            offer_count = c.execute(
                "SELECT COUNT(*) FROM offers WHERE manufacturer_id=? AND status NOT IN ('Beklemede')", (manufacturer_id,)
            ).fetchone()[0]
            pending_offers = c.execute(
                "SELECT COUNT(*) FROM offers WHERE manufacturer_id=? AND admin_status='approved' AND (mfr_status IS NULL OR mfr_status='')",
                (manufacturer_id,)
            ).fetchone()[0]
            order_count = c.execute(
                "SELECT COUNT(*) FROM offers WHERE manufacturer_id=? AND mfr_status='in_production'", (manufacturer_id,)
            ).fetchone()[0]
        elif dealer_id:
            customer_count = c.execute(
                "SELECT COUNT(DISTINCT customer_id) FROM offers WHERE dealer_id=?", (dealer_id,)
            ).fetchone()[0]
            offer_count = c.execute(
                "SELECT COUNT(*) FROM offers WHERE dealer_id=?", (dealer_id,)
            ).fetchone()[0]
            pending_offers = c.execute(
                "SELECT COUNT(*) FROM offers WHERE dealer_id=? AND status='Beklemede'", (dealer_id,)
            ).fetchone()[0]
            order_count = c.execute(
                "SELECT COUNT(*) FROM offers WHERE dealer_id=? AND status='Sipariş Verildi'", (dealer_id,)
            ).fetchone()[0]
        else:
            customer_count = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            offer_count = c.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
            pending_offers = c.execute(
                "SELECT COUNT(*) FROM offers WHERE status='Beklemede'"
            ).fetchone()[0]
            order_count = c.execute(
                "SELECT COUNT(*) FROM offers WHERE status='Sipariş Verildi'"
            ).fetchone()[0]
    return {
        "customer_count": customer_count,
        "offer_count": offer_count,
        "pending_offers": pending_offers,
        "order_count": order_count,
    }


# ── Membrane Cost Calculator ──────────────────────────────────────────────────

def _init_membrane(c):
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_materials(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        material_type TEXT DEFAULT 'other',
        price REAL DEFAULT 0,
        currency TEXT DEFAULT 'TRY',
        unit TEXT DEFAULT 'm2',
        sheet_width REAL DEFAULT 0,
        sheet_height REAL DEFAULT 0,
        usage_per_m2 REAL DEFAULT 1,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_doors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT DEFAULT '',
        door_name TEXT DEFAULT '',
        width_mm REAL NOT NULL,
        height_mm REAL NOT NULL,
        quantity INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_rates(
        currency TEXT PRIMARY KEY,
        rate_to_try REAL NOT NULL DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    for cur in ['USD', 'EUR', 'GBP']:
        if not c.execute("SELECT 1 FROM membrane_rates WHERE currency=?", (cur,)).fetchone():
            c.execute("INSERT INTO membrane_rates(currency,rate_to_try) VALUES(?,1)", (cur,))
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_lists(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    _acol(c, "membrane_doors", "list_id", "INTEGER DEFAULT NULL")

    # Parametric cap macro tables
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_models(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        tool_no INTEGER DEFAULT 1,
        spindle_speed INTEGER DEFAULT 18000,
        feed_xy INTEGER DEFAULT 3000,
        feed_z INTEGER DEFAULT 1000,
        safe_z REAL DEFAULT 5.0,
        constants_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_paths(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER NOT NULL REFERENCES membrane_cap_models(id) ON DELETE CASCADE,
        seq INTEGER DEFAULT 0,
        label TEXT DEFAULT '',
        path_type TEXT DEFAULT 'LINE',
        x1 TEXT DEFAULT '0', y1 TEXT DEFAULT '0', z1 TEXT DEFAULT '0',
        x2 TEXT DEFAULT 'W', y2 TEXT DEFAULT 'H', z2 TEXT DEFAULT '-T',
        ix TEXT DEFAULT '0', jy TEXT DEFAULT '0',
        tool_dia REAL DEFAULT 8.0,
        step_over REAL DEFAULT 0.5,
        feed_override TEXT DEFAULT ''
    )""")
    # Add tool_no to paths (0 = inherit from model)
    _acol(c, "membrane_cap_paths", "tool_no", "INTEGER DEFAULT 0")

    # Structured ops/moves tables (new path editor)
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_ops(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER NOT NULL REFERENCES membrane_cap_models(id) ON DELETE CASCADE,
        name TEXT DEFAULT '',
        tool_no INTEGER DEFAULT 1,
        depth TEXT DEFAULT '-T',
        feed TEXT DEFAULT '',
        ref_corner TEXT DEFAULT 'BL',
        seq INTEGER DEFAULT 0,
        op_type TEXT DEFAULT 'inner'
    )""")
    _acol(c, "membrane_cap_ops", "op_type",      "TEXT DEFAULT 'inner'")
    _acol(c, "membrane_cap_ops", "tool_id",      "INTEGER")
    _acol(c, "membrane_cap_ops", "comp_mode",    "TEXT DEFAULT 'none'")
    _acol(c, "membrane_cap_ops", "offset_side",  "TEXT DEFAULT 'center'")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_tools(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tool_no INTEGER DEFAULT 1,
        diameter REAL DEFAULT 6.0,
        length REAL DEFAULT 0,
        feed_xy INTEGER DEFAULT 3000,
        feed_z INTEGER DEFAULT 1000,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_moves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        op_id INTEGER NOT NULL REFERENCES membrane_cap_ops(id) ON DELETE CASCADE,
        move_type TEXT DEFAULT 'line',
        x TEXT DEFAULT '0',
        y TEXT DEFAULT '0',
        cx TEXT DEFAULT '0',
        cy TEXT DEFAULT '0',
        r TEXT DEFAULT '0',
        seq INTEGER DEFAULT 0
    )""")
    _acol(c, "membrane_cap_moves", "r", "TEXT DEFAULT '0'")

    # Job list tables
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        notes TEXT DEFAULT '',
        sheet_w REAL DEFAULT 2800,
        sheet_h REAL DEFAULT 1100,
        margin REAL DEFAULT 5,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS membrane_cap_job_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES membrane_cap_jobs(id) ON DELETE CASCADE,
        model_id INTEGER DEFAULT NULL,
        model_name TEXT DEFAULT '',
        cap_w REAL NOT NULL DEFAULT 400,
        cap_h REAL NOT NULL DEFAULT 600,
        qty INTEGER DEFAULT 1,
        notes TEXT DEFAULT '',
        seq INTEGER DEFAULT 0
    )""")


def get_membrane_materials():
    with _c() as c:
        rows = c.execute("SELECT id,name,material_type,price,currency,unit,sheet_width,sheet_height,usage_per_m2,notes FROM membrane_materials ORDER BY material_type,name").fetchall()
    cols = ["id","name","material_type","price","currency","unit","sheet_width","sheet_height","usage_per_m2","notes"]
    return [dict(zip(cols, r)) for r in rows]

def save_membrane_material(id=None, **kw):
    fields = ["name","material_type","price","currency","unit","sheet_width","sheet_height","usage_per_m2","notes"]
    numeric = {"price","sheet_width","sheet_height","usage_per_m2"}
    vals = [float(kw.get(f, 0)) if f in numeric else kw.get(f, "") for f in fields]
    with _c() as c:
        cur = c.cursor()
        if id:
            sets = ",".join(f"{f}=?" for f in fields)
            cur.execute(f"UPDATE membrane_materials SET {sets} WHERE id=?", vals + [id])
        else:
            cols = ",".join(fields)
            phs = ",".join("?" for _ in fields)
            cur.execute(f"INSERT INTO membrane_materials({cols}) VALUES({phs})", vals)
            id = cur.lastrowid
        c.commit()
    return id

def del_membrane_material(mid):
    with _c() as c:
        c.execute("DELETE FROM membrane_materials WHERE id=?", (mid,))

def get_membrane_doors():
    with _c() as c:
        rows = c.execute("SELECT id,project_name,door_name,width_mm,height_mm,quantity FROM membrane_doors ORDER BY id").fetchall()
    cols = ["id","project_name","door_name","width_mm","height_mm","quantity"]
    return [dict(zip(cols, r)) for r in rows]

def save_membrane_door(id=None, **kw):
    fields = ["project_name","door_name","width_mm","height_mm","quantity","list_id"]
    vals = [
        kw.get("project_name", ""),
        kw.get("door_name", ""),
        float(kw.get("width_mm", 0)),
        float(kw.get("height_mm", 0)),
        int(kw.get("quantity", 1)),
        kw.get("list_id", None),
    ]
    with _c() as c:
        cur = c.cursor()
        if id:
            sets = ",".join(f"{f}=?" for f in fields)
            cur.execute(f"UPDATE membrane_doors SET {sets} WHERE id=?", vals + [id])
        else:
            cols = ",".join(fields)
            phs = ",".join("?" for _ in fields)
            cur.execute(f"INSERT INTO membrane_doors({cols}) VALUES({phs})", vals)
        c.commit()

def del_membrane_door(did):
    with _c() as c:
        c.execute("DELETE FROM membrane_doors WHERE id=?", (did,))

def get_membrane_lists():
    with _c() as c:
        rows = c.execute("""
            SELECT ml.id, ml.name, ml.notes, ml.created_at,
                   COUNT(md.id) as door_count,
                   COALESCE(SUM(md.quantity), 0) as total_qty
            FROM membrane_lists ml
            LEFT JOIN membrane_doors md ON md.list_id = ml.id
            GROUP BY ml.id ORDER BY ml.id DESC
        """).fetchall()
    cols = ["id","name","notes","created_at","door_count","total_qty"]
    return [dict(zip(cols, r)) for r in rows]

def get_membrane_list(lid):
    with _c() as c:
        r = c.execute("SELECT id,name,notes,created_at FROM membrane_lists WHERE id=?", (lid,)).fetchone()
    return dict(zip(["id","name","notes","created_at"], r)) if r else None

def save_membrane_list(id=None, name="", notes=""):
    with _c() as c:
        cur = c.cursor()
        if id:
            cur.execute("UPDATE membrane_lists SET name=?,notes=? WHERE id=?", (name, notes, id))
        else:
            cur.execute("INSERT INTO membrane_lists(name,notes) VALUES(?,?)", (name, notes))
            id = cur.lastrowid
        c.commit()
    return id

def del_membrane_list(lid):
    with _c() as c:
        c.execute("DELETE FROM membrane_doors WHERE list_id=?", (lid,))
        c.execute("DELETE FROM membrane_lists WHERE id=?", (lid,))

def get_membrane_doors_by_list(lid):
    with _c() as c:
        rows = c.execute(
            "SELECT id,project_name,door_name,width_mm,height_mm,quantity FROM membrane_doors WHERE list_id=? ORDER BY id",
            (lid,)
        ).fetchall()
    cols = ["id","project_name","door_name","width_mm","height_mm","quantity"]
    return [dict(zip(cols, r)) for r in rows]

def get_membrane_rates():
    with _c() as c:
        rows = c.execute("SELECT currency,rate_to_try,updated_at FROM membrane_rates").fetchall()
    return {r[0]: {"rate": r[1], "updated_at": r[2]} for r in rows}

def set_membrane_rate(currency, rate):
    with _c() as c:
        c.execute("INSERT OR REPLACE INTO membrane_rates(currency,rate_to_try,updated_at) VALUES(?,?,datetime('now'))", (currency, rate))


# ── Parametric Cap Models ─────────────────────────────────────────────────────

_CM_KEYS = ["id","name","description","tool_no","spindle_speed","feed_xy","feed_z","safe_z","constants_json","created_at"]
_CM_COLS = ",".join(_CM_KEYS)
_CP_KEYS = ["id","model_id","seq","label","path_type","x1","y1","z1","x2","y2","z2","ix","jy","tool_dia","step_over","feed_override","tool_no"]
_CP_COLS = ",".join(_CP_KEYS)


def get_cap_models():
    with _c() as c:
        rows = c.execute(f"SELECT {_CM_COLS} FROM membrane_cap_models ORDER BY name").fetchall()
    return [dict(zip(_CM_KEYS, r)) for r in rows]


def get_cap_model(mid):
    with _c() as c:
        r = c.execute(f"SELECT {_CM_COLS} FROM membrane_cap_models WHERE id=?", (mid,)).fetchone()
    if not r:
        return None
    m = dict(zip(_CM_KEYS, r))
    try:
        m["constants"] = json.loads(m["constants_json"] or "{}")
    except Exception:
        m["constants"] = {}
    return m


def save_cap_model(id=0, **kw):
    allowed = ["name","description","tool_no","spindle_speed","feed_xy","feed_z","safe_z","constants_json"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_models SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys())
        ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_models({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def del_cap_model(mid):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_models WHERE id=?", (mid,))


def get_cap_paths(model_id):
    with _c() as c:
        rows = c.execute(f"SELECT {_CP_COLS} FROM membrane_cap_paths WHERE model_id=? ORDER BY seq,id", (model_id,)).fetchall()
    return [dict(zip(_CP_KEYS, r)) for r in rows]


def save_cap_path(id=0, **kw):
    allowed = ["model_id","seq","label","path_type","x1","y1","z1","x2","y2","z2","ix","jy","tool_dia","step_over","feed_override","tool_no"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_paths SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys())
        ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_paths({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def del_cap_path(pid):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_paths WHERE id=?", (pid,))


# ── Cap Job List ──────────────────────────────────────────────────────────────

_CJ_KEYS  = ["id","name","notes","sheet_w","sheet_h","margin","created_at"]
_CJ_COLS  = ",".join(_CJ_KEYS)
_CJI_KEYS = ["id","job_id","model_id","model_name","cap_w","cap_h","qty","notes","seq"]
_CJI_COLS = ",".join(_CJI_KEYS)


def get_cap_jobs():
    with _c() as c:
        rows = c.execute(f"""
            SELECT cj.id,cj.name,cj.notes,cj.sheet_w,cj.sheet_h,cj.margin,cj.created_at,
                   COUNT(cji.id) AS item_count, COALESCE(SUM(cji.qty),0) AS total_qty
            FROM membrane_cap_jobs cj
            LEFT JOIN membrane_cap_job_items cji ON cji.job_id=cj.id
            GROUP BY cj.id ORDER BY cj.id DESC
        """).fetchall()
    keys = _CJ_KEYS + ["item_count","total_qty"]
    return [dict(zip(keys, r)) for r in rows]


def get_cap_job(jid):
    with _c() as c:
        r = c.execute(f"SELECT {_CJ_COLS} FROM membrane_cap_jobs WHERE id=?", (jid,)).fetchone()
    return dict(zip(_CJ_KEYS, r)) if r else None


def save_cap_job(id=0, **kw):
    allowed = ["name","notes","sheet_w","sheet_h","margin"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_jobs SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys()); ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_jobs({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def del_cap_job(jid):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_jobs WHERE id=?", (jid,))


def get_cap_job_items(jid):
    with _c() as c:
        rows = c.execute(
            f"SELECT {_CJI_COLS} FROM membrane_cap_job_items WHERE job_id=? ORDER BY seq,id",
            (jid,)
        ).fetchall()
    return [dict(zip(_CJI_KEYS, r)) for r in rows]


def save_cap_job_item(id=0, **kw):
    allowed = ["job_id","model_id","model_name","cap_w","cap_h","qty","notes","seq"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_job_items SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys()); ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_job_items({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def del_cap_job_item(item_id):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_job_items WHERE id=?", (item_id,))


# ── Cap Ops (structured path editor) ─────────────────────────────────────────

_COP_KEYS = ["id","model_id","name","tool_no","depth","feed","ref_corner","seq","op_type","tool_id","comp_mode","offset_side"]
_CMV_KEYS = ["id","op_id","move_type","x","y","cx","cy","r","seq"]

# ── Tool Library ──────────────────────────────────────────────────────────────
_TOOL_KEYS = ["id","name","tool_no","diameter","length","feed_xy","feed_z","notes"]

def get_tools():
    with _c() as c:
        rows = c.execute(
            "SELECT id,name,tool_no,diameter,length,feed_xy,feed_z,notes FROM membrane_tools ORDER BY tool_no,name"
        ).fetchall()
    return [dict(zip(_TOOL_KEYS, r)) for r in rows]

def get_tool(tid):
    with _c() as c:
        r = c.execute(
            "SELECT id,name,tool_no,diameter,length,feed_xy,feed_z,notes FROM membrane_tools WHERE id=?", (tid,)
        ).fetchone()
    return dict(zip(_TOOL_KEYS, r)) if r else None

def save_tool(id=0, **kw):
    allowed = ["name","tool_no","diameter","length","feed_xy","feed_z","notes"]
    f = {k: v for k, v in kw.items() if k in allowed}
    conn = sqlite3.connect(FACTORY_DB, isolation_level=None, check_same_thread=False)
    try:
        cur = conn.cursor()
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            cur.execute(f"UPDATE membrane_tools SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys()); ph = ",".join("?" * len(f))
        cur.execute(f"INSERT INTO membrane_tools({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid
    finally:
        conn.close()

def del_tool(tid):
    conn = sqlite3.connect(FACTORY_DB, isolation_level=None, check_same_thread=False)
    try:
        conn.execute("DELETE FROM membrane_tools WHERE id=?", (tid,))
    finally:
        conn.close()


def get_cap_moves(op_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,op_id,move_type,x,y,cx,cy,r,seq FROM membrane_cap_moves WHERE op_id=? ORDER BY seq",
            (op_id,)
        ).fetchall()
    return [dict(zip(_CMV_KEYS, r)) for r in rows]

def get_cap_ops(model_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,model_id,name,tool_no,depth,feed,ref_corner,seq,op_type,tool_id,comp_mode,offset_side"
            " FROM membrane_cap_ops WHERE model_id=? ORDER BY seq",
            (model_id,)
        ).fetchall()
    ops = [dict(zip(_COP_KEYS, r)) for r in rows]
    for op in ops:
        op['moves'] = get_cap_moves(op['id'])
    return ops

def save_cap_op(id=0, **kw):
    allowed = ["model_id","name","tool_no","depth","feed","ref_corner","seq","op_type","tool_id","comp_mode","offset_side"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_ops SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys()); ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_ops({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid

def del_cap_op(op_id):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_ops WHERE id=?", (op_id,))

def save_cap_move(id=0, **kw):
    allowed = ["op_id","move_type","x","y","cx","cy","r","seq"]
    f = {k: v for k, v in kw.items() if k in allowed}
    with _c() as c:
        if id:
            sets = ",".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE membrane_cap_moves SET {sets} WHERE id=?", list(f.values()) + [id])
            return id
        cols = ",".join(f.keys()); ph = ",".join("?" * len(f))
        cur = c.execute(f"INSERT INTO membrane_cap_moves({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid

def del_cap_move(move_id):
    with _c() as c:
        c.execute("DELETE FROM membrane_cap_moves WHERE id=?", (move_id,))


# ── Deletion Requests ──────────────────────────────────────────────────────

def add_deletion_request(item_type, item_id, item_name, requested_by):
    with _c() as c:
        c.execute(
            "INSERT INTO deletion_requests(item_type,item_id,item_name,requested_by) VALUES(?,?,?,?)",
            (item_type, item_id, item_name, requested_by)
        )

def get_deletion_requests(status=None):
    with _c() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM deletion_requests WHERE status=? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM deletion_requests ORDER BY created_at DESC"
            ).fetchall()
    keys = ["id","item_type","item_id","item_name","requested_by","status","created_at","resolved_at"]
    return [dict(zip(keys, r)) for r in rows]

def resolve_deletion_request(req_id, status):
    with _c() as c:
        c.execute(
            "UPDATE deletion_requests SET status=?, resolved_at=datetime('now') WHERE id=?",
            (status, req_id)
        )


# ── Price Change Requests ──────────────────────────────────────────────────────

_PRCOLS = "id,entity_type,entity_id,entity_name,manufacturer_id,current_price,new_price,currency,note,status,admin_note,created_at,resolved_at"
_PRKEYS = ["id","entity_type","entity_id","entity_name","manufacturer_id","current_price","new_price","currency","note","status","admin_note","created_at","resolved_at"]


def _rpr(r):
    return dict(zip(_PRKEYS, r))


def add_price_request(entity_type, entity_id, entity_name, manufacturer_id, current_price, new_price, currency, note=""):
    with _c() as c:
        cur = c.execute(
            "INSERT INTO price_requests(entity_type,entity_id,entity_name,manufacturer_id,current_price,new_price,currency,note) VALUES(?,?,?,?,?,?,?,?)",
            (entity_type, entity_id, entity_name, manufacturer_id, current_price, new_price, currency, note)
        )
        return cur.lastrowid


def get_price_requests(status=None, manufacturer_id=None):
    q = f"SELECT {_PRCOLS} FROM price_requests WHERE 1=1"
    p = []
    if status:
        q += " AND status=?"
        p.append(status)
    if manufacturer_id:
        q += " AND manufacturer_id=?"
        p.append(manufacturer_id)
    q += " ORDER BY created_at DESC"
    with _c() as c:
        rows = c.execute(q, p).fetchall()
    return [_rpr(r) for r in rows]


def get_price_request(rid):
    with _c() as c:
        r = c.execute(f"SELECT {_PRCOLS} FROM price_requests WHERE id=?", (rid,)).fetchone()
    return _rpr(r) if r else None


def resolve_price_request(rid, status, admin_note=""):
    with _c() as c:
        c.execute(
            "UPDATE price_requests SET status=?,admin_note=?,resolved_at=datetime('now') WHERE id=?",
            (status, admin_note, rid)
        )


def pending_price_requests_count():
    try:
        with _c() as c:
            return c.execute("SELECT COUNT(*) FROM price_requests WHERE status='pending'").fetchone()[0]
    except Exception:
        return 0


# ── Order Proformas & Documents ───────────────────────────────────────────────

def get_order_proformas(order_id):
    try:
        with _c() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM order_proformas WHERE order_id=? ORDER BY uploaded_at DESC", (order_id,)
            )]
    except Exception:
        return []

def add_order_proforma(order_id, file_path, filename, uploaded_by=None):
    with _c() as c:
        c.execute(
            "INSERT INTO order_proformas(order_id,file_path,filename,uploaded_by) VALUES(?,?,?,?)",
            (order_id, file_path, filename, uploaded_by)
        )

def del_order_proforma(pid):
    with _c() as c:
        row = c.execute("SELECT file_path FROM order_proformas WHERE id=?", (pid,)).fetchone()
        c.execute("DELETE FROM order_proformas WHERE id=?", (pid,))
        return dict(row)["file_path"] if row else None

def get_order_documents(order_id):
    try:
        with _c() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM order_documents WHERE order_id=? ORDER BY uploaded_at DESC", (order_id,)
            )]
    except Exception:
        return []

def add_order_document(order_id, file_path, filename, doc_type="", uploaded_by=None):
    with _c() as c:
        c.execute(
            "INSERT INTO order_documents(order_id,file_path,filename,doc_type,uploaded_by) VALUES(?,?,?,?,?)",
            (order_id, file_path, filename, doc_type, uploaded_by)
        )

def del_order_document(did):
    with _c() as c:
        row = c.execute("SELECT file_path FROM order_documents WHERE id=?", (did,)).fetchone()
        c.execute("DELETE FROM order_documents WHERE id=?", (did,))
        return dict(row)["file_path"] if row else None

def set_order_serial(order_id, serial_number):
    with _c() as c:
        c.execute("UPDATE offers SET serial_number=? WHERE id=?", (serial_number, order_id))
