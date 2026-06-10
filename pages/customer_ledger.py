import streamlit as st
import datetime
from i18n import _
import db.factory as fdb
from utils.costs import format_currency
from config import CURRENCIES

PAYMENT_METHODS = ["Nakit", "Banka Havalesi / EFT", "Çek", "Senet", "Kredi Kartı", "Diğer"]


def show(user: dict):
    st.title("💳 Müşteri Cari Yönetimi")

    tab1, tab2 = st.tabs(["📊 Genel Bakış", "📋 Hareketler"])

    with tab1:
        _overview(user)
    with tab2:
        _transactions(user)


def _overview(user: dict):
    """Tüm müşterilerin bakiye özeti."""
    customers_data = fdb.get_all_customer_balances(user_id=user["id"], role=user["role"])

    if not customers_data:
        st.info(_("no_records"))
        return

    # Filtre
    col1, col2 = st.columns(2)
    filter_status = col1.selectbox(
        "Filtrele",
        ["Tümü", "Borçlu (Bakiye > 0)", "Borçsuz / Alacaklı"],
        key="cari_filter",
    )
    search = col2.text_input(_("search"), key="cari_search")

    st.divider()

    total_receivable = 0.0
    shown = 0

    for cust in customers_data:
        balances = cust.get("balances", {})
        if not balances:
            balances = {}

        # Aggregate balance across currencies (simplified: show per currency)
        for currency, bal in balances.items():
            debit = bal.get("debit", 0.0)
            credit = bal.get("credit", 0.0)
            balance = debit - credit

            if filter_status == "Borçlu (Bakiye > 0)" and balance <= 0:
                continue
            if filter_status == "Borçsuz / Alacaklı" and balance > 0:
                continue
            if search and search.lower() not in cust["company_name"].lower():
                continue

            total_receivable += balance
            shown += 1

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
                col1.write(f"**{cust['company_name']}**")
                if cust.get("contact_person"):
                    col1.caption(cust["contact_person"])
                col2.metric("Borç", format_currency(debit, currency))
                col3.metric("Ödeme", format_currency(credit, currency))

                balance_color = "🔴" if balance > 0 else ("🟢" if balance < 0 else "⚪")
                bal_label = "Bakiye (Alacak)" if balance < 0 else "Bakiye (Borç)"
                col4.metric(
                    bal_label,
                    format_currency(abs(balance), currency),
                    delta=f"{balance_color}",
                )

        # If no transactions, show as zero balance
        if not balances:
            if search and search.lower() not in cust["company_name"].lower():
                continue
            shown += 1
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
                col1.write(f"**{cust['company_name']}**")
                if cust.get("contact_person"):
                    col1.caption(cust["contact_person"])
                col2.write("—")
                col3.write("—")
                col4.write("⚪ 0,00")

    st.divider()
    st.info(f"**{shown}** müşteri gösteriliyor. Toplam alacak: {format_currency(total_receivable, 'USD')}")

    # Yeni hareket butonu
    if st.button("➕ Yeni Hareket Ekle", type="primary", key="add_txn_overview"):
        st.session_state["cari_form"] = "new"
        st.session_state.page = "customer_ledger"
        st.session_state["cari_tab"] = 1
        st.rerun()


def _transactions(user: dict):
    """Hareket listesi ve yeni hareket formu."""
    customers = fdb.get_customers(user_id=user["id"], role=user["role"])
    if not customers:
        st.info("Önce müşteri ekleyin.")
        return

    # Müşteri seç
    cust_map = {c["id"]: c["company_name"] for c in customers}
    cust_ids = list(cust_map.keys())

    col1, col2 = st.columns([3, 2])
    selected_cust_id = col1.selectbox(
        "Müşteri Seçin",
        cust_ids,
        format_func=lambda x: cust_map[x],
        key="cari_cust_sel",
    )

    # Para birimi filtresi
    cur_filter = col2.selectbox("Para Birimi", ["Tümü"] + CURRENCIES, key="cari_cur_filter")

    if col1.button("➕ Yeni Hareket", type="primary", key="new_txn_btn"):
        st.session_state["cari_form"] = "new"
        st.session_state["cari_default_cust"] = selected_cust_id

    # Yeni hareket formu
    if st.session_state.get("cari_form") == "new":
        _transaction_form(user, customers, default_cust_id=st.session_state.get("cari_default_cust"))

    # Seçilen müşteri özeti
    if selected_cust_id:
        currency_for_bal = cur_filter if cur_filter != "Tümü" else None
        bal = fdb.get_customer_balance(selected_cust_id, currency=currency_for_bal)
        cust_name = cust_map[selected_cust_id]

        with st.container(border=True):
            st.subheader(f"📊 {cust_name} — Bakiye Özeti")
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Borç (Fatura)", format_currency(bal["total_debit"], cur_filter if cur_filter != "Tümü" else ""))
            col2.metric("Toplam Ödeme", format_currency(bal["total_credit"], cur_filter if cur_filter != "Tümü" else ""))
            balance = bal["balance"]
            delta_str = "🔴 Tahsil Edilecek" if balance > 0 else ("🟢 Fazla Ödeme" if balance < 0 else "✅ Sıfır")
            col3.metric("Net Bakiye", format_currency(abs(balance), cur_filter if cur_filter != "Tümü" else ""),
                        delta=delta_str, delta_color="off")

        st.divider()
        st.subheader("📋 Hareket Geçmişi")

        txns = fdb.get_customer_transactions(customer_id=selected_cust_id)
        if cur_filter != "Tümü":
            txns = [t for t in txns if t["currency"] == cur_filter]

        if not txns:
            st.info(_("no_records"))
        else:
            # Running balance (oldest first, reversed)
            running = 0.0
            txns_display = list(reversed(txns))
            rows_data = []
            for t in txns_display:
                if t["txn_type"] == "debit":
                    running += t["amount"]
                    type_label = "🔴 Borç"
                else:
                    running -= t["amount"]
                    type_label = "🟢 Ödeme"
                rows_data.append({
                    "Tarih": t["txn_date"],
                    "Tür": type_label,
                    "Açıklama": t["description"] or "—",
                    "Ödeme Yöntemi": t["payment_method"] or "—",
                    "Ref. No": t["reference_no"] or "—",
                    "Tutar": format_currency(t["amount"], t["currency"]),
                    "Bakiye": format_currency(abs(running), t["currency"]),
                    "_id": t["id"],
                })

            for row in reversed(rows_data):
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                    col1.write(row["Tarih"])
                    col1.caption(row["Tür"])
                    col2.write(row["Açıklama"])
                    col2.caption(f"{row['Ödeme Yöntemi']} {('· ' + row['Ref. No']) if row['Ref. No'] != '—' else ''}")
                    col3.write(f"**{row['Tutar']}**")
                    col4.write(f"Bakiye: {row['Bakiye']}")
                    if col5.button("🗑️", key=f"del_ctxn_{row['_id']}"):
                        st.session_state[f"confirm_del_ctxn_{row['_id']}"] = True

                    if st.session_state.get(f"confirm_del_ctxn_{row['_id']}"):
                        st.warning("Bu hareketi silmek istediğinize emin misiniz?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("Evet", key=f"yes_ctxn_{row['_id']}"):
                            fdb.delete_customer_transaction(row["_id"])
                            del st.session_state[f"confirm_del_ctxn_{row['_id']}"]
                            st.rerun()
                        if cc2.button("Hayır", key=f"no_ctxn_{row['_id']}"):
                            del st.session_state[f"confirm_del_ctxn_{row['_id']}"]
                            st.rerun()


def _transaction_form(user: dict, customers: list, default_cust_id: int = None):
    cust_map = {c["id"]: c["company_name"] for c in customers}
    cust_ids = list(cust_map.keys())
    default_idx = cust_ids.index(default_cust_id) if default_cust_id in cust_ids else 0

    # Teklif listesi (sipariş verilmiş)
    offers = fdb.get_offers(user_id=user["id"], role=user["role"])
    offer_map = {o["id"]: f"{o['offer_no']} — {format_currency(o['grand_total'], o['currency'])}" for o in offers}

    with st.form("cari_txn_form"):
        st.subheader("Yeni Cari Hareketi")

        col1, col2 = st.columns(2)
        selected_cust = col1.selectbox(
            "Müşteri", cust_ids, index=default_idx,
            format_func=lambda x: cust_map[x],
        )
        txn_type = col2.radio(
            "Hareket Türü",
            ["debit", "credit"],
            format_func=lambda x: "🔴 Borç (Fatura/Satış)" if x == "debit" else "🟢 Ödeme (Tahsilat)",
            horizontal=True,
        )

        col1, col2, col3 = st.columns(3)
        amount = col1.number_input("Tutar", min_value=0.01, step=100.0)
        currency = col2.selectbox("Para Birimi", CURRENCIES)
        txn_date = col3.date_input("Tarih", value=datetime.date.today())

        col1, col2 = st.columns(2)
        payment_method = col1.selectbox("Ödeme Yöntemi", [""] + PAYMENT_METHODS)
        reference_no = col2.text_input("Referans / Fiş No")

        col1, col2 = st.columns(2)
        due_date = col1.date_input("Vade Tarihi", value=None)
        linked_offer = col2.selectbox(
            "Bağlı Teklif (isteğe bağlı)",
            [0] + list(offer_map.keys()),
            format_func=lambda x: "—" if x == 0 else offer_map.get(x, str(x)),
        )

        description = st.text_input("Açıklama")
        notes = st.text_area("Notlar", height=60)

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("💾 Kaydet", type="primary")
        cancelled = col2.form_submit_button("İptal")

    if submitted:
        if amount <= 0:
            st.error("Tutar 0'dan büyük olmalıdır.")
            return
        fdb.add_customer_transaction(
            customer_id=selected_cust,
            txn_type=txn_type,
            amount=amount,
            currency=currency,
            description=description.strip(),
            offer_id=linked_offer or 0,
            payment_method=payment_method,
            reference_no=reference_no.strip(),
            due_date=str(due_date) if due_date else "",
            txn_date=str(txn_date),
            user_id=user["id"],
            notes=notes.strip(),
        )
        st.session_state.pop("cari_form", None)
        st.session_state.pop("cari_default_cust", None)
        st.success("✅ Hareket kaydedildi.")
        st.rerun()

    if cancelled:
        st.session_state.pop("cari_form", None)
        st.session_state.pop("cari_default_cust", None)
        st.rerun()
