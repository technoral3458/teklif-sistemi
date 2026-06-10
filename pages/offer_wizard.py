import streamlit as st
import datetime
from i18n import _
import db.factory as fdb
from utils.costs import calculate_import_cost, calculate_profit, format_currency
from utils.images import image_tag
from config import CURRENCIES, OFFER_STATUSES


def show(user: dict):
    st.title(_("wizard_title"))

    if "wizard" not in st.session_state:
        st.session_state.wizard = {
            "step": 1,
            "customer_id": None,
            "model_id": None,
            "machine_qty": 1,
            "currency": "USD",
            "selected_options": {},  # {opt_id: qty}
            "discount_pct": 0.0,
            "conditions": "",
        }

    wiz = st.session_state.wizard
    step = wiz["step"]

    # Progress indicator
    steps = [_("step_customer"), _("step_machine"), _("step_options"), _("step_summary")]
    cols = st.columns(4)
    for i, s in enumerate(steps, 1):
        color = "🔵" if i == step else ("✅" if i < step else "⚪")
        cols[i - 1].markdown(f"{color} **{s}**")

    st.divider()

    if step == 1:
        _step_customer(user, wiz)
    elif step == 2:
        _step_machine(user, wiz)
    elif step == 3:
        _step_options(user, wiz)
    elif step == 4:
        _step_summary(user, wiz)


def _step_customer(user: dict, wiz: dict):
    st.subheader(_("step_customer"))

    customers = fdb.get_customers(user_id=user["id"], role=user["role"])
    if not customers:
        st.warning("Önce müşteri ekleyin.")
        if st.button("👥 Müşteri Ekle"):
            st.session_state.page = "customers"
            st.rerun()
        return

    cust_options = {c["id"]: c["company_name"] for c in customers}
    cust_ids = list(cust_options.keys())

    current_idx = cust_ids.index(wiz["customer_id"]) if wiz["customer_id"] in cust_ids else 0
    selected_id = st.selectbox(
        _("select_customer"),
        options=cust_ids,
        index=current_idx,
        format_func=lambda x: cust_options[x],
    )
    wiz["customer_id"] = selected_id

    selected_cust = next((c for c in customers if c["id"] == selected_id), None)
    if selected_cust:
        with st.container(border=True):
            st.write(f"**{selected_cust['company_name']}**")
            if selected_cust.get("contact_person"):
                st.write(f"Yetkili: {selected_cust['contact_person']}")
            if selected_cust.get("phone"):
                st.write(f"📞 {selected_cust['phone']}")
            if selected_cust.get("country"):
                st.write(f"📍 {selected_cust['country']} / {selected_cust.get('city', '')}")

    st.divider()
    if st.button(f"➡️ {_('step_machine')}", type="primary"):
        if not wiz["customer_id"]:
            st.error("Müşteri seçiniz.")
            return
        wiz["step"] = 2
        st.rerun()


def _step_machine(user: dict, wiz: dict):
    st.subheader(_("step_machine"))

    cats = [""] + [c["name"] for c in fdb.get_categories()]
    selected_cat = st.selectbox(_("category"), cats, key="wiz_cat")

    models = fdb.get_models(category=selected_cat or None)
    if not models:
        st.info(_("no_records"))
        col1, col2 = st.columns(2)
        if col1.button(f"⬅️ {_('step_customer')}"):
            wiz["step"] = 1; st.rerun()
        return

    cols = st.columns(3)
    for i, model in enumerate(models):
        with cols[i % 3]:
            with st.container(border=True):
                html = image_tag(model["image_path"], width=120)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
                st.write(f"**{model['name']}**")
                if model.get("model_code"):
                    st.caption(model["model_code"])
                price = model["sale_price"] or model["base_price"]
                st.write(format_currency(price, model["currency"]))

                selected = wiz["model_id"] == model["id"]
                label = "✅ Seçildi" if selected else _("select_machine")
                if st.button(label, key=f"sel_m_{model['id']}", type="primary" if selected else "secondary"):
                    wiz["model_id"] = model["id"]
                    wiz["currency"] = model["currency"]
                    wiz["machine_unit_price"] = float(model["sale_price"] or model["base_price"])
                    wiz["selected_options"] = {}
                    st.rerun()

    st.divider()
    col1, col2, col3 = st.columns([2, 2, 3])
    if col1.button(f"⬅️ {_('step_customer')}"):
        wiz["step"] = 1; st.rerun()

    if wiz["model_id"]:
        wiz["machine_qty"] = col2.number_input(_("machine_qty"), min_value=1, value=wiz.get("machine_qty", 1), step=1)
        if col3.button(f"➡️ {_('step_options')}", type="primary"):
            wiz["step"] = 3; st.rerun()
    else:
        col3.warning("Makine seçiniz.")


def _step_options(user: dict, wiz: dict):
    st.subheader(_("step_options"))

    model = fdb.get_model(wiz["model_id"])
    if not model:
        st.error("Model bulunamadı.")
        wiz["step"] = 2; st.rerun()
        return

    st.info(f"Makine: **{model['name']}** × {wiz['machine_qty']} adet")

    options = fdb.get_options(model_id=model["id"])

    if not options:
        st.info("Bu model için opsiyon bulunmuyor.")
    else:
        selected_opts = wiz.get("selected_options", {})
        all_conflict_ids = set()
        for opt_id, qty in selected_opts.items():
            if qty > 0:
                opt = next((o for o in options if o["id"] == opt_id), None)
                if opt:
                    all_conflict_ids.update(opt.get("conflicts_with", []))

        cats_in_opts = list(dict.fromkeys(o.get("category", "Genel") for o in options))

        for cat in cats_in_opts:
            cat_opts = [o for o in options if o.get("category", "Genel") == cat]
            st.subheader(f"📦 {cat}")
            for opt in cat_opts:
                is_conflicted = opt["id"] in all_conflict_ids and selected_opts.get(opt["id"], 0) == 0
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 5, 2])
                    with c1:
                        html = image_tag(opt["image_path"], width=60)
                        if html:
                            st.markdown(html, unsafe_allow_html=True)
                    with c2:
                        label = f"{'~~' if is_conflicted else ''}**{opt['name']}**{'~~' if is_conflicted else ''}"
                        st.markdown(label)
                        if opt.get("description"):
                            st.caption(opt["description"])
                        price = opt["sale_price"] or opt["list_price"]
                        st.write(format_currency(price, opt["currency"]))
                        if is_conflicted:
                            st.warning(f"⚠️ {_('conflict_warning')}")
                    with c3:
                        if is_conflicted:
                            st.write("—")
                        elif opt["qty_type"] == "FIXED_1":
                            checked = st.checkbox("Ekle", value=selected_opts.get(opt["id"], 0) > 0,
                                                   key=f"wiz_opt_{opt['id']}", disabled=is_conflicted)
                            selected_opts[opt["id"]] = 1 if checked else 0
                        elif opt["qty_type"] == "PER_MACHINE":
                            checked = st.checkbox("Ekle", value=selected_opts.get(opt["id"], 0) > 0,
                                                   key=f"wiz_opt_{opt['id']}", disabled=is_conflicted)
                            selected_opts[opt["id"]] = wiz["machine_qty"] if checked else 0
                        else:
                            qty = st.number_input("Adet", min_value=0,
                                                   value=selected_opts.get(opt["id"], 0),
                                                   step=1, key=f"wiz_opt_{opt['id']}")
                            selected_opts[opt["id"]] = qty

        wiz["selected_options"] = selected_opts

    st.divider()
    col1, col2 = st.columns(2)
    if col1.button(f"⬅️ {_('step_machine')}"):
        wiz["step"] = 2; st.rerun()
    if col2.button(f"➡️ {_('step_summary')}", type="primary"):
        wiz["step"] = 4; st.rerun()


def _step_summary(user: dict, wiz: dict):
    st.subheader(_("step_summary"))

    model = fdb.get_model(wiz["model_id"])
    customer = fdb.get_customer(wiz["customer_id"])
    options = fdb.get_options()
    opts_map = {o["id"]: o for o in options}

    if not model or not customer:
        st.error("Model veya müşteri bulunamadı.")
        wiz["step"] = 1; st.rerun()
        return

    machine_qty = wiz.get("machine_qty", 1)
    machine_unit = wiz.get("machine_unit_price", float(model["sale_price"] or model["base_price"]))
    currency = wiz.get("currency", model["currency"])

    # Allow editing currency and machine price
    col1, col2, col3 = st.columns(3)
    currency = col1.selectbox(_("offer_currency"), CURRENCIES,
                               index=CURRENCIES.index(currency) if currency in CURRENCIES else 0,
                               key="wiz_currency")
    machine_unit = col2.number_input(_("unit_price"), value=machine_unit, min_value=0.0, step=100.0, key="wiz_munit")
    discount_pct = col3.number_input(_("discount_pct"), value=wiz.get("discount_pct", 0.0),
                                      min_value=0.0, max_value=100.0, step=0.5, key="wiz_disc")

    wiz["currency"] = currency
    wiz["machine_unit_price"] = machine_unit
    wiz["discount_pct"] = discount_pct

    machine_total = machine_unit * machine_qty

    # Options lines
    selected_opts = wiz.get("selected_options", {})
    opt_items = []
    options_total = 0.0

    for opt_id, qty in selected_opts.items():
        if qty <= 0:
            continue
        opt = opts_map.get(opt_id)
        if not opt:
            continue
        unit_price = float(opt["sale_price"] or opt["list_price"])
        line_total = unit_price * qty
        options_total += line_total
        opt_items.append({
            "option_id": opt_id,
            "option_name": opt["name"],
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": line_total,
            "unit_cost": 0.0,
            "total_cost": 0.0,
        })

    subtotal = machine_total + options_total
    discount_amount = subtotal * discount_pct / 100
    grand_total = subtotal - discount_amount

    # Summary table
    with st.container(border=True):
        st.write(f"**{_('customer')}:** {customer['company_name']}")
        st.write(f"**{_('model_name')}:** {model['name']} × {machine_qty}")
        st.divider()
        st.write(f"**{_('machine_price')}:** {format_currency(machine_unit, currency)} × {machine_qty} = {format_currency(machine_total, currency)}")
        if opt_items:
            st.subheader(_("options_for_machine"))
            for item in opt_items:
                st.write(f"• {item['option_name']} × {item['quantity']} = {format_currency(item['total_price'], currency)}")
        st.divider()
        st.write(f"**{_('subtotal')}:** {format_currency(subtotal, currency)}")
        if discount_pct > 0:
            st.write(f"**İndirim ({discount_pct:.1f}%):** -{format_currency(discount_amount, currency)}")
        st.markdown(f"### 💰 {_('grand_total')}: {format_currency(grand_total, currency)}")

    conditions = st.text_area(_("offer_conditions"), value=wiz.get("conditions", ""), height=80)
    wiz["conditions"] = conditions

    offer_date = st.date_input(_("offer_date"), value=datetime.date.today())

    st.divider()
    col1, col2 = st.columns(2)
    if col1.button(f"⬅️ {_('step_options')}"):
        wiz["step"] = 3; st.rerun()

    if col2.button(f"✅ {_('create_offer')}", type="primary"):
        offer_id = fdb.create_offer(
            user_id=user["id"],
            customer_id=wiz["customer_id"],
            model_id=wiz["model_id"],
            machine_qty=machine_qty,
            currency=currency,
            machine_unit_price=machine_unit,
            machine_total=machine_total,
            options_total=options_total,
            discount_pct=discount_pct,
            subtotal=subtotal,
            grand_total=grand_total,
            conditions=conditions,
            status="Beklemede",
            offer_date=str(offer_date),
        )
        if opt_items:
            fdb.add_offer_items(offer_id, opt_items)

        del st.session_state["wizard"]
        st.success(f"✅ Teklif oluşturuldu! (ID: {offer_id})")
        st.session_state.page = "offers"
        st.rerun()
