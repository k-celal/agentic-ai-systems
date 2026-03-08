# 📝 Capstone: TwinGraph Studio — Alıştırmalar

> Bu alıştırmalar, TwinGraph Studio'nun tüm bileşenlerini keşfetmenizi ve genişletmenizi sağlar.
> Kolaydan zora doğru ilerleyin. Her alıştırmada hangi modül bilgisinin gerektiği belirtilmiştir.

---

## Alıştırma 1: Yeni Konu ile Pipeline Çalıştır (⭐ Kolay)

### Görev

TwinGraph Studio pipeline'ını **farklı bir konu** ile çalıştırın ve varsayılan konu olan "Agentic AI ve MCP" ile sonuçlarını karşılaştırın.

### Adımlar

1. `run.py` dosyasını açın ve pipeline'ın nasıl başlatıldığını inceleyin
2. Yeni bir konu seçin (örneğin: "RAG Sistemleri ve Vektör Veritabanları")
3. Pipeline'ı bu yeni konu ile çalıştırın:
   ```bash
   python run.py --topic "RAG Sistemleri ve Vektör Veritabanları"
   ```
4. Çıktıları karşılaştırın:
   - Araştırma sonuçlarının sayısı ve kalitesi
   - Makale uzunluğu ve yapısı
   - Reflection puanları
   - LinkedIn postu kalitesi
   - Toplam maliyet

### İpuçları

- `mcp/tools/deep_research.py` içindeki `KNOWLEDGE_BASE` sözlüğüne bakarak hangi konularda zengin bilgi olduğunu anlayabilirsiniz
- GraphStore'daki kavramlar ile uyumlu konular daha iyi sonuçlar verir
- En az 3 farklı konu deneyin ve sonuçları tablo halinde karşılaştırın

### Beklenen Davranış

```
Konu 1: "Agentic AI ve MCP"
  → Araştırma: 5 kaynak | Makale: 1,250 kelime | Puan: 8/10 | Maliyet: $0.0089

Konu 2: "RAG Sistemleri ve Vektör Veritabanları"
  → Araştırma: 4 kaynak | Makale: 1,100 kelime | Puan: 7/10 | Maliyet: $0.0075

Konu 3: "Prompt Engineering Teknikleri"
  → Araştırma: 3 kaynak | Makale: 980 kelime | Puan: 7/10 | Maliyet: $0.0068
```

### Bu Alıştırma Neyi Öğretir?

- Pipeline'ın uçtan uca çalışma akışını anlama
- Farklı konuların araştırma kalitesine etkisini gözlemleme
- Maliyet ve kalite arasındaki ilişkiyi kavrama

---

## Alıştırma 2: Memory Sistemine Yeni İçerik Yükle (⭐⭐ Orta)

### Görev

`ContentIngester` kullanarak hafıza sistemine **yeni içerik yükleyin** ve bu içeriğin araştırma kalitesini nasıl etkilediğini ölçün.

### Adımlar

1. `memory/ingestion.py` içindeki `ContentIngester` sınıfını inceleyin
2. Kendi içeriğinizi hazırlayın (en az 3 paragraf, bir AI konusu hakkında)
3. İçeriği GraphStore ve VectorStore'a yükleyin
4. Yükleme öncesi ve sonrası araştırma sonuçlarını karşılaştırın

### Başlangıç Kodu

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory.graph_store import GraphStore
from memory.vector_store import VectorStore
from memory.ingestion import ContentIngester
from mcp.tools.deep_research import search

# Hafıza sistemlerini başlat
graph = GraphStore(pre_populate=True)
vector = VectorStore(pre_populate=True)
ingester = ContentIngester(graph, vector)

# Yükleme öncesi istatistikleri kaydet
onceki_dugum = len(graph.nodes)
onceki_kenar = len(graph.edges)
onceki_belge = len(vector.documents)

# Yeni içerik hazırla
yeni_icerik = """
Yapay zeka ajanları ve otonom sistemler...
(Kendi içeriğinizi buraya yazın)
"""

# İçeriği yükle
sonuc = ingester.ingest(yeni_icerik, "ozel_arastirma_01")
print(f"Eklenen: +{sonuc.nodes_added} düğüm, +{sonuc.edges_added} kenar, "
      f"+{sonuc.documents_added} belge")

# Yükleme sonrası istatistikleri karşılaştır
print(f"\nÖnceki: {onceki_dugum} düğüm, {onceki_kenar} kenar, {onceki_belge} belge")
print(f"Sonrası: {len(graph.nodes)} düğüm, {len(graph.edges)} kenar, "
      f"{len(vector.documents)} belge")

# Araştırma kalitesini ölç
arama_sonucu = vector.search("yapay zeka ajan otonom", top_k=5)
for doc, skor in arama_sonucu:
    print(f"  [{skor:.4f}] {doc['content'][:80]}...")
```

### Beklenen Davranış

```
Eklenen: +5 düğüm, +3 kenar, +2 belge

Önceki: 56 düğüm, 73 kenar, 37 belge
Sonrası: 61 düğüm, 76 kenar, 39 belge

Arama sonuçları artık yeni içeriği de içeriyor:
  [0.3200] Yapay zeka ajanları ve otonom sistemler...  ← YENİ
  [0.2800] AI Agent, kullanıcı talimatlarını anlayan...
```

### Bu Alıştırma Neyi Öğretir?

- ContentIngester'ın entity extraction mekanizmasını anlama
- Graph ve Vector Store'un birlikte nasıl çalıştığını görme
- Hafıza zenginliğinin araştırma kalitesine etkisini gözlemleme

---

## Alıştırma 3: Reflection Threshold'unu Değiştir (⭐⭐ Orta)

### Görev

Orchestrator'daki `reflection_threshold` değerini değiştirerek **maliyet/kalite dengesini analiz edin**.

### Adımlar

1. `agents/orchestrator.py` dosyasındaki `reflection_threshold` parametresini inceleyin
2. Üç farklı eşik değeri ile pipeline'ı çalıştırın:
   - Düşük eşik: `reflection_threshold=5.0` (çoğu makale kabul edilir)
   - Normal eşik: `reflection_threshold=7.0` (varsayılan)
   - Yüksek eşik: `reflection_threshold=9.0` (çok az makale kabul edilir)
3. Her senaryo için şu metrikleri toplayın:
   - Reflection döngü sayısı
   - Son makale puanı
   - Toplam token kullanımı
   - Toplam maliyet
   - Pipeline süresi

### Başlangıç Kodu

```python
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator import OrchestratorAgent

async def karsilastirma():
    esikler = [5.0, 7.0, 9.0]
    sonuclar = []

    for esik in esikler:
        orchestrator = OrchestratorAgent(
            budget_limit=1.0,
            reflection_threshold=esik,
            max_reflection_loops=3,
        )
        result = await orchestrator.run_pipeline("Agentic AI ve MCP")

        sonuclar.append({
            "esik": esik,
            "dongular": result.reflection_loops,
            "puan": result.final_score,
            "token": result.total_tokens,
            "maliyet": result.total_cost,
            "sure": result.duration_seconds,
        })

    # Sonuçları tablo olarak göster
    print(f"\n{'Eşik':>6} | {'Döngü':>5} | {'Puan':>5} | {'Token':>7} | "
          f"{'Maliyet':>10} | {'Süre':>6}")
    print("-" * 60)
    for s in sonuclar:
        print(f"{s['esik']:>6.1f} | {s['dongular']:>5d} | {s['puan']:>5.1f} | "
              f"{s['token']:>7,} | ${s['maliyet']:>9.6f} | {s['sure']:>5.1f}s")

asyncio.run(karsilastirma())
```

### Beklenen Davranış

```
  Eşik | Döngü |  Puan |   Token |    Maliyet |  Süre
------------------------------------------------------------
   5.0 |     1 |   5.4 |   4,200 |  $0.003200 |   2.1s
   7.0 |     2 |   7.8 |   8,420 |  $0.008900 |   4.3s
   9.0 |     3 |   8.2 |  12,800 |  $0.014500 |   6.5s
```

### Analiz Soruları

1. Eşik değerini yükseltmek maliyeti ne kadar artırıyor?
2. Her ek reflection döngüsünün kaliteye katkısı nedir?
3. "Azalan getiri" (diminishing returns) noktası nerede başlıyor?
4. Production'da hangi eşik değeri en uygun olur?

### Bu Alıştırma Neyi Öğretir?

- Reflection döngüsünün maliyet/kalite dengesini anlama
- Eşik değerinin pipeline davranışına etkisini gözlemleme
- Production ortamları için optimal parametre seçimini kavrama

---

## Alıştırma 4: Yeni Agent Ekle — FactCheckerAgent (⭐⭐⭐ Zor)

### Görev

Pipeline'a yeni bir agent ekleyin: **FactCheckerAgent**. Bu agent, Writing Agent'ın ürettiği makale içindeki iddiaları doğrulasın.

### Gereksinimler

1. `agents/fact_checker_agent.py` dosyasını oluşturun
2. Agent, `citation_verify` tool'unu kullanarak iddiaları doğrulasın
3. Doğrulama sonuçlarını yapılandırılmış bir rapor olarak döndürsün
4. Pipeline'da Writing → **FactChecker** → Reflection sırasına ekleyin
5. Orchestrator'ı güncelleyin

### Başlangıç Kodu

```python
"""
FactCheckerAgent - İddia Doğrulama Agent'ı
=============================================
Makale içindeki iddiaları kaynaklarla karşılaştırarak doğrular.
"""

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from mcp.tools.citation_verify import verify_citations

logger = get_logger("fact_checker_agent")


@dataclass
class FactCheckResult:
    """Doğrulama sonucu."""
    total_claims: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    coverage_score: int = 0
    verified_claims: list = field(default_factory=list)
    unverified_claims: list = field(default_factory=list)
    report: str = ""
    token_count: int = 0


class FactCheckerAgent:
    """İddia doğrulama agent'ı."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self._logger = get_logger("fact_checker_agent")
        self._logger.info("FactCheckerAgent başlatıldı")

    async def check_facts(
        self,
        article_content: str,
        research_sources: list,
    ) -> FactCheckResult:
        """
        Makale içeriğindeki iddiaları doğrula.

        Parametreler:
            article_content: Doğrulanacak makale metni
            research_sources: Araştırma kaynakları listesi

        Döndürür:
            FactCheckResult: Doğrulama sonucu
        """
        self._logger.info("İddia doğrulama başlatıldı...")

        # TODO: citation_verify tool'unu kullanarak doğrulama yap
        # TODO: Sonuçları FactCheckResult'a dönüştür
        # TODO: Rapor oluştur

        raise NotImplementedError("Bu metodu tamamlayın!")
```

### Pipeline Güncellemesi

Orchestrator'daki yazım-reflection döngüsüne FactChecker'ı ekleyin:

```
Mevcut:   Writing → Reflection → [Yeterli mi?]
Yeni:     Writing → FactChecker → Reflection → [Yeterli mi?]
```

### Beklenen Davranış

```
[Orchestrator]  Pipeline başlatılıyor...
[Research]      5 kaynak bulundu
[Writing]       Taslak v1 oluşturuldu (1,250 kelime)
[FactChecker]   12 iddia analiz edildi:
                  ✅ 9 doğrulanmış (%75 kapsama)
                  ❌ 3 doğrulanmamış
[Reflection]    Kalite puanı: 7.5/10 → Kabul edildi ✅
[Repurpose]     LinkedIn postu oluşturuldu
```

### Bu Alıştırma Neyi Öğretir?

- Yeni agent oluşturma ve pipeline'a entegre etme
- MCP tool'larını agent içinden kullanma
- Orchestrator'ın agent yönetim mekanizmasını anlama
- Multi-agent mesajlaşma yapısını kavrama

---

## Alıştırma 5: Paralel Research Pipeline (⭐⭐⭐⭐ Çok Zor)

### Görev

Birden fazla kaynağı **aynı anda araştıran** asenkron pipeline yazın. Orchestrator, konuyu alt konulara böler ve her alt konu için paralel araştırma yapar.

### Gereksinimler

1. Orchestrator'a `parallel_research` modu ekleyin
2. Konu analizi yapıp alt konulara bölün (en az 3)
3. `asyncio.gather()` ile paralel araştırma yapın
4. Her alt konunun araştırma sonuçlarını birleştirin
5. Birleştirilmiş araştırma ile tek bir makale üretin
6. Sıralı ve paralel modların performansını karşılaştırın

### Başlangıç Kodu

```python
"""
Paralel Research Pipeline
==========================
Birden fazla alt konuyu aynı anda araştıran async pipeline.
"""

import asyncio
import sys
import os
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.tools.deep_research import search
from memory.graph_store import GraphStore


@dataclass
class ParallelResearchResult:
    """Paralel araştırma sonucu."""
    alt_konular: list[str] = field(default_factory=list)
    sonuclar: list[dict] = field(default_factory=list)
    toplam_kaynak: int = 0
    toplam_sure: float = 0.0
    paralel_tasarruf: float = 0.0  # Sıralıya göre tasarruf edilen süre


async def alt_konulara_bol(ana_konu: str, graph: GraphStore) -> list[str]:
    """
    Ana konuyu araştırılabilir alt konulara böl.

    İpucu: GraphStore'daki ilişkili kavramları kullanarak
    alt konu listesi oluşturabilirsiniz.

    Parametreler:
        ana_konu: Ana araştırma konusu
        graph: GraphStore instance

    Döndürür:
        list[str]: Alt konu listesi (3-5 adet)
    """
    # TODO: GraphStore'dan ilişkili kavramları çek
    # TODO: Bu kavramları alt konu olarak formüle et
    raise NotImplementedError("Bu metodu tamamlayın!")


async def paralel_arastirma(alt_konular: list[str]) -> list[dict]:
    """
    Alt konuları paralel olarak araştır.

    Parametreler:
        alt_konular: Alt konu listesi

    Döndürür:
        list[dict]: Her alt konunun araştırma sonuçları
    """
    async def tek_arastirma(konu: str) -> dict:
        """Tek bir alt konuyu araştır (simüle edilmiş gecikme)."""
        await asyncio.sleep(0.5)  # Simüle edilmiş API gecikmesi
        sonuc = search(konu, max_results=3)
        return {"konu": konu, "sonuc": sonuc}

    # TODO: asyncio.gather() ile tüm araştırmaları paralel çalıştır
    raise NotImplementedError("Bu metodu tamamlayın!")


async def sirali_arastirma(alt_konular: list[str]) -> list[dict]:
    """Alt konuları sıralı olarak araştır (karşılaştırma için)."""
    sonuclar = []
    for konu in alt_konular:
        await asyncio.sleep(0.5)  # Simüle edilmiş API gecikmesi
        sonuc = search(konu, max_results=3)
        sonuclar.append({"konu": konu, "sonuc": sonuc})
    return sonuclar


async def performans_karsilastirmasi():
    """Sıralı vs paralel araştırmanın performans karşılaştırması."""
    graph = GraphStore()
    ana_konu = "Agentic AI ve MCP"

    alt_konular = await alt_konulara_bol(ana_konu, graph)
    print(f"Alt konular ({len(alt_konular)}):")
    for i, konu in enumerate(alt_konular, 1):
        print(f"  {i}. {konu}")

    # Sıralı araştırma
    baslangic = time.time()
    sirali_sonuc = await sirali_arastirma(alt_konular)
    sirali_sure = time.time() - baslangic

    # Paralel araştırma
    baslangic = time.time()
    paralel_sonuc = await paralel_arastirma(alt_konular)
    paralel_sure = time.time() - baslangic

    # Karşılaştırma
    print(f"\n📊 Performans Karşılaştırması:")
    print(f"  Sıralı:  {sirali_sure:.2f}s")
    print(f"  Paralel: {paralel_sure:.2f}s")
    print(f"  Tasarruf: {sirali_sure - paralel_sure:.2f}s "
          f"(%{(1 - paralel_sure / sirali_sure) * 100:.0f} daha hızlı)")

asyncio.run(performans_karsilastirmasi())
```

### Beklenen Davranış

```
Alt konular (3):
  1. Yapay zeka ajanları ve otonom sistemler
  2. MCP protokolü ve araç kullanımı
  3. Çok ajanlı sistemler ve orkestrasyon

  → arastirma_1 başladı: "Yapay zeka ajanları..."
  → arastirma_2 başladı: "MCP protokolü..."
  → arastirma_3 başladı: "Çok ajanlı sistemler..."

  (3 araştırma AYNI ANDA çalışır)

  ← arastirma_1 tamamlandı (0.52s)
  ← arastirma_3 tamamlandı (0.54s)
  ← arastirma_2 tamamlandı (0.56s)

📊 Performans Karşılaştırması:
  Sıralı:  1.58s
  Paralel: 0.56s
  Tasarruf: 1.02s (%65 daha hızlı)
```

### Bonus Görevler

1. Hata toleransı ekleyin: Bir araştırma başarısız olursa diğerleri devam etsin
2. Sonuçları birleştirip tekrarlanan kaynakları kaldırın
3. Her alt konunun araştırma kalitesini ayrı ayrı değerlendirin

### Bu Alıştırma Neyi Öğretir?

- `asyncio.gather()` ile paralel asenkron programlama
- GraphStore'u görev planlamasında kullanma
- Sıralı ve paralel çalışma modlarının performans karşılaştırması
- Production ortamlarında hata toleranslı async tasarım

---

## ✅ Kontrol Listesi

Tüm alıştırmaları tamamladıktan sonra şunları yapabilmelisiniz:

- [ ] Pipeline'ı farklı konularla çalıştırıp sonuçları karşılaştırabiliyorum
- [ ] ContentIngester ile hafıza sistemine yeni içerik yükleyebiliyorum
- [ ] Reflection threshold'unu ayarlayarak maliyet/kalite dengesini optimize edebiliyorum
- [ ] Yeni bir agent oluşturup pipeline'a entegre edebiliyorum
- [ ] Paralel araştırma pipeline'ı yazarak performans artışı sağlayabiliyorum
- [ ] GraphStore ve VectorStore'u etkin bir şekilde kullanabiliyorum
- [ ] MCP tool'larını agent'lar içinden çağırabiliyorum
- [ ] Maliyet raporu oluşturup optimizasyon önerileri üretebiliyorum
- [ ] Async/await ile paralel agent çalıştırma yapabiliyorum
- [ ] Production-grade bir agent sisteminin tüm bileşenlerini anlıyorum

---

> 💡 **İpucu:** Takıldığınızda `expected_outputs/` klasöründeki örneklere bakın.
> Hâlâ takılıyorsanız, `theory.md`'yi tekrar okuyun.
> Her alıştırmada testlerinizi `tests/test_twingraph.py`'ye ekleyin.
