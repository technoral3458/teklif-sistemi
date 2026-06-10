import streamlit as st
import datetime
from i18n import _
import db.factory as fdb
import db.users as udb
from utils.costs import format_currency
from config import CURRENCIES

PAYMENT_METHODS = ["Nakit", "Banka Havalesi / EFT", "Çek", "Senet", "Kredi Kartı", "Diğer"]


def show(user: dict):
    st.title("🏭 Üretici Hesap Takibi")

    # Get all manufacturers
    all_users = udb.get_all_users()
    manufacturers = [u for u in all_users if u["role"] == "manufacturer" and u["is_active"]]

    if not manufacturers:
        st.info("Henüz üretici kaydı bulunmuyor.")
        return

    tab1, tab2 = st.tabs(["📊 Özet", "📋 Hareketler"])

    with tab1:
        _overview(manufacturers)

    with tab2:
        _transactions(manufacturers)


def _overview(manufacturers: list):
    """Tüm üreticilerin bakiye özeti."""
    total_owed = 0.0

    for mfr in manufacturers:
        bal = fdb.get_manufacturer_balance(mfr["id"])
        owed = bal["balance_owed"]
        total_owed += owed

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
            col1.write(f"**{mfr['company_name']}**")
            col1.caption(mfr["email"])
            col2.metric("Toplam Alım", format_currency(bal["total_purchase"], ""))
            col3.metric("Yapılan Ödeme", format_currency(bal["total_payment"], ""))
            color = "🔴" if owed > 0 else ("🟢" if owed < 0 else "⚪")
            label = "Ödenecek Tutar" if owed > 0 else ("Fazla Ödeme" if owed < 0 else "Sıfır")
            col4.metric(label, f"{color} {format_currency(abs(owed), '')}")

    st.divider()
    st.info(f"Toplam ödenecek tutar: **{format_currency(total_owed, '')}**")


def _transactions(manufacturers: list):
    mfr_map = {m["id"]: m["company_name"] for m in manufacturers}
    mfr_ids = list(mfr_map.keys())

    col1, col2 = st.columns([3, 2])
    selected_mfr_id = col1.selectbox(
        "Üretici Seçin",
        mfr_ids,
        format_func=lambda x: mfr_map[x],
        key="mfr_sel",
    )
    cur_filter = col2.selectbox("Para Birimi", ["Tümü"] + CURRENCIES, key="mfr_cur_filter")

    if st.button("➕ Yeni Hareket", type="primary", key="new_mfr_txn"):
        st.session_state["mfr_form"] = "new"
        st.session_state["mfr_default"] = selected_mfr_id

    if st.session_state.get("mfr_form") == "new":
        _transaction_form(manufacturers, default_mfr_id=st.session_state.get("mfr_default"))

    if selected_mfr_id:
        currency_for_bal = cur_filter if cur_filter != "Tümü" else None
        bal = fdb.get_manufacturer_balance(selected_mfr_id, currency=currency_for_bal)
        mfr_name = mfr_map[selected_mfr_id]

        with st.container(border=True):
            st.subheader(f"📊 {mfr_name} — Hesap Özeti")
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Alım (Borç)", format_currency(bal["total_purchase"], ""))
            col2.metric("Yapılan Ödeme", format_currency(bal["total_payment"], ""))
            owed = bal["balance_owed"]
            col3.metric(
                "Ödenecek Bakiye" if owed >= 0 else "Fazla Ödeme",
                format_currency(abs(owed), ""),
                delta="🔴 Ödeme Bekliyor" if owed > 0 else ("🟢 Fazla Ödeme" if owed < 0 else "✅"),
                delta_color="off",
            )

        st.divider()
        st.subheader("📋 Hareket Geçmişi")

        txns = fdb.get_manufacturer_transactions(manufacturer_id=selected_mfr_id)
        if cur_filter != "Tümü":
            txns = [t for t in txns if t["currency"] == cur_filter]

        # Get models for display
        models_map = {m["id"]: m["name"] for m in fdb.get_models()}

        if not txns:
            st.info(_("no_records"))
        else:
            running = 0.0
            for t in reversed(txns):
                if t["txn_type"] == "purchase":
                    running += t["amount"]
                    type_label = "🔴 Alım (Borç)"
                else:
                    running -= t["amount"]
                    type_label = "🟢 Ödeme"

            for t in txns:
                model_name = models_map.get(t.get("model_id", 0), "")
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                    type_label = "🔴 Alım" if t["txn_type"] == "purchase" else "🟢 Ödeme"
                    col1.write(t["txn_date"])
                    col1.caption(type_label)
                    desc = t.get("description") or ""
                    if model_name:
                        desc = f"{desc} ({model_name})" if desc else model_name
                    col2.write(desc or "—")
                    col2.caption(t.get("payment_method") or "")
                    col3.write(f"**{format_currency(t['amount'], t['currency'])}**")
                    ref = t.get("reference_no") or ""
                    if t.get("due_date"):
                        col4.caption(f"Vade: {t['due_date']}")
                    if ref:
                        col4.caption(f"Ref: {ref}")
                    if col5.button("🗑️", key=f"del_mtxn_{t['id']}"):
                        st.session_state[f"confirm_del_mtxn_{t['id']}"] = True

                    if st.session_state.get(f"confirm_del_mtxn_{t['id']}"):
                        st.warning("Bu hareketi silmek istiyor musunuz?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("Evet", key=f"yes_mtxn_{t['id']}"):
                            fdb.delete_manufacturer_transaction(t["id"])
                            del st.session_state[f"confirm_del_mtxn_{t['id']}"]
                            st.rerun()
                        if cc2.button("Hayır", key=f"no_mtxn_{t['id']}"):
                            del st.session_state[f"confirm_del_mtxn_{t['id']}"]
                            st.rerun()


def _transaction_form(manufacturers: list, default_mfr_id: int = None):
    mfr_map = {m["id"]: m["company_name"] for m in manufacturers}
    mfr_ids = list(mfr_map.keys())
    default_idx = mfr_ids.index(default_mfr_id) if default_mfr_id in mfr_ids else 0

    all_models = fdb.get_models()
    model_map = {m["id"]: m["name"] for m in all_models}

    with st.form("mfr_txn_form"):
        st.subheader("Yeni Üretici Hareketi")

        col1, col2 = st.columns(2)
        selected_mfr = col1.selectbox(
            "Üretici", mfr_ids, index=default_idx,
            format_func=lambda x: mfr_map[x],
        )
        txn_type = col2.radio(
            "Hareket Türü",
            ["purchase", "payment"],
            format_func=lambda x: "🔴 Alım / Fatura (Borçlandık)" if x == "purchase" else "🟢 Ödeme Yaptık",
            horizontal=True,
        )

        col1, col2, col3 = st.columns(3)
        amount = col1.number_input("Tutar", min_value=0.01, step=100.0)
        currency = col2.selectbox("Para Birimi", CURRENCIES)
        txn_date = col3.date_input("Tarih", value=datetime.date.today())

        col1, col2 = st.columns(2)
        payment_method = col1.selectbox("Ödeme Yöntemi", [""] + PAYMENT_METHODS)
        reference_no = col2.text_input("Referans / Fatura No")

        col1, col2 = st.columns(2)
        due_date = col1.date_input("Vade Tarihi", value=None)
        linked_model = col2.selectbox(
            "Bağlı Model (isteğe bağlı)",
            [0] + list(model_map.keys()),
            format_func=lambda x: "—" if x == 0 else model_map.get(x, str(x)),
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
        fdb.add_manufacturer_transaction(
            manufacturer_id=selected_mfr,
            txn_type=txn_type,
            amount=amount,
            currency=currency,
            description=description.strip(),
            model_id=linked_model or 0,
            payment_method=payment_method,
            reference_no=reference_no.strip(),
            due_date=str(due_date) if due_date else "",
            txn_date=str(txn_date),
            notes=notes.strip(),
        )
        st.session_state.pop("mfr_form", None)
        st.session_state.pop("mfr_default", None)
        st.success("✅ Hareket kaydedildi.")
        st.rerun()

    if cancelled:
        st.session_state.pop("mfr_form", None)
        st.session_state.pop("mfr_default", None)
        st.rerun()
