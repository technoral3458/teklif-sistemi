import sqlite3

DB_PATH = "database.db"


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def exec_query(query, params=()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Veritabanı Hatası (exec): {e}")
        return False


def get_query(query, params=()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Veritabanı Hatası (get): {e}")
        return []


def add_column_if_missing(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT DEFAULT 'Genel',
            base_price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            port_discount REAL DEFAULT 0.0,
            image_path TEXT,
            specs TEXT,
            compatible_options TEXT,
            gallery_images TEXT DEFAULT '',
            gallery_videos TEXT DEFAULT '',
            user_id INTEGER DEFAULT 1,

            purchase_price REAL DEFAULT 0.0,
            sale_price REAL DEFAULT 0.0,
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opt_name TEXT,
            category TEXT DEFAULT 'Genel',
            opt_price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            opt_image TEXT,
            opt_desc TEXT,
            video_path TEXT,
            remove_keyword TEXT,
            sort_order INTEGER DEFAULT 0,

            purchase_price REAL DEFAULT 0.0,
            sale_price REAL DEFAULT 0.0,
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            tax_office TEXT,
            tax_no TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            user_id INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            model_id INTEGER,
            offer_date TEXT,
            total_price REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Beklemede',
            conditions TEXT,
            user_id INTEGER,

            total_cost REAL DEFAULT 0.0,
            total_profit REAL DEFAULT 0.0,
            profit_rate REAL DEFAULT 0.0,
            cost_locked INTEGER DEFAULT 0
        )
    """)

    c.execute("""
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            image_path TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            company_name TEXT,
            logo_path TEXT,
            website TEXT,
            footer_text TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            company_name TEXT,
            logo_path TEXT,
            website TEXT,
            address_full TEXT,
            phone TEXT,
            role TEXT DEFAULT 'Dealer',
            allowed_categories TEXT DEFAULT '',
            can_view_costs INTEGER DEFAULT 0
        )
    """)

    for table in ["models", "options"]:
        add_column_if_missing(c, table, "purchase_price", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "sale_price", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "shipping_cost", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "customs_tax_rate", "REAL DEFAULT 3.0")
        add_column_if_missing(c, table, "extra_tax_rate", "REAL DEFAULT 10.0")
        add_column_if_missing(c, table, "port_cost", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "document_cost", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "installation_cost", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "other_cost", "REAL DEFAULT 0.0")
        add_column_if_missing(c, table, "cost_note", "TEXT DEFAULT ''")

    add_column_if_missing(c, "offers", "total_cost", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offers", "total_profit", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offers", "profit_rate", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offers", "cost_locked", "INTEGER DEFAULT 0")

    add_column_if_missing(c, "offer_items", "sale_price", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offer_items", "total_sale_price", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offer_items", "total_cost", "REAL DEFAULT 0.0")
    add_column_if_missing(c, "offer_items", "total_profit", "REAL DEFAULT 0.0")

    add_column_if_missing(c, "users", "can_view_costs", "INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


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
    purchase_price = float(purchase_price or 0)
    shipping_cost = float(shipping_cost or 0)
    customs_tax_rate = float(customs_tax_rate or 0)
    extra_tax_rate = float(extra_tax_rate or 0)
    port_cost = float(port_cost or 0)
    document_cost = float(document_cost or 0)
    installation_cost = float(installation_cost or 0)
    other_cost = float(other_cost or 0)

    subtotal_1 = purchase_price + shipping_cost
    customs_tax = subtotal_1 * customs_tax_rate / 100
    subtotal_2 = subtotal_1 + customs_tax
    extra_tax = subtotal_2 * extra_tax_rate / 100
    subtotal_3 = subtotal_2 + extra_tax

    total_cost = subtotal_3 + port_cost + document_cost + installation_cost + other_cost

    return {
        "purchase_price": purchase_price,
        "shipping_cost": shipping_cost,
        "subtotal_1": subtotal_1,
        "customs_tax": customs_tax,
        "subtotal_2": subtotal_2,
        "extra_tax": extra_tax,
        "subtotal_3": subtotal_3,
        "port_cost": port_cost,
        "document_cost": document_cost,
        "installation_cost": installation_cost,
        "other_cost": other_cost,
        "total_cost": total_cost
    }


def calculate_profit(sale_price, total_cost):
    sale_price = float(sale_price or 0)
    total_cost = float(total_cost or 0)
    profit = sale_price - total_cost
    profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

    return {
        "sale_price": sale_price,
        "total_cost": total_cost,
        "profit": profit,
        "profit_rate": profit_rate
    }


init_db()