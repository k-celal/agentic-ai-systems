# 📖 Module 4: Teori — Değerlendirme ve Optimizasyon

## Neden Eval Kritik?

Module 1-3'te agent yazdık, tool eklledik, reflection yaptık. Ama bir soru cevapsız kaldı:

> **Agent'ımız gerçekten iyi mi?**

Hissiyata göre geliştirme, production'da felaket demektir. Eval (değerlendirme) sistemi yazmazsanız:
- Agent'ın ne zaman bozulduğunu bilemezsiniz
- Prompt değişikliğinin etkisini ölçemezsiniz
- Model değiştirdiğinizde ne olduğunu göremezsiniz
- Maliyet kontrolü yapamazsınız

---

## Eval Türleri

### 1. Uçtan Uca (E2E) Eval

Tüm sistemi test eder: Kullanıcı sorusu → Agent çalışır → Cevap doğru mu?

```
Girdi: "İstanbul'da hava nasıl?"
Beklenen:
  - Tool çağrısı: get_weather
  - Cevap içinde: "İstanbul" ve bir sıcaklık değeri
  - Maliyet: < $0.01
  - Süre: < 10 saniye

Gerçek:
  - Tool çağrısı: get_weather ✅
  - Cevap: "İstanbul'da hava 15°C ve güneşli" ✅
  - Maliyet: $0.003 ✅
  - Süre: 2.1 saniye ✅

Sonuç: BAŞARILI (skor: 1.0)
```

### 2. Bileşen Eval: Planner

Planner'ın görevi doğru parçalara ayırıp ayırmadığını test eder:

```
Girdi: "Python ile Fibonacci hesapla ve sonucu dosyaya kaydet"

Beklenen adımlar:
  1. Fibonacci hesaplama kodu yaz
  2. Kodu çalıştır
  3. Sonucu dosyaya kaydet

Gerçek adımlar:
  1. "Fibonacci hesaplama kodu hazırla" ✅
  2. "Kodu çalıştır" ✅
  3. "Sonucu kaydet" ✅

Planner Skoru: 3/3 = 1.0
```

### 3. Bileşen Eval: Tool Seçimi

Agent doğru tool'u seçiyor mu?

```
Görev: "Dosyayı oku"
Beklenen tool: file_read
Agent'ın seçtiği: file_read ✅

Görev: "Hava durumunu öğren"
Beklenen tool: get_weather
Agent'ın seçtiği: search ❌  ← Yanlış!
```

---

## Maliyet Optimizasyonu

### Problem: LLM Çağrıları Pahalı

```
Senaryo: E-ticaret chatbot, günde 10,000 kullanıcı

GPT-4o kullanırsak:
  - Ortalama çağrı: 2000 input + 500 output token
  - Maliyet/çağrı: ~$0.01
  - Günlük: 10,000 × 3 çağrı × $0.01 = $300/gün
  - Aylık: ~$9,000 😱

GPT-4o-mini kullanırsak:
  - Aynı token kullanımı
  - Maliyet/çağrı: ~$0.0006
  - Günlük: 10,000 × 3 × $0.0006 = $18/gün
  - Aylık: ~$540 😊

Akıllı routing ile (%80 basit, %20 karmaşık):
  - 8000 × $0.0006 + 2000 × $0.01 = $4.8 + $20 = $24.8/gün
  - Aylık: ~$744 ← En iyi denge!
```

### Strateji 1: Model Routing (Akıllı Yönlendirme)

Fikir basit: Her görev GPT-4o gerektirmez!

```
Karmaşıklık Skoru Hesaplama:
─────────────────────────────
  Uzun metin (>500 karakter)     → +2
  Çok adımlı görev               → +3
  Kod yazma/analiz                → +2
  Basit soru-cevap                → +0
  Çeviri                          → +1
  Özetleme                        → +1

  Skor 0-3: gpt-4o-mini (ucuz, hızlı)
  Skor 4-6: gpt-4o-mini (yeterli)
  Skor 7+:  gpt-4o (güçlü, pahalı)
```

### Strateji 2: Context Compression (Bağlam Sıkıştırma)

Uzun konuşmaları özetle, token tasarrufu yap:

```
ÖNCE (5000 token):
  system: "Sen bir asistansın..."
  user: "Python nedir?"
  assistant: "Python yüksek seviyeli bir programlama dilidir... [500 kelime]"
  user: "Değişken nasıl tanımlanır?"
  assistant: "Python'da değişken tanımlamak için... [300 kelime]"
  user: "Şimdi bir sınıf yaz"

SONRA (1200 token):
  system: "Sen bir asistansın..."
  system: "[Konuşma özeti: Kullanıcı Python temelleri öğreniyor.
           Python'un ne olduğu ve değişken tanımlama konuşuldu.]"
  user: "Şimdi bir sınıf yaz"

Tasarruf: ~3800 token = ~%76 azalma!
```

### Strateji 3: Cost Guard (Maliyet Koruyucu)

Bütçe limiti koy, aşıldığında dur:

```
CostGuard Yapılandırması:
  budget_limit: $1.00          ← Toplam bütçe
  per_call_limit: $0.10        ← Tek çağrı limiti
  warning_threshold: 0.80      ← %80'de uyar
  kill_threshold: 1.00         ← %100'de durdur

Akış:
  Çağrı 1: $0.003 → Toplam: $0.003 (<%1) ✅
  Çağrı 2: $0.005 → Toplam: $0.008 (<%1) ✅
  ...
  Çağrı 50: $0.02 → Toplam: $0.82 (>%80) ⚠️ UYARI!
  ...
  Çağrı 65: $0.03 → Toplam: $1.01 (>%100) 🛑 DURDUR!
```

---

## Telemetry ve Tracing

### Neden İzleme Önemli?

Production'da bir şeyler ters gidince, "ne oldu?" sorusunu cevaplamalısınız:

```
İzleme Kaydı Örneği:
════════════════════════════════════════════════
Görev: "Hava durumunu öğren ve dosyaya kaydet"
════════════════════════════════════════════════
Adım 1 [0.0s] DÜŞÜNME
  → "Önce hava durumunu sormalıyım"
  Maliyet: $0.002 | 300 token

Adım 2 [0.8s] TOOL ÇAĞRISI
  → get_weather(city="Istanbul")
  Süre: 1.2s | Sonuç: {"temp": 15}

Adım 3 [2.0s] DÜŞÜNME
  → "Sonucu dosyaya kaydetmeliyim"
  Maliyet: $0.003 | 450 token

Adım 4 [2.5s] TOOL ÇAĞRISI
  → file_write(path="hava.txt", content="15°C")
  Süre: 0.1s | Sonuç: {"success": true}

Adım 5 [2.6s] CEVAP
  → "İstanbul'da hava 15°C. Sonuç hava.txt'ye kaydedildi."
  Maliyet: $0.001 | 100 token
════════════════════════════════════════════════
TOPLAM: 2.6s | $0.006 | 850 token | 2 tool çağrısı
════════════════════════════════════════════════
```

---

## Eval Metrikleri

Hangi metrikleri takip etmeliyiz?

| Metrik | Açıklama | Hedef |
|--------|----------|-------|
| Başarı Oranı | Görevlerin % kaçı doğru tamamlandı | >%90 |
| Tool Doğruluğu | Doğru tool seçilme oranı | >%95 |
| Planner Doğruluğu | Adımlar doğru ayrıştırıldı mı? | >%85 |
| Ortalama Süre | Görev tamamlama süresi | <5s |
| Ortalama Maliyet | Görev başına maliyet | <$0.01 |
| Token Verimliliği | Çıktı kalitesi / token harcaması | Yüksek |

---

## Yaygın Hatalar ve Çözümleri

### 1. "Eval yazacak zamanım yok"
→ Eval yazmak sizi **haftalar** debug'dan kurtarır. İlk yatırım kendini 10x geri öder.

### 2. "Eval geçti ama production'da çalışmıyor"
→ Eval case'leriniz gerçek dünyayı yansıtmıyor demektir. Kullanıcı loglarından eval case üretin.

### 3. "Maliyet kontrolsüz artıyor"
→ CostGuard olmadan agent çalıştırmayın. Sonsuz döngü + GPT-4o = felaket.

### 4. "Hangi modeli kullanmalıyım?"
→ Hepsini deneyin, eval ile ölçün! Model routing ile en iyi dengeyi bulun.

---

## 🔗 İleri Okuma
- [docs/03-evals-and-metrics.md](../docs/03-evals-and-metrics.md) — Eval terminolojisi
- [docs/02-glossary.md](../docs/02-glossary.md) — Genel terimler
- [Module 5: Multi-Agent Systems](../module-05-multi-agent/README.md) — Sonraki modül
