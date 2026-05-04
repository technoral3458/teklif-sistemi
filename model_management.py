import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image

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
    lang = st.session_state.get('lang', 'tr')
    return DICT_MODEL.get(lang, DICT_MODEL["tr"]).get(key, key)

# =====================================================================
# VERİTABANI BAĞLANTILARI
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
    
    try:
        cols_mod = [c[1] for c in get_factory("PRAGMA table_info(models)")]
        if "name_zh" not in cols_mod: exec_factory("ALTER TABLE models ADD COLUMN name_zh TEXT DEFAULT ''")
        if "specs_zh" not in cols_mod: exec_factory("ALTER TABLE models ADD COLUMN specs_zh TEXT DEFAULT ''")
        
        cols_opt = [c[1] for c in get_factory("PRAGMA table_info(options)")]
        if "allow_qty" not in cols_opt: exec_factory("ALTER TABLE options ADD COLUMN allow_qty INTEGER DEFAULT 1")
        if "opt_name_zh" not in cols_opt: exec_factory("ALTER TABLE options ADD COLUMN opt_name_zh TEXT DEFAULT ''")
        if "opt_desc_zh" not in cols_opt: exec_factory("ALTER TABLE options ADD COLUMN opt_desc_zh TEXT DEFAULT ''")
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
    
    if not TRANSLATOR_READY and st.session_state.get("user_role") == "manufacturer":
        st.warning("⚠️ Çeviri modülü kurulu değil. Lütfen sunucunuza kurun: `pip install deep-translator`")

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
# VİTRİN VE LİSTELEME
# =====================================================================
def show_list_view(user_role):
    # =====================================================================
    # NOKTA ATIŞI CERRAHİ CSS - KESİN ÇÖZÜM
    # Bu CSS SADECE içinde '.keep-row' adlı gizli etiket olan kapsayıcıları bulur.
    # Ana 4'lü tablo ızgarasını KESİNLİKLE BOZMAZ.
    # =====================================================================
    st.markdown("""
    <style>
    /* 3'lü Buton Grubu İçin (Düzenle, Kopyala, Sil) */
    div[data-testid="stHorizontalBlock"]:has(.keep-row) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.3rem !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.keep-row) > div[data-testid="column"] {
        width: 33.33% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* 2'li Buton Grubu İçin (Kategori Düzenle, Sil) */
    div[data-testid="stHorizontalBlock"]:has(.keep-row-2) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.3rem !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.keep-row-2) > div[data-testid="column"] {
        width: 50% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Buton İç İçi Boşlukları Küçültme (Daha şık durması için) */
    div[data-testid="stHorizontalBlock"]:has(.keep-row) button {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.header(_m("m_title"))
    tab_mod, tab_opt, tab_cat = st.tabs([_m("t_mod"), _m("t_opt"), _m("t_cat")])
    
    with tab_mod:
        col_title, col_add = st.columns([5, 3], vertical_alignment="center")
        col_title.subheader(_m("reg_mach"))
        if col_add.button(_m("add_mach"), type="primary", use_container_width=True, key="btn_add_mach_main"):
            st.session_state.form_loaded = False 
            st.session_state.view_mode = "mod_add"; st.rerun()

        st.markdown("---")
        mods = get_factory("SELECT id, name, category, base_price, currency, image_path, name_zh FROM models ORDER BY category ASC, name ASC")
        if mods:
            df_mods = pd.DataFrame(mods, columns=["id", "name", "category", "price", "currency", "image", "name_zh"])
            for cat in df_mods['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df_mods[df_mods['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4, gap="small")
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                safe_mod_id = int(row['id']) 
                                
                                display_name = row['name_zh'] if user_role == "manufacturer" and row['name_zh'] else row['name']
                                
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{display_name}'>{display_name}</h4>", unsafe_allow_html=True)
                                    
                                    if user_role == "manufacturer":
                                        st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('no_auth_price')}</div>", unsafe_allow_html=True)
                                    else:
                                        if row['price'] > 0: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                        else: st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('price_wait')}</div>", unsafe_allow_html=True)
                                        
                                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                                    with btn_c1:
                                        # CSS HİLESİNİ TETİKLEYEN İŞARETÇİ BURADA
                                        st.markdown('<span class="keep-row"></span>', unsafe_allow_html=True)
                                        if st.button(_m("btn_edit"), key=f"me_{safe_mod_id}", use_container_width=True):
                                            st.session_state.edit_mod_id = safe_mod_id; st.session_state.form_loaded = False; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    with btn_c2:
                                        if st.button(_m("btn_copy"), key=f"mc_{safe_mod_id}", use_container_width=True):
                                            m_data = get_factory("SELECT name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos, name_zh, specs_zh FROM models WHERE id=?", (safe_mod_id,))[0]
                                            exec_factory("""INSERT INTO models (name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos, name_zh, specs_zh) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (m_data[0] + " (Copy)", m_data[1], m_data[2], m_data[3], m_data[4], m_data[5], m_data[6], m_data[7], m_data[8], m_data[9], m_data[10], m_data[11]))
                                            st.success(_m("copied")); st.rerun()
                                    with btn_c3:
                                        if st.button(_m("btn_del"), key=f"md_{safe_mod_id}", use_container_width=True):
                                            exec_factory("DELETE FROM models WHERE id=?", (safe_mod_id,)); st.rerun()
        else: st.info(_m("no_mach"))

    with tab_opt:
        col_opt_t, col_opt_a = st.columns([5, 3], vertical_alignment="center")
        col_opt_t.subheader(_m("opt_showcase"))
        if col_opt_a.button(_m("add_opt"), type="primary", use_container_width=True, key="btn_add_opt_main"):
            st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_add"; st.rerun()

        st.markdown("---")
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image, opt_name_zh, opt_desc_zh FROM options ORDER BY id DESC")
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4, gap="small")
                for j in range(4):
                    if i + j < len(opts):
                        o_id, o_name, o_price, o_desc, o_img, o_name_zh, o_desc_zh = opts[i+j]
                        safe_opt_id = int(o_id)
                        
                        disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
                        disp_desc = o_desc_zh if user_role == "manufacturer" and o_desc_zh else o_desc
                        
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                            else: st.markdown(f"<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{disp_name}'>{disp_name}</h4>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#64748b; font-size:12px; height:36px; overflow:hidden; margin-bottom:5px;'>{disp_desc if disp_desc else '-'}</div>", unsafe_allow_html=True)
                            
                            if user_role == "manufacturer":
                                st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:12px; margin-bottom:15px; padding:2px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('no_auth_price')}</div>", unsafe_allow_html=True)
                            else:
                                if o_price > 0: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>+{o_price:,.2f} USD</div>", unsafe_allow_html=True)
                                else: st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:12px; margin-bottom:15px; padding:2px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('price_wait')}</div>", unsafe_allow_html=True)

                            btn_c1, btn_c2, btn_c3 = st.columns(3)
                            with btn_c1:
                                # CSS HİLESİNİ TETİKLEYEN İŞARETÇİ BURADA
                                st.markdown('<span class="keep-row"></span>', unsafe_allow_html=True)
                                if st.button(_m("btn_edit"), key=f"oe_{safe_opt_id}", use_container_width=True):
                                    st.session_state.edit_opt_id = safe_opt_id; st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_edit"; st.rerun()
                            with btn_c2:
                                if st.button(_m("btn_copy"), key=f"oc_{safe_opt_id}", use_container_width=True):
                                    o_data = get_factory("SELECT opt_name, opt_desc, opt_price, opt_image, sort_order, allow_qty, opt_name_zh, opt_desc_zh FROM options WHERE id=?", (safe_opt_id,))[0]
                                    exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, sort_order, allow_qty, opt_name_zh, opt_desc_zh) VALUES (?,?,?,?,?,?,?,?)", (o_data[0] + " (Copy)", o_data[1], o_data[2], o_data[3], o_data[4], o_data[5], o_data[6], o_data[7]))
                                    st.rerun()
                            with btn_c3:
                                if st.button(_m("btn_del"), key=f"od_{safe_opt_id}", use_container_width=True):
                                    exec_factory("DELETE FROM options WHERE id=?", (safe_opt_id,)); st.rerun()
        else: st.info(_m("no_opt"))

    with tab_cat:
        c1, c2 = st.columns([5, 3], vertical_alignment="bottom")
        c1.subheader(_m("cat_mng"))
        with c2.form("new_cat_form", clear_on_submit=True):
            cc1, cc2 = st.columns([3, 1])
            n_cat = cc1.text_input(_m("new_cat"), label_visibility="collapsed", placeholder=_m("new_cat_ph"))
            if cc2.form_submit_button(_m("btn_add"), use_container_width=True):
                if n_cat.strip():
                    try: exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat.strip(),)); st.rerun()
                    except: st.error(_m("cat_exists"))

        st.markdown("---")
        cats = get_factory("SELECT id, name FROM categories ORDER BY name ASC")
        if cats:
            for i in range(0, len(cats), 4):
                cols = st.columns(4, gap="small")
                for j in range(4):
                    if i + j < len(cats):
                        cid, cname = cats[i+j]
                        with cols[j].container(border=True):
                            if st.session_state.get("edit_cat_id") == cid:
                                new_cname = st.text_input(_m("new_name"), value=cname, key=f"inp_cat_{cid}", label_visibility="collapsed")
                                bc1, bc2 = st.columns(2)
                                if bc1.button(_m("save"), key=f"save_cat_{cid}", use_container_width=True):
                                    if new_cname.strip() and new_cname.strip() != cname:
                                        exec_factory("UPDATE categories SET name=? WHERE id=?", (new_cname.strip(), cid))
                                        exec_factory("UPDATE models SET category=? WHERE category=?", (new_cname.strip(), cname))
                                    st.session_state.edit_cat_id = None; st.rerun()
                                if bc2.button(_m("cancel"), key=f"cancel_cat_{cid}", use_container_width=True):
                                    st.session_state.edit_cat_id = None; st.rerun()
                            else:
                                st.markdown(f"<div style='text-align:center; padding:15px 0;'><span style='font-size:32px;'>📁</span><br><b style='color:#0f172a; font-size:16px;'>{cname}</b></div>", unsafe_allow_html=True)
                                
                                bc1, bc2 = st.columns(2)
                                with bc1:
                                    # 2 Lİ BUTONU YAN YANA TUTACAK CSS İŞARETÇİSİ
                                    st.markdown('<span class="keep-row-2"></span>', unsafe_allow_html=True)
                                    if st.button(_m("btn_edit_txt"), key=f"ed_cat_{cid}", use_container_width=True):
                                        st.session_state.edit_cat_id = cid; st.rerun()
                                with bc2:
                                    if st.button(_m("btn_del_txt"), key=f"rm_cat_{cid}", use_container_width=True):
                                        exec_factory("DELETE FROM categories WHERE id=?", (cid,)); st.rerun()
        else: st.info(_m("no_cat"))


# =====================================================================
# MAKİNE EKLEME/DÜZENLEME FORMU
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button(_m("back_list"), use_container_width=True, key="btn_back_from_mach"):
        st.session_state.view_mode = "list"; st.rerun()
    
    is_edit = (mode == "edit" and mod_id is not None)
    col_title.header(_m("edit_mach") if is_edit else _m("new_mach"))
    st.markdown("---")

    if not st.session_state.get("form_loaded", False):
        st.session_state.form_loaded = True
        cats_list = [c[1] for c in get_factory("SELECT id, name FROM categories")]
        st.session_state.f_cats_list = cats_list if cats_list else ["Diğer Makinalar"]
        
        if is_edit:
            res = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options, name_zh, specs_zh FROM models WHERE id=?", (int(mod_id),))
            r = res[0]
            
            m_name_tr, m_specs_tr, m_name_zh, m_specs_zh = r[0], r[6], r[8], r[9]
            st.session_state.f_name = m_name_zh if user_role == "manufacturer" and m_name_zh else m_name_tr
            
            st.session_state.f_price, st.session_state.f_curr = float(r[1]), r[2]
            st.session_state.f_cat, st.session_state.f_disc, st.session_state.f_img = r[3], float(r[4]), r[5]
            
            s_list = []
            target_specs = m_specs_zh if user_role == "manufacturer" and m_specs_zh else m_specs_tr
            if target_specs:
                for item in str(target_specs).split("||"):
                    if item.strip():
                        parts = item.split("|")
                        s_list.append({"title": parts[0].strip() if len(parts) > 0 else "", "detail": parts[1].strip() if len(parts) > 1 else "", "img": parts[2].strip() if len(parts) > 2 else ""})
            st.session_state.f_specs = s_list if s_list else [{"title": "", "detail": "", "img": ""}]
            st.session_state.f_opts = [x.strip() for x in str(r[7]).split(",") if x.strip()]
        else:
            st.session_state.f_name, st.session_state.f_price, st.session_state.f_curr = "", 0.0, "USD"
            st.session_state.f_cat, st.session_state.f_disc, st.session_state.f_img = st.session_state.f_cats_list[0], 0.0, ""
            st.session_state.f_specs = [{"title": "", "detail": "", "img": ""}]
            st.session_state.f_opts = []

    tab_genel, tab_teknik, tab_donanim = st.tabs([_m("tab_gen"), _m("tab_tech"), _m("tab_comp")])
    
    with tab_genel:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.f_name = st.text_input(_m("m_name"), value=st.session_state.f_name)
            idx_cat = st.session_state.f_cats_list.index(st.session_state.f_cat) if st.session_state.f_cat in st.session_state.f_cats_list else 0
            st.session_state.f_cat = st.selectbox(_m("m_cat"), st.session_state.f_cats_list, index=idx_cat)
            
            if user_role == "manufacturer":
                st.warning(_m("price_lock"))
                st.session_state.f_price = st.session_state.get('f_price', 0.0)
                st.session_state.f_disc = st.session_state.get('f_disc', 0.0)
                st.session_state.f_curr = st.session_state.get('f_curr', 'USD')
            else:
                col_p, col_c = st.columns([3, 1])
                st.session_state.f_price = col_p.number_input(_m("dom_price"), min_value=0.0, value=st.session_state.f_price, step=100.0)
                idx_curr = ["USD", "EUR", "TRY"].index(st.session_state.f_curr) if st.session_state.f_curr in ["USD", "EUR", "TRY"] else 0
                st.session_state.f_curr = col_c.selectbox(_m("currency"), ["USD", "EUR", "TRY"], index=idx_curr)
                st.session_state.f_disc = st.number_input(_m("port_disc"), min_value=0.0, max_value=100.0, value=st.session_state.f_disc)
            
            st.file_uploader(_m("main_img"), type=['png','jpg','jpeg'], key="up_main_img")
        with c2:
            st.markdown(_m("img_prev"))
            up_main = st.session_state.get("up_main_img")
            if up_main: st.image(up_main, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.f_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; height:auto; max-height:300px; object-fit:contain; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
                else: st.markdown(f"<div style='height:200px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border:2px dashed #cbd5e1; border-radius:8px; color:#94a3b8;'>{_m('no_img')}</div>", unsafe_allow_html=True)

    with tab_teknik:
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
        if st.button(_m("add_spec"), use_container_width=True, key="btn_add_spec_row"):
            st.session_state.f_specs.append({"title": "", "detail": "", "img": ""}); st.rerun()

    with tab_donanim:
        opts_avail = get_factory("SELECT id, opt_name, opt_price, opt_image, opt_name_zh FROM options ORDER BY opt_price DESC")
        new_opts = []
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id, o_name, o_price, o_img, o_name_zh = opt
            disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
            
            if user_role == "manufacturer": p_text = ""
            else: p_text = f"(+{o_price:,.0f})" if o_price > 0 else f"({_m('price_wait')})"
                
            is_checked = str(o_id) in st.session_state.f_opts
            
            with chk_cols[idx % 3]:
                with st.container(border=True):
                    img_b64 = get_image_base64(o_img)
                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:80px; object-fit:contain; margin-bottom:10px;"></div>', unsafe_allow_html=True)
                    else: st.markdown(f"<div style='height:80px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:11px; margin-bottom:10px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                    
                    if st.checkbox(f"{disp_name} {p_text}".strip(), value=is_checked, key=f"chk_{o_id}"): 
                        new_opts.append(str(o_id))
        st.session_state.f_opts = new_opts

    st.markdown("---")
    btn_save_text = _m("save_changes") if is_edit else _m("add_sys")
    if st.button(btn_save_text, type="primary", use_container_width=True, key="btn_save_machine"):
        
        if not st.session_state.f_name: st.error(_m("err_name"))
        elif user_role != "manufacturer" and st.session_state.f_price <= 0: st.error(_m("err_price"))
        else:
            with st.spinner(_m("translating")):
                up_main = st.session_state.get("up_main_img")
                if up_main is not None: st.session_state.f_img = process_image(up_main, prefix="machine", size=(1200, 1200), square=False)

                if user_role == "manufacturer":
                    final_name_zh = st.session_state.f_name
                    final_name_tr = auto_translate_to_tr(final_name_zh)
                    
                    spec_strs_zh = []; spec_strs_tr = []
                    for i, sp in enumerate(st.session_state.f_specs):
                        up_spec = st.session_state.get(f"up_spec_{i}")
                        if up_spec is not None: sp["img"] = process_image(up_spec, prefix="spec", size=(400, 400), square=True)
                        if sp["title"].strip() or sp["detail"].strip(): 
                            spec_strs_zh.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                            spec_strs_tr.append(f"{auto_translate_to_tr(sp['title'])}|{auto_translate_to_tr(sp['detail'])}|{sp['img']}")
                            
                    final_specs_zh = " || ".join(spec_strs_zh) + (" || " if spec_strs_zh else "")
                    final_specs_tr = " || ".join(spec_strs_tr) + (" || " if spec_strs_tr else "")
                else:
                    final_name_tr = st.session_state.f_name
                    final_name_zh = st.session_state.get('f_name_zh', '') 
                    
                    spec_strs_tr = []
                    for i, sp in enumerate(st.session_state.f_specs):
                        up_spec = st.session_state.get(f"up_spec_{i}")
                        if up_spec is not None: sp["img"] = process_image(up_spec, prefix="spec", size=(400, 400), square=True)
                        if sp["title"].strip() or sp["detail"].strip(): 
                            spec_strs_tr.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                            
                    final_specs_tr = " || ".join(spec_strs_tr) + (" || " if spec_strs_tr else "")
                    final_specs_zh = st.session_state.get('f_specs_zh', '')
                
                final_opts_str = ",".join(st.session_state.f_opts)
                
                if is_edit:
                    if user_role == "manufacturer":
                        exec_factory("""UPDATE models SET name=?, name_zh=?, category=?, base_price=?, currency=?, specs=?, specs_zh=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?""", (final_name_tr, final_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, final_specs_tr, final_specs_zh, final_opts_str, st.session_state.f_disc, st.session_state.f_img, int(mod_id)))
                    else:
                        exec_factory("""UPDATE models SET name=?, category=?, base_price=?, currency=?, specs=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?""", (final_name_tr, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, final_specs_tr, final_opts_str, st.session_state.f_disc, st.session_state.f_img, int(mod_id)))
                else:
                    exec_factory("""INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path) VALUES (?,?,?,?,?,?,?,?,?,?)""", (final_name_tr, final_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, final_specs_tr, final_specs_zh, final_opts_str, st.session_state.f_disc, st.session_state.f_img))
                
                st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM EKLEME/DÜZENLEME FORMU
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button(_m("back_list"), use_container_width=True, key="btn_back_from_opt"): st.session_state.view_mode = "list"; st.rerun()
    is_edit = (mode == "edit" and opt_id is not None)
    col_title.header(_m("edit_opt_title") if is_edit else _m("new_opt_title"))
    st.markdown("---")

    if not st.session_state.get("opt_form_loaded", False):
        st.session_state.opt_form_loaded = True
        if is_edit:
            r = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image, allow_qty, opt_name_zh, opt_desc_zh FROM options WHERE id=?", (int(opt_id),))[0]
            
            o_name_tr, o_desc_tr = r[0], r[2] if r[2] else ""
            o_name_zh, o_desc_zh = r[5], r[6] if len(r)>6 and r[6] else ""
            
            st.session_state.o_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name_tr
            st.session_state.o_desc = o_desc_zh if user_role == "manufacturer" and o_desc_zh else o_desc_tr
            
            st.session_state.o_price = float(r[1])
            st.session_state.o_img = r[3] if r[3] else ""
            st.session_state.o_allow_qty = bool(r[4] if len(r)>4 and r[4] is not None else 1)
        else:
            st.session_state.o_name, st.session_state.o_price, st.session_state.o_desc, st.session_state.o_img = "", 0.0, "", ""
            st.session_state.o_allow_qty = True

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.o_name = st.text_input(_m("opt_name"), value=st.session_state.o_name)
            
            if user_role == "manufacturer":
                st.warning(_m("opt_price_lock"))
                st.session_state.o_price = st.session_state.get('o_price', 0.0)
            else:
                st.session_state.o_price = st.number_input(_m("opt_price"), min_value=0.0, value=st.session_state.o_price, step=50.0)
            
            st.session_state.o_allow_qty = st.checkbox(_m("allow_qty"), value=st.session_state.o_allow_qty)
            st.session_state.o_desc = st.text_area(_m("opt_desc"), value=st.session_state.o_desc, height=120)
            st.file_uploader(_m("opt_img_up"), type=['png','jpg','jpeg'], key="up_opt_img")
            
        with c2:
            st.markdown(_m("img_prev"))
            up_opt = st.session_state.get("up_opt_img")
            if up_opt: st.image(up_opt, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.o_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

        btn_save_opt_text = _m("save_changes") if is_edit else _m("add_sys")
        if st.button("💾 " + btn_save_opt_text, type="primary", use_container_width=True, key="btn_save_option"):
            
            if not st.session_state.o_name: st.error(_m("err_opt_name"))
            elif user_role != "manufacturer" and st.session_state.o_price <= 0: st.error(_m("err_price"))
            else:
                with st.spinner(_m("translating")):
                    up_opt = st.session_state.get("up_opt_img")
                    if up_opt is not None: st.session_state.o_img = process_image(up_opt, prefix="opt", size=(400, 400), square=True)
                    
                    allow_q = 1 if st.session_state.o_allow_qty else 0
                    
                    if user_role == "manufacturer":
                        final_opt_name_zh = st.session_state.o_name
                        final_opt_desc_zh = st.session_state.o_desc
                        final_opt_name_tr = auto_translate_to_tr(final_opt_name_zh)
                        final_opt_desc_tr = auto_translate_to_tr(final_opt_desc_zh)
                        
                        if is_edit: exec_factory("UPDATE options SET opt_name=?, opt_name_zh=?, opt_desc=?, opt_desc_zh=?, opt_price=?, opt_image=?, allow_qty=? WHERE id=?", (final_opt_name_tr, final_opt_name_zh, final_opt_desc_tr, final_opt_desc_zh, st.session_state.o_price, st.session_state.o_img, allow_q, int(opt_id)))
                        else: exec_factory("INSERT INTO options (opt_name, opt_name_zh, opt_desc, opt_desc_zh, opt_price, opt_image, allow_qty) VALUES (?,?,?,?,?,?,?)", (final_opt_name_tr, final_opt_name_zh, final_opt_desc_tr, final_opt_desc_zh, st.session_state.o_price, st.session_state.o_img, allow_q))
                    else:
                        final_opt_name_tr = st.session_state.o_name
                        final_opt_desc_tr = st.session_state.o_desc
                        
                        if is_edit: exec_factory("UPDATE options SET opt_name=?, opt_desc=?, opt_price=?, opt_image=?, allow_qty=? WHERE id=?", (final_opt_name_tr, final_opt_desc_tr, st.session_state.o_price, st.session_state.o_img, allow_q, int(opt_id)))
                        else: exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, allow_qty) VALUES (?,?,?,?,?)", (final_opt_name_tr, final_opt_desc_tr, st.session_state.o_price, st.session_state.o_img, allow_q))
                        
                    st.session_state.view_mode = "list"; st.rerun()
