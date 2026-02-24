# 🤝 Module 5: Multi-Agent Sistemleri (Çoklu Agent)

## 🎯 Bu Modülün Amacı

"Tek bir agent yetmediğinde ne yaparsınız?" sorusunu cevaplayacağız.
Birden fazla agent'ın **bir takım gibi birlikte çalışmasını** öğrenecek,
görev dağılımı yapan bir orkestratör sistemi kuracaksınız.

Düşünün ki bir şirkettesiniz:
- **Proje Yöneticisi** görevi planlar ve dağıtır
- **Araştırmacı** bilgi toplar
- **Kalite Kontrol** çıktıları denetler
- **Editör** her şeyi birleştirip son halini verir

İşte Multi-Agent sistemi tam olarak bunu yapar — ama AI agent'larla!

---

## 📚 Kazanımlar

Bu modülü tamamladığınızda:

- [x] Multi-Agent mimarisinin ne olduğunu ve neden gerektiğini anlayacaksınız
- [x] Agent rollerini (Planner, Researcher, Critic, Synthesizer) tanımlayabileceksiniz
- [x] Orkestratör (Orchestrator) ile agent'lar arası iletişimi yönetebileceksiniz
- [x] Mesaj geçişi (Message Passing) patternini uygulayabileceksiniz
- [x] Shared Memory (Ortak Bellek) ile agent'lar arası veri paylaşımı yapabileceksiniz
- [x] Tam bir multi-agent pipeline'ı çalıştırabileceksiniz

---

## 🧠 Multi-Agent Nedir?

Tek bir agent her şeyi yapmaya çalıştığında karmaşıklık artar ve hata oranı yükselir.
Multi-Agent yaklaşımında, **her agent tek bir rolde uzmanlaşır** ve birlikte çalışırlar.

### Tek Agent vs Multi-Agent

| Özellik | Tek Agent | Multi-Agent |
|---------|-----------|-------------|
| Karmaşıklık | Her şey tek yerde | Roller ayrılmış |
| Hata yönetimi | Hata bulması zor | Her agent kendi alanını denetler |
| Ölçeklenebilirlik | Sınırlı | Yeni agent eklenebilir |
| Uzmanlık | Genel | Her agent kendi alanında uzman |
| Kalite kontrol | Kendini değerlendirir | Ayrı bir Critic agent denetler |

### Agent Rolleri

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MULTI-AGENT SİSTEMİ                         │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐       │
│  │  📋 PLANNER  │────►│ 🔍 RESEARCHER│────►│ 🔎 CRITIC    │       │
│  │  (Planlayıcı)│     │ (Araştırmacı)│     │ (Eleştirmen) │       │
│  │              │     │              │     │              │       │
│  │ Görevi       │     │ Bilgi toplar │     │ Çıktıları    │       │
│  │ adımlara     │     │ ve araştırır │     │ inceler ve   │       │
│  │ böler        │     │              │     │ eleştirir    │       │
│  └──────────────┘     └──────────────┘     └──────┬───────┘       │
│         ▲                                          │               │
│         │                                          ▼               │
│         │              ┌──────────────┐     ┌──────────────┐       │
│         │              │ 🎼 ORCHESTRA-│     │ 📝 SYNTHE-   │       │
│         └──────────────│   TOR        │◄────│   SIZER      │       │
│                        │ (Orkestratör)│     │ (Sentezci)   │       │
│                        │              │     │              │       │
│                        │ Akışı        │     │ Tüm bulguları│       │
│                        │ yönetir      │     │ birleştirir  │       │
│                        └──────────────┘     └──────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Mesaj Akışı (Pipeline)

```
Kullanıcı Görevi
    │
    ▼
┌──────────┐   "Bu görevi şu      ┌──────────────┐   "Şu bilgileri    ┌──────────┐
│ PLANNER  │──  adımlara böldüm" ─►│  RESEARCHER  │──  buldum"        ─►│  CRITIC  │
│          │                       │              │                    │          │
│ Görevi   │                       │ Bilgi toplar │                    │ Kaliteyi │
│ planlar  │                       │ ve araştırır │                    │ denetler │
└──────────┘                       └──────────────┘                    └────┬─────┘
                                                                           │
                                                     "Eleştirilerim        │
                                                      bunlar"              │
                                                           │               │
                                                           ▼               │
                                                    ┌──────────────┐       │
                                                    │ SYNTHESIZER  │◄──────┘
                                                    │              │
                                                    │ Her şeyi     │
                                                    │ birleştirir  │
                                                    └──────┬───────┘
                                                           │
                                                           ▼
                                                    Son Rapor / Çıktı
```

---

## 📁 Dosya Yapısı

```
module-05-multi-agent/
├── README.md                      ← 📍 Buradasınız
├── theory.md                      ← Multi-Agent teorisi ve patternler
├── agents/
│   ├── __init__.py
│   ├── base_agent.py              ← BaseAgent soyut sınıfı
│   ├── planner.py                 ← PlannerAgent: Görevi planlar
│   ├── researcher.py              ← ResearcherAgent: Bilgi toplar
│   ├── critic.py                  ← CriticAgent: Çıktıları eleştirir
│   └── synthesizer.py             ← SynthesizerAgent: Bulguları birleştirir
├── orchestration/
│   ├── __init__.py
│   ├── orchestrator.py            ← Orkestratör: Agent akışını yönetir
│   └── run.py                     ← Ana çalıştırma scripti
├── mcp/
│   ├── __init__.py
│   └── tools/
│       ├── __init__.py
│       └── shared_memory.py       ← Ortak Bellek MCP aracı
├── exercises/
│   └── exercises.md               ← Pratik görevler
├── expected_outputs/
│   └── sample_output.txt          ← Beklenen çıktı örnekleri
└── tests/
    ├── __init__.py
    └── test_multi_agent.py        ← Testler
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

### 2. Multi-Agent Pipeline'ı Çalıştırın

```bash
# Module 5 dizinine gidin
cd module-05-multi-agent

# Pipeline'ı başlatın
python -m orchestration.run
```

### 3. Shared Memory Tool'unu Test Edin

```bash
# Shared Memory aracını tek başına test edin
python -m mcp.tools.shared_memory
```

### 4. Testleri Çalıştırın

```bash
pytest tests/ -v
```

---

## 🔑 Temel Kavramlar

### Orkestratör (Orchestrator) Nedir?

Orkestratör, bir **orkestra şefi** gibidir:
- Hangi agent'ın ne zaman çalışacağını belirler
- Agent'lar arası mesaj akışını yönetir
- Sonuçları toplar ve bir sonraki agent'a iletir
- Hata durumunda ne yapılacağına karar verir

### Shared Memory (Ortak Bellek) Nedir?

Agent'ların birbirleriyle veri paylaşmasını sağlayan bir MCP aracıdır:
- Bir agent veri yazar → Diğer agent'lar okuyabilir
- Key-value yapısında çalışır (sözlük gibi)
- Pipeline boyunca bilgi birikimini sağlar

### AgentMessage (Agent Mesajı) Nedir?

Agent'lar arası iletişimde kullanılan standart mesaj formatıdır:
- Kimden geldi? (sender)
- Kime gidiyor? (receiver)
- İçerik nedir? (content)
- Ne tür bir mesaj? (message_type)

---

## 📝 Adım Adım Rehber

### Adım 1: Theory'yi Okuyun
[theory.md](theory.md) dosyasını okuyarak multi-agent kavramlarını anlayın.

### Adım 2: Agent'ları İnceleyin
1. `agents/base_agent.py` — Tüm agent'ların temel sınıfı
2. `agents/planner.py` — Planlama agent'ı
3. `agents/researcher.py` — Araştırma agent'ı
4. `agents/critic.py` — Eleştiri agent'ı
5. `agents/synthesizer.py` — Sentez agent'ı

### Adım 3: Orkestratörü İnceleyin
`orchestration/orchestrator.py` dosyasında pipeline'ın nasıl çalıştığını inceleyin.

### Adım 4: Çalıştırın ve Deneyin
`orchestration/run.py`'yi çalıştırarak multi-agent pipeline'ını test edin.

### Adım 5: Exercises Yapın
[exercises/exercises.md](exercises/exercises.md) dosyasındaki görevleri tamamlayın.

### Adım 6: Testleri Çalıştırın
```bash
pytest tests/ -v
```

---

## 🎓 Capstone Projesi

Bu modül, eğitim serisinin en kapsamlı modülüdür.
Module 1-4'te öğrendiğiniz tüm kavramları (agent döngüsü, reflection, tool kullanımı, eval)
bir araya getirerek **gerçek dünya senaryosuna yakın** bir multi-agent sistemi kurarsınız.

**Capstone Görevi:** "Yapay zeka ve eğitim hakkında bir araştırma raporu hazırla"

Bu görev, tüm agent'ların sırayla çalışmasını gerektirir:
1. **Planner** → Konuyu alt başlıklara böler
2. **Researcher** → Her alt başlık için bilgi toplar
3. **Critic** → Toplanan bilgileri eleştirir ve eksikleri belirler
4. **Synthesizer** → Her şeyi birleştirip tutarlı bir rapor oluşturur

→ Çalıştırmak için: `python -m orchestration.run`

---

## ➡️ Sonraki Adımlar

Tebrikler! Multi-Agent sistemlerini artık anlıyorsunuz. 🎉

Önceki modülleri tekrar ziyaret ederek bilgilerinizi pekiştirebilirsiniz:

- [Module 1: Agent Fundamentals](../module-01-agent-fundamentals/README.md)
- [Module 2: Reflection](../module-02-reflection/README.md)
- [Module 3: Tools and MCP](../module-03-tools-and-mcp/README.md)
- [Module 4: Evals and Optimization](../module-04-evals-and-optimization/README.md)
