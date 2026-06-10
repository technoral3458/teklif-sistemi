import streamlit as st
from i18n import _
import db.factory as fdb
from utils.images import save_uploaded_image, image_tag


def show(user: dict):
    st.title(_("categories_title"))

    if st.button(f"➕ {_('add_category')}", type="primary"):
        st.session_state["cat_form"] = "new"

    if st.session_state.get("cat_form") == "new":
        _cat_form()

    cats = fdb.get_categories()
    if not cats:
        st.info(_("no_records"))
        return

    for cat in cats:
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 4, 2])
            with col1:
                html = image_tag(cat["image_path"], width=60)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.write("📁")
            with col2:
                st.write(f"**{cat['name']}**")
                st.caption(f"Sıra: {cat['sort_order']}")
            with col3:
                c1, c2 = st.columns(2)
                if c1.button(_("edit"), key=f"edit_cat{cat['id']}"):
                    st.session_state["cat_form"] = f"edit_{cat['id']}"
                    st.rerun()
                if c2.button(_("delete"), key=f"del_cat{cat['id']}"):
                    st.session_state[f"confirm_del_cat{cat['id']}"] = True

            if st.session_state.get(f"confirm_del_cat{cat['id']}"):
                st.warning(_("confirm_delete"))
                cc1, cc2 = st.columns(2)
                if cc1.button(_("yes"), key=f"yes_del_cat{cat['id']}"):
                    fdb.delete_category(cat["id"])
                    del st.session_state[f"confirm_del_cat{cat['id']}"]
                    st.rerun()
                if cc2.button(_("no"), key=f"no_del_cat{cat['id']}"):
                    del st.session_state[f"confirm_del_cat{cat['id']}"]
                    st.rerun()

            if st.session_state.get("cat_form") == f"edit_{cat['id']}":
                _cat_form(cat)


def _cat_form(cat: dict = None):
    is_new = cat is None
    key_suffix = "new" if is_new else str(cat["id"])

    with st.form(f"cat_form_{key_suffix}"):
        st.subheader(_("add_category") if is_new else _("edit_category"))
        name = st.text_input(_("category_name"), value="" if is_new else cat["name"])
        sort_order = st.number_input(_("sort_order"), value=0 if is_new else cat.get("sort_order", 0),
                                     min_value=0, step=1)
        img_file = st.file_uploader(_("upload_image"), type=["png", "jpg", "jpeg", "webp"])

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button(_("save"), type="primary")
        cancelled = col2.form_submit_button(_("cancel"))

    if submitted:
        if not name.strip():
            st.error(f"{_('category_name')} zorunludur.")
            return
        img_path = cat.get("image_path", "") if not is_new else ""
        if img_file:
            saved = save_uploaded_image(img_file, prefix="cat")
            if saved:
                img_path = saved
        if is_new:
            ok = fdb.add_category(name.strip(), img_path, int(sort_order))
            if not ok:
                st.error("Bu kategori adı zaten var!")
                return
        else:
            fdb.update_category(cat["id"], name.strip(), img_path, int(sort_order))
        st.session_state.pop("cat_form", None)
        st.success(_("success"))
        st.rerun()

    if cancelled:
        st.session_state.pop("cat_form", None)
        st.rerun()
