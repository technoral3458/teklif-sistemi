import streamlit as st
from i18n import _
import db.factory as fdb
from utils.images import save_uploaded_image, image_tag
from utils.costs import format_currency
from config import CURRENCIES, QTY_TYPES, OPTION_SCOPES


QTY_LABELS = {"MANUAL": "Manuel", "FIXED_1": "Sabit 1", "PER_MACHINE": "Makine Adedi Kadar"}
SCOPE_LABELS = {"GLOBAL": "Tüm Makineler", "MODEL_SPECIFIC": "Model Bazlı"}


def show(user: dict):
    st.title(_("options_title"))

    can_edit = user["role"] in ("admin", "manufacturer")
    manufacturer_id = user["id"] if user["role"] == "manufacturer" else None

    if can_edit and st.button(f"➕ {_('add_option')}", type="primary"):
        st.session_state["opt_form"] = "new"

    if st.session_state.get("opt_form") == "new":
        _option_form(user)

    options = fdb.get_options(manufacturer_id=manufacturer_id)

    if not options:
        st.info(_("no_records"))
        return

    search = st.text_input(_("search"), key="opt_search")
    if search:
        q = search.lower()
        options = [o for o in options if q in o["name"].lower()]

    for opt in options:
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 5, 2])
            with col1:
                html = image_tag(opt["image_path"], width=70)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.write("⚙️")
            with col2:
                st.write(f"**{opt['name']}**")
                info_parts = [
                    QTY_LABELS.get(opt["qty_type"], opt["qty_type"]),
                    SCOPE_LABELS.get(opt["scope"], opt["scope"]),
                ]
                if opt.get("category"):
                    info_parts.append(opt["category"])
                st.caption(" | ".join(info_parts))
                price_str = format_currency(opt["sale_price"] or opt["list_price"], opt["currency"])
                st.write(price_str)
            with col3:
                if can_edit:
                    b1, b2 = st.columns(2)
                    if b1.button(_("edit"), key=f"edit_o{opt['id']}"):
                        st.session_state["opt_form"] = f"edit_{opt['id']}"
                        st.rerun()
                    if b2.button(_("delete"), key=f"del_o{opt['id']}"):
                        st.session_state[f"confirm_del_o{opt['id']}"] = True

            if st.session_state.get(f"confirm_del_o{opt['id']}"):
                st.warning(_("confirm_delete"))
                cc1, cc2 = st.columns(2)
                if cc1.button(_("yes"), key=f"yes_del_o{opt['id']}"):
                    fdb.delete_option(opt["id"])
                    del st.session_state[f"confirm_del_o{opt['id']}"]
                    st.rerun()
                if cc2.button(_("no"), key=f"no_del_o{opt['id']}"):
                    del st.session_state[f"confirm_del_o{opt['id']}"]
                    st.rerun()

            if st.session_state.get("opt_form") == f"edit_{opt['id']}":
                _option_form(user, opt)


def _option_form(user: dict, opt: dict = None):
    is_new = opt is None
    key_suffix = "new" if is_new else str(opt["id"])
    can_view_costs = user.get("can_view_costs") or user["role"] == "admin"
    all_models = fdb.get_models()
    all_options = fdb.get_options()

    with st.expander("Yeni Opsiyon" if is_new else "Opsiyonu Düzenle", expanded=True):
        with st.form(f"opt_form_{key_suffix}"):
            tab1, tab2 = st.tabs(["Genel Bilgiler", _("cost_breakdown") if can_view_costs else "🔒 Maliyet"])

            with tab1:
                c1, c2 = st.columns(2)
                name = c1.text_input(_("option_name"), value="" if is_new else opt["name"])
                category = c2.text_input(_("category"), value="" if is_new else opt.get("category", ""))
                description = st.text_area(_("description"), value="" if is_new else opt.get("description", ""), height=60)

                c1, c2, c3 = st.columns(3)
                currency = c1.selectbox(_("currency"), CURRENCIES,
                                         index=CURRENCIES.index(opt.get("currency", "USD") or "USD") if not is_new else 0)
                list_price = c2.number_input(_("list_price"), value=0.0 if is_new else float(opt.get("list_price") or 0), min_value=0.0, step=10.0)
                sale_price = c3.number_input(_("sale_price"), value=0.0 if is_new else float(opt.get("sale_price") or 0), min_value=0.0, step=10.0)

                c1, c2, c3 = st.columns(3)
                qty_type = c1.selectbox(_("qty_type"), QTY_TYPES,
                                         index=QTY_TYPES.index(opt.get("qty_type", "MANUAL")) if not is_new else 0,
                                         format_func=lambda x: QTY_LABELS.get(x, x))
                scope = c2.selectbox(_("scope"), OPTION_SCOPES,
                                      index=OPTION_SCOPES.index(opt.get("scope", "GLOBAL")) if not is_new else 0,
                                      format_func=lambda x: SCOPE_LABELS.get(x, x))
                sort_order = c3.number_input(_("sort_order"), value=0 if is_new else opt.get("sort_order", 0), min_value=0)

                model_ids = [m["id"] for m in all_models]
                model_names = {m["id"]: m["name"] for m in all_models}
                current_models = opt.get("compatible_models", []) if not is_new else []
                compatible_models = st.multiselect(
                    "Uyumlu Modeller (scope=MODEL_SPECIFIC ise)",
                    options=model_ids,
                    default=[x for x in current_models if x in model_ids],
                    format_func=lambda x: model_names.get(x, str(x)),
                    key=f"omodels_{key_suffix}",
                )

                opt_ids = [o["id"] for o in all_options if o["id"] != (opt["id"] if not is_new else -1)]
                opt_names = {o["id"]: o["name"] for o in all_options}
                current_conflicts = opt.get("conflicts_with", []) if not is_new else []
                conflicts_with = st.multiselect(
                    _("conflicts_with"),
                    options=opt_ids,
                    default=[x for x in current_conflicts if x in opt_ids],
                    format_func=lambda x: opt_names.get(x, str(x)),
                    key=f"oconflict_{key_suffix}",
                )

                img_file = st.file_uploader(_("upload_image"), type=["png", "jpg", "jpeg", "webp"], key=f"oimg_{key_suffix}")

            with tab2:
                if can_view_costs:
                    c1, c2 = st.columns(2)
                    purchase_price = c1.number_input(_("purchase_price"), value=0.0 if is_new else float(opt.get("purchase_price") or 0), min_value=0.0, step=10.0)
                    shipping_cost = c2.number_input(_("shipping"), value=0.0 if is_new else float(opt.get("shipping_cost") or 0), min_value=0.0, step=10.0)
                    c1, c2 = st.columns(2)
                    customs_tax_rate = c1.number_input(_("customs_rate"), value=3.0 if is_new else float(opt.get("customs_tax_rate") or 3), min_value=0.0, max_value=100.0, step=0.5)
                    extra_tax_rate = c2.number_input(_("extra_tax_rate"), value=10.0 if is_new else float(opt.get("extra_tax_rate") or 10), min_value=0.0, max_value=100.0, step=0.5)
                    c1, c2, c3, c4 = st.columns(4)
                    port_cost = c1.number_input(_("port_cost"), value=0.0 if is_new else float(opt.get("port_cost") or 0), min_value=0.0, step=10.0)
                    document_cost = c2.number_input(_("document_cost"), value=0.0 if is_new else float(opt.get("document_cost") or 0), min_value=0.0, step=10.0)
                    installation_cost = c3.number_input(_("installation_cost"), value=0.0 if is_new else float(opt.get("installation_cost") or 0), min_value=0.0, step=10.0)
                    other_cost = c4.number_input(_("other_cost"), value=0.0 if is_new else float(opt.get("other_cost") or 0), min_value=0.0, step=10.0)
                    cost_note = st.text_input(_("cost_note"), value="" if is_new else opt.get("cost_note", ""))
                else:
                    st.warning("Maliyet bilgilerini görüntüleme yetkiniz yok.")
                    purchase_price = shipping_cost = port_cost = document_cost = installation_cost = other_cost = 0.0
                    customs_tax_rate = 3.0; extra_tax_rate = 10.0; cost_note = ""

            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button(_("save"), type="primary")
            cancelled = col2.form_submit_button(_("cancel"))

        if submitted:
            if not name.strip():
                st.error(f"{_('option_name')} zorunludur.")
                return
            img_path = opt.get("image_path", "") if not is_new else ""
            if img_file:
                saved = save_uploaded_image(img_file, prefix="opt")
                if saved:
                    img_path = saved
            data = dict(
                name=name.strip(), description=description, category=category,
                currency=currency, list_price=list_price, sale_price=sale_price,
                image_path=img_path, qty_type=qty_type, scope=scope,
                compatible_models=compatible_models, conflicts_with=conflicts_with,
                manufacturer_id=user["id"] if user["role"] == "manufacturer" else 0,
                sort_order=int(sort_order),
                purchase_price=purchase_price, shipping_cost=shipping_cost,
                customs_tax_rate=customs_tax_rate, extra_tax_rate=extra_tax_rate,
                port_cost=port_cost, document_cost=document_cost,
                installation_cost=installation_cost, other_cost=other_cost,
                cost_note=cost_note,
            )
            if is_new:
                fdb.add_option(**data)
            else:
                fdb.update_option(opt["id"], **data)
            st.session_state.pop("opt_form", None)
            st.success(_("success"))
            st.rerun()

        if cancelled:
            st.session_state.pop("opt_form", None)
            st.rerun()
