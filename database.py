import sqlite3
import os
import sys
import re

# =========================================================
# 1. DOSYA YOLLARI VE EXE UYUMLULUĞU
# =========================================================
def get_base_dir():
    """Programın çalıştığı ana dizini bulur (.exe dahil)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ARTIK 2 FARKLI VERİTABANIMIZ VAR:
DB_MAIN = os.path.join(get_base_dir(), "factory_data.db")  # Katalog, Makine, Ayarlar
DB_SALES = os.path.join(get_base_dir(), "sales_data.db")   # Müşteri ve Teklifler

# Hangi tabloların yeni "Satış Veritabanında" tutulacağını belirliyoruz
SALES_TABLES = ['customers', 'offers', 'offer_items']

# =========================================================
# 2. AKILLI YÖNLENDİRİCİ (SMART ROUTER) & SANAL BİRLEŞTİRİCİ
# =========================================================
def _get_db_path(query):
    """Gelen SQL sorgusunu okur ve hangi veritabanına gideceğine karar verir."""
    query_lower = query.lower()
    words = re.findall(r'\w+', query_lower)
    
    for table in SALES_TABLES:
        if table in words:
            return DB_SALES
            
    return DB_MAIN

def get_connection(query=""):
    """
    Sorguya göre doğru veritabanına bağlanır VE diğer veritabanını
    sanal olarak (TEMP VIEW) bu bağlantıya ekler. 
    Böylece JOIN sorguları (Örn: Geçmiş Teklifler) asla çökmez.
    """
    db_path = _get_db_path(query)
    conn = sqlite3.connect(db_path)
    
    try:
        # Mevcut veritabanındaki tabloları bul
        primary_res = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        primary_tables = [r[0] for r in primary_res]

        if db_path == DB_SALES and os.path.exists(DB_MAIN):
            # Sales DB'deyiz, Factory DB'yi sanal olarak bağla
            conn.execute(f"ATTACH DATABASE '{DB_MAIN}' AS factory")
            res = conn.execute("SELECT name FROM factory.sqlite_master WHERE type='table'").fetchall()
            for r in res:
                t_name = r[0]
                if t_name not in primary_tables and not t_name.startswith('sqlite_'):
                    conn.execute(f"CREATE TEMP VIEW IF NOT EXISTS {t_name} AS SELECT * FROM factory.{t_name}")
                    
        elif db_path == DB_MAIN and os.path.exists(DB_SALES):
            # Factory DB'deyiz, Sales DB'yi sanal olarak bağla
            conn.execute(f"ATTACH DATABASE '{DB_SALES}' AS sales")
            res = conn.execute("SELECT name FROM sales.sqlite_master WHERE type='table'").fetchall()
            for r in res:
                t_name = r[0]
                if t_name not in primary_tables and not t_name.startswith('sqlite_'):
                    conn.execute(f"CREATE TEMP VIEW IF NOT EXISTS {t_name} AS SELECT * FROM sales.{t_name}")
    except Exception as e:
        print("Veritabanı Sanal Birleştirme Hatası:", e)
        
    return conn

# =========================================================
# 3. VERİ ÇEKME / İŞLEME (SELECT, INSERT, UPDATE, DELETE)
# =========================================================
def exec_query(query, params=()):
    """Veri ekleme, güncelleme ve silme işlemleri için kullanılır."""
    try:
        with get_connection(query) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Veritabanı Hatası (exec): {e}\nSorgu: {query}")
        return False

def get_query(query, params=()):
    """Veri çekme (SELECT) işlemleri için kullanılır."""
    try:
        with get_connection(query) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Veritabanı Hatası (get): {e}\nSorgu: {query}")
        return []

# =========================================================
# 4. VERİTABANI KURULUMU VE OTOMATİK VERİ TAŞIMA
# =========================================================
def init_db():
    """
    Sistemin çalışması için gerekli tüm tabloları oluşturur. 
    Eğer tablolar zaten varsa eksik sütunları otomatik ekler.
    Eski veritabanındaki müşteri/teklif verilerini yeni satış veritabanına taşır.
    """
    # ---------------------------------------------------------
    # BÖLÜM 1: ANA VERİTABANI (factory_data.db) KURULUMU
    # ---------------------------------------------------------
    conn_main = sqlite3.connect(DB_MAIN)
    c_main = conn_main.cursor()
    
    # 1. MAKİNELER TABLOSU
    c_main.execute("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT, 
        base_price REAL, 
        image_path TEXT, 
        specs TEXT
    )""")
    
    # 2. DONANIM VE OPSİYON HAVUZU
    c_main.execute("""CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        opt_name TEXT, 
        opt_price REAL, 
        opt_image TEXT, 
        opt_desc TEXT,
        remove_keyword TEXT
    )""")
    
    # 3. MODEL-OPSİYON İLİŞKİ TABLOSU
    c_main.execute("""CREATE TABLE IF NOT EXISTS model_options (
        model_id INTEGER, 
        option_id INTEGER
    )""")
    
    # 4. TEKLİF TASARIM AYARLARI TABLOSU
    c_main.execute("""CREATE TABLE IF NOT EXISTS template_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1), 
        logo_name TEXT, 
        footer_text TEXT, 
        t_w_mm INTEGER DEFAULT 30, 
        t_h_mm INTEGER DEFAULT 30, 
        hero_h_px INTEGER DEFAULT 350, 
        desc_w_px INTEGER DEFAULT 450, 
        font_size_pt INTEGER DEFAULT 11
    )""")

    # Başlangıç Ayarları
    c_main.execute("SELECT id FROM template_settings WHERE id=1")
    if not c_main.fetchone():
        c_main.execute("""INSERT INTO template_settings 
        (id, logo_name, footer_text, t_w_mm, t_h_mm, hero_h_px, desc_w_px, font_size_pt) 
        VALUES (1, 'logo.png', 'Ersan Makine A.Ş. | 2026', 30, 30, 350, 450, 11)""")
        
    conn_main.commit()
    conn_main.close()

    # ---------------------------------------------------------
    # BÖLÜM 2: SATIŞ VERİTABANI (sales_data.db) KURULUM VE TAŞIMA
    # ---------------------------------------------------------
    needs_migration = not os.path.exists(DB_SALES) or os.path.getsize(DB_SALES) == 0
    
    conn_sales = sqlite3.connect(DB_SALES)
    c_sales = conn_sales.cursor()

    # 1. MÜŞTERİLER TABLOSU
    c_sales.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        company_name TEXT, 
        tax_office TEXT, 
        tax_no TEXT, 
        contact_person TEXT, 
        phone TEXT, 
        email TEXT, 
        address TEXT
    )""")
    
    # Müşteri Tablosu Sütun Kontrolü
    c_sales.execute("PRAGMA table_info(customers)")
    existing_columns = [col[1] for col in c_sales.fetchall()]
    if "tax_office" not in existing_columns:
        c_sales.execute("ALTER TABLE customers ADD COLUMN tax_office TEXT;")
    if "tax_no" not in existing_columns:
        c_sales.execute("ALTER TABLE customers ADD COLUMN tax_no TEXT;")

    # 2. TEKLİFLER ANA TABLO
    c_sales.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        model_id INTEGER,
        offer_date TEXT,
        total_price REAL,
        notes TEXT,
        conditions TEXT
    )""")

    # 3. TEKLİF İÇERİĞİ / SEÇİLEN OPSİYONLAR
    c_sales.execute("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER,
        option_id INTEGER,
        quantity INTEGER DEFAULT 1
    )""")
    
    conn_sales.commit()

    # ---- ESKİ VERİTABANINDAN (factory_data.db) YENİSİNE TAŞIMA (MIGRATION) ----
    if needs_migration and os.path.exists(DB_MAIN):
        print("SİSTEM BİLGİSİ: 'sales_data.db' oluşturuluyor. Eski Müşteri ve Teklif verileri kurtarılıyor...")
        try:
            c_sales.execute(f"ATTACH DATABASE '{DB_MAIN}' AS old_db")
            
            # Eski DB'de 'customers' tablosu var mı? Varsa taşı.
            c_sales.execute("SELECT name FROM old_db.sqlite_master WHERE type='table' AND name='customers'")
            if c_sales.fetchone():
                c_sales.execute("INSERT OR IGNORE INTO customers SELECT * FROM old_db.customers")
                
            # Eski DB'de 'offers' tablosu var mı? Varsa taşı.
            c_sales.execute("SELECT name FROM old_db.sqlite_master WHERE type='table' AND name='offers'")
            if c_sales.fetchone():
                c_sales.execute("INSERT OR IGNORE INTO offers SELECT * FROM old_db.offers")
                
            # Eski DB'de 'offer_items' tablosu var mı? Varsa taşı.
            c_sales.execute("SELECT name FROM old_db.sqlite_master WHERE type='table' AND name='offer_items'")
            if c_sales.fetchone():
                c_sales.execute("INSERT OR IGNORE INTO offer_items SELECT * FROM old_db.offer_items")
                
            c_sales.execute("DETACH DATABASE old_db")
            conn_sales.commit()
            print("SİSTEM BİLGİSİ: Veri taşıma başarıyla tamamlandı.")
        except Exception as e:
            print(f"VERİ TAŞIMA SIRASINDA UYARI: {e}")

    conn_sales.close()

# Program başladığında veritabanını hazırla
init_db()