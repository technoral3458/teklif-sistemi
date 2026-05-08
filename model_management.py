import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image
import json

# =====================================================================
# 🛡️ YEDEKLEME VE KASA MOTORU (MANUFACTURER VAULT)
# =====================================================================
# Bu fonksiyon üreticinin verilerini ikinci bir dosyaya (kasa) kopyalar.
def sync_to_vault(table, data_dict, operation="upsert", item_id=None):
    try:
        conn = sqlite3.connect('manufacturer_vault.db', check_same_thread=False)
        c = conn.cursor()
        
        if table == "models":
            c.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY, name TEXT, name_zh TEXT, category TEXT, base_price REAL, currency TEXT, specs TEXT, specs_zh TEXT, compatible_options TEXT, port_discount REAL, image_path TEXT, user_id INTEGER)""")
            if operation == "upsert":
                # Varsa güncelle, yoksa ekle
                cols = ", ".join(data_dict.keys())
                placeholders = ", ".join(["?"] * len(data_dict))
                values = tuple(data_dict.values())
                if item_id:
                    c.execute(f"DELETE FROM models WHERE id=?", (item_id,))
                c.execute(f"INSERT INTO models ({cols}) VALUES ({placeholders})", values)
            elif operation == "delete":
                c.execute("DELETE FROM models WHERE id=?", (item_id,))
                
        elif table == "options":
            c.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY, opt_name TEXT, opt_name_zh TEXT, opt_desc TEXT, opt_desc_zh TEXT, opt_price REAL, opt_image TEXT, allow_qty INTEGER, user_id INTEGER)""")
            if operation == "upsert":
                cols = ", ".join(data_dict.keys())
                placeholders = ", ".join(["?"] * len(data_dict))
                values = tuple(data_dict.values())
                if item_id:
                    c.execute(f"DELETE FROM options WHERE id=?", (item_id,))
                c.execute(f"INSERT INTO options ({cols}) VALUES ({placeholders})", values)
            elif operation == "delete":
                c.execute("DELETE FROM options WHERE id=?", (item_id,))
                
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Vault Sync Error: {e}")

# =====================================================================
# 🤖 YAPAY ZEKA ÇEVİRİ MOTORU
# =====================================================================
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_READY = True
except ImportError:
    TRANSLATOR_READY = False

def auto_translate_to_tr(text):
    if not TRANSLATOR_READY: return text
    if not text or not str(text).strip(): return ""
    try: return GoogleTranslator(source='auto', target='tr').translate(str(text))
    except: return text

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
        "copied": "Kopyalandı!", "no_mach": "Sistemde henüz bir makine bulunmuyor.",
        "opt_showcase": "Ekstra Donanımlar Vitrini", "add_opt": "➕ YENİ DONANIM EKLE",
        "no_opt": "Sistemde henüz bir ekstra donanım bulunmuyor.",
        "cat_mng": "📂 Kategori Yönetimi", "new_cat": "Yeni Kategori Ekle", "new_cat_ph": "Yeni Kategori Adı...",
        "btn_add": "➕ Ekle", "cat_exists": "Bu isimde bir kategori zaten mevcut!",
        "new_name": "Yeni Ad", "save": "💾", "cancel": "❌", "btn_edit_txt": "✏️ Düzenle", "btn_del_txt": "🗑️ Sil",
        "no_cat": "Sistemde henüz bir kategori bulunmuyor.",
        "back_list": "🔙 Listeye Dön", "edit_mach": "✏️ Makine Kartı Düzenleyici", "new_mach": "✨ Yeni Makine Kartı Oluştur",
        "tab_gen": "📄 Genel Bilgiler", "tab_tech": "⚙️ Teknik Özellikler", "tab_comp": "🔌 Uyumlu Donanımlar",
        "m_name": "Makine Adı *", "m_cat": "Kategori",
        "price_lock": "🔒 Fiyatlandırma Yöneticiye aittir.",
        "dom_price": "Yurtiçi Fiyat *", "currency": "Para Birimi", "port_disc": "Liman İskontosu (%)",
        "main_img": "Ana Görsel", "img_prev": "**Görsel Önizleme**",
        "spec_title": "Özellik Başlığı", "spec_det": "Özellik Detayı", "choose_img": "Resim Seç",
        "add_spec": "➕ YENİ ÖZELLİK SATIRI EKLE", "no_comp_opt": "Bu makineye tanımlı donanım bulunmuyor.",
        "save_changes": "💾 DEĞİŞİKLİKLERİ KAYDET", "add_sys": "💾 SİSTEME EKLE",
        "err_name": "Lütfen makine adını girin!", "err_price": "Lütfen geçerli bir fiyat girin!",
        "edit_opt_title": "✏️ Donanım Düzenle", "new_opt_title": "✨ Yeni Ekstra Donanım Ekle",
        "opt_name": "Donanım Adı *", "opt_price_lock": "🔒 Fiyatlandırma Yönetici tarafından yapılacaktır.",
        "opt_price": "Fiyat *", "allow_qty": "Bu donanım için adet seçimi yapılabilir",
        "opt_desc": "Açıklama", "opt_img_up": "Donanım Görseli", "err_opt_name": "Donanım Adı zorunludur!",
        "translating": "🤖 Metinler otomatik olarak Türkçeye çevriliyor..."
    },
    "en": {
        "m_title": "📦 Factory Database Management",
        "t_mod": "📦 Models (Showcase)", "t_opt": "⚙️ Extra Options", "t_cat": "📂 Categories",
        "reg_mach": "Registered Machines", "add_mach": "➕ ADD NEW MACHINE",
        "no_img": "No Image", "price_wait": "Price Pending", "no_auth_price": "🔒 Price Hidden",
        "btn_edit": "✏️", "btn_copy": "📄", "btn_del": "🗑️",
        "copied": "Copied!", "no_mach": "No machines found in the system yet.",
        "opt_showcase": "Extra Options Showcase", "add_opt": "➕ ADD NEW OPTION",
        "no_opt": "No extra options found in the system yet.",
        "cat_mng": "📂 Category Management", "new_cat": "Add New Category", "new_cat_ph": "New Category Name...",
        "btn_add": "➕ Add", "cat_exists": "A category with this name already exists!",
        "new_name": "New Name", "save": "💾", "cancel": "❌", "btn_edit_txt": "✏️ Edit", "btn_del_txt": "🗑️ Delete",
        "no_cat": "No categories found in the system yet.",
        "back_list": "🔙 Back to List", "edit_mach": "✏️ Machine Card Editor", "new_mach": "✨ Create New Machine Card",
        "tab_gen": "📄 General Info", "tab_tech": "⚙️ Technical Specs", "tab_comp": "🔌 Compatible Options",
        "m_name": "Machine Name *", "m_cat": "Category",
        "price_lock": "🔒 Pricing belongs to Admin.",
        "dom_price": "Domestic Price *", "currency": "Currency", "port_disc": "Port Discount (%)",
        "main_img": "Main Image", "img_prev": "**Image Preview**",
        "spec_title": "Spec Title", "spec_det": "Spec Detail", "choose_img": "Choose Image",
        "add_spec": "➕ ADD NEW SPEC ROW", "no_comp_opt": "No compatible options defined.",
        "save_changes": "💾 SAVE CHANGES", "add_sys": "💾 ADD TO SYSTEM",
        "err_name": "Please enter the machine name!", "err_price": "Please enter a valid price!",
        "edit_opt_title": "✏️ Edit Option", "new_opt_title": "✨ Add New Extra Option",
        "opt_name": "Option Name *", "opt_price_lock": "🔒 Pricing will be set by the Admin.",
        "opt_price": "Price *", "allow_qty": "Allow quantity selection",
        "opt_desc": "Description", "opt_img_up": "Option Image", "err_opt_name": "Option Name is required!",
        "translating": "🤖 Translating texts automatically..."
    },
    "zh": {
        "m_title": "📦 工厂数据库管理",
        "t_mod": "📦 型号 (展示)", "t_opt": "⚙️ 额外选项", "t_cat": "📂 类别",
        "reg_mach": "已注册机器", "add_mach": "➕ 添加新机器",
        "no_img": "无图像", "price_wait": "等待定价", "no_auth_price": "🔒 价格隐藏",
        "btn_edit": "✏️", "btn_copy": "📄", "btn_del": "🗑️",
        "copied": "已复制！", "no_mach": "系统中尚未找到机器。",
        "opt_showcase": "额外选项展示", "add_opt": "➕ 添加新选项",
        "no_opt": "系统中尚未找到额外选项。",
        "cat_mng": "📂 类别管理", "new_cat": "添加新类别", "new_cat_ph": "新类别名称...",
        "btn_add": "➕ 添加", "cat_exists": "该名称的类别已存在！",
        "new_name": "新名称", "save": "💾", "cancel": "❌", "btn_edit_txt": "✏️ 编辑", "btn_del_txt": "🗑️ 删除",
        "no_cat": "系统中尚未找到类别。",
        "back_list": "🔙 返回列表", "edit_mach": "✏️ 机器卡片编辑器", "new_mach": "✨ 创建新机器卡片",
        "tab_gen": "📄 一般信息", "tab_tech": "⚙️ 技术规格", "tab_comp": "🔌 兼容选项",
        "m_name": "机器名称 (中文) *", "m_cat": "类别",
        "price_lock": "🔒 定价由土耳其总部完成。",
        "dom_price": "价格 *", "currency": "货币", "port_disc": "折扣 (%)",
        "main_img": "主图像文件", "img_prev": "**图像预览**",
        "spec_title": "规格标题", "spec_det": "规格详情", "choose_img": "选择图像",
        "add_spec": "➕ 添加新规格行", "no_comp_opt": "没有为此机器定义兼容选项。",
        "save_changes": "💾 保存更改", "add_sys": "💾 将机器添加到系统",
        "err_name": "请输入机器名称！", "err_price": "请输入有效价格！",
        "edit_opt_title": "✏️ 编辑选项", "new_opt_title": "✨ 添加新额外选项",
        "opt_name": "选项名称 (中文) *", "opt_price_lock": "🔒 定价由土耳其总部完成。",
        "opt_price": "价格 *", "allow_qty": "允许数量选择",
        "opt_desc": "描述", "opt_img_up": "选项图像", "err_opt_name": "选项名称为必填项！",
        "translating": "🤖 正在自动翻译成土耳其语..."
    }
}

def _m(key): 
    lang = st.session_state.get("language", st.session_state.get("lang", "tr")).lower()
    if lang not in DICT_MODEL: lang = "tr"
    return DICT_MODEL[lang].get(key, key)

# =====================================================================
# VERİTABANI BAĞLANTILARI
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except: return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
    except Exception as e: st.error(f"DB Error: {e}")

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
            left = (width - new_size)/2; top = (height - new_size)/2; right = (width + new_size)/2; bottom = (height + new_size)/2
            img = img.crop((left, top, right, bottom)).resize(size, Image.Resampling.LANCZOS)
        else: img.thumbnail(size, Image.Resampling.LANCZOS)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"; filepath = os.path.join("images", filename)
        img.save(filepath, "JPEG", quality=95); return filename
    except: return ""

# =====================================================================
# ANA YÖNETİM MODÜLÜ
# =====================================================================
def show_product_management():
    if "view_mode" not in st.session_state: st.session_state.view_mode = "list"
    user_role = st.session_state.get("user_role", "dealer")
    
    if st.session_state.view_mode == "list": show_list_view(user_role)
    elif st.session_state.view_mode == "mod_add": show_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "mod_edit": show_form_view(mode="edit", mod_id=st.session_state.edit_mod_id, user_role=user_role)
    elif st.session_state.view_mode == "opt_add": show_opt_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "opt_edit": show_opt_form_view(mode="edit", opt_id=st.session_state.edit_opt_id, user_role=user_role)

def show_list_view(user_role):
    st.header(_m("m_title"))
    tab_mod, tab_opt, tab_cat = st.tabs([_m("t_mod"), _m("t_opt"), _m("t_cat")])
    user_id = st.session_state.get("user_id", 1)
    
    with tab_mod:
        c1, c2 = st.columns([5, 3])
        c1.subheader(_m("reg_mach"))
        if c2.button(_m("add_mach"), type="primary", use_container_width=True):
            st.session_state.form_loaded = False; st.session_state.view_mode = "mod_add"; st.rerun()

        st.markdown("---")
        query = "SELECT id, name, category, base_price, currency, image_path, name_zh FROM models"
        params = ()
        if user_role == "manufacturer":
            query += " WHERE user_id=?"; params = (user_id,)
        
        mods = get_factory(query + " ORDER BY category ASC, name ASC", params)
        if mods:
            df = pd.DataFrame(mods, columns=["id", "name", "category", "price", "currency", "image", "name_zh"])
            for cat in df['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df[df['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                disp_name = row['name_zh'] if user_role == "manufacturer" and row['name_zh'] else row['name']
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                                    st.markdown(f"<b>{disp_name}</b>", unsafe_allow_html=True)
                                    
                                    if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                                    else: st.markdown(f"<span style='color:#ea580c; font-weight:bold;'>{row['price']:,.0f} {row['currency']}</span>", unsafe_allow_html=True)
                                    
                                    bc1, bc2, bc3 = st.columns(3)
                                    if bc1.button(_m("btn_edit"), key=f"me_{row['id']}", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']; st.session_state.form_loaded = False; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if bc3.button(_m("btn_del"), key=f"md_{row['id']}", use_container_width=True):
                                        exec_factory("DELETE FROM models WHERE id=?", (row['id'],))
                                        if user_role == "manufacturer": sync_to_vault("models", {}, "delete", row['id'])
                                        st.rerun()
        else: st.info(_m("no_mach"))

    with tab_opt:
        c1, c2 = st.columns([5, 3])
        c1.subheader(_m("opt_showcase"))
        if c2.button(_m("add_opt"), type="primary", use_container_width=True):
            st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_add"; st.rerun()
        
        st.markdown("---")
        query_opt = "SELECT id, opt_name, opt_price, opt_desc, opt_image, opt_name_zh FROM options"
        params_opt = ()
        if user_role == "manufacturer":
            query_opt += " WHERE user_id=?"; params_opt = (user_id,)
            
        opts = get_factory(query_opt + " ORDER BY id DESC", params_opt)
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(opts):
                        o_id, o_name, o_price, o_desc, o_img, o_name_zh = opts[i+j]
                        disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:100px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                            st.markdown(f"<b>{disp_name}</b>", unsafe_allow_html=True)
                            
                            if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                            else: st.markdown(f"<span style='color:#ea580c; font-weight:bold;'>+{o_price:,.0f} USD</span>", unsafe_allow_html=True)
                            
                            bc1, bc2 = st.columns(2)
                            if bc1.button(_m("btn_edit"), key=f"oe_{o_id}", use_container_width=True):
                                st.session_state.edit_opt_id = o_id; st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_edit"; st.rerun()
                            if bc2.button(_m("btn_del"), key=f"od_{o_id}", use_container_width=True):
                                exec_factory("DELETE FROM options WHERE id=?", (o_id,))
                                if user_role == "manufacturer": sync_to_vault("options", {}, "delete", o_id)
                                st.rerun()
        else: st.info(_m("no_opt"))

    with tab_cat:
        st.subheader(_m("cat_mng"))
        if user_role == "admin":
            with st.form("new_cat_form"):
                n_cat = st.text_input(_m("new_cat"))
                if st.form_submit_button(_m("btn_add")):
                    if n_cat.strip():
                        try: exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat.strip(),)); st.rerun()
                        except: st.error(_m("cat_exists"))
        
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
# MAKİNE FORMU (KASA DESTEKLİ)
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    if st.button(_m("back_list")): st.session_state.view_mode = "list"; st.rerun()
    is_edit = (mode == "edit" and mod_id)
    st.header(_m("edit_mach") if is_edit else _m("new_mach"))
    
    if not st.session_state.get("form_loaded", False):
        st.session_state.form_loaded = True
        cats_db = [c[1] for c in get_factory("SELECT id, name FROM categories")]
        st.session_state.f_cats = cats_db if cats_db else ["Diğer Makinalar"]
        if is_edit:
            r = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options, name_zh, specs_zh FROM models WHERE id=?", (mod_id,))[0]
            st.session_state.f_name = r[8] if user_role == "manufacturer" and r[8] else r[0]
            st.session_state.f_price, st.session_state.f_curr, st.session_state.f_cat = r[1], r[2], r[3]
            st.session_state.f_disc, st.session_state.f_img = r[4], r[5]
            st.session_state.f_opts = [x.strip() for x in str(r[7]).split(",") if x.strip()]
            s_list = []
            target_specs = r[9] if user_role == "manufacturer" and r[9] else r[6]
            if target_specs:
                for item in str(target_specs).split("||"):
                    if "|" in item:
                        p = item.split("|"); s_list.append({"title": p[0], "detail": p[1] if len(p)>1 else "", "img": p[2] if len(p)>2 else ""})
            st.session_state.f_specs = s_list if s_list else [{"title": "", "detail": "", "img": ""}]
        else:
            st.session_state.f_name, st.session_state.f_price, st.session_state.f_curr = "", 0.0, "USD"
            st.session_state.f_cat, st.session_state.f_disc, st.session_state.f_img = st.session_state.f_cats[0], 0.0, ""
            st.session_state.f_specs = [{"title": "", "detail": "", "img": ""}]; st.session_state.f_opts = []

    t1, t2, t3 = st.tabs([_m("tab_gen"), _m("tab_tech"), _m("tab_comp")])
    with t1:
        st.session_state.f_name = st.text_input(_m("m_name"), value=st.session_state.f_name)
        idx_cat = st.session_state.f_cats.index(st.session_state.f_cat) if st.session_state.f_cat in st.session_state.f_cats else 0
        st.session_state.f_cat = st.selectbox(_m("m_cat"), st.session_state.f_cats, index=idx_cat)
        if user_role == "manufacturer": st.warning(_m("price_lock"))
        else:
            cp1, cp2 = st.columns(2)
            st.session_state.f_price = cp1.number_input(_m("dom_price"), value=st.session_state.f_price)
            st.session_state.f_curr = cp2.selectbox(_m("currency"), ["USD", "EUR", "TRY"], index=["USD", "EUR", "TRY"].index(st.session_state.f_curr))
        st.file_uploader(_m("main_img"), type=['png','jpg','jpeg'], key="up_main")

    with t2:
        for i in range(len(st.session_state.f_specs)):
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 4, 1])
                st.session_state.f_specs[i]["title"] = c1.text_input(f"{i}-Title", value=st.session_state.f_specs[i]["title"], label_visibility="collapsed")
                st.session_state.f_specs[i]["detail"] = c2.text_input(f"{i}-Det", value=st.session_state.f_specs[i]["detail"], label_visibility="collapsed")
                if c3.button("❌", key=f"ds_{i}"): st.session_state.f_specs.pop(i); st.rerun()
        if st.button(_m("add_spec")): st.session_state.f_specs.append({"title":"","detail":"","img":""}); st.rerun()

    with t3:
        st.write("Donanımları seçin")
        all_o = get_factory("SELECT id, opt_name FROM options")
        new_sel = []
        for oid, oname in all_o:
            if st.checkbox(oname, value=str(oid) in st.session_state.f_opts, key=f"co_{oid}"): new_sel.append(str(oid))
        st.session_state.f_opts = new_sel

    if st.button(_m("save_changes") if is_edit else _m("add_sys"), type="primary", use_container_width=True):
        with st.spinner(_m("translating")):
            uid = st.session_state.get("user_id", 1)
            up = st.session_state.get("up_main")
            if up: st.session_state.f_img = process_image(up, "mach", square=False)
            
            # Çeviri ve Veri Hazırlama
            f_name_tr = auto_translate_to_tr(st.session_state.f_name) if user_role == "manufacturer" else st.session_state.f_name
            f_name_zh = st.session_state.f_name if user_role == "manufacturer" else ""
            
            spec_strs = [f"{s['title']}|{s['detail']}|{s.get('img','')}" for s in st.session_state.f_specs]
            specs_tr = " || ".join([auto_translate_to_tr(s) for s in spec_strs]) if user_role == "manufacturer" else " || ".join(spec_strs)
            specs_zh = " || ".join(spec_strs) if user_role == "manufacturer" else ""
            
            opt_str = ",".join(st.session_state.f_opts)
            
            data_dict = {
                "name": f_name_tr, "name_zh": f_name_zh, "category": st.session_state.f_cat, 
                "base_price": st.session_state.f_price, "currency": st.session_state.f_curr,
                "specs": specs_tr, "specs_zh": specs_zh, "compatible_options": opt_str,
                "port_discount": st.session_state.f_disc, "image_path": st.session_state.f_img, "user_id": uid
            }
            
            if is_edit:
                exec_factory("UPDATE models SET name=?, name_zh=?, category=?, base_price=?, currency=?, specs=?, specs_zh=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?", 
                             (f_name_tr, f_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, specs_zh, opt_str, st.session_state.f_disc, st.session_state.f_img, mod_id))
                if user_role == "manufacturer": 
                    data_dict["id"] = mod_id
                    sync_to_vault("models", data_dict, "upsert", mod_id)
            else:
                exec_factory("INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                             (f_name_tr, f_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, specs_zh, opt_str, st.session_state.f_disc, st.session_state.f_img, uid))
                if user_role == "manufacturer":
                    new_id = get_factory("SELECT id FROM models ORDER BY id DESC LIMIT 1")[0][0]
                    data_dict["id"] = new_id
                    sync_to_vault("models", data_dict, "upsert", new_id)
            
            st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM FORMU (KASA DESTEKLİ)
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    if st.button(_m("back_list")): st.session_state.view_mode = "list"; st.rerun()
    is_edit = (mode == "edit" and opt_id)
    
    if not st.session_state.get("opt_form_loaded", False):
        st.session_state.opt_form_loaded = True
        if is_edit:
            r = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image, allow_qty, opt_name_zh, opt_desc_zh FROM options WHERE id=?", (opt_id,))[0]
            st.session_state.o_name = r[5] if user_role == "manufacturer" and r[5] else r[0]
            st.session_state.o_desc = r[6] if user_role == "manufacturer" and r[6] else r[2]
            st.session_state.o_price, st.session_state.o_img, st.session_state.o_qty = r[1], r[3], bool(r[4])
        else:
            st.session_state.o_name, st.session_state.o_price, st.session_state.o_desc, st.session_state.o_img, st.session_state.o_qty = "", 0.0, "", "", True

    with st.container(border=True):
        st.session_state.o_name = st.text_input(_m("opt_name"), value=st.session_state.o_name)
        if user_role == "manufacturer": st.warning(_m("opt_price_lock"))
        else: st.session_state.o_price = st.number_input(_m("opt_price"), value=st.session_state.o_price)
        st.session_state.o_qty = st.checkbox(_m("allow_qty"), value=st.session_state.o_qty)
        st.session_state.o_desc = st.text_area(_m("opt_desc"), value=st.session_state.o_desc)
        st.file_uploader(_m("opt_img_up"), type=['png','jpg','jpeg'], key="up_opt")

        if st.button(_m("save_changes") if is_edit else _m("add_sys"), type="primary"):
            with st.spinner(_m("translating")):
                uid = st.session_state.get("user_id", 1)
                up = st.session_state.get("up_opt")
                if up: st.session_state.o_img = process_image(up, "opt")
                
                o_name_tr = auto_translate_to_tr(st.session_state.o_name) if user_role == "manufacturer" else st.session_state.o_name
                o_name_zh = st.session_state.o_name if user_role == "manufacturer" else ""
                o_desc_tr = auto_translate_to_tr(st.session_state.o_desc) if user_role == "manufacturer" else st.session_state.o_desc
                o_desc_zh = st.session_state.o_desc if user_role == "manufacturer" else ""
                
                allow_q = 1 if st.session_state.o_qty else 0
                data_opt = {
                    "opt_name": o_name_tr, "opt_name_zh": o_name_zh, "opt_desc": o_desc_tr, 
                    "opt_desc_zh": o_desc_zh, "opt_price": st.session_state.o_price, 
                    "opt_image": st.session_state.o_img, "allow_qty": allow_q, "user_id": uid
                }
                
                if is_edit:
                    exec_factory("UPDATE options SET opt_name=?, opt_name_zh=?, opt_desc=?, opt_desc_zh=?, opt_price=?, opt_image=?, allow_qty=? WHERE id=?", 
                                 (o_name_tr, o_name_zh, o_desc_tr, o_desc_zh, st.session_state.o_price, st.session_state.o_img, allow_q, opt_id))
                    if user_role == "manufacturer":
                        data_opt["id"] = opt_id
                        sync_to_vault("options", data_opt, "upsert", opt_id)
                else:
                    exec_factory("INSERT INTO options (opt_name, opt_name_zh, opt_desc, opt_desc_zh, opt_price, opt_image, allow_qty, user_id) VALUES (?,?,?,?,?,?,?,?)", 
                                 (o_name_tr, o_name_zh, o_desc_tr, o_desc_zh, st.session_state.o_price, st.session_state.o_img, allow_q, uid))
                    if user_role == "manufacturer":
                        new_id = get_factory("SELECT id FROM options ORDER BY id DESC LIMIT 1")[0][0]
                        data_opt["id"] = new_id
                        sync_to_vault("options", data_opt, "upsert", new_id)
                
                st.session_state.view_mode = "list"; st.rerun()
