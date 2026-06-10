import streamlit as st
from i18n import _
import db.users as udb
import db.factory as fdb


def show(user: dict):
    st.title(_("dealers_title"))

    users = udb.get_all_users()
    dealers = [u for u in users if u["role"] in ("dealer", "manufacturer")]
    cats = [c["name"] for c in fdb.get_categories()]

    pending = [u for u in dealers if not u["is_approved"]]
    active = [u for u in dealers if u["is_approved"] and u["is_active"]]
    inactive = [u for u in dealers if u["is_approved"] and not u["is_active"]]

    if pending:
        st.subheader(f"⏳ Onay Bekleyenler ({len(pending)})")
        for u in pending:
            _dealer_card(u, cats, show_approve=True)

    if active:
        st.subheader(f"✅ Aktif ({len(active)})")
        for u in active:
            _dealer_card(u, cats)

    if inactive:
        st.subheader(f"⛔ Pasif ({len(inactive)})")
        for u in inactive:
            _dealer_card(u, cats)

    if not dealers:
        st.info(_("no_records"))


def _dealer_card(u: dict, cats: list, show_approve: bool = False):
    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 3, 3])
        with col1:
            role_label = {"dealer": "Bayi", "manufacturer": "Üretici", "admin": "Admin"}.get(u["role"], u["role"])
            st.write(f"**{u['company_name']}** ({role_label})")
            st.caption(u["email"])
            if u.get("phone"):
                st.caption(f"📞 {u['phone']}")
        with col2:
            cat_list = u["allowed_categories"].split(",") if u["allowed_categories"] else []
            display_cats = ", ".join(cat_list) if cat_list else _("all_categories")
            st.write(f"Kategoriler: {display_cats}")
            st.write(f"Maliyet Görme: {'✅' if u['can_view_costs'] else '❌'}")
        with col3:
            if show_approve:
                c1, c2 = st.columns(2)
                if c1.button(f"✅ {_('approve')}", key=f"app_{u['id']}"):
                    udb.update_user_admin(u["id"], is_approved=1, is_active=1)
                    st.success(f"{u['company_name']} onaylandı.")
                    st.rerun()
                if c2.button(f"❌ {_('reject')}", key=f"rej_{u['id']}"):
                    udb.update_user_admin(u["id"], is_approved=1, is_active=0)
                    st.warning(f"{u['company_name']} reddedildi.")
                    st.rerun()
            else:
                if u["is_active"]:
                    if st.button("⛔ Pasif Yap", key=f"deact_{u['id']}"):
                        udb.update_user_admin(u["id"], is_active=0)
                        st.rerun()
                else:
                    if st.button("✅ Aktif Yap", key=f"act_{u['id']}"):
                        udb.update_user_admin(u["id"], is_active=1)
                        st.rerun()

        if st.session_state.get(f"edit_dealer_{u['id']}"):
            _dealer_edit_form(u, cats)
        else:
            if st.button("✏️ Ayarlar", key=f"edit_d_{u['id']}"):
                st.session_state[f"edit_dealer_{u['id']}"] = True
                st.rerun()


def _dealer_edit_form(u: dict, cats: list):
    with st.form(f"dealer_edit_{u['id']}"):
        st.subheader(f"Bayi Ayarları: {u['company_name']}")

        current_cats = u["allowed_categories"].split(",") if u["allowed_categories"] else []
        selected_cats = st.multiselect(
            _("allowed_categories"),
            options=cats,
            default=[c for c in current_cats if c in cats],
        )
        can_view = st.checkbox(_("can_view_costs"), value=u["can_view_costs"])

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button(_("save"), type="primary")
        cancelled = col2.form_submit_button(_("cancel"))

    if submitted:
        udb.update_user_admin(
            u["id"],
            allowed_categories=",".join(selected_cats),
            can_view_costs=1 if can_view else 0,
        )
        st.session_state.pop(f"edit_dealer_{u['id']}", None)
        st.success(_("success"))
        st.rerun()

    if cancelled:
        st.session_state.pop(f"edit_dealer_{u['id']}", None)
        st.rerun()
