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

        # Translation columns
        for col in ["name_en", "name_zh"]:
            _acol(cur, "categories", col, "TEXT DEFAULT ''")
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
        c.commit()


# ── Company ───────────────────────────────────────────────────────────────────

def get_company():
    with _c() as c:
        r = c.execute(
            "SELECT company_name,address,phone,website,tax_id,email,logo_path FROM company_profile WHERE id=1"
        ).fetchone()
    if not r:
        return {}
    return dict(zip(["company_name", "address", "phone", "website", "tax_id", "email", "logo_path"], r))


def save_company(**kw):
    allowed = ["company_name", "address", "phone", "website", "tax_id", "email", "logo_path"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE company_profile SET {sets} WHERE id=1", list(f.values()))


# ── Categories ────────────────────────────────────────────────────────────────

def get_cats():
    with _c() as c:
        rows = c.execute("SELECT id,name,description,name_en,name_zh FROM categories ORDER BY name").fetchall()
    return [dict(zip(["id","name","description","name_en","name_zh"], r)) for r in rows]


def add_cat(name, description="", name_en="", name_zh=""):
    with _c() as c:
        c.execute("INSERT OR IGNORE INTO categories(name,description,name_en,name_zh) VALUES(?,?,?,?)", (name, description, name_en, name_zh))


def upd_cat(cid, name, description="", name_en="", name_zh=""):
    with _c() as c:
        c.execute("UPDATE categories SET name=?,description=?,name_en=?,name_zh=? WHERE id=?", (name, description, name_en, name_zh, cid))


def del_cat(cid):
    with _c() as c:
        c.execute("DELETE FROM categories WHERE id=?", (cid,))


# ── Models ────────────────────────────────────────────────────────────────────

_MCOLS = ("id,name,category_id,description,base_price,currency,specs,"
          "purchase_price,purchase_currency,shipping_cost,customs_pct,extra_tax_pct,"
          "port_cost,document_cost,installation_cost,other_cost,total_cost,"
          "image_path,compatible_options,"
          "name_en,description_en,name_zh,description_zh,specs_en,specs_zh,created_at")

_MKEYS = ["id", "name", "category_id", "description", "base_price", "currency", "specs",
          "purchase_price", "purchase_currency", "shipping_cost", "customs_pct", "extra_tax_pct",
          "port_cost", "document_cost", "installation_cost", "other_cost", "total_cost",
          "image_path", "compatible_options",
          "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh",
          "created_at"]


def _rm(r):
    return dict(zip(_MKEYS, r))


def get_models(category_id=None):
    q = f"SELECT {_MCOLS} FROM models WHERE 1=1"
    p = []
    if category_id:
        q += " AND category_id=?"
        p.append(category_id)
    q += " ORDER BY name"
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
               "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh"]
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
               "name_en", "description_en", "name_zh", "description_zh", "specs_en", "specs_zh"]
    f = {k: v for k, v in kw.items() if k in allowed}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE models SET {sets} WHERE id=?", list(f.values()) + [mid])


def del_model(mid):
    with _c() as c:
        c.execute("DELETE FROM models WHERE id=?", (mid,))


# ── Options ───────────────────────────────────────────────────────────────────

_OCOLS = "id,name,description,price,currency,scope,category_id,qty_type,conflict_group,image_path,image_priority,variation_image_path,name_en,description_en,name_zh,description_zh,created_at"
_OKEYS = ["id", "name", "description", "price", "currency", "scope",
          "category_id", "qty_type", "conflict_group", "image_path", "image_priority",
          "variation_image_path", "name_en", "description_en", "name_zh", "description_zh",
          "created_at"]


def _ro(r):
    return dict(zip(_OKEYS, r))


def get_options(category_id=None):
    q = f"SELECT {_OCOLS} FROM options WHERE 1=1"
    p = []
    if category_id:
        q += " AND category_id=?"
        p.append(category_id)
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
               "category_id", "qty_type", "conflict_group", "image_path", "image_priority",
               "variation_image_path", "name_en", "description_en", "name_zh", "description_zh"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO options({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_option(oid, **kw):
    allowed = ["name", "description", "price", "currency", "scope",
               "category_id", "qty_type", "conflict_group", "image_path", "image_priority",
               "variation_image_path", "name_en", "description_en", "name_zh", "description_zh"]
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
           "admin_notes,termin_date,mfr_status,mfr_notes,"
           "delivery_method,delivery_time,logistics,payment_notes,created_at")
_OFKEYS = ["id","offer_no","customer_id","model_id","machine_count","currency",
           "base_price","options_total","discount_pct","total_price","status",
           "notes","validity_date","dealer_id","manufacturer_id","admin_status",
           "admin_notes","termin_date","mfr_status","mfr_notes",
           "delivery_method","delivery_time","logistics","payment_notes","created_at"]


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


def get_recent_offers(limit=10):
    with _c() as c:
        rows = c.execute(
            f"SELECT {_OFCOLS} FROM offers ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_rof(r) for r in rows]


def get_offer(oid):
    with _c() as c:
        r = c.execute(f"SELECT {_OFCOLS} FROM offers WHERE id=?", (oid,)).fetchone()
    return _rof(r) if r else None


def create_offer(**kw):
    allowed = ["offer_no", "customer_id", "model_id", "machine_count", "currency",
               "base_price", "options_total", "discount_pct", "total_price",
               "status", "notes", "validity_date", "dealer_id",
               "delivery_method", "delivery_time", "logistics", "payment_notes"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO offers({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_offer_status(oid, status):
    with _c() as c:
        c.execute("UPDATE offers SET status=? WHERE id=?", (status, oid))


def upd_offer(oid, **kw):
    allowed = ["customer_id", "model_id", "machine_count", "currency",
               "base_price", "options_total", "discount_pct", "total_price",
               "status", "notes", "validity_date",
               "delivery_method", "delivery_time", "logistics", "payment_notes"]
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

def reject_order(oid, admin_notes=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET admin_status='rejected', admin_notes=?, status='İptal' WHERE id=?",
            (admin_notes, oid)
        )

def mfr_confirm_order(oid, termin_date, mfr_notes=""):
    with _c() as c:
        c.execute(
            "UPDATE offers SET mfr_status='confirmed', termin_date=?, mfr_notes=?, status='Üretimde' WHERE id=?",
            (termin_date, mfr_notes, oid)
        )

def update_mfr_status(oid, mfr_status):
    status_map = {
        "in_production": "Üretimde",
        "completed":     "Tamamlandı",
        "delivered":     "Teslim Edildi",
    }
    with _c() as c:
        c.execute(
            "UPDATE offers SET mfr_status=?, status=? WHERE id=?",
            (mfr_status, status_map.get(mfr_status, "Üretimde"), oid)
        )


# ── Order Stages ─────────────────────────────────────────────────────────────

def add_order_stage(order_id, stage_name, notes, stage_date):
    with _c() as c:
        c.execute(
            "INSERT INTO order_stages(order_id,stage_name,notes,stage_date) VALUES(?,?,?,?)",
            (order_id, stage_name, notes, stage_date)
        )

def get_order_stages(order_id):
    with _c() as c:
        rows = c.execute(
            "SELECT id,order_id,stage_name,notes,stage_date,created_at FROM order_stages WHERE order_id=? ORDER BY stage_date DESC,id DESC",
            (order_id,)
        ).fetchall()
    return [{"id":r[0],"order_id":r[1],"stage_name":r[2],"notes":r[3],"stage_date":r[4],"created_at":r[5]} for r in rows]

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


def get_stats():
    with _c() as c:
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
