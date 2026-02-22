"""
Module 4 Testleri — Evals & Optimization
==========================================
Bu dosya, modüldeki ana bileşenleri test eder:
- E2E Eval Harness
- Planner Eval
- Tool Selection Eval
- CostGuard
- ContextCompressor
- ModelRouter
- TraceCollector

Çalıştırma:
    cd module-04-evals-and-optimization
    python -m pytest tests/ -v

Neden testler önemli?
- Eval sisteminin kendisi de test edilmeli!
- "Eval'i kimin eval eder?" → Unit testler!
- Refactoring sonrası her şeyin çalıştığını doğrular
"""

import sys
import os
import pytest

# shared/ ve modül dosyalarını import edebilmek için path ayarı
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ============================================================
# E2E Eval Testleri
# ============================================================

class TestEvalHarness:
    """E2E değerlendirme çatısını test eder."""

    def test_eval_case_creation(self):
        """EvalCase doğru oluşturuluyor mu?"""
        from evals.e2e import EvalCase

        case = EvalCase(
            id="test_01",
            task="Test görevi",
            expected_tool="search",
            expected_contains=["test"],
            max_loops=3,
            max_cost=0.01,
        )
        assert case.id == "test_01"
        assert case.expected_tool == "search"
        assert len(case.expected_contains) == 1

    def test_eval_result_creation(self):
        """EvalResult doğru oluşturuluyor mu?"""
        from evals.e2e import EvalResult

        result = EvalResult(
            case_id="test_01",
            success=True,
            score=0.95,
            actual_output="Test çıktısı",
            duration=1.5,
            cost=0.003,
        )
        assert result.success is True
        assert result.score == 0.95
        assert result.cost == 0.003

    def test_harness_runs_all_cases(self):
        """Harness tüm vakaları çalıştırıyor mu?"""
        from evals.e2e import EvalHarness, EvalCase

        cases = [
            EvalCase(id="t1", task="test 1"),
            EvalCase(id="t2", task="test 2"),
            EvalCase(id="t3", task="test 3"),
        ]

        harness = EvalHarness()
        results = harness.run_eval(cases)

        # Her vaka için bir sonuç olmalı
        assert len(results) == 3
        assert results[0].case_id == "t1"
        assert results[1].case_id == "t2"
        assert results[2].case_id == "t3"

    def test_harness_with_sample_cases(self):
        """Örnek vakalar çalışıyor mu?"""
        from evals.e2e import EvalHarness, SAMPLE_EVAL_CASES

        harness = EvalHarness()
        results = harness.run_eval(SAMPLE_EVAL_CASES)

        assert len(results) == len(SAMPLE_EVAL_CASES)
        # Simüle edilmiş agent ile en az bazı vakalar başarılı olmalı
        success_count = sum(1 for r in results if r.success)
        assert success_count > 0

    def test_harness_tool_accuracy(self):
        """Tool doğruluğu skora yansıyor mu?"""
        from evals.e2e import EvalHarness, EvalCase

        # Doğru tool seçimi beklenen vaka
        case = EvalCase(
            id="weather",
            task="İstanbul'da hava nasıl?",
            expected_tool="get_weather",
            expected_contains=["İstanbul"],
            max_cost=0.01,
        )

        harness = EvalHarness()
        results = harness.run_eval([case])

        assert len(results) == 1
        assert results[0].score > 0  # En az bazı puan almalı

    def test_harness_handles_agent_error(self):
        """Agent hatası durumunda ne oluyor?"""
        from evals.e2e import EvalHarness, EvalCase

        # Hata fırlatan agent
        def failing_agent(task):
            raise ValueError("Simüle edilmiş hata!")

        case = EvalCase(id="error_test", task="hata ver")
        harness = EvalHarness(agent_runner=failing_agent)
        results = harness.run_eval([case])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].score == 0.0
        assert "hata" in results[0].error.lower() or "Simüle" in results[0].error


# ============================================================
# Planner Eval Testleri
# ============================================================

class TestPlannerEval:
    """Planner değerlendirmesini test eder."""

    def test_planner_eval_runs(self):
        """PlannerEval çalışıyor mu?"""
        from evals.planner_eval import PlannerEval

        evaluator = PlannerEval()
        results = evaluator.run()

        assert len(results) > 0
        assert all(0 <= r.score <= 1 for r in results)

    def test_planner_perfect_match(self):
        """Mükemmel eşleşmede skor 1.0 mı?"""
        from evals.planner_eval import PlannerEval, PlannerTestCase

        # Planner tam olarak beklenen adımları döndürsün
        def perfect_planner(task):
            return ["adım 1", "adım 2", "adım 3"]

        case = PlannerTestCase(
            id="perfect",
            task="test",
            expected_steps=["adım 1", "adım 2", "adım 3"],
        )

        evaluator = PlannerEval(planner_fn=perfect_planner, test_cases=[case])
        results = evaluator.run()

        assert len(results) == 1
        assert results[0].score == 1.0
        assert results[0].matched_steps == 3


# ============================================================
# Tool Selection Eval Testleri
# ============================================================

class TestToolSelectionEval:
    """Tool seçim değerlendirmesini test eder."""

    def test_tool_eval_runs(self):
        """ToolSelectionEval çalışıyor mu?"""
        from evals.tool_eval import ToolSelectionEval

        evaluator = ToolSelectionEval()
        results = evaluator.run()

        assert len(results) > 0

    def test_correct_tool_selection(self):
        """Doğru tool seçiminde correct=True mı?"""
        from evals.tool_eval import ToolSelectionEval, ToolTestCase

        # Her zaman doğru tool döndüren seçici
        def perfect_selector(task):
            return "search"

        case = ToolTestCase(
            id="test",
            task="bilgi ara",
            expected_tool="search",
        )

        evaluator = ToolSelectionEval(
            tool_selector_fn=perfect_selector,
            test_cases=[case],
        )
        results = evaluator.run()

        assert len(results) == 1
        assert results[0].correct is True

    def test_wrong_tool_selection(self):
        """Yanlış tool seçiminde correct=False mı?"""
        from evals.tool_eval import ToolSelectionEval, ToolTestCase

        # Her zaman yanlış tool döndüren seçici
        def wrong_selector(task):
            return "wrong_tool"

        case = ToolTestCase(
            id="test",
            task="bilgi ara",
            expected_tool="search",
        )

        evaluator = ToolSelectionEval(
            tool_selector_fn=wrong_selector,
            test_cases=[case],
        )
        results = evaluator.run()

        assert len(results) == 1
        assert results[0].correct is False

    def test_acceptable_tools(self):
        """Alternatif tool'lar da kabul ediliyor mu?"""
        from evals.tool_eval import ToolTestCase

        case = ToolTestCase(
            id="test",
            task="test",
            expected_tool="search",
            acceptable_tools=["search", "web_search"],
        )

        # expected_tool otomatik eklenmeli
        assert "search" in case.acceptable_tools
        assert "web_search" in case.acceptable_tools


# ============================================================
# CostGuard Testleri
# ============================================================

class TestCostGuard:
    """Maliyet koruyucuyu test eder."""

    def test_initial_state(self):
        """Başlangıç durumu doğru mu?"""
        from optimization.cost_guard import CostGuard

        guard = CostGuard(budget_limit=1.0, per_call_limit=0.10)

        assert guard.can_proceed() is True
        assert guard.budget_limit == 1.0
        assert guard.per_call_limit == 0.10

    def test_budget_exceeded(self):
        """Bütçe aşıldığında can_proceed False dönüyor mu?"""
        from optimization.cost_guard import CostGuard

        # Çok düşük bütçe
        guard = CostGuard(budget_limit=0.0001)

        # Büyük bir çağrı yap
        guard.record_call(input_tokens=10000, output_tokens=5000, model="gpt-4o")

        # Artık devam edemez
        assert guard.can_proceed() is False

    def test_per_call_limit_alert(self):
        """Tek çağrı limiti aşıldığında uyarı veriyor mu?"""
        from optimization.cost_guard import CostGuard

        guard = CostGuard(
            budget_limit=10.0,
            per_call_limit=0.001,  # Çok düşük çağrı limiti
        )

        result = guard.record_call(
            input_tokens=5000,
            output_tokens=2000,
            model="gpt-4o",  # Pahalı model
        )

        # Uyarı verilmeli
        assert result["alert"] is not None
        assert len(guard.alerts) > 0

    def test_warning_threshold(self):
        """Uyarı eşiği doğru çalışıyor mu?"""
        from optimization.cost_guard import CostGuard

        guard = CostGuard(
            budget_limit=0.001,
            warning_threshold=0.50,  # %50'de uyar
        )

        # Bütçenin yarısından fazlasını harca
        guard.record_call(input_tokens=3000, output_tokens=1500, model="gpt-4o-mini")

        # Uyarı eşiğini kontrol et
        usage = guard._tracker.budget_usage_percent()
        # Eğer %50'yi geçtiyse uyarı verilmiş olmalı
        if usage >= 50:
            assert len(guard.alerts) > 0

    def test_reset(self):
        """Reset doğru çalışıyor mu?"""
        from optimization.cost_guard import CostGuard

        guard = CostGuard(budget_limit=1.0)
        guard.record_call(input_tokens=1000, output_tokens=500)

        guard.reset()

        assert guard.can_proceed() is True
        assert guard._tracker.total_cost == 0
        assert len(guard.alerts) == 0

    def test_get_status_returns_string(self):
        """get_status metin döndürüyor mu?"""
        from optimization.cost_guard import CostGuard

        guard = CostGuard(budget_limit=1.0)
        status = guard.get_status()

        assert isinstance(status, str)
        assert "CostGuard" in status


# ============================================================
# ContextCompressor Testleri
# ============================================================

class TestContextCompressor:
    """Bağlam sıkıştırıcıyı test eder."""

    def test_no_compression_needed(self):
        """Limit aşılmıyorsa sıkıştırma yapmamalı."""
        from optimization.context_compress import ContextCompressor

        compressor = ContextCompressor(max_tokens=10000)

        messages = [
            {"role": "system", "content": "Sen bir asistansın."},
            {"role": "user", "content": "Merhaba!"},
        ]

        result = compressor.compress_messages(messages)
        assert len(result) == len(messages)

    def test_truncation_strategy(self):
        """Kırpma stratejisi mesaj sayısını azaltıyor mu?"""
        from optimization.context_compress import ContextCompressor

        compressor = ContextCompressor(
            max_tokens=50,  # Çok düşük limit
            preserve_last=2,
        )

        messages = [
            {"role": "system", "content": "Sen bir asistansın."},
            {"role": "user", "content": "Soru 1: " + "x" * 200},
            {"role": "assistant", "content": "Cevap 1: " + "y" * 200},
            {"role": "user", "content": "Soru 2: " + "x" * 200},
            {"role": "assistant", "content": "Cevap 2: " + "y" * 200},
            {"role": "user", "content": "Son soru"},
        ]

        result = compressor.compress_messages(messages, strategy="truncate")
        assert len(result) < len(messages)

    def test_summarize_strategy(self):
        """Özetleme stratejisi çalışıyor mu?"""
        from optimization.context_compress import ContextCompressor

        compressor = ContextCompressor(
            max_tokens=50,  # Çok düşük limit
            preserve_last=2,
        )

        messages = [
            {"role": "system", "content": "Sen bir asistansın."},
            {"role": "user", "content": "Python nedir? " + "detay " * 50},
            {"role": "assistant", "content": "Python bir programlama dilidir. " + "açıklama " * 50},
            {"role": "user", "content": "Değişken nedir? " + "detay " * 50},
            {"role": "assistant", "content": "Değişken bir veri tutucudur. " + "açıklama " * 50},
            {"role": "user", "content": "Son soru"},
        ]

        result = compressor.compress_messages(messages, strategy="summarize")
        assert len(result) < len(messages)

    def test_estimate_tokens(self):
        """Token tahmini mantıklı mı?"""
        from optimization.context_compress import ContextCompressor

        compressor = ContextCompressor()

        # Boş metin
        assert compressor.estimate_tokens("") == 0

        # Kısa metin
        tokens = compressor.estimate_tokens("Merhaba dünya!")
        assert tokens > 0
        assert tokens < 20

        # Uzun metin
        long_text = "Bu çok uzun bir metin. " * 100
        tokens_long = compressor.estimate_tokens(long_text)
        assert tokens_long > tokens

    def test_compression_stats(self):
        """Sıkıştırma istatistikleri doğru mu?"""
        from optimization.context_compress import ContextCompressor

        compressor = ContextCompressor(max_tokens=50, preserve_last=1)

        original = [
            {"role": "system", "content": "Sistem talimatı " * 20},
            {"role": "user", "content": "Uzun soru " * 50},
            {"role": "assistant", "content": "Uzun cevap " * 50},
            {"role": "user", "content": "Son soru"},
        ]

        compressed = compressor.compress_messages(original, strategy="truncate")
        stats = compressor.get_compression_stats(original, compressed)

        assert stats["original_messages"] == 4
        assert stats["compressed_messages"] < 4
        assert stats["tokens_saved"] > 0
        assert stats["compression_ratio"] > 0


# ============================================================
# ModelRouter Testleri
# ============================================================

class TestModelRouter:
    """Akıllı model yönlendiriciyi test eder."""

    def test_simple_task_routes_to_cheap(self):
        """Basit görev ucuz modele yönlendiriliyor mu?"""
        from optimization.model_router import ModelRouter

        router = ModelRouter()
        model = router.route("Merhaba!")

        assert model == "gpt-4o-mini"

    def test_complex_task_routes_to_expensive(self):
        """Karmaşık görev pahalı modele yönlendiriliyor mu?"""
        from optimization.model_router import ModelRouter

        router = ModelRouter()
        # Çok adımlı, teknik, uzun ve kod içeren görev → yüksek skor bekleniyor
        model = router.route(
            "Bu kodu refactor et, ardından performans analizi yap, "
            "adım adım birim testlerini implement et ve sonra "
            "güvenlik değerlendirmesi yaparak optimize et. "
            "```python\ndef process(data): pass\n```"
        )

        assert model == "gpt-4o"

    def test_complexity_score_nonnegative(self):
        """Karmaşıklık skoru negatif olamaz."""
        from optimization.model_router import ModelRouter

        router = ModelRouter()
        score = router.calculate_complexity("evet")

        assert score >= 0

    def test_route_with_details(self):
        """Detaylı yönlendirme doğru bilgiler döndürüyor mu?"""
        from optimization.model_router import ModelRouter

        router = ModelRouter()
        details = router.route_with_details("Merhaba!")

        assert "model" in details
        assert "complexity_score" in details
        assert "reason" in details
        assert "estimated_cost_ratio" in details

    def test_stats_tracking(self):
        """İstatistikler doğru takip ediliyor mu?"""
        from optimization.model_router import ModelRouter

        router = ModelRouter()
        router.route("Merhaba!")
        router.route("Test")
        router.route("Karmaşık analiz ve refactoring, adım adım mimari tasarla ve debug et")

        stats = router.get_stats()
        assert isinstance(stats, str)
        assert "Toplam Yönlendirme" in stats

    def test_custom_config(self):
        """Özel yapılandırma çalışıyor mu?"""
        from optimization.model_router import ModelRouter, RoutingConfig

        config = RoutingConfig(
            cheap_model="gpt-3.5-turbo",
            expensive_model="gpt-4-turbo",
            complexity_threshold_high=5,
        )

        router = ModelRouter(config=config)
        model = router.route("Merhaba!")

        assert model == "gpt-3.5-turbo"


# ============================================================
# TraceCollector Testleri
# ============================================================

class TestTraceCollector:
    """İzleme toplayıcıyı test eder."""

    def test_basic_trace(self):
        """Temel izleme çalışıyor mu?"""
        from telemetry.traces import TraceCollector

        tracer = TraceCollector(task_name="test_görevi")
        tracer.start()
        tracer.add_step("düşünme", content="Test düşüncesi", tokens=100, cost=0.001)
        tracer.add_step("cevap", content="Test cevabı", tokens=50, cost=0.0005)
        tracer.end(success=True)

        record = tracer.get_record()
        assert record.task_name == "test_görevi"
        assert record.success is True
        assert len(record.steps) == 2
        assert record.total_tokens == 150
        assert record.total_cost == 0.0015

    def test_report_generation(self):
        """Rapor üretimi çalışıyor mu?"""
        from telemetry.traces import TraceCollector

        tracer = TraceCollector(task_name="rapor_testi")
        tracer.start()
        tracer.add_step("düşünme", content="Test", tokens=100, cost=0.001)
        tracer.end(success=True)

        report = tracer.get_report()
        assert isinstance(report, str)
        assert "rapor_testi" in report
        assert "Başarılı" in report

    def test_reset(self):
        """Reset doğru çalışıyor mu?"""
        from telemetry.traces import TraceCollector

        tracer = TraceCollector(task_name="görev_1")
        tracer.start()
        tracer.add_step("düşünme", content="Adım 1")
        tracer.end(success=True)

        tracer.reset("görev_2")
        tracer.start()
        tracer.add_step("cevap", content="Adım 1")
        tracer.end(success=True)

        record = tracer.get_record()
        assert record.task_name == "görev_2"
        assert len(record.steps) == 1

    def test_failed_trace(self):
        """Başarısız izleme doğru kaydediliyor mu?"""
        from telemetry.traces import TraceCollector

        tracer = TraceCollector(task_name="başarısız_görev")
        tracer.start()
        tracer.add_step("hata", content="Bir şeyler ters gitti!")
        tracer.end(success=False)

        record = tracer.get_record()
        assert record.success is False


# ============================================================
# Ana çalıştırma bloğu
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
