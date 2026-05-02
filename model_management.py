import streamlit as st
import database
import pandas as pd
import os
import uuid

# Sunucuya Dosya Kaydetme Motoru
def save_uploaded_file(uploaded_file, folder_name="images"):
    if uploaded_file is None:
        return ""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    ext = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(folder_name, safe_name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

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

def show_product_management():
    init_management_tables()
    cat_list = get_categories()
    
    st.markdown("<h2 style='color: #1e293b;'>Katalog ve Envanter Yönetimi</h2>", unsafe_allow_html=True)
    
    tab_m, tab_o, tab_c = st.tabs(["📦 Makineler", "🔧 Donanım Havuzu", "🗂️ Kategoriler"])

    # ==========================================
    # SEKME 1: MAKİNELER
    # ==========================================
    with tab_m:
        st.subheader("Mevcut Makine Modelleri")
        m_data = database.get_query("SELECT id, category, name, base_price, currency, port_discount, compatible_options, image_path FROM models ORDER BY id DESC")
        if m_data:
            df_m = pd.DataFrame(m_data, columns=["ID", "Kategori", "Model Adı", "Fiyat", "Birim", "İskonto(%)", "Uyumlu Donanımlar", "Resim Yolu"])
            st.dataframe(df_m.drop(columns=["ID"]), use_container_width=True)
        else:
            st.info("Kayıtlı makine bulunamadı.")
            
        st.markdown("---")
        m_action = st.radio("İşlem Seçin (Makine)", ["➕ Yeni Makine Ekle", "📝 Düzenle / Sil / Kopyala"], horizontal=True)
        
        selected_m_id = None
        m_info = None
        
        if m_action == "📝 Düzenle / Sil / Kopyala":
            if m_data:
                m_options = [f"{row[0]} - {row[2]}" for row in m_data]
                selected_m_str = st.selectbox("İşlem yapılacak makineyi seçin:", m_options)
                selected_m_id = int(selected_m_str.split(" - ")[0])
                m_info = database.get_query("SELECT name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos FROM models WHERE id=?", (selected_m_id,))[0]
            else:
                st.warning("Düzenlenecek makine yok.")
        
        if m_action == "➕ Yeni Makine Ekle" or m_info:
            with st.form("machine_form"):
                mn = st.text_input("Makine Adı *", value=m_info[0] if m_info else "")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    m_cat = st.selectbox("Kategori", cat_list, index=cat_list.index(m_info[1]) if m_info and m_info[1] in cat_list else 0)
                with col2:
                    mp = st.number_input("Yurtiçi Fiyat", min_value=0.0, value=float(m_info[2]) if m_info else 0.0)
                with col3:
                    m_curr = st.selectbox("Para Birimi", ["USD", "EUR", "RMB", "TRY"], index=["USD", "EUR", "RMB", "TRY"].index(m_info[3]) if m_info and m_info[3] in ["USD", "EUR", "RMB", "TRY"] else 0)
                with col4:
                    m_disc = st.number_input("Liman İskontosu (%)", min_value=0.0, value=float(m_info[4]) if m_info else 0.0)
                
                # --- YENİ EKLENEN AKILLI DONANIM SEÇİCİ ---
                st.markdown("#### ⚙️ Uyumlu Donanımları Seçin")
                
                all_opts = database.get_query("SELECT id, opt_name, category, opt_price, currency FROM options ORDER BY category, opt_name")
                opt_display_list = []
                opt_map = {}
                id_to_display = {}

                if all_opts:
                    for oid, oname, ocat, oprice, ocurr in all_opts:
                        disp = f"{oname} [{ocat}] (+{oprice} {ocurr})"
                        opt_display_list.append(disp)
                        opt_map[disp] = str(oid) # Ekranda görünen isim -> Veritabanı ID'si
                        id_to_display[str(oid)] = disp # Veritabanı ID'si -> Ekranda Görünen İsim

                default_opts = []
                if m_info and m_info[5]:
                    saved_ids = [x.strip() for x in str(m_info[5]).split(",") if x.strip()]
                    default_opts = [id_to_display[sid] for sid in saved_ids if sid in id_to_display]

                selected_opt_names = st.multiselect("Bu makineyle satılabilecek donanımları listeden seçin:", options=opt_display_list, default=default_opts)
                # ----------------------------------------
                
                m_specs = st.text_area("Teknik Özellikler (Katalog Görünümü, || ve | ile ayırarak)", value=m_info[6] if m_info else "")
                
                st.markdown("#### 🖼️ Medya Yükleme")
                if m_info and m_info[7]:
                    st.write(f"Mevcut Ana Resim: `{m_info[7]}`")
                uploaded_main_img = st.file_uploader("Ana Makine Resmi Yükle (Değiştirmek veya eklemek için)", type=['png', 'jpg', 'jpeg'])
                
                uploaded_gal_img = st.file_uploader("Galeri Resimleri Yükle (Çoklu Seçim)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
                uploaded_gal_vid = st.file_uploader("Galeri Videoları Yükle (Çoklu Seçim)", type=['mp4', 'avi', 'mov'], accept_multiple_files=True)
                
                submit_m = st.form_submit_button("💾 BİLGİLERİ KAYDET", use_container_width=True)
                
            if submit_m:
                if mn:
                    # Seçilen isimleri tekrar virgüllü ID listesine çeviriyoruz (Örn: "1,4,7")
                    final_opts_str = ",".join([opt_map[name] for name in selected_opt_names])

                    m_img_path = save_uploaded_file(uploaded_main_img, "images") if uploaded_main_img else (m_info[7] if m_info else "")
                    
                    gal_imgs = [save_uploaded_file(img, "images") for img in uploaded_gal_img] if uploaded_gal_img else []
                    existing_gal_imgs = m_info[8].split(",") if m_info and m_info[8] else []
                    final_gal_imgs = ",".join(filter(None, existing_gal_imgs + gal_imgs))

                    gal_vids = [save_uploaded_file(vid, "images") for vid in uploaded_gal_vid] if uploaded_gal_vid else []
                    existing_gal_vids = m_info[9].split(",") if m_info and m_info[9] else []
                    final_gal_vids = ",".join(filter(None, existing_gal_vids + gal_vids))

                    if selected_m_id:
                        database.exec_query("UPDATE models SET name=?, category=?, base_price=?, currency=?, port_discount=?, compatible_options=?, specs=?, image_path=?, gallery_images=?, gallery_videos=? WHERE id=?", 
                                            (mn, m_cat, mp, m_curr, m_disc, final_opts_str, m_specs, m_img_path, final_gal_imgs, final_gal_vids, selected_m_id))
                        st.success("Makine güncellendi!")
                    else:
                        database.exec_query("INSERT INTO models (name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                            (mn, m_cat, mp, m_curr, m_disc, final_opts_str, m_specs, m_img_path, final_gal_imgs, final_gal_vids))
                        st.success("Yeni makine eklendi!")
                    st.rerun()
                else:
                    st.error("Makine adı zorunludur.")
            
            if m_info:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Makineyi Sil", use_container_width=True):
                        database.exec_query("DELETE FROM models WHERE id=?", (selected_m_id,))
                        st.rerun()
                with col_btn2:
                    if st.button("📄 Kopyasını Oluştur", use_container_width=True):
                        database.exec_query("INSERT INTO models (name, category, base_price, currency, port_discount, compatible_options, specs, image_path, gallery_images, gallery_videos) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                            (f"{m_info[0]} (Kopya)", m_info[1], m_info[2], m_info[3], m_info[4], m_info[5], m_info[6], m_info[7], m_info[8], m_info[9]))
                        st.rerun()

    # ==========================================
    # SEKME 2: DONANIM HAVUZU (OPTIONS)
    # ==========================================
    with tab_o:
        st.subheader("Mevcut Ekstra Donanımlar")
        o_data = database.get_query("SELECT id, sort_order, category, opt_name, opt_price, currency, remove_keyword, opt_image FROM options ORDER BY sort_order ASC, id ASC")
        if o_data:
            df_o = pd.DataFrame(o_data, columns=["ID", "Sıra", "Uyumlu Makine Grubu", "Donanım Adı", "Fiyat", "Birim", "Çakışma", "Resim Yolu"])
            st.dataframe(df_o.drop(columns=["ID"]), use_container_width=True)
        else:
            st.info("Kayıtlı donanım bulunamadı.")
            
        st.markdown("---")
        o_action = st.radio("İşlem Seçin (Donanım)", ["➕ Yeni Donanım Ekle", "📝 Düzenle / Sil / Kopyala"], horizontal=True)
        
        selected_o_id = None
        o_info = None
        
        if o_action == "📝 Düzenle / Sil / Kopyala":
            if o_data:
                o_options = [f"{row[0]} - {row[3]}" for row in o_data]
                selected_o_str = st.selectbox("İşlem yapılacak donanımı seçin:", o_options)
                selected_o_id = int(selected_o_str.split(" - ")[0])
                o_info = database.get_query("SELECT opt_name, category, opt_price, currency, remove_keyword, opt_desc, sort_order, opt_image, video_path FROM options WHERE id=?", (selected_o_id,))[0]
        
        if o_action == "➕ Yeni Donanım Ekle" or o_info:
            with st.form("option_form"):
                on = st.text_input("Donanım Adı *", value=o_info[0] if o_info else "")
                o_cat = st.selectbox("Uyumlu Makine Grubu", ["Genel / Tüm Makineler"] + cat_list, index=(["Genel / Tüm Makineler"] + cat_list).index(o_info[1]) if o_info and o_info[1] in (["Genel / Tüm Makineler"] + cat_list) else 0)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    op = st.number_input("Fiyat", min_value=0.0, value=float(o_info[2]) if o_info else 0.0)
                with col2:
                    o_curr = st.selectbox("Para Birimi ", ["USD", "EUR", "RMB", "TRY"], index=["USD", "EUR", "RMB", "TRY"].index(o_info[3]) if o_info and o_info[3] in ["USD", "EUR", "RMB", "TRY"] else 0)
                with col3:
                    o_sort = st.number_input("Listeleme Sırası", min_value=0, value=int(o_info[6]) if o_info else 0)
                
                o_rem = st.text_input("Çakışma Özelliği (Seçilince iptal edilecekler Örn: Spindle, Sürücü)", value=o_info[4] if o_info else "")
                o_desc = st.text_area("Teknik Açıklama", value=o_info[5] if o_info else "")

                st.markdown("#### 🖼️ Medya Yükleme")
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    if o_info and o_info[7]: st.write(f"Mevcut Resim: `{o_info[7]}`")
                    opt_img_upload = st.file_uploader("Donanım Resmi Yükle", type=['png', 'jpg', 'jpeg'])
                with col_o2:
                    if o_info and o_info[8]: st.write(f"Mevcut Video: `{o_info[8]}`")
                    opt_vid_upload = st.file_uploader("Donanım Videosu Yükle", type=['mp4', 'avi', 'mov'])
                
                submit_o = st.form_submit_button("💾 DONANIMI KAYDET", use_container_width=True)
                
            if submit_o:
                if on:
                    opt_img_path = save_uploaded_file(opt_img_upload, "images") if opt_img_upload else (o_info[7] if o_info else "")
                    opt_vid_path = save_uploaded_file(opt_vid_upload, "images") if opt_vid_upload else (o_info[8] if o_info else "")

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
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Donanımı Sil", use_container_width=True):
                        database.exec_query("DELETE FROM options WHERE id=?", (selected_o_id,))
                        st.rerun()
                with col_btn2:
                    if st.button("📄 Kopyasını Oluştur ", use_container_width=True):
                        database.exec_query("INSERT INTO options (opt_name, category, opt_price, currency, remove_keyword, opt_desc, sort_order, opt_image, video_path) VALUES (?,?,?,?,?,?,?,?,?)", 
                                            (f"{o_info[0]} (Kopya)", o_info[1], o_info[2], o_info[3], o_info[4], o_info[5], o_info[6], o_info[7], o_info[8]))
                        st.rerun()

    # ==========================================
    # SEKME 3: KATEGORİLER
    # ==========================================
    with tab_c:
        st.subheader("Sistemdeki Makine Kategorileri")
        c_data = database.get_query("SELECT id, name, image_path FROM categories ORDER BY id")
        if c_data:
            df_c = pd.DataFrame(c_data, columns=["ID", "Kategori Adı", "Resim Yolu"])
            st.dataframe(df_c.drop(columns=["ID"]), use_container_width=True)
            
            st.markdown("---")
            c_action = st.radio("İşlem Seçin (Kategori)", ["➕ Yeni Kategori Ekle", "📝 Düzenle / Sil"], horizontal=True)
            
            selected_c_id = None
            c_info = None
            
            if c_action == "📝 Düzenle / Sil":
                c_options = [f"{row[0]} - {row[1]}" for row in c_data]
                selected_c_str = st.selectbox("İşlem yapılacak kategoriyi seçin:", c_options)
                selected_c_id = int(selected_c_str.split(" - ")[0])
                c_info = database.get_query("SELECT name, image_path FROM categories WHERE id=?", (selected_c_id,))[0]
            
            if c_action == "➕ Yeni Kategori Ekle" or c_info:
                with st.form("cat_form"):
                    cn = st.text_input("Kategori Adı *", value=c_info[0] if c_info else "")
                    
                    if c_info and c_info[1]: st.write(f"Mevcut Kategori Resmi: `{c_info[1]}`")
                    cat_img_upload = st.file_uploader("Kategori Resmi Yükle", type=['png', 'jpg', 'jpeg'])

                    submit_c = st.form_submit_button("💾 KATEGORİYİ KAYDET", use_container_width=True)
                    
                if submit_c:
                    if cn:
                        cat_img_path = save_uploaded_file(cat_img_upload, "images") if cat_img_upload else (c_info[1] if c_info else "")

                        if selected_c_id:
                            database.exec_query("UPDATE categories SET name=?, image_path=? WHERE id=?", (cn, cat_img_path, selected_c_id))
                        else:
                            database.exec_query("INSERT INTO categories (name, image_path) VALUES (?,?)", (cn, cat_img_path))
                        st.rerun()
                
                if c_info:
                    if st.button("🗑️ Kategoriyi Sil", use_container_width=True):
                        database.exec_query("DELETE FROM categories WHERE id=?", (selected_c_id,))
                        st.rerun()
