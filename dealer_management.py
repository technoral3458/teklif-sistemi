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
        "active": "Aktif", "pending": "Askıda / Onay Bekliyor",
        "badge_admin": "👑 YÖNETİCİ", "not_spec": "Belirtilmemiş",
        "tot_offer": "Toplam Teklif", "tot_vol": "Toplam Hacim",
        "conv_offer": "Siparişe Dönen", "conv_vol": "Sipariş Hacmi",
        "edit_auth": "✏️ Bilgileri Düzenle ve Yetkileri Yönet",
        "comp_name": "Firma Adı", "act_type": "Faaliyet Türü / Yetki",
        "email": "E-Posta Adresi", "phone": "Telefon",
        "type_dealer": "Satıcı (Bayi)", "type_prod": "Üretici", "type_admin": "Yönetici",
        "cat_title": "📦 Satıcının Teklif Verebileceği Kategoriler (Filtre):",
        "cat_help": "Satış yapmasına izin verilen makine kategorilerini seçin:",
        "cat_warn": "💡 SADECE Satıcı (Bayi) rolü için geçerlidir.",
        "menu_title": "🔑 Kullanıcının Görüntüleyebileceği Sayfa Menüleri:",
        "btn_update": "🔄 BİLGİLERİ VE YETKİLERİ GÜNCELLE",
        "toast_upd": "yetkileri güncellendi!",
        "err_self": "💡 Kendi yönetici hesabınızı askıya alamaz veya silemezsiniz.",
        "btn_sus": "🚫 Hesabı Askıya Al", "btn_app": "✅ Hesabı Onayla / Aktifleştir", "btn_del": "🗑️ Tamamen Sil",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Yeni Teklif Hazırla", "m_cust": "👥 Müşterilerim",
        "m_past": "📋 Geçmiş Tekliflerim", "m_order": "📦 Siparişler", "m_model": "📦 Tüm Modelleri Yönet",
        "m_deal": "🏢 Bayi / Kullanıcı Yönetimi", "m_prof": "⚙️ Profil Ayarlarım"
    },
    "en": {
        "title": "🏢 Dealer and Manufacturer Management",
        "search_ph": "🔍 Search User (by Company, Email or Phone)",
        "no_user": "No registered users found in the system.",
        "no_match": "No users match your search criteria.",
        "active": "Active", "pending": "Suspended / Pending",
        "badge_admin": "👑 ADMIN", "not_spec": "Not Specified",
        "tot_offer": "Total Offers", "tot_vol": "Total Volume",
        "conv_offer": "Converted to Order", "conv_vol": "Order Volume",
        "edit_auth": "✏️ Edit Info & Manage Permissions",
        "comp_name": "Company Name", "act_type": "Activity Type / Role",
        "email": "Email Address", "phone": "Phone",
        "type_dealer": "Dealer", "type_prod": "Producer", "type_admin": "Admin",
        "cat_title": "📦 Allowed Categories for Dealer (Filter):",
        "cat_help": "Select allowed machine categories for sales:",
        "cat_warn": "💡 Applies ONLY to Dealers.",
        "menu_title": "🔑 Accessible Page Menus for User:",
        "btn_update": "🔄 UPDATE INFO & PERMISSIONS",
        "toast_upd": "permissions updated!",
        "err_self": "💡 You cannot suspend or delete your own admin account.",
        "btn_sus": "🚫 Suspend Account", "btn_app": "✅ Approve / Activate Account", "btn_del": "🗑️ Delete Completely",
        
        "m_dash": "📊 Dashboard", "m_new": "📝 Create New Offer", "m_cust": "👥 My Customers",
        "m_past": "📋 My Past Offers", "m_order": "📦 Orders", "m_model": "📦 Manage All Models",
        "m_deal": "🏢 Dealer / User Management", "m_prof": "⚙️ Profile Settings"
    },
    "zh": {
        "title": "🏢 经销商和制造商管理",
        "search_ph": "🔍 搜索用户 (按公司、电子邮件或电话)",
        "no_user": "系统中尚未找到注册用户。",
        "no_match": "未找到符合搜索条件的用户。",
        "active": "活跃", "pending": "暂停 / 待批准",
        "badge_admin": "👑 管理员", "not_spec": "未指定",
        "tot_offer": "总报价", "tot_vol": "总交易量",
        "conv_offer": "已转为订单", "conv_vol": "订单量",
        "edit_auth": "✏️ 编辑信息和管理权限",
        "comp_name": "公司名称", "act_type": "活动类型/角色",
        "email": "电子邮件", "phone": "电话",
        "type_dealer": "经销商", "type_prod": "制造商", "type_admin": "管理员",
        "cat_title": "📦 经销商允许的类别 (过滤器):",
        "cat_help": "选择允许销售的机器类别:",
        "cat_warn": "💡 仅适用于经销商。",
        "menu_title": "🔑 用户可访问的页面菜单:",
        "btn_update": "🔄 更新信息和权限",
        "toast_upd": "权限已更新！",
        "err_self": "💡 您不能暂停或删除自己的管理员帐户。",
        "btn_sus": "🚫 暂停帐户", "btn_app": "✅ 批准/激活帐户", "btn_del": "🗑️ 完全删除",
        
        "m_dash": "📊 仪表板", "m_new": "📝 创建新报价", "m_cust": "👥 我的客户",
        "m_past": "📋 我的历史报价", "m_order": "📦 订单", "m_model": "📦 管理所有型号",
        "m_deal": "🏢 经销商/用户管理", "m_prof": "⚙️ 配置文件设置"
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
        cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "role" not in cols: conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Dealer'")
        if "allowed_categories" not in cols: conn.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
        conn.commit()
        conn.close()
    except: pass

repair_users_db()

# =====================================================================
# ANA SAYFA GÖRÜNÜMÜ
# =====================================================================
def show_dealer_management():
    st.header(_m("title"))
    
    search_query = st.text_input(_m("search_ph"), placeholder=_m("search_ph"))
    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
    
    try:
        conn_fact = sqlite3.connect('factory_data.db')
        c_cats = conn_fact.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()
        all_categories = [c[0] for c in c_cats]
        conn_fact.close()
    except Exception as e:
        all_categories = []

    conn = sqlite3.connect('users.db')
    try:
        users = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role, allowed_categories FROM users ORDER BY id DESC").fetchall()
    except:
        users_old = conn.execute("SELECT id, company_name, email, phone, user_type, is_approved, allowed_menus, role FROM users ORDER BY id DESC").fetchall()
        users = [(*u, "") for u in users_old]
    conn.close()
    
    conn_s = sqlite3.connect('sales_data.db')
    try:
        all_offers = conn_s.execute("SELECT user_id, status, total_price FROM offers").fetchall()
    except:
        all_offers = []
    conn_s.close()
    
    df_offers = pd.DataFrame(all_offers, columns=['user_id', 'status', 'total_price']) if all_offers else pd.DataFrame(columns=['user_id', 'status', 'total_price'])
    
    if not users:
        st.info(_m("no_user"))
        return
        
    if search_query:
        search_query = search_query.lower()
        users = [u for u in users if search_query in str(u[1]).lower() or search_query in str(u[2]).lower() or search_query in str(u[3]).lower()]
        if not users:
            st.warning(_m("no_match"))
            return

    types_internal = ["Satıcı (Bayi)", "Üretici", "Yönetici"]
    types_display = [_m("type_dealer"), _m("type_prod"), _m("type_admin")]

    for u in users:
        u_id, u_company, u_email, u_phone, u_type, u_approved, u_menus, u_role, u_allowed_cats = u
        
        dealer_offers = df_offers[df_offers['user_id'] == u_id] if not df_offers.empty else pd.DataFrame()
        t_count = len(dealer_offers)
        t_vol = dealer_offers['total_price'].sum() if t_count > 0 else 0
        
        conv_offers = dealer_offers[dealer_offers['status'].isin(["Onaylandı", "Siparişe Çevir"])] if t_count > 0 else pd.DataFrame()
        c_count = len(conv_offers)
        c_vol = conv_offers['total_price'].sum() if c_count > 0 else 0
        
        with st.container(border=True):
            status_color = "#10b981" if u_approved else "#ef4444"
            status_text = _m("active") if u_approved else _m("pending")
            
            try: display_badge = types_display[types_internal.index(u_type)]
            except: display_badge = u_type
                
            role_badge = _m("badge_admin") if u_role == 'admin' else display_badge
            badge_color = "#ea580c" if u_role == 'admin' else "#2563eb"
            disp_phone = u_phone if u_phone else _m("not_spec")
            
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#0f172a;">{u_company}</h3>
                    <span style="background-color:{status_color}15; color:{status_color}; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:800; border:1px solid {status_color}50;">{status_text}</span>
                </div>
                <div style="font-size:14px; color:#64748b; margin-top:5px; margin-bottom:15px;">
                    <b style="color:{badge_color};">{role_badge}</b> | 📧 {u_email} | 📞 {disp_phone}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <div style="flex:1; background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; text-align:center;">
                        <div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">{_m('tot_offer')}</div>
                        <div style="font-size:18px; color:#0f172a; font-weight:900;">{t_count}</div>
                    </div>
                    <div style="flex:1; background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; text-align:center;">
                        <div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">{_m('tot_vol')}</div>
                        <div style="font-size:18px; color:#3b82f6; font-weight:900;">{t_vol:,.0f}</div>
                    </div>
                    <div style="flex:1; background:#ecfdf5; padding:10px; border-radius:8px; border:1px solid #a7f3d0; text-align:center;">
                        <div style="font-size:11px; color:#059669; font-weight:700; text-transform:uppercase;">{_m('conv_offer')}</div>
                        <div style="font-size:18px; color:#10b981; font-weight:900;">{c_count}</div>
                    </div>
                    <div style="flex:1; background:#ecfdf5; padding:10px; border-radius:8px; border:1px solid #a7f3d0; text-align:center;">
                        <div style="font-size:11px; color:#059669; font-weight:700; text-transform:uppercase;">{_m('conv_vol')}</div>
                        <div style="font-size:18px; color:#10b981; font-weight:900;">{c_vol:,.0f}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # 🚀 ST.FORM KALDIRILDI! ARTIK ANINDA TEPKİ VERECEK 🚀
            with st.expander(_m("edit_auth"), expanded=False):
                c1, c2 = st.columns(2)
                new_company = c1.text_input(_m("comp_name"), value=u_company, key=f"inp_cmp_{u_id}")
                
                idx_type = types_internal.index(u_type) if u_type in types_internal else 0
                sel_type_disp = c2.selectbox(_m("act_type"), types_display, index=idx_type, key=f"inp_typ_{u_id}")
                new_type_internal = types_internal[types_display.index(sel_type_disp)]
                
                new_email = c1.text_input(_m("email"), value=u_email, key=f"inp_eml_{u_id}")
                new_phone = c2.text_input(_m("phone"), value=u_phone if u_phone else "", key=f"inp_phn_{u_id}")

                new_cats_str = ""
                # Eğer "Satıcı (Bayi)" seçiliyse menü ANINDA aşağı düşer!
                if new_type_internal == "Satıcı (Bayi)":
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:13px; font-weight:800; color:#ea580c; margin-bottom:5px;'>{_m('cat_title')}</div>", unsafe_allow_html=True)
                    st.caption(_m("cat_warn"))
                    
                    current_cats = [x.strip() for x in str(u_allowed_cats).split(",")] if u_allowed_cats else all_categories
                    safe_defaults = [c for c in current_cats if c in all_categories]
                    
                    selected_cats = st.multiselect(
                        _m("cat_help"), 
                        options=all_categories,
                        default=safe_defaults,
                        key=f"inp_cat_{u_id}"
                    )
                    new_cats_str = ",".join(selected_cats)
                
                st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:13px; font-weight:800; color:#0f172a; margin-bottom:10px;'>{_m('menu_title')}</div>", unsafe_allow_html=True)
                
                menu_options = {
                    "m_dash": _m("m_dash"), "m_new": _m("m_new"), "m_cust": _m("m_cust"),
                    "m_past": _m("m_past"), "m_order": _m("m_order"), "m_model": _m("m_model"),
                    "m_deal": _m("m_deal"), "m_prof": _m("m_prof")
                }
                current_menus = u_menus.split(',') if u_menus is not None else list(menu_options.keys())
                
                selected_menus = []
                m_cols = st.columns(3)
                for idx, (k, v) in enumerate(menu_options.items()):
                    with m_cols[idx % 3]:
                        if st.checkbox(v, value=(k in current_menus), key=f"chk_{u_id}_{k}"):
                            selected_menus.append(k)
                
                new_menus_str = ",".join(selected_menus)
                new_role = "admin" if new_type_internal == "Yönetici" else ("manufacturer" if new_type_internal == "Üretici" else "dealer")
                
                st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
                
                # Buton artık Form'a değil, direkt sayfaya bağlı çalışır
                if st.button(_m("btn_update"), type="primary", use_container_width=True, key=f"btn_save_user_{u_id}"):
                    conn_update = sqlite3.connect('users.db')
                    try:
                        conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", 
                                            (new_company, new_type_internal, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                    except:
                        conn_update.execute("ALTER TABLE users ADD COLUMN allowed_categories TEXT DEFAULT ''")
                        conn_update.execute("UPDATE users SET company_name=?, user_type=?, email=?, phone=?, allowed_menus=?, role=?, allowed_categories=? WHERE id=?", 
                                            (new_company, new_type_internal, new_email, new_phone, new_menus_str, new_role, new_cats_str, u_id))
                        
                    conn_update.commit(); conn_update.close()
                    st.toast(f"{new_company} {_m('toast_upd')}")
                    st.rerun()
                        
            st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            
            if u_id == st.session_state.get('user_id'):
                st.info(_m("err_self"))
            else:
                if u_approved:
                    if c3.button(_m("btn_sus"), key=f"sus_{u_id}", use_container_width=True):
                        conn_act = sqlite3.connect('users.db')
                        conn_act.execute("UPDATE users SET is_approved=0 WHERE id=?", (u_id,))
                        conn_act.commit(); conn_act.close()
                        st.rerun()
                else:
                    if c3.button(_m("btn_app"), key=f"app_{u_id}", use_container_width=True):
                        conn_act = sqlite3.connect('users.db')
                        conn_act.execute("UPDATE users SET is_approved=1 WHERE id=?", (u_id,))
                        conn_act.commit(); conn_act.close()
                        st.rerun()
                        
                if c4.button(_m("btn_del"), key=f"del_{u_id}", use_container_width=True):
                    conn_act = sqlite3.connect('users.db')
                    conn_act.execute("DELETE FROM users WHERE id=?", (u_id,))
                    conn_act.commit(); conn_act.close()
                    st.rerun()
