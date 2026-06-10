import streamlit as st
import json
from i18n import _
import db.factory as fdb
from utils.images import save_uploaded_image, image_tag
from utils.costs import calculate_import_cost, calculate_profit, format_currency
from config import CURRENCIES


def show(user: dict):
    st.title(_("models_title"))

    can_edit = user["role"] in ("admin", "manufacturer")
    manufacturer_id = user["id"] if user["role"] == "manufacturer" else None

    if can_edit and st.button(f"➕ {_('add_model')}", type="primary"):
        st.session_state["model_form"] = "new"
        st.session_state.pop("model_detail", None)

    if st.session_state.get("model_form") == "new":
        _model_form(user)

    cats = [""] + [c["name"] for c in fdb.get_categories()]
    selected_cat = st.selectbox(_("category"), cats, key="model_cat_filter")

    models = fdb.get_models(
        category=selected_cat or None,
        manufacturer_id=manufacturer_id
    )

    if not models:
        st.info(_("no_records"))
        return

    search = st.text_input(_("search"), key="model_search")
    if search:
        q = search.lower()
        models = [m for m in models if q in m["name"].lower() or q in m.get("model_code", "").lower()]

    for model in models:
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 5, 2])
            with col1:
                html = image_tag(model["image_path"], width=80)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.write("🏭")
            with col2:
                st.write(f"**{model['name']}**")
                parts = []
                if model.get("model_code"):
                    parts.append(model["model_code"])
                if model.get("category"):
                    parts.append(model["category"])
                if parts:
                    st.caption(" | ".join(parts))
                price_str = format_currency(model["sale_price"] or model["base_price"], model["currency"])
                st.write(price_str)
            with col3:
                if can_edit:
                    b1, b2, b3 = st.columns(3)
                    if b1.button(_("edit"), key=f"edit_m{model['id']}"):
                        st.session_state["model_form"] = f"edit_{model['id']}"
                        st.session_state.pop("model_detail", None)
                        st.rerun()
                    if b2.button(_("copy"), key=f"copy_m{model['id']}"):
                        _copy_model(model)
                    if b3.button(_("delete"), key=f"del_m{model['id']}"):
                        st.session_state[f"confirm_del_m{model['id']}"] = True
                else:
                    if st.button(_("model_detail"), key=f"det_m{model['id']}"):
                        st.session_state["model_detail"] = model["id"]

            if st.session_state.get(f"confirm_del_m{model['id']}"):
                st.warning(_("confirm_delete"))
                cc1, cc2 = st.columns(2)
                if cc1.button(_("yes"), key=f"yes_del_m{model['id']}"):
                    fdb.delete_model(model["id"])
                    del st.session_state[f"confirm_del_m{model['id']}"]
                    st.rerun()
                if cc2.button(_("no"), key=f"no_del_m{model['id']}"):
                    del st.session_state[f"confirm_del_m{model['id']}"]
                    st.rerun()

            if st.session_state.get("model_form") == f"edit_{model['id']}":
                _model_form(user, model)

            if st.session_state.get("model_detail") == model["id"]:
                _model_detail(model)


def _model_detail(model: dict):
    with st.expander(f"📋 {model['name']} — Detay", expanded=True):
        if model.get("description"):
            st.write(model["description"])
        specs = model.get("specs") or []
        if specs:
            st.subheader(_("tech_specs"))
            for spec in specs:
                st.write(f"**{spec.get('title', '')}**: {spec.get('value', '')}")
        if st.button(_("close"), key=f"close_det_{model['id']}"):
            st.session_state.pop("model_detail", None)
            st.rerun()


def _copy_model(model: dict):
    data = {k: v for k, v in model.items() if k not in ("id", "created_at")}
    data["name"] = f"{model['name']} (Kopya)"
    fdb.add_model(**data)
    st.success(f"'{model['name']}' kopyalandı.")
    st.rerun()


def _model_form(user: dict, model: dict = None):
    is_new = model is None
    key_suffix = "new" if is_new else str(model["id"])
    can_view_costs = user.get("can_view_costs") or user["role"] in ("admin",)

    cats = [c["name"] for c in fdb.get_categories()]
    all_options = fdb.get_options()

    with st.expander(f"{'Yeni Model Ekle' if is_new else 'Modeli Düzenle'}", expanded=True):
        with st.form(f"model_form_{key_suffix}"):
            tab1, tab2, tab3 = st.tabs([_("model_detail"), _("tech_specs"), _("cost_breakdown") if can_view_costs else "🔒 Maliyet"])

            with tab1:
                c1, c2 = st.columns(2)
                name = c1.text_input(_("model_name"), value="" if is_new else model["name"])
                model_code = c2.text_input(_("model_code"), value="" if is_new else model.get("model_code", ""))
                description = st.text_area(_("description"), value="" if is_new else model.get("description", ""), height=80)

                c1, c2, c3 = st.columns(3)
                cat_list = cats if cats else ["Genel"]
                cat_idx = cat_list.index(model["category"]) if not is_new and model.get("category") in cat_list else 0
                category = c1.selectbox(_("category"), cat_list, index=cat_idx)
                currency = c2.selectbox(_("currency"), CURRENCIES,
                                         index=CURRENCIES.index(model.get("currency", "USD") or "USD"))
                sort_order = c3.number_input(_("sort_order"), value=0 if is_new else model.get("sort_order", 0), min_value=0)

                c1, c2 = st.columns(2)
                base_price = c1.number_input(_("base_price"), value=0.0 if is_new else float(model.get("base_price") or 0), min_value=0.0, step=100.0)
                sale_price = c2.number_input(_("sale_price"), value=0.0 if is_new else float(model.get("sale_price") or 0), min_value=0.0, step=100.0)

                img_file = st.file_uploader(_("upload_image"), type=["png", "jpg", "jpeg", "webp"], key=f"mimg_{key_suffix}")

                opt_ids = [o["id"] for o in all_options]
                opt_names = {o["id"]: o["name"] for o in all_options}
                current_compat = model.get("compatible_options", []) if not is_new else []
                compatible_options = st.multiselect(
                    _("compatible_options"),
                    options=opt_ids,
                    default=[x for x in current_compat if x in opt_ids],
                    format_func=lambda x: opt_names.get(x, str(x)),
                    key=f"mcompat_{key_suffix}"
                )

            with tab2:
                st.info("Teknik özellikleri aşağıya JSON formatında girin: [{\"title\": \"...\", \"value\": \"...\"}]")
                specs_default = json.dumps(model.get("specs", []), ensure_ascii=False, indent=2) if not is_new else "[]"
                specs_json = st.text_area("Teknik Özellikler (JSON)", value=specs_default, height=200, key=f"mspecs_{key_suffix}")

            with tab3:
                if can_view_costs:
                    c1, c2 = st.columns(2)
                    purchase_price = c1.number_input(_("purchase_price"), value=0.0 if is_new else float(model.get("purchase_price") or 0), min_value=0.0, step=10.0)
                    shipping_cost = c2.number_input(_("shipping"), value=0.0 if is_new else float(model.get("shipping_cost") or 0), min_value=0.0, step=10.0)
                    c1, c2 = st.columns(2)
                    customs_tax_rate = c1.number_input(_("customs_rate"), value=3.0 if is_new else float(model.get("customs_tax_rate") or 3), min_value=0.0, max_value=100.0, step=0.5)
                    extra_tax_rate = c2.number_input(_("extra_tax_rate"), value=10.0 if is_new else float(model.get("extra_tax_rate") or 10), min_value=0.0, max_value=100.0, step=0.5)
                    c1, c2, c3, c4 = st.columns(4)
                    port_cost = c1.number_input(_("port_cost"), value=0.0 if is_new else float(model.get("port_cost") or 0), min_value=0.0, step=10.0)
                    document_cost = c2.number_input(_("document_cost"), value=0.0 if is_new else float(model.get("document_cost") or 0), min_value=0.0, step=10.0)
                    installation_cost = c3.number_input(_("installation_cost"), value=0.0 if is_new else float(model.get("installation_cost") or 0), min_value=0.0, step=10.0)
                    other_cost = c4.number_input(_("other_cost"), value=0.0 if is_new else float(model.get("other_cost") or 0), min_value=0.0, step=10.0)
                    cost_note = st.text_input(_("cost_note"), value="" if is_new else model.get("cost_note", ""))
                else:
                    st.warning("Maliyet bilgilerini görüntüleme yetkiniz yok.")
                    purchase_price = shipping_cost = customs_tax_rate = extra_tax_rate = 0.0
                    extra_tax_rate = 10.0; customs_tax_rate = 3.0
                    port_cost = document_cost = installation_cost = other_cost = 0.0
                    cost_note = ""

            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button(_("save"), type="primary")
            cancelled = col2.form_submit_button(_("cancel"))

        if submitted:
            if not name.strip():
                st.error(f"{_('model_name')} zorunludur.")
                return
            try:
                specs = json.loads(specs_json)
            except Exception:
                specs = []
            img_path = model.get("image_path", "") if not is_new else ""
            if img_file:
                saved = save_uploaded_image(img_file, prefix="model")
                if saved:
                    img_path = saved
            data = dict(
                name=name.strip(), model_code=model_code, description=description,
                category=category, currency=currency, base_price=base_price,
                sale_price=sale_price, image_path=img_path,
                gallery_images=model.get("gallery_images", []) if not is_new else [],
                specs=specs, compatible_options=compatible_options,
                manufacturer_id=user["id"] if user["role"] == "manufacturer" else 0,
                sort_order=int(sort_order),
                purchase_price=purchase_price, shipping_cost=shipping_cost,
                customs_tax_rate=customs_tax_rate, extra_tax_rate=extra_tax_rate,
                port_cost=port_cost, document_cost=document_cost,
                installation_cost=installation_cost, other_cost=other_cost,
                cost_note=cost_note,
            )
            if is_new:
                fdb.add_model(**data)
            else:
                fdb.update_model(model["id"], **data)
            st.session_state.pop("model_form", None)
            st.success(_("success"))
            st.rerun()

        if cancelled:
            st.session_state.pop("model_form", None)
            st.rerun()
