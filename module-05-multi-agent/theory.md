# 📖 Module 5: Teori — Multi-Agent Sistemleri

## Multi-Agent Sistemi Nedir?

**Multi-Agent sistemi**, birden fazla yapay zeka agent'ının **koordineli olarak**
birlikte çalıştığı bir mimaridir.

Gerçek hayattan bir benzetme:

Bir hastanede tek bir doktor tüm işleri yapmaz:
- **Pratisyen hekim** ilk değerlendirmeyi yapar (→ Planner)
- **Uzman doktor** detaylı tetkik yapar (→ Researcher)
- **Radyolog** sonuçları inceler ve rapor yazar (→ Critic)
- **Başhekim** tüm raporları değerlendirip tedavi planı oluşturur (→ Synthesizer)

Her uzman **kendi alanında** en iyidir ve birlikte çalışarak
tek bir doktorun yapabileceğinden çok daha iyi sonuç üretirler.

---

## Neden Tek Agent Yetmez?

### Tek Agent'ın Sınırları

```
Görev: "AI ve eğitim hakkında kapsamlı bir rapor yaz"

Tek Agent Yaklaşımı:
┌─────────────────────────────┐
│      TEK AGENT              │
│                             │
│ 1. Konuyu anla              │
│ 2. Araştırma yap            │    ← Çok fazla sorumluluk!
│ 3. Bilgileri topla          │    ← Context window doluyor
│ 4. Kaliteyi kontrol et      │    ← Kendi hatasını göremez
│ 5. Rapor yaz                │    ← Sonuç genelde yetersiz
│                             │
└─────────────────────────────┘
```

### Sorunlar:
1. **Context window sınırı:** Tek agent çok fazla bilgiyi aynı anda tutamaz
2. **Uzmanlık eksikliği:** Genel bir prompt ile özelleşmiş iş yapmak zordur
3. **Kendini eleştirememe:** Aynı LLM kendi hatasını bulmakta zorlanır
4. **Karmaşıklık artışı:** Tek bir system prompt'a her şeyi sığdırmak mümkün değil

### Multi-Agent Çözümü

```
Görev: "AI ve eğitim hakkında kapsamlı bir rapor yaz"

Multi-Agent Yaklaşımı:
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│ PLANNER  │─►│  RESEARCHER  │─►│  CRITIC  │─►│ SYNTHESIZER  │
│          │  │              │  │          │  │              │
│ "3 alt   │  │ Her başlık   │  │ "Kaynak  │  │ "İşte tutarlı│
│  başlık  │  │ için bilgi   │  │  eksik,  │  │  ve kapsamlı │
│  olsun"  │  │ topladım"    │  │  veri    │  │  rapor"      │
│          │  │              │  │  yetersiz"│  │              │
└──────────┘  └──────────────┘  └──────────┘  └──────────────┘
```

---

## Multi-Agent Patternleri

### 1. Orkestratör Pattern (Orchestrator)

En yaygın pattern. Bir merkezi **orkestratör**, tüm agent'ları yönetir.

```
                    ┌──────────────┐
                    │ ORKESTRATÖR  │
                    │              │
                    │ Agent'ları   │
                    │ sırayla      │
                    │ çağırır      │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Agent A  │ │ Agent B  │ │ Agent C  │
        └──────────┘ └──────────┘ └──────────┘
```

**Avantajları:**
- Merkezi kontrol → Akışı takip etmek kolay
- Hata yönetimi tek yerden yapılır
- Agent sıralaması dinamik olarak değiştirilebilir

**Dezavantajları:**
- Orkestratör tek hata noktası (single point of failure)
- Çok agent varsa orkestratör karmaşıklaşabilir

**Bu modülde bu pattern'i kullanıyoruz!**

---

### 2. Blackboard Pattern (Kara Tahta)

Tüm agent'lar ortak bir **kara tahtaya** (shared memory) yazar ve okur.
Sıralı çağrı yerine, her agent tahtayı izler ve ihtiyaç olduğunda devreye girer.

```
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Agent A  │ │ Agent B  │ │ Agent C  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ═══════════════════════════════════════
        ║         KARA TAHTA (Blackboard)     ║
        ║                                     ║
        ║  plan: "3 adımlı araştırma"        ║
        ║  research: "bulduğum veriler..."    ║
        ║  critique: "şu eksikler var..."    ║
        ║  final: "birleştirilmiş rapor"     ║
        ═══════════════════════════════════════
```

**Avantajları:**
- Agent'lar bağımsız çalışabilir
- Yeni agent eklemek çok kolay
- Ortak veri deposu sayesinde bilgi kaybı olmaz

**Dezavantajları:**
- Senkronizasyon problemi (kim ne zaman yazar?)
- Çakışma riski (iki agent aynı veriyi değiştirirse?)

**Bu modülde SharedMemory aracı bu pattern'in basit bir örneğidir.**

---

### 3. Mesaj Geçişi Pattern (Message Passing)

Agent'lar birbirlerine doğrudan **mesaj** gönderir.
Her mesajın bir göndericisi, alıcısı ve içeriği vardır.

```
┌──────────┐  mesaj   ┌──────────┐  mesaj   ┌──────────┐
│ Agent A  │─────────►│ Agent B  │─────────►│ Agent C  │
│          │          │          │          │          │
│          │◄─────────│          │◄─────────│          │
└──────────┘  cevap   └──────────┘  cevap   └──────────┘
```

**Avantajları:**
- Agent'lar arası iletişim doğrudan ve hızlı
- Her agent kendi mesaj kuyruğunu yönetir
- Dağıtık sistemlere uygun

**Dezavantajları:**
- Mesaj formatını standartlaştırmak gerekir
- Çok agent varsa mesaj trafiği karmaşıklaşır

**Bu modülde AgentMessage dataclass'ı bu pattern'i temsil eder.**

---

## Agent Rolleri Detaylı

### 📋 Planner (Planlayıcı)

**Görevi:** Büyük görevi küçük, yönetilebilir adımlara bölmek.

**Neden önemli?**
- Karmaşık görevler doğrudan çözülemez
- Adımlara bölmek hata oranını azaltır
- Diğer agent'ların neyi yapacağını belirler

**Gerçek hayat karşılığı:** Proje yöneticisi

```python
# Planner'ın yaptığı iş
görev = "AI ve eğitim hakkında rapor yaz"
plan = [
    "1. Yapay zekanın eğitimdeki mevcut kullanımlarını araştır",
    "2. Kişiselleştirilmiş öğrenme sistemlerini incele",
    "3. Gelecek trendleri ve zorlukları belirle",
]
```

---

### 🔍 Researcher (Araştırmacı)

**Görevi:** Planner'ın belirlediği adımlar için bilgi toplamak.

**Neden önemli?**
- Bilgi toplamak uzmanlık gerektirir
- Doğru kaynakları bulmak kritik
- Tool'ları etkin kullanmak gerekir

**Gerçek hayat karşılığı:** Araştırma asistanı

```python
# Researcher'ın yaptığı iş
adım = "Yapay zekanın eğitimdeki mevcut kullanımları"
bulgular = {
    "adaptif_ogrenme": "AI ile kişiselleştirilmiş müfredat...",
    "otomatik_degerlendirme": "Ödev ve sınav otomasyonu...",
    "chatbot_asistanlar": "7/24 öğrenci desteği...",
}
```

---

### 🔎 Critic (Eleştirmen)

**Görevi:** Diğer agent'ların çıktılarını incelemek ve eleştirmek.

**Neden önemli?**
- Kendi hatasını bulmak zordur (başka bir göz gerekir)
- Kalite kontrolü ayrı bir süreç olmalı
- Eksikleri ve hataları erken aşamada bulmak maliyeti düşürür

**Gerçek hayat karşılığı:** Editör / Kalite kontrol uzmanı

```python
# Critic'in yaptığı iş
bulgular = researcher_çıktısı
eleştiri = {
    "güçlü_yönler": ["Konu çeşitliliği iyi"],
    "zayıf_yönler": ["Kaynak belirtilmemiş", "Veri yetersiz"],
    "öneriler": ["İstatistiksel veri ekle", "Örnek vaka çalışması ekle"],
}
```

---

### 📝 Synthesizer (Sentezci)

**Görevi:** Tüm bulguları ve eleştirileri birleştirip tutarlı bir çıktı üretmek.

**Neden önemli?**
- Parçalar ayrı ayrı iyi olsa da, birleştirilmesi uzmanlık gerektirir
- Tutarlılık ve akış kontrolü gerekir
- Son çıktının kalitesini belirler

**Gerçek hayat karşılığı:** Baş editör / Rapor yazarı

```python
# Synthesizer'ın yaptığı iş
plan = planner_çıktısı
bulgular = researcher_çıktısı
eleştiri = critic_çıktısı

son_rapor = """
# AI ve Eğitim Raporu
## 1. Giriş
...
## 2. Mevcut Uygulamalar
...
## 3. Sonuç ve Öneriler
...
"""
```

---

## Shared Memory (Ortak Bellek)

Agent'lar arasında veri paylaşımı kritik bir konudur.
Bu modülde **key-value tabanlı** basit bir ortak bellek kullanıyoruz.

### Nasıl Çalışır?

```
Agent A:  store("plan", "3 adımlı plan...")
              │
              ▼
    ┌─────────────────────┐
    │   SHARED MEMORY     │
    │                     │
    │  plan ──► "3 adım"  │
    │  data ──► "..."     │
    └─────────────────────┘
              │
              ▼
Agent B:  retrieve("plan") → "3 adımlı plan..."
```

### Avantajları
1. **Gevşek bağlantı (loose coupling):** Agent'lar birbirlerini doğrudan bilmek zorunda değil
2. **Veri kalıcılığı:** Pipeline boyunca bilgi kaybolmaz
3. **Denetlenebilirlik:** Shared memory'nin içeriği her zaman incelenebilir

---

## Pipeline vs Dinamik Yönlendirme

### Pipeline (Sıralı Akış) — Bu Modülde

```
Planner → Researcher → Critic → Synthesizer
```

Her agent sırayla çalışır. Basit ve öngörülebilir.

### Dinamik Yönlendirme (İleri Düzey)

```
                    Planner
                       │
                ┌──────┼──────┐
                ▼      ▼      ▼
           Researcher  ...   ...
                │
                ▼
             Critic
                │
         ┌──────┴──────┐
         │             │
    "Yeterli"     "Yetersiz"
         │             │
         ▼             ▼
    Synthesizer   Researcher'a
                  geri gönder
```

Orkestratör, Critic'in cevabına göre pipeline'ı **dinamik olarak** yönlendirir.
Bu ileri düzey bir konudur ve alıştırmalarda keşfedeceksiniz.

---

## Hata Yönetimi

Multi-Agent sistemlerde hata yönetimi kritiktir.
Bir agent başarısız olursa tüm pipeline çökebilir.

### Stratejiler

1. **Timeout:** Her agent'a maksimum çalışma süresi ver
2. **Fallback:** Agent başarısız olursa varsayılan cevap kullan
3. **Retry:** Geçici hatalarda otomatik tekrar dene
4. **İzolasyon:** Bir agent'ın hatası diğerlerini etkilemesin

```python
# Hata yönetimi örneği
try:
    sonuç = await agent.process(mesaj)
except TimeoutError:
    sonuç = "Agent zaman aşımına uğradı"
except Exception as e:
    sonuç = f"Agent hatası: {e}"
    # Varsayılan cevap kullan veya pipeline'ı durdur
```

---

## 🔗 İleri Okuma

- [docs/01-concepts-map.md](../docs/01-concepts-map.md) — Tüm kavram haritası
- [docs/02-glossary.md](../docs/02-glossary.md) — Terimler sözlüğü
- [Module 1: Agent Fundamentals](../module-01-agent-fundamentals/README.md) — Agent temelleri
- [Module 2: Reflection](../module-02-reflection/README.md) — Reflection
- [Module 3: Tools and MCP](../module-03-tools-and-mcp/README.md) — Tool'lar ve MCP
- [Module 4: Evals and Optimization](../module-04-evals-and-optimization/README.md) — Değerlendirme ve Optimizasyon
