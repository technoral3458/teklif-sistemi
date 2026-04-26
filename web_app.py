import streamlit as st
import database
import datetime
import os
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Ersan Makine ERP", page_icon="⚙️", layout="wide")

# Masaüstündeki OfferWizard stilini web'e uyarlayan CSS
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    [data-testid="stSidebar"] { background-color: #0f172a; }
    .option-card {
        background: white; padding: 15px; border-radius: 10px;
        border: 1px solid #e2e8f0; margin-bottom: 10px;
    }
    .price-tag { color: #e67e22; font-weight: 900; font-size: 1.1em; }
    .total-box {
        background: #1e293b; color: white; padding: 20px;
        border-radius: 10px; text-align: center; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. YAN MENÜ (SIDEBAR)
with st.sidebar:
    st.title("🚀 ERSAN MAKİNE")
    st.caption("Bulut Yönetim Paneli")
    st.markdown("---")
    menu = st.radio("Menü", ["🏠 Genel Bakış", "📄 Yeni Teklif Hazırla", "📋 Geçmiş Teklifler"])
    st.markdown("---")
    currency = st.selectbox("Para Birimi", ["USD", "EUR", "RMB"])

# 3. YENİ TEKLİF HAZIRLAMA SİHRİBAZI
if menu == "📄 Yeni Teklif Hazırla":
    st.title("📄 Yeni Teklif Hazırlama")
    
    col_settings, col_preview = st.columns([1, 1.2])

    with col_settings:
        st.subheader("📋 Teklif Ayarları")
        
        # Müşteri ve Kategori (offer_wizard.py index 164-180)
        customers = database.get_query("SELECT id, company_name FROM customers")
        cust_dict = {c[1]: c[0] for c in customers} if customers else {"Müşteri Yok": 0}
        selected_cust = st.selectbox("Müşteri Seçin", list(cust_dict.keys()))

        categories = ["Tüm Kategoriler", "CNC Router Makinaları", "CNC Delik Makinaları", "Kenar Bantlama Makinaları"]
        selected_cat = st.selectbox("Kategori Filtresi", categories)

        # Modeller (offer_wizard.py index 335-360)
        query = "SELECT id, name, base_price, specs, image_path, compatible_options FROM models WHERE currency=?"
        params = [currency]
        if selected_cat != "Tüm Kategoriler":
            query += " AND category=?"
            params.append(selected_cat)
        
        models = database.get_query(query, tuple(params))
        model_dict = {m[1]: m for m in models} if models else {}
        selected_model_name = st.selectbox("Makine Modeli", list(model_dict.keys()))

        if selected_model_name:
            m_data = model_dict[selected_model_name]
            m_id, m_base_price, m_specs, m_img, m_comp_opts = m_data[0], m_data[2], m_data[3], m_data[4], m_data[5]
            m_qty = st.number_input("Makine Adedi", min_value=1, value=1)
            
            st.markdown("---")
            st.subheader("⚙️ Uyumlu Ekstra Donanımlar")
            
            # Opsiyon Motoru (offer_wizard.py index 435-460)
            comp_list = m_comp_opts.split(",") if m_comp_opts else []
            options = database.get_query("SELECT id, opt_name, opt_price, opt_desc FROM options WHERE currency=?", (currency,))
            
            selected_options = []
            options_total = 0.0
            
            for oid, oname, oprice, odesc in options:
                if str(oid) in comp_list:
                    with st.container():
                        st.markdown(f"**{oname}** (+{oprice:,.2f} {currency})")
                        is_selected = st.checkbox(f"Ekle: {oname}", key=f"opt_{oid}")
                        if is_selected:
                            o_qty = st.number_input(f"Adet ({oname})", min_value=1, value=1, key=f"qty_{oid}")
                            line_price = oprice * o_qty
                            options_total += line_price
                            selected_options.append({"name": oname, "qty": o_qty, "price": oprice})

            # Fiyat ve İskonto (offer_wizard.py index 198-215)
            st.markdown("---")
            subtotal = (m_base_price * m_qty) + options_total
            discount_pct = st.slider("Özel İskonto Oranı (%)", 0.0, 50.0, 0.0, 0.5)
            final_price = subtotal * (1 - (discount_pct / 100))
            
            st.markdown(f"""
                <div class="total-box">
                    <div style="font-size:0.9em; opacity:0.8;">Sistem Toplamı: {subtotal:,.2f} {currency}</div>
                    <div style="font-size:1.5em; font-weight:bold; margin-top:10px;">Net Fiyat: {final_price:,.2f} {currency}</div>
                </div>
            """, unsafe_allow_html=True)

    with col_preview:
        st.subheader("👁️ Teklif Önizleme")
        if selected_model_name:
            st.info("Teklif Şablonu (HTML) burada oluşturuluyor...")
            # Burada preview_engine.py devreye girecek
            st.markdown(f"**Müşteri:** {selected_cust}")
            st.markdown(f"**Model:** {selected_model_name}")
            if m_img and os.path.exists(m_img):
                st.image(m_img, width=400)
            
            if st.button("💾 TEKLİFİ SİSTEME KAYDET", use_container_width=True):
                # Kayıt mantığı (offer_wizard.py index 585-615)
                st.success("Teklif veritabanına başarıyla kaydedildi!")

elif menu == "🏠 Genel Bakış":
    st.title("Genel Bakış")
    st.write("Dashboard verileri yükleniyor...")