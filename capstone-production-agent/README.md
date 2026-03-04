# 🧠 Capstone: TwinGraph Studio

## Production-Ready Agentic Content & Research Orchestrator

> Araştıran, yazan, eleştiren, dönüştüren ve maliyeti optimize eden **çoklu agent sistemi**.
> Tüm modüllerde öğrendiklerinizin **gerçek dünya birleşimi**.

---

## 🎯 Projenin Amacı

Kullanıcıdan gelen **tek bir komutla**:

```
"Agentic AI ve MCP üzerine derin bir Medium yazısı üret ve LinkedIn postuna dönüştür."
```

Sistem şunları yapar:

1. **Deep Research** yapar — kaynak toplar, özetler
2. **GraphRAG hafızasını** kullanır — önceki bilgiyi hatırlar
3. **Medium makalesi** üretir — yapılandırılmış, kaynakçalı
4. **Reflection** ile kalite kontrol yapar — eleştirir, geliştirir
5. **LinkedIn postuna** dönüştürür — hook, değer, CTA
6. **Maliyet & kalite** eval'ini raporlar

Ve tüm bunları: **MCP üzerinden**, **Multi-agent mimariyle**, **Eval & cost guard ile** yapar.

---

## 🏗️ Mimari

```
                    Kullanıcı
                       │
                       ▼
              ┌─────────────────┐
              │  ORCHESTRATOR   │ ← Ana koordinatör
              │     Agent       │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │ RESEARCH  │  │ WRITING   │  │ REFLECTION│
  │  Agent    │  │  Agent    │  │  Agent    │
  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
        │              │              │
        ▼              ▼              ▼
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │ REPURPOSE │  │COST GUARD │  │   EVAL    │
  │  Agent    │  │  Agent    │  │  System   │
  └─────┬─────┘  └─────┬─────┘  └───────────┘
        │              │
        ▼              ▼
  ┌─────────────────────────────────────────┐
  │              MCP SERVER                  │
  │  ┌────────────────────────────────────┐ │
  │  │         Tool Registry              │ │
  │  │  ┌──────┬──────┬──────┬─────────┐ │ │
  │  │  │search│save  │eval  │citation │ │ │
  │  │  │@v1   │      │      │verify   │ │ │
  │  │  └──────┴──────┴──────┴─────────┘ │ │
  │  └────────────────────────────────────┘ │
  │                                         │
  │  ┌────────────────────────────────────┐ │
  │  │         Memory System              │ │
  │  │  ┌──────────┐  ┌───────────────┐  │ │
  │  │  │  Graph   │  │    Vector     │  │ │
  │  │  │  Store   │  │    Store      │  │ │
  │  │  └──────────┘  └───────────────┘  │ │
  │  └────────────────────────────────────┘ │
  └─────────────────────────────────────────┘
```

---

## 🧩 Agent Rolleri

| Agent | Rol | Ne Yapar? | Model |
|-------|-----|-----------|-------|
| **Orchestrator** | Koordinatör | Tüm pipeline'ı yönetir, agent'lara görev atar | gpt-4o-mini |
| **Research** | Araştırmacı | Deep research yapar, kaynakları özetler, citation çıkarır | gpt-4o-mini |
| **Writing** | Yazar | GraphRAG + research ile Medium makalesi üretir | gpt-4o |
| **Reflection** | Eleştirmen | Tutarsızlık, tekrar, yüzeysellik tespit eder | gpt-4o-mini |
| **Repurpose** | Dönüştürücü | Long-form → LinkedIn post, hook + CTA üretir | gpt-4o-mini |
| **Cost Guard** | Maliyet Bekçisi | Token kullanımı kontrol, model routing, bütçe koruması | — |

---

## 🛠️ MCP Tool Set

| Tool | Açıklama | İdempotent? |
|------|----------|-------------|
| `deep_research.search` | Konu hakkında kaynak araştırması yapar | ✅ |
| `memory.graph_query` | GraphRAG'dan ilişkili kavramları çeker | ✅ |
| `memory.vector_search` | Vektör benzerliği ile içerik arar | ✅ |
| `content.save` | Üretilen içeriği kaydeder | ❌ |
| `eval.writing_score` | Yazı kalitesini puanlar | ✅ |
| `citation.verify` | Kaynakça doğrulaması yapar | ✅ |
| `cost.report` | Maliyet raporu üretir | ✅ |

---

## 📁 Dosya Yapısı

```
capstone-production-agent/
├── README.md                    ← 📍 Buradasınız
├── theory.md                    ← Production agent kavramları
├── run.py                       ← Ana çalıştırma dosyası
│
├── agents/                      ← 🤖 Agent'lar
│   ├── orchestrator.py          ← Pipeline koordinatörü
│   ├── research_agent.py        ← Deep research
│   ├── writing_agent.py         ← İçerik üretici
│   ├── reflection_agent.py      ← Kalite eleştirmeni
│   ├── repurpose_agent.py       ← Format dönüştürücü
│   └── cost_guard_agent.py      ← Maliyet bekçisi
│
├── mcp/                         ← 🛠️ MCP Altyapısı
│   ├── server.py                ← MCP sunucusu
│   ├── registry.py              ← Tool kayıt sistemi
│   ├── middleware/               ← Ara katmanlar
│   │   ├── logging_mw.py
│   │   └── retry.py
│   └── tools/                   ← Tool'lar
│       ├── deep_research.py
│       ├── content_save.py
│       ├── eval_tool.py
│       ├── cost_report.py
│       └── citation_verify.py
│
├── memory/                      ← 🧠 Hafıza Sistemi
│   ├── graph_store.py           ← Kavram grafı (GraphRAG)
│   ├── vector_store.py          ← Vektör benzerliği
│   └── ingestion.py             ← İçerik yükleme
│
├── evals/                       ← 📊 Değerlendirme
│   ├── writing_eval.py          ← Yazı kalitesi eval
│   └── cost_eval.py             ← Maliyet eval
│
├── routing/                     ← 🔀 Model Yönlendirme
│   └── model_router.py
│
├── exercises/
│   └── exercises.md
├── expected_outputs/
│   ├── sample_output.txt
│   ├── medium_article.md
│   └── linkedin_post.txt
└── tests/
    └── test_twingraph.py
```

---

## 🚀 Nasıl Çalıştırılır?

```bash
cd capstone-production-agent

# Temel demo
python run.py

# Özel konu ile
python run.py --topic "Agentic AI ve MCP"
```

### Beklenen Çıktı

```
[Orchestrator]  Pipeline başlatılıyor...
[Research]      Deep research çalışıyor... 5 kaynak bulundu
[Writing]       Taslak v1 oluşturuldu (1,250 kelime)
[Reflection]    Kalite puanı: 6/10 → İyileştirme gerekli
[Writing]       Taslak v2 oluşturuldu (1,480 kelime)
[Reflection]    Kalite puanı: 8/10 → Kabul edildi ✅
[Repurpose]     LinkedIn postu oluşturuldu (280 kelime)
[Cost Guard]    Toplam: 8,420 token | $0.0089 | Bütçe: %18 kullanıldı

📄 Çıktılar:
  → medium_article.md
  → linkedin_post.txt
  → run_report.json
```

---

## 📊 Production Kriterleri

Bu capstone **"çalıştı"** demek yetmez. Şu metrikleri takip eder:

| Metrik | Açıklama | Hedef |
|--------|----------|-------|
| Writing Coherence | Yazı tutarlılık skoru | ≥ 7/10 |
| Citation Coverage | Kaynakça kapsama oranı | ≥ %80 |
| Token Efficiency | Token başına üretilen kelime | ≥ 0.3 |
| Reflection Delta | Reflection sonrası iyileşme | ≥ +15% |
| Tool Success Rate | Tool çağrı başarısı | ≥ %95 |
| Pipeline Latency | Toplam çalışma süresi | < 60s |

---

## 🎓 Bu Capstone Neyi Kanıtlar?

Bu projeyi tamamladığınızda:

| Yetkinlik | Modül | Capstone'da |
|-----------|-------|-------------|
| Agent execution loop | Module 1 | ✅ Orchestrator döngüsü |
| MCP tool calling | Module 1, 3 | ✅ 7 tool, registry, middleware |
| Reflection pattern | Module 2 | ✅ Writing → Critique → Improve |
| Tool versioning | Module 3 | ✅ search@v1 registry |
| Error handling | Module 3 | ✅ Retry, timeout middleware |
| E2E eval | Module 4 | ✅ Writing eval, cost eval |
| Model routing | Module 4 | ✅ Ucuz → pahalı model geçişi |
| Multi-agent | Module 5 | ✅ 5 agent, mesajlaşma, orkestrasyon |
| Shared memory | Module 5 | ✅ GraphRAG, vector store |
| Production mindset | — | ✅ Structured logs, cost guard |

---

## 🔗 Bağlantılar

- [← Module 5: Multi-Agent](../module-05-multi-agent/README.md)
- [← Ana README](../README.md)
- [← Roadmap](../docs/00-roadmaps.md)

---

> **"Bu proje CV'ye yazılır."** — Sadece bir öğrenme egzersizi değil, gerçek bir production-grade sisteminiz olacak.
