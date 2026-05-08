import streamlit as st
import sqlite3
import pandas as pd
import math

# =====================================================================
# 🌍 ÇOKLU DİL SÖZLÜĞÜ (TR - EN - ZH)
# =====================================================================
DICT_DEALER = {
    "tr": {
        "title": "🏢 Bayi ve Üretici Yönetimi",
        "search_ph": "🔍 Firma Adı, E-Posta veya Telefon ile ara...",
        "no_user": "Sistemde henüz kayıtlı kullanıcı bulunmuyor.",
        "no_match": "Arama kriterinize uygun kullanıcı bulunamadı.",
        "active": "Aktif", "pending": "Askıda",
        "badge_admin": "👑 YÖNETİCİ", "not_spec": "Belirtilmemiş",
        "tot_offer": "Toplam Teklif", "tot_vol": "Toplam Hacim",
        "conv_offer": "Siparişe Dönen", "conv_vol": "Sipariş Hacmi",
        "comp_name": "Firma Adı", "act_type": "Faaliyet Türü",
        "email": "E-Posta Adresi", "phone": "Telefon",
        "type_dealer": "Satıcı (Bayi)", "type_prod": "Üretici", "type_admin": "Yönetici",
        "cat_title": "📦 Kategoriler (Filtre):",
        "cat_help": "Satış izni verilen kategoriler:",
        "cat_warn": "💡 Sadece Satıcı (Bayi) için geçerlidir.",
        "menu_title": "🔑 Menü İzinleri:",
        "btn_update": "💾 BİLGİLERİ GÜNCELLE",
        "toast_upd": "kullanıcısının bilgileri güncellendi!",
        "err_self": "Kendi yönetici hesabınızı askıya alamaz veya silemezsiniz.",
        "btn_sus": "🚫 Askıya Al", "btn_app": "✅ Onayla", "btn_del": "🗑️ Sil",
        "btn_manage": "⚙️ Yönet", "btn_back": "⬅️ Listeye Dön", "page": "Sayfa",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif", "m_cust": "👥 Müşteriler",
        "m_past": "📋 Geçmiş Teklifler", "m_order": "📦 Siparişler", "m_model": "📦 Modeller",
        "m_deal": "🏢 Bayiler", "m_prof": "⚙️ Ayarlar"
    },
    "en": {
        "title": "🏢 Dealer and Manufacturer Management",
        "search_ph": "🔍 Search by Company, Email or Phone...",
        "no_user": "No registered users found in the system.",
        "no_match": "No users match your search criteria.",
        "active": "Active", "pending": "Suspended",
        "badge_admin": "👑 ADMIN", "not_spec": "Not Specified",
        "tot_offer": "Total Offers", "tot_vol": "Total Volume",
        "conv_offer": "Converted Orders", "conv_vol": "Order Volume",
        "comp_name": "Company Name", "act_type": "Role",
        "email": "Email Address", "phone": "Phone",
        "type_dealer": "Dealer", "type_prod": "Producer", "type_admin": "Admin",
        "cat_title": "📦 Allowed Categories:",
        "cat_help": "Select allowed categories:",
        "cat_warn": "💡 Applies ONLY to Dealers.",
        "menu_title": "🔑 Menu Access:",
        "btn_update": "💾 UPDATE INFO",
        "toast_upd": "permissions updated!",
        "err_self": "You cannot suspend or delete your own account.",
        "btn_sus": "🚫 Suspend", "btn_app": "✅ Approve", "btn_del": "🗑️ Delete",
        "btn_manage": "⚙️ Manage", "btn_back": "⬅️ Back to List", "page": "Page",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 New Offer", "m_cust": "👥 Customers",
        "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_model": "📦 Models",
        "m_deal": "🏢 Dealers", "m_prof": "⚙️ Settings"
    },
    "zh": {
        "title": "🏢 经销商和制造商管理",
        "search_ph": "🔍 按公司、电子邮件或电话搜索...",
        "no_user": "系统中尚未找到注册用户。",
        "no_match": "未找到符合搜索条件的用户。",
        "active": "活跃", "pending": "暂停",
        "badge_admin": "👑 管理员", "not_spec": "未指定",
        "tot_offer": "总报价", "tot_vol": "总交易量",
        "conv_offer": "已转换订单", "conv_vol": "订单量",
        "comp_name": "公司名称", "act_type": "角色",
        "email": "电子邮件", "phone": "电话",
        "type_dealer": "经销商", "type_prod": "制造商", "type_admin": "管理员",
        "cat_title": "📦 允许的类别:",
        "cat_help": "选择允许的类别:",
        "cat_warn": "💡 仅适用于经销商。",
        "menu_title": "🔑 菜单访问:",
        "btn_update": "💾 更新信息",
        "toast_upd": "权限已更新！",
        "err_self": "您不能暂停或删除自己的帐户。",
        "btn_sus": "🚫 暂停", "btn_app": "✅ 批准", "btn_del": "🗑️ 删除",
        "btn_manage": "⚙️ 管理", "btn_back": "⬅️ 返回列表", "page": "页",
        
        "m_dash": "📊 仪表板", "m_new": "📝 新报价", "m_cust": "👥 客户",
        "m_past": "📋 历史报价", "m_order": "📦 订单", "m_model": "📦 型号",
        "m_deal": "🏢 经销商", "m_prof": "⚙️ 设置"
    }
}

def _m(key): 
    lang = "tr"
    if "language" in st.session_state: lang = st.session_state.language
    elif "lang" in st.session_state: lang = st.session_state.lang
    lang = str(lang).lower()
    if lang not in DICT_DEALER: lang = "tr"
    return DICT_DEALER[lang].get(key, key)

# =====================================================================
# VERİTABANI İŞLEMLERİ
# =====================================================================
def repair_users_db():
    try:
        conn = sqlite3.connect('users.db')
        try: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Dealer'")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
        except: pass
        conn.commit(); conn.close()
    except: pass

repair_users_db()

def get_db_data():
    try:
        conn_f = sqlite3.connect('factory_data.db')
        all_cats = [c[0] for c in conn_f.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()]
        conn_f.close()
    except: all_cats = []

    conn = sqlite3.connect('users.db')
    try: users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role, allowed_categories FROM users ORDER BY id DESC").fetchall()
    except: users = [(*u, "") for u in conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role FROM users ORDER BY id DESC").fetchall()]
    conn.close()
    
    conn_s = sqlite3.connect('sales_data.db')
    try: all_offs = conn_s.execute("SELECT user_id, status, total_price FROM offers").fetchall()
    except: all_offs = []
    conn_s.close()
    
    df_o = pd.DataFrame(all_offs, columns=['user_id', 'status', 'total_price']) if all_offs else pd.DataFrame(columns=['user_id', 'status', 'total_price'])
    return users, all_cats, df_o

# =====================================================================
# ANA YÖNETİM MODÜLÜ (LİSTE & DETAY MANTIKLI)
# =====================================================================
def show_dealer_management():
    # 🎨 SAAS LİSTE VE DETAY CSS KODLARI 🎨
    st.markdown("""
    <style>
    /* Liste Satır Tasarımı */
    .list-row {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s;
    }
    .list-row:hover {
        border-color: #cbd5e1;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .list-col { display: flex; flex-direction: column; justify-content: center; }
    
    /* İstatistik Çubuğu (Detay Sayfası İçin) */
    .stats-bar {
        background-color: #ffffff; border-radius: 12px; display: flex; 
        padding: 20px 0; margin: 20px 0; border: 1px solid #f1f5f9;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .stat-box { flex: 1; text-align: center; border-right: 1px solid #f1f5f9; }
    .stat-box:last-child { border-right: none; }
    .stat-lbl { font-size: 11px; font-weight: 800; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }
    .stat-val { font-size: 24px; font-weight: 900; color: #1e293b; }
    .stat-val.blue { color: #3b82f6; }
    .stat-val.green { color: #10b981; }
    
    /* Rozetler */
    .badge-active { background:#ecfdf5; color:#10b981; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:800; border:1px solid #a7f3d0; }
    .badge-suspended { background:#fef2f2; color:#ef4444; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:800; border:1px solid #fecaca; }
    .role-admin { color:#ea580c; font-weight:bold; font-size:12px; }
    .role-user { color:#3b82f6; font-weight:bold; font-size:12px; }
    </style>
    """, unsafe_allow_html=True)

    # Oturum Yönetimi
    if "manage_dealer_id" not in st.session_state:
        st.session_state.manage_dealer_id = None
    if "dealer_page" not in st.session_state:
        st.session_state.dealer_page = 1

    users, all_categories, df_offers = get_db_data()
    types_internal = ["Satıcı (Bayi)", "Üretici", "Yönetici"]
    types_display = [_m("type_dealer"), _m("type_prod"), _m("type_admin")]

    # =========================================================
    # GÖRÜNÜM 2: DETAY VE YÖNETİM SAYFASI (PROFİL İÇİ)
    # =========================================================
    if st.session_state.manage_dealer_id:
        target_u = [u for u in users if u[0] == st.session_state.manage_dealer_id]
        if not target_u:
            st.session_state.manage_dealer_id = None
            st.rerun()
            
        u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role, u_allowed_cats = target_u[0]
        
        st.button(_m("btn_back"), on_click=lambda: st.session_state.update(manage_dealer_id=None))
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
        
        # İstatistik Hesaplama
        d_offers = df_offers[df_offers['user_id'] == u_id] if not df_offers.empty else pd.DataFrame()
        t_count = len(d_offers); t_vol = d_offers['total_price'].sum() if t_count > 0 else 0
        c_offers = d_offers[d_offers['status'].isin(["Onaylandı", "Siparişe Çevir"])] if t_count > 0 else pd.DataFrame()
        c_count = len(c_offers); c_vol = c_offers['total_price'].sum() if c_count > 0 else 0
        
        status_text = _m("active") if u_approved else _m("pending")
        badge_html = f"<span class='badge-active'>🟢 {status_text}</span>" if u_approved else f"<span class='badge-suspended'>🔴 {status_text}</span>"
        try: display_badge = types_display[types_internal.index(u_type)]
        except: display_badge = u_type
        r_badge = _m("badge_admin") if u_role == 'admin' else display_badge
        b_color = "role-admin" if u_role == 'admin' else "role-user"
        disp_phone = u_phone if u_phone else _m("not_spec")

        # ÜST BAŞLIK VE İSTATİSTİKLER
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; color:#0f172a; font-weight:900;">{u_company}</h2>
                {badge_html}
            </div>
            <div style="font-size:15px; color:#64748b; margin-top:5px;">
                <span class="{b_color}">{r_badge}</span> &nbsp;|&nbsp; 📧 {u_email} &nbsp;|&nbsp; 📞 {disp_phone}
            </div>
            <div class='stats-bar'>
                <div class='stat-box'><div class='stat-lbl'>{_m('tot_offer')}</div><div class='stat-val'>{t_count}</div></div>
                <div class='stat-box'><div class='stat-lbl'>{_m('tot_vol')}</div><div class='stat-val blue'>{t_vol:,.0f}</div></div>
                <div class='stat-box'><div class='stat-lbl'>{_m('conv_offer')}</div><div class='stat-val'>{c_count}</div></div>
                <div class='stat-box'><div class='stat-lbl'>{_m('conv_vol')}</div><div class='stat-val green'>{c_vol:,.0f}</div></div>
            </div>
        """, unsafe_allow_html=True)

        # BİLGİLERİ DÜZENLE FORMU
        with st.container(border=True):
            st.markdown(f"<h4 style='margin-top:0; color:#1e293b;'>{_m('edit_auth')}</h4>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            n_comp = c1.text_input(_m("comp_name"), value=u_company)
            idx_type = types_internal.index(u_type) if u_type in types_internal else 0
            sel_type = c2.selectbox(_m("act_type"), types_display, index=idx_type)
            n_type_int = types_internal[types_display.index(sel_type)]
            
            n_email = c1.text_input(_m("email"), value=u_email)
            n_phone = c2.text_input(_m("phone"), value=u_phone if u_phone else "")

            n_cats_str = ""
            if n_type_int == "Satıcı (Bayi)":
                st.markdown("<hr style='margin:15px 0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:13px; font-weight:800; color:#ea580c; margin-bottom:5px;'>{_m('cat_title')}</div>", unsafe_allow_html=True)
                cur_cats = [x.strip() for x in str(u_allowed_cats).split(",")] if u_allowed_cats else all_categories
                sel_cats = st.multiselect(_m("cat_help"), options=all_categories, default=[c for c in cur_cats if c in all_categories])
                n_cats_str = ",".join(sel_cats)
            
            st.markdown("<hr style='margin:15px 0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:13px; font-weight:800; color:#0f172a; margin-bottom:10px;'>{_m('menu_title')}</div>", unsafe_allow_html=True)
            menu_options = {"m_dash": _m("m_dash"), "m_new": _m("m_new"), "m_cust": _m("m_cust"), "m_past": _m("m_past"), "m_order": _m("m_order"), "m_model": _m("m_model"), "m_deal": _m("m_deal"), "m_prof": _m("m_prof")}
            cur_menus = u_menus.split(',') if u_menus is not None else list(menu_options.keys())
            
            sel_menus = []
            m_cols = st.columns(4)
            for idx, (k, v) in enumerate(menu_options.items()):
                with m_cols[idx % 4]:
                    if st.checkbox(v, value=(k in cur_menus), key=f"chk_{k}"): sel_menus.append(k)
            
            n_menus_str = ",".join(sel_menus)
            n_role = "admin" if n_type_int == "Yönetici" else ("manufacturer" if n_type_int == "Üretici" else "dealer")
            
            st.write("")
            col_space, col_save = st.columns([3, 2])
            if col_save.button(_m("btn_update"), type="primary", use_container_width=True):
                conn_u = sqlite3.connect('users.db')
                conn_u.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", (n_comp, n_type_int, n_email, n_phone, n_menus_str, n_role, n_cats_str, u_id))
                conn_u.commit(); conn_u.close()
                st.toast(f"{n_comp} {_m('toast_upd')}"); st.rerun()

        # HESAP AKSİYONLARI (ASKIYA AL / SİL)
        st.write("")
        if u_id == st.session_state.get('user_id'):
            st.info(_m("err_self"))
        else:
            ca1, ca2, ca3 = st.columns([2, 1, 1])
            with ca2:
                if u_approved:
                    if st.button(_m("btn_sus"), use_container_width=True):
                        conn_a = sqlite3.connect('users.db'); conn_a.execute("UPDATE users SET is_approved=0 WHERE id=?", (u_id,)); conn_a.commit(); conn_a.close(); st.rerun()
                else:
                    if st.button(_m("btn_app"), type="primary", use_container_width=True):
                        conn_a = sqlite3.connect('users.db'); conn_a.execute("UPDATE users SET is_approved=1 WHERE id=?", (u_id,)); conn_a.commit(); conn_a.close(); st.rerun()
            with ca3:
                if st.button(_m("btn_del"), use_container_width=True):
                    conn_a = sqlite3.connect('users.db'); conn_a.execute("DELETE FROM users WHERE id=?", (u_id,)); conn_a.commit(); conn_a.close()
                    st.session_state.manage_dealer_id = None; st.rerun()

    # =========================================================
    # GÖRÜNÜM 1: LİSTE SAYFASI (1 SAYFADA 10 BAYİ)
    # =========================================================
    else:
        st.header(_m("title"))
        search_query = st.text_input(_m("search_ph"))
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        
        if not users: st.info(_m("no_user")); return
            
        if search_query:
            search_query = search_query.lower()
            users = [u for u in users if search_query in str(u[1]).lower() or search_query in str(u[2]).lower() or search_query in str(u[3]).lower()]
            if not users: st.warning(_m("no_match")); return

        # SAYFALAMA (PAGINATION) MANTIĞI
        ITEMS_PER_PAGE = 10
        total_pages = math.ceil(len(users) / ITEMS_PER_PAGE)
        
        if st.session_state.dealer_page > total_pages: st.session_state.dealer_page = total_pages
        if st.session_state.dealer_page < 1: st.session_state.dealer_page = 1
            
        start_idx = (st.session_state.dealer_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        current_users = users[start_idx:end_idx]

        # LİSTE BAŞLIKLARI
        cl1, cl2, cl3, cl4 = st.columns([3, 3, 2, 2])
        cl1.caption("FİRMA BİLGİSİ"); cl2.caption("İLETİŞİM"); cl3.caption("DURUM"); cl4.caption("İŞLEM")
        st.markdown("<hr style='margin:0 0 10px 0; border-top:2px solid #e2e8f0;'>", unsafe_allow_html=True)

        # LİSTE SATIRLARI
        for u in current_users:
            u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role, u_allowed_cats = u
            
            try: display_badge = types_display[types_internal.index(u_type)]
            except: display_badge = u_type
            r_badge = _m("badge_admin") if u_role == 'admin' else display_badge
            b_color = "role-admin" if u_role == 'admin' else "role-user"
            
            s_text = _m("active") if u_approved else _m("pending")
            b_html = f"<span class='badge-active'>🟢 {s_text}</span>" if u_approved else f"<span class='badge-suspended'>🔴 {s_text}</span>"

            with st.container():
                c1, c2, c3, c4 = st.columns([3, 3, 2, 2], vertical_alignment="center")
                c1.markdown(f"<div class='list-col'><b style='color:#0f172a; font-size:15px;'>{u_company}</b><span class='{b_color}'>{r_badge}</span></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='list-col' style='font-size:13px; color:#475569;'>{u_email}<br>{u_phone if u_phone else '-'}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='list-col'>{b_html}</div>", unsafe_allow_html=True)
                if c4.button(_m("btn_manage"), key=f"manage_{u_id}", use_container_width=True):
                    st.session_state.manage_dealer_id = u_id
                    st.rerun()
                st.markdown("<hr style='margin:5px 0; border-top:1px solid #f1f5f9;'>", unsafe_allow_html=True)

        # SAYFALAMA KONTROLLERİ (ALT KISIM)
        if total_pages > 1:
            st.write("")
            cp1, cp2, cp3 = st.columns([1, 2, 1])
            with cp2:
                page_opts = [i for i in range(1, total_pages + 1)]
                new_page = st.selectbox(f"{_m('page')} Seçimi (Toplam: {total_pages})", options=page_opts, index=(st.session_state.dealer_page - 1), label_visibility="collapsed")
                if new_page != st.session_state.dealer_page:
                    st.session_state.dealer_page = new_page
                    st.rerun()
