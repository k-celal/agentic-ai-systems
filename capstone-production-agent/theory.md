# 📖 Capstone Teori: Production Agent Mühendisliği

## Öğrenme Agent'ından Production Agent'ına

Modüllerde öğrendiğiniz agent'lar **eğitim amaçlıydı**. Production'da işler farklıdır:

| Boyut | Öğrenme Agent'ı | Production Agent |
|-------|-----------------|------------------|
| Hata | "Hata oldu, debug ederim" | Otomatik retry, fallback |
| Maliyet | "Token ucuz, sorun yok" | Her kuruş takip edilir |
| Güvenilirlik | "Çoğu zaman çalışıyor" | %99.9+ uptime |
| İzlenebilirlik | `print()` yeter | Structured logging, tracing |
| Ölçeklenebilirlik | Tek kullanıcı | Eşzamanlı çoklu istek |

---

## 1. Multi-Agent Orkestrasyon: Pipeline Düşüncesi

TwinGraph Studio'da agent'lar bir **pipeline** oluşturur:

```
Research → Writing → Reflection → [Yeterli mi?]
                                      │
                              Evet ───┤─── Hayır
                                │           │
                          Repurpose     Writing'e
                                │       geri dön
                          Çıktı Kaydet
```

### Neden Pipeline?

1. **Sorumluluk ayrımı**: Her agent tek bir şeyi iyi yapar
2. **Debug kolaylığı**: Hangi adımda sorun var, hemen görürsün
3. **Maliyet kontrolü**: Her adımın maliyetini ayrı ölçersin
4. **Kalite kontrolü**: Reflection pipeline'ın ortasında kalite kapısı

---

## 2. GraphRAG: Hafıza ile Akıllı İçerik

### Nedir?

Normal bir LLM her seferinde "sıfırdan" düşünür. GraphRAG ile agent **hatırlar**:

```
Geleneksel:
  Soru: "MCP nedir?"
  → LLM: Genel bilgi (eğitim verisinden)

GraphRAG ile:
  Soru: "MCP nedir?"
  → Graph Store: "MCP → agent → tool → protocol" ilişkileri
  → Vector Store: Benzer önceki yazılar
  → LLM: Zenginleştirilmiş, tutarlı, kişisel cevap
```

### İki Katmanlı Hafıza

```
┌─────────────────────────────────────────┐
│             HAFIZA SİSTEMİ              │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │  Graph Store  │  │  Vector Store  │  │
│  │              │  │               │  │
│  │  Kavram ──── │  │ "MCP agent    │  │
│  │  ↕    ↕     │  │  tool proto..." │  │
│  │  İlişki     │  │  → benzer      │  │
│  │  ↕    ↕     │  │    içerikler   │  │
│  │  Alt kavram │  │               │  │
│  └──────────────┘  └────────────────┘  │
│                                         │
│  Graph: "Ne ile ne bağlantılı?"         │
│  Vector: "Buna en benzer ne var?"       │
└─────────────────────────────────────────┘
```

---

## 3. Model Routing: Akıllı Maliyet Yönetimi

Her görevin aynı modele ihtiyacı yoktur:

```
┌──────────────┐
│  Görev Geldi │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Karmaşıklık      │
│ Analizi          │
└──────┬───────────┘
       │
  ┌────┼────┐
  ▼         ▼
Basit     Karmaşık
  │         │
  ▼         ▼
gpt-4o    gpt-4o
-mini     (pahalı)
(ucuz)
  │         │
  ▼         ▼
$0.15     $2.50
/1M tok   /1M tok
```

### TwinGraph'ta Model Routing

| Agent | Görev Tipi | Model | Neden? |
|-------|------------|-------|--------|
| Orchestrator | Planlama | gpt-4o-mini | Basit koordinasyon |
| Research | Özetleme | gpt-4o-mini | Çok sayıda çağrı, ucuz olmalı |
| Writing | Final yazım | gpt-4o | Kalite kritik |
| Reflection | Eleştiri | gpt-4o-mini | Hata bulma, basit |
| Repurpose | Format dönüşümü | gpt-4o-mini | Şablon tabanlı |

**Sonuç:** Toplam maliyeti %60-70 düşürebilirsiniz.

---

## 4. Eval: "Çalışıyor" Yetmez

### Writing Eval

```python
# İçerik kalitesini 5 boyutta ölç
dimensions = {
    "coherence":  "Tutarlılık — fikirler mantıklı akıyor mu?",
    "depth":      "Derinlik — yüzeysel mi, derinlemesine mi?",
    "originality":"Özgünlük — klişe mi, taze bakış açısı mı?",
    "structure":  "Yapı — başlık, paragraf, akış düzgün mü?",
    "citations":  "Kaynak — iddialar desteklenmiş mi?",
}
```

### Cost Eval

```python
# Maliyet etkinliğini ölç
metrics = {
    "token_per_word":     "Kaç token harcayarak 1 kelime ürettin?",
    "cost_per_article":   "Bir makale kaça mal oldu?",
    "reflection_roi":     "Reflection maliyeti vs kalite artışı",
    "routing_savings":    "Model routing ne kadar tasarruf sağladı?",
}
```

---

## 5. Retry & Error Recovery

Production'da her şey ilk seferde çalışmaz:

```
İstek → Başarısız (429 Rate Limit)
  │
  ├── Deneme 1: Hemen (başarısız)
  ├── Deneme 2: 1s bekle (başarısız)
  ├── Deneme 3: 3s bekle (başarılı ✅)
  │
  └── 3 denemede de başarısız?
       → Fallback: Farklı model dene
       → Fallback: Cache'ten döndür
       → Son çare: Graceful error
```

---

## 6. Structured Logging

`print()` yerine structured log:

```python
# Kötü
print("Agent çalıştı")

# İyi
logger.info("agent.writing.draft_created", extra={
    "agent": "writing",
    "version": "v1",
    "word_count": 1250,
    "token_used": 3400,
    "duration_ms": 2300,
    "model": "gpt-4o",
})
```

Yapılandırılmış loglar:
- Filtrelenebilir (sadece hataları göster)
- Aranabilir (hangi agent en çok token harcadı?)
- Görselleştirilebilir (dashboard)

---

## 🔗 İleri Okuma

- [docs/01-concepts-map.md](../docs/01-concepts-map.md) — Kavram haritası
- [docs/03-evals-and-metrics.md](../docs/03-evals-and-metrics.md) — Eval detayları
- [Module 5: Multi-Agent](../module-05-multi-agent/README.md) — Multi-agent temelleri
