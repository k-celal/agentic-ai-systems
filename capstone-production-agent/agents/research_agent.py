"""
Research Agent - Derin Araştırma Agent'ı
==========================================
Verilen bir konu hakkında kapsamlı araştırma yapan agent.

NEDEN BU AGENT VAR?
--------------------
Kaliteli bir makale yazmak için önce kaliteli araştırma gerekir.
ResearchAgent, pipeline'ın ilk adımıdır ve şunları yapar:

1. **Kaynak Toplama**: MCP tool'ları üzerinden derin araştırma yapar
   - deep_research.search → Web tabanlı kaynak araması
   - memory.graph_query → GraphRAG'dan ilişkili kavramları çeker
   - memory.vector_search → Benzer içerikleri vektör benzerliği ile bulur

2. **Bilgi Özetleme**: Toplanan kaynakları anlamlı bir özete dönüştürür
   - Her kaynaktan temel noktaları çıkarır
   - Kaynaklar arası bağlantıları tespit eder
   - Konu hakkında tutarlı bir araştırma özeti oluşturur

3. **Kaynakça Çıkarma**: Her kaynak için yapılandırılmış citation oluşturur
   - Kaynak URL'si / adı
   - Başlık
   - Temel nokta (key point)

Demo Modu:
    API key olmadan da çalışabilir. _mock_research() metodu
    gerçekçi demo verileri üretir, böylece pipeline'ı uçtan uca
    test edebilirsiniz.

Kullanım:
    from agents.research_agent import ResearchAgent

    agent = ResearchAgent()
    result = await agent.research("Agentic AI ve MCP Protokolü")

    print(result.summary)
    print(f"Kaynak sayısı: {len(result.sources)}")
    print(f"Token kullanımı: {result.token_count}")
"""

import os
import sys
import json
from dataclasses import dataclass, field
from typing import Optional, Any

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger, AgentTracer
from shared.schemas.message import build_messages
from shared.utils.helpers import retry_async, truncate_text, parse_json_safely


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class Citation:
    """
    Bir kaynakçayı temsil eder.

    Neden yapılandırılmış kaynakça?
    - Makalede doğru atıf yapılmasını sağlar
    - Kaynakçanın doğrulanabilir olmasını sağlar
    - Writing agent'a hangi bilginin nereden geldiğini söyler
    """
    source: str         # Kaynak URL'si veya adı
    title: str          # Başlık
    key_point: str      # Bu kaynaktan çıkarılan temel nokta


@dataclass
class ResearchOutput:
    """
    Araştırma sonucunu temsil eden veri sınıfı.

    Bu sınıf, ResearchAgent'ın çıktısıdır ve Writing Agent'a girdi olarak verilir.

    Alanlar:
        topic: Araştırılan konu
        sources: Bulunan kaynakların listesi (her biri bir dict)
        summary: Tüm kaynakların birleştirilmiş özeti
        citations: Yapılandırılmış kaynakça listesi
        token_count: Bu araştırmada kullanılan toplam token sayısı
    """
    topic: str                                         # Araştırılan konu
    sources: list[dict] = field(default_factory=list)  # Ham kaynak verileri
    summary: str = ""                                  # Birleştirilmiş araştırma özeti
    citations: list[Citation] = field(default_factory=list)  # Yapılandırılmış kaynakçalar
    token_count: int = 0                               # Kullanılan toplam token


# ============================================================
# Sistem Prompt'u
# ============================================================

RESEARCH_SYSTEM_PROMPT = """Sen deneyimli bir araştırma analistisin.
Görevin: Verilen konu hakkında kapsamlı ve derinlemesine araştırma yapmak.

Araştırma çıktın şu formatta olmalıdır (JSON):
{
    "summary": "Konunun kapsamlı özeti (en az 300 kelime)",
    "key_findings": [
        "Bulgu 1: ...",
        "Bulgu 2: ...",
        "Bulgu 3: ..."
    ],
    "connections": [
        "İlişki 1: Kavram A ile Kavram B arasındaki bağlantı",
        "İlişki 2: ..."
    ],
    "citations": [
        {
            "source": "kaynak_url_veya_adı",
            "title": "Kaynak Başlığı",
            "key_point": "Bu kaynaktan çıkarılan temel bulgu"
        }
    ]
}

Kurallar:
1. Her bulgu somut ve doğrulanabilir olmalı
2. Kaynaklar arası bağlantıları mutlaka belirt
3. Özet, konunun tüm boyutlarını kapsamalı
4. Teknik terimleri Türkçe açıklamalarıyla birlikte kullan
5. Cevabını SADECE JSON formatında ver, başka metin ekleme
"""


# ============================================================
# ResearchAgent Sınıfı
# ============================================================

class ResearchAgent:
    """
    Derin Araştırma Agent'ı.

    Bu agent, verilen bir konu hakkında MCP tool'larını kullanarak
    veya LLM ile kapsamlı araştırma yapar.

    İki çalışma modu:
    1. **Tool Modu**: MCP tool'ları ile gerçek araştırma
       - deep_research.search ile web kaynakları
       - memory.graph_query ile GraphRAG'dan bilgi
       - memory.vector_search ile benzer içerikler
    2. **Demo Modu**: API key yoksa simüle edilmiş araştırma
       - Gerçekçi demo verileri üretir
       - Pipeline test edilebilir

    Parametreler:
        model: Kullanılacak LLM modeli (varsayılan: gpt-4o-mini)
        temperature: Yaratıcılık seviyesi (varsayılan: 0.3 - düşük, tutarlı)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
    ):
        """
        ResearchAgent'ı başlat.

        Parametreler:
            model: Araştırma özetleme için kullanılacak model.
                   Araştırma pahalı bir yaratıcılık gerektirmez,
                   bu yüzden gpt-4o-mini yeterlidir.
            temperature: Düşük tutulur çünkü araştırma sonuçları
                        tutarlı ve güvenilir olmalı.
        """
        self._client = LLMClient(model=model, temperature=temperature)
        self._logger = get_logger("research_agent")
        self._tracer = AgentTracer("research_agent")

    async def research(
        self,
        topic: str,
        tools_dict: Optional[dict[str, Any]] = None,
    ) -> ResearchOutput:
        """
        Verilen konu hakkında kapsamlı araştırma yap.

        Bu metod, pipeline'ın ilk adımıdır. Sonucu
        doğrudan WritingAgent'a girdi olarak verilir.

        Parametreler:
            topic: Araştırılacak konu
                   Örnek: "Agentic AI sistemleri ve MCP Protokolü"
            tools_dict: MCP tool fonksiyonlarının sözlüğü (isteğe bağlı)
                        Örnek: {"deep_research.search": search_fn, ...}
                        Verilmezse sadece LLM ile araştırma yapar.

        Döndürür:
            ResearchOutput: Araştırma sonucu (özet, kaynaklar, kaynakça)

        Örnek:
            agent = ResearchAgent()
            result = await agent.research("Yapay zeka etiği")
            print(result.summary)
        """
        self._tracer.start_task(f"Araştırma: {topic}")
        self._logger.info(f"Araştırma başlatılıyor | Konu: {topic}")

        total_tokens = 0
        all_sources: list[dict] = []

        # ────────────────────────────────────
        # Adım 1: MCP Tool'ları ile veri topla
        # ────────────────────────────────────
        if tools_dict:
            # Deep Research araması
            if "deep_research.search" in tools_dict:
                self._tracer.log_tool_call("deep_research.search", {"topic": topic})
                try:
                    search_result = await tools_dict["deep_research.search"](topic)
                    if isinstance(search_result, dict):
                        all_sources.append(search_result)
                    elif isinstance(search_result, list):
                        all_sources.extend(search_result)
                    self._tracer.log_tool_result("deep_research.search", search_result)
                    self._logger.info(f"Deep research tamamlandı | Kaynak: {len(all_sources)}")
                except Exception as e:
                    self._tracer.log_error(f"deep_research.search hatası: {e}")
                    self._logger.error(f"Deep research hatası: {e}")

            # GraphRAG sorgusu
            if "memory.graph_query" in tools_dict:
                self._tracer.log_tool_call("memory.graph_query", {"topic": topic})
                try:
                    graph_result = await tools_dict["memory.graph_query"](topic)
                    if graph_result:
                        all_sources.append({"type": "graph", "data": graph_result})
                    self._tracer.log_tool_result("memory.graph_query", graph_result)
                    self._logger.info("GraphRAG sorgusu tamamlandı")
                except Exception as e:
                    self._tracer.log_error(f"memory.graph_query hatası: {e}")
                    self._logger.error(f"GraphRAG hatası: {e}")

            # Vektör arama
            if "memory.vector_search" in tools_dict:
                self._tracer.log_tool_call("memory.vector_search", {"query": topic})
                try:
                    vector_result = await tools_dict["memory.vector_search"](topic)
                    if vector_result:
                        all_sources.append({"type": "vector", "data": vector_result})
                    self._tracer.log_tool_result("memory.vector_search", vector_result)
                    self._logger.info("Vektör arama tamamlandı")
                except Exception as e:
                    self._tracer.log_error(f"memory.vector_search hatası: {e}")
                    self._logger.error(f"Vektör arama hatası: {e}")

        # ────────────────────────────────────
        # Adım 2: LLM ile araştırma özetleme
        # ────────────────────────────────────
        self._tracer.log_think("Kaynakları özetleyeceğim ve kaynakça çıkaracağım")

        # Kaynak bilgilerini prompt'a ekle
        source_context = ""
        if all_sources:
            source_context = f"\n\nToplanan Kaynaklar:\n{json.dumps(all_sources, ensure_ascii=False, indent=2)}"

        user_message = (
            f"Şu konu hakkında kapsamlı bir araştırma özeti hazırla: '{topic}'"
            f"{source_context}"
        )

        messages = build_messages(
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            user_message=user_message,
        )

        response = await self._client.chat_with_messages(messages)
        total_tokens += response.usage.total_tokens

        # ────────────────────────────────────
        # Adım 3: Cevabı parse et
        # ────────────────────────────────────
        research_output = self._parse_research_response(
            response.content or "",
            topic,
            all_sources,
            total_tokens,
        )

        # Demo mod kontrolü: API yoksa mock veri kullan
        if response.model == "demo-mode":
            self._logger.info("Demo mod algılandı, mock araştırma verileri kullanılıyor")
            research_output = self._mock_research(topic)

        self._tracer.log_response(
            f"Araştırma tamamlandı | "
            f"Kaynak: {len(research_output.sources)} | "
            f"Kaynakça: {len(research_output.citations)} | "
            f"Token: {research_output.token_count}"
        )
        self._tracer.end_task(success=True)

        return research_output

    def _parse_research_response(
        self,
        content: str,
        topic: str,
        sources: list[dict],
        token_count: int,
    ) -> ResearchOutput:
        """
        LLM cevabını ResearchOutput'a dönüştür.

        LLM'den gelen JSON cevabını parse eder ve yapılandırılmış
        veri sınıfına çevirir. JSON parse başarısız olursa
        ham metni özet olarak kullanır.
        """
        parsed = parse_json_safely(content)

        if parsed:
            # JSON başarıyla parse edildi
            citations = []
            for c in parsed.get("citations", []):
                citations.append(Citation(
                    source=c.get("source", "Bilinmeyen"),
                    title=c.get("title", "Başlıksız"),
                    key_point=c.get("key_point", ""),
                ))

            return ResearchOutput(
                topic=topic,
                sources=sources,
                summary=parsed.get("summary", content),
                citations=citations,
                token_count=token_count,
            )
        else:
            # JSON parse başarısız, ham metni kullan
            self._logger.warning("Araştırma cevabı JSON olarak parse edilemedi, ham metin kullanılıyor")
            return ResearchOutput(
                topic=topic,
                sources=sources,
                summary=content,
                citations=[],
                token_count=token_count,
            )

    def _mock_research(self, topic: str) -> ResearchOutput:
        """
        API key olmadan demo araştırma verisi üret.

        Bu metod neden var?
        - Pipeline'ı uçtan uca test etmek için gerçek API gerekmez
        - Öğrenme sürecinde maliyetsiz denemeler yapılabilir
        - CI/CD testlerinde kullanılabilir

        Parametreler:
            topic: Araştırılacak konu

        Döndürür:
            ResearchOutput: Gerçekçi demo araştırma verisi
        """
        self._logger.info(f"Mock araştırma üretiliyor | Konu: {topic}")

        mock_sources = [
            {
                "title": f"{topic} - Kapsamlı Rehber",
                "url": "https://example.com/research/guide",
                "snippet": f"{topic} konusunun temel kavramları ve uygulama alanları.",
            },
            {
                "title": f"{topic}: Güncel Gelişmeler 2025",
                "url": "https://example.com/research/trends",
                "snippet": f"{topic} alanındaki son gelişmeler ve gelecek trendleri.",
            },
            {
                "title": f"Production-Grade {topic} Sistemleri",
                "url": "https://example.com/research/production",
                "snippet": f"{topic} sistemlerinin production ortamında uygulanması.",
            },
            {
                "title": f"{topic} ve Etik Değerlendirmeler",
                "url": "https://example.com/research/ethics",
                "snippet": f"{topic} kullanımında etik sorunlar ve çözüm önerileri.",
            },
            {
                "title": f"Açık Kaynak {topic} Araçları",
                "url": "https://example.com/research/tools",
                "snippet": f"{topic} için kullanılan popüler açık kaynak araçlar ve frameworkler.",
            },
        ]

        mock_citations = [
            Citation(
                source="https://example.com/research/guide",
                title=f"{topic} - Kapsamlı Rehber",
                key_point=f"{topic} kavramının temel tanımı ve çalışma prensibi.",
            ),
            Citation(
                source="https://example.com/research/trends",
                title=f"{topic}: Güncel Gelişmeler 2025",
                key_point=f"{topic} alanında 2025 yılında öne çıkan 3 temel trend.",
            ),
            Citation(
                source="https://example.com/research/production",
                title=f"Production-Grade {topic} Sistemleri",
                key_point="Production ortamında güvenilirlik, ölçeklenebilirlik ve maliyet optimizasyonu.",
            ),
            Citation(
                source="https://example.com/research/ethics",
                title=f"{topic} ve Etik Değerlendirmeler",
                key_point="Otonom karar verme sistemlerinde şeffaflık ve hesap verebilirlik.",
            ),
            Citation(
                source="https://example.com/research/tools",
                title=f"Açık Kaynak {topic} Araçları",
                key_point="LangChain, CrewAI, AutoGen gibi frameworklerin karşılaştırması.",
            ),
        ]

        mock_summary = (
            f"{topic} Araştırma Özeti\n"
            f"{'=' * 40}\n\n"
            f"1. TANIM VE KAPSAM\n"
            f"{topic}, yapay zeka alanında hızla gelişen bir disiplindir. "
            f"Bu alan, otonom karar verebilen, çevresiyle etkileşime geçebilen ve "
            f"karmaşık görevleri adım adım çözebilen sistemlerin tasarımını kapsar.\n\n"
            f"2. TEMEL KAVRAMLAR\n"
            f"- Agent Döngüsü: Düşün → Plan → Çalıştır → Gözlemle döngüsü\n"
            f"- Tool Kullanımı: Harici araçlarla etkileşim (API, veritabanı, dosya)\n"
            f"- Hafıza Yönetimi: Kısa ve uzun vadeli bilgi depolama\n"
            f"- Çoklu Agent: Birden fazla agent'ın koordineli çalışması\n\n"
            f"3. GÜNCEL GELİŞMELER\n"
            f"- MCP (Model Context Protocol) standardının yaygınlaşması\n"
            f"- GraphRAG ile bilgi grafiği tabanlı hafıza sistemleri\n"
            f"- Production-grade agent framework'lerinin olgunlaşması\n"
            f"- Maliyet optimizasyonu ve model yönlendirme stratejileri\n\n"
            f"4. ZORLUKLAR VE FIRSATLAR\n"
            f"- Zorluklar: Hallüsinasyon kontrolü, maliyet yönetimi, güvenilirlik\n"
            f"- Fırsatlar: İçerik üretimi, araştırma otomasyonu, karar destek sistemleri\n\n"
            f"5. SONUÇ\n"
            f"{topic} alanı, 2025 itibarıyla prototipten production'a geçiş aşamasındadır. "
            f"Başarılı uygulamalar; iyi tasarlanmış agent mimarisi, etkili tool kullanımı "
            f"ve kapsamlı değerlendirme mekanizmaları gerektirmektedir."
        )

        return ResearchOutput(
            topic=topic,
            sources=mock_sources,
            summary=mock_summary,
            citations=mock_citations,
            token_count=150,  # Demo mod token tahmini
        )


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_research():
        """
        ResearchAgent'ı bağımsız test et.

        Bu test:
        1. Agent'ı oluşturur
        2. Örnek bir konu ile araştırma yapar
        3. Sonuçları ekrana yazdırır
        """
        print("=" * 50)
        print("🧪 ResearchAgent Test")
        print("=" * 50)

        agent = ResearchAgent()
        result = await agent.research("Agentic AI ve MCP Protokolü")

        print(f"\n📋 Konu: {result.topic}")
        print(f"📚 Kaynak Sayısı: {len(result.sources)}")
        print(f"📝 Kaynakça Sayısı: {len(result.citations)}")
        print(f"🔢 Token Kullanımı: {result.token_count}")
        print(f"\n📄 Özet (ilk 500 karakter):")
        print(result.summary[:500])

        if result.citations:
            print(f"\n📎 Kaynakçalar:")
            for i, c in enumerate(result.citations, 1):
                print(f"  {i}. [{c.title}]")
                print(f"     Kaynak: {c.source}")
                print(f"     Nokta: {c.key_point}")

    asyncio.run(test_research())
