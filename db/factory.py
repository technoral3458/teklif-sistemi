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
        rows = c.execute("SELECT id,name,description FROM categories ORDER BY name").fetchall()
    return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]


def add_cat(name, description=""):
    with _c() as c:
        c.execute("INSERT OR IGNORE INTO categories(name,description) VALUES(?,?)", (name, description))


def upd_cat(cid, name, description=""):
    with _c() as c:
        c.execute("UPDATE categories SET name=?,description=? WHERE id=?", (name, description, cid))


def del_cat(cid):
    with _c() as c:
        c.execute("DELETE FROM categories WHERE id=?", (cid,))


# ── Models ────────────────────────────────────────────────────────────────────

_MCOLS = ("id,name,category_id,description,base_price,currency,specs,"
          "purchase_price,purchase_currency,shipping_cost,customs_pct,extra_tax_pct,"
          "port_cost,document_cost,installation_cost,other_cost,total_cost,"
          "image_path,compatible_options,created_at")

_MKEYS = ["id", "name", "category_id", "description", "base_price", "currency", "specs",
          "purchase_price", "purchase_currency", "shipping_cost", "customs_pct", "extra_tax_pct",
          "port_cost", "document_cost", "installation_cost", "other_cost", "total_cost",
          "image_path", "compatible_options", "created_at"]


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
               "other_cost", "total_cost", "image_path", "compatible_options"]
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
               "other_cost", "total_cost", "image_path", "compatible_options"]
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

_OCOLS = "id,name,description,price,currency,scope,category_id,qty_type,conflict_group,created_at"
_OKEYS = ["id", "name", "description", "price", "currency", "scope",
          "category_id", "qty_type", "conflict_group", "created_at"]


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
               "category_id", "qty_type", "conflict_group"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO options({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_option(oid, **kw):
    allowed = ["name", "description", "price", "currency", "scope",
               "category_id", "qty_type", "conflict_group"]
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
           "notes,validity_date,dealer_id,created_at")
_OFKEYS = ["id", "offer_no", "customer_id", "model_id", "machine_count", "currency",
           "base_price", "options_total", "discount_pct", "total_price", "status",
           "notes", "validity_date", "dealer_id", "created_at"]


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
               "status", "notes", "validity_date", "dealer_id"]
    f = {k: v for k, v in kw.items() if k in allowed}
    cols = ",".join(f.keys())
    ph = ",".join("?" * len(f))
    with _c() as c:
        cur = c.execute(f"INSERT INTO offers({cols}) VALUES({ph})", list(f.values()))
        return cur.lastrowid


def upd_offer_status(oid, status):
    with _c() as c:
        c.execute("UPDATE offers SET status=? WHERE id=?", (status, oid))


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
