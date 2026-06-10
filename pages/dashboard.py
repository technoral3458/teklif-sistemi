import streamlit as st
from i18n import _
import db.factory as fdb


def show(user: dict):
    st.title(_("dashboard_title"))
    stats = fdb.get_stats(user_id=user["id"], role=user["role"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(_("total_customers"), stats["customers"])
    col2.metric(_("total_offers"), stats["offers"])
    col3.metric(_("total_models"), stats["models"])
    col4.metric(_("total_orders"), stats["orders"])

    st.divider()
    st.subheader(_("recent_offers"))

    offers = fdb.get_offers(user_id=user["id"], role=user["role"])[:10]
    if not offers:
        st.info(_("no_records"))
        return

    customers = {c["id"]: c["company_name"] for c in fdb.get_customers(user_id=user["id"], role=user["role"])}
    models = {m["id"]: m["name"] for m in fdb.get_models()}

    for o in offers:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.write(f"**{o['offer_no']}** — {customers.get(o['customer_id'], '?')}")
            c2.write(models.get(o["model_id"], "?"))
            c3.write(f"{o['grand_total']:,.2f} {o['currency']}")
            status_color = {
                "Beklemede": "🟡", "Onaylandı": "🟢",
                "Reddedildi": "🔴", "Sipariş Verildi": "🔵", "İptal": "⚫"
            }.get(o["status"], "⚪")
            c4.write(f"{status_color} {o['status']}")
