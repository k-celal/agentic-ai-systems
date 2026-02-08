# 🗺️ Öğrenme Yol Haritası (Roadmap)

## Genel Bakış

Bu yol haritası, sizi **sıfırdan production-ready AI agent** geliştiricisi yapacak şekilde tasarlanmıştır.
Her modül bir öncekinin üzerine inşa eder. Sırayla ilerlemenizi öneririz.

---

## 📅 Önerilen İlerleme Planı

| Hafta | Modül | Konu | Tahmini Süre |
|-------|-------|------|-------------|
| 1 | Module 1 | Agent Temelleri + MCP Giriş | 8-10 saat |
| 2 | Module 2 | Reflection (Yansıtma) | 6-8 saat |
| 3 | Module 3 | Tool Use & MCP Mühendisliği | 10-12 saat |
| 4 | Module 4 | Evals & Optimization | 8-10 saat |
| 5 | Module 5 | Multi-Agent Sistemleri | 10-12 saat |
| 6-7 | Capstone | Production Agent Projesi | 15-20 saat |

**Toplam**: ~60-70 saat (yoğun tempo ile 4-6 hafta)

---

## 🧩 Modül Detayları

### Module 1: Agent Fundamentals (Agent Temelleri)

**Kazanımlar:**
- Agent nedir, neden sadece prompt yetmez?
- Agent execution loop: Think → Decide → Act → Observe
- MCP ile ilk tool bağlantısı
- Human-in-the-Loop (HITL) kavramı
- Basit başarı/başarısızlık değerlendirmesi

**Proje:** Hello Agent + Hello MCP
- Basit bir agent döngüsü
- Echo, time gibi MCP tool'ları

**Ön Koşul:** Python temelleri, LLM API bilgisi (isteğe bağlı)

---

### Module 2: Reflection (Yansıtma)

**Kazanımlar:**
- Agent neden kendini eleştirmeli?
- Reflection pattern (üret → eleştir → geliştir)
- Tool çıktısını doğrulama
- Maliyet vs fayda analizi

**Proje:** Reflective Agent + Validation Tool
- Agent bir metin üretir
- MCP validation tool ile kontrol eder
- Eleştirir ve geliştirir

**Ön Koşul:** Module 1

---

### Module 3: Tool Use & MCP (Araç Kullanımı)

**Kazanımlar:**
- MCP client/server mimarisi detaylı
- Tool schema ve contracts
- Tool versiyonlama (search@v1, search@v2)
- Hata yönetimi: timeout, retry, idempotency
- Güvenli kod çalıştırma (sandbox)

**Proje:** MCP Tool Registry + Error Handling
- Tool registry sistemi
- JSON schema doğrulama
- Hata yönetimi middleware'leri

**Ön Koşul:** Module 1, Module 2

---

### Module 4: Evals & Optimization (Değerlendirme ve Optimizasyon)

**Kazanımlar:**
- E2E (uçtan uca) değerlendirme
- Component-level eval (planner, tool selection)
- Hata kategorilendirme
- Maliyet optimizasyonu
- Model routing (ucuz model → pahalı model)

**Proje:** Eval Harness + Cost Guard + Model Router
- Otomatik değerlendirme sistemi
- Token maliyet takibi
- Akıllı model yönlendirme

**Ön Koşul:** Module 1-3

---

### Module 5: Multi-Agent Systems (Çoklu Agent)

**Kazanımlar:**
- Agent rolleri ve sorumlulukları
- Mesaj iletişim sistemi
- Paylaşılan hafıza (shared memory)
- Blackboard pattern
- Orkestrasyon stratejileri

**Proje:** Multi-Agent Research Team
- Planner, Researcher, Critic, Synthesizer rolleri
- Shared Memory MCP tool'u
- Mesajlaşma altyapısı

**Ön Koşul:** Module 1-4

---

### Capstone: Production Agent

**Kazanımlar:**
- Tüm kavramları birleştirme
- Production-ready mimari
- Gerçek dünya senaryosu

**Proje:** Test Automation AI Assistant
- UI test akışı planlama
- Tool'lar: runner, snapshot, selector
- Eval ve maliyet optimizasyonu

**Ön Koşul:** Tüm modüller

---

## 🎯 Modüller Arası Bağlantılar

```
MCP altyapısı ─────────────────────────────────────────┐
(shared/ altında başlar, her modülde büyür)             │
                                                        │
Module 1: Agent Loop ──► Module 2: Reflection ──┐      │
                                                 │      │
Module 3: Tool Use & MCP (derinleştirir) ◄──────┘      │
         │                                              │
         ▼                                              │
Module 4: Evals & Optimization                          │
         │                                              │
         ▼                                              │
Module 5: Multi-Agent ──► Capstone ◄────────────────────┘
```

---

## 💡 İpuçları

1. **Her modülü sırayla yapın** — atlamayın, her biri bir sonrakine hazırlık
2. **Exercises'leri mutlaka yapın** — sadece okumak yetmez
3. **Expected outputs ile karşılaştırın** — doğru yolda olduğunuzu doğrulayın
4. **Kendi deneylerinizi ekleyin** — "Ya şunu değiştirirsem ne olur?" sorusunu sorun
5. **tests/ klasöründeki eval'leri çalıştırın** — kodunuzun doğruluğunu kontrol edin
