import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
import uuid
from PIL import Image

def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return res
    except: return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e: st.error(f"Hata: {e}")

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

def process_image(uploaded_file, prefix="img", size=(400, 400), square=True):
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
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join("images", filename)
        img.save(filepath, "JPEG", quality=95)
        return filename
    except: return ""

def show_product_management():
    exec_factory("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    exec_factory("CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_desc TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)")
    exec_factory("""CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, specs TEXT, currency TEXT DEFAULT 'USD', port_discount REAL DEFAULT 0.0, compatible_options TEXT DEFAULT '', gallery_images TEXT DEFAULT '', category TEXT DEFAULT 'Diğer Makinalar', gallery_videos TEXT DEFAULT '')""")

    if "view_mode" not in st.session_state: st.session_state.view_mode = "list"
    if "edit_mod_id" not in st.session_state: st.session_state.edit_mod_id = None
    if "edit_opt_id" not in st.session_state: st.session_state.edit_opt_id = None

    if st.session_state.view_mode == "list": show_list_view()
    elif st.session_state.view_mode == "mod_add": show_form_view(mode="add")
    elif st.session_state.view_mode == "mod_edit": show_form_view(mode="edit", mod_id=st.session_state.edit_mod_id)
    elif st.session_state.view_mode == "opt_add": show_opt_form_view(mode="add")
    elif st.session_state.view_mode == "opt_edit": show_opt_form_view(mode="edit", opt_id=st.session_state.edit_opt_id)

def show_list_view():
    st.header(":package: Fabrika Veritabanı Yönetimi")
    tab_mod, tab_opt, tab_cat = st.tabs(["📦 Modeller (Vitrin)", "⚙️ Ekstra Donanımlar (Vitrin)", "📂 Kategoriler"])
    
    with tab_mod:
        col_title, col_add = st.columns([3, 1])
        col_title.subheader("Kayıtlı Makineler")
        if col_add.button("➕ YENİ MAKİNE EKLE", type="primary", use_container_width=True):
            st.session_state.form_loaded = False 
            st.session_state.view_mode = "mod_add"; st.rerun()

        st.markdown("---")
        mods = get_factory("SELECT id, name, category, base_price, currency, image_path FROM models ORDER BY category ASC, name ASC")
        if mods:
            df_mods = pd.DataFrame(mods, columns=["id", "name", "category", "price", "currency", "image"])
            for cat in df_mods['category'].unique():
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df_mods[df_mods['category'] == cat].reset_index(drop=True)
                    for i in range(0, len(cat_mods), 4):
                        cols = st.columns(4, gap="small")
                        for j in range(4):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                safe_mod_id = int(row['id']) 
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:150px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown("<div style='height:150px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>Görsel Yok</div>", unsafe_allow_html=True)
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>{row['name']}</h4>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                                    if btn_c1.button("✏️", key=f"me_{safe_mod_id}", help="Düzenle"):
                                        st.session_state.edit_mod_id = safe_mod_id
                                        st.session_state.form_loaded = False
                                        st.session_state.view_mode = "mod_edit"; st.rerun()
                                    if btn_c2.button("📄", key=f"mc_{safe_mod_id}", help="Kopyala"):
                                        m_data = get_factory("SELECT name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos FROM models WHERE id=?", (safe_mod_id,))[0]
                                        exec_factory("""INSERT INTO models (name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos) VALUES (?,?,?,?,?,?,?,?,?,?)""", (m_data[0] + " (Kopya)", m_data[1], m_data[2], m_data[3], m_data[4], m_data[5], m_data[6], m_data[7], m_data[8], m_data[9]))
                                        st.success("Kopyalandı!"); st.rerun()
                                    if btn_c3.button("🗑️", key=f"md_{safe_mod_id}", help="Sil"):
                                        exec_factory("DELETE FROM models WHERE id=?", (safe_mod_id,)); st.rerun()
        else: st.info("Sistemde henüz bir makine bulunmuyor.")

    with tab_opt:
        col_opt_t, col_opt_a = st.columns([3, 1])
        col_opt_t.subheader("Ekstra Donanımlar Vitrini")
        if col_opt_a.button("➕ YENİ DONANIM EKLE", type="primary", use_container_width=True):
            st.session_state.opt_form_loaded = False; st.session_state.view_mode = "opt_add"; st.rerun()

        st.markdown("---")
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc, opt_image FROM options ORDER BY id DESC")
        if opts:
            for i in range(0, len(opts), 4):
                cols = st.columns(4, gap="small")
                for j in range(4):
                    if i + j < len(opts):
                        o_id, o_name, o_price, o_desc, o_img = opts[i+j]
                        safe_opt_id = int(o_id)
                        with cols[j].container(border=True):
                            img_b64 = get_image_base64(o_img)
                            if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:120px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                            else: st.markdown("<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:12px; margin-bottom:15px;'>Görsel Yok</div>", unsafe_allow_html=True)
                            st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{o_name}'>{o_name}</h4>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#64748b; font-size:12px; height:36px; overflow:hidden; margin-bottom:5px;'>{o_desc if o_desc else '-'}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:16px; margin-bottom:15px;'>+{o_price:,.2f} USD</div>", unsafe_allow_html=True)
                            btn_c1, btn_c2, btn_c3 = st.columns(3)
                            if btn_c1.button("✏️", key=f"oe_{safe_opt_id}"):
                                st.session_state.edit_opt_id = safe_opt_id
                                st.session_state.opt_form_loaded = False
                                st.session_state.view_mode = "opt_edit"; st.rerun()
                            if btn_c2.button("📄", key=f"oc_{safe_opt_id}"):
                                o_data = get_factory("SELECT opt_name, opt_desc, opt_price, opt_image, sort_order FROM options WHERE id=?", (safe_opt_id,))[0]
                                exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image, sort_order) VALUES (?,?,?,?,?)", (o_data[0] + " (Kopya)", o_data[1], o_data[2], o_data[3], o_data[4]))
                                st.rerun()
                            if btn_c3.button("🗑️", key=f"od_{safe_opt_id}"):
                                exec_factory("DELETE FROM options WHERE id=?", (safe_opt_id,)); st.rerun()

    with tab_cat:
        c1, c2 = st.columns([2,1])
        with c1:
            st.subheader("Mevcut Kategoriler")
            cats = get_factory("SELECT id, name FROM categories")
            if cats:
                for cid, cname in cats:
                    col_a, col_b = st.columns([4,1])
                    col_a.write(f"📁 {cname}")
                    if col_b.button("Sil", key=f"del_cat_{cid}"): exec_factory("DELETE FROM categories WHERE id=?", (cid,)); st.rerun()
        with c2:
            st.subheader("Yeni Ekle")
            with st.form("new_cat"):
                n_cat = st.text_input("Kategori Adı")
                if st.form_submit_button("Ekle") and n_cat:
                    try: exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat,)); st.rerun()
                    except: st.error("Kategori mevcut!")

def show_form_view(mode="add", mod_id=None):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.view_mode = "list"; st.rerun()
    
    is_edit = (mode == "edit" and mod_id is not None)
    col_title.header("✏️ Makine Kartı Düzenleyici" if is_edit else "✨ Yeni Makine Kartı Oluştur")
    st.markdown("---")

    if not st.session_state.get("form_loaded", False):
        st.session_state.form_loaded = True
        cats_list = [c[1] for c in get_factory("SELECT id, name FROM categories")]
        st.session_state.f_cats_list = cats_list if cats_list else ["Diğer Makinalar"]
        
        if is_edit:
            res = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options FROM models WHERE id=?", (int(mod_id),))
            r = res[0]
            st.session_state.f_name, st.session_state.f_price, st.session_state.f_curr = r[0], float(r[1]), r[2]
            st.session_state.f_cat, st.session_state.f_disc, st.session_state.f_img = r[3], float(r[4]), r[5]
            s_list = []
            if r[6]:
                for item in str(r[6]).split("||"):
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

    tab_genel, tab_teknik, tab_donanim = st.tabs(["📄 Genel Bilgiler", "⚙️ Teknik Özellikler", "🔌 Uyumlu Ekstra Donanımlar"])
    
    with tab_genel:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.f_name = st.text_input("Makine Adı *", value=st.session_state.f_name)
            idx_cat = st.session_state.f_cats_list.index(st.session_state.f_cat) if st.session_state.f_cat in st.session_state.f_cats_list else 0
            st.session_state.f_cat = st.selectbox("Kategori", st.session_state.f_cats_list, index=idx_cat)
            col_p, col_c = st.columns([3, 1])
            st.session_state.f_price = col_p.number_input("Yurtiçi Fiyat *", min_value=0.0, value=st.session_state.f_price, step=100.0)
            idx_curr = ["USD", "EUR", "TRY"].index(st.session_state.f_curr) if st.session_state.f_curr in ["USD", "EUR", "TRY"] else 0
            st.session_state.f_curr = col_c.selectbox("Para Birimi", ["USD", "EUR", "TRY"], index=idx_curr)
            st.session_state.f_disc = st.number_input("Liman Teslim İskontosu (%)", min_value=0.0, max_value=100.0, value=st.session_state.f_disc)
            st.file_uploader("Ana Görsel Dosyası", type=['png','jpg','jpeg'], key="up_main_img")
        with c2:
            st.markdown("**Görsel Önizleme**")
            up_main = st.session_state.get("up_main_img")
            if up_main: st.image(up_main, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.f_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

    with tab_teknik:
        st.info("💡 Sistem artık yeni yüklenen resimleri 400x400 yüksek çözünürlükte işliyor.")
        for i in range(len(st.session_state.f_specs)):
            col_t, col_d, col_i, col_x = st.columns([2.5, 4, 3, 0.5], vertical_alignment="center")
            st.session_state.f_specs[i]["title"] = col_t.text_input("Başlık", value=st.session_state.f_specs[i]["title"], key=f"t_{i}", label_visibility="collapsed")
            st.session_state.f_specs[i]["detail"] = col_d.text_input("Detay", value=st.session_state.f_specs[i]["detail"], key=f"d_{i}", label_visibility="collapsed")
            with col_i:
                c_prev, c_up = st.columns([1, 3], vertical_alignment="center")
                up_spec = st.session_state.get(f"up_spec_{i}")
                if up_spec: c_prev.image(up_spec, width=40)
                else:
                    cur_img = st.session_state.f_specs[i].get("img", "")
                    if cur_img:
                        b64 = get_image_base64(cur_img)
                        if b64: c_prev.markdown(f'<img src="{b64}" style="width:40px; height:40px; border-radius:4px; object-fit:cover;">', unsafe_allow_html=True)
                c_up.file_uploader("Resim Seç", type=['png','jpg','jpeg'], key=f"up_spec_{i}", label_visibility="collapsed")
            if col_x.button("❌", key=f"del_spec_{i}"): st.session_state.f_specs.pop(i); st.rerun()
        if st.button("➕ YENİ ÖZELLİK SATIRI EKLE", use_container_width=True):
            st.session_state.f_specs.append({"title": "", "detail": "", "img": ""}); st.rerun()

    with tab_donanim:
        opts_avail = get_factory("SELECT id, opt_name, opt_price FROM options ORDER BY opt_price DESC")
        new_opts = []
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id, o_name, o_price = opt
            is_checked = str(o_id) in st.session_state.f_opts
            with chk_cols[idx % 3]:
                if st.checkbox(f"{o_name} (+{o_price:,.0f})", value=is_checked, key=f"chk_{o_id}"): new_opts.append(str(o_id))
        st.session_state.f_opts = new_opts

    st.markdown("---")
    if st.button("💾 " + ("DEĞİŞİKLİKLERİ KAYDET" if is_edit else "MAKİNEYİ SİSTEME EKLE"), type="primary", use_container_width=True):
        if not st.session_state.f_name or st.session_state.f_price <= 0: st.error("Makine adı ve geçerli bir fiyat girin!")
        else:
            up_main = st.session_state.get("up_main_img")
            if up_main is not None: st.session_state.f_img = process_image(up_main, prefix="machine", size=(1200, 900), square=False)

            spec_strs = []
            for i, sp in enumerate(st.session_state.f_specs):
                up_spec = st.session_state.get(f"up_spec_{i}")
                if up_spec is not None: sp["img"] = process_image(up_spec, prefix="spec", size=(400, 400), square=True)
                if sp["title"].strip() or sp["detail"].strip(): spec_strs.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
            
            final_specs_str = " || ".join(spec_strs) + (" || " if spec_strs else "")
            final_opts_str = ",".join(st.session_state.f_opts)
            
            if is_edit:
                exec_factory("""UPDATE models SET name=?, category=?, base_price=?, currency=?, specs=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?""", (st.session_state.f_name, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, final_specs_str, final_opts_str, st.session_state.f_disc, st.session_state.f_img, int(mod_id)))
            else:
                exec_factory("""INSERT INTO models (name, category, base_price, currency, specs, compatible_options, port_discount, image_path) VALUES (?,?,?,?,?,?,?,?)""", (st.session_state.f_name, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, final_specs_str, final_opts_str, st.session_state.f_disc, st.session_state.f_img))
            st.session_state.view_mode = "list"; st.rerun()

def show_opt_form_view(mode="add", opt_id=None):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True): st.session_state.view_mode = "list"; st.rerun()
    is_edit = (mode == "edit" and opt_id is not None)
    col_title.header("✏️ Donanım Düzenle" if is_edit else "✨ Yeni Ekstra Donanım Ekle")
    st.markdown("---")

    if not st.session_state.get("opt_form_loaded", False):
        st.session_state.opt_form_loaded = True
        if is_edit:
            r = get_factory("SELECT opt_name, opt_price, opt_desc, opt_image FROM options WHERE id=?", (int(opt_id),))[0]
            st.session_state.o_name, st.session_state.o_price = r[0], float(r[1])
            st.session_state.o_desc, st.session_state.o_img = r[2] if r[2] else "", r[3] if r[3] else ""
        else:
            st.session_state.o_name, st.session_state.o_price, st.session_state.o_desc, st.session_state.o_img = "", 0.0, "", ""

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.session_state.o_name = st.text_input("Donanım Adı *", value=st.session_state.o_name)
            st.session_state.o_price = st.number_input("Fiyat *", min_value=0.0, value=st.session_state.o_price, step=50.0)
            st.session_state.o_desc = st.text_area("Açıklama", value=st.session_state.o_desc, height=120)
            st.file_uploader("Donanım Görseli", type=['png','jpg','jpeg'], key="up_opt_img")
        with c2:
            st.markdown("**Görsel Önizleme**")
            up_opt = st.session_state.get("up_opt_img")
            if up_opt: st.image(up_opt, use_container_width=True)
            else:
                prev_img = get_image_base64(st.session_state.o_img)
                if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px;">', unsafe_allow_html=True)

        if st.button("💾 " + ("DEĞİŞİKLİKLERİ KAYDET" if is_edit else "DONANIMI SİSTEME EKLE"), type="primary", use_container_width=True):
            if not st.session_state.o_name or st.session_state.o_price <= 0: st.error("Ad ve fiyat zorunludur!")
            else:
                up_opt = st.session_state.get("up_opt_img")
                if up_opt is not None: st.session_state.o_img = process_image(up_opt, prefix="opt", size=(400, 400), square=True)
                if is_edit: exec_factory("UPDATE options SET opt_name=?, opt_desc=?, opt_price=?, opt_image=? WHERE id=?", (st.session_state.o_name, st.session_state.o_desc, st.session_state.o_price, st.session_state.o_img, int(opt_id)))
                else: exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price, opt_image) VALUES (?,?,?,?)", (st.session_state.o_name, st.session_state.o_desc, st.session_state.o_price, st.session_state.o_img))
                st.session_state.view_mode = "list"; st.rerun()
