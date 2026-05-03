import streamlit as st
import sqlite3
import pandas as pd
import datetime

# =====================================================================
# VERİTABANI MOTORLARI
# =====================================================================
def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_factory(query, params=()):
    conn = sqlite3.connect('factory_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_users(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

# =====================================================================
# TEKLİF LİSTESİ MODÜLÜ
# =====================================================================
def show_offer_management(user_id, user_role):
    st.header("📋 Teklif Listesi ve Durum Yönetimi")
    
    conn_s = sqlite3.connect('sales_data.db')
    offers_raw = conn_s.execute("SELECT id, customer_id, model_id, total_price, status, user_id, offer_date FROM offers ORDER BY id DESC").fetchall()
    conn_s.close()
    
    if not offers_raw:
        st.info("Sistemde henüz kayıtlı bir teklif bulunmuyor.")
        return

    df_offers = pd.DataFrame(offers_raw, columns=["id", "customer_id", "model_id", "total_price", "status", "user_id", "offer_date"])
    
    # Veri Hazırlama (İsimleri Çekme)
    user_dict = {u[0]: u[1] for u in get_users("SELECT id, company_name FROM users")}
    cust_dict = {c[0]: c[1] for c in get_sales("SELECT id, company_name FROM customers")}
    mod_dict = {m[0]: m[1] for m in get_factory("SELECT id, name FROM models")}

    df_offers['Bayi'] = df_offers['user_id'].map(user_dict).fillna("Bilinmeyen Bayi")
    df_offers['Müşteri'] = df_offers['customer_id'].map(cust_dict).fillna("Bilinmeyen Müşteri")
    df_offers['Model'] = df_offers['model_id'].map(mod_dict).fillna("Bilinmeyen Model")

    # Admin değilse sadece kendi tekliflerini görsün
    if user_role != 'admin':
        df_offers = df_offers[df_offers['user_id'] == user_id]

    # --- FİLTRELEME ARAÇLARI (Daha Kompakt) ---
    with st.container(border=True):
        f_col1, f_col2 = st.columns(2)
        if user_role == 'admin':
            bayi_filtresi = f_col1.selectbox("Bayi Seçimi", ["Tümü"] + list(df_offers['Bayi'].unique()), label_visibility="collapsed")
        else:
            bayi_filtresi = "Tümü"
            
        durum_filtresi = f_col2.selectbox("Durum Filtresi", ["Tümü", "Beklemede", "Siparişe Çevir", "Reddedildi"], label_visibility="collapsed")

    filtered_df = df_offers.copy()
    if bayi_filtresi != "Tümü": filtered_df = filtered_df[filtered_df['Bayi'] == bayi_filtresi]
    if durum_filtresi != "Tümü": filtered_df = filtered_df[filtered_df['status'] == durum_filtresi]

    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)

    # --- LİSTELEME ---
    for _, row in filtered_df.iterrows():
        off_id = row['id']
        o_status = row['status']
        
        # Siparişe çevrilenler için Açık Yeşil arka plan rengi
        bg_color = "#f0fdf4" if o_status == "Siparişe Çevir" else "#ffffff"
        border_color = "#bbf7d0" if o_status == "Siparişe Çevir" else "#e2e8f0"
        
        # Kart Tasarımı
        st.markdown(f"""
            <div style="background-color:{bg_color}; padding:15px; border-radius:10px; border:1px solid {border_color}; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h5 style="margin:0; color:#0f172a;">{row['Müşteri']}</h5>
                        <div style="font-size:12px; color:#64748b; margin-top:3px;">
                            <b>{row['Bayi']}</b> | {row['offer_date']}
                        </div>
                        <div style="margin-top:8px; font-size:14px;">
                            Model: <b>{row['Model']}</b> | Tutar: <span style="color:#ea580c; font-weight:bold;">{row['total_price']:,.2f}</span>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Aksiyon Butonları (Kartın hemen altına şık bir şekilde)
        c_act1, c_act2, c_act3, c_act4 = st.columns([1.5, 1, 1, 1])
        
        # Durum Değiştirme (Sadece Admin)
        if user_role == 'admin':
            new_stat = c_act1.selectbox("Durum", ["Beklemede", "Siparişe Çevir", "Reddedildi"], 
                                      index=["Beklemede", "Siparişe Çevir", "Reddedildi"].index(o_status if o_status in ["Beklemede", "Siparişe Çevir", "Reddedildi"] else "Beklemede"), 
                                      key=f"stat_{off_id}", label_visibility="collapsed")
            if c_act1.button("Güncelle", key=f"btn_{off_id}", use_container_width=True):
                conn = sqlite3.connect('sales_data.db')
                if new_stat == "Siparişe Çevir":
                    o_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    conn.execute("UPDATE offers SET status=?, order_date=? WHERE id=?", (new_stat, o_time, off_id))
                else:
                    conn.execute("UPDATE offers SET status=? WHERE id=?", (new_stat, off_id))
                conn.commit(); conn.close()
                st.rerun()
        else:
            c_act1.markdown(f"<div style='padding:5px; text-align:center; border-radius:5px; background:#f1f5f9; font-size:12px; font-weight:700;'>{o_status}</div>", unsafe_allow_html=True)

        if c_act2.button("✏️ Düzenle", key=f"ed_{off_id}", use_container_width=True):
            st.session_state.edit_offer_id = off_id
            st.session_state.active_tab = "📝 Yeni Teklif Hazırla"
            st.rerun()
        
        if c_act3.button("📄 Proforma", key=f"pr_{off_id}", use_container_width=True):
            st.session_state.proforma_id = off_id
            st.session_state.active_tab = "PROFORMA"
            st.rerun()
            
        if c_act4.button("🗑️ Sil", key=f"rm_{off_id}", use_container_width=True):
            conn = sqlite3.connect('sales_data.db')
            conn.execute("DELETE FROM offers WHERE id=?", (off_id,))
            conn.execute("DELETE FROM offer_items WHERE offer_id=?", (off_id,))
            conn.commit(); conn.close()
            st.rerun()
        
        st.markdown("<hr style='margin:10px 0; border:0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)
