import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "factory_data.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def ensure_profit_schema():
    conn = get_conn()
    cur = conn.cursor()

    cols = {
        "purchase_price": "REAL DEFAULT 0.0",
        "sale_price": "REAL DEFAULT 0.0",
        "shipping_cost": "REAL DEFAULT 0.0",
        "customs_tax_rate": "REAL DEFAULT 3.0",
        "extra_tax_rate": "REAL DEFAULT 10.0",
        "port_cost": "REAL DEFAULT 0.0",
        "document_cost": "REAL DEFAULT 0.0",
        "installation_cost": "REAL DEFAULT 0.0",
        "other_cost": "REAL DEFAULT 0.0",
        "cost_note": "TEXT DEFAULT ''"
    }

    for table in ["models", "options"]:
        existing = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        for col, typ in cols.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def inject_profit_css():
    st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        gap: 8px !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        padding-bottom: 8px !important;
        margin-bottom: 18px !important;
        border-bottom: 1px solid #e2e8f0 !important;
        scrollbar-width: none !important;
    }

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none !important;
    }

    .stTabs [data-baseweb="tab"] {
        flex: 0 0 auto !important;
        min-width: max-content !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        color: #475569 !important;
        box-shadow: 0 2px 6px rgba(15,23,42,0.04) !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        border-color: #2563eb !important;
    }

    @media (max-width: 768px) {
        h1 {
            font-size: 34px !important;
            line-height: 1.15 !important;
        }

        .block-container {
            padding-left: 14px !important;
            padding-right: 14px !important;
        }

        div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }

        button {
            min-height: 48px !important;
            border-radius: 14px !important;
            font-weight: 900 !important;
        }

        input, textarea {
            font-size: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def calculate_import_cost(purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate, port_cost, document_cost, installation_cost, other_cost):
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

    return subtotal_1, customs_tax, subtotal_2, extra_tax, subtotal_3, total_cost


def show_profit_management(user_role="admin"):
    inject_profit_css()
    ensure_profit_schema()

    if user_role != "admin":
        st.error("Bu sayfayı görüntüleme yetkiniz yok.")
        return

    st.title("💰 Maliyet ve Kârlılık Yönetimi")
    st.caption("Bu alan sadece yönetici tarafından görülmelidir.")

    tab_models, tab_options, tab_report = st.tabs([
        "📦 Makine Maliyetleri",
        "⚙️ Opsiyon Maliyetleri",
        "📊 Kârlılık Raporu"
    ])

    with tab_models:
        show_model_costs()

    with tab_options:
        show_option_costs()

    with tab_report:
        show_profit_report()


def show_model_costs():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    models = conn.execute("SELECT * FROM models ORDER BY name ASC").fetchall()
    conn.close()

    if not models:
        st.info("Henüz kayıtlı makine yok.")
        return

    selected = st.selectbox("Makine Seç", [f"{m['id']} - {m['name']}" for m in models])
    model_id = int(selected.split(" - ")[0])

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    model = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    conn.close()

    st.subheader(model["name"])

    c1, c2 = st.columns(2)

    with c1:
        purchase_price = st.number_input("Üretici Alış Fiyatı", value=float(model["purchase_price"] or 0), step=100.0)
        sale_price = st.number_input("Satış Fiyatı", value=float(model["sale_price"] or 0), step=100.0)
        shipping_cost = st.number_input("Nakliye", value=float(model["shipping_cost"] or 0), step=100.0)
        customs_tax_rate = st.number_input("Gümrük Vergisi %", value=float(model["customs_tax_rate"] or 3), step=0.1)

    with c2:
        extra_tax_rate = st.number_input("Ek Vergi %", value=float(model["extra_tax_rate"] or 10), step=0.1)
        port_cost = st.number_input("Liman / Kıyı Gideri", value=float(model["port_cost"] or 0), step=100.0)
        document_cost = st.number_input("Belge Gideri", value=float(model["document_cost"] or 0), step=100.0)
        installation_cost = st.number_input("Kurulum Gideri", value=float(model["installation_cost"] or 0), step=100.0)
        other_cost = st.number_input("Diğer Giderler", value=float(model["other_cost"] or 0), step=100.0)

    cost_note = st.text_area("Maliyet Notu", value=model["cost_note"] or "")

    subtotal_1, customs_tax, subtotal_2, extra_tax, subtotal_3, total_cost = calculate_import_cost(
        purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate,
        port_cost, document_cost, installation_cost, other_cost
    )

    profit = sale_price - total_cost
    profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Maliyet", f"{total_cost:,.2f} $")
    m2.metric("Net Kâr", f"{profit:,.2f} $")
    m3.metric("Kâr Oranı", f"%{profit_rate:.2f}")

    with st.expander("Hesaplama Detayı"):
        st.write(f"Alış + Nakliye: {subtotal_1:,.2f} $")
        st.write(f"Gümrük Vergisi: {customs_tax:,.2f} $")
        st.write(f"Gümrük Sonrası: {subtotal_2:,.2f} $")
        st.write(f"Ek Vergi: {extra_tax:,.2f} $")
        st.write(f"Vergiler Sonrası: {subtotal_3:,.2f} $")
        st.write(f"Toplam Maliyet: {total_cost:,.2f} $")

    if st.button("💾 Makine Maliyetini Kaydet", type="primary", use_container_width=True):
        conn = get_conn()
        conn.execute("""
            UPDATE models
            SET purchase_price=?, sale_price=?, shipping_cost=?, customs_tax_rate=?,
                extra_tax_rate=?, port_cost=?, document_cost=?, installation_cost=?,
                other_cost=?, cost_note=?
            WHERE id=?
        """, (
            purchase_price, sale_price, shipping_cost, customs_tax_rate,
            extra_tax_rate, port_cost, document_cost, installation_cost,
            other_cost, cost_note, model_id
        ))
        conn.commit()
        conn.close()
        st.success("Makine maliyeti kaydedildi.")
        st.rerun()


def show_option_costs():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    options = conn.execute("SELECT * FROM options ORDER BY opt_name ASC").fetchall()
    conn.close()

    if not options:
        st.info("Henüz kayıtlı opsiyon yok.")
        return

    selected = st.selectbox("Opsiyon Seç", [f"{o['id']} - {o['opt_name']}" for o in options])
    option_id = int(selected.split(" - ")[0])

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    option = conn.execute("SELECT * FROM options WHERE id=?", (option_id,)).fetchone()
    conn.close()

    st.subheader(option["opt_name"])

    c1, c2 = st.columns(2)

    with c1:
        purchase_price = st.number_input("Alış Fiyatı", value=float(option["purchase_price"] or 0), step=50.0)
        sale_price = st.number_input("Satış Fiyatı", value=float(option["sale_price"] or 0), step=50.0)
        shipping_cost = st.number_input("Nakliye", value=float(option["shipping_cost"] or 0), step=50.0)
        customs_tax_rate = st.number_input("Gümrük Vergisi %", value=float(option["customs_tax_rate"] or 3), step=0.1)

    with c2:
        extra_tax_rate = st.number_input("Ek Vergi %", value=float(option["extra_tax_rate"] or 10), step=0.1)
        port_cost = st.number_input("Liman / Kıyı Gideri", value=float(option["port_cost"] or 0), step=50.0)
        document_cost = st.number_input("Belge Gideri", value=float(option["document_cost"] or 0), step=50.0)
        installation_cost = st.number_input("Kurulum Gideri", value=float(option["installation_cost"] or 0), step=50.0)
        other_cost = st.number_input("Diğer Giderler", value=float(option["other_cost"] or 0), step=50.0)

    cost_note = st.text_area("Maliyet Notu", value=option["cost_note"] or "")

    _, _, _, _, _, total_cost = calculate_import_cost(
        purchase_price, shipping_cost, customs_tax_rate, extra_tax_rate,
        port_cost, document_cost, installation_cost, other_cost
    )

    profit = sale_price - total_cost
    profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Maliyet", f"{total_cost:,.2f} $")
    m2.metric("Net Kâr", f"{profit:,.2f} $")
    m3.metric("Kâr Oranı", f"%{profit_rate:.2f}")

    if st.button("💾 Opsiyon Maliyetini Kaydet", type="primary", use_container_width=True):
        conn = get_conn()
        conn.execute("""
            UPDATE options
            SET purchase_price=?, sale_price=?, shipping_cost=?, customs_tax_rate=?,
                extra_tax_rate=?, port_cost=?, document_cost=?, installation_cost=?,
                other_cost=?, cost_note=?
            WHERE id=?
        """, (
            purchase_price, sale_price, shipping_cost, customs_tax_rate,
            extra_tax_rate, port_cost, document_cost, installation_cost,
            other_cost, cost_note, option_id
        ))
        conn.commit()
        conn.close()
        st.success("Opsiyon maliyeti kaydedildi.")
        st.rerun()


def show_profit_report():
    conn = get_conn()

    try:
        models = pd.read_sql_query("""
            SELECT name, purchase_price, sale_price, shipping_cost, customs_tax_rate,
                   extra_tax_rate, port_cost, document_cost, installation_cost, other_cost
            FROM models
        """, conn)
    except Exception as e:
        conn.close()
        st.error(f"Rapor okunamadı: {e}")
        return

    conn.close()

    if models.empty:
        st.info("Rapor için kayıtlı makine yok.")
        return

    rows = []

    for _, r in models.iterrows():
        _, _, _, _, _, total_cost = calculate_import_cost(
            r["purchase_price"], r["shipping_cost"], r["customs_tax_rate"],
            r["extra_tax_rate"], r["port_cost"], r["document_cost"],
            r["installation_cost"], r["other_cost"]
        )

        sale_price = float(r["sale_price"] or 0)
        profit = sale_price - total_cost
        profit_rate = (profit / sale_price * 100) if sale_price > 0 else 0

        rows.append({
            "Makine": r["name"],
            "Satış Fiyatı": sale_price,
            "Toplam Maliyet": total_cost,
            "Net Kâr": profit,
            "Kâr Oranı %": profit_rate
        })

    df = pd.DataFrame(rows)

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Satış", f"{df['Satış Fiyatı'].sum():,.2f} $")
    c2.metric("Toplam Maliyet", f"{df['Toplam Maliyet'].sum():,.2f} $")
    c3.metric("Toplam Kâr", f"{df['Net Kâr'].sum():,.2f} $")

    st.dataframe(df, use_container_width=True, hide_index=True)