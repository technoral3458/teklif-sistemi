import streamlit as st
from i18n import _
import db.factory as fdb
from utils.costs import calculate_import_cost, calculate_profit, format_currency


def show(user: dict):
    st.title(_("costs_title"))

    tab1, tab2 = st.tabs(["🏭 Modeller", "⚙️ Opsiyonlar"])

    with tab1:
        _cost_table_models(user)

    with tab2:
        _cost_table_options(user)


def _cost_table_models(user: dict):
    models = fdb.get_models()
    if not models:
        st.info(_("no_records"))
        return

    for model in models:
        cost = calculate_import_cost(
            purchase_price=model["purchase_price"],
            shipping_cost=model["shipping_cost"],
            customs_tax_rate=model["customs_tax_rate"],
            extra_tax_rate=model["extra_tax_rate"],
            port_cost=model["port_cost"],
            document_cost=model["document_cost"],
            installation_cost=model["installation_cost"],
            other_cost=model["other_cost"],
        )
        profit = calculate_profit(
            sale_price=model["sale_price"] or model["base_price"],
            total_cost=cost["total_cost"],
        )

        with st.expander(f"🏭 {model['name']} — {model.get('model_code', '')}"):
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(_("cost_breakdown"))
                st.write(f"Alış Fiyatı: {format_currency(cost['purchase_price'], model['currency'])}")
                st.write(f"Nakliye: {format_currency(cost['shipping_cost'], model['currency'])}")
                st.write(f"Ara Toplam 1: {format_currency(cost['sub1'], model['currency'])}")
                st.write(f"Gümrük (%{model['customs_tax_rate']}): {format_currency(cost['customs_tax'], model['currency'])}")
                st.write(f"Ara Toplam 2: {format_currency(cost['sub2'], model['currency'])}")
                st.write(f"Ek Vergi (%{model['extra_tax_rate']}): {format_currency(cost['extra_tax'], model['currency'])}")
                st.write(f"Liman: {format_currency(cost['port_cost'], model['currency'])}")
                st.write(f"Evrak: {format_currency(cost['document_cost'], model['currency'])}")
                st.write(f"Kurulum: {format_currency(cost['installation_cost'], model['currency'])}")
                st.write(f"Diğer: {format_currency(cost['other_cost'], model['currency'])}")
                st.markdown(f"**{_('total_cost')}: {format_currency(cost['total_cost'], model['currency'])}**")
            with c2:
                st.subheader("Kârlılık")
                st.write(f"Satış Fiyatı: {format_currency(profit['sale_price'], model['currency'])}")
                st.write(f"Toplam Maliyet: {format_currency(profit['total_cost'], model['currency'])}")
                net = profit["net_profit"]
                color = "green" if net >= 0 else "red"
                st.markdown(f"**Net Kâr:** :{color}[{format_currency(net, model['currency'])}]")
                st.write(f"Kâr Oranı: %{profit['profit_rate']:.2f}")
                st.write(f"Kâr Marjı: %{profit['margin']:.2f}")
                if model.get("cost_note"):
                    st.info(f"Not: {model['cost_note']}")


def _cost_table_options(user: dict):
    options = fdb.get_options()
    if not options:
        st.info(_("no_records"))
        return

    for opt in options:
        cost = calculate_import_cost(
            purchase_price=opt["purchase_price"],
            shipping_cost=opt["shipping_cost"],
            customs_tax_rate=opt["customs_tax_rate"],
            extra_tax_rate=opt["extra_tax_rate"],
            port_cost=opt["port_cost"],
            document_cost=opt["document_cost"],
            installation_cost=opt["installation_cost"],
            other_cost=opt["other_cost"],
        )
        profit = calculate_profit(
            sale_price=opt["sale_price"] or opt["list_price"],
            total_cost=cost["total_cost"],
        )

        with st.expander(f"⚙️ {opt['name']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"Toplam Maliyet: {format_currency(cost['total_cost'], opt['currency'])}")
            with c2:
                net = profit["net_profit"]
                color = "green" if net >= 0 else "red"
                st.markdown(f"Net Kâr: :{color}[{format_currency(net, opt['currency'])}]")
                st.write(f"Kâr Oranı: %{profit['profit_rate']:.2f}")
