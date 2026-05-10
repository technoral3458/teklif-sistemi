import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "database.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


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

    return subtotal_1, customs_tax, subtotal_2, extra_tax, subtotal_3, total_cost


def show_profit_management(user_role="admin"):
    if user_role != "admin":
        st.error("Bu sayfayı görüntüleme yetkiniz yok.")
        return

    st.header("💰 Maliyet ve Kârlılık Yönetimi")
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

    model_names = [f"{m['id']} - {m['name']}" for m in models]
    selected = st.selectbox("Makine Seç", model_names)
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

    a, b, c = st.columns(3)
    a.metric("Toplam Maliyet", f"{total_cost:,.2f} $")
    b.metric("Net Kâr", f"{profit:,.2f} $")
    c.metric("Kâr Oranı", f"%{profit_rate:.2f}")

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

    option_names = [f"{o['id']} - {o['opt_name']}" for o in options]
    selected = st.selectbox("Opsiyon Seç", option_names)
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

    a, b, c = st.columns(3)
    a.metric("Toplam Maliyet", f"{total_cost:,.2f} $")
    b.metric("Net Kâr", f"{profit:,.2f} $")
    c.metric("Kâr Oranı", f"%{profit_rate:.2f}")

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

    models = pd.read_sql_query("""
        SELECT name, purchase_price, sale_price, shipping_cost, customs_tax_rate,
               extra_tax_rate, port_cost, document_cost, installation_cost, other_cost
        FROM models
    """, conn)

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

    total_sale = df["Satış Fiyatı"].sum()
    total_cost = df["Toplam Maliyet"].sum()
    total_profit = df["Net Kâr"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Satış", f"{total_sale:,.2f} $")
    c2.metric("Toplam Maliyet", f"{total_cost:,.2f} $")
    c3.metric("Toplam Kâr", f"{total_profit:,.2f} $")

    st.dataframe(df, use_container_width=True, hide_index=True)