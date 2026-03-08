"""
Orchestrator Agent - Pipeline Koordinatörü
=============================================
Tüm agent'ları yöneten ve pipeline'ı uçtan uca çalıştıran ana koordinatör.

NEDEN BU AGENT VAR?
--------------------
Çoklu agent sistemlerinde en büyük sorun koordinasyondur:
- Hangi agent ne zaman çalışacak?
- Agent'lar arası veri nasıl aktarılacak?
- Bir adım başarısız olursa ne olacak?
- Bütçe kontrolü her adımda nasıl yapılacak?
- Reflection döngüsü kaç kez tekrarlanacak?

OrchestratorAgent, tüm bu soruları cevaplayan merkezi koordinatördür.

Pipeline Akışı:
    1. Kullanıcı → Konu verir
    2. CostGuard → Bütçe kontrolü
    3. ResearchAgent → Derin araştırma
    4. CostGuard → Bütçe kontrolü
    5. WritingAgent → İlk taslak (v1)
    6. CostGuard → Bütçe kontrolü
    7. ReflectionAgent → Kalite değerlendirmesi
       ↓ Puan < eşik? → WritingAgent'a geri bildirim → 5'e dön (maks 3 döngü)
       ↓ Puan ≥ eşik? → Devam et
    8. CostGuard → Bütçe kontrolü
    9. RepurposeAgent → LinkedIn postu
    10. CostGuard → Son rapor

Agent Mesajlaşma:
    Her agent arası iletişim AgentMessage formatında yapılır:
    - sender: Gönderen agent
    - receiver: Alıcı agent
    - content: Mesaj içeriği
    - metadata: Ek bilgiler (token, versiyon, puan vb.)

Kullanım:
    from agents.orchestrator import OrchestratorAgent

    orchestrator = OrchestratorAgent(budget_limit=0.50)
    result = await orchestrator.run_pipeline("Agentic AI ve MCP Protokolü")

    print(result.final_article)
    print(result.linkedin_post)
    print(f"Toplam maliyet: ${result.total_cost:.6f}")
"""

import os
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger, AgentTracer
from shared.utils.helpers import truncate_text

# ============================================================
# Agent import'ları
# ============================================================
from agents.research_agent import ResearchAgent, ResearchOutput
from agents.writing_agent import WritingAgent, ArticleDraft
from agents.reflection_agent import ReflectionAgent, ReflectionResult
from agents.repurpose_agent import RepurposeAgent, LinkedInPost
from agents.cost_guard_agent import CostGuardAgent


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class AgentMessage:
    """
    Agent'lar arası mesajı temsil eder.

    Çoklu agent sistemlerinde, agent'ların birbirleriyle
    iletişim kurması gerekir. Bu sınıf, her mesajı
    standart bir formatta tutar.

    Neden yapılandırılmış mesaj?
    - Gönderen/alıcı takibi
    - Mesaj geçmişi loglama
    - Debug kolaylığı
    - Metadata ile ek bilgi taşıma

    Alanlar:
        sender: Gönderen agent'ın adı
        receiver: Alıcı agent'ın adı
        content: Mesaj içeriği (metin veya serileştirilmiş veri)
        metadata: Ek bilgiler (token sayısı, versiyon, puan vb.)
    """
    sender: str                                         # Gönderen agent
    receiver: str                                       # Alıcı agent
    content: str                                        # Mesaj içeriği
    metadata: dict[str, Any] = field(default_factory=dict)  # Ek bilgiler
    timestamp: datetime = field(default_factory=datetime.now)  # Zaman damgası


@dataclass
class PipelineState:
    """
    Pipeline'ın anlık durumunu tutan sınıf.

    Pipeline boyunca her adımın çıktısı burada saklanır.
    Bu sayede:
    - Herhangi bir noktada durumu inceleyebilirsiniz
    - Hata durumunda kaldığınız yerden devam edebilirsiniz
    - Son rapor için tüm verilere erişebilirsiniz

    Alanlar:
        topic: Pipeline konusu
        research_output: Araştırma sonucu
        draft_versions: Makale taslak versiyonları
        reflection_scores: Her reflection döngüsünün puanları
        final_article: Son kabul edilen makale
        linkedin_post: Üretilen LinkedIn postu
        total_tokens: Toplam kullanılan token
        total_cost: Toplam maliyet (USD)
        messages: Tüm agent mesajları (debug için)
    """
    topic: str = ""                                                  # Pipeline konusu
    research_output: Optional[ResearchOutput] = None                 # Araştırma sonucu
    draft_versions: list[ArticleDraft] = field(default_factory=list) # Taslak versiyonları
    reflection_scores: list[float] = field(default_factory=list)     # Reflection puanları
    final_article: Optional[ArticleDraft] = None                     # Son makale
    linkedin_post: Optional[LinkedInPost] = None                     # LinkedIn postu
    total_tokens: int = 0                                            # Toplam token
    total_cost: float = 0.0                                          # Toplam maliyet
    messages: list[AgentMessage] = field(default_factory=list)       # Agent mesajları
    start_time: Optional[datetime] = None                            # Başlangıç zamanı
    end_time: Optional[datetime] = None                              # Bitiş zamanı


@dataclass
class PipelineResult:
    """
    Pipeline'ın nihai sonucunu temsil eder.

    Bu sınıf, pipeline tamamlandığında kullanıcıya döndürülen
    tüm çıktıları içerir.

    Alanlar:
        success: Pipeline başarılı mı?
        topic: İşlenen konu
        final_article: Son makale metni
        linkedin_post: LinkedIn postu metni
        total_tokens: Toplam kullanılan token
        total_cost: Toplam maliyet
        reflection_loops: Kaç reflection döngüsü yapıldı?
        final_score: Son kabul edilen makale puanı
        duration_seconds: Pipeline süresi (saniye)
        cost_report: Detaylı maliyet raporu
        state: Tam pipeline durumu (debug için)
    """
    success: bool = False                               # Pipeline başarılı mı?
    topic: str = ""                                     # İşlenen konu
    final_article: str = ""                             # Son makale metni
    linkedin_post: str = ""                             # LinkedIn postu
    total_tokens: int = 0                               # Toplam token
    total_cost: float = 0.0                             # Toplam maliyet
    reflection_loops: int = 0                           # Reflection döngü sayısı
    final_score: float = 0.0                            # Son makale puanı
    duration_seconds: float = 0.0                       # Pipeline süresi
    cost_report: str = ""                               # Detaylı maliyet raporu
    state: Optional[PipelineState] = None               # Tam durum


# ============================================================
# OrchestratorAgent Sınıfı
# ============================================================

class OrchestratorAgent:
    """
    Pipeline Koordinatörü - Tüm agent'ları yöneten merkezi agent.

    Bu agent:
    1. Alt agent'ları oluşturur ve yapılandırır
    2. Pipeline adımlarını sırayla çalıştırır
    3. Agent'lar arası veri akışını yönetir
    4. Her adımda bütçe kontrolü yapar
    5. Reflection döngüsünü kontrol eder (maks 3)
    6. Detaylı loglama ve raporlama yapar

    Parametreler:
        budget_limit: Toplam pipeline bütçesi (USD)
        reflection_threshold: Makale kabul eşiği (1-10)
        max_reflection_loops: Maksimum reflection döngü sayısı

    Kullanım:
        orchestrator = OrchestratorAgent(
            budget_limit=0.50,
            reflection_threshold=7.0,
            max_reflection_loops=3,
        )

        result = await orchestrator.run_pipeline(
            topic="Agentic AI ve MCP Protokolü"
        )

        if result.success:
            print(result.final_article)
            print(result.linkedin_post)
        print(result.cost_report)
    """

    def __init__(
        self,
        budget_limit: float = 1.0,
        reflection_threshold: float = 7.0,
        max_reflection_loops: int = 3,
    ):
        """
        OrchestratorAgent'ı başlat.

        Alt agent'lar burada oluşturulur. Her agent,
        CostGuardAgent'ın model yönlendirme önerisine göre
        yapılandırılır.

        Parametreler:
            budget_limit: Toplam bütçe (USD). Pipeline bu bütçeyi aşamaz.
            reflection_threshold: Makale kalite eşiği (1-10).
                                  Bu değerin altındaki makaleler reddedilir.
            max_reflection_loops: Maksimum reflection döngüsü.
                                  Sonsuz döngüyü engeller.
        """
        self._logger = get_logger("orchestrator")
        self._tracer = AgentTracer("orchestrator")

        # Yapılandırma
        self._reflection_threshold = reflection_threshold
        self._max_reflection_loops = max_reflection_loops

        # ── Alt Agent'ları Oluştur ──
        # CostGuard önce oluşturulur çünkü model yönlendirmesi için gerekli
        self._cost_guard = CostGuardAgent(
            budget_limit=budget_limit,
            warning_threshold=0.80,
            per_step_limit=5000,
        )

        # Her agent, görev tipine uygun model ile oluşturulur
        self._research_agent = ResearchAgent(
            model=self._cost_guard.get_routing_recommendation("research"),
            temperature=0.3,
        )
        self._writing_agent = WritingAgent(
            model=self._cost_guard.get_routing_recommendation("final_writing"),
            temperature=0.8,
        )
        self._reflection_agent = ReflectionAgent(
            model=self._cost_guard.get_routing_recommendation("reflection"),
            temperature=0.2,
        )
        self._repurpose_agent = RepurposeAgent(
            model=self._cost_guard.get_routing_recommendation("repurpose"),
            temperature=0.7,
        )

        self._logger.info(
            f"OrchestratorAgent başlatıldı | "
            f"Bütçe: ${budget_limit:.4f} | "
            f"Reflection eşiği: {reflection_threshold} | "
            f"Maks döngü: {max_reflection_loops}"
        )

    async def run_pipeline(
        self,
        topic: str,
        tools_dict: Optional[dict[str, Any]] = None,
        memory_context: Optional[str] = None,
    ) -> PipelineResult:
        """
        Tam pipeline'ı çalıştır: Araştırma → Yazım → Reflection → Dönüştürme.

        Bu metod, pipeline'ın tüm adımlarını sırayla çalıştırır ve
        her adımda bütçe kontrolü yapar.

        Parametreler:
            topic: İçerik konusu
                   Örnek: "Agentic AI ve MCP Protokolü"
            tools_dict: MCP tool fonksiyonları (isteğe bağlı)
                        ResearchAgent'a iletilir.
            memory_context: GraphRAG'dan gelen ek bağlam (isteğe bağlı)
                           WritingAgent'a iletilir.

        Döndürür:
            PipelineResult: Pipeline sonucu

        Örnek:
            result = await orchestrator.run_pipeline("Agentic AI ve MCP")

            if result.success:
                # Makaleyi kaydet
                with open("article.md", "w") as f:
                    f.write(result.final_article)
                # LinkedIn postunu kaydet
                with open("linkedin.txt", "w") as f:
                    f.write(result.linkedin_post)

            print(result.cost_report)
        """
        self._tracer.start_task(f"Pipeline: {topic}")
        self._logger.info("=" * 60)
        self._logger.info(f"🚀 Pipeline başlatılıyor | Konu: {topic}")
        self._logger.info("=" * 60)

        # Pipeline durumunu başlat
        state = PipelineState(
            topic=topic,
            start_time=datetime.now(),
        )

        try:
            # ════════════════════════════════════════
            # ADIM 1: ARAŞTIRMA
            # ════════════════════════════════════════
            self._logger.info("─" * 40)
            self._logger.info("📚 ADIM 1: Araştırma")
            self._logger.info("─" * 40)

            if not self._cost_guard.can_proceed(estimated_tokens=2000):
                return self._create_budget_error_result(state, "Araştırma adımı")

            research_output = await self._research_agent.research(
                topic=topic,
                tools_dict=tools_dict,
            )
            state.research_output = research_output

            # Kullanım kaydet
            self._cost_guard.record_usage(
                agent_name="research_agent",
                input_tokens=research_output.token_count // 2,
                output_tokens=research_output.token_count // 2,
                model=self._cost_guard.get_routing_recommendation("research"),
            )
            state.total_tokens += research_output.token_count

            # Agent mesajı kaydet
            state.messages.append(AgentMessage(
                sender="orchestrator",
                receiver="research_agent",
                content=f"Araştırma tamamlandı: {len(research_output.sources)} kaynak",
                metadata={"token_count": research_output.token_count},
            ))

            self._logger.info(
                f"✅ Araştırma tamamlandı | "
                f"Kaynak: {len(research_output.sources)} | "
                f"Kaynakça: {len(research_output.citations)} | "
                f"Token: {research_output.token_count}"
            )

            # ════════════════════════════════════════
            # ADIM 2: YAZIM + REFLECTION DÖNGÜSÜ
            # ════════════════════════════════════════
            self._logger.info("─" * 40)
            self._logger.info("✍️  ADIM 2: Yazım & Reflection Döngüsü")
            self._logger.info("─" * 40)

            current_draft: Optional[ArticleDraft] = None
            current_feedback: Optional[str] = None
            reflection_loop_count = 0

            for loop_idx in range(self._max_reflection_loops + 1):
                # ── 2a: Yazım ──
                if not self._cost_guard.can_proceed(estimated_tokens=3000):
                    self._logger.warning("Bütçe limiti! Yazım adımı atlanıyor.")
                    break

                self._logger.info(
                    f"  ✏️  Taslak v{loop_idx + 1} "
                    f"{'oluşturuluyor' if loop_idx == 0 else 'iyileştiriliyor'}..."
                )

                current_draft = await self._writing_agent.write_article(
                    research_output=research_output,
                    memory_context=memory_context,
                    feedback=current_feedback,
                )
                state.draft_versions.append(current_draft)

                # Kullanım kaydet
                self._cost_guard.record_usage(
                    agent_name="writing_agent",
                    input_tokens=current_draft.token_count // 2,
                    output_tokens=current_draft.token_count // 2,
                    model=self._cost_guard.get_routing_recommendation("final_writing"),
                )
                state.total_tokens += current_draft.token_count

                state.messages.append(AgentMessage(
                    sender="writing_agent",
                    receiver="orchestrator",
                    content=f"Taslak v{current_draft.version}: {current_draft.word_count} kelime",
                    metadata={
                        "version": current_draft.version,
                        "word_count": current_draft.word_count,
                        "token_count": current_draft.token_count,
                    },
                ))

                self._logger.info(
                    f"  ✅ Taslak v{current_draft.version} hazır | "
                    f"{current_draft.word_count} kelime | {current_draft.token_count} token"
                )

                # ── 2b: Reflection ──
                # Son döngüdeyse reflection yapma (zaten maks döngüye ulaştık)
                if loop_idx >= self._max_reflection_loops:
                    self._logger.info(
                        f"  ⚠️  Maksimum döngü sayısına ({self._max_reflection_loops}) ulaşıldı. "
                        f"Son taslak kabul ediliyor."
                    )
                    break

                if not self._cost_guard.can_proceed(estimated_tokens=1500):
                    self._logger.warning("Bütçe limiti! Reflection adımı atlanıyor.")
                    break

                self._logger.info(f"  🔍 Reflection v{loop_idx + 1}...")

                reflection_result = await self._reflection_agent.reflect(
                    draft=current_draft,
                    research_output=research_output,
                    threshold=self._reflection_threshold,
                )

                # Kullanım kaydet
                self._cost_guard.record_usage(
                    agent_name="reflection_agent",
                    input_tokens=reflection_result.token_count // 2,
                    output_tokens=reflection_result.token_count // 2,
                    model=self._cost_guard.get_routing_recommendation("reflection"),
                )
                state.total_tokens += reflection_result.token_count
                state.reflection_scores.append(reflection_result.overall_score)
                reflection_loop_count += 1

                state.messages.append(AgentMessage(
                    sender="reflection_agent",
                    receiver="orchestrator",
                    content=f"Puan: {reflection_result.overall_score:.1f}/10",
                    metadata={
                        "overall_score": reflection_result.overall_score,
                        "dimension_scores": reflection_result.dimension_scores,
                        "is_acceptable": reflection_result.is_acceptable,
                    },
                ))

                self._logger.info(
                    f"  📊 Puan: {reflection_result.overall_score:.1f}/10 | "
                    f"Kabul: {'✅' if reflection_result.is_acceptable else '❌'}"
                )

                # Kabul edildiyse döngüden çık
                if reflection_result.is_acceptable:
                    self._logger.info("  ✅ Makale kabul edildi! Devam ediliyor.")
                    break

                # Kabul edilmediyse geri bildirim hazırla
                current_feedback = self._reflection_agent.format_feedback(reflection_result)
                self._logger.info(
                    f"  🔄 İyileştirme gerekli. "
                    f"Sorun: {len(reflection_result.issues)} | "
                    f"Öneri: {len(reflection_result.suggestions)}"
                )

                state.messages.append(AgentMessage(
                    sender="orchestrator",
                    receiver="writing_agent",
                    content=f"İyileştirme talebi (döngü {loop_idx + 1})",
                    metadata={"feedback_length": len(current_feedback)},
                ))

            # Son taslağı kaydet
            state.final_article = current_draft

            # ════════════════════════════════════════
            # ADIM 3: DÖNÜŞTÜRME (REPURPOSE)
            # ════════════════════════════════════════
            self._logger.info("─" * 40)
            self._logger.info("🔄 ADIM 3: LinkedIn'e Dönüştürme")
            self._logger.info("─" * 40)

            if current_draft and self._cost_guard.can_proceed(estimated_tokens=1500):
                linkedin_post = await self._repurpose_agent.repurpose_to_linkedin(
                    article_content=current_draft.content,
                    topic=topic,
                )
                state.linkedin_post = linkedin_post

                # Kullanım kaydet
                self._cost_guard.record_usage(
                    agent_name="repurpose_agent",
                    input_tokens=linkedin_post.token_count // 2,
                    output_tokens=linkedin_post.token_count // 2,
                    model=self._cost_guard.get_routing_recommendation("repurpose"),
                )
                state.total_tokens += linkedin_post.token_count

                state.messages.append(AgentMessage(
                    sender="repurpose_agent",
                    receiver="orchestrator",
                    content=f"LinkedIn postu: {linkedin_post.word_count} kelime",
                    metadata={
                        "word_count": linkedin_post.word_count,
                        "token_count": linkedin_post.token_count,
                    },
                ))

                self._logger.info(
                    f"✅ LinkedIn postu hazır | "
                    f"{linkedin_post.word_count} kelime | {linkedin_post.token_count} token"
                )
            else:
                self._logger.warning("LinkedIn dönüştürme atlandı (bütçe limiti veya taslak yok)")

            # ════════════════════════════════════════
            # ADIM 4: SONUÇ ve RAPORLAMA
            # ════════════════════════════════════════
            self._logger.info("─" * 40)
            self._logger.info("📊 ADIM 4: Sonuç Raporu")
            self._logger.info("─" * 40)

            state.end_time = datetime.now()
            state.total_cost = self._cost_guard.total_cost

            duration = (state.end_time - state.start_time).total_seconds()
            cost_report = self._cost_guard.get_report()

            result = PipelineResult(
                success=True,
                topic=topic,
                final_article=current_draft.content if current_draft else "",
                linkedin_post=state.linkedin_post.full_text if state.linkedin_post else "",
                total_tokens=state.total_tokens,
                total_cost=state.total_cost,
                reflection_loops=reflection_loop_count,
                final_score=state.reflection_scores[-1] if state.reflection_scores else 0.0,
                duration_seconds=duration,
                cost_report=cost_report,
                state=state,
            )

            self._logger.info("=" * 60)
            self._logger.info(f"🎉 Pipeline tamamlandı!")
            self._logger.info(f"   Konu:           {topic}")
            self._logger.info(f"   Süre:           {duration:.2f}s")
            self._logger.info(f"   Taslak sayısı:  {len(state.draft_versions)}")
            self._logger.info(f"   Reflection:     {reflection_loop_count} döngü")
            if state.reflection_scores:
                self._logger.info(f"   Son puan:       {state.reflection_scores[-1]:.1f}/10")
            self._logger.info(f"   Toplam token:   {state.total_tokens:,}")
            self._logger.info(f"   Toplam maliyet: ${state.total_cost:.6f}")
            self._logger.info("=" * 60)
            self._logger.info(cost_report)

            self._tracer.end_task(success=True)

            return result

        except Exception as e:
            self._logger.error(f"Pipeline hatası: {e}")
            self._tracer.log_error(str(e))
            self._tracer.end_task(success=False)

            state.end_time = datetime.now()
            duration = (state.end_time - state.start_time).total_seconds()

            return PipelineResult(
                success=False,
                topic=topic,
                total_tokens=state.total_tokens,
                total_cost=self._cost_guard.total_cost,
                duration_seconds=duration,
                cost_report=self._cost_guard.get_report(),
                state=state,
            )

    # ────────────────────────────────────────────────────────
    # Yardımcı Metodlar
    # ────────────────────────────────────────────────────────

    def _create_budget_error_result(
        self,
        state: PipelineState,
        step_name: str,
    ) -> PipelineResult:
        """
        Bütçe aşımı durumunda hata sonucu oluştur.

        Pipeline bütçe limiti nedeniyle erken sonlandırıldığında
        mevcut durumu ve maliyet raporunu içeren sonuç döndürür.
        """
        self._logger.error(
            f"Pipeline durduruluyor: Bütçe limiti! "
            f"Durdurulan adım: {step_name}"
        )
        state.end_time = datetime.now()
        duration = (state.end_time - state.start_time).total_seconds()

        return PipelineResult(
            success=False,
            topic=state.topic,
            total_tokens=state.total_tokens,
            total_cost=self._cost_guard.total_cost,
            duration_seconds=duration,
            cost_report=self._cost_guard.get_report(),
            state=state,
        )


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_pipeline():
        """
        OrchestratorAgent pipeline'ını uçtan uca test et.

        Bu test, tüm agent'ların birlikte çalıştığını doğrular.
        API key yoksa demo modda çalışır.

        Beklenen çıktı:
            [Orchestrator]  Pipeline başlatılıyor...
            [Research]      Deep research çalışıyor... 5 kaynak bulundu
            [Writing]       Taslak v1 oluşturuldu (1,250 kelime)
            [Reflection]    Kalite puanı: 5.4/10 → İyileştirme gerekli
            [Writing]       Taslak v2 oluşturuldu (1,480 kelime)
            [Reflection]    Kalite puanı: 7.8/10 → Kabul edildi ✅
            [Repurpose]     LinkedIn postu oluşturuldu (280 kelime)
            [Cost Guard]    Toplam: 8,420 token | Bütçe: %18 kullanıldı
        """
        print("=" * 60)
        print("🧪 OrchestratorAgent - Pipeline Testi")
        print("=" * 60)

        orchestrator = OrchestratorAgent(
            budget_limit=1.0,
            reflection_threshold=7.0,
            max_reflection_loops=3,
        )

        result = await orchestrator.run_pipeline(
            topic="Agentic AI ve MCP Protokolü"
        )

        print("\n" + "=" * 60)
        print("📋 PIPELINE SONUCU")
        print("=" * 60)
        print(f"Başarılı:        {'✅ Evet' if result.success else '❌ Hayır'}")
        print(f"Konu:            {result.topic}")
        print(f"Süre:            {result.duration_seconds:.2f}s")
        print(f"Reflection:      {result.reflection_loops} döngü")
        print(f"Son Puan:        {result.final_score:.1f}/10")
        print(f"Toplam Token:    {result.total_tokens:,}")
        print(f"Toplam Maliyet:  ${result.total_cost:.6f}")

        if result.final_article:
            print(f"\n📄 Makale (ilk 300 karakter):")
            print(result.final_article[:300])

        if result.linkedin_post:
            print(f"\n💼 LinkedIn Postu (ilk 300 karakter):")
            print(result.linkedin_post[:300])

        print(f"\n{result.cost_report}")

    asyncio.run(test_pipeline())
