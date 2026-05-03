import sqlite3
import os

# Web sürümü için tek ve güçlü bir veritabanı kullanıyoruz
DB_PATH = 'database.db'

def get_connection():
    """Veritabanına bağlantı açar."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def exec_query(query, params=()):
    """INSERT, UPDATE, DELETE işlemleri için."""
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
    """SELECT işlemleri için."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Veritabanı Hatası (get): {e}")
        return []

def init_db():
    """
    Sizin eski kodlarınızdaki tüm tablo yapılarını 
    web sürümüne uygun şekilde tek çatıda toplar.
    """
    conn = get_connection()
    c = conn.cursor()

    # 1. MAKİNELER TABLOSU (Geliştirilmiş)
    c.execute("""CREATE TABLE IF NOT EXISTS models (
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
        gallery_videos TEXT DEFAULT ''
    )""")

    # 2. DONANIM VE OPSİYON HAVUZU
    c.execute("""CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        opt_name TEXT, 
        category TEXT DEFAULT 'Genel',
        opt_price REAL DEFAULT 0.0, 
        currency TEXT DEFAULT 'USD',
        opt_image TEXT, 
        opt_desc TEXT,
        video_path TEXT,
        remove_keyword TEXT,
        sort_order INTEGER DEFAULT 0
    )""")

    # 3. MÜŞTERİLER TABLOSU
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        company_name TEXT, 
        tax_office TEXT, 
        tax_no TEXT, 
        contact_person TEXT, 
        phone TEXT, 
        email TEXT, 
        address TEXT,
        user_id INTEGER -- Hangi bayiye ait olduğu
    )""")

    # 4. TEKLİFLER ANA TABLO
    c.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        model_id INTEGER,
        offer_date TEXT,
        total_price REAL,
        status TEXT DEFAULT 'Beklemede', -- Sizin istediğiniz analiz paneli için
        conditions TEXT, -- JSON formatında tüm şartlar (ödeme planı, banka vb.)
        user_id INTEGER -- Teklifi hazırlayan bayi ID
    )""")

    # 5. TEKLİF İÇERİĞİ / SEÇİLEN OPSİYONLAR
    c.execute("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER,
        option_id INTEGER,
        quantity INTEGER DEFAULT 1
    )""")

    # 6. KATEGORİLER
    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT UNIQUE, 
        image_path TEXT DEFAULT ''
    )""")

    # 7. ŞİRKET PROFİLİ (Logo, Antet vb.)
    c.execute("""CREATE TABLE IF NOT EXISTS company_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        company_name TEXT,
        logo_path TEXT,
        website TEXT,
        footer_text TEXT
    )""")

    conn.commit()
    conn.close()

# Dosya import edildiği anda veritabanını hazırla
init_db()
