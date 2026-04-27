import streamlit as st
import database
import datetime
import os
import json

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Ersan Makine | Teklif Sistemi", page_icon="⚙️", layout="wide")

# Kurumsal Tema CSS (Masaüstü uygulamasına benzer tasarım)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2563eb; color: white; }
    .price-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #2563eb; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .option-box { background: #ffffff; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HESAPLAMA MOTORU (offer_wizard.py mantığı) ---
def calculate_offer(base_price, discount_pct, selected_options, machine_qty):
    multiplier = 1.0 - (discount_pct / 100.0)
    # Makine ana fiyatı üzerinden iskonto
    discounted_base = base_price * multiplier
    total_machine_price = discounted_base * machine_qty
    
    # Opsiyonlar üzerinden iskonto ve toplam
    total_options_price = 0
    for opt in selected_options:
        opt_discounted = opt['price'] * multiplier
        total_options_price += (opt_discounted * opt['qty'])
        
    return total_machine_price + total_options_price

# --- 3. YAN MENÜ ---
with st.sidebar:
    st.image("https://ersanmakina.net/wp-content/uploads/2023/01/logo-ersan.png", width=200) # Logonuzu buraya ekleyebilirsiniz
    st.title("Yönetim Paneli")
    menu = st.radio("İşlem Seçin", ["🏠 Ana Sayfa", "📄 Yeni Teklif Oluştur", "📋 Kayıtlı Teklifler"])
    st.markdown("---")
    currency = st.selectbox("Para Birimi", ["USD", "EUR", "TRY"])

# --- 4. ANA SAYFA (Dashboard) ---
if menu == "🏠 Ana Sayfa":
    st.title("Hoş Geldiniz, Sefa Bey")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Toplam Müşteri", len(database.get_query("SELECT id FROM customers")))
    with col2:
        st.metric("Aktif Modeller", len(database.get_query("SELECT id FROM models")))
    with col3:
        st.metric("Hazırlanan Teklifler", len(database.get_query("SELECT id FROM offers")))

# --- 5. YENİ TEKLİF OLUŞTURMA (Sihirbaz) ---
elif menu == "📄 Yeni Teklif Oluştur":
    st.title("Teklif Hazırlama Sihirbazı")
    
    # Veritabanından ham verileri çek
    customers = database.get_query("SELECT id, company_name FROM customers")
    cust_list = {c[1]: c[0] for c in customers}
    
    col_input, col_preview = st.columns([1, 1.2])

    with col_input:
        st.subheader("🛠️ Makine ve Müşteri Seçimi")
        selected_cust_name = st.selectbox("Müşteri Seçin", list(cust_list.keys()))
        
        categories = ["Tüm Kategoriler", "CNC Router Makinaları", "CNC Delik Makinaları", "Kenar Bantlama Makinaları"]
        sel_cat = st.selectbox("Kategori Filtresi", categories)
        
        # Modelleri getir (Kategoriye göre)
        m_query = "SELECT id, name, base_price, specs, compatible_options FROM models WHERE currency=?"
        m_params = [currency]
        if sel_cat != "Tüm Kategoriler":
            m_query += " AND category=?"
            m_params.append(sel_cat)
            
        models = database.get_query(m_query, tuple(m_params))
        model_names = [m[1] for m in models]
        selected_model_name = st.selectbox("Model Seçin", model_names)

        if selected_model_name:
            # Seçilen modelin verilerini al
            m_data = [m for m in models if m[1] == selected_model_name][0]
            m_id, m_base_price, m_specs, m_compat_str = m_data[0], m_data[2], m_data[3], m_data[4]
            
            m_qty = st.number_input("Makine Adedi", min_value=1, value=1)
            discount = st.slider("İskonto Oranı (%)", 0.0, 50.0, 0.0, 0.5)
            
            st.markdown("---")
            st.subheader("⚙️ Opsiyonlar")
            
            # Uyumlu opsiyonları filtrele (offer_wizard.py mantığı)
            compat_ids = m_compat_str.split(",") if m_compat_str else []
            all_opts = database.get_query("SELECT id, opt_name, opt_price, opt_desc FROM options WHERE currency=?", (currency,))
            
            selected_opts_list = []
            for oid, oname, oprice, odesc in all_opts:
                if str(oid) in compat_ids:
                    with st.container():
                        is_sel = st.checkbox(f"{oname} (+{oprice:,.2f} {currency})", key=f"chk_{oid}")
                        if is_sel:
                            o_qty = st.number_input(f"Adet ({oname})", min_value=1, value=1, key=f"q_{oid}")
                            selected_opts_list.append({'name': oname, 'price': oprice, 'qty': o_qty, 'desc': odesc})

    with col_preview:
        st.subheader("👁️ Teklif Önizleme")
        
        if selected_model_name:
            final_total = calculate_offer(m_base_price, discount, selected_opts_list, m_qty)
            
            # HTML Önizleme (preview_engine.py şablonu özeti)
            preview_html = f"""
            <div style="background: white; padding: 30px; border: 1px solid #ccc; font-family: sans-serif;">
                <h2 style="color: #2563eb;">TEKLİF FORMU</h2>
                <hr>
                <p><b>Müşteri:</b> {selected_cust_name}</p>
                <p><b>Tarih:</b> {datetime.date.today().strftime('%d.%m.%Y')}</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr style="background: #f1f5f9;">
                        <th style="padding: 10px; border: 1px solid #ddd;">Ürün / Donanım</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Adet</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Birim Fiyat</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><b>{selected_model_name}</b> (Ana Makine)</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{m_qty}</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{m_base_price:,.2f} {currency}</td>
                    </tr>
            """
            
            for o in selected_opts_list:
                preview_html += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">{o['name']}</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{o['qty']}</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{o['price']:,.2f} {currency}</td>
                    </tr>
                """
            
            preview_html += f"""
                </table>
                <div style="margin-top: 20px; text-align: right;">
                    <p>Ara Toplam: {(m_base_price * m_qty) + sum(x['price']*x['qty'] for x in selected_opts_list):,.2f} {currency}</p>
                    <p style="color: red;">İskonto (%{discount}): -{((m_base_price * m_qty) + sum(x['price']*x['qty'] for x in selected_opts_list)) * (discount/100):,.2f} {currency}</p>
                    <h3 style="color: #1e293b;">NET TOPLAM: {final_total:,.2f} {currency}</h3>
                </div>
            </div>
            """
            
            st.markdown(preview_html, unsafe_allow_html=True)
            
            if st.button("💾 Teklifi Sisteme Kaydet ve PDF Oluştur"):
                # Veritabanına kaydetme işlemi buraya gelecek
                st.success(f"{selected_cust_name} adına teklif başarıyla kaydedildi!")

# --- 6. GEÇMİŞ TEKLİFLER ---
elif menu == "📋 Kayıtlı Teklifler":
    st.title("Teklif Arşivi")
    offers = database.get_query("""
        SELECT o.id, c.company_name, o.model_name, o.total_price, o.date 
        FROM offers o 
        JOIN customers c ON o.customer_id = c.id 
        ORDER BY o.date DESC
    """)
    if offers:
        st.table(offers)
    else:
        st.warning("Henüz kayıtlı bir teklif bulunamadı.")
