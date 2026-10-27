"""
Migration script: old system → new B2B system
Run once on the server:  python3 migrate_from_old.py
"""
import sqlite3
import json
import os
import sys
import datetime

OLD_USERS_DB    = "old_data/users.db"
OLD_FACTORY_DB  = "old_data/factory_data.db"
NEW_USERS_DB    = "data/users.db"
NEW_FACTORY_DB  = "data/factory.db"

def main():
    # ── Verify source files ────────────────────────────────────────
    for p in [OLD_USERS_DB, OLD_FACTORY_DB]:
        if not os.path.exists(p):
            print(f"ERROR: {p} not found. Copy old DB files to old_data/ first.")
            sys.exit(1)

    os.makedirs("data", exist_ok=True)

    # ── Init new DBs (creates tables if not yet created) ──────────
    import db.factory as fdb
    import db.users as udb
    fdb.init()
    udb.init()

    src_u = sqlite3.connect(OLD_USERS_DB)
    src_f = sqlite3.connect(OLD_FACTORY_DB)
    src_u.row_factory = sqlite3.Row
    src_f.row_factory = sqlite3.Row

    dst_u = sqlite3.connect(NEW_USERS_DB)
    dst_f = sqlite3.connect(NEW_FACTORY_DB)

    # ── 1. USERS ──────────────────────────────────────────────────
    print("\n[1/5] Migrating users...")
    dst_u.execute("DELETE FROM users")

    old_users = src_u.execute("SELECT * FROM users").fetchall()
    inserted_users = 0
    for u in old_users:
        u = dict(u)
        role = u.get("role", "dealer")
        if role not in ("admin", "manufacturer", "dealer"):
            role = "dealer"

        # address_full → address
        address = u.get("address_full") or u.get("address") or ""
        # preferred_lang → lang
        lang = u.get("preferred_lang") or "tr"
        # logo path: keep as-is (images need manual copy)
        logo_path = u.get("logo_path") or ""

        dst_u.execute("""
            INSERT OR REPLACE INTO users
            (id, email, password, company_name, role, user_type, is_approved, is_active,
             phone, logo_path, website, address, allowed_categories, can_view_costs, lang, theme)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            u["id"],
            u["email"],
            u["password"],
            u.get("company_name") or "",
            role,
            role,        # user_type mirrors role
            int(u.get("is_approved") or 0),
            1,           # is_active (old had is_verified, default active for approved)
            u.get("phone") or "",
            logo_path,
            u.get("website") or "",
            address,
            u.get("allowed_categories") or "",
            int(u.get("can_view_costs") or 0),
            lang,
            "dark",
        ))
        inserted_users += 1

    dst_u.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name='users'")
    dst_u.commit()
    print(f"  ✓ {inserted_users} users imported")
    for u in old_users:
        print(f"    [{dict(u)['role']:12s}] {dict(u)['email']} — {dict(u)['company_name']}")

    # ── 2. CATEGORIES ─────────────────────────────────────────────
    print("\n[2/5] Migrating categories...")
    dst_f.execute("DELETE FROM categories")

    old_cats = src_f.execute("SELECT id, name FROM categories ORDER BY sort_order").fetchall()
    cat_name_to_id = {}
    for cat in old_cats:
        cat = dict(cat)
        dst_f.execute(
            "INSERT OR REPLACE INTO categories (id, name) VALUES (?, ?)",
            (cat["id"], cat["name"])
        )
        cat_name_to_id[cat["name"]] = cat["id"]

    # Update sequence
    dst_f.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM categories) WHERE name='categories'")
    dst_f.commit()
    print(f"  ✓ {len(old_cats)} categories imported")
    for c in old_cats:
        print(f"    [{dict(c)['id']}] {dict(c)['name']}")

    # ── 3. OPTIONS ────────────────────────────────────────────────
    print("\n[3/5] Migrating options...")
    dst_f.execute("DELETE FROM options")

    old_opts = src_f.execute("SELECT * FROM options ORDER BY id").fetchall()
    inserted_opts = 0
    for o in old_opts:
        o = dict(o)
        cat_name = o.get("category") or ""
        category_id = cat_name_to_id.get(cat_name)  # None if not found (global)

        # allow_qty: 1 → MANUAL, 0 → FIXED_1
        qty_type = "MANUAL" if o.get("allow_qty") else "FIXED_1"

        # usage_scope: "both" or anything → GLOBAL; "specific" → MODEL_SPECIFIC
        scope_val = o.get("usage_scope") or "both"
        scope = "MODEL_SPECIFIC" if scope_val == "specific" else "GLOBAL"

        dst_f.execute("""
            INSERT OR REPLACE INTO options
            (id, name, description, price, currency, scope, category_id, qty_type, conflict_group)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            o["id"],
            o.get("opt_name") or "",
            o.get("opt_desc") or "",
            float(o.get("opt_price") or 0),
            o.get("currency") or "USD",
            scope,
            category_id,
            qty_type,
            o.get("conflict_feature") or "",
        ))
        inserted_opts += 1

    dst_f.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM options) WHERE name='options'")
    dst_f.commit()
    print(f"  ✓ {inserted_opts} options imported")

    # ── 4. MODELS ─────────────────────────────────────────────────
    print("\n[4/5] Migrating models...")
    dst_f.execute("DELETE FROM models")

    old_models = src_f.execute("SELECT * FROM models ORDER BY id").fetchall()
    inserted_models = 0
    for m in old_models:
        m = dict(m)
        cat_name = m.get("category") or ""
        category_id = cat_name_to_id.get(cat_name)

        # compatible_options: "10,11,13" → "[10,11,13]"
        compat_raw = m.get("compatible_options") or ""
        try:
            compat_list = [int(x.strip()) for x in compat_raw.split(",") if x.strip().isdigit()]
            compat_json = json.dumps(compat_list)
        except Exception:
            compat_json = "[]"

        pp   = float(m.get("purchase_price") or 0)
        sc   = float(m.get("shipping_cost") or 0)
        cust = float(m.get("customs_tax_rate") or 0)
        ext  = float(m.get("extra_tax_rate") or 0)
        port = float(m.get("port_cost") or 0)
        doc  = float(m.get("document_cost") or 0)
        inst = float(m.get("installation_cost") or 0)
        othr = float(m.get("other_cost") or 0)
        total_cost = pp + sc + pp * cust / 100 + pp * ext / 100 + port + doc + inst + othr

        dst_f.execute("""
            INSERT OR REPLACE INTO models
            (id, name, category_id, description, base_price, currency, specs,
             purchase_price, purchase_currency, shipping_cost, customs_pct, extra_tax_pct,
             port_cost, document_cost, installation_cost, other_cost, total_cost,
             image_path, compatible_options)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            m["id"],
            m.get("name") or "",
            category_id,
            "",
            float(m.get("base_price") or 0),
            m.get("currency") or "USD",
            m.get("specs") or "",
            pp,
            "USD",
            sc,
            cust,
            ext,
            port,
            doc,
            inst,
            othr,
            total_cost,
            "",   # image_path: old image files not available, needs re-upload
            compat_json,
        ))
        inserted_models += 1

    dst_f.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM models) WHERE name='models'")
    dst_f.commit()
    print(f"  ✓ {inserted_models} models imported")
    for m in old_models:
        print(f"    [{dict(m)['id']}] {dict(m)['name']} — {dict(m)['base_price']} {dict(m)['currency']}")

    # ── 5. CUSTOMERS + OFFERS ─────────────────────────────────────
    print("\n[5/5] Migrating customers & offers...")
    dst_f.execute("DELETE FROM customers")
    dst_f.execute("DELETE FROM offers")
    dst_f.execute("DELETE FROM offer_items")

    old_customers = src_f.execute("SELECT * FROM customers").fetchall()
    inserted_custs = 0
    for c in old_customers:
        c = dict(c)
        name = c.get("company_name") or c.get("name") or "İsimsiz"
        if name == "Test":
            continue   # skip test record
        dst_f.execute("""
            INSERT OR REPLACE INTO customers (id, name, contact_person, email, phone, address)
            VALUES (?,?,?,?,?,?)
        """, (
            c["id"], name,
            c.get("contact_person") or "",
            c.get("email") or "",
            c.get("phone") or "",
            c.get("address") or "",
        ))
        inserted_custs += 1

    dst_f.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM customers) WHERE name='customers'")

    old_offers = src_f.execute("SELECT * FROM offers").fetchall()
    inserted_offers = 0
    for o in old_offers:
        o = dict(o)
        # parse offer_date "05.03.2026 11:06" → "2026-03-05 11:06:00"
        created_at = ""
        raw_date = o.get("offer_date") or ""
        try:
            dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y %H:%M")
            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_at = raw_date

        # extract discount_pct from conditions JSON
        discount_pct = 0.0
        conditions = {}
        try:
            conditions = json.loads(o.get("conditions") or "{}")
            discount_pct = float(conditions.get("discount_pct") or 0)
        except Exception:
            pass

        # get model base_price for reference
        model_row = dst_f.execute("SELECT base_price, currency FROM models WHERE id=?", (o.get("model_id"),)).fetchone()
        base_price = float(model_row[0]) if model_row else 0.0
        currency   = model_row[1] if model_row else "USD"

        total_price = float(o.get("total_price") or 0)
        subtotal    = float(conditions.get("subtotal_calculated") or total_price)
        options_total = max(0.0, subtotal - base_price)

        offer_no = f"TKL-{created_at[:10].replace('-','')}-{o['id']:03d}" if created_at else f"TKL-{o['id']:06d}"

        # notes from conditions
        extra_notes = conditions.get("notes") or ""
        main_notes  = o.get("notes") or ""
        notes = "\n".join(filter(None, [main_notes, extra_notes]))

        dst_f.execute("""
            INSERT OR REPLACE INTO offers
            (id, offer_no, customer_id, model_id, machine_count, currency,
             base_price, options_total, discount_pct, total_price,
             status, notes, validity_date, dealer_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            o["id"],
            offer_no,
            o.get("customer_id"),
            o.get("model_id"),
            1,           # machine_count default 1
            currency,
            base_price,
            options_total,
            discount_pct,
            total_price,
            o.get("status") or "Beklemede",
            notes,
            "",
            o.get("user_id"),
            created_at,
        ))
        inserted_offers += 1

    dst_f.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM offers) WHERE name='offers'")
    dst_f.commit()

    print(f"  ✓ {inserted_custs} customers imported  (test records skipped)")
    print(f"  ✓ {inserted_offers} offers imported")

    src_u.close()
    src_f.close()
    dst_u.close()
    dst_f.close()

    print("\n" + "="*50)
    print("Migration complete!")
    print("NOTE: Machine images were not copied (needs manual re-upload).")
    print("NOTE: User logos need manual copy from old server's 'images/' folder.")
    print("="*50)

if __name__ == "__main__":
    main()
