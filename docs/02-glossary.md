# 📖 Terimler Sözlüğü (Glossary)

Agentic AI dünyasında karşılaşacağınız tüm terimler, **alfabetik sırada** ve Türkçe açıklamalarıyla.

---

## A

### Agent (Ajan)
Bir görevi **otonom olarak** yerine getirebilen yapay zeka sistemi. Sadece soru-cevap yapmaz; düşünür, plan yapar, araç kullanır ve kendini düzeltir.

```
Chatbot: "Bana sor, cevaplayayım"
Agent:   "Bana görev ver, planlar yapayım, araçlar kullanayım, tamamlayayım"
```

### Agent Execution Loop (Agent Çalışma Döngüsü)
Agent'ın tekrarladığı temel döngü: **Think → Decide → Act → Observe**. Bu döngü, görev tamamlanana kadar devam eder.

### Autonomy (Otonomi)
Agent'ın insan müdahalesi olmadan ne kadar bağımsız çalışabildiği. Bkz: **HITL**, **HOTL**.

---

## B

### Blackboard Pattern (Kara Tahta Deseni)
Birden fazla agent'ın ortak bir "kara tahta"ya yazıp okuduğu iletişim deseni. Her agent tahtadan bilgi alır, işler ve sonucu tahtaya yazar.

---

## C

### Chain of Thought (Düşünce Zinciri)
LLM'in bir soruyu adım adım düşünerek çözmesi. "Hemen cevap ver" yerine "Adım adım düşün" demek genellikle daha iyi sonuç verir.

### Component Eval (Bileşen Değerlendirmesi)
Agent'ın tek bir parçasını (planner, tool seçimi vb.) ayrı ayrı test etme.

### Context Window (Bağlam Penceresi)
LLM'in aynı anda görebildiği maksimum metin miktarı. Token cinsinden ölçülür (örn: 128K token).

### Context Compression (Bağlam Sıkıştırma)
Context window'u verimli kullanmak için gereksiz mesajları kaldırma veya özetleme.

### Cost Guard (Maliyet Koruması)
Agent'ın harcadığı token/para miktarını izleyen ve limiti aşınca durduran mekanizma.

---

## E

### E2E Eval (Uçtan Uca Değerlendirme)
Agent'ın görevi baştan sona başarıyla tamamlayıp tamamlamadığını test etme. "Sonuç doğru mu?" sorusunun cevabı.

### Eval (Değerlendirme)
Agent sisteminin performansını ölçme. Başarı oranı, maliyet, hız gibi metrikler kullanılır.

### Execution Loop
Bkz: **Agent Execution Loop**

---

## F

### Fallback (Yedek Plan)
Bir tool veya işlem başarısız olduğunda devreye giren alternatif yol.

### Few-Shot Prompting
LLM'e birkaç örnek vererek istenen formatı/davranışı gösterme tekniği.

---

## G

### Grounding (Temellendirme)
LLM çıktısını gerçek verilerle destekleme. Agent'ın "uydurma" (hallucination) yerine gerçek bilgiye dayalı cevap vermesi.

---

## H

### Hallucination (Halüsinasyon)
LLM'in gerçekte var olmayan bilgiyi uydurması. Agent'lar, tool kullanarak bu sorunu azaltır.

### HITL (Human-in-the-Loop)
Her önemli adımda insan onayı gerektiren çalışma modu. En güvenli ama en yavaş mod.

### HOTL (Human-on-the-Loop)
Agent bağımsız çalışır, insan izler ve gerektiğinde müdahale eder. Güvenlik ve hız arasında denge.

---

## I

### Idempotency (Etkisizlik)
Aynı tool çağrısını birden fazla kez yapmanın aynı sonucu vermesi. Retry mekanizmaları için kritik.

```python
# İdempotent: Aynı sonuç
get_weather("Istanbul")  # → 15°C
get_weather("Istanbul")  # → 15°C (aynı)

# İdempotent DEĞİL: Her seferinde farklı
create_user("Ahmet")  # → User #1
create_user("Ahmet")  # → User #2 (dikkat!)
```

---

## J

### JSON-RPC
MCP protokolünün kullandığı mesajlaşma formatı. Agent ve MCP server arasındaki iletişim bu formatta yapılır.

### JSON Schema
Tool parametrelerini tanımlayan standart format. Agent, hangi parametrelerin gerekli olduğunu bu şemadan öğrenir.

---

## L

### LLM (Large Language Model)
GPT-4, Claude, Gemini gibi büyük dil modelleri. Agent'ın "beyni" rolünü üstlenir.

---

## M

### MCP (Model Context Protocol)
Agent'ların dış araçlarla iletişim kurmasını sağlayan standart protokol. Client-server mimarisi kullanır.

### MCP Client (MCP İstemcisi)
Agent tarafındaki bileşen. Tool çağrılarını MCP server'a gönderir.

### MCP Server (MCP Sunucusu)
Tool'ları barındıran ve çalıştıran sunucu. Agent'tan gelen istekleri alır, tool'u çalıştırır, sonucu döndürür.

### Middleware (Ara Katman)
Tool çağrıları öncesinde/sonrasında çalışan ek işlemler. Loglama, timeout, doğrulama gibi.

### Model Routing (Model Yönlendirme)
Görevin zorluğuna göre farklı LLM modelleri kullanma stratejisi. Basit görev → ucuz model, zor görev → pahalı model.

### Multi-Agent (Çoklu Agent)
Birden fazla agent'ın birlikte çalışarak bir görevi yerine getirmesi.

---

## O

### Observation (Gözlem)
Agent'ın bir tool çağrısından dönen sonucu değerlendirmesi.

### Orchestration (Orkestrasyon)
Birden fazla agent'ı koordine etme ve yönetme süreci.

---

## P

### Planner (Planlayıcı)
Görevi alt görevlere bölen ve sıralayan agent bileşeni.

### Prompt Engineering
LLM'den istenen çıktıyı almak için girdileri (prompt) optimize etme sanatı.

---

## R

### Reflection (Yansıtma)
Agent'ın kendi çıktısını eleştirip geliştirmesi. Generate → Critique → Improve döngüsü.

### Retry (Tekrar Deneme)
Başarısız bir işlemi belirli bir stratejiyle (exponential backoff vb.) tekrar deneme.

---

## S

### Sandbox (Kum Havuzu)
Kodun güvenli bir ortamda, sistem kaynaklarına erişimi kısıtlı şekilde çalıştırılması.

### Schema (Şema)
Verinin yapısını tanımlayan format. Tool parametreleri, mesaj formatları vb. için kullanılır.

### Shared Memory (Paylaşılan Hafıza)
Birden fazla agent'ın okuyup yazabildiği ortak veri deposu.

---

## T

### Task Decomposition (Görev Parçalama)
Büyük bir görevi küçük, yönetilebilir alt görevlere bölme.

### Telemetry (Telemetri)
Agent'ın çalışma sürecini izleme: loglar, izleme (tracing), maliyet takibi.

### Token
LLM'lerin metni işlediği birim. Yaklaşık 1 token ≈ 4 karakter (İngilizce'de). Türkçe'de daha az karakter/token olabilir.

### Tool (Araç)
Agent'ın kullanabildiği dış fonksiyon. Hava durumu sorgulama, dosya okuma, kod çalıştırma gibi.

### Tool Calling (Araç Çağırma)
LLM'in bir tool'u kullanma kararı vermesi ve doğru parametrelerle çağırması.

### Tool Registry (Araç Kaydı)
Mevcut tool'ların listesini ve şemalarını tutan merkezi kayıt sistemi.

### Tracing (İzleme)
Agent'ın her adımını (LLM çağrısı, tool çağrısı, kararlar) detaylı şekilde kaydetme.

---

## V

### Validation (Doğrulama)
Girdi veya çıktının belirli kurallara uygun olduğunu kontrol etme.

### Versioning (Sürümleme)
Tool'ların farklı versiyonlarını yönetme (search@v1, search@v2).

---

> 💡 **Yeni bir terimle karşılaştığınızda** bu sözlüğe dönüp bakın. Her modülde yeni terimler eklenir.
