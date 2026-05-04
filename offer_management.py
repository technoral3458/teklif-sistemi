import streamlit as st
import sqlite3
import pandas as pd
import datetime

# =====================================================================
# VERİTABANI MOTORLARI
# =====================================================================
def get_db_connection(db_name):
    return sqlite3.connect(db_name, check_same_thread=False)

# =====================================================================
# TEKLİF YÖNETİM MODÜLÜ (TAM LİSTE)
# =====================================================================
def show_offer_management(user_id, user_role):
    st.markdown("### 📋 Teklif Listesi ve Durum Yönetimi")
    
    conn_s = get_db_connection('sales_data.db')
    
    # Tüm teklifleri veritabanından çek
    offers_raw = conn_s.execute("SELECT id, customer_id, model_id, total_price, status, user_id, offer_date FROM offers ORDER BY id DESC").fetchall()
    
    if not offers_raw:
        st.info("Sistemde henüz kayıtlı bir teklif bulunmuyor.")
        conn_s.close()
        return

    # Verileri DataFrame'e aktar
    df_offers = pd.DataFrame(offers_raw, columns=["id", "customer_id", "model_id", "total_price", "status", "user_id", "offer_date"])
    
    # İlgili isimleri diğer veritabanlarından çekip eşleştirme
    conn_u = get_db_connection('users.db')
    user_dict = {u[0]: u[1] for u in conn_u.execute("SELECT id, company_name FROM users").fetchall()}
    conn_u.close()

    cust_dict = {c[0]: c[1] for c in conn_s.execute("SELECT id, company_name FROM customers").fetchall()}
    
    conn_f = get_db_connection('factory_data.db')
    mod_dict = {m[0]: m[1] for m in conn_f.execute("SELECT id, name FROM models").fetchall()}
    conn_f.close()

    df_offers['Bayi'] = df_offers['user_id'].map(user_dict).fillna("Bilinmeyen Bayi")
    df_offers['Müşteri'] = df_offers['customer_id'].map(cust_dict).fillna("Bilinmeyen Müşteri")
    df_offers['Model'] = df_offers['model_id'].map(mod_dict).fillna("Bilinmeyen Model")

    # Eğer yönetici değilse sadece kendi tekliflerini görsün
    if user_role != 'admin':
        df_offers = df_offers[df_offers['user_id'] == user_id]

    # --- FİLTRELEME ALANI (Kibar ve Kompakt Tasarım) ---
    with st.expander("🔍 Filtreleme Seçenekleri", expanded=True):
        f1, f2 = st.columns(2)
        if user_role == 'admin':
            bayi_filtresi = f1.selectbox("Bayi Seçimi", ["Tümü"] + list(df_offers['Bayi'].unique()))
        else:
            bayi_filtresi = "Tümü"
            
        durum_filtresi = f2.selectbox("Durum Seçimi", ["Tümü", "Beklemede", "Siparişe Çevir", "Reddedildi"])

    # Filtreleri Uygula
    filtered_df = df_offers.copy()
    if bayi_filtresi != "Tümü":
        filtered_df = filtered_df[filtered_df['Bayi'] == bayi_filtresi]
    if durum_filtresi != "Tümü":
        filtered_df = filtered_df[filtered_df['status'] == durum_filtresi]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("Bu kriterlere uygun teklif bulunamadı.")
        conn_s.close()
        return

    # --- KARTLI VE ZARİF LİSTELEME GÖRÜNÜMÜ ---
    for _, row in filtered_df.iterrows():
        off_id = row['id']
        stat = row['status']
        
        # Siparişe Çevrilenler için Açık Yeşil Arka Plan Rengi
        bg_color = "#f0fdf4" if stat == "Siparişe Çevir" else "#ffffff"
        border_color = "#bbf7d0" if stat == "Siparişe Çevir" else "#e2e8f0"
        
        with st.container():
            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:15px; border-radius:10px; border:1px solid {border_color}; margin-bottom:5px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:16px; font-weight:800; color:#0f172a;">{row['Müşteri']}</span>
                            <div style="font-size:13px; color:#64748b; margin-top:2px;">
                                <b>{row['Bayi']}</b> | Tarih: {row['offer_date']}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:18px; font-weight:900; color:#ea580c;">{row['total_price']:,.2f}</div>
                            <div style="font-size:12px; font-weight:600; color:#64748b;">{row['Model']}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- AKSİYON BUTONLARI VE DURUM YÖNETİMİ ---
            c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
            
            # Yönetici ise durumu değiştirebilir
            if user_role == 'admin':
                new_stat = c1.selectbox(
                    "Durum", 
                    ["Beklemede", "Siparişe Çevir", "Reddedildi"], 
                    index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(stat if stat in ["Beklemede", "Siparişe Çevir", "Reddedildi"] else "Beklemede"), 
                    key=f"s_{off_id}", 
                    label_visibility="collapsed"
                )
                if c1.button("✔️ Güncelle", key=f"b_{off_id}", use_container_width=True):
                    # Siparişe çevrildiyse o anki saati damgala
                    o_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M") if new_stat == "Siparişe Çevir" else ""
                    conn_s.execute("UPDATE offers SET status=?, order_date=? WHERE id=?", (new_stat, o_time, off_id))
                    conn_s.commit()
                    st.toast(f"#{off_id} Numaralı Teklif Güncellendi!")
                    st.rerun()
            else:
                # Bayi ise sadece durumu görür
                c1.markdown(f"<div style='text-align:center; padding:7px; background:#f1f5f9; border-radius:5px; font-size:13px; font-weight:800; color:#475569;'>{stat}</div>", unsafe_allow_html=True)

            if c2.button("✏️ Düzenle", key=f"e_{off_id}", use_container_width=True):
                st.session_state.edit_offer_id = off_id
                st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
                st.rerun()
            
            if c3.button("📄 Proforma", key=f"p_{off_id}", use_container_width=True):
                st.session_state.proforma_id = off_id
                st.session_state.active_tab = "PROFORMA"
                st.rerun()
            
            if c4.button("🗑️ Sil", key=f"r_{off_id}", use_container_width=True):
                conn_s.execute("DELETE FROM offers WHERE id=?", (off_id,))
                conn_s.execute("DELETE FROM offer_items WHERE offer_id=?", (off_id,))
                conn_s.commit()
                st.rerun()
            
            # Kartlar arası şık bir boşluk
            st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    
    conn_s.close()
