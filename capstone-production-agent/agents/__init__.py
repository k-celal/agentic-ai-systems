"""
TwinGraph Studio - Agent Modülü
==================================
Production-Ready Agentic Content & Research Orchestrator

Bu modül, TwinGraph Studio'nun çekirdek agent'larını içerir.
Her agent belirli bir sorumluluğa sahiptir ve birlikte
uçtan uca bir içerik üretim pipeline'ı oluşturur.

Agent'lar ve Sorumlulukları:
-----------------------------
1. OrchestratorAgent  → Pipeline koordinatörü (tüm akışı yönetir)
2. ResearchAgent      → Derin araştırma (kaynak toplama ve özetleme)
3. WritingAgent       → İçerik üretici (Medium makalesi yazma)
4. ReflectionAgent    → Kalite eleştirmeni (5 boyutlu değerlendirme)
5. RepurposeAgent     → Format dönüştürücü (LinkedIn postu üretme)
6. CostGuardAgent     → Maliyet bekçisi (bütçe koruma ve model yönlendirme)

Pipeline Akışı:
    Kullanıcı → Orchestrator → Research → Writing → Reflection
                                              ↕ (döngü)
                                          Repurpose → Çıktı

    Her adımda CostGuard bütçe kontrolü yapar.

Veri Sınıfları:
    - ResearchOutput  → Araştırma sonucu
    - Citation        → Kaynakça kaydı
    - ArticleDraft    → Makale taslağı
    - ReflectionResult → Değerlendirme sonucu
    - LinkedInPost    → LinkedIn postu
    - AgentMessage    → Agent arası mesaj
    - PipelineState   → Pipeline durumu
    - PipelineResult  → Pipeline nihai sonucu

Kullanım:
    from agents import OrchestratorAgent

    orchestrator = OrchestratorAgent(budget_limit=0.50)
    result = await orchestrator.run_pipeline("Agentic AI ve MCP")

    print(result.final_article)
    print(result.linkedin_post)
    print(result.cost_report)
"""

# ── Agent Sınıfları ──
from agents.orchestrator import OrchestratorAgent
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from agents.reflection_agent import ReflectionAgent
from agents.repurpose_agent import RepurposeAgent
from agents.cost_guard_agent import CostGuardAgent

# ── Veri Sınıfları ──
from agents.orchestrator import AgentMessage, PipelineState, PipelineResult
from agents.research_agent import ResearchOutput, Citation
from agents.writing_agent import ArticleDraft
from agents.reflection_agent import ReflectionResult
from agents.repurpose_agent import LinkedInPost

# ── Dışa aktarılan isimler ──
__all__ = [
    # Agent'lar
    "OrchestratorAgent",
    "ResearchAgent",
    "WritingAgent",
    "ReflectionAgent",
    "RepurposeAgent",
    "CostGuardAgent",
    # Veri sınıfları
    "AgentMessage",
    "PipelineState",
    "PipelineResult",
    "ResearchOutput",
    "Citation",
    "ArticleDraft",
    "ReflectionResult",
    "LinkedInPost",
]
