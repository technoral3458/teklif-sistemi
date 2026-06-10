import streamlit as st
import datetime
from i18n import _
import db.factory as fdb
from utils.costs import format_currency
from utils.images import image_tag, get_image_base64
from config import OFFER_STATUSES


STATUS_COLORS = {
    "Beklemede": "🟡", "Onaylandı": "🟢", "Reddedildi": "🔴",
    "Sipariş Verildi": "🔵", "İptal": "⚫",
}


def show(user: dict):
    st.title(_("offers_title"))

    status_filter = st.selectbox(_("filter"), ["Tümü"] + OFFER_STATUSES, key="offers_filter")
    offers = fdb.get_offers(
        user_id=user["id"], role=user["role"],
        status=status_filter if status_filter != "Tümü" else None
    )

    customers = {c["id"]: c for c in fdb.get_customers(user_id=user["id"], role=user["role"])}
    models_map = {m["id"]: m for m in fdb.get_models()}

    if not offers:
        st.info(_("no_records"))
        return

    for offer in offers:
        cust = customers.get(offer["customer_id"])
        model = models_map.get(offer["model_id"])
        cust_name = cust["company_name"] if cust else "?"
        model_name = model["name"] if model else "?"

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
            with col1:
                st.write(f"**{offer['offer_no']}**")
                st.caption(f"📅 {offer['offer_date']}")
            with col2:
                st.write(f"👤 {cust_name}")
                st.caption(f"🏭 {model_name} ×{offer['machine_qty']}")
            with col3:
                st.write(f"**{format_currency(offer['grand_total'], offer['currency'])}**")
                color = STATUS_COLORS.get(offer["status"], "⚪")
                st.write(f"{color} {offer['status']}")
            with col4:
                b1, b2 = st.columns(2)
                if b1.button("👁️", key=f"view_o{offer['id']}", help=_("view_offer")):
                    st.session_state["offer_detail"] = offer["id"]
                    st.rerun()
                if b2.button("🗑️", key=f"del_o{offer['id']}", help=_("delete")):
                    st.session_state[f"confirm_del_offer{offer['id']}"] = True

            if st.session_state.get(f"confirm_del_offer{offer['id']}"):
                st.warning(_("confirm_delete"))
                cc1, cc2 = st.columns(2)
                if cc1.button(_("yes"), key=f"yes_dof{offer['id']}"):
                    fdb.delete_offer(offer["id"])
                    del st.session_state[f"confirm_del_offer{offer['id']}"]
                    st.rerun()
                if cc2.button(_("no"), key=f"no_dof{offer['id']}"):
                    del st.session_state[f"confirm_del_offer{offer['id']}"]
                    st.rerun()

            if st.session_state.get("offer_detail") == offer["id"]:
                _offer_detail(offer, cust, model, user)


def _offer_detail(offer: dict, cust: dict, model: dict, user: dict):
    with st.expander(f"Teklif Detayı — {offer['offer_no']}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Teklif No:** {offer['offer_no']}")
            st.write(f"**Tarih:** {offer['offer_date']}")
            st.write(f"**Müşteri:** {cust['company_name'] if cust else '?'}")
        with col2:
            st.write(f"**Model:** {model['name'] if model else '?'}")
            st.write(f"**Adet:** {offer['machine_qty']}")
            st.write(f"**Para Birimi:** {offer['currency']}")

        st.divider()
        items = fdb.get_offer_items(offer["id"])

        st.write(f"Makine Birim: {format_currency(offer['machine_unit_price'], offer['currency'])} × {offer['machine_qty']} = {format_currency(offer['machine_total'], offer['currency'])}")

        if items:
            st.subheader("Opsiyonlar")
            for item in items:
                st.write(f"• {item['option_name']} × {item['quantity']} = {format_currency(item['total_price'], offer['currency'])}")

        st.divider()
        st.write(f"Ara Toplam: {format_currency(offer['subtotal'], offer['currency'])}")
        if offer["discount_pct"]:
            disc = offer["subtotal"] * offer["discount_pct"] / 100
            st.write(f"İndirim ({offer['discount_pct']}%): -{format_currency(disc, offer['currency'])}")
        st.markdown(f"### 💰 Genel Toplam: {format_currency(offer['grand_total'], offer['currency'])}")

        if offer.get("conditions"):
            st.info(f"Koşullar: {offer['conditions']}")

        if user.get("can_view_costs") or user["role"] == "admin":
            if offer.get("total_cost"):
                st.divider()
                st.write(f"Toplam Maliyet: {format_currency(offer['total_cost'], offer['currency'])}")
                st.write(f"Net Kâr: {format_currency(offer['total_profit'], offer['currency'])}")
                st.write(f"Kâr Oranı: %{offer['profit_rate']:.1f}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        new_status = c1.selectbox("Durum Değiştir", OFFER_STATUSES,
                                   index=OFFER_STATUSES.index(offer["status"]) if offer["status"] in OFFER_STATUSES else 0,
                                   key=f"status_sel_{offer['id']}")
        if c2.button("💾 Kaydet", key=f"save_status_{offer['id']}"):
            order_date = str(datetime.date.today()) if new_status == "Sipariş Verildi" else offer.get("order_date", "")
            fdb.update_offer_status(offer["id"], new_status, order_date)
            st.success("Durum güncellendi.")
            st.rerun()
        if c3.button(_("close"), key=f"close_det_{offer['id']}"):
            st.session_state.pop("offer_detail", None)
            st.rerun()
