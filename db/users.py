import sqlite3
import bcrypt
import random
import os
from config import USERS_DB, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASS, DEFAULT_ADMIN_COMPANY


def _conn():
    return sqlite3.connect(USERS_DB, check_same_thread=False)


def _add_col(cur, table, col, typ):
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def init():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
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
                address_full TEXT DEFAULT '',
                allowed_categories TEXT DEFAULT '',
                can_view_costs INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        extra_cols = [
            ("phone", "TEXT DEFAULT ''"),
            ("logo_path", "TEXT DEFAULT ''"),
            ("website", "TEXT DEFAULT ''"),
            ("address_full", "TEXT DEFAULT ''"),
            ("allowed_categories", "TEXT DEFAULT ''"),
            ("can_view_costs", "INTEGER DEFAULT 0"),
            ("is_active", "INTEGER DEFAULT 1"),
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
        ]
        for col, typ in extra_cols:
            _add_col(c, "users", col, typ)

        # Create default admin if not exists
        admin = c.execute("SELECT id FROM users WHERE email=?", (DEFAULT_ADMIN_EMAIL,)).fetchone()
        if not admin:
            hashed = bcrypt.hashpw(DEFAULT_ADMIN_PASS.encode(), bcrypt.gensalt()).decode()
            c.execute(
                """INSERT INTO users (email, password, company_name, role, user_type,
                   is_approved, is_active, can_view_costs)
                   VALUES (?, ?, ?, 'admin', 'admin', 1, 1, 1)""",
                (DEFAULT_ADMIN_EMAIL, hashed, DEFAULT_ADMIN_COMPANY)
            )
        else:
            # Ensure admin has can_view_costs=1
            c.execute("UPDATE users SET can_view_costs=1, is_approved=1, is_active=1 WHERE role='admin'")
        conn.commit()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_user_by_email(email: str):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, email, password, company_name, role, is_approved, is_active, "
            "phone, logo_path, website, address_full, allowed_categories, can_view_costs "
            "FROM users WHERE email=?", (email,)
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "email": row[1], "password": row[2],
        "company_name": row[3], "role": row[4],
        "is_approved": bool(row[5]), "is_active": bool(row[6]),
        "phone": row[7], "logo_path": row[8], "website": row[9],
        "address_full": row[10], "allowed_categories": row[11] or "",
        "can_view_costs": bool(row[12]),
    }


def get_user_by_id(user_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, email, password, company_name, role, is_approved, is_active, "
            "phone, logo_path, website, address_full, allowed_categories, can_view_costs "
            "FROM users WHERE id=?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "email": row[1], "password": row[2],
        "company_name": row[3], "role": row[4],
        "is_approved": bool(row[5]), "is_active": bool(row[6]),
        "phone": row[7], "logo_path": row[8], "website": row[9],
        "address_full": row[10], "allowed_categories": row[11] or "",
        "can_view_costs": bool(row[12]),
    }


def register_user(email: str, password: str, company_name: str,
                  user_type: str = "dealer", phone: str = "") -> tuple[bool, str]:
    if get_user_by_email(email):
        return False, "email_in_use"
    hashed = hash_password(password)
    role = "dealer" if user_type == "dealer" else "manufacturer"
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users (email, password, company_name, role, user_type, phone) VALUES (?,?,?,?,?,?)",
                (email, hashed, company_name, role, user_type, phone)
            )
            conn.commit()
        return True, "ok"
    except sqlite3.IntegrityError:
        return False, "email_in_use"


def create_reset_token(email: str) -> str | None:
    user = get_user_by_email(email)
    if not user:
        return None
    token = str(random.randint(100000, 999999))
    with _conn() as conn:
        conn.execute("DELETE FROM reset_tokens WHERE email=?", (email,))
        conn.execute("INSERT INTO reset_tokens (email, token) VALUES (?,?)", (email, token))
        conn.commit()
    return token


def verify_reset_token(email: str, token: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM reset_tokens WHERE email=? AND token=? "
            "AND created_at >= datetime('now', '-30 minutes')",
            (email, token)
        ).fetchone()
    return row is not None


def reset_password(email: str, new_password: str):
    hashed = hash_password(new_password)
    with _conn() as conn:
        conn.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
        conn.execute("DELETE FROM reset_tokens WHERE email=?", (email,))
        conn.commit()


def update_user_profile(user_id: int, **kwargs):
    allowed = ["company_name", "phone", "logo_path", "website", "address_full"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [user_id]
    with _conn() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE id=?", vals)
        conn.commit()


def change_password(user_id: int, new_password: str):
    hashed = hash_password(new_password)
    with _conn() as conn:
        conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        conn.commit()


def get_all_users():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, email, company_name, role, is_approved, is_active, phone, "
            "allowed_categories, can_view_costs, created_at FROM users ORDER BY id"
        ).fetchall()
    return [
        {
            "id": r[0], "email": r[1], "company_name": r[2], "role": r[3],
            "is_approved": bool(r[4]), "is_active": bool(r[5]), "phone": r[6],
            "allowed_categories": r[7] or "", "can_view_costs": bool(r[8]),
            "created_at": r[9],
        }
        for r in rows
    ]


def update_user_admin(user_id: int, **kwargs):
    allowed = ["is_approved", "is_active", "role", "allowed_categories", "can_view_costs", "company_name"]
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [user_id]
    with _conn() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE id=?", vals)
        conn.commit()


def delete_user(user_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
