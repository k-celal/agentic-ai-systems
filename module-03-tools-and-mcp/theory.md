# 📖 Module 3: Teori — Tool Use & MCP Mühendisliği

## MCP Neden Önemli?

Module 1'de basit MCP gördük. Şimdi **production seviyesinde** MCP öğreneceğiz.

Gerçek dünyada karşılaşacağınız sorunlar:
- Tool çağrısı timeout olursa ne olur?
- Aynı tool farklı versiyonlarda çalışıyorsa?
- Tool hatalı parametre alırsa?
- 50 tane tool varsa LLM hangisini seçecek?

Bu modül bu sorunları çözer.

---

## Tool Registry Nedir?

Bir "telefon rehberi" gibi düşünün:

```
Tool Registry
├── search@v1     → Basit arama
├── search@v2     → Gelişmiş arama (filtre destekli)
├── file_write    → Dosya yazma
├── code_exec     → Kod çalıştırma (sandbox)
└── ...

Her tool'un:
- Adı
- Versiyonu
- Şeması (parametreler)
- Açıklaması
- Metadata'sı (timeout, idempotent mi?)
var.
```

---

## Middleware Pattern

Tool çağrısından önce/sonra çalışan ek işlemler:

```
Agent İsteği → [Logging] → [Timeout] → [Validation] → Tool → Sonuç
                                                          ↓
Agent ← [Logging] ← [Timeout] ← [Validation] ← ──────── Sonuç
```

### Neden Middleware?
1. **Logging:** Her çağrıyı kaydet (debug için)
2. **Timeout:** Uzun süren çağrıları iptal et
3. **Validation:** Parametreleri tool'a göndermeden kontrol et
4. **Retry:** Başarısız çağrıları tekrar dene

---

## Error Handling Stratejileri

### 1. Timeout
```python
# Tool 30 saniyeden uzun sürerse iptal et
result = await call_with_timeout(tool, args, timeout=30)
```

### 2. Retry with Backoff
```python
# 3 deneme, artan bekleme: 1s, 2s, 4s
result = await retry(tool, args, max_retries=3, backoff=2.0)
```

### 3. Idempotency (Etkisizlik)
```
İdempotent tool: Aynı çağrıyı 10 kez yapsan aynı sonuç
  ✅ get_weather("Istanbul") → her seferinde aynı
  
İdempotent DEĞİL: Her çağrı farklı etki
  ⚠️ send_email(to="x@y.com") → 10 kez çağırırsan 10 email gider!
```

---

## Tool Versioning

Aynı tool'un farklı versiyonları olabilir:

```
search@v1:
  - Basit metin araması
  - Parametreler: query

search@v2:
  - Gelişmiş arama
  - Parametreler: query, filters, max_results, sort_by
  - Geriye uyumlu (v1 parametreleri de çalışır)
```

---

## 🔗 İleri Okuma
- [docs/02-glossary.md](../docs/02-glossary.md) — MCP terimleri
- [Module 4: Evals](../module-04-evals-and-optimization/README.md) — Sonraki modül
