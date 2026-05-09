import streamlit as st
import sqlite3
import os
import base64
import uuid
from PIL import Image

# =====================================================================
# 🛠️ ÖLÜMSÜZ VERİTABANI MOTORU (SADE VE NET)
# =====================================================================
def db_query(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return [dict(row) for row in res]
    except:
        return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()
        return True
    except Exception as e:
        st.error(f"İşlem Hatası: {e}")
        return False

def get_safe(row, key, default=""):
    if row and key in row and row[key] is not None:
        return row[key]
    return default

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
# ÇOKLU DİL
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

DICT_MODEL = {
    "tr": {
        "m_title": "📦 Fabrika Veritabanı Yönetimi", "t_mod": "📦 Modeller (Vitrin)", "t_opt": "⚙️ Donanımlar", "t_cat": "📂 Kategoriler",
        "reg_mach": "Kayıtlı Makineler", "add_mach": "➕ YENİ MAKİNE EKLE", "no_img": "Görsel Yok", "price_wait": "Fiyat Bekleniyor", "no_auth_price": "🔒 Fiyat Gizli",
        "opt_showcase": "Ekstra Donanımlar", "add_opt": "➕ YENİ DONANIM EKLE", "cat_mng": "Kategori Yönetimi", "new_cat": "Yeni Kategori Adı...", "btn_add": "➕ Ekle",
        "back_list": "🔙 Listeye Dön", "edit_mach": "✏️ Makine Düzenleyici", "new_mach": "✨ Makine Kartı Oluştur",
        "tab_gen": "📄 Genel Bilgiler", "tab_tech": "⚙️ Teknik Özellikler", "tab_comp": "🔌 Uyumlu Donanımlar",
        "m_name": "Makine Adı *", "m_cat": "Kategori", "dom_price": "Fiyat *", "currency": "Para Birimi", "port_disc": "İskonto (%)",
        "main_img": "Ana Görsel", "img_prev": "**Görsel Önizleme**", "spec_title": "Özellik Başlığı", "spec_det": "Özellik Detayı", "choose_img": "Resim Seç",
        "add_spec": "➕ YENİ ÖZELLİK SATIRI EKLE", "save_changes": "💾 DEĞİŞİKLİKLERİ KAYDET", "add_sys": "💾 SİSTEME EKLE",
        "edit_opt_title": "✏️ Donanım Düzenle", "new_opt_title": "✨ Yeni Donanım Ekle",
        "opt_name": "Donanım Adı *", "opt_price": "Fiyat *", "allow_qty": "Bu donanım için adet seçilebilir", "opt_desc": "Açıklama", "opt_img_up": "Donanım Görseli",
        "opt_suffix": "Model Adı Eki (Suffix)", "opt_v_img": "Varyasyon Ana Resmi", "opt_suffix_help": "💡 Örn: L, -PRO vb."
    }
}
def _m(key): return DICT_MODEL.get(st.session_state.get("lang", "tr").lower(), DICT_MODEL["tr"]).get(key, key)

# =====================================================================
# YÖNLENDİRME
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
# LİSTELEME EKRANI (PANDAS KALDIRILDI, KOPYALA BUTONU EKLENDİ)
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
            # Saf Python Gruplama (Hataya yer yok)
            cats_dict = {}
            for m in mods:
                c = m.get('category')
                if not c: c = "Diğer Makinalar"
                if c not in cats_dict: cats_dict[c] = []
                cats_dict[c].append(m)

            for cat, cat_mods in cats_dict.items():
                with st.expander(f"📁 {cat}", expanded=True):
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods[i + j]
                                d_name = row.get('name_zh') if user_role == "manufacturer" and row.get('name_zh') else row.get('name')
                                m_id = int(row.get('id'))
                                
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row.get('image_path'))
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{d_name}</h4>", unsafe_allow_html=True)
                                    
                                    if user_role == "manufacturer": st.markdown(f"<div style='color:#64748b; font-weight:800; font-size:13px; margin-bottom:15px; padding:3px; background:#f1f5f9; border-radius:4px; text-align:center;'>{_m('no_auth_price')}</div>", unsafe_allow_html=True)
                                    else: st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>{row.get('base_price',0):,.2f} {row.get('currency','USD')}</div>", unsafe_allow_html=True)
                                        
                                    bc1, bc2, bc3 = st.columns(3)
                                    if bc1.button("✏️", key=f"me_{m_id}", use_container_width=True, help="Düzenle"):
                                        st.session_state.edit_mod_id = m_id; st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if bc2.button("📄", key=f"mc_{m_id}", use_container_width=True, help="Kopyala"):
                                        c_data = db_query("SELECT * FROM models WHERE id=?", (m_id,))
                                        if c_data:
                                            cd = c_data[0]
                                            exec_factory("""INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path, user_id) 
                                                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", 
                                                         (get_safe(cd,'name','') + " (Kopya)", get_safe(cd,'name_zh',''), get_safe(cd,'category',''), get_safe(cd,'base_price',0.0), get_safe(cd,'currency','USD'), get_safe(cd,'specs',''), get_safe(cd,'specs_zh',''), get_safe(cd,'compatible_options',''), get_safe(cd,'port_discount',0.0), get_safe(cd,'image_path',''), user_id))
                                        st.rerun()
                                    if bc3.button("🗑️", key=f"md_{m_id}", use_container_width=True, help="Sil"):
                                        exec_factory("DELETE FROM models WHERE id=?", (m_id,))
                                        st.rerun()
        else: st.info("Sistemde makine bulunmuyor.")

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
                        o_id = int(o.get('id'))
                        d_name = o.get('opt_name_zh') if user_role == "manufacturer" and o.get('opt_name_zh') else o.get('opt_name')
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o.get('opt_image'))
                            if img_b64: st.markdown(f'<img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:10px;">', unsafe_allow_html=True)
                            else: st.markdown(f"<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{_m('no_img')}</div>", unsafe_allow_html=True)
                            
                            st.markdown(f"<b style='color:#0f172a;'>{d_name}</b>", unsafe_allow_html=True)
                            if o.get('opt_suffix') or o.get('opt_variant_image'):
                                st.markdown(f"<div style='font-size:11px; color:#2563eb; font-weight:bold; margin-top:3px;'>✨ Akıllı Varyasyon</div>", unsafe_allow_html=True)
                            
                            if user_role == "manufacturer": st.caption(_m("no_auth_price"))
                            else: st.markdown(f"<div style='color:#ea580c; font-weight:bold; margin-top:5px;'>+{o.get('opt_price',0):,.0f} USD</div>", unsafe_allow_html=True)
                            
                            bc1, bc2, bc3 = st.columns(3)
                            if bc1.button("✏️", key=f"oe_{o_id}", use_container_width=True, help="Düzenle"):
                                st.session_state.edit_opt_id = o_id; st.session_state.view_mode = "opt_edit"; st.rerun()
                            if bc2.button("📄", key=f"oc_{o_id}", use_container_width=True, help="Kopyala"):
                                c_data = db_query("SELECT * FROM options WHERE id=?", (o_id,))
                                if c_data:
                                    cd = c_data[0]
                                    exec_factory("""INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, sort_order, allow_qty, opt_name_zh, opt_desc_zh, opt_suffix, opt_variant_image, user_id) 
                                                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""", 
                                                 (get_safe(cd,'opt_name','') + " (Kopya)", get_safe(cd,'opt_desc',''), get_safe(cd,'opt_price',0.0), get_safe(cd,'opt_image',''), get_safe(cd,'sort_order',0), get_safe(cd,'allow_qty',1), get_safe(cd,'opt_name_zh',''), get_safe(cd,'opt_desc_zh',''), get_safe(cd,'opt_suffix',''), get_safe(cd,'opt_variant_image',''), user_id))
                                st.rerun()
                            if bc3.button("🗑️", key=f"od_{o_id}", use_container_width=True, help="Sil"):
                                exec_factory("DELETE FROM options WHERE id=?", (o_id,))
                                st.rerun()
        else: st.info("Sistemde donanım bulunmuyor.")

    with tab_cat:
        st.subheader(_m("cat_mng"))
        with st.form("new_cat_form", clear_on_submit=True):
            n_cat = st.text_input(_m("new_cat"))
            if st.form_submit_button(_m("btn_add")) and n_cat.strip():
                exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat.strip(),)); st.rerun()
        cats = db_query("SELECT * FROM categories ORDER BY name ASC")
        for c in cats:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.write(f"📁 {c.get('name')}")
                if c2.button("🗑️ Sil", key=f"del_cat_{c.get('id')}", use_container_width=True):
                    exec_factory("DELETE FROM categories WHERE id=?", (c.get('id'),)); st.rerun()

# =====================================================================
# MAKİNE DÜZENLEME FORMU 
# =====================================================================
def show_form_view(mode="add", mod_id=None, user_role="dealer"):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button(_m("back_list"), use_container_width=True): st.session_state.view_mode = "list"; st.rerun()
    st.header(_m("edit_mach") if mode == "edit" else _m("new_mach"))
    st.markdown("---")

    cats_db_raw = db_query("SELECT name FROM categories")
    cats_db = [c.get('name') for c in cats_db_raw] if cats_db_raw else ["Diğer Makinalar"]

    r = {}
    if mode == "edit" and mod_id is not None:
        r_list = db_query("SELECT * FROM models WHERE id=?", (int(mod_id),))
        if not r_list: st.error("Kayıt veritabanında bulunamadı."); st.stop()
        r = r_list[0]

    f_name = r.get("name_zh", "") if user_role == "manufacturer" and r.get("name_zh") else r.get("name", "")
    f_price = float(r.get("base_price", 0.0) or 0.0)
    f_curr = r.get("currency", "USD") or "USD"
    f_cat = r.get("category", cats_db[0]) or cats_db[0]
    f_disc = float(r.get("port_discount", 0.0) or 0.0)
    f_img = r.get("image_path", "") or ""
    
    f_opts_raw = str(r.get("compatible_options", ""))
    f_opts = [x.strip() for x in f_opts_raw.split(",") if x.strip()]
    
    s_list = []
    t_specs = str(r.get("specs_zh", "") if user_role == "manufacturer" and r.get("specs_zh") else r.get("specs", ""))
    if t_specs:
        for item in t_specs.split("||"):
            if item.strip():
                p = item.split("|")
                s_t = p[0].strip() if len(p) > 0 else ""
                s_d = p[1].strip() if len(p) > 1 else ""
                s_i = p[2].strip() if len(p) > 2 else ""
                s_list.append({"title": s_t, "detail": s_d, "img": s_i})
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
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">', unsafe_allow_html=True)

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
                            if b64: c_prev.markdown(f'<img src="{b64}" style="width:40px; height:40px; border-radius:4px; object-fit:contain;">', unsafe_allow_html=True)
                    c_up.file_uploader(_m("choose_img"), type=['png','jpg','jpeg'], key=f"up_spec_{i}", label_visibility="collapsed")
                    
                if col_x.button("❌", key=f"del_spec_{i}", use_container_width=True): 
                    st.session_state.f_specs.pop(i); st.rerun()
                    
        st.write("")
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
                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:80px; object-fit:contain; margin-bottom:10px;"></div>', unsafe_allow_html=True)
                    if st.checkbox(f"{o_name} (+{o_price:,.0f})", value=(o_id in f_opts), key=f"chk_{o_id}"): sel_opts.append(o_id)

    st.markdown("---")
    if st.button(_m("save_changes"), type="primary", use_container_width=True):
        if not new_name: st.error(_m("err_name"))
        else:
            with st.spinner("İşleniyor..."):
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
                
                if mode == "edit":
                    exec_factory("UPDATE models SET name=?, name_zh=?, category=?, base_price=?, currency=?, specs=?, specs_zh=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?", (n_tr, n_zh, new_cat, new_price, new_curr, specs_tr, specs_zh, opt_str, new_disc, final_img, int(mod_id)))
                else:
                    exec_factory("INSERT INTO models (name, name_zh, category, base_price, currency, specs, specs_zh, compatible_options, port_discount, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (n_tr, n_zh, new_cat, new_price, new_curr, specs_tr, specs_zh, opt_str, new_disc, final_img, uid))
                
                st.session_state.view_mode = "list"; st.rerun()

# =====================================================================
# DONANIM DÜZENLEME FORMU
# =====================================================================
def show_opt_form_view(mode="add", opt_id=None, user_role="dealer"):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button(_m("back_list"), use_container_width=True): st.session_state.view_mode = "list"; st.rerun()
    st.header(_m("edit_opt_title") if mode == "edit" else _m("new_opt_title"))
    st.markdown("---")

    r = {}
    if mode == "edit" and opt_id is not None:
        r_list = db_query("SELECT * FROM options WHERE id=?", (int(opt_id),))
        if not r_list: st.error("Kayıt bulunamadı."); st.stop()
        r = r_list[0]

    o_name = r.get("opt_name_zh", "") if user_role == "manufacturer" and r.get("opt_name_zh") else r.get("opt_name", "")
    o_desc = r.get("opt_desc_zh", "") if user_role == "manufacturer" and r.get("opt_desc_zh") else r.get("opt_desc", "")
    o_price = float(r.get("opt_price", 0.0) or 0.0)
    o_qty = bool(r.get("allow_qty", 1))
    o_img = r.get("opt_image", "") or ""
    o_suffix = r.get("opt_suffix", "") or ""
    o_v_img = r.get("opt_variant_image", "") or ""

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
                with st.spinner("İşleniyor..."):
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
                        exec_factory("UPDATE options SET opt_name=?, opt_name_zh=?, opt_desc=?, opt_desc_zh=?, opt_price=?, opt_image=?, allow_qty=?, opt_suffix=?, opt_variant_image=? WHERE id=?", (n_tr, n_zh, d_tr, d_zh, new_price, final_img, allow_q, new_suffix, final_v_img, int(opt_id)))
                    else: 
                        exec_factory("INSERT INTO options (opt_name, opt_name_zh, opt_desc, opt_desc_zh, opt_price, opt_image, allow_qty, opt_suffix, opt_variant_image, user_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (n_tr, n_zh, d_tr, d_zh, new_price, final_img, allow_q, new_suffix, final_v_img, uid))
                    
                    st.session_state.view_mode = "list"; st.rerun()
