# 📖 Module 1: Teori — Agent Temelleri

## Agent Nedir?

**Agent** (ajan), bir görevi **otonom olarak** yerine getirebilen yapay zeka sistemidir.

Düşünün ki bir asistanınız var:
- Ona "yarın için İstanbul uçak bileti bul" diyorsunuz
- Asistan:
  1. Hangi havayollarını aramalıyım diye **düşünür**
  2. Uçuş arama sitesine gidip **araç kullanır**
  3. Sonuçları **değerlendirir**
  4. En uygun seçeneği size **sunar**

İşte bir AI Agent de tam olarak bunu yapar — ama kodla!

---

## Neden Sadece Prompt Yetmez?

### Prompt ile yapabilecekleriniz:
```
Kullanıcı: "Python'da fibonacci fonksiyonu yaz"
LLM:       "def fibonacci(n): ..."  ← Tek seferde cevap
```

### Prompt ile YAPAMADIKLARINIZ:
```
Kullanıcı: "Dosyayı oku, hataları bul, düzelt ve test et"
LLM:       "???"  ← Dosyayı okuyamaz, test edemez!
```

**Agent farkı:**
- LLM tek başına dış dünya ile etkileşemez
- Agent, LLM'e "eller" (tool'lar) verir
- Agent, adım adım plan yapar ve uygular
- Agent, sonuçları değerlendirir ve gerekirse tekrar dener

---

## Agent Execution Loop (Çalışma Döngüsü)

Her agent'ın kalbi bir **döngüdür**. Bu döngüyü anlamak, agent geliştirmenin temelidir.

### 4 Aşamalı Döngü

```
┌─────────────────────────────────────────┐
│                                         │
│  ┌──────────┐    ┌──────────────┐      │
│  │  1.DÜŞÜN │───►│ 2.KARAR VER  │      │
│  │  (Think) │    │ (Decide)     │      │
│  └──────────┘    └──────┬───────┘      │
│       ▲                 │               │
│       │                 ▼               │
│  ┌──────────┐    ┌──────────────┐      │
│  │4.GÖZLEMLE│◄───│  3.YÜRÜT     │      │
│  │(Observe) │    │  (Act)       │      │
│  └──────────┘    └──────────────┘      │
│                                         │
│  Görev tamamlanana kadar TEKRARLA       │
└─────────────────────────────────────────┘
```

#### 1. DÜŞÜN (Think)
LLM, mevcut durumu analiz eder:
- "Görev ne?"
- "Elimde ne bilgi var?"
- "Ne yapmam lazım?"

#### 2. KARAR VER (Decide)
LLM, bir sonraki aksiyonu seçer:
- Tool çağır mı?
- Cevap ver mi?
- Daha fazla bilgi iste mi?

#### 3. YÜRÜT (Act)
Seçilen aksiyon gerçekleştirilir:
- MCP üzerinden tool çağrılır
- Sonuç alınır

#### 4. GÖZLEMLE (Observe)
Sonuç değerlendirilir:
- "Başarılı mı?"
- "Yeterli bilgi aldım mı?"
- "Devam mı, bitir mi?"

---

## Task Decomposition (Görev Parçalama)

Büyük görevleri küçük adımlara bölmek, agent'ların en kritik yeteneğidir.

### Örnek

**Görev:** "Türkiye'nin en büyük 3 şehrinin hava durumunu karşılaştır"

**Kötü yaklaşım (tek adım):**
```
Hemen hepsini bir kerede çöz → Muhtemelen hata yapar
```

**İyi yaklaşım (parçalanmış):**
```
Adım 1: İstanbul hava durumunu al
Adım 2: Ankara hava durumunu al
Adım 3: İzmir hava durumunu al
Adım 4: Üçünü karşılaştır ve özet yaz
```

---

## Degrees of Autonomy (Otonomi Seviyeleri)

Agent ne kadar bağımsız çalışmalı? Bu kritik bir tasarım kararıdır.

### 1. HITL (Human-in-the-Loop)
- Agent her adımda insan onayı ister
- En güvenli, en yavaş
- **Ne zaman:** Kritik işlemler (para transferi, e-posta gönderme)

```python
# HITL Örneği
action = agent.plan_next_step()
print(f"Yapılacak: {action}")
confirm = input("Onaylıyor musunuz? (e/h): ")
if confirm == "e":
    agent.execute(action)
```

### 2. HOTL (Human-on-the-Loop)
- Agent çalışır, insan izler
- Gerektiğinde insan müdahale eder
- **Ne zaman:** Araştırma, veri analizi

### 3. Fully Autonomous (Tam Otonom)
- Agent tamamen bağımsız
- İnsan müdahalesi yok
- **Ne zaman:** Log analizi, monitoring

---

## MCP Nedir ve Neden Baştan Kullanıyoruz?

**MCP (Model Context Protocol)**, agent'ların tool'larla konuşma standardıdır.

### Neden Module 1'de başlıyoruz?
1. Agent = LLM + Tool'lar → Tool olmadan agent olmaz
2. MCP, tool bağlantısının standart yoludur
3. Baştan doğru altyapı kurmak, sonra refactoring'den kurtarır

### MCP Nasıl Çalışır?

```
Agent (Client)          MCP Server
    │                       │
    │  "Hangi tool'lar var?" │
    │ ─────────────────────►│
    │                       │
    │  [echo, time, ...]    │
    │ ◄─────────────────────│
    │                       │
    │  "time tool'unu çağır"│
    │ ─────────────────────►│
    │                       │
    │  "14:30:00"           │
    │ ◄─────────────────────│
```

### Bu Modüldeki Tool'lar

| Tool | Ne Yapar | Neden Var |
|------|----------|-----------|
| `echo` | Gelen mesajı geri döndürür | Tool çağrısını test etmek |
| `get_time` | Şu anki saati döndürür | Gerçek veri döndüren ilk tool |

---

## Basit Eval: Başarı mı, Başarısızlık mı?

Bu modülde karmaşık değerlendirme yapmıyoruz. Sadece:

```python
# En basit eval
def evaluate(task, result):
    """Görev başarılı mı?"""
    if result.status == "completed":
        return "✅ BAŞARILI"
    elif result.status == "max_loops_exceeded":
        return "❌ BAŞARISIZ: Sonsuz döngüye girdi"
    elif result.status == "error":
        return "❌ BAŞARISIZ: Hata oluştu"
    else:
        return "⚠️ BELİRSİZ"
```

Module 4'te çok daha gelişmiş eval yapacağız!

---

## 🔗 İleri Okuma

- [docs/01-concepts-map.md](../docs/01-concepts-map.md) — Tüm kavram haritası
- [docs/02-glossary.md](../docs/02-glossary.md) — Terimler sözlüğü
- [Module 2: Reflection](../module-02-reflection/README.md) — Sonraki modül
