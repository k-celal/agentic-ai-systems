"""
Writing Agent - İçerik Üretici Agent
=======================================
Araştırma sonuçlarını yapılandırılmış bir Medium makalesine dönüştüren agent.

NEDEN BU AGENT VAR?
--------------------
İyi bir araştırma, iyi bir yazıya otomatik dönüşmez. WritingAgent,
ham araştırma verilerini okuyucuya değer katan, yapılandırılmış bir
makaleye dönüştürür.

Makalenin yapısı:
- Başlık (dikkat çekici, SEO uyumlu)
- Alt başlık (konunun özeti)
- Giriş (okuyucuyu neden okuması gerektiğine ikna eden)
- Gövde paragrafları (her biri bir alt konuyu derinlemesine ele alan)
- Sonuç (öğrenilenlerin özeti ve eylem çağrısı)
- Kaynakça (araştırma kaynakları)

Reflection Döngüsü:
    Bu agent, ReflectionAgent'tan gelen geri bildirimle çalışır.
    İlk taslak → Reflection → İyileştirilmiş taslak → Reflection → ...
    Her çağrıda `feedback` parametresi ile önceki eleştiriler iletilir
    ve agent bu eleştirilere göre makaleyi iyileştirir.

Kullanım:
    from agents.writing_agent import WritingAgent

    agent = WritingAgent()

    # İlk taslak
    draft_v1 = await agent.write_article(research_output)

    # Geri bildirimle iyileştirme
    draft_v2 = await agent.write_article(research_output, feedback="Giriş daha güçlü olmalı")
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger, AgentTracer
from shared.schemas.message import build_messages
from shared.utils.helpers import truncate_text


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class ArticleDraft:
    """
    Bir makale taslağını temsil eder.

    WritingAgent her çağrıda yeni bir ArticleDraft üretir.
    Pipeline, draft'ların versiyonlarını takip eder.

    Alanlar:
        title: Makale başlığı
        content: Tam makale metni (markdown formatında)
        word_count: Kelime sayısı
        version: Taslak versiyonu (v1, v2, v3...)
        token_count: Bu taslağı üretmek için kullanılan token sayısı
    """
    title: str = ""                          # Makale başlığı
    content: str = ""                        # Tam makale metni
    word_count: int = 0                      # Kelime sayısı
    version: int = 1                         # Taslak versiyonu
    token_count: int = 0                     # Kullanılan token


# ============================================================
# Sistem Prompt'ları
# ============================================================

WRITING_SYSTEM_PROMPT = """Sen deneyimli bir teknik yazar ve Medium editörüsün.
Görevin: Araştırma sonuçlarını okuyucu dostu, derinlemesine bir Medium makalesine dönüştürmek.

Makale Yapısı:
1. **Başlık**: Dikkat çekici, merak uyandıran, SEO uyumlu
2. **Alt Başlık**: Konunun 1 cümlelik özeti
3. **Giriş** (2-3 paragraf): Okuyucuyu konuya çek, neden okuması gerektiğini anlat
4. **Gövde Bölümleri** (3-5 bölüm): Her biri bir alt konuyu derinlemesine ele alsın
   - Her bölümün kendi alt başlığı olsun
   - Somut örnekler ve açıklamalar içersin
   - Teknik terimleri Türkçe karşılıklarıyla birlikte kullan
5. **Sonuç** (1-2 paragraf): Öğrenilenleri özetle, okuyucuya eylem öner
6. **Kaynakça**: Araştırma kaynaklarını listele

Yazım Kuralları:
- Dil: Türkçe (teknik terimlerin İngilizce karşılığını parantez içinde ver)
- Ton: Profesyonel ama samimi, "sen" dili kullan
- Format: Markdown
- Minimum 800 kelime
- Gerçek örneklerle destekle
- Kaynaklara atıf yap
"""

REVISION_SYSTEM_PROMPT = """Sen deneyimli bir teknik yazar ve Medium editörüsün.
Görevin: Önceki taslağı, verilen geri bildirime göre iyileştirmek.

Kurallar:
1. Geri bildirimde belirtilen SOMUT sorunları düzelt
2. Makalenin güçlü yanlarını koru
3. Yapıyı ve akışı iyileştir
4. Yeni içerik ekleyerek derinliği artır
5. Kelime sayısını AZALTMA, artır veya koru
6. Kaynakça kullanımını güçlendir
7. Çıktını Markdown formatında ver
"""


# ============================================================
# WritingAgent Sınıfı
# ============================================================

class WritingAgent:
    """
    İçerik Üretici Agent.

    Bu agent, ResearchAgent'ın çıktısını alır ve yapılandırılmış
    bir Medium makalesi üretir. ReflectionAgent'tan gelen geri
    bildirimle taslağı iteratif olarak iyileştirir.

    Neden yüksek temperature?
    - Yaratıcı yazım, LLM'in daha "serbest" düşünmesini gerektirir
    - temperature=0.8, farklı ve ilgi çekici cümleler üretir
    - Araştırma agent'ı (0.3) ile yazım agent'ı (0.8) farklı temperature kullanır

    Parametreler:
        model: Yazım için kullanılacak model (varsayılan: gpt-4o)
               Son yazım kalitesi önemli olduğu için güçlü model önerilir.
        temperature: Yaratıcılık seviyesi (varsayılan: 0.8 - yüksek yaratıcılık)
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.8,
    ):
        """
        WritingAgent'ı başlat.

        Parametreler:
            model: Yazım modeli. gpt-4o önerilir çünkü:
                   - Daha iyi Türkçe dil kalitesi
                   - Daha tutarlı yapı ve akış
                   - Daha yaratıcı ve çeşitli ifadeler
            temperature: Yüksek tutulur çünkü yaratıcı yazım gerekir.
                        0.8, tutarlılık ile yaratıcılık arasında iyi bir denge.
        """
        self._client = LLMClient(model=model, temperature=temperature)
        self._logger = get_logger("writing_agent")
        self._tracer = AgentTracer("writing_agent")
        self._version_counter = 0  # Taslak versiyonu takipçisi

    async def write_article(
        self,
        research_output: any,
        memory_context: Optional[str] = None,
        feedback: Optional[str] = None,
    ) -> ArticleDraft:
        """
        Araştırma sonuçlarından makale üret veya mevcut taslağı iyileştir.

        Bu metod iki modda çalışır:
        1. **İlk taslak** (feedback=None): Araştırmadan yeni makale üretir
        2. **İyileştirme** (feedback=str): Geri bildirime göre taslağı geliştirir

        Parametreler:
            research_output: ResearchAgent'ın çıktısı.
                             .summary, .citations, .topic alanlarını kullanır.
            memory_context: GraphRAG'dan gelen ek bağlam bilgisi (isteğe bağlı).
                           Önceki yazılardan/araştırmalardan ilgili bilgiler.
            feedback: ReflectionAgent'tan gelen geri bildirim (isteğe bağlı).
                     İlk taslak için None, iyileştirme için str.

        Döndürür:
            ArticleDraft: Üretilen makale taslağı

        Örnek:
            # İlk taslak
            draft = await agent.write_article(research_output)

            # Geri bildirimle iyileştirme
            draft_v2 = await agent.write_article(
                research_output,
                feedback="Giriş bölümü daha güçlü olmalı, örnekler artırılmalı"
            )
        """
        self._version_counter += 1
        is_revision = feedback is not None

        task_desc = (
            f"Taslak v{self._version_counter} iyileştirme"
            if is_revision
            else f"Taslak v{self._version_counter} oluşturma"
        )
        self._tracer.start_task(task_desc)
        self._logger.info(
            f"Makale {'iyileştirme' if is_revision else 'oluşturma'} başlatılıyor | "
            f"Versiyon: {self._version_counter} | Konu: {getattr(research_output, 'topic', 'N/A')}"
        )

        # ────────────────────────────────────
        # Prompt hazırlama
        # ────────────────────────────────────
        if is_revision:
            system_prompt = REVISION_SYSTEM_PROMPT
            user_message = self._build_revision_prompt(research_output, feedback)
        else:
            system_prompt = WRITING_SYSTEM_PROMPT
            user_message = self._build_initial_prompt(research_output, memory_context)

        self._tracer.log_think(
            f"{'İyileştirme' if is_revision else 'İlk taslak'} prompt'u hazırlandı"
        )

        # ────────────────────────────────────
        # LLM çağrısı
        # ────────────────────────────────────
        messages = build_messages(
            system_prompt=system_prompt,
            user_message=user_message,
        )

        response = await self._client.chat_with_messages(messages)
        content = response.content or ""

        # Demo mod kontrolü
        if response.model == "demo-mode":
            self._logger.info("Demo mod algılandı, mock makale üretiliyor")
            content = self._mock_article(
                getattr(research_output, "topic", "Demo Konu"),
                is_revision,
            )

        # ────────────────────────────────────
        # ArticleDraft oluştur
        # ────────────────────────────────────
        title = self._extract_title(content)
        word_count = len(content.split())

        draft = ArticleDraft(
            title=title,
            content=content,
            word_count=word_count,
            version=self._version_counter,
            token_count=response.usage.total_tokens,
        )

        self._tracer.log_response(
            f"Taslak v{draft.version} oluşturuldu | "
            f"Kelime: {draft.word_count} | Token: {draft.token_count}"
        )
        self._tracer.end_task(success=True)

        self._logger.info(
            f"Makale taslağı hazır | v{draft.version} | "
            f"{draft.word_count} kelime | {draft.token_count} token"
        )

        return draft

    # ────────────────────────────────────────────────────────
    # Prompt Oluşturma Yardımcıları
    # ────────────────────────────────────────────────────────

    def _build_initial_prompt(
        self,
        research_output: any,
        memory_context: Optional[str],
    ) -> str:
        """
        İlk taslak için kullanıcı prompt'u oluştur.

        Araştırma çıktısını ve hafıza bağlamını birleştirerek
        zengin bir prompt hazırlar.
        """
        parts = [
            f"Konu: {getattr(research_output, 'topic', 'Bilinmeyen Konu')}",
            "",
            "Araştırma Özeti:",
            getattr(research_output, "summary", "Araştırma özeti mevcut değil."),
            "",
        ]

        # Kaynakçaları ekle
        citations = getattr(research_output, "citations", [])
        if citations:
            parts.append("Kullanılabilir Kaynaklar:")
            for i, c in enumerate(citations, 1):
                source = getattr(c, "source", "N/A")
                title = getattr(c, "title", "N/A")
                key_point = getattr(c, "key_point", "N/A")
                parts.append(f"  {i}. [{title}]({source}) - {key_point}")
            parts.append("")

        # Hafıza bağlamı
        if memory_context:
            parts.append("Ek Bağlam (Hafıza Sisteminden):")
            parts.append(truncate_text(memory_context, max_length=1000))
            parts.append("")

        parts.append(
            "Bu araştırma sonuçlarını kullanarak kapsamlı bir Medium makalesi yaz. "
            "Makale Türkçe olmalı ve en az 800 kelime içermelidir."
        )

        return "\n".join(parts)

    def _build_revision_prompt(
        self,
        research_output: any,
        feedback: str,
    ) -> str:
        """
        İyileştirme için kullanıcı prompt'u oluştur.

        Önceki geri bildirimi net bir şekilde aktararak
        agent'ın somut iyileştirmeler yapmasını sağlar.
        """
        parts = [
            f"Konu: {getattr(research_output, 'topic', 'Bilinmeyen Konu')}",
            "",
            "Araştırma Özeti:",
            truncate_text(getattr(research_output, "summary", ""), max_length=800),
            "",
            "─" * 40,
            "GERİ BİLDİRİM (bu sorunları düzelt):",
            feedback,
            "─" * 40,
            "",
            "Yukarıdaki geri bildirimleri dikkate alarak makaleyi baştan yaz. "
            "Eleştirilerde belirtilen sorunları düzelt, güçlü yanları koru. "
            "Makale Türkçe olmalı ve Markdown formatında olmalıdır."
        ]

        return "\n".join(parts)

    def _extract_title(self, content: str) -> str:
        """
        Makale içeriğinden başlığı çıkar.

        Markdown'da başlık genellikle ilk satırda # ile başlar.
        Bulamazsa varsayılan bir başlık döndürür.
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line.lstrip("# ").strip()
            elif line.startswith("## ") and not line.startswith("### "):
                return line.lstrip("## ").strip()
        return "Başlıksız Makale"

    def _mock_article(self, topic: str, is_revision: bool) -> str:
        """
        Demo mod için mock makale üret.

        API key olmadan pipeline'ı test edebilmek için
        gerçekçi bir makale yapısı üretir.
        """
        version_note = " (İyileştirilmiş)" if is_revision else ""

        return (
            f"# {topic}: Kapsamlı Bir İnceleme{version_note}\n\n"
            f"## Yapay Zekanın Yeni Sınırları\n\n"
            f"### Giriş\n\n"
            f"{topic} konusu, teknoloji dünyasında hızla önem kazanan bir alan. "
            f"Bu makalede, konunun temellerinden ileri düzey uygulamalarına kadar "
            f"kapsamlı bir inceleme sunuyoruz.\n\n"
            f"Günümüzde yapay zeka sistemleri, basit soru-cevap modellerinden "
            f"otonom karar verebilen agent'lara doğru evrilmekte. Bu evrim, "
            f"sadece teknoloji meraklılarını değil, tüm sektörleri etkileyen "
            f"köklü bir dönüşümü temsil ediyor.\n\n"
            f"### 1. Temel Kavramlar\n\n"
            f"{topic} alanını anlamak için önce temel kavramları netleştirmemiz gerekiyor. "
            f"Agent (ajan) kavramı, otonom hareket edebilen bir yazılım varlığını ifade eder. "
            f"Bu agent'lar, verilen bir görevi tamamlamak için kendi başlarına plan yapar, "
            f"araçları kullanır ve sonuçları değerlendirir.\n\n"
            f"Temel bileşenler şunlardır:\n"
            f"- **Agent Döngüsü**: Düşün → Plan → Çalıştır → Gözlemle\n"
            f"- **Tool Kullanımı**: API'ler, veritabanları ve dosya sistemleri ile etkileşim\n"
            f"- **Hafıza Yönetimi**: Kısa vadeli (bağlam) ve uzun vadeli (veritabanı) bilgi depolama\n\n"
            f"### 2. MCP Protokolü\n\n"
            f"Model Context Protocol (MCP), agent'ların araçlarla standart bir şekilde "
            f"iletişim kurmasını sağlayan bir protokoldür. Tıpkı HTTP'nin web için "
            f"bir standart olması gibi, MCP de agent-tool iletişimi için bir standart sunar.\n\n"
            f"MCP'nin avantajları:\n"
            f"- Araç keşfi (tool discovery)\n"
            f"- Standart şema tanımları\n"
            f"- Güvenlik ve yetkilendirme\n"
            f"- Versiyon yönetimi\n\n"
            f"### 3. Çoklu Agent Sistemleri\n\n"
            f"Tek bir agent'ın yapamadığını, birden fazla agent bir arada yapabilir. "
            f"Çoklu agent sistemlerinde her agent belirli bir role sahiptir: "
            f"araştırmacı, yazar, eleştirmen, editör gibi.\n\n"
            f"Bu sistemlerin en büyük avantajı, karmaşık görevleri paralel olarak "
            f"işleyebilmeleri ve birbirlerinin çıktılarını iyileştirebilmeleridir.\n\n"
            f"### 4. Production Zorlukları\n\n"
            f"Bir agent sistemini prototipten production'a taşımak ciddi mühendislik "
            f"zorlukları içerir:\n\n"
            f"- **Maliyet Kontrolü**: Her LLM çağrısı para, kontrol mekanizması şart\n"
            f"- **Güvenilirlik**: API hataları, timeout'lar, bozuk çıktılar\n"
            f"- **Gözlemlenebilirlik**: Her adımın loglanması ve izlenebilmesi\n"
            f"- **Kalite Güvencesi**: Hallüsinasyon tespiti ve reflection döngüleri\n\n"
            f"### Sonuç\n\n"
            f"{topic} alanı, yazılım mühendisliğinin geleceğini şekillendiren "
            f"en heyecan verici disiplinlerden biri. Bu makalede ele aldığımız "
            f"temel kavramlar, protokoller ve mimari kalıplar, bu alanda sağlam "
            f"bir temel oluşturmanızı sağlayacaktır.\n\n"
            f"Bir sonraki adım olarak, kendi çoklu agent sisteminizi tasarlamayı "
            f"ve TwinGraph Studio gibi production-grade bir pipeline kurmayı denemenizi öneriyoruz.\n\n"
            f"### Kaynakça\n\n"
            f"1. {topic} - Kapsamlı Rehber (example.com)\n"
            f"2. {topic}: Güncel Gelişmeler 2025 (example.com)\n"
            f"3. Production-Grade {topic} Sistemleri (example.com)\n"
        )


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    import asyncio
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.research_agent import ResearchOutput, Citation

    async def test_writing():
        """
        WritingAgent'ı bağımsız test et.

        Bu test:
        1. Mock araştırma verisi oluşturur
        2. İlk taslağı üretir
        3. Geri bildirimle iyileştirilmiş taslağı üretir
        """
        print("=" * 50)
        print("🧪 WritingAgent Test")
        print("=" * 50)

        # Mock araştırma verisi
        research = ResearchOutput(
            topic="Agentic AI ve MCP Protokolü",
            sources=[{"title": "Test Kaynak", "url": "https://example.com"}],
            summary="Agentic AI, otonom karar verebilen yapay zeka sistemlerini kapsar. "
                    "MCP protokolü ise agent-tool iletişimini standardize eder.",
            citations=[
                Citation(
                    source="https://example.com",
                    title="Agentic AI Rehberi",
                    key_point="Agent döngüsü ve tool kullanımı temel kavramlardır."
                ),
            ],
            token_count=100,
        )

        agent = WritingAgent()

        # İlk taslak
        print("\n--- İlk Taslak ---")
        draft_v1 = await agent.write_article(research)
        print(f"Başlık: {draft_v1.title}")
        print(f"Kelime: {draft_v1.word_count}")
        print(f"Versiyon: {draft_v1.version}")
        print(f"Token: {draft_v1.token_count}")
        print(f"İlk 300 karakter:\n{draft_v1.content[:300]}")

        # Geri bildirimle iyileştirme
        print("\n--- İyileştirilmiş Taslak ---")
        draft_v2 = await agent.write_article(
            research,
            feedback="Giriş bölümü daha güçlü olmalı. Somut örnekler ekle."
        )
        print(f"Başlık: {draft_v2.title}")
        print(f"Kelime: {draft_v2.word_count}")
        print(f"Versiyon: {draft_v2.version}")
        print(f"Token: {draft_v2.token_count}")

    asyncio.run(test_writing())
