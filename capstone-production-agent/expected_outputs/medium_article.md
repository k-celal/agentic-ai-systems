# Agentic AI ve MCP: Yapay Zeka Ajanlarının Yeni Çağı

## Yapay zeka artık sadece soru-cevap yapmıyor — otonom kararlar alıyor, araçlar kullanıyor ve kendi çıktısını eleştiriyor.

---

Yapay zeka dünyasında sessiz bir devrim yaşanıyor. Geleneksel chatbot'lar sadece tek bir soruya tek bir cevap üretirken, yeni nesil **AI ajanları** çok adımlı görevleri bağımsız olarak yürütebiliyor. Bir makale mi yazılacak? Agent önce araştırma yapıyor, sonra taslak oluşturuyor, ardından kendi çıktısını eleştirip iyileştiriyor. Tüm bunları, insan müdahalesi olmadan.

Bu yazıda, agentic AI sistemlerinin nasıl çalıştığını, MCP (Model Context Protocol) protokolünün bu sistemlerdeki kritik rolünü ve tüm bunları bir araya getiren mimari kalıpları inceleyeceğiz.

---

## Agent Döngüsü: Düşün, Harekete Geç, Gözlemle

Bir AI ajanının çalışma prensibi şaşırtıcı derecede basittir. **ReAct** (Reasoning + Acting) kalıbı olarak bilinen bu döngü üç adımdan oluşur:

1. **Düşün (Think):** LLM, mevcut durumu değerlendirir ve bir plan oluşturur.
2. **Harekete Geç (Act):** Plan doğrultusunda bir araç çağırır — web araması, dosya okuma, API çağrısı gibi.
3. **Gözlemle (Observe):** Aracın sonucunu inceler ve bir sonraki adıma karar verir.

Bu döngü, görev tamamlanana kadar tekrarlanır. Ancak gerçek gücü, bu döngünün **araç kullanımı** ile birleşmesinden gelir. Bir LLM tek başına sadece metin üretir; araçlarla donatıldığında ise gerçek dünya ile etkileşime girer.

```
Kullanıcı: "Agentic AI hakkında bir makale yaz"
    ↓
Agent: [Düşün] Önce konuyu araştırmalıyım
Agent: [Harekete Geç] → deep_research.search("agentic AI")
Agent: [Gözlemle] 5 kaynak buldum, şimdi yazabilirim
Agent: [Düşün] Araştırma sonuçlarını yapılandırmalıyım
Agent: [Harekete Geç] → content.save("makale.md", icerik)
    ↓
Kullanıcı: Makale hazır!
```

---

## MCP: Ajanların Evrensel Aracı Dili

LLM'lerin araç kullanabilmesi için bir standarda ihtiyaç vardır. İşte **Model Context Protocol (MCP)** tam olarak bunu sağlar.

Anthropic tarafından geliştirilen MCP, LLM uygulamaları ile harici araçlar arasındaki iletişimi standartlaştıran açık bir protokoldür. Bunu şöyle düşünebilirsiniz: USB-C, tüm fiziksel cihazları tek bir standartta birleştirdi; MCP ise tüm dijital araçları tek bir protokolde birleştiriyor.

MCP'nin temel bileşenleri şunlardır:

- **MCP Sunucusu (Server):** Araçları barındırır ve çağrılmalarını bekler. Her araç, JSON Schema formatında tanımlanmış bir şemaya sahiptir.
- **MCP İstemcisi (Client):** LLM uygulaması tarafındadır. Araç çağrılarını JSON-RPC formatında sunucuya iletir.
- **Araç Tanımları:** Her aracın adı, açıklaması, parametreleri ve zorunlu alanları belirtilir. LLM bu şemayı okuyarak aracı doğru parametrelerle çağırır.

Bir MCP aracının nasıl tanımlandığına bakalım:

```json
{
  "name": "deep_research.search",
  "description": "Konu hakkında kaynak araştırması yapar",
  "parameters": {
    "query": {
      "type": "string",
      "description": "Arama sorgusu"
    },
    "max_results": {
      "type": "number",
      "description": "Maksimum sonuç sayısı"
    }
  },
  "required": ["query"]
}
```

Bu standartlaşma sayesinde, bir kez yazılan araç herhangi bir MCP uyumlu agent tarafından kullanılabilir. Araç geliştirici ile agent geliştirici birbirinden bağımsız çalışabilir.

---

## Reflection: Ajanın Kendi Eleştirmeni Olması

Tek seferde mükemmel bir çıktı üretmek neredeyse imkansızdır — insanlar için de, AI için de. **Reflection** kalıbı, bu gerçekliği kabullenip sistematik bir iyileştirme döngüsü kurar.

Süreç şöyle işler:

1. **Üretici (Generator):** Writing Agent bir makale taslağı üretir.
2. **Değerlendirici (Evaluator):** Reflection Agent bu taslağı beş boyutta puanlar — tutarlılık, derinlik, özgünlük, yapı ve kaynakça.
3. **Karar:** Puan belirlenen eşiğin üzerindeyse makale kabul edilir. Altındaysa, sorunlar ve öneriler Writing Agent'a geri bildirim olarak iletilir.
4. **İyileştirme:** Writing Agent, geri bildirimi dikkate alarak geliştirilmiş bir versiyon üretir.

Bu döngü genellikle 2-3 turda optimal sonuca ulaşır. İlk taslak %60-70 kalitedeyken, reflection sonrası %85-90 seviyesine çıkabilir. Ancak her ek tur ekstra maliyet getirir — bu yüzden **maliyet-kalite dengesi** kritik bir karardır.

---

## Çok Ajanlı Orkestrasyon: Uzmanların İş Birliği

Karmaşık görevlerde tek bir ajanın her şeyi yapması verimli değildir. Bunun yerine, her biri kendi uzmanlık alanına sahip birden fazla ajanın koordineli çalıştığı **çok ajanlı sistemler** kullanılır.

TwinGraph Studio'nun mimarisi buna güzel bir örnektir:

| Ajan | Rol | Model |
|------|-----|-------|
| **Orchestrator** | Pipeline koordinatörü | gpt-4o-mini |
| **Research** | Derin araştırma | gpt-4o-mini |
| **Writing** | İçerik üretimi | gpt-4o |
| **Reflection** | Kalite eleştirisi | gpt-4o-mini |
| **Repurpose** | Format dönüştürme | gpt-4o-mini |
| **Cost Guard** | Maliyet kontrolü | — |

Dikkat ederseniz, sadece **Writing Agent** pahalı model (gpt-4o) kullanıyor. Diğer tüm ajanlar ucuz model (gpt-4o-mini) ile çalışıyor. Bu **model yönlendirme (routing)** stratejisi, aynı kalitede %60-70 maliyet tasarrufu sağlayabiliyor.

Ajanlar arası iletişim iki yöntemle gerçekleşir:

- **Mesaj geçirme:** Orchestrator, her ajana yapılandırılmış mesajlar göndererek görev atar ve sonuçları toplar.
- **Paylaşılan hafıza:** GraphRAG (kavram grafı) ve VectorStore (vektör deposu) üzerinden ajanlar ortak bilgiye erişir.

---

## Maliyet Bekçisi: Her Kuruş Önemli

Production ortamında kontrolsüz LLM çağrıları bütçeyi hızla tüketebilir. Bir reflection döngüsü 3 kez tekrarlanırsa, her turda hem writing hem reflection agent'ı çağrılır — bu da 6 ek API çağrısı demektir.

**CostGuard Agent**, pipeline boyunca üç katmanlı koruma sağlar:

1. **Ön kontrol:** Her adımdan önce tahmini maliyeti hesaplar ve kalan bütçeyle karşılaştırır.
2. **Kayıt:** Her LLM çağrısı sonrası gerçek kullanımı kaydeder.
3. **Yönlendirme:** Bütçe sıkışırsa, otomatik olarak ucuz modele geçiş önerir.

Bu mekanizma, pipeline'ın "kontrolsüz harcama" yapmasını engeller ve her çalıştırmanın bütçe dahilinde kalmasını garanti eder.

---

## Geleceğe Bakış

Agentic AI henüz başlangıç aşamasında. Önümüzdeki dönemde şu gelişmeleri bekliyoruz:

- **Daha akıllı orkestrasyon:** Ajanlar, görev karmaşıklığına göre dinamik olarak oluşturulup yok edilecek.
- **Gerçek zamanlı öğrenme:** Ajanlar, her etkileşimden öğrenerek performanslarını sürekli iyileştirecek.
- **Standartlaşma:** MCP gibi protokoller yaygınlaşacak ve ajanlar arası birlikte çalışabilirlik artacak.
- **Maliyet düşüşü:** Daha verimli modeller ve akıllı yönlendirme ile agent pipeline'ları çok daha ucuz hale gelecek.

Yapay zeka ajanları, yazılım geliştirmenin geleceğini şekillendiriyor. Bugün bu teknolojiyi öğrenmek, yarının fırsatlarına hazır olmak demek.

---

## Kaynakça

1. **"Yapay Zeka Ajanları: Otonom Sistemlerin Yükselişi"** — TwinGraph Araştırma, 2025. https://arastirma.twingraph.dev/ai-agents-rehberi
2. **"Model Context Protocol (MCP): LLM Araç Standartı"** — TwinGraph Araştırma, 2025. https://arastirma.twingraph.dev/mcp-protokolu
3. **"Çok Ajanlı Sistemler: Orkestrasyon ve İş Birliği"** — TwinGraph Araştırma, 2025. https://arastirma.twingraph.dev/cok-ajanli-sistemler
4. **"Yansıma Kalıbı: Ajanların Öz-Değerlendirmesi"** — TwinGraph Araştırma, 2025. https://arastirma.twingraph.dev/yansima-kalibi
5. **"AI Ajan Değerlendirmesi: Metrikler ve Optimizasyon"** — TwinGraph Araştırma, 2025. https://arastirma.twingraph.dev/degerlendirme-rehberi

---

*Bu makale, TwinGraph Studio pipeline'ı tarafından üretilmiştir. Araştırma, yazım, reflection ve kaynak doğrulama süreçleri otomatik olarak yürütülmüştür.*

*Toplam maliyet: $0.050141 | Reflection döngüsü: 2 | Son kalite puanı: 7.8/10*
