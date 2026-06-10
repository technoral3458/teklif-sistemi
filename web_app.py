import streamlit as st
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import db.users as udb
import db.factory as fdb
from i18n import _, SUPPORTED_LANGS
from config import APP_NAME, APP_ICON, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM


# ── Initialise databases ──────────────────────────────────────────────
udb.init()
fdb.init()


# ── Mobile detection ──────────────────────────────────────────────────
def _is_mobile() -> bool:
    try:
        ua = st.context.headers.get("User-Agent", "").lower()
        return any(x in ua for x in ["mobile", "android", "iphone", "ipad"])
    except Exception:
        return False


IS_MOBILE = _is_mobile()

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed" if IS_MOBILE else "expanded",
)


# ── Language init ─────────────────────────────────────────────────────
if "lang" not in st.session_state:
    try:
        accept = st.context.headers.get("Accept-Language", "")
        primary = accept.split(",")[0][:2].lower() if accept else "tr"
        st.session_state.lang = primary if primary in SUPPORTED_LANGS else "tr"
    except Exception:
        st.session_state.lang = "tr"


# ── SMTP helper ───────────────────────────────────────────────────────
def _send_email(to_email: str, code: str, subject: str = APP_NAME) -> bool:
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASS]):
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{APP_NAME} <{SMTP_FROM or SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(f"Doğrulama Kodunuz: {code}", "plain", "utf-8"))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False


# ── Auth pages ────────────────────────────────────────────────────────
def show_login():
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        # Language selector at top
        lang_col1, lang_col2 = st.columns([3, 1])
        with lang_col2:
            lang_labels = {"tr": "🇹🇷 TR", "en": "🇬🇧 EN", "zh": "🇨🇳 ZH"}
            selected_lang = st.selectbox(
                _("language"),
                SUPPORTED_LANGS,
                index=SUPPORTED_LANGS.index(st.session_state.lang),
                format_func=lambda x: lang_labels.get(x, x),
                key="lang_login",
                label_visibility="collapsed",
            )
            if selected_lang != st.session_state.lang:
                st.session_state.lang = selected_lang
                st.rerun()

        st.markdown(f"<h2 style='text-align:center'>{APP_ICON} {APP_NAME}</h2>", unsafe_allow_html=True)
        st.divider()

        tab1, tab2, tab3 = st.tabs([_("login_tab"), _("reg_tab"), _("forgot_tab")])

        with tab1:
            _login_tab()
        with tab2:
            _register_tab()
        with tab3:
            _forgot_tab()


def _login_tab():
    with st.form("login_form"):
        email = st.text_input(_("email"))
        password = st.text_input(_("password"), type="password")
        submitted = st.form_submit_button(_("login_btn"), type="primary", use_container_width=True)

    if submitted:
        user = udb.get_user_by_email(email.strip().lower())
        if not user or not udb.check_password(password, user["password"]):
            st.error(_("wrong_credentials"))
            return
        if not user["is_approved"]:
            st.warning(_("pending_approval"))
            return
        if not user["is_active"]:
            st.error(_("account_inactive"))
            return
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()


def _register_tab():
    with st.form("reg_form"):
        user_type = st.radio(_("business_type"), ["dealer", "manufacturer"],
                             format_func=lambda x: _("dealer") if x == "dealer" else _("manufacturer"),
                             horizontal=True)
        company = st.text_input(_("company_name"))
        email = st.text_input(_("email"))
        phone = st.text_input(_("phone"))
        password = st.text_input(_("password"), type="password")
        submitted = st.form_submit_button(_("register_btn"), type="primary", use_container_width=True)

    st.caption(_("required_fields"))

    if submitted:
        if not all([company.strip(), email.strip(), phone.strip(), password]):
            st.error(_("required_fields"))
            return
        ok, reason = udb.register_user(
            email=email.strip().lower(),
            password=password,
            company_name=company.strip(),
            user_type=user_type,
            phone=phone.strip(),
        )
        if ok:
            st.success(_("reg_success"))
        else:
            st.error(_("email_in_use"))


def _forgot_tab():
    step = st.session_state.get("forgot_step", 1)

    if step == 1:
        with st.form("forgot_form1"):
            email = st.text_input(_("forgot_email"))
            submitted = st.form_submit_button(_("send_code"), type="primary", use_container_width=True)
        if submitted:
            token = udb.create_reset_token(email.strip().lower())
            if token:
                sent = _send_email(email.strip().lower(), token, subject=f"{APP_NAME} — Şifre Sıfırlama")
                if not sent:
                    st.warning(f"Mail gönderilemedi. Test kodu: {token}")
                st.session_state.forgot_email = email.strip().lower()
                st.session_state.forgot_step = 2
                st.rerun()
            else:
                st.error(_("no_email"))

    elif step == 2:
        with st.form("forgot_form2"):
            code = st.text_input(_("enter_code"))
            new_pass = st.text_input(_("new_password"), type="password")
            submitted = st.form_submit_button(_("change_password_btn"), type="primary", use_container_width=True)
        if submitted:
            forgot_email = st.session_state.get("forgot_email", "")
            if udb.verify_reset_token(forgot_email, code.strip()):
                udb.reset_password(forgot_email, new_pass)
                st.success(_("pass_changed"))
                del st.session_state["forgot_step"]
                del st.session_state["forgot_email"]
            else:
                st.error(_("wrong_code"))


# ── Sidebar / navigation ──────────────────────────────────────────────
def show_sidebar(user: dict):
    with st.sidebar:
        profile = fdb.get_company_profile()
        company_name = profile.get("company_name") or user["company_name"]
        st.markdown(f"### {APP_ICON} {company_name}")

        role = user["role"]
        role_label = {"admin": _("role_admin"), "dealer": _("role_dealer"),
                      "manufacturer": _("role_manufacturer")}.get(role, role)
        st.caption(f"{user['company_name']} — {role_label}")
        st.divider()

        # Language
        lang_labels = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "zh": "🇨🇳 中文"}
        selected_lang = st.selectbox(
            _("language"),
            SUPPORTED_LANGS,
            index=SUPPORTED_LANGS.index(st.session_state.lang),
            format_func=lambda x: lang_labels.get(x, x),
            key="lang_sidebar",
        )
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

        st.divider()

        # Menu items based on role
        menu = _build_menu(user)
        current_page = st.session_state.get("page", "dashboard")

        for page_key, label in menu:
            is_active = current_page == page_key
            if st.button(label, key=f"nav_{page_key}",
                         use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.page = page_key
                st.rerun()

        st.divider()
        if st.button(_("logout"), use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def _build_menu(user: dict) -> list:
    role = user["role"]
    menu = [("dashboard", _("menu_dashboard"))]

    if role in ("dealer", "admin"):
        menu.append(("new_offer", _("menu_new_offer")))
        menu.append(("customers", _("menu_customers")))
        menu.append(("offers", _("menu_offers")))
        menu.append(("orders", _("menu_orders")))

    if role in ("admin", "manufacturer"):
        menu.append(("models", _("menu_models")))
        menu.append(("options", _("menu_options")))
        menu.append(("categories", _("menu_categories")))

    if role == "admin":
        menu.append(("dealers", _("menu_dealers")))

    if user.get("can_view_costs") or role == "admin":
        menu.append(("costs", _("menu_costs")))

    menu.append(("profile", _("menu_profile")))

    if role == "admin":
        menu.append(("admin", _("menu_admin")))

    return menu


# ── Main router ───────────────────────────────────────────────────────
def main():
    user = st.session_state.get("user")

    if not user:
        show_login()
        return

    show_sidebar(user)

    page = st.session_state.get("page", "dashboard")

    if page == "dashboard":
        from pages import dashboard
        dashboard.show(user)

    elif page == "new_offer":
        from pages import offer_wizard
        offer_wizard.show(user)

    elif page == "customers":
        from pages import customers
        customers.show(user)

    elif page == "offers":
        from pages import offers
        offers.show(user)

    elif page == "orders":
        from pages import orders
        orders.show(user)

    elif page == "models":
        from pages import models
        models.show(user)

    elif page == "options":
        from pages import options
        options.show(user)

    elif page == "categories":
        from pages import categories
        categories.show(user)

    elif page == "dealers":
        if user["role"] == "admin":
            from pages import dealers
            dealers.show(user)
        else:
            st.error("Bu sayfaya erişim yetkiniz yok.")

    elif page == "costs":
        if user.get("can_view_costs") or user["role"] == "admin":
            from pages import costs
            costs.show(user)
        else:
            st.error("Bu sayfaya erişim yetkiniz yok.")

    elif page == "profile":
        from pages import profile
        profile.show(user)

    elif page == "admin":
        if user["role"] == "admin":
            from pages import admin
            admin.show(user)
        else:
            st.error("Bu sayfaya erişim yetkiniz yok.")

    else:
        st.session_state.page = "dashboard"
        st.rerun()


if __name__ == "__main__":
    main()
else:
    main()
