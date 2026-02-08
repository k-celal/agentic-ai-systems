# 📊 Değerlendirme ve Metrikler Rehberi (Evals & Metrics)

## Neden Eval Yapmalıyız?

Bir agent "çalışıyor" demek yetmez. Şu soruları cevaplamalıyız:
- **Doğru mu?** Görevi gerçekten başarıyla tamamlıyor mu?
- **Ne kadar maliyetli?** Her görev için ne kadar token/para harcıyor?
- **Ne kadar hızlı?** Kullanıcı ne kadar bekliyor?
- **Güvenilir mi?** 100 denemeden kaçında başarılı?

---

## 📐 Evaluation Seviyeleri

### Seviye 1: Unit Eval (Birim Değerlendirme)

Tek bir bileşeni test eder:

```python
# Örnek: Tool doğru parametre ile çağrılıyor mu?
def test_tool_call_params():
    """Agent 'İstanbul hava durumu' dediğinde
    get_weather tool'unu city='Istanbul' ile çağırmalı"""
    
    result = agent.plan("İstanbul'da hava nasıl?")
    
    assert result.tool_name == "get_weather"
    assert result.params["city"] == "Istanbul"
```

### Seviye 2: Component Eval (Bileşen Değerlendirmesi)

Agent'ın bir alt sistemini test eder:

```python
# Örnek: Planner doğru adımları üretiyor mu?
def test_planner_steps():
    """Karmaşık bir görev için planner
    mantıklı adımlar üretmeli"""
    
    steps = planner.decompose("Blog yazısı yaz ve yayınla")
    
    assert len(steps) >= 3
    assert any("araştır" in s.lower() for s in steps)
    assert any("yaz" in s.lower() for s in steps)
```

### Seviye 3: E2E Eval (Uçtan Uca Değerlendirme)

Tüm sistemi test eder:

```python
# Örnek: Agent görevi baştan sona tamamlıyor mu?
def test_e2e_weather_summary():
    """Agent hava durumu özetini başarıyla üretmeli"""
    
    result = agent.run("İstanbul hava durumunu özetle")
    
    assert result.status == "success"
    assert "İstanbul" in result.output
    assert any(word in result.output for word in ["derece", "°C", "sıcaklık"])
```

---

## 📏 Temel Metrikler

### 1. Başarı Oranı (Success Rate)

```
Başarı Oranı = Başarılı Görevler / Toplam Görevler × 100

Örnek: 100 görevden 87'si başarılı → %87 başarı oranı
```

**Hedef:** Production için minimum %90+

### 2. Token Maliyeti (Token Cost)

```
Görev Maliyeti = (Input Tokens × Input Fiyatı) + (Output Tokens × Output Fiyatı)

Örnek (GPT-4o-mini):
  Input:  1500 token × $0.15/1M = $0.000225
  Output:  500 token × $0.60/1M = $0.000300
  Toplam: $0.000525 (~0.05 cent)
```

**Takip edilecek:** Ortalama görev maliyeti, en pahalı görevler

### 3. Gecikme (Latency)

```
Toplam Süre = LLM Çağrı Süresi + Tool Çalışma Süresi + Ağ Gecikmesi

Örnek:
  LLM çağrısı: 1.2s
  Tool çağrısı: 0.3s
  × 3 döngü iterasyonu
  Toplam: ~4.5s
```

**Hedef:** Kullanıcı-etkileşimli görevler için <10s

### 4. Döngü Sayısı (Loop Iterations)

```
Kaç döngüde tamamlandı?

İdeal:  1-3 döngü (basit görevler)
Normal: 3-5 döngü (orta görevler)
Uyarı:  5+ döngü (sonsuz döngü riski!)
```

### 5. Tool Çağrı Başarısı (Tool Call Success)

```
Tool Başarı Oranı = Başarılı Tool Çağrıları / Toplam Tool Çağrıları × 100

Hata Tipleri:
  - Yanlış tool seçimi
  - Hatalı parametreler
  - Timeout
  - Tool hatası
```

---

## 🔬 Eval Nasıl Yapılır?

### Adım 1: Test Senaryoları Hazırlayın

```python
# eval_cases.py
EVAL_CASES = [
    {
        "id": "weather_simple",
        "task": "İstanbul'da hava nasıl?",
        "expected_tool": "get_weather",
        "expected_contains": ["İstanbul", "derece"],
        "max_loops": 3,
        "max_cost": 0.01,
    },
    {
        "id": "weather_compare",
        "task": "İstanbul ve Ankara'nın hava durumunu karşılaştır",
        "expected_tool": "get_weather",
        "expected_contains": ["İstanbul", "Ankara", "karşılaştır"],
        "max_loops": 5,
        "max_cost": 0.05,
    },
]
```

### Adım 2: Eval Runner Yazın

```python
# eval_runner.py
def run_eval(cases):
    results = []
    for case in cases:
        result = agent.run(case["task"])
        
        score = {
            "id": case["id"],
            "success": result.status == "success",
            "correct_tool": result.tool_used == case["expected_tool"],
            "output_valid": all(
                word in result.output 
                for word in case["expected_contains"]
            ),
            "loops": result.loop_count,
            "cost": result.total_cost,
            "latency": result.total_time,
        }
        results.append(score)
    
    return results
```

### Adım 3: Sonuçları Analiz Edin

```python
# eval_report.py
def print_report(results):
    total = len(results)
    success = sum(1 for r in results if r["success"])
    avg_cost = sum(r["cost"] for r in results) / total
    avg_latency = sum(r["latency"] for r in results) / total
    
    print(f"Başarı Oranı: {success}/{total} ({success/total*100:.1f}%)")
    print(f"Ortalama Maliyet: ${avg_cost:.4f}")
    print(f"Ortalama Gecikme: {avg_latency:.2f}s")
    
    # Başarısız olanları göster
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\nBaşarısız Görevler ({len(failures)}):")
        for f in failures:
            print(f"  - {f['id']}: loops={f['loops']}, cost=${f['cost']:.4f}")
```

---

## 📈 Metrik Takip Tablosu

Her modülü tamamladığınızda bu tabloyu doldurun:

| Metrik | Module 1 | Module 2 | Module 3 | Module 4 | Module 5 | Capstone |
|--------|----------|----------|----------|----------|----------|----------|
| Başarı Oranı | | | | | | |
| Ort. Maliyet | | | | | | |
| Ort. Gecikme | | | | | | |
| Ort. Döngü | | | | | | |
| Tool Başarısı | | | | | | |

---

## 🎯 Optimization Stratejileri

### Maliyet Düşürme
1. **Model Routing:** Basit görevler için ucuz model kullan
2. **Context Compression:** Gereksiz mesajları kaldır
3. **Caching:** Tekrarlanan sorguları cache'le
4. **Early Stopping:** Cevap hazırsa döngüyü bitir

### Hız Artırma
1. **Parallel Tool Execution:** Bağımsız tool'ları paralel çağır
2. **Streaming:** Sonuçları akış halinde döndür
3. **Model Seçimi:** Daha hızlı modeller tercih et

### Doğruluk Artırma
1. **Reflection:** Agent'ı kendini eleştirmeye zorla
2. **Validation Tools:** Çıktıyı doğrulama araçlarıyla kontrol et
3. **Better Prompts:** System prompt'ları iyileştir
4. **Few-Shot Examples:** Örnekler ekle

---

> 💡 **Eval olmadan optimization olmaz.** Önce ölç, sonra iyileştir. Her değişiklikten sonra tekrar ölç.
