# 📊 Module 4: Evals & Optimization (Değerlendirme ve Optimizasyon)

## 🎯 Bu Modülün Amacı

Agent sisteminizin **ne kadar iyi çalıştığını ölçmeyi** ve **maliyetini optimize etmeyi** öğreneceksiniz:
- Uçtan uca (E2E) değerlendirme
- Bileşen bazlı değerlendirme (planner, tool seçimi)
- Maliyet kontrolü ve bütçe yönetimi
- Akıllı model yönlendirme
- Bağlam sıkıştırma (context compression)
- Detaylı izleme (tracing/telemetry)

---

## 📚 Kazanımlar

- [x] Agent'ınızın başarı oranını sistematik olarak ölçebileceksiniz
- [x] Planner doğruluğunu ve tool seçim isabetini test edebileceksiniz
- [x] Token harcamasını izleyip bütçe limiti koyabileceksiniz
- [x] Basit görevleri ucuz modele, karmaşık görevleri güçlü modele yönlendirebileceksiniz
- [x] Konuşma geçmişini sıkıştırarak token tasarrufu yapabileceksiniz
- [x] Her adımı zamanlama ve maliyetiyle izleyebileceksiniz (tracing)

---

## 📁 Dosya Yapısı

```
module-04-evals-and-optimization/
├── README.md                            ← Bu dosya
├── theory.md                            ← Teori: Eval, optimizasyon, model routing
├── evals/
│   ├── __init__.py
│   ├── e2e.py                           ← Uçtan uca değerlendirme çatısı
│   ├── planner_eval.py                  ← Planner doğruluğu değerlendirmesi
│   └── tool_eval.py                     ← Tool seçim isabeti değerlendirmesi
├── optimization/
│   ├── __init__.py
│   ├── cost_guard.py                    ← Maliyet koruyucu (bütçe limiti)
│   ├── context_compress.py              ← Bağlam sıkıştırıcı (token tasarrufu)
│   └── model_router.py                  ← Akıllı model yönlendirici
├── telemetry/
│   ├── __init__.py
│   └── traces.py                        ← Adım adım izleme (tracing)
├── exercises/
│   └── exercises.md                     ← Alıştırmalar
├── expected_outputs/
│   └── sample_output.txt                ← Örnek çıktı
└── tests/
    ├── __init__.py
    └── test_evals.py                    ← Testler
```

---

## 🚀 Nasıl Çalıştırılır?

```bash
# Modül dizinine geçin
cd module-04-evals-and-optimization

# Uçtan uca değerlendirme çatısını çalıştırın
python -m evals.e2e

# Planner değerlendirmesini çalıştırın
python -m evals.planner_eval

# Tool seçim değerlendirmesini çalıştırın
python -m evals.tool_eval

# Maliyet koruyucu demosunu çalıştırın
python -m optimization.cost_guard

# Bağlam sıkıştırma demosunu çalıştırın
python -m optimization.context_compress

# Model yönlendirici demosunu çalıştırın
python -m optimization.model_router

# Telemetry/tracing demosunu çalıştırın
python -m telemetry.traces

# Testleri çalıştırın
python -m pytest tests/ -v
```

---

## 🔑 Temel Kavramlar

### Neden Eval Yapmalıyız?

"Ölçemezseniz, geliştiremezsiniz." Agent geliştirmede en büyük hata: **hissiyata göre geliştirme**.

```
❌ Yanlış Yaklaşım:
   "Çalışıyor gibi görünüyor" → Deploy et → Kullanıcılar şikayet eder

✅ Doğru Yaklaşım:
   Eval yaz → Ölç → İyileştir → Tekrar ölç → Deploy et
```

### Eval Türleri

```
┌─────────────────────────────────────────────────────────────┐
│                    EVAL PİRAMİDİ                            │
│                                                             │
│                    ┌──────────┐                              │
│                    │  E2E     │  ← Uçtan uca                │
│                    │  Eval    │    (en yavaş, en değerli)    │
│                   ┌┴──────────┴┐                             │
│                   │  Bileşen    │  ← Planner, Tool, LLM     │
│                   │  Eval'leri  │    (orta hız)              │
│                  ┌┴─────────────┴┐                           │
│                  │  Birim Testler │  ← Fonksiyon bazlı       │
│                  │  (Unit Tests)  │    (en hızlı)            │
│                  └───────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Optimizasyon Stratejileri

```
┌──────────────────────────────────────────────────────────────┐
│               MALİYET OPTİMİZASYON STRATEJİLERİ             │
│                                                              │
│  1. Model Routing                                            │
│     ┌─────────┐    Basit görev    ┌──────────────┐          │
│     │  Görev  │───────────────────│ gpt-4o-mini  │ (ucuz)   │
│     │ Analizi │                    └──────────────┘          │
│     │         │    Karmaşık görev ┌──────────────┐          │
│     └─────────┘───────────────────│   gpt-4o     │ (güçlü)  │
│                                    └──────────────┘          │
│                                                              │
│  2. Context Compression                                      │
│     [10 mesaj, 5000 token] → Sıkıştır → [özet, 500 token]  │
│                                                              │
│  3. Cost Guard                                               │
│     Bütçe: $1.00 → Kullanım: $0.85 → ⚠️ Uyarı!            │
│     Bütçe: $1.00 → Kullanım: $1.01 → 🛑 Durdur!           │
└──────────────────────────────────────────────────────────────┘
```

---

## 💡 İpuçları

1. **Eval'leri her değişiklikten önce ve sonra çalıştırın** — Regresyon yakalamanın tek yolu budur
2. **Maliyet limitlerini her zaman koyun** — Sonsuz döngüde kalan agent cüzdanınızı boşaltabilir
3. **Model routing ile %80 maliyet tasarrufu mümkün** — Her görev GPT-4o gerektirmez
4. **Context compression ile uzun konuşmaları yönetin** — 128K context window bile bir noktada dolar

---

## ➡️ Sonraki Modül
→ [Module 5: Multi-Agent Systems](../module-05-multi-agent/README.md)
