# 📖 Module 2: Teori — Reflection (Yansıtma)

## Reflection Nedir?

**Reflection**, agent'ın kendi ürettiği çıktıyı **eleştirmesi** ve **geliştirmesi** sürecidir.

İnsanlar bunu doğal olarak yapar:
- Bir e-posta yazarsınız → okursunuz → "bu kısım kaba" → düzeltirsiniz
- Kod yazarsınız → çalıştırırsınız → hata alırsınız → düzeltirsiniz

AI Agent'lar da aynı şeyi yapabilir — ve yapmalıdır!

---

## Neden Reflection Önemli?

### Reflection olmadan:
```
Görev: "Python'da sıralama fonksiyonu yaz"
Agent: def sort(lst): return sorted(lst)  ← Çalışır ama basit, docstring yok, edge case yok
```

### Reflection ile:
```
Görev: "Python'da sıralama fonksiyonu yaz"

[ÜRET] Agent: def sort(lst): return sorted(lst)

[ELEŞTİR] Agent: 
  - ❌ Docstring eksik
  - ❌ Type hint yok
  - ❌ Boş liste kontrolü yok
  - ❌ Hata yönetimi yok

[GELİŞTİR] Agent:
  def sort(lst: list) -> list:
      """Listeyi küçükten büyüğe sıralar.
      
      Args:
          lst: Sıralanacak liste
      Returns:
          Sıralı liste
      Raises:
          TypeError: lst liste değilse
      """
      if not isinstance(lst, list):
          raise TypeError("Girdi bir liste olmalı")
      return sorted(lst)
```

Gördüğünüz gibi, reflection ile çıktı **çok daha kaliteli** oldu!

---

## Reflection Desenleri

### 1. Self-Reflection (Öz Yansıtma)
Agent, kendi çıktısını kendisi eleştirir.

```
LLM Çağrısı 1: "Python sıralama fonksiyonu yaz"
→ Çıktı üretilir

LLM Çağrısı 2: "Bu kodu eleştir, sorunları bul"
→ Eleştiri üretilir

LLM Çağrısı 3: "Eleştirileri dikkate alarak kodu geliştir"
→ İyileştirilmiş çıktı
```

**Avantaj:** Basit, ek tool gerekmez
**Dezavantaj:** LLM kendi hatalarını göremeyebilir

### 2. External Validation (Dış Doğrulama)
Bir tool/sistem ile doğrulama yapılır.

```
LLM: Kod üretir
→ Validation Tool: Kodu çalıştırır, lint kontrol eder
→ Sonuç: "3 hata bulundu: satır 5, 12, 18"
→ LLM: Hataları düzeltir
```

**Avantaj:** Objektif doğrulama
**Dezavantaj:** Tool geliştirmek gerekir

### 3. Hybrid (Karma)
Hem öz yansıtma hem dış doğrulama birlikte.

---

## Maliyet vs Fayda

Reflection **bedava değildir**! Her ek LLM çağrısı:
- 💰 Token maliyeti ekler
- ⏱️ Gecikme ekler

### Ne zaman reflection YAPMALIYIZ?

| Durum | Reflection Gerekli mi? |
|-------|----------------------|
| Kritik içerik (rapor, e-posta) | ✅ Evet |
| Uzun, karmaşık çıktılar | ✅ Evet |
| Doğrulanabilir sonuçlar (kod, matematik) | ✅ Evet (validation ile) |
| Basit soru-cevap | ❌ Gereksiz |
| Zaman kritik görevler | ⚠️ Dikkatli karar ver |

### Reflection Bütçesi Formülü

```
Reflection_Maliyeti = (Eleştiri_Tokens + İyileştirme_Tokens) × Fiyat
Reflection_Faydası  = Kalite_Artışı × Görev_Önemi

Karar: Fayda > Maliyet ise reflection yap
```

---

## Bu Modülün Mimarisi

```
┌─────────────────────────────────────────────────────┐
│                 REFLECTIVE AGENT                     │
│                                                      │
│  ┌──────────┐                                       │
│  │ generate │ ← İlk çıktıyı üret                   │
│  │   .py    │                                       │
│  └────┬─────┘                                       │
│       │                                             │
│       ▼                                             │
│  ┌──────────┐     ┌──────────────┐                  │
│  │ critique │────►│ MCP validate │ ← Dış doğrulama  │
│  │   .py    │     │   tool       │                  │
│  └────┬─────┘     └──────────────┘                  │
│       │                                             │
│       ▼                                             │
│  ┌──────────┐                                       │
│  │ improve  │ ← Eleştirilere göre geliştir          │
│  │   .py    │                                       │
│  └──────────┘                                       │
│                                                      │
│  Döngü: generate → critique → improve → critique...  │
└─────────────────────────────────────────────────────┘
```

---

## 🔗 İleri Okuma
- [docs/01-concepts-map.md](../docs/01-concepts-map.md) — Reflection kavram haritası
- [Module 3: Tool Use & MCP](../module-03-tools-and-mcp/README.md) — Sonraki modül
