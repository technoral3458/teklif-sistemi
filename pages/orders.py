import streamlit as st
from i18n import _
import db.factory as fdb
from utils.costs import format_currency


def show(user: dict):
    st.title(_("orders_title"))

    offers = fdb.get_offers(user_id=user["id"], role=user["role"], status="Sipariş Verildi")
    customers = {c["id"]: c for c in fdb.get_customers(user_id=user["id"], role=user["role"])}
    models_map = {m["id"]: m for m in fdb.get_models()}

    if not offers:
        st.info(_("no_records"))
        return

    for offer in offers:
        cust = customers.get(offer["customer_id"])
        model = models_map.get(offer["model_id"])
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 3, 3])
            col1.write(f"**{offer['offer_no']}**")
            col1.caption(f"📅 Sipariş: {offer.get('order_date', offer['offer_date'])}")
            col2.write(cust["company_name"] if cust else "?")
            col2.caption(f"{model['name'] if model else '?'} ×{offer['machine_qty']}")
            col3.write(f"**{format_currency(offer['grand_total'], offer['currency'])}**")
            col3.write("🔵 Sipariş Verildi")
