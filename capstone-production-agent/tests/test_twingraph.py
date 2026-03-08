"""
TwinGraph Studio — Kapsamlı Test Paketi
=========================================
Tüm bileşenlerin doğru çalıştığını doğrulayan testler.

Kapsam:
    - GraphStore: Düğüm/kenar oluşturma, sorgulama, ilişkili kavramlar
    - VectorStore: Belge ekleme, benzerlik araması, ön-doldurma
    - ContentIngester: Varlık çıkarma, yükleme
    - DeepResearch: Arama, bulanık eşleme
    - ContentSave: Kaydetme, okuma
    - EvalTool: Yazı değerlendirmesi
    - CitationVerify: Kaynak doğrulama
    - CostReport: Maliyet raporu
    - WritingEvaluator: (evals modülü)
    - CostEvaluator: (evals modülü)
    - ModelRouter: Model yönlendirme
    - CostGuardAgent: Bütçe kontrolü, kullanım kaydı, yönlendirme

Çalıştırma:
    cd capstone-production-agent
    python -m pytest tests/test_twingraph.py -v
"""

import os
import sys
import pytest

# === Proje kök dizinini ve capstone dizinini path'e ekle ===
CAPSTONE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(CAPSTONE_DIR)
sys.path.insert(0, CAPSTONE_DIR)
sys.path.insert(0, PROJECT_ROOT)


# ═══════════════════════════════════════════════════════════════
#  TEST: GraphStore
# ═══════════════════════════════════════════════════════════════

class TestGraphStore:
    """GraphStore (kavram grafı) testleri."""

    def setup_method(self):
        """Her test öncesi temiz bir GraphStore oluştur."""
        from memory.graph_store import GraphStore
        self.store = GraphStore(pre_populate=False)

    def test_add_node_returns_id(self):
        """Düğüm ekleme geçerli bir ID döndürmelidir."""
        node_id = self.store.add_node("Test Kavram", "concept")
        assert node_id is not None
        assert len(node_id) > 0
        assert node_id in self.store.nodes

    def test_add_node_duplicate_returns_same_id(self):
        """Aynı etiketle eklenen düğüm, mevcut ID'yi döndürmelidir."""
        id1 = self.store.add_node("MCP", "technology")
        id2 = self.store.add_node("MCP", "technology")
        assert id1 == id2

    def test_add_node_with_properties(self):
        """Düğüm özellikleri doğru kaydedilmelidir."""
        node_id = self.store.add_node(
            "Python", "technology",
            {"açıklama": "Programlama dili", "versiyon": "3.12"},
        )
        node = self.store.nodes[node_id]
        assert node.label == "Python"
        assert node.entity_type == "technology"
        assert node.properties["açıklama"] == "Programlama dili"

    def test_add_edge_returns_id(self):
        """Kenar ekleme geçerli bir ID döndürmelidir."""
        id_a = self.store.add_node("A", "concept")
        id_b = self.store.add_node("B", "concept")
        edge_id = self.store.add_edge(id_a, id_b, "related_to")
        assert edge_id is not None
        assert len(edge_id) > 0

    def test_add_edge_invalid_source_returns_empty(self):
        """Geçersiz kaynak düğüm ile kenar eklemek boş string döndürmelidir."""
        id_b = self.store.add_node("B", "concept")
        edge_id = self.store.add_edge("gecersiz_id", id_b, "related_to")
        assert edge_id == ""

    def test_query_existing_concept(self):
        """Mevcut kavram sorgusu 'found: True' döndürmelidir."""
        self.store.add_node("LLM", "technology")
        result = self.store.query("LLM")
        assert result["found"] is True
        assert result["node"]["label"] == "LLM"

    def test_query_nonexistent_concept(self):
        """Var olmayan kavram sorgusu 'found: False' döndürmelidir."""
        result = self.store.query("YokOlanKavram12345")
        assert result["found"] is False
        assert result["related_nodes"] == []

    def test_get_related_concepts(self):
        """İlişkili kavramlar doğru döndürülmelidir."""
        id_a = self.store.add_node("AI Agent", "concept")
        id_b = self.store.add_node("LLM", "technology")
        id_c = self.store.add_node("Tool Calling", "concept")
        self.store.add_edge(id_a, id_b, "uses")
        self.store.add_edge(id_a, id_c, "uses")

        related = self.store.get_related_concepts("AI Agent")
        labels = [r["label"] for r in related]
        assert "LLM" in labels
        assert "Tool Calling" in labels

    def test_pre_populated_data_exists(self):
        """Ön-doldurulmuş veri yüklenmiş olmalıdır."""
        from memory.graph_store import GraphStore
        full_store = GraphStore(pre_populate=True)
        stats = full_store.get_stats()
        assert stats["total_nodes"] >= 50
        assert stats["total_edges"] >= 60


# ═══════════════════════════════════════════════════════════════
#  TEST: VectorStore
# ═══════════════════════════════════════════════════════════════

class TestVectorStore:
    """VectorStore (vektör deposu) testleri."""

    def setup_method(self):
        """Her test öncesi temiz bir VectorStore oluştur."""
        from memory.vector_store import VectorStore
        self.store = VectorStore(pre_populate=False)

    def test_add_document_returns_id(self):
        """Belge ekleme geçerli bir ID döndürmelidir."""
        doc_id = self.store.add_document("Test belge içeriği burada.")
        assert doc_id is not None
        assert len(doc_id) > 0

    def test_add_document_with_metadata(self):
        """Metadata doğru kaydedilmelidir."""
        doc_id = self.store.add_document(
            "MCP protokolü hakkında bilgi.",
            {"konu": "MCP", "kaynak": "test"},
        )
        doc = self.store.get_document(doc_id)
        assert doc is not None
        assert doc["metadata"]["konu"] == "MCP"

    def test_search_returns_relevant_results(self):
        """Arama, en alakalı belgeleri döndürmelidir."""
        self.store.add_document(
            "Yapay zeka ajanları otonom görevleri tamamlar",
            {"konu": "AI"},
        )
        self.store.add_document(
            "Python programlama dili web geliştirme için kullanılır",
            {"konu": "Python"},
        )
        self.store.add_document(
            "AI agent tool calling ile araçlara erişir",
            {"konu": "AI"},
        )

        results = self.store.search("yapay zeka agent otonom", top_k=2)
        assert len(results) > 0
        # En yüksek skorlu sonuç AI ile ilgili olmalı
        top_doc, top_score = results[0]
        assert top_score > 0
        assert "AI" in top_doc["metadata"].get("konu", "") or "agent" in top_doc["content"].lower()

    def test_search_with_metadata_filter(self):
        """Metadata filtresi ile arama çalışmalıdır."""
        self.store.add_document("AI agent araştırma yapar", {"konu": "AI"})
        self.store.add_document("Python güçlü bir dildir", {"konu": "Python"})

        results = self.store.search(
            "agent araştırma",
            metadata_filter={"konu": "AI"},
        )
        for doc, _ in results:
            assert doc["metadata"]["konu"] == "AI"

    def test_pre_populated_data_exists(self):
        """Ön-doldurulmuş veri yüklenmiş olmalıdır."""
        from memory.vector_store import VectorStore
        full_store = VectorStore(pre_populate=True)
        stats = full_store.get_stats()
        assert stats["total_documents"] >= 30


# ═══════════════════════════════════════════════════════════════
#  TEST: ContentIngester
# ═══════════════════════════════════════════════════════════════

class TestContentIngester:
    """ContentIngester (içerik yükleme) testleri."""

    def setup_method(self):
        """Her test öncesi temiz hafıza sistemi oluştur."""
        from memory.graph_store import GraphStore
        from memory.vector_store import VectorStore
        from memory.ingestion import ContentIngester

        self.graph = GraphStore(pre_populate=False)
        self.vector = VectorStore(pre_populate=False)
        self.ingester = ContentIngester(self.graph, self.vector)

    def test_extract_entities_finds_known_terms(self):
        """Bilinen teknoloji terimleri doğru çıkarılmalıdır."""
        text = "MCP protokolü, LLM tabanlı agent'ların tool calling yapmasını sağlar."
        entities = self.ingester.extract_entities(text)
        entity_texts = [e[0].lower() for e in entities]
        assert any("mcp" in t for t in entity_texts)
        assert any("llm" in t for t in entity_texts)

    def test_ingest_adds_to_stores(self):
        """İçerik yükleme, hem grafa hem vektör deposuna eklemelidir."""
        content = (
            "MCP (Model Context Protocol), Anthropic tarafından geliştirilmiş "
            "açık bir iletişim protokolüdür. LLM tabanlı agent'ların harici "
            "araçlara erişmesini standartlaştırır."
        )
        result = self.ingester.ingest(content, "test_kaynak")
        assert result.documents_added >= 1
        assert result.source_name == "test_kaynak"
        assert len(self.vector.documents) >= 1

    def test_ingest_empty_content(self):
        """Boş içerik yükleme, sıfır sonuç döndürmelidir."""
        result = self.ingester.ingest("", "bos_kaynak")
        assert result.documents_added == 0
        assert result.nodes_added == 0


# ═══════════════════════════════════════════════════════════════
#  TEST: DeepResearch (MCP Tool)
# ═══════════════════════════════════════════════════════════════

class TestDeepResearch:
    """deep_research.search aracı testleri."""

    def test_search_returns_results(self):
        """Arama sonuçları döndürmelidir."""
        from mcp.tools.deep_research import search

        result = search("yapay zeka ajanları", max_results=5)
        assert result["total_results"] > 0
        assert result["returned"] > 0
        assert len(result["results"]) > 0

    def test_search_results_have_required_fields(self):
        """Her sonuçta gerekli alanlar bulunmalıdır."""
        from mcp.tools.deep_research import search

        result = search("MCP protokolü", max_results=3)
        for item in result["results"]:
            assert "title" in item
            assert "source_url" in item
            assert "summary" in item
            assert "relevance_score" in item
            assert 0.0 <= item["relevance_score"] <= 1.0

    def test_search_fuzzy_matching(self):
        """Bulanık eşleme ile farklı sorgularda sonuç bulunmalıdır."""
        from mcp.tools.deep_research import search

        result_tr = search("yapay zeka ajan", max_results=3)
        result_en = search("AI agent tool", max_results=3)
        # Her iki dilde de sonuç dönmeli
        assert result_tr["total_results"] > 0
        assert result_en["total_results"] > 0


# ═══════════════════════════════════════════════════════════════
#  TEST: ContentSave (MCP Tool)
# ═══════════════════════════════════════════════════════════════

class TestContentSave:
    """content_save aracı testleri."""

    def test_save_and_read_content(self):
        """İçerik kaydedilip okunabilmelidir."""
        from mcp.tools.content_save import save_content, read_content, SAVED_CONTENTS

        # Temiz başla
        SAVED_CONTENTS.clear()

        save_result = save_content("test.md", "# Test Başlık\nİçerik burada.", "markdown")
        assert save_result["status"] == "created"
        assert save_result["filename"] == "test.md"

        read_result = read_content("test.md")
        assert read_result["found"] is True
        assert "# Test Başlık" in read_result["content"]

    def test_save_updates_version(self):
        """Aynı dosya adıyla tekrar kaydetme, versiyonu artırmalıdır."""
        from mcp.tools.content_save import save_content, SAVED_CONTENTS

        SAVED_CONTENTS.clear()

        save_content("rapor.txt", "Versiyon 1", "text")
        result = save_content("rapor.txt", "Versiyon 2", "text")
        assert result["status"] == "updated"
        assert result["version"] == 2

    def test_read_nonexistent_file(self):
        """Var olmayan dosya okuma 'found: False' döndürmelidir."""
        from mcp.tools.content_save import read_content, SAVED_CONTENTS

        SAVED_CONTENTS.clear()

        result = read_content("yok_dosya.txt")
        assert result["found"] is False


# ═══════════════════════════════════════════════════════════════
#  TEST: EvalTool (MCP Tool)
# ═══════════════════════════════════════════════════════════════

class TestEvalTool:
    """eval_tool (yazı değerlendirme) testleri."""

    def test_evaluate_writing_returns_valid_score(self):
        """Değerlendirme geçerli bir puan döndürmelidir (1-10 arası)."""
        from mcp.tools.eval_tool import evaluate_writing

        uzun_metin = (
            "Yapay zeka ajanları, modern yazılım dünyasının en heyecan verici gelişmelerinden "
            "biridir. Bu ajanlar, belirli görevleri tamamlamak için otonom kararlar alabilir. "
            "LLM tabanlı ajanlar özellikle güçlüdür çünkü doğal dil anlama ve üretme "
            "yeteneklerine sahiptirler.\n\n"
            "Bir ajanın temel bileşenleri şunlardır: algılama, düşünme ve eylem. Algılama "
            "aşamasında ajan kullanıcı girdisini ve çevre bilgisini alır. Düşünme aşamasında "
            "bu bilgiyi işler ve bir plan oluşturur. Eylem aşamasında ise planı uygulamaya "
            "koyar.\n\n"
            "Araç kullanımı, ajanların yeteneklerini büyük ölçüde genişletir. Bir ajan web "
            "araması yapabilir, dosya okuyabilir ve API çağırabilir. MCP protokolü bu araç "
            "kullanımını standartlaştırır.\n\n"
            "Çok ajanlı sistemlerde birden fazla uzman ajan koordineli çalışır. Bir yönetici "
            "ajan görevleri alt ajanlara dağıtır ve sonuçları birleştirir."
        )

        result = evaluate_writing(uzun_metin, min_words=50)
        assert 1.0 <= result["score"] <= 10.0
        assert result["grade"] in ["A+", "A", "B", "C", "D", "F"]
        assert "dimensions" in result
        assert "stats" in result

    def test_evaluate_short_text_low_score(self):
        """Kısa metin düşük puan almalıdır."""
        from mcp.tools.eval_tool import evaluate_writing

        result = evaluate_writing("Çok kısa.", min_words=500)
        assert result["score"] < 5.0
        assert len(result["issues"]) > 0


# ═══════════════════════════════════════════════════════════════
#  TEST: CitationVerify (MCP Tool)
# ═══════════════════════════════════════════════════════════════

class TestCitationVerify:
    """citation_verify (kaynak doğrulama) testleri."""

    def test_verify_citations_with_sources(self):
        """Kaynaklarla desteklenen içerik yüksek kapsama puanı almalıdır."""
        from mcp.tools.citation_verify import verify_citations

        content = (
            "Yapay zeka ajanları otonom kararlar alabilen sistemlerdir. "
            "LLM tabanlı ajanlar düşünme ve eylem döngüsünde çalışır. "
            "Araç kullanımı modern ajanların temel yeteneklerinden biridir."
        )
        sources = [
            {
                "title": "AI Agent Rehberi",
                "content": (
                    "Yapay zeka ajanları otonom kararlar alabilen yazılım sistemleridir. "
                    "LLM tabanlı ajanlar düşünme eylem döngüsünde çalışır. "
                    "Araç kullanımı temel yetenektir."
                ),
            },
        ]

        result = verify_citations(content, sources)
        assert result["coverage_score"] > 0
        assert result["total_claims"] > 0
        assert len(result["verified_claims"]) >= 0

    def test_verify_citations_empty_sources(self):
        """Boş kaynak listesi ile kapsama puanı 0 olmalıdır."""
        from mcp.tools.citation_verify import verify_citations

        result = verify_citations("Test içerik cümlesi burada.", [])
        assert result["coverage_score"] == 0


# ═══════════════════════════════════════════════════════════════
#  TEST: CostReport (MCP Tool)
# ═══════════════════════════════════════════════════════════════

class TestCostReport:
    """cost_report (maliyet raporu) testleri."""

    def test_generate_cost_report(self):
        """Maliyet raporu doğru hesaplanmalıdır."""
        from mcp.tools.cost_report import generate_cost_report

        records = [
            {
                "agent": "researcher",
                "model": "gpt-4o-mini",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cost": 0.00045,
                "output_words": 100,
            },
            {
                "agent": "writer",
                "model": "gpt-4o",
                "input_tokens": 2000,
                "output_tokens": 1500,
                "cost": 0.02,
                "output_words": 300,
            },
        ]

        report = generate_cost_report(records)
        assert report["total_cost"] > 0
        assert report["total_calls"] == 2
        assert report["total_input_tokens"] == 3000
        assert report["total_output_tokens"] == 2000
        assert "researcher" in report["per_agent_cost"]
        assert "writer" in report["per_agent_cost"]
        assert "gpt-4o-mini" in report["per_model_cost"]
        assert "gpt-4o" in report["per_model_cost"]

    def test_generate_cost_report_empty(self):
        """Boş kayıt listesi ile rapor sıfır değerler döndürmelidir."""
        from mcp.tools.cost_report import generate_cost_report

        report = generate_cost_report([])
        assert report["total_cost"] == 0.0
        assert report["total_calls"] == 0


# ═══════════════════════════════════════════════════════════════
#  TEST: WritingEvaluator (evals modülü)
#  NOT: evals/writing_eval.py ve evals/cost_eval.py henüz
#  oluşturulmamışsa, bu testler mevcut eval_tool'u kullanır.
# ═══════════════════════════════════════════════════════════════

class TestWritingEvaluator:
    """Yazı değerlendirme testleri (eval_tool üzerinden)."""

    def test_evaluate_and_compare_versions(self):
        """İki versiyon karşılaştırıldığında, iyileştirilmiş sürüm daha yüksek puan almalıdır."""
        from mcp.tools.eval_tool import evaluate_writing

        v1 = "Kısa metin. Az bilgi. Yetersiz."

        v2 = (
            "Yapay zeka ajanları, belirli görevleri tamamlamak için otonom kararlar "
            "alabilen yazılım sistemleridir. Bu ajanlar algılama, düşünme ve eylem "
            "döngüsünde çalışır.\n\n"
            "Araç kullanımı, ajanların yeteneklerini büyük ölçüde genişletir. Bir ajan "
            "web araması yapabilir, dosya okuyabilir ve API'leri çağırabilir. MCP "
            "protokolü bu araç kullanımını standartlaştırır.\n\n"
            "Çok ajanlı sistemlerde birden fazla uzman ajan koordineli çalışır. "
            "Bir yönetici ajan görevleri dağıtır ve sonuçları birleştirir."
        )

        score_v1 = evaluate_writing(v1, min_words=50)["score"]
        score_v2 = evaluate_writing(v2, min_words=50)["score"]
        assert score_v2 > score_v1

    def test_evaluate_returns_dimensions(self):
        """Değerlendirme sonucunda tüm boyutlar bulunmalıdır."""
        from mcp.tools.eval_tool import evaluate_writing

        result = evaluate_writing(
            "Bir test metni. Bu metin değerlendirme için yazılmıştır. "
            "Yeterince uzun olmalı.",
            min_words=10,
        )
        dims = result["dimensions"]
        assert "word_count" in dims
        assert "sentence_variety" in dims
        assert "paragraph_structure" in dims
        assert "keyword_density" in dims
        assert "readability" in dims


# ═══════════════════════════════════════════════════════════════
#  TEST: CostEvaluator (evals modülü)
#  NOT: Maliyet değerlendirmesi cost_report üzerinden simüle edilir.
# ═══════════════════════════════════════════════════════════════

class TestCostEvaluator:
    """Maliyet değerlendirme testleri (cost_report üzerinden)."""

    def test_evaluate_cost_efficiency(self):
        """Maliyet verimliliği metrikleri hesaplanabilmelidir."""
        from mcp.tools.cost_report import generate_cost_report

        records = [
            {
                "agent": "writer",
                "model": "gpt-4o",
                "input_tokens": 2000,
                "output_tokens": 1500,
                "cost": 0.02,
                "output_words": 400,
            },
        ]

        report = generate_cost_report(records)
        # Kelime başına maliyet hesaplanmalı
        assert report["cost_per_word"] > 0
        # Optimizasyon önerileri olmalı
        assert len(report["optimization_suggestions"]) > 0


# ═══════════════════════════════════════════════════════════════
#  TEST: ModelRouter (CostGuard üzerinden)
# ═══════════════════════════════════════════════════════════════

class TestModelRouter:
    """Model yönlendirme testleri (CostGuardAgent üzerinden)."""

    def setup_method(self):
        """Her test öncesi CostGuardAgent oluştur."""
        from agents.cost_guard_agent import CostGuardAgent
        self.guard = CostGuardAgent(budget_limit=1.0)

    def test_route_planning_to_cheap_model(self):
        """Planlama görevleri ucuz modele yönlendirilmelidir."""
        model = self.guard.get_routing_recommendation("planning")
        assert model == "gpt-4o-mini"

    def test_route_final_writing_to_expensive_model(self):
        """Final yazım görevleri güçlü modele yönlendirilmelidir."""
        model = self.guard.get_routing_recommendation("final_writing")
        assert model == "gpt-4o"

    def test_route_research_to_cheap_model(self):
        """Araştırma görevleri ucuz modele yönlendirilmelidir."""
        model = self.guard.get_routing_recommendation("research")
        assert model == "gpt-4o-mini"

    def test_route_unknown_task_to_default(self):
        """Bilinmeyen görev tipi varsayılan modele yönlendirilmelidir."""
        model = self.guard.get_routing_recommendation("bilinmeyen_gorev")
        assert model == "gpt-4o-mini"

    def test_route_different_task_types(self):
        """Farklı görev tipleri doğru modellere yönlendirilmelidir."""
        routing_map = {
            "orchestration": "gpt-4o-mini",
            "research": "gpt-4o-mini",
            "summarization": "gpt-4o-mini",
            "final_writing": "gpt-4o",
            "creative_writing": "gpt-4o",
            "reflection": "gpt-4o-mini",
            "evaluation": "gpt-4o-mini",
            "repurpose": "gpt-4o-mini",
        }
        for task_type, expected_model in routing_map.items():
            model = self.guard.get_routing_recommendation(task_type)
            assert model == expected_model, (
                f"Görev '{task_type}' için beklenen '{expected_model}', "
                f"alınan '{model}'"
            )


# ═══════════════════════════════════════════════════════════════
#  TEST: CostGuardAgent
# ═══════════════════════════════════════════════════════════════

class TestCostGuardAgent:
    """CostGuardAgent (maliyet bekçisi) testleri."""

    def setup_method(self):
        """Her test öncesi düşük bütçeli CostGuardAgent oluştur."""
        from agents.cost_guard_agent import CostGuardAgent
        self.guard = CostGuardAgent(
            budget_limit=0.01,
            warning_threshold=0.80,
            per_step_limit=5000,
        )

    def test_can_proceed_initial(self):
        """Başlangıçta bütçe mevcut olmalı ve devam edilebilmelidir."""
        assert self.guard.can_proceed(estimated_tokens=1000) is True

    def test_can_proceed_exceeds_step_limit(self):
        """Adım limitini aşan token tahmini reddedilmelidir."""
        assert self.guard.can_proceed(estimated_tokens=10000) is False

    def test_record_usage_returns_cost(self):
        """Kullanım kaydı maliyet değeri döndürmelidir."""
        cost = self.guard.record_usage(
            agent_name="test_agent",
            input_tokens=500,
            output_tokens=300,
            model="gpt-4o-mini",
        )
        assert cost >= 0
        assert self.guard.total_cost > 0

    def test_record_usage_tracks_agent(self):
        """Kullanım kaydı agent bazında takip edilmelidir."""
        self.guard.record_usage("agent_a", 100, 100, "gpt-4o-mini")
        self.guard.record_usage("agent_b", 200, 200, "gpt-4o")
        self.guard.record_usage("agent_a", 150, 150, "gpt-4o-mini")

        report = self.guard.get_report()
        assert "agent_a" in report
        assert "agent_b" in report

    def test_get_routing_recommendation(self):
        """Model yönlendirme önerisi döndürmelidir."""
        model = self.guard.get_routing_recommendation("final_writing")
        assert model in ["gpt-4o", "gpt-4o-mini"]

    def test_budget_tracking_after_usage(self):
        """Kullanım sonrası bütçe doğru güncellenmeli."""
        initial_remaining = self.guard.remaining_budget
        self.guard.record_usage("test", 500, 500, "gpt-4o-mini")
        assert self.guard.remaining_budget < initial_remaining


# ═══════════════════════════════════════════════════════════════
#  Ana çalıştırma
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
