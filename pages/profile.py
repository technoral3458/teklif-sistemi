import streamlit as st
from i18n import _
import db.users as udb
from utils.images import save_uploaded_image, image_tag


def show(user: dict):
    st.title(_("profile_title"))

    tab1, tab2 = st.tabs(["Firma Bilgileri", _("change_password")])

    with tab1:
        _profile_tab(user)

    with tab2:
        _password_tab(user)


def _profile_tab(user: dict):
    with st.form("profile_form"):
        company = st.text_input("Firma Adı", value=user.get("company_name", ""))
        phone = st.text_input(_("phone_field") if hasattr(_, "__call__") else "Telefon",
                               value=user.get("phone", ""))
        website = st.text_input(_("website"), value=user.get("website", ""))
        address = st.text_area(_("address"), value=user.get("address_full", ""), height=80)

        st.write(f"**E-Posta:** {user['email']}")
        role_labels = {"admin": "Sistem Yöneticisi", "dealer": "Bayi", "manufacturer": "Üretici"}
        st.write(f"**Rol:** {role_labels.get(user['role'], user['role'])}")

        logo_file = st.file_uploader(_("company_logo"), type=["png", "jpg", "jpeg", "webp"])
        if user.get("logo_path"):
            html = image_tag(user["logo_path"], width=100)
            if html:
                st.markdown(f"Mevcut logo: {html}", unsafe_allow_html=True)

        submitted = st.form_submit_button(_("save"), type="primary")

    if submitted:
        logo_path = user.get("logo_path", "")
        if logo_file:
            saved = save_uploaded_image(logo_file, prefix="logo")
            if saved:
                logo_path = saved
        udb.update_user_profile(
            user["id"],
            company_name=company.strip(),
            phone=phone,
            website=website,
            address_full=address,
            logo_path=logo_path,
        )
        # Update session
        st.session_state.user["company_name"] = company.strip()
        st.session_state.user["phone"] = phone
        st.session_state.user["website"] = website
        st.session_state.user["address_full"] = address
        st.session_state.user["logo_path"] = logo_path
        st.success(_("profile_saved"))
        st.rerun()


def _password_tab(user: dict):
    with st.form("pass_form"):
        current = st.text_input(_("current_password"), type="password")
        new_pass = st.text_input(_("new_password"), type="password")
        confirm = st.text_input(_("confirm_password"), type="password")
        submitted = st.form_submit_button(_("change_password_btn"), type="primary")

    if submitted:
        if not udb.check_password(current, user["password"]):
            st.error(_("wrong_current_pass"))
            return
        if new_pass != confirm:
            st.error(_("pass_mismatch"))
            return
        if len(new_pass) < 6:
            st.error("Şifre en az 6 karakter olmalıdır.")
            return
        udb.change_password(user["id"], new_pass)
        fresh = udb.get_user_by_id(user["id"])
        if fresh:
            st.session_state.user["password"] = fresh["password"]
        st.success(_("pass_changed"))
