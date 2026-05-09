import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image
import json

# =====================================================================
# 🛡️ GÜVENLİ VERİ OKUMA VE TABLO ONARIM MOTORU
# =====================================================================
def get_safe(row, index, default=""):
    """Eksik sütun gelse bile çökmesini engelleyen çelik zırh"""
    if row and isinstance(row, (list, tuple)) and len(row) > index:
        return row[index] if row[index] is not None else default
    return default

def repair_model_db():
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        conn.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)""")
        if not conn.execute("SELECT * FROM categories").fetchall():
            conn.execute("INSERT OR IGNORE INTO categories (name) VALUES ('CNC İşleme Merkezleri')")
            conn.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Diğer Makinalar')")
            
        conn.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', category TEXT DEFAULT 'Diğer Makinalar')""")
        try: conn.execute("ALTER TABLE models ADD COLUMN name_zh TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE models ADD COLUMN specs_zh TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE models ADD COLUMN compatible_options TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE models ADD COLUMN port_discount REAL DEFAULT 0.0")
        except: pass
        try: conn.execute("ALTER TABLE models ADD COLUMN user_id INTEGER DEFAULT 1")
        except: pass

        conn.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)""")
        try: conn.execute("ALTER TABLE options ADD COLUMN opt_name_zh TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN opt_desc TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN opt_desc_zh TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN allow_qty INTEGER DEFAULT 1")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN opt_suffix TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN opt_variant_image TEXT DEFAULT ''")
        except: pass
        try: conn.execute("ALTER TABLE options ADD COLUMN user_id INTEGER DEFAULT 1")
        except: pass

        conn.commit(); conn.close()
    except Exception as e:
        print(f"Oto-Tamir Hatası: {e}")

repair_model_db()

# =====================================================================
# 🛡️ YEDEKLEME VE KASA MOTORU (MANUFACTURER VAULT)
# =====================================================================
def sync_to_vault(table, data_dict, operation="upsert", item_id=None):
    try:
        conn = sqlite3.connect('manufacturer_vault.db', check_same_thread=False)
        c = conn.cursor()
        
        if table == "models":
            c.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY, name TEXT, name_zh TEXT, category TEXT, base_price REAL, currency TEXT, specs TEXT, specs_zh TEXT, compatible_options TEXT, port_discount REAL, image_path TEXT, user_id INTEGER)""")
            if operation == "upsert":
                cols = ", ".join(data_dict.keys()); placeholders = ", ".join(["?"] * len(data_dict)); values = tuple(data_dict.values())
                if item_id: c.execute(f"DELETE FROM models WHERE id=?", (item_id,))
                c.execute(f"INSERT INTO models ({cols}) VALUES ({placeholders})", values)
            elif operation == "delete":
                c.execute("DELETE FROM models WHERE id=?", (item_id,))
                
        elif table == "options":
            c.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY, opt_name TEXT, opt_name_zh TEXT, opt_desc TEXT, opt_desc_zh TEXT, opt_price REAL, opt_image TEXT, allow_qty INTEGER, opt_suffix TEXT DEFAULT '', opt_variant_image TEXT DEFAULT '', user_id INTEGER)""")
            try: c.execute("ALTER TABLE options ADD COLUMN opt_suffix TEXT DEFAULT ''")
            except: pass
            try: c.execute("ALTER TABLE options ADD COLUMN opt_variant_image TEXT DEFAULT ''")
            except: pass

            if operation == "upsert":
                cols = ", ".join(data_dict.keys()); placeholders = ", ".join(["?"] * len(data_dict)); values = tuple(data_dict.values())
                if item_id: c.execute(f"DELETE FROM options WHERE id=?", (item_id,))
                c.execute(f"INSERT INTO options ({cols}) VALUES ({placeholders})", values)
            elif operation == "delete":
                c.execute("DELETE FROM options WHERE id=?", (item_id,))
                
        conn.commit(); conn.close()
    except Exception as e: print(f"Vault Sync Error: {e}")

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
        "translating": "🤖 Metinler otomatik olarak Türkçeye çevriliyor...",
        "opt_suffix": "Model Adı Eki (Suffix)", "opt_v_img": "Seçilince Değişecek Ana Resim", 
        "opt_suffix_help": "💡 Örn: 'L' yazarsanız, bayi bu donanımı seçtiğinde makine isminin sonuna bu harf otomatik eklenir."
    }
}
def _m(key): 
    lang = st.session_state.get("language", st.session_state.get("lang", "tr"))
    return DICT_MODEL.get(str(lang).lower(), DICT_MODEL["tr"]).get(key, key)

# =====================================================================
# VERİTABANI BAĞLANTILARI
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
        return res
    except Exception as e: 
        return [] # Hata fırlatma, boş döndür (Güvenlik Kalkanı)

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
        return True
    except Exception as e:
        st.error(f"Veritabanı Yazma Hatası: {e}")
        return False

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
        
        # GÜVENLİ VERİ ÇEKİMİ (Sütun yoksa eski sorguya düşer)
        q_ext = " WHERE user_id=?" if user_role == "manufacturer" else ""
        p_ext = (user_id,) if user_role == "manufacturer" else ()
        
        mods = get_factory("SELECT id, name, category, base_price, currency, image_path, name_zh FROM models" + q_ext + " ORDER BY category ASC, name ASC", p_ext)
        if not mods: # Eğer name_zh sütunu yoksa ve hata verdiyse eski sistem sorgusunu çalıştır
            mods = get_factory("SELECT id, name, category, base_price, currency, image_path FROM models" + q_ext + " ORDER BY category ASC, name ASC", p_ext)
            if mods: mods = [(*m, "") for m in mods] # Boş name_zh ekle
            
        if mods:
            safe_mods = [[get_safe(m,0,0), get_safe(m,1,""), get_safe(m,2,"Diğer Makinalar"), get_safe(m,3,0.0), get_safe(m,4,"USD"), get_safe(m,5,""), get_safe(m,6,"")] for m in mods]
            df = pd.DataFrame(safe_mods, columns=["id", "name", "category", "price", "currency", "image", "name_zh"])
            for cat in df['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df[df['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                display_name = row['name_zh'] if user_role == "manufacturer" and row['name_zh'] else row['name']
                                
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{display_name}'>{display_name}</h4>", unsafe_allow_html=True)
                                    
                                    if user_role == "manufacturer": st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('no_auth_price')}</div>", unsafe_allow_html=True)
                                    else:
                                        if row['price'] > 0: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                        else: st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('price_wait')}</div>", unsafe_allow_html=True)
                                        
                                    bc1, bc2, bc3 = st.columns(3)
                                    if bc1.button(_m("btn_edit"), key=f"me_{row['id']}", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']; st.session_state.form_loaded = False; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if bc2.button(_m("btn_copy"), key=f"mc_{row['id']}", use_container_width=True):
                                        st.warning("Kopyalama yapmadan önce düzenleme modunda kontrol edin.")
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
        
        # GÜVENLİ DONANIM ÇEKİMİ
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image, opt_name_zh, opt_suffix, opt_variant_image FROM options" + q_ext + " ORDER BY id DESC", p_ext)
        if not opts:
            opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image FROM options" + q_ext + " ORDER BY id DESC", p_ext)
            if opts: opts = [(*o, "", "", "") for o in opts]
            
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(opts):
                        row_opt = opts[i+j]
                        o_id = get_safe(row_opt, 0, 0); o_name = get_safe(row_opt, 1, "Bilinmeyen")
                        o_price = get_safe(row_opt, 2, 0.0); o_desc = get_safe(row_opt, 3, "")
                        o_img = get_safe(row_opt, 4, ""); o_name_zh = get_safe(row_opt, 5, "")
                        o_suffix = get_safe(row_opt, 6, ""); o_var_img = get_safe(row_opt, 7, "")
                        
                        disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                            else: st.markdown(f"<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<b>{disp_name}</b>", unsafe_allow_html=True)
                            if o_suffix or o_var_img:
                                st.markdown(f"<div style='font-size:11px; color:#2563eb; font-weight:bold; margin-bottom:5px;'>✨ Akıllı Varyasyon</div>", unsafe_allow_html=True)
                            
                            if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                            else: st.markdown(f"<span style='color:#ea580c; font-weight:bold;'>+{o_price:,.0f} USD</span>", unsafe_allow_html=True)
                            
                            bc1, bc2, bc3 = st.columns(3)
                            if bc1.button(_m("btn_edit"), key=f"oe_{o_id}", use_container_width=True):
                                st.session_state.edit_opt_id = o_id; st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_edit"; st.rerun()
                            if bc2.button(_m("btn_copy"), key=f"oc_{o_id}", use_container_width=True):
                                st.warning("Kopyalama yapmadan önce düzenleme modunda kontrol edin.")
                            if bc3.button(_m("btn_del"), key=f"od_{o_id}", use_container_width=True):
                                exec_factory("DELETE FROM options WHERE id=?", (o_id,))
                                if user_role == "manufacturer": sync_to_vault("options", {}, "delete", o_id)
                                st.rerun()
        else: st.info(_m("no_opt"))

    with tab_cat:
        st.subheader(_m("cat_mng"))
        if user_role == "admin":
            with st.form("new_cat_form", clear_on_submit=True):
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
# MAKİNE (MODEL) DÜZENLEME FORMU
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
            # GÜVENLİ ÇEKİM
            r_list = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options, name_zh, specs_zh FROM models WHERE id=?", (mod_id,))
            if not r_list:
                r_list = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options FROM models WHERE id=?", (mod_id,))
                if r_list: r_list = [(*r_list[0], "", "")]
            
            if not r_list:
                st.error("Kayıt bulunamadı. Lütfen listeye dönün."); st.stop()
                
            r = r_list[0]
            st.session_state.f_name = get_safe(r, 8, "") if user_role == "manufacturer" and get_safe(r, 8, "") else get_safe(r, 0, "")
            st.session_state.f_price, st.session_state.f_curr, st.session_state.f_cat = get_safe(r, 1, 0.0), get_safe(r, 2, "USD"), get_safe(r, 3, st.session_state.f_cats[0])
            st.session_state.f_disc, st.session_state.f_img = get_safe(r, 4, 0.0), get_safe(r, 5, "")
            st.session_state.f_opts = [x.strip() for x in str(get_safe(r, 7, "")).split(",") if x.strip()]
            
            s_list = []
            target_specs = get_safe(r, 9, "") if user_role == "manufacturer" and get_safe(r, 9, "") else get_safe(r, 6, "")
            if target_specs:
                for item in str(target_specs).split("||"):
                    if item.strip():
                        p = item.split("|")
                        s_list.append({"title": p[0].strip() if len(p)>0 else "", "detail": p[1].strip() if len(p)>1 else "", "img": p[2].strip() if len(p)>2 else ""})
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
        user_id = st.session_state.get("user_id", 1)
        opts_avail = get_factory("SELECT id, opt_name, opt_price, opt_image, opt_name_zh FROM options WHERE user_id=? ORDER BY opt_price DESC", (user_id,)) if user_role == "manufacturer" else get_factory("SELECT id, opt_name, opt_price, opt_image, opt_name_zh FROM options ORDER BY opt_price DESC")
        
        new_opts = []
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id = get_safe(opt, 0, 0)
            o_name = get_safe(opt, 1, "Bilinmeyen")
            o_price = get_safe(opt, 2, 0.0)
            o_img = get_safe(opt, 3, "")
            o_name_zh = get_safe(opt, 4, "")
            
            disp_name = o_name_zh if user_role == "manufacturer" and o_name_zh else o_name
            p_text = "" if user_role == "manufacturer" else (f"(+{o_price:,.0f})" if o_price > 0 else f"({_m('price_wait')})")
            
            with chk_cols[idx % 3]:
                with st.container(border=True):
                    img_b64 = get_image_base64(o_img)
                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:80px; object-fit:contain; margin-bottom:10px;"></div>', unsafe_allow_html=True)
                    if st.checkbox(f"{disp_name} {p_text}".strip(), value=str(o_id) in st.session_state.f_opts, key=f"chk_{o_id}"): new_opts.append(str(o_id))
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

                if user_role == "manufacturer":
                    f_name_zh = st.session_state.f_name; f_name_tr = auto_translate_to_tr(f_name_zh)
                    s_zh, s_tr = [], []
                    for i, sp in enumerate(st.session_state.f_specs):
                        up_s = st.session_state.get(f"up_spec_{i}")
                        if up_s is not None: sp["img"] = process_image(up_s, prefix="spec", size=(400, 400), square=True)
                        if sp["title"].strip() or sp["detail"].strip(): 
                            s_zh.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                            s_tr.append(f"{auto_translate_to_tr(sp['title'])}|{auto_translate_to_tr(sp['detail'])}|{sp['img']}")
                    specs_zh = " || ".join(s_zh) + (" || " if s_zh else "")
                    specs_tr = " || ".join(s_tr) + (" || " if s_tr else "")
                else:
                    f_name_tr = st.session_state.f_name; f_name_zh = st.session_state.get('f_name_zh', '')
                    s_tr = []
                    for i, sp in enumerate(st.session_state.f_specs):
                        up_s = st.session_state.get(f"up_spec_{i}")
                        if up_s is not None: sp["img"] = process_image(up_s, prefix="spec", size=(400, 400), square=True)
                        if sp["title"].strip() or sp["detail"].strip(): s_tr.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                    specs_tr = " || ".join(s_tr) + (" || " if s_tr else "")
                    specs_zh = st.session_state.get('f_specs_zh', '')
                
                opt_str = ",".join(st.session_state.f_opts)
                data_dict = {"name": f_name_tr, "name_zh": f_name_zh, "category": st.session_state.f_cat, "base_price": st.session_state.f_price, "currency": st.session_state.f_curr, "specs": specs_tr, "specs_zh": specs_zh, "compatible_options": opt_str, "port_discount": st.session_state.f_disc, "image_path": st.session_state.f_img, "user_id": uid}
                
                if is_edit:
                    success = exec_factory("UPDATE models SET name=?, name_zh=?, category=?, base_price=?, currency=?, specs=?, specs_zh=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?", (f_name_tr, f_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, specs_zh, opt_str, st.session_state.f_disc, st.session_state.f_img, mod_id))
                    if success and user_role == "manufacturer": 
                        data_dict["id"] = mod_id
                        sync_to_vault("models", data_dict, "upsert", mod_id)
                else:
                    success = exec_factory("INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f_name_tr, f_name_zh, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, specs_tr, specs_zh, opt_str, st.session_state.f_disc, st.session_state.f_img, uid))
                    if success and user_role == "manufacturer":
                        new_id_res = get_factory("SELECT id FROM models ORDER BY id DESC LIMIT 1")
                        if new_id_res:
                            new_id = new_id_res[0][0]
                            data_dict["id"] = new_id
                            sync_to_vault("models", data_dict, "upsert", new_id)
                
                st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM FORMU (YENİ AKILLI VARYASYON EKLENDİ)
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
            # GÜVENLİ ÇEKİM
            r_list = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image, allow_qty, opt_name_zh, opt_desc_zh, opt_suffix, opt_variant_image FROM options WHERE id=?", (opt_id,))
            if not r_list:
                r_list = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image, allow_qty FROM options WHERE id=?", (opt_id,))
                if r_list: r_list = [(*r_list[0], "", "", "", "")]
                
            if not r_list:
                st.error("Kayıt bulunamadı. Lütfen listeye dönün."); st.stop()
                
            r = r_list[0]
            st.session_state.o_name = get_safe(r, 5, "") if user_role == "manufacturer" and get_safe(r, 5, "") else get_safe(r, 0, "")
            st.session_state.o_desc = get_safe(r, 6, "") if user_role == "manufacturer" and get_safe(r, 6, "") else get_safe(r, 2, "")
            st.session_state.o_price, st.session_state.o_img, st.session_state.o_qty = get_safe(r, 1, 0.0), get_safe(r, 3, ""), bool(get_safe(r, 4, 1))
            st.session_state.o_suffix = get_safe(r, 7, "")
            st.session_state.o_v_img = get_safe(r, 8, "")
        else:
            st.session_state.o_name, st.session_state.o_price, st.session_state.o_desc, st.session_state.o_img, st.session_state.o_qty = "", 0.0, "", "", True
            st.session_state.o_suffix, st.session_state.o_v_img = "", ""

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.o_name = st.text_input(_m("opt_name"), value=st.session_state.o_name)
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            v_col1, v_col2 = st.columns(2)
            st.session_state.o_suffix = v_col1.text_input(_m("opt_suffix"), value=st.session_state.o_suffix, placeholder="Örn: L, -PRO")
            v_col1.info(_m("opt_suffix_help"))
            v_col2.file_uploader(_m("opt_v_img"), type=['png','jpg','jpeg'], key="up_v_img")
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            
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
                    
                    up_var = st.session_state.get("up_v_img")
                    if up_var: st.session_state.o_v_img = process_image(up_var, "variant_machine", size=(1200, 1200), square=False)
                    
                    allow_q = 1 if st.session_state.o_qty else 0
                    
                    if user_role == "manufacturer":
                        o_n_zh = st.session_state.o_name; o_n_tr = auto_translate_to_tr(o_n_zh)
                        o_d_zh = st.session_state.o_desc; o_d_tr = auto_translate_to_tr(o_d_zh)
                        
                        data_opt = {"opt_name": o_n_tr, "opt_name_zh": o_n_zh, "opt_desc": o_d_tr, "opt_desc_zh": o_d_zh, "opt_price": st.session_state.o_price, "opt_image": st.session_state.o_img, "allow_qty": allow_q, "opt_suffix": st.session_state.o_suffix, "opt_variant_image": st.session_state.o_v_img, "user_id": uid}
                        
                        if is_edit: 
                            success = exec_factory("UPDATE options SET opt_name=?, opt_name_zh=?, opt_desc=?, opt_desc_zh=?, opt_price=?, opt_image=?, allow_qty=?, opt_suffix=?, opt_variant_image=? WHERE id=?", (o_n_tr, o_n_zh, o_d_tr, o_d_zh, st.session_state.o_price, st.session_state.o_img, allow_q, st.session_state.o_suffix, st.session_state.o_v_img, opt_id))
                            if success:
                                data_opt["id"] = opt_id
                                sync_to_vault("options", data_opt, "upsert", opt_id)
                        else: 
                            success = exec_factory("INSERT INTO options (opt_name, opt_name_zh, opt_desc, opt_desc_zh, opt_price, opt_image, allow_qty, opt_suffix, opt_variant_image, user_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (o_n_tr, o_n_zh, o_d_tr, o_d_zh, st.session_state.o_price, st.session_state.o_img, allow_q, st.session_state.o_suffix, st.session_state.o_v_img, uid))
                            if success:
                                new_id_res = get_factory("SELECT id FROM options ORDER BY id DESC LIMIT 1")
                                if new_id_res:
                                    new_id = new_id_res[0][0]
                                    data_opt["id"] = new_id
                                    sync_to_vault("options", data_opt, "upsert", new_id)
                    else:
                        o_n_tr = st.session_state.o_name; o_d_tr = st.session_state.o_desc
                        if is_edit: exec_factory("UPDATE options SET opt_name=?, opt_desc=?, opt_price=?, opt_image=?, allow_qty=?, opt_suffix=?, opt_variant_image=? WHERE id=?", (o_n_tr, o_d_tr, st.session_state.o_price, st.session_state.o_img, allow_q, st.session_state.o_suffix, st.session_state.o_v_img, opt_id))
                        else: exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, allow_qty, opt_suffix, opt_variant_image, user_id) VALUES (?,?,?,?,?,?,?,?)", (o_n_tr, o_d_tr, st.session_state.o_price, st.session_state.o_img, allow_q, st.session_state.o_suffix, st.session_state.o_v_img, uid))
                    
                    st.session_state.view_mode = "list"; st.rerun()
