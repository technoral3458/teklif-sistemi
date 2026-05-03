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
            st.session_state.form_loaded = False # Yeni forma girerken hafızayı temizle
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
                    for i in range(0, len(cat_mods), 3):
                        cols = st.columns(3, gap="medium")
                        for j in range(3):
                            if i + j < len(cat_mods):
                                row = cat_mods.iloc[i + j]
                                safe_mod_id = int(row['id']) 
                                
                                with cols[j].container(border=True):
                                    img_b64 = get_image_base64(row['image'])
                                    if img_b64: st.markdown(f'<div style="text-align:center;"><img src="{img_b64}" style="width:100%; height:180px; object-fit:contain; margin-bottom:15px;"></div>', unsafe_allow_html=True)
                                    else: st.markdown("<div style='height:180px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#94a3b8; font-size:13px; margin-bottom:15px;'>Görsel Yok</div>", unsafe_allow_html=True)
                                    
                                    st.markdown(f"<h4 style='margin:0; color:#0f172a; font-size:16px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>{row['name']}</h4>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#ea580c; font-weight:800; font-size:18px; margin-bottom:15px;'>{row['price']:,.2f} {row['currency']}</div>", unsafe_allow_html=True)
                                    
                                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                                    if btn_c1.button("✏️", key=f"e_{safe_mod_id}", help="Düzenle", use_container_width=True):
                                        st.session_state.edit_mod_id = safe_mod_id
                                        st.session_state.form_loaded = False
                                        st.session_state.mod_view_mode = "edit"
                                        st.rerun()
                                        
                                    if btn_c2.button("📄", key=f"c_{safe_mod_id}", help="Kopyala", use_container_width=True):
                                        m_data = get_factory("SELECT name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos FROM models WHERE id=?", (safe_mod_id,))[0]
                                        exec_factory("""INSERT INTO models (name, base_price, image_path, specs, currency, port_discount, compatible_options, gallery_images, category, gallery_videos) 
                                                        VALUES (?,?,?,?,?,?,?,?,?,?)""", 
                                                     (m_data[0] + " (Kopya)", m_data[1], m_data[2], m_data[3], m_data[4], m_data[5], m_data[6], m_data[7], m_data[8], m_data[9]))
                                        st.success("Makine kopyalandı!"); st.rerun()
                                        
                                    if btn_c3.button("🗑️", key=f"d_{safe_mod_id}", help="Sil", use_container_width=True):
                                        exec_factory("DELETE FROM models WHERE id=?", (safe_mod_id,))
                                        st.error("Makine silindi!"); st.rerun()
        else: st.info("Sistemde henüz bir makine bulunmuyor.")

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
                    try: exec_factory("INSERT INTO categories (name) VALUES (?)", (n_cat,)); st.rerun()
                    except: st.error("Bu kategori zaten var!")

# =====================================================================
# GÖRÜNÜM 2: GELİŞMİŞ VE DİNAMİK TAM SAYFA FORM
# =====================================================================
def show_form_view(mode="add", mod_id=None):
    # Üst Bar ve Geri Dönüş
    col_back, col_title = st.columns([1, 5], vertical_alignment="center")
    if col_back.button("🔙 Listeye Dön", use_container_width=True):
        st.session_state.mod_view_mode = "list"
        st.rerun()
    
    is_edit = (mode == "edit" and mod_id is not None)
    col_title.header("✏️ Makine Kartı Düzenleyici" if is_edit else "✨ Yeni Makine Kartı Oluştur")
    st.markdown("---")

    # --- 1. HAFIZA (STATE) YÖNETİMİ ---
    # Form ilk kez açıldığında veritabanından verileri çekip hafızaya alıyoruz.
    if not st.session_state.get("form_loaded", False):
        st.session_state.form_loaded = True
        
        cats_list = [c[1] for c in get_factory("SELECT id, name FROM categories")]
        st.session_state.f_cats_list = cats_list if cats_list else ["Diğer Makinalar"]
        
        if is_edit:
            res = get_factory("SELECT name, base_price, currency, category, port_discount, image_path, specs, compatible_options FROM models WHERE id=?", (int(mod_id),))
            r = res[0]
            st.session_state.f_name = r[0]
            st.session_state.f_price = float(r[1])
            st.session_state.f_curr = r[2]
            st.session_state.f_cat = r[3]
            st.session_state.f_disc = float(r[4])
            st.session_state.f_img = r[5]
            
            # Specs'i parçalayıp dinamik satırlar için listeye çeviriyoruz
            s_list = []
            if r[6]:
                for item in str(r[6]).split("||"):
                    if item.strip():
                        parts = item.split("|")
                        s_list.append({
                            "title": parts[0].strip() if len(parts) > 0 else "",
                            "detail": parts[1].strip() if len(parts) > 1 else "",
                            "img": parts[2].strip() if len(parts) > 2 else ""
                        })
            st.session_state.f_specs = s_list if s_list else [{"title": "", "detail": "", "img": ""}]
            
            # Donanımları parse et
            st.session_state.f_opts = [x.strip() for x in str(r[7]).split(",") if x.strip()]
        else:
            st.session_state.f_name = ""
            st.session_state.f_price = 0.0
            st.session_state.f_curr = "USD"
            st.session_state.f_cat = st.session_state.f_cats_list[0]
            st.session_state.f_disc = 0.0
            st.session_state.f_img = ""
            st.session_state.f_specs = [{"title": "", "detail": "", "img": ""}]
            st.session_state.f_opts = []

    # --- 2. PROFESYONEL SEKME (TAB) YAPISI ---
    tab_genel, tab_teknik, tab_donanim = st.tabs(["📄 Genel Bilgiler", "⚙️ Teknik Özellikler", "🔌 Uyumlu Ekstra Donanımlar"])
    
    # 2.A - GENEL BİLGİLER SEKME
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
            st.session_state.f_img = st.text_input("Ana Resim Yolu (Örn: makine_resmi.png)", value=st.session_state.f_img)
        
        with c2:
            st.markdown("**Görsel Önizleme**")
            prev_img = get_image_base64(st.session_state.f_img)
            if prev_img: st.markdown(f'<img src="{prev_img}" style="width:100%; border-radius:8px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
            else: st.markdown("<div style='height:200px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border:2px dashed #cbd5e1; border-radius:8px; color:#94a3b8;'>Görsel Yok</div>", unsafe_allow_html=True)

    # 2.B - DİNAMİK TEKNİK ÖZELLİKLER (Masaüstü Programı Mantığı)
    with tab_teknik:
        st.info("💡 Özellikleri alt alta ekleyin. İşlemi bitirdiğinizde kaydet butonuna basmayı unutmayın.")
        
        # Dinamik satırların oluşturulması
        for i in range(len(st.session_state.f_specs)):
            col_t, col_d, col_i, col_x = st.columns([3, 4, 2, 0.5], vertical_alignment="center")
            
            st.session_state.f_specs[i]["title"] = col_t.text_input("Başlık", value=st.session_state.f_specs[i]["title"], key=f"t_{i}", label_visibility="collapsed", placeholder="Başlık (Örn: Cnc Kontrol Sistemi)")
            st.session_state.f_specs[i]["detail"] = col_d.text_input("Detay", value=st.session_state.f_specs[i]["detail"], key=f"d_{i}", label_visibility="collapsed", placeholder="Teknik Detay (Örn: Delta NC50E)")
            st.session_state.f_specs[i]["img"] = col_i.text_input("Resim", value=st.session_state.f_specs[i]["img"], key=f"i_{i}", label_visibility="collapsed", placeholder="İkon (Örn: delta.png)")
            
            if col_x.button("❌", key=f"del_spec_{i}", help="Satırı Sil"):
                st.session_state.f_specs.pop(i)
                st.rerun()

        if st.button("➕ YENİ ÖZELLİK SATIRI EKLE", use_container_width=True):
            st.session_state.f_specs.append({"title": "", "detail": "", "img": ""})
            st.rerun()

    # 2.C - İŞARETLEMELİ (CHECKBOX) UYUMLU DONANIMLAR
    with tab_donanim:
        st.write("Makine ile uyumlu olan opsiyonel donanımları işaretleyiniz:")
        opts_avail = get_factory("SELECT id, opt_name, opt_price FROM options ORDER BY opt_price DESC")
        
        new_opts = [] # İşaretlenenleri toplayacağımız liste
        
        # Seçenekleri 3 sütunlu ızgaraya dizelim
        chk_cols = st.columns(3)
        for idx, opt in enumerate(opts_avail):
            o_id, o_name, o_price = opt
            is_checked = str(o_id) in st.session_state.f_opts
            
            with chk_cols[idx % 3]:
                if st.checkbox(f"{o_name} (+{o_price:,.0f})", value=is_checked, key=f"chk_{o_id}"):
                    new_opts.append(str(o_id))
                    
        st.session_state.f_opts = new_opts

    st.markdown("---")
    
    # --- 3. KAYDETME MOTORU ---
    if st.button("💾 " + ("DEĞİŞİKLİKLERİ KAYDET" if is_edit else "MAKİNEYİ SİSTEME EKLE"), type="primary", use_container_width=True):
        if not st.session_state.f_name or st.session_state.f_price <= 0:
            st.error("Lütfen makine adı ve geçerli bir fiyat girin!")
        else:
            # Dinamik tabloyu veritabanının anladığı formata (||) dönüştür
            spec_strs = []
            for sp in st.session_state.f_specs:
                if sp["title"].strip() or sp["detail"].strip():
                    spec_strs.append(f"{sp['title']}|{sp['detail']}|{sp['img']}")
            
            final_specs_str = " || ".join(spec_strs) + (" || " if spec_strs else "")
            final_opts_str = ",".join(st.session_state.f_opts)
            
            if is_edit:
                exec_factory("""UPDATE models SET name=?, category=?, base_price=?, currency=?, specs=?, compatible_options=?, port_discount=?, image_path=? WHERE id=?""", 
                             (st.session_state.f_name, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, 
                              final_specs_str, final_opts_str, st.session_state.f_disc, st.session_state.f_img, int(mod_id)))
                st.success("Makine başarıyla güncellendi!")
            else:
                exec_factory("""INSERT INTO models (name, category, base_price, currency, specs, compatible_options, port_discount, image_path) 
                                VALUES (?,?,?,?,?,?,?,?)""", 
                             (st.session_state.f_name, st.session_state.f_cat, st.session_state.f_price, st.session_state.f_curr, 
                              final_specs_str, final_opts_str, st.session_state.f_disc, st.session_state.f_img))
                st.success("Yeni makine başarıyla eklendi!")
            
            st.session_state.mod_view_mode = "list"
            st.rerun()
