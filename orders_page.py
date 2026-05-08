import streamlit as st
import sqlite3
import pandas as pd
import json

# =====================================================================
# VERİTABANI BAĞLANTILARI
# =====================================================================
def get_factory(query, params=()):
    conn = sqlite3.connect('factory_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_users(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

# =====================================================================
# SİPARİŞLER ANA EKRANI
# =====================================================================
def show_orders(user_id, is_admin=False):
    st.header("📦 Sipariş Yönetimi")
    st.markdown("<p style='color:#64748b; margin-top:-10px; margin-bottom:20px;'>Siparişe dönen (onaylanan) tekliflerinizi ve üretim taleplerini buradan takip edebilirsiniz.</p>", unsafe_allow_html=True)
    
    # 1. KULLANICI ROLÜNÜ TESPİT ET (Bayi mi, Üretici mi?)
    u_role = 'dealer'
    if is_admin:
        u_role = 'admin'
    else:
        u_type_res = get_users("SELECT user_type FROM users WHERE id=?", (user_id,))
        if u_type_res and u_type_res[0][0] == 'Üretici':
            u_role = 'manufacturer'

    # 2. ROL BAZLI SİPARİŞ FİLTRELEME
    offers = []
    
    if u_role == 'manufacturer':
        # 🚀 ÜRETİCİ MANTIĞI: Sadece kendi makinelerine ait siparişleri görür! 🚀
        my_models = get_factory("SELECT id FROM models WHERE user_id=?", (user_id,))
        my_model_ids = [str(m[0]) for m in my_models]
        
        if my_model_ids:
            placeholders = ",".join(my_model_ids)
            offers = get_sales(f"SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') AND model_id IN ({placeholders}) ORDER BY id DESC")
            
    elif u_role == 'admin':
        # ADMİN: Sistemedeki tüm siparişleri görür
        offers = get_sales("SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') ORDER BY id DESC")
        
    else:
        # BAYİ: Sadece kendi yarattığı siparişleri görür
        offers = get_sales("SELECT id, customer_id, model_id, total_price, offer_date, order_date, status, conditions, user_id FROM offers WHERE status IN ('Onaylandı', 'Siparişe Çevir', 'Sipariş') AND user_id=? ORDER BY id DESC", (user_id,))

    # Eğer sonuç yoksa uyarı ver ve bitir
    if not offers:
        st.info("Sistemde henüz siparişe dönmüş ve onaylanmış bir kayıt bulunmuyor.")
        return

    # 3. VERİLERİ ŞIK BİR ŞEKİLDE LİSTELE (KART TASARIMI)
    st.markdown("<div style='font-size:13px; font-weight:bold; color:#64748b; margin-bottom:15px;'>TOPLAM " + str(len(offers)) + " SİPARİŞ BULUNDU</div>", unsafe_allow_html=True)
    
    for o in offers:
        o_id, c_id, m_id, t_price, o_date, ord_date, status, conds_str, dealer_id = o
        
        # Müşteri Adını Çek
        c_info = get_sales("SELECT company_name FROM customers WHERE id=?", (c_id,))
        c_name = c_info[0][0] if c_info else "Bilinmeyen Müşteri"
        
        # Makine Adını ve Para Birimini Çek
        m_info = get_factory("SELECT name, currency FROM models WHERE id=?", (m_id,))
        m_name = m_info[0][0] if m_info else "Bilinmeyen Makine"
        m_curr = m_info[0][1] if m_info else "USD"
        
        # Satan Bayinin Adını Çek (Özellikle Üreticiler İçin Önemli)
        d_info = get_users("SELECT company_name FROM users WHERE id=?", (dealer_id,))
        d_name = d_info[0][0] if d_info else "Bilinmeyen Bayi"
        
        # Adet ve Şartları Çözümle
        try: conds = json.loads(conds_str)
        except: conds = {}
        qty = conds.get("machine_qty", 1)
        
        # Kart Tasarımı
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([1, 2, 2.5, 1.5], vertical_alignment="center")
            
            # Sipariş Numarası ve Tarih
            c1.markdown(f"""
                <div style='background:#f1f5f9; padding:15px 5px; border-radius:8px; text-align:center; border:1px solid #e2e8f0;'>
                    <b style='color:#2563eb; font-size:16px;'>TR-{o_id:04d}</b><br>
                    <span style='color:#64748b; font-size:12px; font-weight:600;'>{ord_date or o_date}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Makine Bilgisi
            c2.markdown(f"""
                <div style='line-height:1.4;'>
                    <b style='color:#0f172a; font-size:15px;'>{m_name}</b><br>
                    <span style='color:#475569; font-size:13px;'><b>Adet:</b> {qty} Takım</span><br>
                    <span style='display:inline-block; margin-top:5px; padding:2px 8px; background:#dcfce7; color:#10b981; border-radius:4px; font-size:12px; font-weight:bold;'>{status}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Üretici isek Satan Bayiyi, Bayi isek Müşteriyi ön plana çıkaralım
            if u_role == 'manufacturer':
                c3.markdown(f"""
                    <div style='line-height:1.4; border-left:3px solid #cbd5e1; padding-left:10px;'>
                        <span style='color:#64748b; font-size:11px; font-weight:bold;'>SATAN BAYİ</span><br>
                        <b style='color:#0f172a; font-size:14px;'>🏢 {d_name}</b><br>
                        <span style='color:#64748b; font-size:11px; font-weight:bold; margin-top:4px; display:block;'>NİHAİ MÜŞTERİ</span>
                        <span style='color:#475569; font-size:13px;'>👤 {c_name}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                c3.markdown(f"""
                    <div style='line-height:1.4; border-left:3px solid #cbd5e1; padding-left:10px;'>
                        <span style='color:#64748b; font-size:11px; font-weight:bold;'>NİHAİ MÜŞTERİ</span><br>
                        <b style='color:#0f172a; font-size:14px;'>🏢 {c_name}</b>
                    </div>
                """, unsafe_allow_html=True)
            
            # Fiyat
            c4.markdown(f"""
                <div style='text-align:right; background:#fffbeb; padding:15px 10px; border-radius:8px; border:1px solid #fde68a;'>
                    <span style='font-size:11px; color:#b45309; font-weight:bold; text-transform:uppercase;'>NİHAİ TUTAR</span><br>
                    <span style='font-size:18px; font-weight:900; color:#ea580c;'>{t_price:,.2f} {m_curr}</span>
                </div>
            """, unsafe_allow_html=True)
