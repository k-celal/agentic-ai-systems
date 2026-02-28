# 📝 Module 5: Alıştırmalar (Exercises)

## Alıştırma 1: Yeni Agent Rolü Ekle (⭐ Kolay)

### Görev
Pipeline'a yeni bir agent ekleyin: **FactCheckerAgent** (Doğrulayıcı Agent)

Bu agent:
- Researcher'ın bulgularını almalı
- Bilgilerin doğruluğunu kontrol etmeli
- Doğrulanmış ve doğrulanmamış bilgileri ayırmalı

### İpuçları
1. `agents/base_agent.py`'deki `BaseAgent` sınıfını miras alın
2. `_build_system_prompt()` ve `process()` metotlarını tanımlayın
3. Pipeline sırasını güncelleyin: Planner → Researcher → **FactChecker** → Critic → Synthesizer
4. `orchestration/run.py`'deki agent listesine ekleyin

### Başlangıç Kodu
```python
class FactCheckerAgent(BaseAgent):
    """Doğrulayıcı Agent - Bilgilerin doğruluğunu kontrol eder."""
    
    def __init__(self, model=None):
        super().__init__(
            name="fact_checker",
            role="Doğrulayıcı",
            model=model,
            temperature=0.2,  # Çok düşük: Doğrulama objektif olmalı
        )
    
    def _build_system_prompt(self):
        return "Sen bir doğrulama uzmanısın..."
    
    async def process(self, input_data):
        # Bilgileri doğrula
        ...
```

### Beklenen Davranış
```
Pipeline: Planner → Researcher → FactChecker → Critic → Synthesizer
FactChecker çıktısı:
  ✅ Doğrulanmış: AI eğitimde kullanılıyor
  ⚠️ Doğrulanamamış: %90 verimlilik artışı
  ❌ Yanlış: AI tüm öğretmenlerin yerini aldı
```

---

## Alıştırma 2: Shared Memory Entegrasyonu (⭐⭐ Orta)

### Görev
Agent'ların orkestratör yerine **Shared Memory** üzerinden iletişim kurmasını sağlayın.

### Adımlar
1. `mcp/tools/shared_memory.py`'deki `SharedMemoryTool`'u import edin
2. Her agent `process()` çağrısından sonra sonucunu Shared Memory'ye kaydetsin
3. Her agent, önceki agent'ın çıktısını Shared Memory'den okusun
4. Pipeline sonunda tüm anahtarları listeleyin

### İpuçları
```python
# Orchestrator'da SharedMemory kullan
memory = SharedMemoryTool()

# Planner çalıştıktan sonra
memory.store("plan", planner_result.content)

# Researcher çalışmadan önce
plan = memory.retrieve("plan")
researcher_result = await researcher.process(plan["value"])
```

### Beklenen Davranış
```
Shared Memory İçeriği:
  plan: "1. AI uygulamaları 2. Kişisel öğrenme..."
  research: "ARAŞTIRMA BULGULARI:..."
  critique: "ELEŞTİRİ RAPORU:..."
  final_report: "# Yapay Zeka ve Eğitim..."
```

---

## Alıştırma 3: Dinamik Pipeline (⭐⭐ Orta)

### Görev
Critic'in puanına göre pipeline'ı **dinamik olarak yönlendirin**.

Eğer Critic'in puanı 7'den düşükse:
- Researcher'a geri dön ve ek araştırma yaptır
- Tekrar Critic'e gönder
- Maksimum 2 tur tekrar yapılabilir

### İpuçları
1. Critic'in çıktısından puanı çıkarmak için basit bir parsing fonksiyonu yazın
2. Orchestrator'a `max_retries` parametresi ekleyin
3. Pipeline'da "geri dönüş" (loop-back) mekanizması ekleyin

### Başlangıç Kodu
```python
def _extract_score(self, critic_output: str) -> int:
    """Critic çıktısından puan çıkar (1-10)."""
    # "Puan: 6/10" veya "Genel Değerlendirme: 6" gibi ifadeleri ara
    import re
    match = re.search(r'(\d+)\s*/?\s*10', critic_output)
    if match:
        return int(match.group(1))
    return 5  # Varsayılan puan

async def run_pipeline_with_retry(self, task, max_retries=2):
    """Dinamik pipeline: Critic puanı düşükse tekrar dene."""
    # İlk turda normal pipeline çalıştır
    # Critic puanı düşükse researcher'a geri dön
    ...
```

### Beklenen Davranış
```
Tur 1:
  Planner → Researcher → Critic (Puan: 5/10 - Düşük!)
  → Researcher'a geri dönülüyor...

Tur 2:
  Researcher (ek araştırma) → Critic (Puan: 8/10 - Yeterli!)
  → Synthesizer'a devam ediliyor...
```

---

## Alıştırma 4: Agent İstatistikleri (⭐⭐⭐ Zor)

### Görev
Her agent için detaylı istatistik toplayan bir **AgentProfiler** sınıfı yazın.

İstatistikler:
- Çalışma süresi (saniye)
- Çıktı uzunluğu (karakter)
- Token kullanımı (input/output)
- Başarı/başarısızlık oranı

### İpuçları
1. `shared/telemetry/cost_tracker.py`'deki `CostTracker`'dan ilham alın
2. Her agent çağrısını `time.time()` ile ölçün
3. İstatistikleri bir sözlükte toplayın
4. `get_report()` metodu ile güzel formatlı rapor üretin

### Beklenen Çıktı
```
📊 Agent İstatistikleri
═══════════════════════════════════
Agent: planner
  Süre:          1.23s
  Çıktı:         456 karakter
  Token (input):  200
  Token (output): 150
  Başarı:         ✅

Agent: researcher
  Süre:          2.45s
  Çıktı:         1234 karakter
  Token (input):  350
  Token (output): 400
  Başarı:         ✅
═══════════════════════════════════
```

---

## Alıştırma 5: Paralel Agent Çalıştırma (⭐⭐⭐ Zor)

### Görev
Birbirinden bağımsız agent'ları **paralel** çalıştırın.

Örneğin, Planner 3 alt görev belirlediyse:
- 3 ayrı Researcher agent'ı AYNI ANDA çalışsın
- Her biri farklı bir alt görevi araştırsın
- Hepsi bitince sonuçlar birleştirilsin

### İpuçları
1. `asyncio.gather()` kullanarak birden fazla async fonksiyonu paralel çalıştırın
2. Her alt görev için yeni bir `ResearcherAgent` oluşturun
3. Sonuçları birleştirip Critic'e gönderin

### Başlangıç Kodu
```python
async def run_parallel_research(self, subtasks: list[str]) -> list[AgentResult]:
    """Birden fazla araştırma görevini paralel çalıştır."""
    tasks = []
    for i, subtask in enumerate(subtasks):
        researcher = ResearcherAgent()
        researcher.name = f"researcher_{i+1}"
        tasks.append(researcher.process(subtask))
    
    # Tüm araştırmaları paralel çalıştır
    results = await asyncio.gather(*tasks)
    return results
```

### Beklenen Davranış
```
Planner: 3 alt görev belirlendi
  → researcher_1 başladı: "AI uygulamaları"
  → researcher_2 başladı: "Kişisel öğrenme"
  → researcher_3 başladı: "Gelecek trendleri"
  
  (3 araştırma AYNI ANDA çalışır)
  
  ← researcher_1 tamamlandı (1.2s)
  ← researcher_3 tamamlandı (1.5s)
  ← researcher_2 tamamlandı (1.8s)

Toplam süre: ~1.8s (sıralı olsaydı: ~4.5s)
```

---

## ✅ Kontrol Listesi

Tüm alıştırmaları tamamladıktan sonra şunları yapabilmelisiniz:

- [ ] Yeni bir agent rolü oluşturup pipeline'a ekleyebiliyorum
- [ ] Shared Memory ile agent'lar arası veri paylaşımı yapabiliyorum
- [ ] Pipeline'da dinamik yönlendirme (koşullu dallanma) yapabiliyorum
- [ ] Agent performans istatistikleri toplayabiliyorum
- [ ] Paralel agent çalıştırarak performans artışı sağlayabiliyorum

---

> 💡 **İpucu:** Takıldığınızda `expected_outputs/` klasöründeki örneklere bakın.
> Hâlâ takılıyorsanız, `theory.md`'yi tekrar okuyun.
> Her alıştırmada testlerinizi `tests/test_multi_agent.py`'ye ekleyin.
