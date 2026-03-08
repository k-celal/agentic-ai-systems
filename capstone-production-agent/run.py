#!/usr/bin/env python3
"""
TwinGraph Studio — Ana Giriş Noktası
=======================================
Production-Ready Agentic Content & Research Orchestrator

Bu dosya, TwinGraph Studio capstone projesinin ana çalıştırma noktasıdır.
Tüm bileşenleri bir araya getirerek uçtan uca demo pipeline'ını çalıştırır.

Pipeline Akışı:
    1. Hafıza Sistemi → GraphRAG + VectorStore yükleme
    2. Deep Research  → Derin araştırma (MCP tool'ları ile)
    3. Makale Yazımı  → Taslak oluşturma (WritingAgent)
    4. Reflection     → Kalite kontrolü ve iyileştirme döngüsü
    5. LinkedIn Post  → İçerik dönüştürme (RepurposeAgent)
    6. Sonuç Raporu   → Kalite puanı, maliyet raporu, çıktılar

Kullanım:
    # Varsayılan konu ile çalıştır
    python run.py

    # Özel konu ile çalıştır
    python run.py --topic "GraphRAG ve Bilgi Grafileri"

Not:
    API key olmadan da çalışır (demo mod).
    Demo modda tüm agent'lar mock veri üretir.
"""

import os
import sys
import time
import asyncio
import argparse

# ============================================================
# Import Yolları
# ============================================================
# capstone-production-agent/ dizinini sys.path'e ekle
CAPSTONE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CAPSTONE_DIR)

# Workspace kökünü (agentic-ai-systems/) sys.path'e ekle
WORKSPACE_DIR = os.path.dirname(CAPSTONE_DIR)
sys.path.insert(0, WORKSPACE_DIR)


# ============================================================
# Güvenli Import'lar
# ============================================================
# Her import try/except ile korunur, böylece eksik bileşenler
# tüm pipeline'ı çökertmez.

def _safe_import(module_path: str, class_name: str, description: str):
    """
    Güvenli import yardımcısı.

    Import başarısız olursa None döndürür ve uyarı mesajı yazdırır.
    Bu sayede eksik bir bileşen tüm pipeline'ı engellemez.
    """
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"  ⚠️  {description} yüklenemedi: {e}")
        return None


# ── Shared Modüller ──
try:
    from shared.telemetry.logger import get_logger
    from shared.telemetry.cost_tracker import CostTracker, MODEL_PRICING
    _shared_available = True
except ImportError as e:
    print(f"⚠️  Shared modül yüklenemedi: {e}")
    print("   shared/ dizininin doğru konumda olduğundan emin olun.")
    _shared_available = False

    # Fallback logger
    class _FallbackLogger:
        def info(self, msg): print(f"  [INFO] {msg}")
        def warning(self, msg): print(f"  [WARN] {msg}")
        def error(self, msg): print(f"  [ERROR] {msg}")
        def debug(self, msg): pass

    def get_logger(name): return _FallbackLogger()

# ── MCP Sunucusu ──
create_server = _safe_import("mcp.server", "create_server", "MCP Sunucusu")

# ── Hafıza Sistemi ──
GraphStore = _safe_import("memory.graph_store", "GraphStore", "Graph Store")
VectorStore = _safe_import("memory.vector_store", "VectorStore", "Vector Store")

# ── Agent'lar ──
OrchestratorAgent = _safe_import("agents.orchestrator", "OrchestratorAgent", "Orchestrator Agent")
ResearchAgent = _safe_import("agents.research_agent", "ResearchAgent", "Research Agent")
WritingAgent = _safe_import("agents.writing_agent", "WritingAgent", "Writing Agent")
ReflectionAgent = _safe_import("agents.reflection_agent", "ReflectionAgent", "Reflection Agent")
RepurposeAgent = _safe_import("agents.repurpose_agent", "RepurposeAgent", "Repurpose Agent")
CostGuardAgent = _safe_import("agents.cost_guard_agent", "CostGuardAgent", "Cost Guard Agent")

# ── Veri Sınıfları ──
ResearchOutput = _safe_import("agents.research_agent", "ResearchOutput", "ResearchOutput")
ArticleDraft = _safe_import("agents.writing_agent", "ArticleDraft", "ArticleDraft")
ReflectionResult = _safe_import("agents.reflection_agent", "ReflectionResult", "ReflectionResult")
LinkedInPost = _safe_import("agents.repurpose_agent", "LinkedInPost", "LinkedInPost")

# ── Evaluation ──
WritingEvaluator = _safe_import("evals.writing_eval", "WritingEvaluator", "Writing Evaluator")
CostEvaluator = _safe_import("evals.cost_eval", "CostEvaluator", "Cost Evaluator")

# ── Routing ──
TwinGraphModelRouter = _safe_import("routing.model_router", "TwinGraphModelRouter", "Model Router")

# ── MCP Tools ──
save_content_fn = None
try:
    from mcp.tools.content_save import save_content
    save_content_fn = save_content
except ImportError:
    pass


# ============================================================
# Terminal Çıktı Yardımcıları
# ============================================================

def _header():
    """Ana başlık banner'ı yazdır."""
    print()
    print("═" * 56)
    print("🧠 TwinGraph Studio — Agentic Content Orchestrator")
    print("═" * 56)


def _step(num: int, title: str):
    """Adım başlığı yazdır."""
    print(f"\n─── Adım {num}: {title} ───")


def _footer():
    """Kapanış banner'ı yazdır."""
    print()
    print("═" * 56)


def _info(icon: str, message: str):
    """Bilgi satırı yazdır."""
    print(f"{icon} {message}")


# ============================================================
# Pipeline Fonksiyonları (Fallback — Bileşen Bazlı)
# ============================================================

async def _run_fallback_pipeline(topic: str, logger) -> dict:
    """
    Orchestrator import'u başarısız olduğunda, her bileşeni
    ayrı ayrı çalıştıran fallback pipeline.

    Bu mod, eksik bağımlılıklar olsa bile demo çalıştırmaya
    imkan tanır.
    """
    logger.info("Fallback mod: Bileşenler ayrı ayrı çalıştırılıyor")
    results = {
        "success": False,
        "topic": topic,
        "article": "",
        "linkedin": "",
        "total_tokens": 0,
        "total_cost": 0.0,
        "reflection_loops": 0,
        "final_score": 0.0,
    }

    # ── Adım 1: Araştırma ──
    _step(2, "Deep Research")
    if ResearchAgent:
        try:
            research_agent = ResearchAgent(model="gpt-4o-mini", temperature=0.3)
            _info("🔍", "Araştırma başlıyor...")
            research_output = await research_agent.research(topic=topic)
            source_count = len(getattr(research_output, "sources", []))
            token_count = getattr(research_output, "token_count", 0)
            results["total_tokens"] += token_count
            _info("📄", f"{source_count} kaynak bulundu")
            _info("📝", "Özet hazırlandı")
        except Exception as e:
            logger.error(f"Araştırma hatası: {e}")
            _info("❌", f"Araştırma hatası: {e}")
            research_output = None
    else:
        _info("⚠️", "ResearchAgent kullanılamıyor, atlanıyor")
        research_output = None

    # ── Adım 2: Yazım ──
    _step(3, "Makale Yazımı")
    article_content = ""
    article_word_count = 0

    if WritingAgent and research_output:
        try:
            writing_agent = WritingAgent(model="gpt-4o", temperature=0.8)
            _info("✍️", "Taslak v1 oluşturuluyor...")
            draft = await writing_agent.write_article(research_output=research_output)
            article_content = getattr(draft, "content", "")
            article_word_count = getattr(draft, "word_count", len(article_content.split()))
            token_count = getattr(draft, "token_count", 0)
            results["total_tokens"] += token_count
            results["article"] = article_content
            _info("📄", f"{article_word_count} kelime yazıldı")
        except Exception as e:
            logger.error(f"Yazım hatası: {e}")
            _info("❌", f"Yazım hatası: {e}")
    else:
        _info("⚠️", "WritingAgent kullanılamıyor veya araştırma yok, atlanıyor")

    # ── Adım 3: Reflection ──
    _step(4, "Reflection")
    if ReflectionAgent and article_content and research_output:
        try:
            reflection_agent = ReflectionAgent(model="gpt-4o-mini", temperature=0.2)
            _info("🪞", "Kalite kontrolü...")
            reflection_result = await reflection_agent.reflect(
                draft=draft if 'draft' in dir() else type('D', (), {'content': article_content, 'title': '', 'word_count': article_word_count, 'version': 1})(),
                research_output=research_output,
                threshold=7.0,
            )
            score = getattr(reflection_result, "overall_score", 0.0)
            is_acceptable = getattr(reflection_result, "is_acceptable", False)
            token_count = getattr(reflection_result, "token_count", 0)
            results["total_tokens"] += token_count
            results["final_score"] = score
            results["reflection_loops"] = 1

            grade = "A+" if score >= 9 else "A" if score >= 8 else "B" if score >= 7 else "C" if score >= 6 else "D" if score >= 5 else "F"
            _info("📊", f"Puan: {score}/10 | {grade}")

            if not is_acceptable:
                _info("🔄", "İyileştirme gerekli, tekrar yazılıyor...")
                # İkinci yazım denemesi
                if WritingAgent:
                    try:
                        feedback = reflection_agent.format_feedback(reflection_result)
                        draft_v2 = await writing_agent.write_article(
                            research_output=research_output,
                            feedback=feedback,
                        )
                        article_content = getattr(draft_v2, "content", article_content)
                        article_word_count = getattr(draft_v2, "word_count", article_word_count)
                        results["article"] = article_content
                        results["total_tokens"] += getattr(draft_v2, "token_count", 0)

                        # İkinci reflection
                        reflection_v2 = await reflection_agent.reflect(
                            draft=draft_v2,
                            research_output=research_output,
                            threshold=7.0,
                        )
                        score_v2 = getattr(reflection_v2, "overall_score", score)
                        results["final_score"] = score_v2
                        results["reflection_loops"] = 2
                        results["total_tokens"] += getattr(reflection_v2, "token_count", 0)

                        grade_v2 = "A+" if score_v2 >= 9 else "A" if score_v2 >= 8 else "B" if score_v2 >= 7 else "C" if score_v2 >= 6 else "D" if score_v2 >= 5 else "F"
                        _info("📊", f"Yeni Puan: {score_v2}/10 | {grade_v2}")
                    except Exception as e:
                        logger.error(f"İyileştirme hatası: {e}")
            else:
                _info("✅", "Makale kabul edildi!")
        except Exception as e:
            logger.error(f"Reflection hatası: {e}")
            _info("❌", f"Reflection hatası: {e}")
    else:
        _info("⚠️", "ReflectionAgent kullanılamıyor, atlanıyor")

    # ── Adım 4: LinkedIn ──
    _step(5, "LinkedIn Post")
    if RepurposeAgent and article_content:
        try:
            repurpose_agent = RepurposeAgent(model="gpt-4o-mini", temperature=0.7)
            _info("📱", "Dönüştürülüyor...")
            linkedin_post = await repurpose_agent.repurpose_to_linkedin(
                article_content=article_content,
                topic=topic,
            )
            linkedin_text = getattr(linkedin_post, "full_text", "")
            linkedin_word_count = getattr(linkedin_post, "word_count", len(linkedin_text.split()))
            results["linkedin"] = linkedin_text
            results["total_tokens"] += getattr(linkedin_post, "token_count", 0)
            _info("✅", f"{linkedin_word_count} kelime")
        except Exception as e:
            logger.error(f"LinkedIn hatası: {e}")
            _info("❌", f"LinkedIn hatası: {e}")
    else:
        _info("⚠️", "RepurposeAgent kullanılamıyor, atlanıyor")

    results["success"] = bool(article_content)
    return results


# ============================================================
# Ana Pipeline Fonksiyonu
# ============================================================

async def main():
    """
    TwinGraph Studio ana pipeline fonksiyonu.

    Adımlar:
    1. Argümanları parse et
    2. Hafıza sistemini yükle
    3. MCP sunucusunu başlat
    4. Pipeline'ı çalıştır (orchestrator veya fallback)
    5. Değerlendirme yap (evals)
    6. Sonuç raporunu yazdır
    7. Çıktıları kaydet
    """
    # ── Argüman parse ──
    parser = argparse.ArgumentParser(
        description="TwinGraph Studio — Agentic Content Orchestrator"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Agentic AI ve MCP",
        help="İçerik konusu (varsayılan: 'Agentic AI ve MCP')",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=1.0,
        help="Bütçe limiti USD (varsayılan: 1.0)",
    )
    args = parser.parse_args()

    topic = args.topic
    budget = args.budget

    logger = get_logger("twingraph_studio")
    pipeline_start = time.time()

    # ════════════════════════════════════════════════════════
    # BAŞLIK
    # ════════════════════════════════════════════════════════
    _header()
    _info("📋", f"Konu: {topic}")

    # ════════════════════════════════════════════════════════
    # ADIM 1: HAFIZA SİSTEMİ
    # ════════════════════════════════════════════════════════
    _step(1, "Hafıza Sistemi")

    graph_store = None
    vector_store = None
    graph_stats = {"total_nodes": 0, "total_edges": 0}
    vector_doc_count = 0

    if GraphStore:
        try:
            graph_store = GraphStore(pre_populate=True)
            graph_stats = graph_store.get_stats()
            _info("🧠", f"GraphRAG: {graph_stats['total_nodes']} kavram, {graph_stats['total_edges']} ilişki yüklendi")
        except Exception as e:
            logger.error(f"GraphStore hatası: {e}")
            _info("⚠️", f"GraphStore yüklenemedi: {e}")
    else:
        _info("⚠️", "GraphStore kullanılamıyor")

    if VectorStore:
        try:
            vector_store = VectorStore(pre_populate=True)
            vector_doc_count = len(vector_store.documents)
            _info("📚", f"Vector Store: {vector_doc_count} döküman hazır")
        except Exception as e:
            logger.error(f"VectorStore hatası: {e}")
            _info("⚠️", f"VectorStore yüklenemedi: {e}")
    else:
        _info("⚠️", "VectorStore kullanılamıyor")

    # ── Hafızadan bağlam çek ──
    memory_context = None
    if graph_store:
        try:
            query_result = graph_store.query(topic.split()[0] if topic else "AI")
            if query_result.get("found"):
                related = query_result.get("related_nodes", [])
                if related:
                    concepts = [r["label"] for r in related[:10]]
                    memory_context = (
                        f"GraphRAG Bağlamı — '{topic}' ile ilişkili kavramlar:\n"
                        + ", ".join(concepts)
                    )
        except Exception as e:
            logger.warning(f"Graf sorgusu hatası: {e}")

    # ── MCP Sunucusu ──
    mcp_server = None
    tools_dict = None
    if create_server:
        try:
            mcp_server = create_server()
            # Tool fonksiyonlarını dict olarak hazırla (ResearchAgent için)
            # Not: MCP server'ın tool'ları senkron çalışır, async wrapper gerekebilir
        except Exception as e:
            logger.warning(f"MCP sunucusu başlatılamadı: {e}")

    # ════════════════════════════════════════════════════════
    # PIPELINE ÇALIŞTIR
    # ════════════════════════════════════════════════════════

    pipeline_result = None
    fallback_result = None

    if OrchestratorAgent:
        # ── Orchestrator ile çalıştır ──
        try:
            orchestrator = OrchestratorAgent(
                budget_limit=budget,
                reflection_threshold=7.0,
                max_reflection_loops=3,
            )

            # Adımları terminal'e yazdır
            _step(2, "Deep Research")
            _info("🔍", "Araştırma başlıyor...")

            pipeline_result = await orchestrator.run_pipeline(
                topic=topic,
                tools_dict=tools_dict,
                memory_context=memory_context,
            )

            # Orchestrator kendi loglamasını yapıyor, burada özeti göster
            if pipeline_result:
                state = getattr(pipeline_result, "state", None)

                # Research özeti
                if state and state.research_output:
                    source_count = len(state.research_output.sources)
                    _info("📄", f"{source_count} kaynak bulundu")
                    _info("📝", "Özet hazırlandı")

                # Writing özeti
                _step(3, "Makale Yazımı")
                if state and state.draft_versions:
                    first_draft = state.draft_versions[0]
                    _info("✍️", f"Taslak v1 oluşturuluyor...")
                    _info("📄", f"{first_draft.word_count} kelime yazıldı")

                # Reflection özeti
                _step(4, "Reflection")
                if state and state.reflection_scores:
                    _info("🪞", "Kalite kontrolü...")
                    for i, score in enumerate(state.reflection_scores):
                        grade = "A+" if score >= 9 else "A" if score >= 8 else "B" if score >= 7 else "C" if score >= 6 else "D" if score >= 5 else "F"
                        _info("📊", f"Puan: {score}/10 | {grade}")
                        if i < len(state.reflection_scores) - 1:
                            _info("🔄", "İyileştirme gerekli, tekrar yazılıyor...")
                    if pipeline_result.final_score >= 7.0:
                        _info("✅", "Makale kabul edildi!")

                # LinkedIn özeti
                _step(5, "LinkedIn Post")
                if state and state.linkedin_post:
                    _info("📱", "Dönüştürülüyor...")
                    _info("✅", f"{state.linkedin_post.word_count} kelime")
                else:
                    _info("⚠️", "LinkedIn postu oluşturulamadı")

        except Exception as e:
            logger.error(f"Orchestrator hatası: {e}")
            _info("❌", f"Orchestrator hatası: {e}")
            _info("🔄", "Fallback moda geçiliyor...")
            fallback_result = await _run_fallback_pipeline(topic, logger)
    else:
        # ── Fallback: Bileşen bazlı çalıştır ──
        _info("⚠️", "Orchestrator kullanılamıyor — fallback mod aktif")
        fallback_result = await _run_fallback_pipeline(topic, logger)

    # ════════════════════════════════════════════════════════
    # SONUÇLARI TOPLA
    # ════════════════════════════════════════════════════════

    pipeline_end = time.time()
    duration = pipeline_end - pipeline_start

    # Sonuç verilerini normalize et
    if pipeline_result:
        final_article = pipeline_result.final_article or ""
        linkedin_post = pipeline_result.linkedin_post or ""
        total_tokens = pipeline_result.total_tokens
        total_cost = pipeline_result.total_cost
        reflection_loops = pipeline_result.reflection_loops
        final_score = pipeline_result.final_score
        success = pipeline_result.success
        cost_report = pipeline_result.cost_report
    elif fallback_result:
        final_article = fallback_result.get("article", "")
        linkedin_post = fallback_result.get("linkedin", "")
        total_tokens = fallback_result.get("total_tokens", 0)
        total_cost = fallback_result.get("total_cost", 0.0)
        reflection_loops = fallback_result.get("reflection_loops", 0)
        final_score = fallback_result.get("final_score", 0.0)
        success = fallback_result.get("success", False)
        cost_report = ""
    else:
        final_article = ""
        linkedin_post = ""
        total_tokens = 0
        total_cost = 0.0
        reflection_loops = 0
        final_score = 0.0
        success = False
        cost_report = ""

    article_word_count = len(final_article.split()) if final_article else 0

    # ════════════════════════════════════════════════════════
    # ADIM 6: DEĞERLENDİRME ve SONUÇ RAPORU
    # ════════════════════════════════════════════════════════
    _step(6, "Sonuç Raporu")

    # ── Yazı kalitesi değerlendirmesi ──
    eval_score = final_score
    eval_grade = "N/A"
    if WritingEvaluator and final_article:
        try:
            writing_eval = WritingEvaluator()
            eval_result = writing_eval.evaluate(
                final_article,
                sources_used=5,
            )
            eval_score = eval_result.overall_score
            eval_grade = eval_result.grade
            _info("📊", f"Yazı Kalitesi: {eval_score}/10 ({eval_grade})")

            # Boyut detayları
            for dim, score in eval_result.dimension_scores.items():
                bar = "█" * int(score) + "░" * (10 - int(score))
                dim_names = {
                    "coherence": "Tutarlılık",
                    "depth": "Derinlik",
                    "originality": "Özgünlük",
                    "structure": "Yapı",
                    "citations": "Kaynakça",
                }
                dim_label = dim_names.get(dim, dim)
                print(f"   {dim_label:12s} {bar} {score:.1f}")
        except Exception as e:
            logger.warning(f"Yazı değerlendirme hatası: {e}")
            _info("📊", f"Yazı Kalitesi: {final_score}/10")
    else:
        _info("📊", f"Yazı Kalitesi: {final_score}/10")

    # ── Maliyet değerlendirmesi ──
    if CostEvaluator and total_tokens > 0:
        try:
            cost_eval = CostEvaluator()
            cost_result = cost_eval.evaluate(
                total_tokens=total_tokens,
                total_cost=total_cost,
                word_count=article_word_count,
                reflection_improvement=final_score - 5.4 if reflection_loops > 0 else 0,
                num_reflection_loops=reflection_loops,
            )
            _info("💰", f"Toplam Maliyet: ${total_cost:.6f} (Not: {cost_result.efficiency_grade})")

            # Baseline karşılaştırma
            baseline = cost_eval.compare_with_baseline(cost_result)
            if baseline["savings"] > 0:
                _info("💡", f"Model yönlendirme tasarrufu: ${baseline['savings']:.6f} (%{baseline['savings_percent']:.0f})")
        except Exception as e:
            logger.warning(f"Maliyet değerlendirme hatası: {e}")
            _info("💰", f"Toplam Maliyet: ${total_cost:.6f}")
    else:
        _info("💰", f"Toplam Maliyet: ${total_cost:.6f}")

    _info("⏱️", f"Toplam Süre: {duration:.1f}s")

    # ── Model yönlendirme raporu ──
    if TwinGraphModelRouter:
        try:
            router = TwinGraphModelRouter()
            usage_log = [
                {"task": "research",   "tokens": total_tokens // 5,     "model": "gpt-4o-mini"},
                {"task": "writing",    "tokens": total_tokens * 2 // 5, "model": "gpt-4o"},
                {"task": "reflection", "tokens": total_tokens // 5,     "model": "gpt-4o-mini"},
                {"task": "repurpose",  "tokens": total_tokens // 5,     "model": "gpt-4o-mini"},
            ]
            # Raporu logla ama terminale basma (çıktıyı temiz tut)
            savings_report = router.get_savings_report(usage_log)
            logger.info(savings_report)
        except Exception as e:
            logger.warning(f"Router raporu hatası: {e}")

    # ── Çıktıları kaydet ──
    saved_files = []
    if save_content_fn:
        try:
            if final_article:
                result = save_content_fn(
                    filename=f"makale_{topic.replace(' ', '_')[:30]}.md",
                    content=final_article,
                    content_type="markdown",
                )
                if result.get("status") == "saved":
                    saved_files.append(result.get("filename", "makale.md"))

            if linkedin_post:
                result = save_content_fn(
                    filename=f"linkedin_{topic.replace(' ', '_')[:30]}.txt",
                    content=linkedin_post,
                    content_type="text",
                )
                if result.get("status") == "saved":
                    saved_files.append(result.get("filename", "linkedin.txt"))
        except Exception as e:
            logger.warning(f"İçerik kaydetme hatası: {e}")

    if saved_files:
        _info("📄", f"Çıktılar kaydedildi: {', '.join(saved_files)}")
    else:
        _info("📄", "Çıktılar bellekte mevcut (kayıt aracı kullanılamadı)")

    # ── Maliyet raporu (Orchestrator'dan) ──
    if cost_report:
        logger.info(cost_report)

    # ── Agent bazlı maliyet dağılımı ──
    if pipeline_result and hasattr(pipeline_result, "state") and pipeline_result.state:
        state = pipeline_result.state
        if state.messages:
            print(f"\n  📋 Agent Aktivite Özeti:")
            agents_seen = set()
            for msg in state.messages:
                agent = msg.sender
                if agent not in agents_seen and agent != "orchestrator":
                    agents_seen.add(agent)
                    token_info = msg.metadata.get("token_count", msg.metadata.get("word_count", "?"))
                    print(f"     {agent:20s} | {msg.content[:50]}")

    _footer()

    # ── Başarı/başarısızlık özeti ──
    if success:
        print(f"✅ Pipeline başarıyla tamamlandı!")
        if final_article:
            print(f"   Makale: {article_word_count} kelime")
        if linkedin_post:
            print(f"   LinkedIn: {len(linkedin_post.split())} kelime")
    else:
        print(f"⚠️  Pipeline kısmen tamamlandı veya hatalarla karşılaştı.")
        print(f"   API key yoksa bu normal — demo mod çalışmaktadır.")

    print()


# ============================================================
# Giriş Noktası
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  İptal edildi (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
