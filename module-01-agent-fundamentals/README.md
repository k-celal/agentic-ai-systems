# 🧩 Module 1: Agent Fundamentals (Agent Temelleri)

## 🎯 Bu Modülün Amacı

"Agent nedir, neden sadece bir prompt yetmez?" sorusunu cevaplayacağız.
İlk agent'ınızı yazacak ve MCP tool'ları ile bağlayacaksınız.

---

## 📚 Kazanımlar

Bu modülü tamamladığınızda:

- [x] Agent ile chatbot arasındaki farkı anlayacaksınız
- [x] Agent execution loop'u (Think → Decide → Act → Observe) yazabileceksiniz
- [x] MCP server oluşturup basit tool'lar ekleyebileceksiniz
- [x] Agent'ın MCP üzerinden tool çağırmasını sağlayabileceksiniz
- [x] HITL (Human-in-the-Loop) kavramını bileceksiniz
- [x] Basit bir başarı/başarısızlık değerlendirmesi yapabileceksiniz

---

## 📁 Dosya Yapısı

```
module-01-agent-fundamentals/
├── README.md              ← 📍 Buradasınız
├── theory.md              ← Kavramsal açıklamalar
├── agent/
│   ├── __init__.py
│   ├── loop.py            ← Agent çalışma döngüsü
│   ├── planner.py         ← Basit görev planlayıcı
│   └── run.py             ← Çalıştırma scripti
├── mcp/
│   ├── server.py          ← MCP sunucusu
│   └── tools/
│       ├── __init__.py
│       ├── echo.py        ← Echo aracı (gelen mesajı geri döndür)
│       └── time_tool.py   ← Zaman aracı (şu anki saati döndür)
├── exercises/
│   └── exercises.md       ← Pratik görevler
├── expected_outputs/
│   └── sample_output.txt  ← Beklenen çıktı örnekleri
└── tests/
    └── test_agent.py      ← Mini değerlendirmeler
```

---

## 🚀 Nasıl Çalıştırılır?

### 1. Ortamı Hazırlayın

```bash
# Proje kök dizininde olduğunuzdan emin olun
cd agentic-ai-systems

# Virtual environment aktif olmalı
source venv/bin/activate  # macOS/Linux
# veya: venv\Scripts\activate  # Windows
```

### 2. Agent'ı Çalıştırın

```bash
# Module 1 dizinine gidin
cd module-01-agent-fundamentals

# Agent'ı başlatın
python -m agent.run
```

### 3. MCP Server'ı Test Edin (Ayrı bir terminal)

```bash
# MCP server'ı başlatın
python -m mcp.server
```

---

## 🔑 Temel Kavramlar

### Agent vs Chatbot

| Özellik | Chatbot | Agent |
|---------|---------|-------|
| Çalışma şekli | Tek soru → tek cevap | Döngüde çalışır |
| Araç kullanımı | Yok | Tool çağırabilir |
| Planlama | Yok | Görevi adımlara böler |
| Kendini düzeltme | Yok | Sonucu değerlendirir |
| Bellek | Sınırlı | Mesaj geçmişi tutar |

### Agent Execution Loop

```
Kullanıcı: "İstanbul'da saat kaç?"
    │
    ▼
🧠 DÜŞÜN: "Saati öğrenmem lazım, time tool'unu kullanmalıyım"
    │
    ▼
📋 KARAR VER: Tool çağır → get_time(timezone="Europe/Istanbul")
    │
    ▼
🔧 YÜRÜT: MCP Server'a istek gönder → "14:30:00"
    │
    ▼
👁️ GÖZLEMLE: "Saati aldım, kullanıcıya söyleyebilirim"
    │
    ▼
💬 CEVAP: "İstanbul'da saat şu anda 14:30."
```

---

## 📝 Adım Adım Rehber

### Adım 1: Theory'yi Okuyun
[theory.md](theory.md) dosyasını okuyarak kavramları anlayın.

### Adım 2: Kodu İnceleyin
1. `agent/loop.py` — Agent döngüsünün nasıl çalıştığını
2. `agent/planner.py` — Görev planlamanın nasıl yapıldığını
3. `mcp/tools/` — Tool'ların nasıl tanımlandığını inceleyin

### Adım 3: Çalıştırın ve Deneyin
`agent/run.py`'yi çalıştırarak agent'ı görev ile test edin.

### Adım 4: Exercises Yapın
[exercises/exercises.md](exercises/exercises.md) dosyasındaki görevleri tamamlayın.

### Adım 5: Testleri Çalıştırın
```bash
pytest tests/ -v
```

---

## ➡️ Sonraki Modül

Tebrikler! Artık bir agent yazabilirsiniz. 🎉

Bir sonraki modülde, agent'ınızın **kendini eleştirmesini ve geliştirmesini** öğreneceksiniz.

→ [Module 2: Reflection](../module-02-reflection/README.md)
