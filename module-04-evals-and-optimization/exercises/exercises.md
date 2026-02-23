# 📝 Module 4: Alıştırmalar

## Alıştırma 1: Yeni Eval Case Ekle (⭐ Kolay)

`evals/e2e.py` dosyasındaki `SAMPLE_EVAL_CASES` listesine 3 yeni eval vakası ekleyin:
1. Çeviri görevi: "Bu metni İngilizce'ye çevir: Merhaba dünya"
2. Özetleme görevi: "Bu makaleyi özetle: [uzun metin]"
3. Çok adımlı görev: "Python'da sıralama algoritması yaz, test et ve dosyaya kaydet"

Her vaka için `expected_tool`, `expected_contains` ve `max_cost` alanlarını doğru doldurun.

**İpucu:** Simüle edilmiş agent'a (`_simulated_agent_run`) da yeni kurallar eklemeniz gerekebilir.

---

## Alıştırma 2: Seçici Sıkıştırma Stratejisi (⭐⭐ Orta)

`optimization/context_compress.py` dosyasındaki `ContextCompressor` sınıfına 3. strateji olan **seçici sıkıştırma** (selective compression) ekleyin:

- Her mesajın "önem skorunu" hesaplayın:
  - Tool sonuçları → yüksek önem (korunmalı)
  - Kullanıcı soruları → orta önem
  - Uzun assistant cevapları → düşük önem (özetlenebilir)
- Düşük önemli mesajları özetle, yüksek önemli olanları koru

```python
def compress_messages(self, messages, strategy="selective"):
    # Yeni strateji implementasyonu
```

**Test:** Aynı mesaj listesini 3 farklı stratejiyle sıkıştırın ve sonuçları karşılaştırın.

---

## Alıştırma 3: Model Router'a Öğrenme Ekle (⭐⭐ Orta)

`optimization/model_router.py` dosyasındaki `ModelRouter` sınıfına geri bildirim mekanizması ekleyin:

1. `record_feedback(task, model_used, quality_score)` methodu ekleyin
2. Quality score 1-5 arası (1=kötü, 5=mükemmel)
3. Eğer ucuz model sürekli düşük skor alıyorsa, eşik değerini otomatik düşürün
4. Eğer pahalı model gereksiz kullanılıyorsa (basit görevlerde 5 skor), eşiği yükseltin

```python
def record_feedback(self, task: str, model_used: str, quality_score: int):
    """
    Yönlendirme kararına geri bildirim ver.
    Bu bilgi gelecek yönlendirmeleri iyileştirir.
    """
    # Implementasyonunuz
```

**İpucu:** Son N geri bildirimin ortalamasını kullanarak eşikleri dinamik ayarlayabilirsiniz.

---

## Alıştırma 4: Regression Detector (⭐⭐⭐ Zor)

Eval sonuçlarını kaydeden ve regresyon tespit eden bir `RegressionDetector` sınıfı yazın:

1. Eval sonuçlarını JSON dosyasına kaydedin (tarih, skor, detaylar)
2. Önceki çalıştırmalarla karşılaştırın
3. Skor düşüşlerini tespit edin ve raporlayın

```python
class RegressionDetector:
    def __init__(self, history_file="eval_history.json"):
        ...
    
    def save_results(self, results: list[EvalResult]):
        """Sonuçları geçmişe kaydet."""
        ...
    
    def detect_regressions(self) -> list[dict]:
        """
        Geçmiş sonuçlarla karşılaştır.
        Skor düşüşü varsa uyar.
        """
        ...
    
    def print_trend_report(self):
        """Son 5 çalıştırmanın trend raporunu yazdır."""
        ...
```

**Hedef çıktı:**
```
📉 Regresyon Tespit Raporu
══════════════════════════
Vaka: weather_basic
  Önceki skor: 1.00 → Şimdiki skor: 0.60
  ⚠️ REGRESYON TESPİT EDİLDİ! (-%40)

Vaka: calc_fibonacci
  Önceki skor: 0.85 → Şimdiki skor: 0.90
  ✅ İyileşme (+%6)
```

---

## Alıştırma 5: Tam Entegrasyon (⭐⭐⭐ Çok Zor)

Tüm modülleri birleştiren bir `OptimizedAgent` sınıfı yazın:

1. `ModelRouter` ile model seçimi
2. `ContextCompressor` ile bağlam yönetimi
3. `CostGuard` ile maliyet kontrolü
4. `TraceCollector` ile izleme
5. `EvalHarness` ile otomatik değerlendirme

```python
class OptimizedAgent:
    def __init__(self):
        self.router = ModelRouter()
        self.compressor = ContextCompressor(max_tokens=4000)
        self.guard = CostGuard(budget_limit=0.50)
        self.tracer = TraceCollector()
    
    async def run(self, task: str) -> str:
        # 1. Model seç
        model = self.router.route(task)
        
        # 2. Bütçe kontrolü
        if not self.guard.can_proceed():
            return "Bütçe aşıldı, görev iptal edildi."
        
        # 3. İzlemeyi başlat
        self.tracer.reset(task)
        self.tracer.start()
        
        # 4. Mesajları sıkıştır
        compressed = self.compressor.compress_messages(self.messages)
        
        # 5. LLM çağrısı yap
        response = await self.llm.chat_with_messages(compressed)
        
        # 6. Maliyeti kaydet
        self.guard.record_call(...)
        
        # 7. İzlemeyi bitir
        self.tracer.end(success=True)
        
        return response.content
```

**Bonus:** `EvalHarness` ile `OptimizedAgent`'ı değerlendirin ve rapor oluşturun.

---

## ✅ Kontrol Listesi

- [ ] E2E eval çatısını anlıyorum ve yeni vakalar yazabiliyorum
- [ ] Planner ve tool seçim değerlendirmesi yapabiliyorum
- [ ] Context compression stratejilerini uygulayabiliyorum
- [ ] Model routing ile maliyet optimizasyonu yapabiliyorum
- [ ] CostGuard ile bütçe kontrolü koyabiliyorum
- [ ] Trace collector ile adım adım izleme yapabiliyorum
- [ ] Tüm bileşenleri entegre edebiliyorum
