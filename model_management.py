import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image
import streamlit.components.v1 as components

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
    try:
        return GoogleTranslator(source='auto', target='tr').translate(str(text))
    except:
        return text

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
    lang = "tr"
    if "language" in st.session_state: lang = st.session_state.language
    elif "lang" in st.session_state: lang = st.session_state.lang
    lang = str(lang).lower()
    if lang not in DICT_MODEL: lang = "tr"
    return DICT_MODEL[lang].get(key, key)

# =====================================================================
# VERİTABANI BAĞLANTILARI VE OTOMATİK ONARIM
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except Exception as e: 
        st.error(f"Veritabanı Okuma Hatası: {e}")
        return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
    except Exception as e:
        st.error(f"Veritabanı Yazma Hatası: {e}")

def repair_factory_db():
    exec_factory("CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_desc TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)")
    exec_factory("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', port_discount REAL DEFAULT 0.0, compatible_options TEXT DEFAULT '', gallery_images TEXT DEFAULT '', category TEXT DEFAULT 'Diğer Makinalar', gallery_videos TEXT DEFAULT '')""")
    
    # EKSİK SÜTUNLARI OTOMATİK EKLE
    try: exec_factory("ALTER TABLE models ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass
    try: exec_factory("ALTER TABLE options ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass
    try: exec_factory("ALTER TABLE options ADD COLUMN allow_qty INTEGER DEFAULT 1")
    except: pass
    try: exec_factory("ALTER TABLE options ADD COLUMN opt_name_zh TEXT DEFAULT ''")
    except: pass
    try: exec_factory("ALTER TABLE options ADD COLUMN opt_desc_zh TEXT DEFAULT ''")
    except: pass

repair_factory_db()

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
            width, height = img.size
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            img = img.crop((left, top, right, bottom))
            img = img.resize(size, Image.Resampling.LANCZOS)
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
    exec_factory("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    if "view_mode" not in st.session_state: st.session_state.view_mode = "list"
    if "edit_mod_id" not in st.session_state: st.session_state.edit_mod_id = None
    if "edit_opt_id" not in st.session_state: st.session_state.edit_opt_id = None
    if "edit_cat_id" not in st.session_state: st.session_state.edit_cat_id = None
    user_role = st.session_state.get("user_role", "dealer")
    if st.session_state.view_mode == "list": show_list_view(user_role)
    elif st.session_state.view_mode == "mod_add": show_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "mod_edit": show_form_view(mode="edit", mod_id=st.session_state.edit_mod_id, user_role=user_role)
    elif st.session_state.view_mode == "opt_add": show_opt_form_view(mode="add", user_role=user_role)
    elif st.session_state.view_mode == "opt_edit": show_opt_form_view(mode="edit", opt_id=st.session_state.edit_opt_id, user_role=user_role)

# =====================================================================
# LİSTELEME (İzolasyon Filtreli)
# =====================================================================
def show_list_view(user_role):
    st.header(_m("m_title"))
    tab_mod, tab_opt, tab_cat = st.tabs([_m("t_mod"), _m("t_opt"), _m("t_cat")])
    user_id = st.session_state.get("user_id", 1)
    
    with tab_mod:
        col_title, col_add = st.columns([5, 3], vertical_alignment="center")
        col_title.subheader(_m("reg_mach"))
        if col_add.button(_m("add_mach"), type="primary", use_container_width=True):
            st.session_state.form_loaded = False; st.session_state.view_mode = "mod_add"; st.rerun()
        if user_role == "manufacturer":
            mods = get_factory("SELECT id, name, category, base_price, currency, image_path, name_zh FROM models WHERE user_id=? ORDER BY category ASC, name ASC", (user_id,))
        else:
            mods = get_factory("SELECT id, name, category, base_price, currency, image_path, name_zh FROM models ORDER BY category ASC, name ASC")
        if mods:
            df_mods = pd.DataFrame(mods, columns=["id", "name", "category", "price", "currency", "image", "name_zh"])
            for cat in df_mods['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df_mods[df_mods['category'] == cat]
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                display_name = row['name_zh'] if user_role == "manufacturer" and row['name_zh'] else row['name']
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:150px; object-fit:contain;">', unsafe_allow_html=True)
                                    st.markdown(f"**{display_name}**")
                                    if st.button(_m("btn_edit"), key=f"me_{row['id']}", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']; st.session_state.form_loaded = False; st.session_state.view_mode = "mod_edit"; st.rerun()
        else: st.info(_m("no_mach"))

    with tab_opt:
        col_opt_t, col_opt_a = st.columns([5, 3], vertical_alignment="center")
        col_opt_t.subheader(_m("opt_showcase"))
        if col_opt_a.button(_m("add_opt"), type="primary", use_container_width=True):
            st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_add"; st.rerun()
        
        # DONANIM İZOLASYONU
        if user_role == "manufacturer":
            opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image, opt_name_zh FROM options WHERE user_id=? ORDER BY id DESC", (user_id,))
        else:
            opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image, opt_name_zh FROM options ORDER BY id DESC")
            
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(opts):
                        o_id, o_name, o_price, o_desc, o_img, o_name_zh = opts[i+j]
                        disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain;">', unsafe_allow_html=True)
                            st.markdown(f"**{disp_name}**")
                            if st.button(_m("btn_edit"), key=f"oe_{o_id}", use_container_width=True):
                                st.session_state.edit_opt_id = o_id; st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_edit"; st.rerun()
        else: st.info(_m("no_opt"))

    with tab_cat:
        # Kategori yönetimi aynen kalıyor...
        st.subheader(_m("cat_mng"))
        # (Kategori kodları burada devam eder)

# =====================================================================
# MAKİNE FORMU (Sadece Kendi Donanımlarını Seçebilir)
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    # (Genel form yapısı aynı)
    # Donanım sekmesinde (tab_donanim) izolasyon:
    user_id = st.session_state.get("user_id", 1)
    if user_role == "manufacturer":
        opts_avail = get_factory("SELECT id, opt_name, opt_price, opt_image, opt_name_zh FROM options WHERE user_id=? ORDER BY opt_price DESC", (user_id,))
    else:
        opts_avail = get_factory("SELECT id, opt_name, opt_price, opt_image, opt_name_zh FROM options ORDER BY opt_price DESC")
    # (Makinaya donanım bağlama kodları bu filtrelenmiş listeyi kullanır)

# =====================================================================
# DONANIM FORMU (Kaydederken User_ID Ekler)
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    # (Donanım ekleme/düzenleme formu)
    # Kaydetme kısmında:
    user_id = st.session_state.get("user_id", 1)
    # exec_factory("INSERT INTO options (opt_name, user_id, ...) VALUES (?,?,...)", (o_name, user_id, ...))
