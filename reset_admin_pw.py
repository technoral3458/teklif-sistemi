#!/usr/bin/env python3
"""Run on the server to reset the admin password: python reset_admin_pw.py <new_password>"""
import sys, sqlite3, bcrypt, os

DB = os.path.join(os.path.dirname(__file__), "data", "users.db")
if len(sys.argv) < 2:
    print("Usage: python reset_admin_pw.py <new_password>")
    sys.exit(1)

new_pw = sys.argv[1]
h = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
with sqlite3.connect(DB) as c:
    rows = c.execute("SELECT id, email FROM users WHERE role='admin'").fetchall()
    if not rows:
        print("No admin user found.")
        sys.exit(1)
    c.execute("UPDATE users SET password=? WHERE role='admin'", (h,))
    print(f"Password reset for: {rows[0][1]}")
