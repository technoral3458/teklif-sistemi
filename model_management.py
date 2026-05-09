# Donanım Formu İçerisine Eklenecek Yeni Alanlar
st.session_state.o_suffix = st.text_input("Model Adı Eki (Suffix)", value=st.session_state.get('o_suffix', ''), placeholder="Örn: L veya -PRO")
st.file_uploader("Varyasyon Görseli (Seçildiğinde Ana Resim Olur)", type=['png','jpg','jpeg'], key="up_variant")

### 2. Adım: Teklif Sihirbazı Reaksiyonu (`offer_wizard.py`)
Bayi donanımı tıkladığı anda ismin ve görselin değişmesi için gereken "Zeka" katmanı:

```python
# offer_wizard.py içerisindeki donanım seçim mantığı (Özet Mantık)
selected_options_data = get_factory("SELECT opt_name, opt_suffix, opt_variant_image FROM options WHERE id IN ({})".format(placeholders))

current_suffix = ""
variation_image = base_machine_image # Varsayılan resim

for opt in selected_options_data:
    # 1. İsim Eki Hesaplama
    if opt['opt_suffix']:
        current_suffix += " " + opt['opt_suffix']
    
    # 2. Görsel Değiştirme (Eğer varyasyon görseli tanımlıysa)
    if opt['opt_variant_image']:
        variation_image = opt['opt_variant_image']

# Ekranda Gösterilecek Final Veriler
final_model_display_name = base_model_name + current_suffix
st.image(variation_image) # Anlık olarak değişen resim
st.markdown(f"## {final_model_display_name}") # Anlık olarak değişen başlık

**Sefa Bey**, bu yapıyı projenize tam entegre etmek için hazır olduğunuzda söyleyin, ilgili dosyaların **tam kodlarını** bu mantığa göre revize edip size tek parça halinde göndereyim. Hangi dosyadan başlayalım?
