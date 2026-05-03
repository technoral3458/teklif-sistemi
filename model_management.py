import streamlit as st
import database
import pandas as pd
import os
import uuid

# =====================================================================
# SUNUCUYA DOSYA KAYDETME MOTORU
# =====================================================================
def save_uploaded_file(uploaded_file, folder_name="images"):
    if uploaded_file is None:
        return ""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name, exist_ok=True)
    
    ext = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
    file_path = f"{folder_name}/{safe_name}"
    
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"⚠️ Dosya sunucuya kaydedilemedi: {e}")
        return ""

# =====================================================================
# VERİTABANI TABLO KONTROLLERİ
# =====================================================================
def init_management_tables():
    database.exec_query("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image_path TEXT DEFAULT '')")
    count = database.get_query("SELECT COUNT(*) FROM categories")
    if not count or count[0][0] == 0:
        defaults = ["Genel / Tüm Makineler", "CNC Router Makinaları", "CNC Delik Makinaları", 
                    "Kenar Bantlama Makinaları", "Eğri Kenar Bantlama Makinaları", 
                    "Panel Ebatlama Makinaları", "Boya Makinaları", "Profil Makinaları", "Zımpara Makinaları", "Diğer Makinalar"]
        for cat in defaults:
            database.exec_query("INSERT INTO categories (name) VALUES (?)", (cat,))

    database.exec_query("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, base_price REAL, 
        currency TEXT DEFAULT 'USD', specs TEXT, compatible_options TEXT, image_path TEXT)""")
    try:
        m_cols = [c[1] for c in database.get_query("PRAGMA table_info(models)")]
        if "category" not in m_cols: database.exec_query("ALTER TABLE models ADD COLUMN category TEXT DEFAULT 'Diğer Makinalar'")
        if "compatible_options" not in m_cols: database.exec_query("ALTER TABLE models ADD COLUMN compatible_options TEXT DEFAULT ''")
        if "port_discount" not in m_cols: database.exec_query("ALTER TABLE models ADD COLUMN port_discount REAL DEFAULT 0.0")
        if "gallery_images" not in m_cols: database.exec_query("ALTER TABLE models ADD COLUMN gallery_images TEXT DEFAULT ''") 
        if "gallery_videos" not in m_cols: database.exec_query("ALTER TABLE models ADD COLUMN gallery_videos TEXT DEFAULT ''")
    except: pass

    database.exec_query("""CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, category TEXT, opt_price REAL, 
        currency TEXT DEFAULT 'USD', opt_desc TEXT, opt_image TEXT, video_path TEXT, remove_keyword TEXT)""")
    try:
        o_cols = [c[1] for c in database.get_query("PRAGMA table_info(options)")]
        if "remove_keyword" not in o_cols: database.exec_query("ALTER TABLE options ADD COLUMN remove_keyword TEXT DEFAULT ''")
        if "video_path" not in o_cols: database.exec_query("ALTER TABLE options ADD COLUMN video_path TEXT DEFAULT ''")
        if "sort_order" not in o_cols: database.exec_query("ALTER TABLE options ADD COLUMN sort_order INTEGER DEFAULT 0")
    except: pass

def get_categories():
    res = database.get_query("SELECT name FROM categories ORDER BY id")
    return [r[0] for r in res] if res else ["Diğer Makinalar"]

# =====================================================================
# TEKNİK ÖZELLİK AYRIŞTIRICILARI (SPECS)
# =====================================================================
def decode_specs(specs_str):
    if not specs_str: return []
    specs_list = []
    for spec in str(specs_str).split("||"):
        parts = spec.split("|")
        name = parts[0] if len(parts) > 0 else ""
        val = parts[1] if len(parts) > 1 else ""
        icon = parts[2] if len(parts) > 2 else ""
        if name or val or icon:
            specs_list.append({"id": str(uuid.uuid4()), "name": name, "val": val, "icon": icon})
    return specs_list

def init_machine_specs_state(selected_m_id, specs_str):
    if st.session_state.get("current_editing_m_id") != selected_m_id:
        st.session_state.machine_specs_list = decode_specs(specs_str)
        st.session_state.current_editing_m_id = selected_m_id

# =====================================================================
# ANA YÖNETİM SAYFASI
# =====================================================================
def show_product_management():
    init_management_tables()
    cat_list = get_categories()
    
    if 'machine_specs_list' not in st.session_state: st.session_state.machine_specs_list = []
    if 'current_editing_m_id' not in st.session_state: st.session_state.current_editing_m_id = None
    
    st.markdown("<h2 style='color: #1e293b;'>Katalog ve Envanter Yönetimi</h2>", unsafe_allow_html=True)
    tab_m, tab_o, tab_c = st.tabs(["📦 Makineler", "🔧 Donanım Havuzu", "🗂️ Kategoriler"])

    # =================================================================
    # SEKME 1: MAKİNELER
    # =================================================================
    with tab_m:
        m_data = database.get_query("SELECT id, category, name, base_price, currency, port_discount, compatible_options, specs, image_path FROM models ORDER BY id DESC")
        if m_data:
            df_m = pd.DataFrame(m_data, columns=["ID", "Kategori", "Model Adı", "Fiyat", "Birim", "İskonto(%)", "Donanımlar", "Specs", "Resim"])
            st.dataframe(df_m.drop(columns=["ID", "Specs"]), use_container_width=True)
        else:
            st.info("Kayıtlı makine bulunamadı.")
            
        st.markdown("---")
        m_action = st.radio("İşlem Seçin (Makine)", ["➕ Yeni Makine Ekle", "📝 Düzenle / Sil / Kopyala"], horizontal=True)
        
        selected_m_id, m_info = None, None
        
        if m_action == "📝 Düzenle / Sil / Kopyala":
            if m_data:
                m_options = [f"{row[0]} - {row[2]}" for row in m_data]
                sel_str = st.selectbox("İşlem yapılacak makineyi seçin:", m_options, key="sel_m")
                selected_m_id = int(sel_str.split(" - ")[0])
                m_info = database.get_query("SELECT name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos FROM models WHERE id=?", (selected_m_id,))[0]
                init_machine_specs_state(selected_m_id, m_info[6])
            else:
                st.warning("Düzenlenecek makine yok.")
        
        if m_action == "➕ Yeni Makine Ekle":
            init_machine_specs_state("NEW_MACHINE", "")

        if m_action == "➕ Yeni Makine Ekle" or m_info:
            with st.form("machine_form", clear_on_submit=False):
                mn = st.text_input("Makine Adı *", value=m_info[0] if m_info else "")
                
                col1, col2, col3, col4 = st.columns(4)
                m_cat = col1.selectbox("Kategori", cat_list, index=cat_list.index(m_info[1]) if m_info and m_info[1] in cat_list else 0)
                mp = col2.number_input("Yurtiçi Fiyat", min_value=0.0, value=float(m_info[2]) if m_info else 0.0)
                m_curr = col3.selectbox("Para Birimi", ["USD", "EUR", "RMB", "TRY"], index=["USD", "EUR", "RMB", "TRY"].index(m_info[3]) if m_info and m_info[3] in ["USD", "EUR", "RMB", "TRY"] else 0)
                m_disc = col4.number_input("Liman İskontosu (%)", min_value=0.0, value=float(m_info[4]) if m_info else 0.0)
                
                # Opsiyon Seçimi
                st.markdown("#### ⚙️ Uyumlu Donanımları Seçin")
                all_opts = database.get_query("SELECT id, opt_name, category, opt_price, currency FROM options ORDER BY category, opt_name")
                opt_display_list = []
                opt_map = {}
                id_to_display = {}

                if all_opts:
                    for oid, oname, ocat, oprice, ocurr in all_opts:
                        disp = f"{oname} [{ocat}] (+{oprice} {ocurr})"
                        opt_display_list.append(disp)
                        opt_map[disp] = str(oid)
                        id_to_display[str(oid)] = disp

                default_opts = []
                if m_info and m_info[5]:
                    saved_ids = [x.strip() for x in str(m_info[5]).split(",") if x.strip()]
                    default_opts = [id_to_display[sid] for sid in saved_ids if sid in id_to_display]

                selected_opt_names = st.multiselect("Bu makineyle satılabilecek donanımları listeden seçin:", options=opt_display_list, default=default_opts)
                
                # --- TEKNİK ÖZELLİKLER BÖLÜMÜ (CANLI ÖNİZLEME İLE) ---
                st.markdown("---")
                st.markdown("#### 📋 Adım Adım Teknik Özellik Ekleme Sihirbazı")
                
                to_delete_spec_id = None
                for i, spec in enumerate(st.session_state.machine_specs_list):
                    unique_key = spec["id"]
                    
                    with st.container(border=True):
                        col_h1, col_h2 = st.columns([10, 1])
                        col_h1.markdown(f"**Özellik #{i+1}: {spec['name'] if spec['name'] else 'Doldurunuz'}**")
                        if col_h2.form_submit_button("SİL", key=f"del_{unique_key}"):
                            to_delete_spec_id = unique_key
                        
                        col_i1, col_i2 = st.columns(2)
                        spec['name'] = col_i1.text_input("Özellik Adı", value=spec['name'], key=f"n_{unique_key}")
                        spec['val'] = col_i2.text_input("Değer / Açıklama", value=spec['val'], key=f"v_{unique_key}")
                        
                        up_icon = st.file_uploader("Bu özellik için İkon Yükle", type=['png','jpg','jpeg'], key=f"u_{unique_key}")
                        
                        if up_icon:
                            st.image(up_icon, caption="Yüklenen İkon (Kaydedilecek)", width=60)
                        elif spec['icon'] and os.path.isfile(spec['icon']):
                            try:
                                with open(spec['icon'], "rb") as f:
                                    st.image(f.read(), width=60, caption="Mevcut İkon")
                            except: pass

                # --- ANA MEDYA ÖNİZLEME ---
                st.markdown("---")
                st.markdown("#### 🖼️ Ana Resim ve Galeri")
                col_img_up, col_img_pre = st.columns([2, 1])
                
                with col_img_up:
                    up_main = st.file_uploader("Ana Makine Resmi", type=['png','jpg','jpeg'], key="m_up_main")
                    up_gal_i = st.file_uploader("Galeri Resimleri (Çoklu)", type=['png','jpg','jpeg'], accept_multiple_files=True, key="m_up_gal_i")
                    up_gal_v = st.file_uploader("Galeri Videoları (Çoklu)", type=['mp4','avi','mov'], accept_multiple_files=True, key="m_up_gal_v")
                
                with col_img_pre:
                    if up_main:
                        st.image(up_main, caption="Yeni Ana Resim (Önizleme)", use_container_width=True)
                    elif m_info and m_info[7] and os.path.isfile(m_info[7]):
                        try:
                            with open(m_info[7], "rb") as f:
                                st.image(f.read(), caption="Mevcut Ana Resim", use_container_width=True)
                        except: pass

                col_btn_add, col_btn_save = st.columns(2)
                add_spec_btn = col_btn_add.form_submit_button("➕ YENİ TEKNİK ÖZELLİK KUTUSU EKLE", use_container_width=True)
                submit_m = col_btn_save.form_submit_button("💾 BİLGİLERİ VE RESİMLERİ KAYDET", type="primary", use_container_width=True)
                
            if to_delete_spec_id:
                st.session_state.machine_specs_list = [s for s in st.session_state.machine_specs_list if s["id"] != to_delete_spec_id]
                st.rerun()
                
            if add_spec_btn:
                st.session_state.machine_specs_list.append({"id": str(uuid.uuid4()), "name": "", "val": "", "icon": ""})
                st.rerun()
            
            if submit_m:
                if mn:
                    final_opts_str = ",".join([opt_map[name] for name in selected_opt_names])
                    m_specs_list = []
                    
                    for spec in st.session_state.machine_specs_list:
                        unique_key = spec["id"]
                        name = spec['name'].strip()
                        val = spec['val'].strip()
                        
                        uploaded_icon_file = st.session_state.get(f"u_{unique_key}")
                        if uploaded_icon_file:
                            final_icon_path = save_uploaded_file(uploaded_icon_file, "images")
                        else:
                            final_icon_path = spec['icon']
                        
                        if name or val or final_icon_path:
                            m_specs_list.append(f"{name}|{val}|{final_icon_path}")
                    
                    final_specs_str = "||".join(m_specs_list)

                    m_img_path = save_uploaded_file(up_main, "images") if up_main else (m_info[7] if m_info else "")
                    
                    gal_imgs = [save_uploaded_file(img, "images") for img in up_gal_i] if up_gal_i else []
                    existing_gal_imgs = m_info[8].split(",") if m_info and m_info[8] else []
                    final_gal_imgs = ",".join(filter(None, existing_gal_imgs + gal_imgs))

                    gal_vids = [save_uploaded_file(vid, "images") for vid in up_gal_v] if up_gal_v else []
                    existing_gal_vids = m_info[9].split(",") if m_info and m_info[9] else []
                    final_gal_vids = ",".join(filter(None, existing_gal_vids + gal_vids))

                    if selected_m_id:
                        database.exec_query("UPDATE models SET name=?, category=?, base_price=?, currency=?, port_discount=?, compatible_options=?, specs=?, image_path=?, gallery_images=?, gallery_videos=? WHERE id=?", 
                                            (mn, m_cat, mp, m_curr, m_disc, final_opts_str, final_specs_str, m_img_path, final_gal_imgs, final_gal_vids, selected_m_id))
                        st.success("Makine başarıyla güncellendi!")
                    else:
                        database.exec_query("INSERT INTO models (name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                            (mn, m_cat, mp, m_curr, m_disc, final_opts_str, final_specs_str, m_img_path, final_gal_imgs, final_gal_vids))
                        st.success("Yeni makine sisteme eklendi!")
                    
                    st.session_state.machine_specs_list = []
                    st.session_state.current_editing_m_id = None
                    st.rerun()
                else:
                    st.error("Makine adı zorunludur.")
            
            if m_info:
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Makineyi Kökten Sil", use_container_width=True):
                        database.exec_query("DELETE FROM models WHERE id=?", (selected_m_id,))
                        st.session_state.machine_specs_list = []
                        st.session_state.current_editing_m_id = None
                        st.rerun()
                with col_btn2:
                    if st.button("📄 Kopyasını Oluştur (Yeni ID)", use_container_width=True):
                        database.exec_query("INSERT INTO models (name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                            (f"{m_info[0]} (Kopya)", m_info[1], m_info[2], m_info[3], m_info[4], m_info[5], m_info[6], m_info[7], m_info[8], m_info[9]))
                        st.rerun()

    # =================================================================
    # SEKME 2: DONANIM HAVUZU (OPTIONS) (CANLI ÖNİZLEMELİ)
    # =================================================================
    with tab_o:
        o_data = database.get_query("SELECT id, sort_order, category, opt_name, opt_price, currency, remove_keyword, opt_image FROM options ORDER BY sort_order ASC, id ASC")
        if o_data:
            df_o = pd.DataFrame(o_data, columns=["ID", "Sıra", "Uyumlu Makine Grubu", "Donanım Adı", "Fiyat", "Birim", "Çakışma", "Resim Yolu"])
            st.dataframe(df_o.drop(columns=["ID"]), use_container_width=True)
        else:
            st.info("Kayıtlı donanım bulunamadı.")
            
        st.markdown("---")
        o_action = st.radio("İşlem Seçin (Donanım)", ["➕ Yeni Donanım Ekle", "📝 Düzenle / Sil / Kopyala"], horizontal=True)
        
        selected_o_id, o_info = None, None
        
        if o_action == "📝 Düzenle / Sil / Kopyala":
            if o_data:
                o_options = [f"{row[0]} - {row[3]}" for row in o_data]
                sel_o_str = st.selectbox("İşlem yapılacak donanımı seçin:", o_options)
                selected_o_id = int(sel_o_str.split(" - ")[0])
                o_info = database.get_query("SELECT opt_name, category, opt_price, currency, remove_keyword, opt_desc, sort_order, opt_image, video_path FROM options WHERE id=?", (selected_o_id,))[0]
        
        if o_action == "➕ Yeni Donanım Ekle" or o_info:
            with st.form("option_form"):
                on = st.text_input("Donanım Adı *", value=o_info[0] if o_info else "")
                o_cat = st.selectbox("Uyumlu Makine Grubu", ["Genel / Tüm Makineler"] + cat_list, index=(["Genel / Tüm Makineler"] + cat_list).index(o_info[1]) if o_info and o_info[1] in (["Genel / Tüm Makineler"] + cat_list) else 0)
                
                col1, col2, col3 = st.columns(3)
                op = col1.number_input("Fiyat", min_value=0.0, value=float(o_info[2]) if o_info else 0.0)
                o_curr = col2.selectbox("Para Birimi ", ["USD", "EUR", "RMB", "TRY"], index=["USD", "EUR", "RMB", "TRY"].index(o_info[3]) if o_info and o_info[3] in ["USD", "EUR", "RMB", "TRY"] else 0)
                o_sort = col3.number_input("Sıralama Önceliği", min_value=0, value=int(o_info[6]) if o_info else 0)
                
                o_rem = st.text_input("Çakışma Özelliği (Opsiyonel)", value=o_info[4] if o_info else "")
                o_desc = st.text_area("Teknik Açıklama", value=o_info[5] if o_info else "")

                st.markdown("#### 🖼️ Medya Yükleme (Canlı Önizleme)")
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    o_up_img = st.file_uploader("Donanım Resmi", type=['png','jpg','jpeg'], key="o_img")
                    if o_up_img:
                        st.image(o_up_img, caption="Yeni Resim", width=150)
                    elif o_info and o_info[7] and os.path.isfile(o_info[7]):
                        try:
                            with open(o_info[7], "rb") as f: st.image(f.read(), caption="Mevcut Resim", width=150)
                        except: pass
                        
                with col_o2:
                    o_up_vid = st.file_uploader("Donanım Videosu", type=['mp4','avi','mov'], key="o_vid")
                
                submit_o = st.form_submit_button("💾 DONANIMI KAYDET", use_container_width=True, type="primary")
                
            if submit_o:
                if on:
                    opt_img_path = save_uploaded_file(o_up_img, "images") if o_up_img else (o_info[7] if o_info else "")
                    opt_vid_path = save_uploaded_file(o_up_vid, "images") if o_up_vid else (o_info[8] if o_info else "")

                    if selected_o_id:
                        database.exec_query("UPDATE options SET opt_name=?, category=?, opt_price=?, currency=?, remove_keyword=?, opt_desc=?, sort_order=?, opt_image=?, video_path=? WHERE id=?", 
                                            (on, o_cat, op, o_curr, o_rem, o_desc, o_sort, opt_img_path, opt_vid_path, selected_o_id))
                        st.success("Donanım güncellendi!")
                    else:
                        database.exec_query("INSERT INTO options (opt_name, category, opt_price, currency, remove_keyword, opt_desc, sort_order, opt_image, video_path) VALUES (?,?,?,?,?,?,?,?,?)", 
                                            (on, o_cat, op, o_curr, o_rem, o_desc, o_sort, opt_img_path, opt_vid_path))
                        st.success("Yeni donanım eklendi!")
                    st.rerun()
                else:
                    st.error("Donanım adı zorunludur.")
            
            if o_info:
                st.markdown("---")
                cb1, cb2 = st.columns(2)
                with cb1:
                    if st.button("🗑️ Donanımı Sil", use_container_width=True):
                        database.exec_query("DELETE FROM options WHERE id=?", (selected_o_id,))
                        st.rerun()
                with cb2:
                    if st.button("📄 Kopyasını Oluştur", use_container_width=True):
                        database.exec_query("INSERT INTO options (opt_name, category, opt_price, currency, remove_keyword, opt_desc, sort_order, opt_image, video_path) VALUES (?,?,?,?,?,?,?,?,?)", 
                                            (f"{o_info[0]} (Kopya)", o_info[1], o_info[2], o_info[3], o_info[4], o_info[5], o_info[6], o_info[7], o_info[8]))
                        st.rerun()

    # =================================================================
    # SEKME 3: KATEGORİLER (CANLI ÖNİZLEMELİ)
    # =================================================================
    with tab_c:
        c_data = database.get_query("SELECT id, name, image_path FROM categories ORDER BY id")
        if c_data:
            df_c = pd.DataFrame(c_data, columns=["ID", "Kategori Adı", "Resim Yolu"])
            st.dataframe(df_c.drop(columns=["ID"]), use_container_width=True)
            
            st.markdown("---")
            c_action = st.radio("İşlem Seçin (Kategori)", ["➕ Yeni Kategori Ekle", "📝 Düzenle / Sil"], horizontal=True)
            
            selected_c_id, c_info = None, None
            
            if c_action == "📝 Düzenle / Sil":
                c_options = [f"{row[0]} - {row[1]}" for row in c_data]
                sel_c_str = st.selectbox("İşlem yapılacak kategoriyi seçin:", c_options)
                selected_c_id = int(sel_c_str.split(" - ")[0])
                c_info = database.get_query("SELECT name, image_path FROM categories WHERE id=?", (selected_c_id,))[0]
            
            if c_action == "➕ Yeni Kategori Ekle" or c_info:
                with st.form("cat_form"):
                    cn = st.text_input("Kategori Adı *", value=c_info[0] if c_info else "")
                    
                    c_up_img = st.file_uploader("Kategori Resmi Yükle", type=['png','jpg','jpeg'], key="c_img")
                    if c_up_img:
                        st.image(c_up_img, caption="Yeni Kategori Resmi", width=150)
                    elif c_info and c_info[1] and os.path.isfile(c_info[1]):
                        try:
                            with open(c_info[1], "rb") as f: st.image(f.read(), caption="Mevcut Resim", width=150)
                        except: pass

                    submit_c = st.form_submit_button("💾 KATEGORİYİ KAYDET", use_container_width=True, type="primary")
                    
                if submit_c:
                    if cn:
                        cat_img_path = save_uploaded_file(c_up_img, "images") if c_up_img else (c_info[1] if c_info else "")

                        if selected_c_id:
                            database.exec_query("UPDATE categories SET name=?, image_path=? WHERE id=?", (cn, cat_img_path, selected_c_id))
                            st.success("Kategori güncellendi!")
                        else:
                            database.exec_query("INSERT INTO categories (name, image_path) VALUES (?,?)", (cn, cat_img_path))
                            st.success("Yeni kategori eklendi!")
                        st.rerun()
                
                if c_info:
                    st.markdown("---")
                    if st.button("🗑️ Kategoriyi Sil", use_container_width=True):
                        database.exec_query("DELETE FROM categories WHERE id=?", (selected_c_id,))
                        st.rerun()
