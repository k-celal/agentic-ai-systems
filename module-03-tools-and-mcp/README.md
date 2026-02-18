# 🛠️ Module 3: Tool Use & MCP (Araç Kullanımı ve MCP Mühendisliği)

## 🎯 Bu Modülün Amacı

MCP'yi **production seviyesinde** öğreneceksiniz:
- Tool registry sistemi
- JSON schema doğrulama
- Hata yönetimi (timeout, retry)
- Tool versiyonlama
- Güvenli kod çalıştırma

---

## 📚 Kazanımlar

- [x] MCP client/server mimarisini derinlemesine anlayacaksınız
- [x] Tool registry sistemi yazabileceksiniz
- [x] JSON Schema ile parametre doğrulama yapabileceksiniz
- [x] Timeout, retry, idempotency pattern'lerini uygulayabileceksiniz
- [x] Tool versiyonlama yapabileceksiniz
- [x] Middleware sistemi (logging, timeout) kurabileceksiniz

---

## 📁 Dosya Yapısı

```
module-03-tools-and-mcp/
├── README.md
├── theory.md
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          ← Gelişmiş MCP Server
│   ├── registry.py        ← Tool Registry sistemi
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── logging_mw.py  ← Loglama middleware
│   │   └── timeout.py     ← Timeout middleware
│   └── tools/
│       ├── __init__.py
│       ├── search.py       ← Arama tool'u
│       ├── file_write.py   ← Dosya yazma tool'u
│       └── code_exec.py    ← Kod çalıştırma tool'u (sandbox)
├── agent/
│   ├── __init__.py
│   └── tool_router.py     ← Akıllı tool yönlendirici
├── exercises/
│   └── exercises.md
├── expected_outputs/
│   └── sample_output.txt
└── tests/
    └── test_mcp.py
```

---

## 🚀 Nasıl Çalıştırılır?

```bash
cd module-03-tools-and-mcp
python -m mcp_server.server    # MCP Server'ı test et
python -m agent.tool_router    # Tool Router'ı test et
```

---

## 🔑 Temel Kavram: MCP Derinlemesine

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP MİMARİSİ (Detaylı)                    │
│                                                               │
│  ┌───────────────┐         ┌─────────────────────────────┐  │
│  │  Agent         │         │   MCP Server                │  │
│  │  (MCP Client)  │         │                             │  │
│  │                │ JSON-RPC│  ┌───────────────────────┐  │  │
│  │  ┌──────────┐ │◄───────►│  │   Tool Registry       │  │  │
│  │  │Tool Router│ │         │  │  ┌─────┬─────┬─────┐ │  │  │
│  │  └──────────┘ │         │  │  │ T1  │ T2  │ T3  │ │  │  │
│  │                │         │  │  │v1.0 │v2.0 │v1.0 │ │  │  │
│  └───────────────┘         │  │  └─────┴─────┴─────┘ │  │  │
│                             │  └───────────────────────┘  │  │
│                             │                             │  │
│                             │  ┌───────────────────────┐  │  │
│                             │  │   Middleware Stack     │  │  │
│                             │  │  ┌─────────────────┐  │  │  │
│                             │  │  │ Logging          │  │  │  │
│                             │  │  ├─────────────────┤  │  │  │
│                             │  │  │ Timeout          │  │  │  │
│                             │  │  ├─────────────────┤  │  │  │
│                             │  │  │ Validation       │  │  │  │
│                             │  │  └─────────────────┘  │  │  │
│                             │  └───────────────────────┘  │  │
│                             └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## ➡️ Sonraki Modül
→ [Module 4: Evals & Optimization](../module-04-evals-and-optimization/README.md)
