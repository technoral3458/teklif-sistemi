import sqlite3
import json
from config import FACTORY_DB


def _conn():
    return sqlite3.connect(FACTORY_DB, check_same_thread=False)


def _add_col(cur, table, col, typ):
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def init():
    with _conn() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS company_profile (
                id INTEGER PRIMARY KEY CHECK (id=1),
                company_name TEXT DEFAULT '',
                logo_path TEXT DEFAULT '',
                website TEXT DEFAULT '',
                footer_text TEXT DEFAULT ''
            )
        """)
        if not c.execute("SELECT id FROM company_profile WHERE id=1").fetchone():
            c.execute("INSERT INTO company_profile (id) VALUES (1)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                image_path TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model_code TEXT DEFAULT '',
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Genel',
                currency TEXT DEFAULT 'USD',
                base_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0,
                image_path TEXT DEFAULT '',
                gallery_images TEXT DEFAULT '[]',
                specs TEXT DEFAULT '[]',
                compatible_options TEXT DEFAULT '[]',
                manufacturer_id INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                purchase_price REAL DEFAULT 0.0,
                shipping_cost REAL DEFAULT 0.0,
                customs_tax_rate REAL DEFAULT 3.0,
                extra_tax_rate REAL DEFAULT 10.0,
                port_cost REAL DEFAULT 0.0,
                document_cost REAL DEFAULT 0.0,
                installation_cost REAL DEFAULT 0.0,
                other_cost REAL DEFAULT 0.0,
                cost_note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Genel',
                currency TEXT DEFAULT 'USD',
                list_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0,
                image_path TEXT DEFAULT '',
                variant_image_path TEXT DEFAULT '',
                qty_type TEXT DEFAULT 'MANUAL',
                scope TEXT DEFAULT 'GLOBAL',
                compatible_models TEXT DEFAULT '[]',
                conflicts_with TEXT DEFAULT '[]',
                manufacturer_id INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                purchase_price REAL DEFAULT 0.0,
                shipping_cost REAL DEFAULT 0.0,
                customs_tax_rate REAL DEFAULT 3.0,
                extra_tax_rate REAL DEFAULT 10.0,
                port_cost REAL DEFAULT 0.0,
                document_cost REAL DEFAULT 0.0,
                installation_cost REAL DEFAULT 0.0,
                other_cost REAL DEFAULT 0.0,
                cost_note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                tax_office TEXT DEFAULT '',
                tax_no TEXT DEFAULT '',
                contact_person TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                country TEXT DEFAULT '',
                city TEXT DEFAULT '',
                address TEXT DEFAULT '',
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_no TEXT DEFAULT '',
                customer_id INTEGER,
                model_id INTEGER,
                machine_qty INTEGER DEFAULT 1,
                currency TEXT DEFAULT 'USD',
                machine_unit_price REAL DEFAULT 0.0,
                machine_total REAL DEFAULT 0.0,
                options_total REAL DEFAULT 0.0,
                discount_pct REAL DEFAULT 0.0,
                subtotal REAL DEFAULT 0.0,
                grand_total REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                total_profit REAL DEFAULT 0.0,
                profit_rate REAL DEFAULT 0.0,
                conditions TEXT DEFAULT '',
                status TEXT DEFAULT 'Beklemede',
                offer_date TEXT DEFAULT (date('now')),
                order_date TEXT DEFAULT '',
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS offer_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                option_name TEXT DEFAULT '',
                quantity INTEGER DEFAULT 1,
                unit_price REAL DEFAULT 0.0,
                total_price REAL DEFAULT 0.0,
                unit_cost REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0
            )
        """)

        # ── Cari / Hesap Takibi ──────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS customer_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                txn_type TEXT NOT NULL,
                amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                description TEXT DEFAULT '',
                offer_id INTEGER DEFAULT 0,
                payment_method TEXT DEFAULT '',
                reference_no TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                txn_date TEXT DEFAULT (date('now')),
                user_id INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS manufacturer_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer_id INTEGER NOT NULL,
                txn_type TEXT NOT NULL,
                amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                description TEXT DEFAULT '',
                model_id INTEGER DEFAULT 0,
                payment_method TEXT DEFAULT '',
                reference_no TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                txn_date TEXT DEFAULT (date('now')),
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.commit()


# ── Company Profile ──────────────────────────────────────────────────

def get_company_profile():
    with _conn() as conn:
        row = conn.execute(
            "SELECT company_name, logo_path, website, footer_text FROM company_profile WHERE id=1"
        ).fetchone()
    if row:
        return {"company_name": row[0], "logo_path": row[1], "website": row[2], "footer_text": row[3]}
    return {"company_name": "", "logo_path": "", "website": "", "footer_text": ""}


def update_company_profile(**kwargs):
    allowed = ["company_name", "logo_path", "website", "footer_text"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as conn:
        conn.execute(f"UPDATE company_profile SET {sets} WHERE id=1", list(fields.values()))
        conn.commit()


# ── Categories ───────────────────────────────────────────────────────

def get_categories():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, name, image_path, sort_order FROM categories ORDER BY sort_order, name"
        ).fetchall()
    return [{"id": r[0], "name": r[1], "image_path": r[2], "sort_order": r[3]} for r in rows]


def add_category(name: str, image_path: str = "", sort_order: int = 0) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO categories (name, image_path, sort_order) VALUES (?,?,?)",
                (name, image_path, sort_order)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def update_category(cat_id: int, name: str, image_path: str = "", sort_order: int = 0):
    with _conn() as conn:
        conn.execute(
            "UPDATE categories SET name=?, image_path=?, sort_order=? WHERE id=?",
            (name, image_path, sort_order, cat_id)
        )
        conn.commit()


def delete_category(cat_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        conn.commit()


# ── Models ───────────────────────────────────────────────────────────

def _row_to_model(row):
    return {
        "id": row[0], "name": row[1], "model_code": row[2], "description": row[3],
        "category": row[4], "currency": row[5], "base_price": row[6], "sale_price": row[7],
        "image_path": row[8], "gallery_images": _jload(row[9], []),
        "specs": _jload(row[10], []), "compatible_options": _jload(row[11], []),
        "manufacturer_id": row[12], "sort_order": row[13],
        "purchase_price": row[14], "shipping_cost": row[15],
        "customs_tax_rate": row[16], "extra_tax_rate": row[17],
        "port_cost": row[18], "document_cost": row[19],
        "installation_cost": row[20], "other_cost": row[21],
        "cost_note": row[22], "created_at": row[23],
    }


_MODEL_COLS = ("id, name, model_code, description, category, currency, base_price, sale_price, "
               "image_path, gallery_images, specs, compatible_options, manufacturer_id, sort_order, "
               "purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate, "
               "port_cost, document_cost, installation_cost, other_cost, cost_note, created_at")


def get_models(category: str = None, manufacturer_id: int = None):
    q = f"SELECT {_MODEL_COLS} FROM models WHERE 1=1"
    params = []
    if category:
        q += " AND category=?"; params.append(category)
    if manufacturer_id:
        q += " AND manufacturer_id=?"; params.append(manufacturer_id)
    q += " ORDER BY sort_order, name"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row_to_model(r) for r in rows]


def get_model(model_id: int):
    with _conn() as conn:
        row = conn.execute(
            f"SELECT {_MODEL_COLS} FROM models WHERE id=?", (model_id,)
        ).fetchone()
    return _row_to_model(row) if row else None


def add_model(**kwargs) -> int:
    fields = _model_fields(kwargs)
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO models ({cols}) VALUES ({placeholders})", list(fields.values()))
        conn.commit()
        return cur.lastrowid


def update_model(model_id: int, **kwargs):
    fields = _model_fields(kwargs)
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as conn:
        conn.execute(f"UPDATE models SET {sets} WHERE id=?", list(fields.values()) + [model_id])
        conn.commit()


def delete_model(model_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM models WHERE id=?", (model_id,))
        conn.commit()


def _model_fields(d: dict) -> dict:
    allowed = ["name", "model_code", "description", "category", "currency", "base_price",
               "sale_price", "image_path", "gallery_images", "specs", "compatible_options",
               "manufacturer_id", "sort_order", "purchase_price", "shipping_cost",
               "customs_tax_rate", "extra_tax_rate", "port_cost", "document_cost",
               "installation_cost", "other_cost", "cost_note"]
    result = {}
    for k, v in d.items():
        if k in allowed:
            if k in ("gallery_images", "specs", "compatible_options") and isinstance(v, (list, dict)):
                result[k] = json.dumps(v, ensure_ascii=False)
            else:
                result[k] = v
    return result


# ── Options ──────────────────────────────────────────────────────────

def _row_to_option(row):
    return {
        "id": row[0], "name": row[1], "description": row[2], "category": row[3],
        "currency": row[4], "list_price": row[5], "sale_price": row[6],
        "image_path": row[7], "variant_image_path": row[8],
        "qty_type": row[9], "scope": row[10],
        "compatible_models": _jload(row[11], []),
        "conflicts_with": _jload(row[12], []),
        "manufacturer_id": row[13], "sort_order": row[14],
        "purchase_price": row[15], "shipping_cost": row[16],
        "customs_tax_rate": row[17], "extra_tax_rate": row[18],
        "port_cost": row[19], "document_cost": row[20],
        "installation_cost": row[21], "other_cost": row[22],
        "cost_note": row[23], "created_at": row[24],
    }


_OPT_COLS = ("id, name, description, category, currency, list_price, sale_price, "
             "image_path, variant_image_path, qty_type, scope, compatible_models, conflicts_with, "
             "manufacturer_id, sort_order, purchase_price, shipping_cost, customs_tax_rate, "
             "extra_tax_rate, port_cost, document_cost, installation_cost, other_cost, cost_note, created_at")


def get_options(category: str = None, manufacturer_id: int = None, model_id: int = None):
    q = f"SELECT {_OPT_COLS} FROM options WHERE 1=1"
    params = []
    if category:
        q += " AND category=?"; params.append(category)
    if manufacturer_id:
        q += " AND manufacturer_id=?"; params.append(manufacturer_id)
    q += " ORDER BY sort_order, name"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    opts = [_row_to_option(r) for r in rows]
    if model_id is not None:
        opts = [o for o in opts if _option_compatible(o, model_id)]
    return opts


def _option_compatible(opt: dict, model_id: int) -> bool:
    if opt["scope"] == "GLOBAL":
        return True
    return model_id in (opt["compatible_models"] or [])


def get_option(opt_id: int):
    with _conn() as conn:
        row = conn.execute(f"SELECT {_OPT_COLS} FROM options WHERE id=?", (opt_id,)).fetchone()
    return _row_to_option(row) if row else None


def add_option(**kwargs) -> int:
    fields = _option_fields(kwargs)
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO options ({cols}) VALUES ({placeholders})", list(fields.values()))
        conn.commit()
        return cur.lastrowid


def update_option(opt_id: int, **kwargs):
    fields = _option_fields(kwargs)
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as conn:
        conn.execute(f"UPDATE options SET {sets} WHERE id=?", list(fields.values()) + [opt_id])
        conn.commit()


def delete_option(opt_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM options WHERE id=?", (opt_id,))
        conn.commit()


def _option_fields(d: dict) -> dict:
    allowed = ["name", "description", "category", "currency", "list_price", "sale_price",
               "image_path", "variant_image_path", "qty_type", "scope",
               "compatible_models", "conflicts_with", "manufacturer_id", "sort_order",
               "purchase_price", "shipping_cost", "customs_tax_rate", "extra_tax_rate",
               "port_cost", "document_cost", "installation_cost", "other_cost", "cost_note"]
    result = {}
    for k, v in d.items():
        if k in allowed:
            if k in ("compatible_models", "conflicts_with") and isinstance(v, (list, dict)):
                result[k] = json.dumps(v, ensure_ascii=False)
            else:
                result[k] = v
    return result


# ── Customers ────────────────────────────────────────────────────────

def get_customers(user_id: int = None, role: str = "dealer"):
    q = ("SELECT id, company_name, tax_office, tax_no, contact_person, phone, email, "
         "country, city, address, user_id, created_at FROM customers")
    params = []
    if role == "dealer" and user_id:
        q += " WHERE user_id=?"; params.append(user_id)
    q += " ORDER BY company_name"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [
        {"id": r[0], "company_name": r[1], "tax_office": r[2], "tax_no": r[3],
         "contact_person": r[4], "phone": r[5], "email": r[6], "country": r[7],
         "city": r[8], "address": r[9], "user_id": r[10], "created_at": r[11]}
        for r in rows
    ]


def get_customer(cust_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, company_name, tax_office, tax_no, contact_person, phone, email, "
            "country, city, address, user_id, created_at FROM customers WHERE id=?", (cust_id,)
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "company_name": row[1], "tax_office": row[2], "tax_no": row[3],
            "contact_person": row[4], "phone": row[5], "email": row[6], "country": row[7],
            "city": row[8], "address": row[9], "user_id": row[10], "created_at": row[11]}


def add_customer(user_id: int, **kwargs) -> int:
    allowed = ["company_name", "tax_office", "tax_no", "contact_person", "phone",
               "email", "country", "city", "address"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    fields["user_id"] = user_id
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO customers ({cols}) VALUES ({placeholders})", list(fields.values()))
        conn.commit()
        return cur.lastrowid


def update_customer(cust_id: int, **kwargs):
    allowed = ["company_name", "tax_office", "tax_no", "contact_person", "phone",
               "email", "country", "city", "address"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as conn:
        conn.execute(f"UPDATE customers SET {sets} WHERE id=?", list(fields.values()) + [cust_id])
        conn.commit()


def delete_customer(cust_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM customers WHERE id=?", (cust_id,))
        conn.commit()


# ── Offers ───────────────────────────────────────────────────────────

def _row_to_offer(row):
    return {
        "id": row[0], "offer_no": row[1], "customer_id": row[2], "model_id": row[3],
        "machine_qty": row[4], "currency": row[5], "machine_unit_price": row[6],
        "machine_total": row[7], "options_total": row[8], "discount_pct": row[9],
        "subtotal": row[10], "grand_total": row[11], "total_cost": row[12],
        "total_profit": row[13], "profit_rate": row[14], "conditions": row[15],
        "status": row[16], "offer_date": row[17], "order_date": row[18],
        "user_id": row[19], "created_at": row[20],
    }


def get_offers(user_id: int = None, role: str = "dealer", status: str = None):
    q = ("SELECT id, offer_no, customer_id, model_id, machine_qty, currency, "
         "machine_unit_price, machine_total, options_total, discount_pct, "
         "subtotal, grand_total, total_cost, total_profit, profit_rate, "
         "conditions, status, offer_date, order_date, user_id, created_at "
         "FROM offers WHERE 1=1")
    params = []
    if role == "dealer" and user_id:
        q += " AND user_id=?"; params.append(user_id)
    if status:
        q += " AND status=?"; params.append(status)
    q += " ORDER BY id DESC"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row_to_offer(r) for r in rows]


def get_offer(offer_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, offer_no, customer_id, model_id, machine_qty, currency, "
            "machine_unit_price, machine_total, options_total, discount_pct, "
            "subtotal, grand_total, total_cost, total_profit, profit_rate, "
            "conditions, status, offer_date, order_date, user_id, created_at "
            "FROM offers WHERE id=?", (offer_id,)
        ).fetchone()
    return _row_to_offer(row) if row else None


def create_offer(user_id: int, **kwargs) -> int:
    with _conn() as conn:
        last = conn.execute("SELECT MAX(id) FROM offers").fetchone()[0] or 0
        offer_no = f"TKL-{last + 1:05d}"
    allowed = ["customer_id", "model_id", "machine_qty", "currency",
               "machine_unit_price", "machine_total", "options_total", "discount_pct",
               "subtotal", "grand_total", "total_cost", "total_profit", "profit_rate",
               "conditions", "status", "offer_date"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    fields["user_id"] = user_id
    fields["offer_no"] = offer_no
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO offers ({cols}) VALUES ({placeholders})", list(fields.values()))
        conn.commit()
        return cur.lastrowid


def update_offer_status(offer_id: int, status: str, order_date: str = ""):
    with _conn() as conn:
        conn.execute(
            "UPDATE offers SET status=?, order_date=? WHERE id=?",
            (status, order_date, offer_id)
        )
        conn.commit()


def delete_offer(offer_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM offers WHERE id=?", (offer_id,))
        conn.execute("DELETE FROM offer_items WHERE offer_id=?", (offer_id,))
        conn.commit()


# ── Offer Items ──────────────────────────────────────────────────────

def add_offer_items(offer_id: int, items: list):
    with _conn() as conn:
        conn.execute("DELETE FROM offer_items WHERE offer_id=?", (offer_id,))
        for item in items:
            conn.execute(
                "INSERT INTO offer_items (offer_id, option_id, option_name, quantity, "
                "unit_price, total_price, unit_cost, total_cost) VALUES (?,?,?,?,?,?,?,?)",
                (offer_id, item.get("option_id", 0), item.get("option_name", ""),
                 item.get("quantity", 1), item.get("unit_price", 0),
                 item.get("total_price", 0), item.get("unit_cost", 0),
                 item.get("total_cost", 0))
            )
        conn.commit()


def get_offer_items(offer_id: int):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, offer_id, option_id, option_name, quantity, "
            "unit_price, total_price, unit_cost, total_cost FROM offer_items WHERE offer_id=?",
            (offer_id,)
        ).fetchall()
    return [
        {"id": r[0], "offer_id": r[1], "option_id": r[2], "option_name": r[3],
         "quantity": r[4], "unit_price": r[5], "total_price": r[6],
         "unit_cost": r[7], "total_cost": r[8]}
        for r in rows
    ]


# ── Utilities ────────────────────────────────────────────────────────

def _jload(val, default):
    if not val:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def get_stats(user_id: int = None, role: str = "admin") -> dict:
    with _conn() as conn:
        if role == "dealer" and user_id:
            customers = conn.execute("SELECT COUNT(*) FROM customers WHERE user_id=?", (user_id,)).fetchone()[0]
            offers = conn.execute("SELECT COUNT(*) FROM offers WHERE user_id=?", (user_id,)).fetchone()[0]
            orders = conn.execute(
                "SELECT COUNT(*) FROM offers WHERE user_id=? AND status='Sipariş Verildi'", (user_id,)
            ).fetchone()[0]
        else:
            customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            offers = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
            orders = conn.execute(
                "SELECT COUNT(*) FROM offers WHERE status='Sipariş Verildi'"
            ).fetchone()[0]
        models = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    return {"customers": customers, "offers": offers, "models": models, "orders": orders}


# ── Customer Transactions (Müşteri Cari) ─────────────────────────────

def _row_to_ctxn(row) -> dict:
    return {
        "id": row[0], "customer_id": row[1], "txn_type": row[2],
        "amount": row[3], "currency": row[4], "description": row[5],
        "offer_id": row[6], "payment_method": row[7], "reference_no": row[8],
        "due_date": row[9], "txn_date": row[10], "user_id": row[11],
        "notes": row[12], "created_at": row[13],
    }

_CTXN_COLS = ("id, customer_id, txn_type, amount, currency, description, "
              "offer_id, payment_method, reference_no, due_date, txn_date, "
              "user_id, notes, created_at")


def get_customer_transactions(customer_id: int = None, user_id: int = None) -> list:
    q = f"SELECT {_CTXN_COLS} FROM customer_transactions WHERE 1=1"
    params = []
    if customer_id:
        q += " AND customer_id=?"; params.append(customer_id)
    if user_id:
        q += " AND user_id=?"; params.append(user_id)
    q += " ORDER BY txn_date DESC, id DESC"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row_to_ctxn(r) for r in rows]


def add_customer_transaction(customer_id: int, txn_type: str, amount: float,
                              currency: str = "USD", **kwargs) -> int:
    allowed = ["description", "offer_id", "payment_method", "reference_no",
               "due_date", "txn_date", "user_id", "notes"]
    fields = {"customer_id": customer_id, "txn_type": txn_type,
              "amount": amount, "currency": currency}
    for k in allowed:
        if k in kwargs:
            fields[k] = kwargs[k]
    cols = ", ".join(fields.keys())
    ph = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO customer_transactions ({cols}) VALUES ({ph})",
                           list(fields.values()))
        conn.commit()
        return cur.lastrowid


def delete_customer_transaction(txn_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM customer_transactions WHERE id=?", (txn_id,))
        conn.commit()


def get_customer_balance(customer_id: int, currency: str = None) -> dict:
    with _conn() as conn:
        q = ("SELECT txn_type, SUM(amount) FROM customer_transactions "
             "WHERE customer_id=?")
        params = [customer_id]
        if currency:
            q += " AND currency=?"; params.append(currency)
        q += " GROUP BY txn_type"
        rows = conn.execute(q, params).fetchall()
    totals = {"debit": 0.0, "credit": 0.0}
    for row in rows:
        totals[row[0]] = float(row[1] or 0)
    balance = totals["debit"] - totals["credit"]
    return {
        "total_debit": totals["debit"],
        "total_credit": totals["credit"],
        "balance": balance,
    }


def get_all_customer_balances(user_id: int = None, role: str = "admin") -> list:
    customers = get_customers(user_id=user_id, role=role)
    result = []
    with _conn() as conn:
        for c in customers:
            rows = conn.execute(
                "SELECT txn_type, SUM(amount), currency FROM customer_transactions "
                "WHERE customer_id=? GROUP BY txn_type, currency",
                (c["id"],)
            ).fetchall()
            by_currency = {}
            for row in rows:
                cur = row[2] or "USD"
                if cur not in by_currency:
                    by_currency[cur] = {"debit": 0.0, "credit": 0.0}
                by_currency[cur][row[0]] = float(row[1] or 0)
            result.append({**c, "balances": by_currency})
    return result


# ── Manufacturer Transactions (Üretici Hesap Takibi) ─────────────────

def _row_to_mtxn(row) -> dict:
    return {
        "id": row[0], "manufacturer_id": row[1], "txn_type": row[2],
        "amount": row[3], "currency": row[4], "description": row[5],
        "model_id": row[6], "payment_method": row[7], "reference_no": row[8],
        "due_date": row[9], "txn_date": row[10], "notes": row[11], "created_at": row[12],
    }

_MTXN_COLS = ("id, manufacturer_id, txn_type, amount, currency, description, "
              "model_id, payment_method, reference_no, due_date, txn_date, notes, created_at")


def get_manufacturer_transactions(manufacturer_id: int = None) -> list:
    q = f"SELECT {_MTXN_COLS} FROM manufacturer_transactions WHERE 1=1"
    params = []
    if manufacturer_id:
        q += " AND manufacturer_id=?"; params.append(manufacturer_id)
    q += " ORDER BY txn_date DESC, id DESC"
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row_to_mtxn(r) for r in rows]


def add_manufacturer_transaction(manufacturer_id: int, txn_type: str, amount: float,
                                  currency: str = "USD", **kwargs) -> int:
    allowed = ["description", "model_id", "payment_method", "reference_no",
               "due_date", "txn_date", "notes"]
    fields = {"manufacturer_id": manufacturer_id, "txn_type": txn_type,
              "amount": amount, "currency": currency}
    for k in allowed:
        if k in kwargs:
            fields[k] = kwargs[k]
    cols = ", ".join(fields.keys())
    ph = ", ".join("?" * len(fields))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO manufacturer_transactions ({cols}) VALUES ({ph})",
                           list(fields.values()))
        conn.commit()
        return cur.lastrowid


def delete_manufacturer_transaction(txn_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM manufacturer_transactions WHERE id=?", (txn_id,))
        conn.commit()


def get_manufacturer_balance(manufacturer_id: int, currency: str = None) -> dict:
    with _conn() as conn:
        q = ("SELECT txn_type, SUM(amount) FROM manufacturer_transactions "
             "WHERE manufacturer_id=?")
        params = [manufacturer_id]
        if currency:
            q += " AND currency=?"; params.append(currency)
        q += " GROUP BY txn_type"
        rows = conn.execute(q, params).fetchall()
    totals = {"purchase": 0.0, "payment": 0.0}
    for row in rows:
        if row[0] in totals:
            totals[row[0]] = float(row[1] or 0)
    owed = totals["purchase"] - totals["payment"]
    return {
        "total_purchase": totals["purchase"],
        "total_payment": totals["payment"],
        "balance_owed": owed,
    }
