import streamlit as st
from i18n import _
import db.factory as fdb

COUNTRIES = [
    "", "Türkiye", "Almanya", "Amerika Birleşik Devletleri", "Azerbaycan",
    "Birleşik Arap Emirlikleri", "Birleşik Krallık", "Çin", "Fransa",
    "Gürcistan", "Irak", "İran", "İspanya", "İtalya", "Japonya", "Katar",
    "Kosova", "Mısır", "Özbekistan", "Romanya", "Rusya", "Sırbistan",
    "Suudi Arabistan", "Yunanistan", "Diğer",
]


def show(user: dict):
    st.title(_("customers_title"))

    if st.button(f"➕ {_('add_customer')}", type="primary"):
        st.session_state["cust_form"] = "new"

    if st.session_state.get("cust_form") == "new":
        _customer_form(user)

    customers = fdb.get_customers(user_id=user["id"], role=user["role"])
    if not customers:
        st.info(_("no_records"))
        return

    search = st.text_input(_("search"), key="cust_search")
    if search:
        q = search.lower()
        customers = [c for c in customers if q in c["company_name"].lower()
                     or q in (c["contact_person"] or "").lower()]

    for cust in customers:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 3, 2])
            with col1:
                st.write(f"**{cust['company_name']}**")
                if cust["contact_person"]:
                    st.caption(cust["contact_person"])
            with col2:
                if cust["phone"]:
                    st.write(f"📞 {cust['phone']}")
                if cust["email"]:
                    st.write(f"📧 {cust['email']}")
            with col3:
                c1, c2 = st.columns(2)
                if c1.button(_("edit"), key=f"edit_c{cust['id']}"):
                    st.session_state["cust_form"] = f"edit_{cust['id']}"
                    st.rerun()
                if c2.button(_("delete"), key=f"del_c{cust['id']}"):
                    st.session_state[f"confirm_del_c{cust['id']}"] = True

            if st.session_state.get(f"confirm_del_c{cust['id']}"):
                st.warning(_("confirm_delete"))
                cc1, cc2 = st.columns(2)
                if cc1.button(_("yes"), key=f"yes_del_c{cust['id']}"):
                    fdb.delete_customer(cust["id"])
                    del st.session_state[f"confirm_del_c{cust['id']}"]
                    st.rerun()
                if cc2.button(_("no"), key=f"no_del_c{cust['id']}"):
                    del st.session_state[f"confirm_del_c{cust['id']}"]
                    st.rerun()

            if st.session_state.get("cust_form") == f"edit_{cust['id']}":
                _customer_form(user, cust)


def _customer_form(user: dict, cust: dict = None):
    is_new = cust is None
    key_suffix = "new" if is_new else str(cust["id"])

    with st.form(f"cust_form_{key_suffix}"):
        st.subheader(_("add_customer") if is_new else _("edit_customer"))
        company = st.text_input(_("company_name_field"), value="" if is_new else cust["company_name"])
        tax_office = st.text_input(_("tax_office"), value="" if is_new else cust.get("tax_office", ""))
        tax_no = st.text_input(_("tax_no"), value="" if is_new else cust.get("tax_no", ""))
        contact = st.text_input(_("contact_person"), value="" if is_new else cust.get("contact_person", ""))
        phone = st.text_input(_("phone_field"), value="" if is_new else cust.get("phone", ""))
        email = st.text_input(_("email_field"), value="" if is_new else cust.get("email", ""))

        countries = COUNTRIES
        country_idx = countries.index(cust["country"]) if not is_new and cust.get("country") in countries else 0
        country = st.selectbox(_("country"), countries, index=country_idx)
        city = st.text_input(_("city"), value="" if is_new else cust.get("city", ""))
        address = st.text_area(_("address"), value="" if is_new else cust.get("address", ""), height=80)

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button(_("save"), type="primary")
        cancelled = col2.form_submit_button(_("cancel"))

    if submitted:
        if not company.strip():
            st.error(f"{_('company_name_field')} zorunludur.")
            return
        data = dict(company_name=company.strip(), tax_office=tax_office, tax_no=tax_no,
                    contact_person=contact, phone=phone, email=email,
                    country=country, city=city, address=address)
        if is_new:
            fdb.add_customer(user["id"], **data)
        else:
            fdb.update_customer(cust["id"], **data)
        st.session_state.pop("cust_form", None)
        st.success(_("success"))
        st.rerun()

    if cancelled:
        st.session_state.pop("cust_form", None)
        st.rerun()
