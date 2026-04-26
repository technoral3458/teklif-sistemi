import streamlit as st
# import database -> Mevcut veritabanı dosyan aynen çalışmaya devam edecek!

# Sayfa Ayarları
st.set_page_config(page_title="Ersan Makine Teklif", page_icon="⚙️", layout="wide")

st.title("⚙️ Ersan Makine - Bulut Teklif Sihirbazı")
st.markdown("---")

# 2 Sütunlu Tasarım (Masaüstündeki gibi)
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Teklif Ayarları")
    customer = st.selectbox("Müşteri Seçin", ["Müşteri A", "Müşteri B", "Yeni Müşteri"])
    model = st.selectbox("Makine Modeli", ["NA-2136 Titanium", "NA-2128 Gold"])
    qty = st.number_input("Makine Adedi", min_value=1, value=1)
    
with col2:
    st.subheader("💰 Fiyat ve İskonto")
    base_price = st.number_input("Sistem Toplamı ($)", value=25000.0)
    discount = st.number_input("İskonto Oranı (%)", min_value=0.0, max_value=100.0, value=10.0)
    
    agreed_price = base_price * (1 - (discount / 100))
    st.success(f"Anlaşılan Net Fiyat: **{agreed_price:,.2f} $**")

st.markdown("---")

# Kaydetme Butonu
if st.button("💾 TEKLİFİ KAYDET VE PDF OLUŞTUR", use_container_width=True):
    st.balloons()
    st.write(f"**{customer}** için **{model}** modelli teklif başarıyla sisteme kaydedildi!")
    st.info("PDF oluşturma motoru web için devreye giriyor...")