import streamlit as st
import sqlite3
import pandas as pd
import os
import base64

# =====================================================================
# FABRİKA VERİTABANI BAĞLANTILARI
# =====================================================================
def get_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall()
        conn.close()
        return res
    except Exception as e: 
        st.error(f"Veritabanı Okuma Hatası: {e}")
        return []

def exec_factory(query, params=()):
    try:
        conn = sqlite3.connect('factory_data.db')
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Veritabanı Yazma Hatası: {e}")

# Görseli Base64'e Çevir (Küçük Resimler İçin)
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

# =====================================================================
# ANA YÖNETİM MODÜLÜ (SAYFA GEÇİŞ MOTORU)
# =====================================================================
def show_product_management():
    exec_factory("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    exec_factory("CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_desc TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)")
    exec_factory("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, 
        specs TEXT, currency TEXT DEFAULT 'USD', port_discount REAL DEFAULT 0.0, 
        compatible_options TEXT DEFAULT '', gallery_images TEXT DEFAULT '', category TEXT DEFAULT 'Diğer Makinalar', gallery_videos TEXT DEFAULT '')""")

    if "mod_view_mode" not in st.session_state: st.session_state.mod_view_mode = "list"
    if "edit_mod_id" not in st.session_state: st.session_state.edit_mod_id = None

    if st.session_state.mod_view_mode == "list":
        show_list_view()
    elif st.session_state.mod_view_mode == "add":
        show_form_view(mode="add")
    elif st.session_state.mod_view_mode == "edit":
        show_form_view(mode="edit", mod_id=st.session_state.edit_mod_id)

# =====================================================================
# GÖRÜNÜM 1: KATEGORİLİ VE 3'LÜ VİTRİN TİPİ LİSTE
# =====================================================================
def show_list_view():
    st.header(":package: Fabrika Veritabanı Yönetimi")
    tab_mod, tab_opt, tab_cat = st.tabs(["📦 Modeller (Vitrin)", "⚙️ Ekstra Donanımlar", "📂 Kategoriler"])
    
    with tab_mod:
        col_title, col_add = st.columns([3, 1])
        col_title.subheader("Kayıtlı Makineler")
        if col_add.button("➕ YENİ MAKİNE EKLE", type="primary", use_container_width=True):
            st.session_state.mod_view_mode = "add"
            st.rerun()

        st.markdown("---")
        
        mods = get_factory("SELECT id, name, category, base_price, currency, image_path FROM models ORDER BY category ASC, name ASC")
        if mods:
            df_mods = pd.DataFrame(mods, columns=["id", "name", "category", "price", "currency", "image"])
            categories = df_mods['category'].unique()
            
            for cat in categories:
                with st.expander(f"📁 {cat}", expanded=True):
                    cat_mods = df_mods[df_mods['category'] == cat].reset_index(drop=True)
                    
                    # 3'LÜ GRID (IZGARA) SİSTEMİ MANTIĞI
                    for i in range(0, len(cat_mods), 3):
                        cols = st.columns(3, gap="medium")
                        for j in range(3):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                with cols[j].container(border=True):
                                    
                                    # Yüksek ve Net Görsel Alanı
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64:
                                        st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:180px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else:
                                        st.markdown("<div style='height:180px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>Görsel Yok</div>", unsafe_allow_html=True)
                                    
                                    # Başlık ve Fiyat Alanı (Uzun isimler taşmasın diye CSS ile kırpılır)
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:16px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>{row['name']}</h4>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:18px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                    
                                    # Yan Yana 3 Aksiyon Butonu
                                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                                    if btn_c1.button("✏️", key=f"e_{row['id']}", help="Düzenle", use_container_width=True):
                                        st.session_state.edit_mod_id = row['id']
                                        st.session_state.mod_view_mode = "edit"
                                        st.rerun()
                                        
                                    if btn_c2.button("📄", key=f"c_{row['id']}", help="Kopyala", use_container_width=True):
                                        m_data = get_factory("SELECT name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos FROM models WHERE id=?", (row['id'],))[0]
                                        exec_factory("""INSERT INTO models (name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos) 
                                                        VALUES (?,?,?,?,?,?,?,?,?,?)""", 
                                                     (m_data[0] + " (Kopya)", m_data[1], m_data[2], m_data[3], m_data[4], m_data[5], m_data[6], m_data[7], m_data[8], m_data[9]))
                                        st.success("Makine başarıyla çoğaltıldı!"); st.rerun()
                                        
                                    if btn_c3.button("🗑️", key=f"d_{row['id']}", help="Sil", use_container_width=True):
                                        exec_factory("DELETE FROM models WHERE id=?", (row['id'],))
                                        st.error("Makine silindi!"); st.rerun()
        else:
            st.info("Sistemde henüz bir makine bulunmuyor.")

    with tab_opt:
        st.subheader("Kayıtlı Donanım Listesi")
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc FROM options")
        if opts:
            df_opts = pd.DataFrame(opts, columns=["ID", "Donanım Adı", "Fiyat", "Açıklama"])
            st.dataframe(df_opts.set_index("ID"), use_container_width=True)
            del_opt_id = st.selectbox("Silmek istediğiniz donanımı seçin:", ["Seçiniz..."] + [f"{o[0]} - {o[1]}" for o in opts])
            if st.button("Seçili Donanımı Sil") and del_opt_id != "Seçiniz...":
                exec_factory("DELETE FROM options WHERE id=?", (del_opt_id.split(" - ")[0],))
                st.success("Silindi!"); st.rerun()
        else: st.info("Sistemde kayıtlı donanım bulunamadı.")
        
        with st.expander("➕ Yeni Donanım Ekle"):
            with st.form("new_opt"):
                o_name = st.text_input("Donanım Adı")
                o_desc = st.text_area("Açıklama (Opsiyonel)")
                o_price = st.number_input("Fiyat", min_value=0.0, step=10.0)
                if st.form_submit_button("Donanımı Kaydet") and o_name:
                    exec_factory("INSERT INTO options (opt_name, opt_desc, opt_price) VALUES (?,?,?)", (o_name, o_desc, o_price))
                    st.success("Eklendi!"); st.rerun()

    with tab_cat:
        c1, c2 = st.columns([2,1])
        with c1:
            st.subheader("Mevcut Kategoriler")
            cats = get_factory("SELECT id, name FROM categories")
            if cats:
                for cid, cname in cats:
                    col_a, col_b = st.columns([4,1])
                    col_a.write(f"📁 {cname}")
                    if col_b.button("Sil", key=f"del_cat_{cid}"):
                        exec_factory("DELETE FROM categories WHERE id=?", (cid,))
                        st.rerun()
            else: st.info("Sistemde kategori bulunamadı.")
        with c2:
            st.subheader("Yeni Ekle")
            with st.form("new_cat"):
                n_cat = st.text_input("Kategori Adı")
                if st.form_submit_button("Ekle") and n_cat:
                    try:
                        exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat,))
                        st.rerun()
                    except: st.error("Bu kategori zaten var!")

# =====================================================================
# GÖRÜNÜM 2: TAM SAYFA EKLEME / DÜZENLEME FORMU
# =====================================================================
def show_form_view(mode="add", mod_id=None):
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.mod_view_mode = "list"
        st.rerun()
    
    is_edit = (mode == "edit" and mod_id is not None)
    col_title.header("✏️ Makineyi Düzenle" if is_edit else "✨ Yeni Makine Ekle")
    st.markdown("---")

    existing_data = {}
    if is_edit:
        res = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options FROM models WHERE id=?", (mod_id,))
        if res:
            r = res[0]
            existing_data = {"name": r[0], "price": r[1], "curr": r[2], "cat": r[3], "disc": r[4], "img": r[5], "specs": r[6], "opts": str(r[7]).split(",") if r[7] else []}

    opts_avail = get_factory("SELECT id, opt_name FROM options")
    opt_list_full = [f"{o[0]} - {o[1]}" for o in opts_avail]
    
    pre_selected_opts = []
    if is_edit and existing_data.get("opts"):
        saved_ids = [x.strip() for x in existing_data["opts"] if x.strip()]
        pre_selected_opts = [opt for opt in opt_list_full if opt.split(" - ")[0] in saved_ids]

    cats_list = [c[1] for c in get_factory("SELECT id, name FROM categories")]
    if not cats_list: cats_list = ["Diğer Makinalar"]

    with st.container(border=True):
        m_name = st.text_input("Makine Modeli Adı *", value=existing_data.get("name", ""))
        
        c1, c2, c3 = st.columns(3)
        m_cat = c1.selectbox("Kategori", cats_list, index=cats_list.index(existing_data.get("cat")) if existing_data.get("cat") in cats_list else 0)
        m_price = c2.number_input("Baz Fiyat *", min_value=0.0, value=float(existing_data.get("price", 0.0)), step=100.0)
        m_curr = c3.selectbox("Para Birimi", ["USD", "EUR", "TRY"], index=["USD", "EUR", "TRY"].index(existing_data.get("curr", "USD")))
        
        c4, c5 = st.columns(2)
        m_disc = c4.number_input("İskonto (%)", min_value=0.0, max_value=100.0, value=float(existing_data.get("disc", 0.0)))
        
        st.markdown("<small style='color:#64748b;'>*Makinenin ana görsel adını girin (Örn: machine_na2136.png). Görseller klasörde bulunmalıdır.*</small>", unsafe_allow_html=True)
        m_img = c5.text_input("Ana Görsel Dosya Adı", value=existing_data.get("img", ""))

        m_specs = st.text_area("Standart Özellikler", value=existing_data.get("specs", ""), height=150, help="Format: Özellik|Açıklama|resim_adi.png ||")
        
        sel_opts = st.multiselect("Uyumlu Ekstra Donanımlar", options=opt_list_full, default=pre_selected_opts)

        st.write("")
        btn_col_a, btn_col_b, btn_col_c = st.columns([1, 1, 1])
        
        if btn_col_b.button("💾 " + ("DEĞİŞİKLİKLERİ KAYDET" if is_edit else "MAKİNEYİ SİSTEME EKLE"), type="primary", use_container_width=True):
            if not m_name or m_price <= 0:
                st.error("Lütfen makine adı ve geçerli bir fiyat girin!")
            else:
                opt_ids = ",".join([s.split(" - ")[0] for s in sel_opts])
                if is_edit:
                    exec_factory("""UPDATE models SET name=?, category=?, base_price=?, currency=?, specs=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?""", 
                                 (m_name, m_cat, m_price, m_curr, m_specs, opt_ids, m_disc, m_img, mod_id))
                    st.success("Makine başarıyla güncellendi!")
                else:
                    exec_factory("""INSERT INTO models (name, category, base_price, currency, specs, compatible_options, port_discount, image_path) 
                                    VALUES (?,?,?,?,?,?,?,?)""", 
                                 (m_name, m_cat, m_price, m_curr, m_specs, opt_ids, m_disc, m_img))
                    st.success("Yeni makine başarıyla eklendi!")
                st.session_state.mod_view_mode = "list"
                st.rerun()
