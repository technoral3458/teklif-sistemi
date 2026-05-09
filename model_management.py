import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image

# =====================================================================
# 🛠️ DİNAMİK VE YOK EDİLEMEZ VERİTABANI MOTORU (DICTIONARY MİMARİSİ)
# =====================================================================
def db_query(query, params=()):
    """Sıra numarasıyla değil, isimle veri çeken zırhlı motor."""
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row # Verileri liste değil, sözlük olarak alır!
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return [dict(row) for row in res] # Artık IndexError yok!
    except Exception as e:
        # Eğer bir sütun eksikse hatayı yutar, boş döner.
        return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
        return True
    except Exception as e:
        st.error(f"Kayıt Hatası (Lütfen sayfayı yenileyin): {e}")
        return False

# EKSİK SÜTUNLARI ZORLA OLUŞTURMA MOTORU
def enforce_column(table, column, def_val):
    conn = sqlite3.connect('factory_data.db')
    cols = [x[1] for x in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        try: conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {def_val}")
        except: pass
    conn.commit(); conn.close()

def repair_model_db():
    conn = sqlite3.connect('factory_data.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)""")
    if not conn.execute("SELECT * FROM categories").fetchall():
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES ('CNC İşleme Merkezleri')")
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Diğer Makinalar')")
    conn.execute("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', category TEXT DEFAULT 'Diğer Makinalar')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)""")
    conn.commit(); conn.close()

    # Zorunlu yeni sütunları tek tek garantile
    enforce_column("models", "name_zh", "TEXT DEFAULT ''")
    enforce_column("models", "specs_zh", "TEXT DEFAULT ''")
    enforce_column("models", "compatible_options", "TEXT DEFAULT ''")
    enforce_column("models", "port_discount", "REAL DEFAULT 0.0")
    enforce_column("models", "user_id", "INTEGER DEFAULT 1")
    enforce_column("models", "gallery_images", "TEXT DEFAULT ''")

    enforce_column("options", "opt_name_zh", "TEXT DEFAULT ''")
    enforce_column("options", "opt_desc", "TEXT DEFAULT ''")
    enforce_column("options", "opt_desc_zh", "TEXT DEFAULT ''")
    enforce_column("options", "allow_qty", "INTEGER DEFAULT 1")
    enforce_column("options", "opt_suffix", "TEXT DEFAULT ''") # AKILLI VARYASYON
    enforce_column("options", "opt_variant_image", "TEXT DEFAULT ''") # AKILLI VARYASYON
    enforce_column("options", "user_id", "INTEGER DEFAULT 1")

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
            elif operation == "delete": c.execute("DELETE FROM models WHERE id=?", (item_id,))
        elif table == "options":
            c.execute("""CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY, opt_name TEXT, opt_name_zh TEXT, opt_desc TEXT, opt_desc_zh TEXT, opt_price REAL, opt_image TEXT, allow_qty INTEGER, opt_suffix TEXT DEFAULT '', opt_variant_image TEXT DEFAULT '', user_id INTEGER)""")
            cols_info = [col[1] for col in c.execute("PRAGMA table_info(options)").fetchall()]
            if "opt_suffix" not in cols_info: c.execute("ALTER TABLE options ADD COLUMN opt_suffix TEXT DEFAULT ''")
            if "opt_variant_image" not in cols_info: c.execute("ALTER TABLE options ADD COLUMN opt_variant_image TEXT DEFAULT ''")
            if operation == "upsert":
                cols = ", ".join(data_dict.keys()); placeholders = ", ".join(["?"] * len(data_dict)); values = tuple(data_dict.values())
                if item_id: c.execute(f"DELETE FROM options WHERE id=?", (item_id,))
                c.execute(f"INSERT INTO options ({cols}) VALUES ({placeholders})", values)
            elif operation == "delete": c.execute("DELETE FROM options WHERE id=?", (item_id,))
        conn.commit(); conn.close()
    except: pass

# =====================================================================
# 🤖 YAPAY ZEKA ÇEVİRİ MOTORU
# =====================================================================
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_READY = True
except ImportError:
    TRANSLATOR_READY = False

def auto_translate_to_tr(text):
    if not TRANSLATOR_READY or not text or not str(text).strip(): return text
    try: return GoogleTranslator(source='auto', target='tr').translate(str(text))
    except: return text

# =====================================================================
# RESİM YARDIMCILARI
# =====================================================================
def get_image_base64(img_path):
    if not img_path: return ""
    paths = [img_path, f"images/{img_path}"]
    for p in paths:
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
            img = img.crop(((width - new_size)/2, (height - new_size)/2, (width + new_size)/2, (height + new_size)/2)).resize(size, Image.Resampling.LANCZOS)
        else: img.thumbnail(size, Image.Resampling.LANCZOS)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
        img.save(os.path.join("images", filename), "JPEG", quality=95)
        return filename
    except: return ""

# =====================================================================
# DİL SÖZLÜĞÜ
# =====================================================================
DICT_MODEL = {
    "tr": {
        "m_title": "📦 Fabrika Veritabanı", "t_mod": "📦 Modeller", "t_opt": "⚙️ Donanımlar", "t_cat": "📂 Kategoriler",
        "reg_mach": "Makineler", "add_mach": "➕ YENİ MAKİNE", "no_img": "Görsel Yok", "price_wait": "Fiyat Bekleniyor", "no_auth_price": "🔒 Fiyat Gizli",
        "opt_showcase": "Donanımlar", "add_opt": "➕ YENİ DONANIM", "cat_mng": "Kategori Yönetimi", "new_cat": "Kategori Ekle",
        "back_list": "🔙 Listeye Dön", "edit_mach": "✏️ Makine Düzenle", "new_mach": "✨ Makine Ekle",
        "tab_gen": "📄 Genel", "tab_tech": "⚙️ Teknik", "tab_comp": "🔌 Donanımlar",
        "m_name": "Makine Adı *", "m_cat": "Kategori", "dom_price": "Fiyat *", "currency": "Para Birimi", "port_disc": "İskonto (%)",
        "main_img": "Ana Görsel", "spec_title": "Başlık", "spec_det": "Detay", "choose_img": "Resim",
        "add_spec": "➕ ÖZELLİK EKLE", "save_changes": "💾 KAYDET", "add_sys": "💾 EKLE",
        "edit_opt_title": "✏️ Donanım Düzenle", "new_opt_title": "✨ Donanım Ekle",
        "opt_name": "Donanım Adı *", "opt_price": "Fiyat *", "allow_qty": "Adet seçilebilir", "opt_desc": "Açıklama", "opt_img_up": "Görsel",
        "opt_suffix": "Model Adı Eki (Örn: L)", "opt_v_img": "Varyasyon Ana Resmi"
    }
}
def _m(key): 
    lang = st.session_state.get("lang", "tr")
    return DICT_MODEL.get(str(lang).lower(), DICT_MODEL["tr"]).get(key, key)

# =====================================================================
# ANA YÖNETİM MODÜLÜ
# =====================================================================
def show_product_management():
    if "view_mode" not in st.session_state: st.session_state.view_mode = "list"
    user_role = st.session_state.get("user_role", "dealer")
    
    if st.session_state.view_mode == "list": show_list_view(user_role)
    elif st.session_state.view_mode == "mod_add": show_form_view("add", None, user_role)
    elif st.session_state.view_mode == "mod_edit": show_form_view("edit", st.session_state.get("edit_mod_id"), user_role)
    elif st.session_state.view_mode == "opt_add": show_opt_form_view("add", None, user_role)
    elif st.session_state.view_mode == "opt_edit": show_opt_form_view("edit", st.session_state.get("edit_opt_id"), user_role)

# =====================================================================
# LİSTELEME EKRANI
# =====================================================================
def show_list_view(user_role):
    st.header(_m("m_title"))
    tab_mod, tab_opt, tab_cat = st.tabs([_m("t_mod"), _m("t_opt"), _m("t_cat")])
    user_id = st.session_state.get("user_id", 1)
    
    with tab_mod:
        c1, c2 = st.columns([5, 3])
        c1.subheader(_m("reg_mach"))
        if c2.button(_m("add_mach"), type="primary", use_container_width=True):
            st.session_state.view_mode = "mod_add"; st.rerun()

        q_ext = " WHERE user_id=?" if user_role == "manufacturer" else ""
        p_ext = (user_id,) if user_role == "manufacturer" else ()
        
        mods = db_query("SELECT * FROM models" + q_ext + " ORDER BY category ASC, name ASC", p_ext)
            
        if mods:
            df = pd.DataFrame(mods)
            for cat in df['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df[df['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                d_name = row.get('name_zh') if user_role == "manufacturer" and row.get('name_zh') else row.get('name')
                                
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row.get('image_path'))
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{d_name}</h4>", unsafe_allow_html=True)
                                    if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                                    else: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px;'>{row.get('base_price',0):,.2f} {row.get('currency','USD')}</div>", unsafe_allow_html=True)
                                        
                                    bc1, bc2 = st.columns(2)
                                    if bc1.button("✏️", key=f"me_{row['id']}", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if bc2.button("🗑️", key=f"md_{row['id']}", use_container_width=True):
                                        exec_factory("DELETE FROM models WHERE id=?", (row['id'],))
                                        if user_role == "manufacturer": sync_to_vault("models", {}, "delete", row['id'])
                                        st.rerun()
        else: st.info("Sistemde makine yok.")

    with tab_opt:
        c1, c2 = st.columns([5, 3])
        c1.subheader(_m("opt_showcase"))
        if c2.button(_m("add_opt"), type="primary", use_container_width=True):
            st.session_state.view_mode = "opt_add"; st.rerun()
        
        opts = db_query("SELECT * FROM options" + q_ext + " ORDER BY id DESC", p_ext)
            
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(opts):
                        o = opts[i+j]
                        d_name = o.get('opt_name_zh') if user_role == "manufacturer" and o.get('opt_name_zh') else o.get('opt_name')
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o.get('opt_image'))
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                            else: st.markdown(f"<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<b>{d_name}</b>", unsafe_allow_html=True)
                            if o.get('opt_suffix') or o.get('opt_variant_image'):
                                st.markdown(f"<div style='font-size:11px; color:#2563eb; font-weight:bold;'>✨ Varyasyon</div>", unsafe_allow_html=True)
                            
                            if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                            else: st.markdown(f"<span style='color:#ea580c; font-weight:bold;'>+{o.get('opt_price',0):,.0f} USD</span>", unsafe_allow_html=True)
                            
                            bc1, bc2 = st.columns(2)
                            if bc1.button("✏️", key=f"oe_{o['id']}", use_container_width=True):
                                st.session_state.edit_opt_id = o['id']; st.session_state.view_mode = "opt_edit"; st.rerun()
                            if bc2.button("🗑️", key=f"od_{o['id']}", use_container_width=True):
                                exec_factory("DELETE FROM options WHERE id=?", (o['id'],))
                                if user_role == "manufacturer": sync_to_vault("options", {}, "delete", o['id'])
                                st.rerun()
        else: st.info("Sistemde donanım yok.")

    with tab_cat:
        with st.form("new_cat_form", clear_on_submit=True):
            n_cat = st.text_input(_m("new_cat"))
            if st.form_submit_button(_m("btn_add")) and n_cat.strip():
                exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat.strip(),)); st.rerun()
        cats = db_query("SELECT * FROM categories ORDER BY name ASC")
        for c in cats:
            st.write(f"📁 {c.get('name')}")

# =====================================================================
# MAKİNE (MODEL) DÜZENLEME FORMU - %100 ÇÖKMEYE KARŞI KORUMALI
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    if st.button(_m("back_list")): st.session_state.view_mode = "list"; st.rerun()
    st.header(_m("edit_mach") if mode == "edit" else _m("new_mach"))
    st.markdown("---")

    cats_db = [c.get('name') for c in db_query("SELECT name FROM categories")]
    if not cats_db: cats_db = ["Diğer Makinalar"]

    r = {}
    if mode == "edit" and mod_id:
        r_list = db_query("SELECT * FROM models WHERE id=?", (mod_id,))
        if not r_list: st.error("Kayıt veritabanında bulunamadı."); st.stop()
        r = r_list[0] # r artık bir Sözlük (Dictionary)!

    # DICTIONARY KULLANIMI: ASLA INDEXERROR VERMEZ!
    f_name = r.get("name_zh", "") if user_role == "manufacturer" and r.get("name_zh") else r.get("name", "")
    f_price = r.get("base_price", 0.0)
    f_curr = r.get("currency", "USD")
    f_cat = r.get("category", cats_db[0])
    f_disc = r.get("port_discount", 0.0)
    f_img = r.get("image_path", "")
    f_opts_raw = str(r.get("compatible_options", ""))
    f_opts = [x.strip() for x in f_opts_raw.split(",") if x.strip()]
    
    s_list = []
    t_specs = str(r.get("specs_zh", "") if user_role == "manufacturer" and r.get("specs_zh") else r.get("specs", ""))
    if t_specs:
        for item in t_specs.split("||"):
            if item.strip():
                p = item.split("|")
                s_list.append({"title": get_safe(p,0,""), "detail": get_safe(p,1,""), "img": get_safe(p,2,"")})
    if not s_list: s_list = [{"title": "", "detail": "", "img": ""}]
    
    if "f_specs" not in st.session_state or st.session_state.get("cur_mod_id") != mod_id:
        st.session_state.f_specs = s_list
        st.session_state.cur_mod_id = mod_id

    t1, t2, t3 = st.tabs([_m("tab_gen"), _m("tab_tech"), _m("tab_comp")])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        with c1:
            new_name = st.text_input(_m("m_name"), value=f_name)
            new_cat = st.selectbox(_m("m_cat"), cats_db, index=cats_db.index(f_cat) if f_cat in cats_db else 0)
            
            cp1, cp2 = st.columns([3, 1])
            new_price = cp1.number_input(_m("dom_price"), value=f_price, step=100.0)
            new_curr = cp2.selectbox(_m("currency"), ["USD", "EUR", "TRY"], index=["USD", "EUR", "TRY"].index(f_curr) if f_curr in ["USD", "EUR", "TRY"] else 0)
            new_disc = st.number_input(_m("port_disc"), value=f_disc, max_value=100.0)
            new_img_up = st.file_uploader(_m("main_img"), type=['png','jpg','jpeg'])
            
        with c2:
            st.markdown(_m("img_prev"))
            if new_img_up: st.image(new_img_up, use_container_width=True)
            else:
                prev_img = get_image_base64(f_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

    with t2:
        for i in range(len(st.session_state.f_specs)):
            with st.container(border=True):
                col_t, col_d, col_i, col_x = st.columns([3, 4, 3, 1], vertical_alignment="bottom")
                st.session_state.f_specs[i]["title"] = col_t.text_input(_m("spec_title"), value=st.session_state.f_specs[i]["title"], key=f"t_{i}")
                st.session_state.f_specs[i]["detail"] = col_d.text_input(_m("spec_det"), value=st.session_state.f_specs[i]["detail"], key=f"d_{i}")
                
                with col_i:
                    c_prev, c_up = st.columns([1, 2], vertical_alignment="bottom")
                    up_spec = st.session_state.get(f"up_spec_{i}")
                    if up_spec: c_prev.image(up_spec, width=40)
                    else:
                        cur_img = st.session_state.f_specs[i].get("img", "")
                        if cur_img:
                            b64 = get_image_base64(cur_img)
                            if b64: c_prev.markdown(f'<img src="{b64}" style="width:40px; height:40px; border-radius:4px;">', unsafe_allow_html=True)
                    c_up.file_uploader(_m("choose_img"), type=['png','jpg','jpeg'], key=f"up_spec_{i}", label_visibility="collapsed")
                    
                if col_x.button("❌", key=f"del_spec_{i}", use_container_width=True): 
                    st.session_state.f_specs.pop(i); st.rerun()
                    
        if st.button(_m("add_spec"), use_container_width=True):
            st.session_state.f_specs.append({"title": "", "detail": "", "img": ""}); st.rerun()

    with t3:
        opts_avail = db_query("SELECT * FROM options ORDER BY opt_price DESC")
        sel_opts = []
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id = str(opt.get("id"))
            o_name = opt.get("opt_name_zh") if user_role == "manufacturer" and opt.get("opt_name_zh") else opt.get("opt_name", "Bilinmeyen")
            o_price = opt.get("opt_price", 0.0)
            
            with chk_cols[idx % 3]:
                with st.container(border=True):
                    img_b64 = get_image_base64(opt.get("opt_image"))
                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:80px; object-fit:contain;"></div>', unsafe_allow_html=True)
                    if st.checkbox(f"{o_name} (+{o_price:,.0f})", value=(o_id in f_opts), key=f"chk_{o_id}"): sel_opts.append(o_id)

    st.markdown("---")
    if st.button(_m("save_changes"), type="primary", use_container_width=True):
        if not new_name: st.error(_m("err_name"))
        else:
            final_img = f_img
            if new_img_up: final_img = process_image(new_img_up, "machine", square=False)
            uid = st.session_state.get("user_id", 1)

            n_zh = new_name if user_role == "manufacturer" else r.get('name_zh', '')
            n_tr = auto_translate_to_tr(new_name) if user_role == "manufacturer" else new_name
            
            s_zh, s_tr = [], []
            for i, sp in enumerate(st.session_state.f_specs):
                up_s = st.session_state.get(f"up_spec_{i}")
                if up_s is not None: sp["img"] = process_image(up_s, "spec", square=True)
                if sp["title"].strip() or sp["detail"].strip(): 
                    if user_role == "manufacturer":
                        s_zh.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                        s_tr.append(f"{auto_translate_to_tr(sp['title'])}|{auto_translate_to_tr(sp['detail'])}|{sp['img']}")
                    else:
                        s_tr.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
                        
            specs_zh = " || ".join(s_zh) if user_role == "manufacturer" else r.get('specs_zh', '')
            specs_tr = " || ".join(s_tr)
            opt_str = ",".join(sel_opts)
            
            data_dict = {"name": n_tr, "name_zh": n_zh, "category": new_cat, "base_price": new_price, "currency": new_curr, "specs": specs_tr, "specs_zh": specs_zh, "compatible_options": opt_str, "port_discount": new_disc, "image_path": final_img, "user_id": uid}
            
            if mode == "edit":
                exec_factory("UPDATE models SET name=?, name_zh=?, category=?, base_price=?, currency=?, specs=?, specs_zh=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?", (n_tr, n_zh, new_cat, new_price, new_curr, specs_tr, specs_zh, opt_str, new_disc, final_img, mod_id))
                if user_role == "manufacturer": 
                    data_dict["id"] = mod_id; sync_to_vault("models", data_dict, "upsert", mod_id)
            else:
                exec_factory("INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (n_tr, n_zh, new_cat, new_price, new_curr, specs_tr, specs_zh, opt_str, new_disc, final_img, uid))
            
            st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM FORMU - ÇÖKMEYE KARŞI KORUMALI
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    if st.button(_m("back_list")): st.session_state.view_mode = "list"; st.rerun()
    st.header(_m("edit_opt_title") if mode == "edit" else _m("new_opt_title"))
    st.markdown("---")

    r = {}
    if mode == "edit" and opt_id:
        r_list = db_query("SELECT * FROM options WHERE id=?", (opt_id,))
        if not r_list: st.error("Kayıt bulunamadı."); st.stop()
        r = r_list[0]

    o_name = r.get("opt_name_zh", "") if user_role == "manufacturer" and r.get("opt_name_zh") else r.get("opt_name", "")
    o_desc = r.get("opt_desc_zh", "") if user_role == "manufacturer" and r.get("opt_desc_zh") else r.get("opt_desc", "")
    o_price = r.get("opt_price", 0.0)
    o_qty = bool(r.get("allow_qty", 1))
    o_img = r.get("opt_image", "")
    o_suffix = r.get("opt_suffix", "")
    o_v_img = r.get("opt_variant_image", "")

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            new_name = st.text_input(_m("opt_name"), value=o_name)
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            v_col1, v_col2 = st.columns(2)
            new_suffix = v_col1.text_input(_m("opt_suffix"), value=o_suffix, placeholder="Örn: L, -PRO")
            v_col1.info(_m("opt_suffix_help"))
            new_var_up = v_col2.file_uploader(_m("opt_v_img"), type=['png','jpg','jpeg'])
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            
            new_price = st.number_input(_m("opt_price"), value=o_price, step=50.0)
            new_qty = st.checkbox(_m("allow_qty"), value=o_qty)
            new_desc = st.text_area(_m("opt_desc"), value=o_desc, height=120)
            new_img_up = st.file_uploader(_m("opt_img_up"), type=['png','jpg','jpeg'])
            
        with c2:
            st.markdown(_m("img_prev"))
            if new_img_up: st.image(new_img_up, use_container_width=True)
            else:
                prev_img = get_image_base64(o_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

        if st.button("💾 " + _m("save_changes"), type="primary", use_container_width=True):
            if not new_name: st.error(_m("err_opt_name"))
            else:
                final_img = o_img
                if new_img_up: final_img = process_image(new_img_up, "opt", square=True)
                
                final_v_img = o_v_img
                if new_var_up: final_v_img = process_image(new_var_up, "variant", square=False)
                
                uid = st.session_state.get("user_id", 1)
                allow_q = 1 if new_qty else 0
                
                n_zh = new_name if user_role == "manufacturer" else r.get('opt_name_zh', '')
                n_tr = auto_translate_to_tr(new_name) if user_role == "manufacturer" else new_name
                d_zh = new_desc if user_role == "manufacturer" else r.get('opt_desc_zh', '')
                d_tr = auto_translate_to_tr(new_desc) if user_role == "manufacturer" else new_desc

                if mode == "edit": 
                    exec_factory("UPDATE options SET opt_name=?, opt_name_zh=?, opt_desc=?, opt_desc_zh=?, opt_price=?, opt_image=?, allow_qty=?, opt_suffix=?, opt_variant_image=? WHERE id=?", (n_tr, n_zh, d_tr, d_zh, new_price, final_img, allow_q, new_suffix, final_v_img, opt_id))
                else: 
                    exec_factory("INSERT INTO options (opt_name, opt_name_zh, opt_desc, opt_desc_zh, opt_price, opt_image, allow_qty, opt_suffix, opt_variant_image, user_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (n_tr, n_zh, d_tr, d_zh, new_price, final_img, allow_q, new_suffix, final_v_img, uid))
                
                st.session_state.view_mode = "list"; st.rerun()
