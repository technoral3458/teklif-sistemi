# Tanıtım Videosu

`record_promo.py`, çalışan sistemin arayüzünü gezerek tanıtım videosu kaydeder.
Ekranda hareket eden bir imleç, tıklama efekti, Türkçe altyazılar ve açılış/kapanış
kartları videoya gömülür. Sahte ekran görüntüsü değildir — gerçek sistemin kaydıdır.

## Çalıştırma

```bash
pip install playwright imageio-ffmpeg
python3 -m playwright install chromium

python3 promo/record_promo.py https://panel.firmaniz.com kullanici@firma.com 'SIFRE' ./promo_out
```

Beşinci parametre olarak bir parametrik kesim işinin numarasını verirseniz
3B döndürme sahnesi de eklenir:

```bash
python3 promo/record_promo.py https://panel.firmaniz.com kullanici@firma.com 'SIFRE' ./promo_out 12
```

Çıktı `promo_out/` içine `.webm` olarak düşer. MP4'e çevirmek için:

```bash
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -i promo_out/*.webm -vf "scale=1920:1080:flags=lanczos,fps=30" \
    -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart tanitim.mp4
```

## Dikkat

- Kayıt sırasında sistemde **gerçek bir teklif oluşur**. Video bittikten sonra
  o teklifi silebilirsiniz.
- Kendi sunucunuzda çalıştırırsanız video sizin logonuz, makineleriniz ve
  müşterilerinizle oluşur. Müşteri adları videoda görüneceği için, paylaşmadan
  önce isimleri kontrol edin.
- Video sessizdir; müzik/seslendirme eklemek isterseniz montaj programında ekleyin.

## Sahne akışı

Açılış kartı → giriş → müşteri seç → makine seç → opsiyonlar (fiyat canlı güncellenir)
→ teslim bilgileri → teklif hazır → belgeler → müşteri self-servis yapılandırıcı
→ servis talebi → parametrik kesim 3B → kapanış kartı.

Sahneleri, altyazıları ve süreleri `record_promo.py` içindeki `main()` fonksiyonundan
düzenleyebilirsiniz.
