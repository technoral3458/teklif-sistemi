import streamlit as st
import sqlite3
import pandas as pd

# DOĞRUDAN SİZİN FABRİKA VERİTABANINIZA BAĞLANIR
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
    conn = sqlite3.connect('factory_data.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def show_product_management():
    st.header(":package: Fabrika Veritabanı Yönetimi (Modeller & Donanımlar)")
    
    # Eksik tablo varsa sistemi korumak için oluştur (Sizin verileriniz silinmez)
    exec_factory("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    exec_factory("CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, opt_name TEXT, opt_desc TEXT, opt_price REAL, opt_image TEXT, sort_order INTEGER DEFAULT 0)")
    exec_factory("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_price REAL, image_path TEXT, 
        specs TEXT, currency TEXT DEFAULT 'USD', port_discount REAL DEFAULT 0.0, 
        compatible_options TEXT DEFAULT '', gallery_images TEXT DEFAULT '', category TEXT DEFAULT 'Diğer Makinalar', gallery_videos TEXT DEFAULT '')""")

    tab_mod, tab_opt, tab_cat = st.tabs(["📦 Sistemdeki Modeller", "⚙️ Ekstra Donanımlar", "📂 Kategoriler"])
    
    # ---------------- 1. KATEGORİLER ----------------
    with tab_cat:
        c1, c2 = st.columns([2,1])
        with c1:
            st.subheader("Mevcut Kategoriler")
            cats = get_factory("SELECT id, name FROM categories")
            if cats:
                for cid, cname in cats:
                    col_a, col_b = st.columns([4,1])
                    col_a.write(f"- {cname}")
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

    # ---------------- 2. DONANIMLAR ----------------
    with tab_opt:
        st.subheader("Kayıtlı Donanım Listesi")
        opts = get_factory("SELECT id, opt_name, opt_price, opt_desc FROM options")
        if opts:
            df_opts = pd.DataFrame(opts, columns=["ID", "Donanım Adı", "Fiyat", "Açıklama"])
            st.dataframe(df_opts.set_index("ID"), use_container_width=True)
            
            # Donanım silme alanı
            del_opt_id = st.selectbox("Silmek istediğiniz donanımı seçin:", ["Seçiniz..."] + [f"{o[0]} - {o[1]}" for o in opts])
            if st.button("Seçili Donanımı Sil") and del_opt_id != "Seçiniz...":
                o_id = del_opt_id.split(" - ")[0]
                exec_factory("DELETE FROM options WHERE id=?", (o_id,))
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

    # ---------------- 3. MODELLER / MAKİNELER ----------------
    with tab_mod:
        st.subheader("Kayıtlı Makineler")
        mods = get_factory("SELECT id, name, category, base_price, currency FROM models")
        if mods:
            for mid, mname, mcat, mprice, mcurr in mods:
                with st.container(border=True):
                    c_a, c_b = st.columns([4,1])
                    c_a.markdown(f"**{mname}**<br><small>{mcat} | {mprice:,.2f} {mcurr}</small>", unsafe_allow_html=True)
                    if c_b.button("Sil", key=f"del_mod_{mid}"):
                        exec_factory("DELETE FROM models WHERE id=?", (mid,))
                        st.rerun()
        else:
            st.error("Veritabanında makine bulunamadı. Lütfen fabrika dosyasının ('factory_data.db') ana dizinde olduğundan emin olun.")
        
        with st.expander("➕ Yeni Makine Ekle"):
            with st.form("new_mod"):
                m_name = st.text_input("Makine Modeli Adı")
                cats_list = [c[1] for c in get_factory("SELECT id, name FROM categories")]
                m_cat = st.selectbox("Kategori", cats_list if cats_list else ["Diğer Makinalar"])
                
                c1, c2 = st.columns(2)
                m_price = c1.number_input("Baz Fiyat", min_value=0.0, step=100.0)
                m_curr = c2.selectbox("Para Birimi", ["USD", "EUR", "TRY"])
                
                m_specs = st.text_area("Standart Özellikler (Format: Özellik|Açıklama|resim_adi.png ||)")
                
                opts_avail = get_factory("SELECT id, opt_name FROM options")
                sel_opts = st.multiselect("Uyumlu Donanımlar", [f"{o[0]} - {o[1]}" for o in opts_avail])
                
                m_disc = st.number_input("Limandan Devir İskontosu (%)", min_value=0.0, max_value=100.0, value=0.0)
                
                if st.form_submit_button("Makineyi Kaydet", type="primary") and m_name:
                    opt_ids = ",".join([s.split(" - ")[0] for s in sel_opts])
                    exec_factory("""INSERT INTO models (name, category, base_price, currency, specs, compatible_options, port_discount) 
                                    VALUES (?,?,?,?,?,?,?)""", 
                                 (m_name, m_cat, m_price, m_curr, m_specs, opt_ids, m_disc))
                    st.success("Makine eklendi!"); st.rerun()
