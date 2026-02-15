# 🪞 Module 2: Reflection (Yansıtma)

## 🎯 Bu Modülün Amacı

Agent'ınıza **kendini eleştirme ve geliştirme** yeteneği kazandıracağız.
"Ürettim, bitti" yerine "Ürettim, kontrol ettim, geliştirdim" döngüsü kuracağız.

---

## 📚 Kazanımlar

Bu modülü tamamladığınızda:

- [x] Reflection pattern'i anlayacak ve uygulayabileceksiniz
- [x] Agent'ın kendi çıktısını eleştirmesini sağlayabileceksiniz
- [x] MCP validation tool ile dış doğrulama yapabileceksiniz
- [x] "Maliyet vs Fayda" dengesini değerlendirebileceksiniz
- [x] Reflection'ın ne zaman faydalı, ne zaman gereksiz olduğunu bileceksiniz

---

## 📁 Dosya Yapısı

```
module-02-reflection/
├── README.md              ← 📍 Buradasınız
├── theory.md              ← Reflection kavramları
├── agent/
│   ├── __init__.py
│   ├── generate.py        ← İçerik üretici
│   ├── critique.py        ← Eleştiri modülü
│   ├── improve.py         ← İyileştirme modülü
│   └── run.py             ← Çalıştırma scripti
├── mcp/
│   ├── __init__.py
│   └── tools/
│       ├── __init__.py
│       └── validate.py    ← Doğrulama aracı
├── exercises/
│   └── exercises.md
├── expected_outputs/
│   └── sample_output.txt
└── tests/
    └── test_reflection.py
```

---

## 🚀 Nasıl Çalıştırılır?

```bash
cd module-02-reflection
python -m agent.run
```

---

## 🔑 Temel Kavram: Reflection Pattern

```
┌──────────────────────────────────────────────────────────┐
│                  REFLECTION DÖNGÜSÜ                       │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │  ÜRET    │───►│ ELEŞTİR  │───►│ GELİŞTİR │           │
│  │(Generate)│    │(Critique) │    │(Improve)  │           │
│  └──────────┘    └──────────┘    └─────┬─────┘           │
│       ▲                                │                  │
│       │           Yeterli mi?          │                  │
│       │    ┌──────────────────┐        │                  │
│       └────│  Hayır → Tekrarla│◄───────┘                  │
│            │  Evet  → Bitir   │                           │
│            └──────────────────┘                           │
└──────────────────────────────────────────────────────────┘
```

### Gerçek Hayat Analojisi

Bir makale yazıyorsunuz:
1. **Üret:** İlk taslağı yazarsınız
2. **Eleştir:** "Hmm, giriş bölümü zayıf, örnekler eksik"
3. **Geliştir:** Giriş bölümünü güçlendirir, örnekler eklersiniz
4. **Tekrar kontrol:** "Şimdi daha iyi ama sonuç bölümü kısa" → Tekrar geliştir

Agent da tam olarak bunu yapar!

---

## ➡️ Sonraki Modül
→ [Module 3: Tool Use & MCP](../module-03-tools-and-mcp/README.md)
