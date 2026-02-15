# 🤖 Agentic AI Systems — Sıfırdan Üretim Seviyesine

> **Ajan Tabanlı Yapay Zeka Sistemlerini** adım adım, örneklerle ve gerçek kodlarla öğrenin.
> Hiçbir ön bilgi gerektirmez. Her modül bir öncekinin üzerine inşa eder.

---

## 📖 Bu Repo Nedir?

Bu repo, **AI Agent** (yapay zeka ajanı) geliştirmeyi **sıfırdan** öğreten bir kurs niteliğinde monorepo'dur.

**Ne öğreneceksiniz?**
- Bir AI Agent'ın nasıl düşündüğünü, karar verdiğini ve hareket ettiğini
- Agent'ların dış dünya ile nasıl iletişim kurduğunu (MCP & Tool Use)
- Kendini eleştiren ve geliştiren agent'lar yazmayı (Reflection)
- Agent sistemlerini test etme, optimize etme ve üretime taşımayı
- Birden fazla agent'ı bir orkestra gibi yönetmeyi (Multi-Agent)

---

## 🗺️ Öğrenme Yolu (Roadmap)

```
Module 1                Module 2             Module 3
Agent Temelleri    →    Reflection      →    Tool Use & MCP
(Düşün-Karar-Yap)      (Kendini Eleştir)    (Dış Dünya Bağlantısı)
       │                      │                     │
       └──────────────────────┴─────────────────────┘
                              │
                    Module 4: Evals & Optimization
                    (Test Et, Optimize Et)
                              │
                    Module 5: Multi-Agent
                    (Takım Çalışması)
                              │
                    🏁 Capstone: TwinGraph Studio
                    (Hepsini Birleştir)
```

---

## 🗂️ Repo Yapısı

```
agentic-ai-systems/
├── README.md                          ← 📍 Buradasınız
├── requirements.txt                   ← Tüm bağımlılıklar
├── .env.example                       ← API key ayarları
│
├── docs/                              ← 📚 Genel dökümanlar
│   ├── 00-roadmaps.md                  ← Öğrenme yol haritası
│   ├── 01-concepts-map.md             ← Kavram haritası
│   ├── 02-glossary.md                 ← Terimler sözlüğü
│   └── 03-evals-and-metrics.md        ← Değerlendirme rehberi
│
├── shared/                            ← 🔧 Ortak altyapı kodu
│   ├── llm/                           ← Model istemcileri
│   ├── schemas/                       ← Veri şemaları
│   ├── telemetry/                     ← Loglama ve izleme
│   └── utils/                         ← Yardımcı fonksiyonlar
│
├── module-01-agent-fundamentals/      ← 🧩 Agent Temelleri
├── module-02-reflection/              ← 🪞 Yansıtma (Reflection)
├── module-03-tools-and-mcp/           ← 🛠️ Araçlar ve MCP
├── module-04-evals-and-optimization/  ← 📊 Değerlendirme & Optimizasyon
├── module-05-multi-agent/             ← 🤖 Çoklu Agent Sistemleri
│
└── capstone-production-agent/         ← 🏁 TwinGraph Studio (Final Projesi)
```

---

## 🚀 Hızlı Başlangıç

### 1. Repoyu Klonlayın

```bash
git clone https://github.com/k-celal/agentic-ai-systems.git
cd agentic-ai-systems
```

### 2. Python Ortamını Kurun

```bash
# Python 3.10+ gereklidir
python -m venv venv

# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. API Key'lerinizi Ayarlayın

```bash
cp .env.example .env
# .env dosyasını açın ve kendi API key'lerinizi girin
```

### 5. İlk Modülü Çalıştırın

```bash
cd module-01-agent-fundamentals
python agent/run.py
```

---

## 📦 Her Modülde Ne Var?

Her modül şu standart yapıyı takip eder:

```
module-XX-isim/
├── README.md            → Amaç, kazanımlar, nasıl çalıştırılır
├── theory.md            → Kavramsal açıklamalar ve diyagramlar
├── agent/               → Agent kodu
├── mcp/                 → MCP server ve tool kodları
├── exercises/           → Pratik görevler (kendin yap!)
├── expected_outputs/    → Beklenen çıktı örnekleri
└── tests/               → Mini değerlendirmeler (eval)
```

---

## 🧠 Temel Kavram: Agent Nedir?

Bir **AI Agent**, sadece bir chatbot değildir. Şu döngüyü çalıştıran bir sistemdir:

```
┌─────────────────────────────────────┐
│           AGENT DÖNGÜSÜ             │
│                                     │
│   1. DÜŞÜN (Think)                  │
│      └→ Görevi analiz et            │
│                                     │
│   2. KARAR VER (Decide)             │
│      └→ Hangi aracı kullanmalıyım?  │
│                                     │
│   3. YÜRÜT (Act)                    │
│      └→ Aracı çağır, sonucu al     │
│                                     │
│   4. GÖZLEMLE (Observe)             │
│      └→ Sonucu değerlendir          │
│                                     │
│   5. TEKRARLA veya BİTİR            │
│      └→ Hedef tamamlandı mı?        │
└─────────────────────────────────────┘
```

**Chatbot**: "Bana bir şey sor, cevaplayayım"
**Agent**: "Bana bir görev ver, planlar yapayım, araçlar kullanayım, kendimi düzelteyim ve görevi tamamlayayım"

---

## 🔑 MCP (Model Context Protocol) Nedir?

MCP, agent'ların **dış dünya ile konuşma protokolü**dür.

```
┌──────────┐     MCP Protokolü     ┌──────────┐
│  AGENT   │ ◄──────────────────► │ MCP      │
│ (Client) │    JSON-RPC mesajlar  │ SERVER   │
│          │                       │ (Tools)  │
└──────────┘                       └──────────┘
                                       │
                                       ├── echo tool
                                       ├── time tool
                                       ├── search tool
                                       └── ...daha fazlası
```

**Neden önemli?**
- Agent, LLM'nin bilemeyeceği şeyleri yapabilir (dosya okuma, API çağırma, kod çalıştırma)
- Standart bir protokol — her tool aynı şekilde bağlanır
- Güvenli — tool'lar izole çalışır

---

## 💡 Kimler İçin?

| Profil | Bu Repo Sana Uygun mu? |
|--------|----------------------|
| Python biliyorum, AI ajanlarını merak ediyorum | ✅ Kesinlikle |
| Prompt engineering biliyorum, agent'a geçmek istiyorum | ✅ Tam sana göre |
| Hiç kod yazmadım | ⚠️ Temel Python bilgisi gerekli |
| Senior AI mühendisiyim | ✅ Module 3+ ve Capstone'a atlayabilirsin |
| LLM API kullanmayı biliyorum | ✅ Module 1'i hızlı geçip ilerleyebilirsin |

---

## 🛠️ Teknoloji Stack'i

| Teknoloji | Ne İçin Kullanıyoruz |
|-----------|---------------------|
| **Python 3.10+** | Ana programlama dili |
| **OpenAI API** | LLM çağrıları (GPT-4o, GPT-4o-mini) |
| **MCP SDK** | Model Context Protocol altyapısı |
| **Pydantic** | Veri doğrulama ve şemalar |
| **pytest** | Test framework'ü |
| **python-dotenv** | Ortam değişkenleri |

---

## 📋 Ön Koşullar

- **Python 3.10+** yüklü olmalı
- **OpenAI API key** (veya uyumlu bir LLM API)
- Temel Python bilgisi (değişkenler, fonksiyonlar, sınıflar)
- Terminal/komut satırı kullanabilme

---

## 🤝 Katkıda Bulunma

1. Bu repoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeni-ornek`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni örnek eklendi'`)
4. Push edin (`git push origin feature/yeni-ornek`)
5. Pull Request açın

---

## ⭐ Bu Repo İşinize Yaradıysa

Bir **yıldız** ⭐ bırakmayı unutmayın! Daha fazla kişinin bu kaynağa ulaşmasına yardımcı olur.

---

> **"En iyi öğrenme yolu yapmaktır."** — Her modülü sadece okumayın, kodları çalıştırın, exercises'leri yapın, kendi deneylerinizi ekleyin!
