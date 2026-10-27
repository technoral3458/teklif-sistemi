import sqlite3, bcrypt, random
from config import USERS_DB, ADMIN_EMAIL, ADMIN_PASS, ADMIN_COMPANY


def _c():
    con = sqlite3.connect(USERS_DB, check_same_thread=False, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

def _acol(cur, tbl, col, typ):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")

def init():
    with _c() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            company_name TEXT DEFAULT '',
            role TEXT DEFAULT 'dealer',
            user_type TEXT DEFAULT 'dealer',
            is_approved INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            phone TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            website TEXT DEFAULT '',
            address TEXT DEFAULT '',
            allowed_categories TEXT DEFAULT '',
            can_view_costs INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'tr',
            theme TEXT DEFAULT 'dark',
            created_at TEXT DEFAULT(datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,token TEXT,
            created_at TEXT DEFAULT(datetime('now'))
        )""")
        for col,typ in [
            ("phone","TEXT DEFAULT ''"),("logo_path","TEXT DEFAULT ''"),
            ("website","TEXT DEFAULT ''"),("address","TEXT DEFAULT ''"),
            ("allowed_categories","TEXT DEFAULT ''"),("can_view_costs","INTEGER DEFAULT 0"),
            ("is_active","INTEGER DEFAULT 1"),("lang","TEXT DEFAULT 'tr'"),
            ("theme","TEXT DEFAULT 'dark'"),("allowed_menus","TEXT DEFAULT ''"),
            ("parent_id","INTEGER DEFAULT NULL"),
            ("allowed_actions","TEXT DEFAULT ''"),
            ("allowed_models","TEXT DEFAULT ''"),
            ("is_manufacturer","INTEGER DEFAULT 0"),
            ("senior_mode","INTEGER DEFAULT 0"),
            ("is_admin","INTEGER DEFAULT 0"),
            ("reg_ip","TEXT DEFAULT ''"),
            ("last_login","TEXT DEFAULT ''"),
        ]:
            _acol(c.cursor(),"users",col,typ)
        existing = c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not existing:
            h = bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode()
            c.execute(
                "INSERT INTO users(email,password,company_name,role,user_type,is_approved,is_active,can_view_costs) VALUES(?,?,?,'admin','admin',1,1,1)",
                (ADMIN_EMAIL, h, ADMIN_COMPANY),
            )
        else:
            # Keep existing password; only ensure account stays active
            c.execute(
                "UPDATE users SET is_approved=1,is_active=1,can_view_costs=1 WHERE role='admin'",
            )

def _row(r):
    if not r: return None
    keys=["id","email","password","company_name","role","is_approved","is_active",
          "phone","logo_path","website","address","allowed_categories","can_view_costs","lang","theme","allowed_menus","created_at","parent_id","allowed_actions","allowed_models","is_manufacturer","senior_mode","is_admin","reg_ip","last_login"]
    return dict(zip(keys,r))

_SEL = "id,email,password,company_name,role,is_approved,is_active,phone,logo_path,website,address,allowed_categories,can_view_costs,lang,theme,allowed_menus,created_at,parent_id,allowed_actions,allowed_models,is_manufacturer,senior_mode,is_admin,reg_ip,last_login"

def by_email(email):
    with _c() as c:
        return _row(c.execute(f"SELECT {_SEL} FROM users WHERE email=?",(email,)).fetchone())

def by_id(uid):
    with _c() as c:
        return _row(c.execute(f"SELECT {_SEL} FROM users WHERE id=?",(uid,)).fetchone())

def get_admin():
    with _c() as c:
        return _row(c.execute(f"SELECT {_SEL} FROM users WHERE role='admin' LIMIT 1").fetchone())

def check_pw(plain,hashed):
    try: return bcrypt.checkpw(plain.encode(),hashed.encode())
    except: return False

def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(),bcrypt.gensalt()).decode()

def register(email,password,company_name,user_type="dealer",phone="",reg_ip=""):
    if by_email(email): return False,"email_in_use"
    role = "dealer" if user_type=="dealer" else "manufacturer"
    try:
        with _c() as c:
            c.execute("INSERT INTO users(email,password,company_name,role,user_type,phone,reg_ip) VALUES(?,?,?,?,?,?,?)",
                      (email,hash_pw(password),company_name,role,user_type,phone,reg_ip))
        return True,"ok"
    except: return False,"email_in_use"


def touch_login(uid):
    """Başarılı girişi işaretler — hiç giriş yapmamış hesapları ayıklamak için."""
    with _c() as c:
        c.execute("UPDATE users SET last_login=datetime('now') WHERE id=?",(uid,))


def reg_ip_counts():
    """{IP: o IP'den kaç kayıt} — aynı kaynaktan gelen kayıt yığınını yakalar."""
    with _c() as c:
        rows=c.execute(
            "SELECT reg_ip,COUNT(*) FROM users"
            " WHERE reg_ip IS NOT NULL AND reg_ip NOT IN ('','-')"
            " GROUP BY reg_ip").fetchall()
    return {r[0]: r[1] for r in rows}

def reset_token(email):
    u = by_email(email)
    if not u: return None
    tok = str(random.randint(100000,999999))
    with _c() as c:
        c.execute("DELETE FROM reset_tokens WHERE email=?",(email,))
        c.execute("INSERT INTO reset_tokens(email,token) VALUES(?,?)",(email,tok))
    return tok

def verify_token(email,tok):
    with _c() as c:
        r = c.execute("SELECT id FROM reset_tokens WHERE email=? AND token=? AND created_at>=datetime('now','-30 minutes')",(email,tok)).fetchone()
    return r is not None

def reset_pw(email,new_pw):
    with _c() as c:
        c.execute("UPDATE users SET password=? WHERE email=?",(hash_pw(new_pw),email))
        c.execute("DELETE FROM reset_tokens WHERE email=?",(email,))

def update_profile(uid,**kw):
    allowed=["company_name","phone","logo_path","website","address","lang","theme","senior_mode"]
    f={k:v for k,v in kw.items() if k in allowed}
    if not f: return
    sets=",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE users SET {sets} WHERE id=?",list(f.values())+[uid])

def change_pw(uid,new_pw):
    with _c() as c:
        c.execute("UPDATE users SET password=? WHERE id=?",(hash_pw(new_pw),uid))

def all_users():
    with _c() as c:
        rows=c.execute(f"SELECT {_SEL} FROM users ORDER BY id").fetchall()
    return [_row(r) for r in rows]

def all_manufacturers():
    with _c() as c:
        rows=c.execute(
            f"SELECT {_SEL} FROM users WHERE (role='manufacturer' OR is_manufacturer=1)"
            " AND (parent_id IS NULL OR parent_id=0) ORDER BY company_name"
        ).fetchall()
    return [_row(r) for r in rows]

def effective_mfr_id(user):
    """Return the manufacturer ID to use for order filtering: own ID or parent's ID."""
    return user.get("parent_id") or user["id"]

def has_action(user, action_key):
    """Check if user can perform a manufacturer action.
    Main accounts (no parent_id) always have full access.
    Sub-accounts need the action explicitly listed in allowed_actions."""
    if not user.get("parent_id"):
        return True
    allowed = [a for a in (user.get("allowed_actions") or "").split(",") if a]
    return action_key in allowed

def update_admin(uid,**kw):
    allowed=["is_approved","is_active","role","allowed_categories","can_view_costs","company_name","allowed_menus","parent_id","allowed_actions","allowed_models","is_manufacturer","senior_mode","is_admin"]
    f={k:v for k,v in kw.items() if k in allowed}
    if not f: return
    sets=",".join(f"{k}=?" for k in f)
    with _c() as c:
        c.execute(f"UPDATE users SET {sets} WHERE id=?",list(f.values())+[uid])

def create_user_by_admin(email, password, company_name, role, phone=""):
    if by_email(email): return False, "email_in_use"
    try:
        with _c() as c:
            c.execute(
                "INSERT INTO users(email,password,company_name,role,user_type,phone,is_approved,is_active) VALUES(?,?,?,?,?,?,1,1)",
                (email, hash_pw(password), company_name, role, role, phone)
            )
        return True, "ok"
    except: return False, "email_in_use"

def get_manufacturer_group_ids(user):
    """Return all manufacturer IDs in the same group (self + parent + siblings + children)."""
    uid = user["id"]
    parent_id = user.get("parent_id")
    with _c() as c:
        if parent_id:
            rows = c.execute(
                "SELECT id FROM users WHERE id=? OR parent_id=?",
                (parent_id, parent_id)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id FROM users WHERE id=? OR parent_id=?",
                (uid, uid)
            ).fetchall()
    return {r[0] for r in rows}

def delete_user(uid):
    with _c() as c:
        c.execute("DELETE FROM users WHERE id=? AND role!='admin'",(uid,))


def _safe_ids(ids, protect_id=None):
    """Toplu işlem için kimlikleri süzer.

    Listeye hiçbir koşulda girmeyenler: admin rolündeki hesaplar, yönetici
    modu verilmiş hesaplar ve işlemi yapanın kendisi. Yanlışlıkla "tümünü
    seç" yapılması yetkili bir hesabı silmemeli; tekil silme düğmesi
    (bilinçli bir işlem) bu hesaplar için çalışmaya devam eder."""
    want = {int(i) for i in ids if str(i).strip().isdigit()}
    want.discard(int(protect_id) if protect_id else -1)
    if not want:
        return []
    q = ",".join("?" * len(want))
    with _c() as c:
        rows = c.execute(
            f"SELECT id FROM users WHERE id IN ({q})"
            " AND role!='admin' AND COALESCE(is_admin,0)=0",
            list(want)).fetchall()
    return [r[0] for r in rows]


def bulk_delete(ids, protect_id=None) -> int:
    safe = _safe_ids(ids, protect_id)
    if not safe:
        return 0
    q = ",".join("?" * len(safe))
    with _c() as c:
        c.execute(f"DELETE FROM users WHERE id IN ({q})", safe)
    return len(safe)


def bulk_set(ids, protect_id=None, **kw) -> int:
    """Seçilenlerin onay/aktiflik durumunu topluca değiştirir."""
    allowed = ["is_approved","is_active"]
    f = {k:v for k,v in kw.items() if k in allowed}
    safe = _safe_ids(ids, protect_id)
    if not f or not safe:
        return 0
    sets = ",".join(f"{k}=?" for k in f)
    q = ",".join("?" * len(safe))
    with _c() as c:
        c.execute(f"UPDATE users SET {sets} WHERE id IN ({q})",
                  list(f.values()) + safe)
    return len(safe)
