import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image
import json

# =====================================================================
# 🛡️ GÜVENLİ VERİ OKUMA ZIRHI
# =====================================================================
def get_safe(row, index, default=""):
    """Eksik sütunlarda sistemin patlamasını (IndexError) engelleyen zırh"""
    if row and isinstance(row, (list, tuple)) and len(row) > index:
        return row[index] if row[index] is not None else default
    return default

# =====================================================================
# 🌍 ÇOKLU DİL SÖZLÜĞÜ (TR - EN - ZH)
# =====================================================================
DICT_MODEL = {
    "tr": {
        "m_title": "📦 Fabrika Veritabanı Yönetimi",
        "t_mod": "📦 Modeller (Vitrin)", "t_opt": "⚙️ Ekstra Donanımlar", "t_cat": "📂 Kategoriler",
        "reg_mach": "Kayıtlı Makineler", "add_mach": "➕ YENİ MAKİNE EKLE",
        "no_img": "Görsel Yok", "price_wait": "Fiyat Bekleniyor", "no_auth_price": "🔒 Fiyat Gizli",
        "btn_edit": "✏️", "btn_copy": "📄", "btn_del": "🗑️",
        "opt_showcase": "Ekstra Donanımlar Vitrini", "add_opt": "➕ YENİ DONANIM EKLE",
        "no_opt": "Sistemde henüz donanım yok.", "no_mach": "Sistemde makine yok.",
        "cat_mng": "📂 Kategori Yönetimi", "new_cat": "Kategori Ekle", "btn_add": "➕ Ekle",
        "back_list": "🔙 Listeye Dön", "edit_mach": "✏️ Makine Düzenleyici", "new_mach": "✨ Makine Oluştur",
        "tab_gen": "📄 Genel", "tab_tech": "⚙️ Teknik", "tab_comp": "🔌 Donanımlar",
        "m_name": "Makine Adı *", "m_cat": "Kategori", "price_lock": "🔒 Fiyat Yöneticiye Aittir",
        "dom_price": "Fiyat *", "currency": "Para Birimi", "port_disc": "İskonto (%)",
        "main_img": "Ana Görsel", "img_prev": "**Görsel Önizleme**",
        "spec_title": "Özellik Başlığı", "spec_det": "Özellik Detayı", "choose_img": "Resim Seç",
        "add_spec": "➕ ÖZELLİK EKLE", "save_changes": "💾 KAYDET", "add_sys": "💾 EKLE",
        "err_name": "Makine adı zorunludur!", "err_price": "Geçerli fiyat giriniz!",
        "edit_opt_title": "✏️ Donanım Düzenle", "new_opt_title": "✨ Donanım Ekle",
        "opt_name": "Donanım Adı *", "opt_price_lock": "🔒 Fiyat Yöneticiye Aittir",
        "opt_price": "Fiyat *", "allow_qty": "Adet seçilebilir", "opt_desc": "Açıklama", 
        "opt_img_up": "Görsel", "err_opt_name": "Donanım adı zorunludur!", "translating": "Çevriliyor...",
        "opt_suffix": "Model Adı Eki (Suffix)", "opt_v_img": "Varyasyon Resmi", "opt_suffix_help": "💡 Örn: 'L'"
    }
}
def _m(key): 
    lang = st.session_state.get("language", st.session_state.get("lang", "tr"))
    return DICT_MODEL.get(str(lang).lower(), DICT_MODEL["tr"]).get(key, key)

# =====================================================================
# VERİTABANI İŞLEMLERİ
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except Exception as e: return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
        return True
    except Exception as e: return False

def get_image_base64(img_path):
    if not img_path: return ""
    paths_to_try = [img_path, f"images/{img_path}", f"../images/{img_path}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(p)[1].lower().replace('.', '')
                return f"data:image/{ext if ext else 'png'};base64,{b64}"
    return ""

def process_image(uploaded_file, prefix="img", size=(1200, 1200), square=True):
    if not os.path.exists("images"): os.makedirs("images")
    try:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        if square:
            width, height = img.size; new_size = min(width, height)
            left = (width - new_size) / 2; top = (height - new_size) / 2
            right = (width + new_size) / 2; bottom = (height + new_size) / 2
            img = img.crop((left, top, right, bottom)).resize(size, Image.Resampling.LANCZOS)
        else:
            img.thumbnail(size, Image.Resampling.LANCZOS)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join("images", filename)
        img.save(filepath, "JPEG", quality=95)
        return filename
    except: return ""

# =====================================================================
# ANA YÖNETİM MODÜLÜ
# =====================================================================
def show_product_management():
    if "view_mode" not in st.session_state: st.session_state.view_mode = "list"
    if "edit_mod_id" not in st.session_state: st.session_state.edit_mod_id = None
    if "edit_opt_id" not in st.session_state: st.session_state.edit_opt_id = None
    
    user_role = st.session_state.get("user_role", "dealer")
    
    if st.session_state.view_mode == "list": show_list_view(user_role)
    elif st.session_state.view_mode == "mod_add": show_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "mod_edit": show_form_view(mode="edit", mod_id=st.session_state.edit_mod_id, user_role=user_role)
    elif st.session_state.view_mode == "opt_add": show_opt_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "opt_edit": show_opt_form_view(mode="edit", opt_id=st.session_state.edit_opt_id, user_role=user_role)

# =====================================================================
# LİSTELEME EKRANI
# =====================================================================
def show_list_view(user_role):
    st.header(_m("m_title"))
    tab_mod, tab_opt, tab_cat = st.tabs([_m("t_mod"), _m("t_opt"), _m("t_cat")])
    user_id = st.session_state.get("user_id", 1)
    
    with tab_mod:
        col_title, col_add = st.columns([5, 3])
        col_title.subheader(_m("reg_mach"))
        if col_add.button(_m("add_mach"), type="primary", use_container_width=True):
            st.session_state.form_loaded = False; st.session_state.view_mode = "mod_add"; st.rerun()

        st.markdown("---")
        query = "SELECT id, name, category, base_price, currency, image_path FROM models"
        params = ()
        if user_role == "manufacturer": query += " WHERE user_id=?"; params = (user_id,)
            
        mods = get_factory(query + " ORDER BY category ASC, name ASC", params)
        if mods:
            safe_mods = [[get_safe(m,0,0), get_safe(m,1,""), get_safe(m,2,"Diğer"), get_safe(m,3,0.0), get_safe(m,4,"USD"), get_safe(m,5,"")] for m in mods]
            df = pd.DataFrame(safe_mods, columns=["id", "name", "category", "price", "currency", "image"])
            for cat in df['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df[df['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['name']}</h4>", unsafe_allow_html=True)
                                    
                                    if user_role == "manufacturer": st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('no_auth_price')}</div>", unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                        
                                    bc1, bc2 = st.columns(2)
                                    if bc1.button(_m("btn_edit"), key=f"me_{row['id']}", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']; st.session_state.form_loaded = False; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if bc2.button(_m("btn_del"), key=f"md_{row['id']}", use_container_width=True):
                                        exec_factory("DELETE FROM models WHERE id=?", (row['id'],)); st.rerun()
        else: st.info(_m("no_mach"))

    with tab_opt:
        c1, c2 = st.columns([5, 3])
        c1.subheader(_m("opt_showcase"))
        if c2.button(_m("add_opt"), type="primary", use_container_width=True):
            st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_add"; st.rerun()
        
        st.markdown("---")
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image FROM options" + (" WHERE user_id=?" if user_role == "manufacturer" else "") + " ORDER BY id DESC", (user_id,) if user_role == "manufacturer" else ())
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(opts):
                        row_opt = opts[i+j]
                        o_id = get_safe(row_opt, 0, 0); o_name = get_safe(row_opt, 1, "Bilinmeyen")
                        o_price = get_safe(row_opt, 2, 0.0); o_img = get_safe(row_opt, 4, "")
                        
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                            else: st.markdown(f"<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<b>{o_name}</b>", unsafe_allow_html=True)
                            if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                            else: st.markdown(f"<span style='color:#ea580c; font-weight:bold;'>+{o_price:,.0f} USD</span>", unsafe_allow_html=True)
                            
                            bc1, bc2 = st.columns(2)
                            if bc1.button(_m("btn_edit"), key=f"oe_{o_id}", use_container_width=True):
                                st.session_state.edit_opt_id = o_id; st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_edit"; st.rerun()
                            if bc2.button(_m("btn_del"), key=f"od_{o_id}", use_container_width=True):
                                exec_factory("DELETE FROM options WHERE id=?", (o_id,)); st.rerun()
        else: st.info(_m("no_opt"))

    with tab_cat:
        st.subheader(_m("cat_mng"))
        if user_role == "admin":
            with st.form("new_cat_form", clear_on_submit=True):
                n_cat = st.text_input(_m("new_cat"))
                if st.form_submit_button(_m("btn_add")):
                    if n_cat.strip(): exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat.strip(),)); st.rerun()
        cats = get_factory("SELECT id, name FROM categories ORDER BY name ASC")
        if cats:
            for c_id, c_name in cats:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"📁 {c_name}")
                    if user_role == "admin":
                        if col2.button(_m("btn_del_txt"), key=f"rc_{c_id}", use_container_width=True):
                            exec_factory("DELETE FROM categories WHERE id=?", (c_id,)); st.rerun()

# =====================================================================
# MAKİNE (MODEL) DÜZENLEME FORMU - HATASIZ
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button(_m("back_list"), use_container_width=True): st.session_state.view_mode = "list"; st.rerun()
    
    is_edit = (mode == "edit" and mod_id)
    col_title.header(_m("edit_mach") if is_edit else _m("new_mach"))
    st.markdown("---")

    if not st.session_state.get("form_loaded", False):
        st.session_state.form_loaded = True
        cats_db = [c[1] for c in get_factory("SELECT id, name FROM categories")]
        st.session_state.f_cats = cats_db if cats_db else ["Diğer Makinalar"]
        
        if is_edit:
            # DİKKAT: ASLA DOĞRUDAN [0] KULLANMIYORUZ!
            r_list = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options FROM models WHERE id=?", (mod_id,))
            if r_list and len(r_list) > 0:
                r = r_list[0]
            else:
                st.error("Kayıt veritabanında bulunamadı. Lütfen listeye dönün.")
                st.stop() # Çökmeyi durdur
                
            st.session_state.f_name = get_safe(r, 0, "")
            st.session_state.f_price, st.session_state.f_curr, st.session_state.f_cat = get_safe(r, 1, 0.0), get_safe(r, 2, "USD"), get_safe(r, 3, st.session_state.f_cats[0])
            st.session_state.f_disc, st.session_state.f_img = get_safe(r, 4, 0.0), get_safe(r, 5, "")
            st.session_state.f_opts = [x.strip() for x in str(get_safe(r, 7, "")).split(",") if x.strip()]
            
            s_list = []
            target_specs = get_safe(r, 6, "")
            if target_specs:
                for item in str(target_specs).split("||"):
                    if item.strip():
                        p = item.split("|")
                        s_list.append({"title": get_safe(p, 0, ""), "detail": get_safe(p, 1, ""), "img": get_safe(p, 2, "")})
            st.session_state.f_specs = s_list if s_list else [{"title": "", "detail": "", "img": ""}]
        else:
            st.session_state.f_name, st.session_state.f_price, st.session_state.f_curr = "", 0.0, "USD"
            st.session_state.f_cat, st.session_state.f_disc, st.session_state.f_img = st.session_state.f_cats[0], 0.0, ""
            st.session_state.f_specs = [{"title": "", "detail": "", "img": ""}]
            st.session_state.f_opts = []

    t1, t2, t3 = st.tabs([_m("tab_gen"), _m("tab_tech"), _m("tab_comp")])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.f_name = st.text_input(_m("m_name"), value=st.session_state.f_name)
            idx_cat = st.session_state.f_cats.index(st.session_state.f_cat) if st.session_state.f_cat in st.session_state.f_cats else 0
            st.session_state.f_cat = st.selectbox(_m("m_cat"), st.session_state.f_cats, index=idx_cat)
            
            if user_role == "manufacturer": st.warning(_m("price_lock"))
            else:
                cp1, cp2 = st.columns([3, 1])
                st.session_state.f_price = cp1.number_input(_m("dom_price"), value=st.session_state.f_price, min_value=0.0, step=100.0)
                st.session_state.f_curr = cp2.selectbox(_m("currency"), ["USD", "EUR", "TRY"], index=["USD", "EUR", "TRY"].index(st.session_state.f_curr) if st.session_state.f_curr in ["USD", "EUR", "TRY"] else 0)
                st.session_state.f_disc = st.number_input(_m("port_disc"), value=st.session_state.f_disc, min_value=0.0, max_value=100.0)
            
            st.file_uploader(_m("main_img"), type=['png','jpg','jpeg'], key="up_main")
            
        with c2:
            st.markdown(_m("img_prev"))
            up_main = st.session_state.get("up_main")
            if up_main: st.image(up_main, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.f_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
                else: st.markdown(f"<div style='height:200px; display:flex; align-items:center; justify-content:center; background:#f8fafc; border:2px dashed #cbd5e1; border-radius:8px; color:#94a3b8;'>{_m('no_img')}</div>", unsafe_allow_html=True)

    with t2:
        for i in range(len(st.session_state.f_specs)):
            with st.container(border=True):
                col_t, col_d, col_i, col_x = st.columns([3, 4, 3, 1], vertical_alignment="bottom")
                st.session_state.f_specs[i]["title"] = col_t.text_input(_m("spec_title"), value=st.session_state.f_specs[i]["title"], key=f"t_{i}", placeholder=_m("spec_title"))
                st.session_state.f_specs[i]["detail"] = col_d.text_input(_m("spec_det"), value=st.session_state.f_specs[i]["detail"], key=f"d_{i}", placeholder=_m("spec_det"))
                
                with col_i:
                    c_prev, c_up = st.columns([1, 2], vertical_alignment="bottom")
                    up_spec = st.session_state.get(f"up_spec_{i}")
                    if up_spec: c_prev.image(up_spec, width=40)
                    else:
                        cur_img = st.session_state.f_specs[i].get("img", "")
                        if cur_img:
                            b64 = get_image_base64(cur_img)
                            if b64: c_prev.markdown(f'<img src="{b64}" style="width:40px; height:40px; border-radius:4px; object-fit:contain;">', unsafe_allow_html=True)
                    c_up.file_uploader(_m("choose_img"), type=['png','jpg','jpeg'], key=f"up_spec_{i}", label_visibility="collapsed")
                    
                if col_x.button("❌", key=f"del_spec_{i}", use_container_width=True): 
                    st.session_state.f_specs.pop(i); st.rerun()
                    
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        if st.button(_m("add_spec"), use_container_width=True):
            st.session_state.f_specs.append({"title": "", "detail": "", "img": ""}); st.rerun()

    with t3:
        opts_avail = get_factory("SELECT id, opt_name, opt_price, opt_image FROM options ORDER BY opt_price DESC")
        new_opts = []
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id = get_safe(opt, 0, 0); o_name = get_safe(opt, 1, "Bilinmeyen")
            o_price = get_safe(opt, 2, 0.0); o_img = get_safe(opt, 3, "")
            
            p_text = "" if user_role == "manufacturer" else (f"(+{o_price:,.0f})" if o_price > 0 else f"({_m('price_wait')})")
            
            with chk_cols[idx % 3]:
                with st.container(border=True):
                    img_b64 = get_image_base64(o_img)
                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:80px; object-fit:contain; margin-bottom:10px;"></div>', unsafe_allow_html=True)
                    if st.checkbox(f"{o_name} {p_text}".strip(), value=str(o_id) in st.session_state.f_opts, key=f"chk_{o_id}"): new_opts.append(str(o_id))
        st.session_state.f_opts = new_opts

    st.markdown("---")
    btn_save_text = _m("save_changes") if is_edit else _m("add_sys")
    if st.button(btn_save_text, type="primary", use_container_width=True):
        if not st.session_state.f_name: st.error(_m("err_name"))
        elif user_role != "manufacturer" and st.session_state.f_price <= 0: st.error(_m("err_price"))
        else:
            with st.spinner(_m("translating")):
                up_main = st.session_state.get("up_main")
                if up_main is not None: st.session_state.f_img = process_image(up_main, prefix="machine", size=(1200, 1200), square=False)
                uid = st.session_state.get("user_id", 1)

                f_name_tr = st.session_state.f_name
                s_tr = []
                for i, sp in enumerate(st.session_state.f_specs):
                    up_s = st.session_state.get(f"up_spec_{i}")
                    if up_s is not None: sp["img"] = process_image(up_s, prefix="spec", size=(400, 400), square=True)
                    if sp["title"].strip() or sp["detail"].strip(): s_tr.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                specs_tr = " || ".join(s_tr) + (" || " if s_tr else "")
                opt_str = ",".join(st.session_state.f_opts)
                
                if is_edit:
                    exec_factory("UPDATE models SET name=?, category=?, base_price=?, currency=?, specs=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?", (f_name_tr, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, opt_str, st.session_state.f_disc, st.session_state.f_img, mod_id))
                else:
                    exec_factory("INSERT INTO models (name, category, base_price, currency, specs, compatible_options, port_discount, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?)", (f_name_tr, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, opt_str, st.session_state.f_disc, st.session_state.f_img, uid))
                
                st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM FORMU - HATASIZ
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    col_b, col_t = st.columns([1, 5], vertical_alignment="center")
    if col_b.button(_m("back_list"), use_container_width=True): st.session_state.view_mode = "list"; st.rerun()
    is_edit = (mode == "edit" and opt_id)
    col_t.header(_m("edit_opt_title") if is_edit else _m("new_opt_title"))
    st.markdown("---")

    if not st.session_state.get("opt_form_loaded", False):
        st.session_state.opt_form_loaded = True
        if is_edit:
            r_list = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image, allow_qty FROM options WHERE id=?", (opt_id,))
            if r_list and len(r_list) > 0:
                r = r_list[0]
            else:
                st.error("Kayıt bulunamadı. Lütfen listeye dönün."); st.stop()
                
            st.session_state.o_name = get_safe(r, 0, "")
            st.session_state.o_price, st.session_state.o_img, st.session_state.o_qty = get_safe(r, 1, 0.0), get_safe(r, 3, ""), bool(get_safe(r, 4, 1))
            st.session_state.o_desc = get_safe(r, 2, "")
        else:
            st.session_state.o_name, st.session_state.o_price, st.session_state.o_desc, st.session_state.o_img, st.session_state.o_qty = "", 0.0, "", "", True

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.o_name = st.text_input(_m("opt_name"), value=st.session_state.o_name)
            
            if user_role == "manufacturer": st.warning(_m("opt_price_lock"))
            else: st.session_state.o_price = st.number_input(_m("opt_price"), value=st.session_state.o_price, min_value=0.0, step=50.0)
            
            st.session_state.o_qty = st.checkbox(_m("allow_qty"), value=st.session_state.o_qty)
            st.session_state.o_desc = st.text_area(_m("opt_desc"), value=st.session_state.o_desc, height=120)
            st.file_uploader(_m("opt_img_up"), type=['png','jpg','jpeg'], key="up_opt")
            
        with c2:
            st.markdown(_m("img_prev"))
            up_o = st.session_state.get("up_opt")
            if up_o: st.image(up_o, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.o_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

        if st.button("💾 " + (_m("save_changes") if is_edit else _m("add_sys")), type="primary", use_container_width=True):
            if not st.session_state.o_name: st.error(_m("err_opt_name"))
            elif user_role != "manufacturer" and st.session_state.o_price <= 0: st.error(_m("err_price"))
            else:
                with st.spinner(_m("translating")):
                    uid = st.session_state.get("user_id", 1)
                    up = st.session_state.get("up_opt")
                    if up: st.session_state.o_img = process_image(up, "opt", square=True)
                    allow_q = 1 if st.session_state.o_qty else 0
                    o_n_tr = st.session_state.o_name; o_d_tr = st.session_state.o_desc
                    
                    if is_edit: exec_factory("UPDATE options SET opt_name=?, opt_desc=?, opt_price=?, opt_image=?, allow_qty=? WHERE id=?", (o_n_tr, o_d_tr, st.session_state.o_price, st.session_state.o_img, allow_q, opt_id))
                    else: exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, allow_qty, user_id) VALUES (?,?,?,?,?,?)", (o_n_tr, o_d_tr, st.session_state.o_price, st.session_state.o_img, allow_q, uid))
                    
                    st.session_state.view_mode = "list"; st.rerun()
