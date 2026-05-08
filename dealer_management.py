import streamlit as st
import sqlite3
import pandas as pd

# =====================================================================
# 🌍 ÇOKLU DİL SÖZLÜĞÜ (TR - EN - ZH)
# =====================================================================
DICT_DEALER = {
    "tr": {
        "title": "🏢 Bayi ve Üretici Yönetimi",
        "search_ph": "🔍 Kullanıcı Ara (Firma Adı, E-Posta veya Telefon ile)",
        "no_user": "Sistemde henüz kayıtlı kullanıcı bulunmuyor.",
        "no_match": "Arama kriterinize uygun kullanıcı bulunamadı.",
        "active": "Aktif", "pending": "Askıda",
        "badge_admin": "👑 YÖNETİCİ", "not_spec": "Belirtilmemiş",
        "tot_offer": "Top. Teklif", "tot_vol": "Top. Hacim",
        "conv_offer": "Siparişler", "conv_vol": "Sip. Hacmi",
        "edit_auth": "✏️ Düzenle / Yetki Ver",
        "comp_name": "Firma Adı", "act_type": "Faaliyet Türü",
        "email": "E-Posta Adresi", "phone": "Telefon",
        "type_dealer": "Satıcı (Bayi)", "type_prod": "Üretici", "type_admin": "Yönetici",
        "cat_title": "📦 Kategoriler (Filtre):",
        "cat_help": "Satış izni verilen kategoriler:",
        "cat_warn": "💡 Sadece Satıcı (Bayi) için geçerlidir.",
        "menu_title": "🔑 Menü İzinleri:",
        "btn_update": "💾 GÜNCELLE",
        "toast_upd": "yetkileri güncellendi!",
        "err_self": "Kendi hesabınızı silemezsiniz.",
        "btn_sus": "🚫 Askıya Al", "btn_app": "✅ Onayla", "btn_del": "🗑️ Sil",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif", "m_cust": "👥 Müşteriler",
        "m_past": "📋 Geçmiş Teklifler", "m_order": "📦 Siparişler", "m_model": "📦 Modeller",
        "m_deal": "🏢 Bayiler", "m_prof": "⚙️ Ayarlar"
    },
    "en": {
        "title": "🏢 Dealer and Manufacturer Management",
        "search_ph": "🔍 Search User (by Company, Email or Phone)",
        "no_user": "No registered users found in the system.",
        "no_match": "No users match your search criteria.",
        "active": "Active", "pending": "Suspended",
        "badge_admin": "👑 ADMIN", "not_spec": "Not Specified",
        "tot_offer": "Total Off.", "tot_vol": "Tot. Vol",
        "conv_offer": "Orders", "conv_vol": "Ord. Vol",
        "edit_auth": "✏️ Edit Info & Auth",
        "comp_name": "Company Name", "act_type": "Role",
        "email": "Email Address", "phone": "Phone",
        "type_dealer": "Dealer", "type_prod": "Producer", "type_admin": "Admin",
        "cat_title": "📦 Allowed Categories:",
        "cat_help": "Select allowed categories:",
        "cat_warn": "💡 Applies ONLY to Dealers.",
        "menu_title": "🔑 Menu Access:",
        "btn_update": "💾 UPDATE",
        "toast_upd": "permissions updated!",
        "err_self": "You cannot delete your own account.",
        "btn_sus": "🚫 Suspend", "btn_app": "✅ Approve", "btn_del": "🗑️ Delete",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 New Offer", "m_cust": "👥 Customers",
        "m_past": "📋 Past Offers", "m_order": "📦 Orders", "m_model": "📦 Models",
        "m_deal": "🏢 Dealers", "m_prof": "⚙️ Settings"
    },
    "zh": {
        "title": "🏢 经销商和制造商管理",
        "search_ph": "🔍 搜索用户 (按公司、电子邮件或电话)",
        "no_user": "系统中尚未找到注册用户。",
        "no_match": "未找到符合搜索条件的用户。",
        "active": "活跃", "pending": "暂停",
        "badge_admin": "👑 管理员", "not_spec": "未指定",
        "tot_offer": "总报价", "tot_vol": "总交易量",
        "conv_offer": "订单", "conv_vol": "订单量",
        "edit_auth": "✏️ 编辑权限",
        "comp_name": "公司名称", "act_type": "角色",
        "email": "电子邮件", "phone": "电话",
        "type_dealer": "经销商", "type_prod": "制造商", "type_admin": "管理员",
        "cat_title": "📦 允许的类别:",
        "cat_help": "选择允许销售的类别:",
        "cat_warn": "💡 仅适用于经销商。",
        "menu_title": "🔑 菜单访问:",
        "btn_update": "💾 更新",
        "toast_upd": "权限已更新！",
        "err_self": "您不能删除自己的帐户。",
        "btn_sus": "🚫 暂停", "btn_app": "✅ 批准", "btn_del": "🗑️ 删除",
        
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
# VERİTABANI GÜVENLİ ONARIM
# =====================================================================
def repair_users_db():
    try:
        conn = sqlite3.connect('users.db')
        try: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Dealer'")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
        except: pass
        conn.commit()
        conn.close()
    except: pass

repair_users_db()

# =====================================================================
# ANA SAYFA GÖRÜNÜMÜ (KOMPAKT GRID TASARIM)
# =====================================================================
def show_dealer_management():
    # 🎨 KOMPAKT VE DAR BEYAZ CSS KODLARI 🎨
    st.markdown("""
    <style>
    .stats-bar {
        background-color: #ffffff; 
        border-radius: 8px; 
        display: flex; 
        padding: 10px 0; 
        margin: 10px 0;
        border: 1px solid #f1f5f9;
        box-shadow: 0 2px 4px -1px rgba(0,0,0,0.05);
    }
    .stat-box {
        flex: 1; 
        text-align: center; 
        border-right: 1px solid #f1f5f9;
    }
    .stat-box:last-child {
        border-right: none;
    }
    .stat-lbl {
        font-size: 9px; 
        font-weight: 800; 
        color: #94a3b8; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .stat-val {
        font-size: 16px; 
        font-weight: 900; 
        color: #1e293b;
    }
    .stat-val.blue { color: #3b82f6; }
    .stat-val.green { color: #10b981; }
    
    div[data-baseweb="input"] > div {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    .badge-active {
        background:#ecfdf5; color:#10b981; padding:3px 10px; 
        border-radius:20px; font-size:11px; font-weight:800; border:1px solid #a7f3d0;
    }
    .badge-suspended {
        background:#fef2f2; color:#ef4444; padding:3px 10px; 
        border-radius:20px; font-size:11px; font-weight:800; border:1px solid #fecaca;
    }
    .compact-title {
        margin:0; color:#0f172a; font-weight:900; font-size: 16px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    </style>
    """, unsafe_allow_html=True)

    st.header(_m("title"))
    
    search_query = st.text_input(_m("search_ph"), placeholder=_m("search_ph"))
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    
    # --- VERİLERİ ÇEK ---
    try:
        conn_fact = sqlite3.connect('factory_data.db')
        all_categories = [c[0] for c in conn_fact.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()]
        conn_fact.close()
    except: all_categories = []

    conn = sqlite3.connect('users.db')
    try: users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role, allowed_categories FROM users ORDER BY id DESC").fetchall()
    except: users = [(*u, "") for u in conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role FROM users ORDER BY id DESC").fetchall()]
    conn.close()
    
    conn_s = sqlite3.connect('sales_data.db')
    try: all_offers = conn_s.execute("SELECT user_id, status, total_price FROM offers").fetchall()
    except: all_offers = []
    conn_s.close()
    
    df_offers = pd.DataFrame(all_offers, columns=['user_id', 'status', 'total_price']) if all_offers else pd.DataFrame(columns=['user_id', 'status', 'total_price'])
    
    if not users:
        st.info(_m("no_user")); return
        
    if search_query:
        search_query = search_query.lower()
        users = [u for u in users if search_query in str(u[1]).lower() or search_query in str(u[2]).lower() or search_query in str(u[3]).lower()]
        if not users:
            st.warning(_m("no_match")); return

    types_internal = ["Satıcı (Bayi)", "Üretici", "Yönetici"]
    types_display = [_m("type_dealer"), _m("type_prod"), _m("type_admin")]

    # =========================================================
    # GRID YAPISI BAŞLIYOR (2 KOLONLU DİZİLİM)
    # =========================================================
    for i in range(0, len(users), 2):
        cols = st.columns(2) # 2'li Grid Kolonları
        
        for j in range(2):
            if i + j < len(users):
                u = users[i + j]
                u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role, u_allowed_cats = u
                
                # İstatistik Hesaplama
                dealer_offers = df_offers[df_offers['user_id'] == u_id] if not df_offers.empty else pd.DataFrame()
                t_count = len(dealer_offers)
                t_vol = dealer_offers['total_price'].sum() if t_count > 0 else 0
                
                conv_offers = dealer_offers[dealer_offers['status'].isin(["Onaylandı", "Siparişe Çevir"])] if t_count > 0 else pd.DataFrame()
                c_count = len(conv_offers)
                c_vol = conv_offers['total_price'].sum() if c_count > 0 else 0
                
                # Her bayi kendi yarım-kolonluk kartının içinde çiziliyor
                with cols[j].container(border=True):
                    status_text = _m("active") if u_approved else _m("pending")
                    badge_html = f"<span class='badge-active'>🟢 {status_text}</span>" if u_approved else f"<span class='badge-suspended'>🔴 {status_text}</span>"
                    
                    try: display_badge = types_display[types_internal.index(u_type)]
                    except: display_badge = u_type
                        
                    role_badge = _m("badge_admin") if u_role == 'admin' else display_badge
                    badge_color = "#ea580c" if u_role == 'admin' else "#3b82f6"
                    disp_phone = u_phone if u_phone else _m("not_spec")
                    
                    st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 class="compact-title" title="{u_company}">{u_company}</h3>
                            {badge_html}
                        </div>
                        <div style="font-size:12px; color:#64748b; margin-top:4px; font-weight:500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            <b style="color:{badge_color};">{role_badge}</b> | 📧 {u_email} <br> 📞 {disp_phone}
                        </div>
                        
                        <div class='stats-bar'>
                            <div class='stat-box'>
                                <div class='stat-lbl'>{_m('tot_offer')}</div>
                                <div class='stat-val'>{t_count}</div>
                            </div>
                            <div class='stat-box'>
                                <div class='stat-lbl'>{_m('tot_vol')}</div>
                                <div class='stat-val blue'>{t_vol:,.0f}</div>
                            </div>
                            <div class='stat-box'>
                                <div class='stat-lbl'>{_m('conv_offer')}</div>
                                <div class='stat-val'>{c_count}</div>
                            </div>
                            <div class='stat-box'>
                                <div class='stat-lbl'>{_m('conv_vol')}</div>
                                <div class='stat-val green'>{c_vol:,.0f}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # --- DÜZENLEME ALANI ---
                    with st.expander(_m("edit_auth"), expanded=False):
                        # Dar alanda olduğumuz için inputs alt alta daha iyi durabilir, 
                        # ama c1, c2 ile yan yana da şık durur.
                        c1, c2 = st.columns(2)
                        new_company = c1.text_input(_m("comp_name"), value=u_company, key=f"inp_cmp_{u_id}")
                        idx_type = types_internal.index(u_type) if u_type in types_internal else 0
                        sel_type_disp = c2.selectbox(_m("act_type"), types_display, index=idx_type, key=f"inp_typ_{u_id}")
                        new_type_internal = types_internal[types_display.index(sel_type_disp)]
                        
                        new_email = c1.text_input(_m("email"), value=u_email, key=f"inp_eml_{u_id}")
                        new_phone = c2.text_input(_m("phone"), value=u_phone if u_phone else "", key=f"inp_phn_{u_id}")

                        new_cats_str = ""
                        if new_type_internal == "Satıcı (Bayi)":
                            st.markdown(f"<div style='font-size:12px; font-weight:800; color:#ea580c; margin-top:5px;'>{_m('cat_title')}</div>", unsafe_allow_html=True)
                            current_cats = [x.strip() for x in str(u_allowed_cats).split(",")] if u_allowed_cats else all_categories
                            selected_cats = st.multiselect("Kategoriler", options=all_categories, default=[c for c in current_cats if c in all_categories], key=f"inp_cat_{u_id}", label_visibility="collapsed")
                            new_cats_str = ",".join(selected_cats)
                        
                        st.markdown(f"<div style='font-size:12px; font-weight:800; color:#0f172a; margin-top:10px; margin-bottom:5px;'>{_m('menu_title')}</div>", unsafe_allow_html=True)
                        menu_options = {"m_dash": _m("m_dash"), "m_new": _m("m_new"), "m_cust": _m("m_cust"), "m_past": _m("m_past"), "m_order": _m("m_order"), "m_model": _m("m_model"), "m_deal": _m("m_deal"), "m_prof": _m("m_prof")}
                        current_menus = u_menus.split(',') if u_menus is not None else list(menu_options.keys())
                        
                        selected_menus = []
                        m_cols = st.columns(2) # Dar alanda 2 kolon daha iyi
                        for idx, (k, v) in enumerate(menu_options.items()):
                            with m_cols[idx % 2]:
                                if st.checkbox(v, value=(k in current_menus), key=f"chk_{u_id}_{k}"):
                                    selected_menus.append(k)
                        
                        new_menus_str = ",".join(selected_menus)
                        new_role = "admin" if new_type_internal == "Yönetici" else ("manufacturer" if new_type_internal == "Üretici" else "dealer")
                        
                        st.write("")
                        if st.button(_m("btn_update"), type="primary", use_container_width=True, key=f"btn_save_user_{u_id}"):
                            conn_update = sqlite3.connect('users.db')
                            try: conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", (new_company, new_type_internal, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                            except:
                                try: conn_update.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
                                except: pass
                                conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", (new_company, new_type_internal, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                            conn_update.commit(); conn_update.close()
                            st.toast(f"{new_company} {_m('toast_upd')}"); st.rerun()

                    # --- AKSİYON BUTONLARI ---
                    st.write("")
                    if u_id == st.session_state.get('user_id'):
                        st.info(_m("err_self"))
                    else:
                        c_act1, c_act2 = st.columns(2)
                        with c_act1:
                            if u_approved:
                                if st.button(_m("btn_sus"), key=f"sus_{u_id}", use_container_width=True):
                                    conn_act = sqlite3.connect('users.db'); conn_act.execute("UPDATE users SET is_approved=0 WHERE id=?", (u_id,)); conn_act.commit(); conn_act.close(); st.rerun()
                            else:
                                if st.button(_m("btn_app"), key=f"app_{u_id}", type="primary", use_container_width=True):
                                    conn_act = sqlite3.connect('users.db'); conn_act.execute("UPDATE users SET is_approved=1 WHERE id=?", (u_id,)); conn_act.commit(); conn_act.close(); st.rerun()
                        with c_act2:
                            if st.button(_m("btn_del"), key=f"del_{u_id}", use_container_width=True):
                                conn_act = sqlite3.connect('users.db'); conn_act.execute("DELETE FROM users WHERE id=?", (u_id,)); conn_act.commit(); conn_act.close(); st.rerun()
