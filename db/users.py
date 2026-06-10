import sqlite3, bcrypt, random
from config import USERS_DB, ADMIN_EMAIL, ADMIN_PASS, ADMIN_COMPANY


def _c():
    return sqlite3.connect(USERS_DB, check_same_thread=False)

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
        ]:
            _acol(c.cursor(),"users",col,typ)
        h = bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode()
        existing = c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if existing:
            c.execute(
                "UPDATE users SET email=?,password=?,can_view_costs=1,is_approved=1,is_active=1 WHERE role='admin'",
                (ADMIN_EMAIL, h),
            )
        else:
            c.execute(
                "INSERT INTO users(email,password,company_name,role,user_type,is_approved,is_active,can_view_costs) VALUES(?,?,?,'admin','admin',1,1,1)",
                (ADMIN_EMAIL, h, ADMIN_COMPANY),
            )

def _row(r):
    if not r: return None
    keys=["id","email","password","company_name","role","is_approved","is_active",
          "phone","logo_path","website","address","allowed_categories","can_view_costs","lang","theme","allowed_menus","created_at"]
    return dict(zip(keys,r))

_SEL = "id,email,password,company_name,role,is_approved,is_active,phone,logo_path,website,address,allowed_categories,can_view_costs,lang,theme,allowed_menus,created_at"

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

def register(email,password,company_name,user_type="dealer",phone=""):
    if by_email(email): return False,"email_in_use"
    role = "dealer" if user_type=="dealer" else "manufacturer"
    try:
        with _c() as c:
            c.execute("INSERT INTO users(email,password,company_name,role,user_type,phone) VALUES(?,?,?,?,?,?)",
                      (email,hash_pw(password),company_name,role,user_type,phone))
        return True,"ok"
    except: return False,"email_in_use"

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
    allowed=["company_name","phone","logo_path","website","address","lang","theme"]
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

def update_admin(uid,**kw):
    allowed=["is_approved","is_active","role","allowed_categories","can_view_costs","company_name","allowed_menus"]
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

def delete_user(uid):
    with _c() as c:
        c.execute("DELETE FROM users WHERE id=?",(uid,))
