import streamlit as st
from i18n import _
import db.factory as fdb
import db.users as udb
from utils.images import save_uploaded_image, image_tag


def show(user: dict):
    st.title(_("admin_title"))

    tab1, tab2 = st.tabs([_("company_profile"), _("user_list")])

    with tab1:
        _company_tab()

    with tab2:
        _users_tab()


def _company_tab():
    profile = fdb.get_company_profile()

    with st.form("company_profile_form"):
        company_name = st.text_input(_("company_name_sys"), value=profile.get("company_name", ""))
        website = st.text_input(_("website"), value=profile.get("website", ""))
        footer = st.text_area(_("footer_text"), value=profile.get("footer_text", ""), height=80)
        logo_file = st.file_uploader(_("company_logo"), type=["png", "jpg", "jpeg", "webp"])
        if profile.get("logo_path"):
            html = image_tag(profile["logo_path"], width=120)
            if html:
                st.markdown(html, unsafe_allow_html=True)
        submitted = st.form_submit_button(_("save"), type="primary")

    if submitted:
        logo_path = profile.get("logo_path", "")
        if logo_file:
            saved = save_uploaded_image(logo_file, prefix="company")
            if saved:
                logo_path = saved
        fdb.update_company_profile(
            company_name=company_name,
            website=website,
            footer_text=footer,
            logo_path=logo_path,
        )
        st.success(_("success"))
        st.rerun()


def _users_tab():
    users = udb.get_all_users()

    st.write(f"Toplam {len(users)} kullanıcı")

    for u in users:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 3, 3])
            with col1:
                role_label = {"admin": "Yönetici", "dealer": "Bayi", "manufacturer": "Üretici"}.get(u["role"], u["role"])
                st.write(f"**{u['company_name']}** ({role_label})")
                st.caption(u["email"])
            with col2:
                status = "✅ Aktif" if u["is_active"] and u["is_approved"] else ("⏳ Onay Bekliyor" if not u["is_approved"] else "⛔ Pasif")
                st.write(status)
                st.caption(f"Kayıt: {u.get('created_at', '')[:10]}")
            with col3:
                if u["role"] != "admin":
                    c1, c2 = st.columns(2)
                    if not u["is_approved"]:
                        if c1.button("✅", key=f"app_u{u['id']}", help="Onayla"):
                            udb.update_user_admin(u["id"], is_approved=1, is_active=1)
                            st.rerun()
                    elif u["is_active"]:
                        if c1.button("⛔", key=f"deact_u{u['id']}", help="Pasif yap"):
                            udb.update_user_admin(u["id"], is_active=0)
                            st.rerun()
                    else:
                        if c1.button("✅", key=f"act_u{u['id']}", help="Aktif yap"):
                            udb.update_user_admin(u["id"], is_active=1)
                            st.rerun()
                    if c2.button("🗑️", key=f"del_u{u['id']}", help="Sil"):
                        st.session_state[f"confirm_del_u{u['id']}"] = True

                    if st.session_state.get(f"confirm_del_u{u['id']}"):
                        st.warning(f"{u['email']} silinsin mi?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button(_("yes"), key=f"yes_du{u['id']}"):
                            udb.delete_user(u["id"])
                            del st.session_state[f"confirm_del_u{u['id']}"]
                            st.rerun()
                        if cc2.button(_("no"), key=f"no_du{u['id']}"):
                            del st.session_state[f"confirm_del_u{u['id']}"]
                            st.rerun()
