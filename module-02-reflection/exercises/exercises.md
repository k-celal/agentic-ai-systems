# 📝 Module 2: Alıştırmalar

## Alıştırma 1: Reflection Eşiğini Ayarla (⭐ Kolay)

### Görev
`quality_threshold` değerini değiştirerek reflection döngüsünün davranışını gözlemleyin.

1. `threshold=3` yapın → Neredeyse hiç reflection yapmadan kabul eder
2. `threshold=9` yapın → Çok fazla reflection yapar (maliyetli!)
3. `threshold=7` yapın → Dengeli

### Soru
Her threshold değerinde kaç iterasyon geçti? Token maliyeti ne kadar değişti?

---

## Alıştırma 2: Yeni Validation Kuralı Ekle (⭐⭐ Orta)

### Görev
`mcp/tools/validate.py`'ye yeni bir doğrulama kuralı ekleyin: **Okunabilirlik Skoru**

- Ortalama cümle uzunluğu 20 kelimeden fazlaysa uyarı ver
- Ortalama kelime uzunluğu 8 karakterden fazlaysa uyarı ver

---

## Alıştırma 3: Reflection Geçmişini Görselleştir (⭐⭐ Orta)

### Görev
Her iterasyondaki puanı bir grafik gibi gösterin:

```
İterasyon 1: ████████░░ 4/10
İterasyon 2: ██████████████░░ 7/10  
İterasyon 3: ████████████████░░ 8/10 ✅
```

---

## Alıştırma 4: Farklı Görevlerde Reflection Karşılaştırması (⭐⭐⭐ Zor)

### Görev
3 farklı görev türü için reflection'ın faydasını ölçün:
1. Basit soru: "Python nedir?"
2. Kod yazma: "Fibonacci fonksiyonu yaz"
3. Makale: "Yapay zeka hakkında 500 kelimelik makale yaz"

Her biri için reflection'lı ve reflection'sız çalıştırın. Kalite farkını karşılaştırın.

---

## ✅ Kontrol Listesi

- [ ] Reflection pattern'i uygulayabiliyorum
- [ ] Threshold'un etkisini anlıyorum
- [ ] Validation tool yazabiliyorum
- [ ] Maliyet-fayda analizi yapabiliyorum
