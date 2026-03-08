"""
Cost Evaluator - Maliyet Verimlilik Değerlendirici
====================================================
Pipeline çalışmasının maliyet verimliliğini ölçen değerlendirici.

NEDEN BU MODÜL VAR?
--------------------
CostGuardAgent, pipeline sırasında bütçeyi korur. Bu modül ise
pipeline TAMAMLANDIKTAN SONRA, maliyet verimliliğini geriye dönük analiz eder.

Farklar:
- CostGuardAgent → Anlık koruma (bütçe aşımını engeller)
- CostEvaluator  → Sonradan analiz (ne kadar verimli çalıştık?)

Ölçülen Metrikler:
1. total_cost        → Toplam API maliyeti (USD)
2. cost_per_word     → Kelime başına maliyet
3. tokens_per_word   → Kelime başına token kullanımı
4. model_routing_savings → Model yönlendirme tasarrufu
5. reflection_roi    → Reflection döngüsünün yatırım getirisi

Verimlilik Notları:
    A+ → Her şey optimal, maliyet çok düşük
    A  → İyi verimlilik
    B  → Kabul edilebilir
    C  → İyileştirme gerekli
    D  → Verimsiz
    F  → Çok verimsiz

Kullanım:
    from evals.cost_eval import CostEvaluator

    evaluator = CostEvaluator()
    result = evaluator.evaluate(
        total_tokens=8500,
        total_cost=0.0042,
        word_count=1200,
        reflection_improvement=1.5,
        num_reflection_loops=2,
    )

    print(f"Maliyet Notu: {result.efficiency_grade}")
    print(f"Kelime başına maliyet: ${result.cost_per_word:.6f}")
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from shared.telemetry.cost_tracker import MODEL_PRICING


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class CostEvalResult:
    """
    Maliyet değerlendirme sonucu.

    Bu sınıf, CostEvaluator'ın çıktısıdır.
    Pipeline raporunda ve optimizasyon kararlarında kullanılır.

    Alanlar:
        total_cost: Toplam maliyet (USD)
        cost_per_word: Kelime başına maliyet (USD)
        tokens_per_word: Kelime başına token kullanımı
        efficiency_grade: Verimlilik notu (A+, A, B, C, D, F)
        model_routing_savings: Model yönlendirme tasarrufu (USD)
        reflection_roi: Reflection yatırım getirisi (pozitif = karlı)
        suggestions: İyileştirme önerileri
    """
    total_cost: float = 0.0                                     # Toplam maliyet
    cost_per_word: float = 0.0                                  # Kelime başına maliyet
    tokens_per_word: float = 0.0                                # Kelime başına token
    efficiency_grade: str = "F"                                 # Verimlilik notu
    model_routing_savings: float = 0.0                          # Yönlendirme tasarrufu
    reflection_roi: float = 0.0                                 # Reflection ROI
    reflection_roi_positive: bool = False                       # ROI pozitif mi?
    suggestions: list[str] = field(default_factory=list)        # Öneriler


# ============================================================
# Verimlilik Eşikleri
# ============================================================

# Kelime başına maliyet eşikleri (USD)
# Bu değerler, tipik bir pipeline çalışmasına göre kalibre edilmiştir.
COST_PER_WORD_THRESHOLDS = {
    "A+": 0.000005,   # $0.005 / 1000 kelime
    "A":  0.000010,   # $0.010 / 1000 kelime
    "B":  0.000025,   # $0.025 / 1000 kelime
    "C":  0.000050,   # $0.050 / 1000 kelime
    "D":  0.000100,   # $0.100 / 1000 kelime
}
# Üstü → F notu

# Tokens per word eşikleri
TOKENS_PER_WORD_IDEAL = 7.0       # İdeal: 7 token / kelime
TOKENS_PER_WORD_ACCEPTABLE = 12.0  # Kabul edilebilir üst sınır


# ============================================================
# CostEvaluator Sınıfı
# ============================================================

class CostEvaluator:
    """
    Maliyet Verimlilik Değerlendirici.

    Pipeline tamamlandıktan sonra, maliyet verimliliğini
    çok boyutlu olarak analiz eder.

    Analiz Boyutları:
    1. Kelime başına maliyet → Ne kadar ucuz içerik ürettik?
    2. Token verimliliği → Token'ları ne kadar etkin kullandık?
    3. Model yönlendirme tasarrufu → Akıllı model seçimi ne kadar tasarruf sağladı?
    4. Reflection ROI → Reflection döngüsü maliyetine değdi mi?

    Kullanım:
        evaluator = CostEvaluator()

        result = evaluator.evaluate(
            total_tokens=8500,
            total_cost=0.0042,
            word_count=1200,
            reflection_improvement=1.5,
            num_reflection_loops=2,
        )

        print(f"Not: {result.efficiency_grade}")
        for s in result.suggestions:
            print(f"  → {s}")

        # Baseline ile karşılaştır
        comparison = evaluator.compare_with_baseline(result)
        print(f"Tasarruf: ${comparison['savings']:.6f}")
    """

    def __init__(self):
        """CostEvaluator'ı başlat."""
        self._logger = get_logger("cost_evaluator")

    def evaluate(
        self,
        total_tokens: int,
        total_cost: float,
        word_count: int,
        reflection_improvement: float = 0.0,
        num_reflection_loops: int = 0,
    ) -> CostEvalResult:
        """
        Pipeline maliyet verimliliğini değerlendir.

        Parametreler:
            total_tokens: Toplam kullanılan token sayısı
            total_cost: Toplam maliyet (USD)
            word_count: Üretilen toplam kelime sayısı
                        (makale + LinkedIn postu)
            reflection_improvement: Reflection döngüsünün sağladığı
                                    puan iyileşmesi (v_son - v_ilk)
            num_reflection_loops: Yapılan reflection döngüsü sayısı

        Döndürür:
            CostEvalResult: Maliyet değerlendirme sonucu

        Örnek:
            result = evaluator.evaluate(
                total_tokens=8500,
                total_cost=0.0042,
                word_count=1200,
                reflection_improvement=1.5,
                num_reflection_loops=2,
            )
        """
        self._logger.info(
            f"Maliyet değerlendirmesi başlıyor | "
            f"Token: {total_tokens:,} | Maliyet: ${total_cost:.6f} | "
            f"Kelime: {word_count}"
        )

        suggestions: list[str] = []

        # ── Kelime başına maliyet ──
        cost_per_word = total_cost / max(word_count, 1)

        # ── Token başına kelime ──
        tokens_per_word = total_tokens / max(word_count, 1)

        if tokens_per_word > TOKENS_PER_WORD_ACCEPTABLE:
            suggestions.append(
                f"Token/kelime oranı yüksek ({tokens_per_word:.1f}). "
                f"Prompt'ları kısaltarak token tüketimini azalt."
            )

        # ── Model yönlendirme tasarrufu ──
        # Tüm çağrılar gpt-4o ile yapılsaydı ne kadar tutardı?
        all_gpt4o_cost = self._estimate_all_gpt4o_cost(total_tokens)
        model_routing_savings = max(0, all_gpt4o_cost - total_cost)

        if model_routing_savings > 0:
            savings_percent = (model_routing_savings / max(all_gpt4o_cost, 0.000001)) * 100
            if savings_percent < 30:
                suggestions.append(
                    f"Model yönlendirme tasarrufu düşük (%{savings_percent:.0f}). "
                    f"Daha fazla görevi gpt-4o-mini'ye yönlendir."
                )
        else:
            suggestions.append(
                "Model yönlendirme aktif değil. Basit görevlerde gpt-4o-mini kullanarak "
                "maliyeti %40-70 azaltabilirsin."
            )

        # ── Reflection ROI ──
        reflection_roi = 0.0
        reflection_roi_positive = False

        if num_reflection_loops > 0:
            # Reflection'ın tahmini maliyeti (toplam maliyetin bir kısmı)
            # Her reflection döngüsü ≈ writing + reflection agent çağrısı
            estimated_reflection_cost = total_cost * (
                num_reflection_loops / max(num_reflection_loops + 2, 1)
            )

            # ROI: İyileşme puanı / harcanan maliyet oranı
            # Pozitif iyileşme = karlı yatırım
            if reflection_improvement > 0:
                # Kalite başına maliyet (düşük iyi)
                quality_cost_ratio = estimated_reflection_cost / max(reflection_improvement, 0.01)
                # ROI basit formül: iyileşme - harcama (normalize)
                reflection_roi = reflection_improvement - (estimated_reflection_cost * 1000)
                reflection_roi_positive = reflection_improvement > 0.5
            else:
                reflection_roi = -estimated_reflection_cost * 1000
                reflection_roi_positive = False
                suggestions.append(
                    "Reflection döngüsü kaliteyi iyileştirmedi. "
                    "Reflection eşiğini düşürmeyi veya döngü sayısını azaltmayı düşün."
                )

            if num_reflection_loops >= 3 and reflection_improvement < 1.0:
                suggestions.append(
                    f"{num_reflection_loops} reflection döngüsüne rağmen "
                    f"sadece {reflection_improvement:.1f} puan iyileşme. "
                    f"Maksimum döngü sayısını 2'ye düşürmeyi düşün."
                )

        # ── Verimlilik notu hesapla ──
        efficiency_grade = self._calculate_efficiency_grade(
            cost_per_word, tokens_per_word, model_routing_savings, all_gpt4o_cost
        )

        # ── Genel öneriler ──
        if total_cost > 0.05:
            suggestions.append(
                f"Toplam maliyet ${total_cost:.4f}. Bütçe limitini "
                f"kontrol et ve gereksiz döngüleri azalt."
            )

        if word_count < 500 and total_cost > 0.01:
            suggestions.append(
                "Düşük kelime sayısına rağmen yüksek maliyet. "
                "Prompt'ları optimize et veya daha kısa araştırma kullan."
            )

        result = CostEvalResult(
            total_cost=total_cost,
            cost_per_word=cost_per_word,
            tokens_per_word=round(tokens_per_word, 1),
            efficiency_grade=efficiency_grade,
            model_routing_savings=model_routing_savings,
            reflection_roi=round(reflection_roi, 2),
            reflection_roi_positive=reflection_roi_positive,
            suggestions=suggestions,
        )

        self._logger.info(
            f"Maliyet değerlendirmesi tamamlandı | "
            f"Not: {efficiency_grade} | "
            f"$/kelime: {cost_per_word:.8f} | "
            f"Token/kelime: {tokens_per_word:.1f} | "
            f"Tasarruf: ${model_routing_savings:.6f}"
        )

        return result

    def compare_with_baseline(self, result: CostEvalResult) -> dict:
        """
        Sonucu tek-model (all-gpt-4o) baseline ile karşılaştır.

        Bu karşılaştırma, akıllı model yönlendirmenin
        ne kadar tasarruf sağladığını gösterir.

        Parametreler:
            result: Maliyet değerlendirme sonucu

        Döndürür:
            dict: Karşılaştırma sonucu
                - actual_cost: Gerçek maliyet
                - baseline_cost: Tümü gpt-4o olsaydı maliyet
                - savings: Tasarruf miktarı (USD)
                - savings_percent: Tasarruf yüzdesi
                - verdict: Değerlendirme mesajı

        Örnek:
            comparison = evaluator.compare_with_baseline(result)
            print(f"Tasarruf: ${comparison['savings']:.6f} (%{comparison['savings_percent']:.0f})")
        """
        # Baseline: tüm token'lar gpt-4o ile işlenseydi
        word_count = max(int(result.total_cost / max(result.cost_per_word, 0.0000001)), 1)
        total_tokens = int(result.tokens_per_word * word_count)
        baseline_cost = self._estimate_all_gpt4o_cost(total_tokens)

        actual_cost = result.total_cost
        savings = max(0, baseline_cost - actual_cost)
        savings_percent = (savings / max(baseline_cost, 0.000001)) * 100

        # Değerlendirme mesajı
        if savings_percent >= 60:
            verdict = "Mükemmel! Model yönlendirme çok etkili çalışıyor."
        elif savings_percent >= 40:
            verdict = "İyi tasarruf. Model yönlendirme etkili."
        elif savings_percent >= 20:
            verdict = "Orta düzey tasarruf. Daha fazla görev gpt-4o-mini'ye yönlendirilebilir."
        elif savings_percent > 0:
            verdict = "Düşük tasarruf. Model yönlendirme stratejisi gözden geçirilmeli."
        else:
            verdict = "Tasarruf yok. Tüm çağrılar zaten gpt-4o ile yapılıyor olabilir."

        comparison = {
            "actual_cost": actual_cost,
            "baseline_cost": baseline_cost,
            "savings": savings,
            "savings_percent": round(savings_percent, 1),
            "verdict": verdict,
        }

        self._logger.info(
            f"Baseline karşılaştırma | "
            f"Gerçek: ${actual_cost:.6f} | "
            f"Baseline: ${baseline_cost:.6f} | "
            f"Tasarruf: ${savings:.6f} (%{savings_percent:.0f})"
        )

        return comparison

    # ────────────────────────────────────────────────────────
    # Yardımcı Metodlar
    # ────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_all_gpt4o_cost(total_tokens: int) -> float:
        """
        Tüm token'lar gpt-4o ile işlenseydi maliyeti tahmin et.

        Varsayım: input ve output token'lar eşit dağılmıştır.
        Bu, en kötü senaryo tahminidir.

        Parametreler:
            total_tokens: Toplam token sayısı

        Döndürür:
            float: Tahmini maliyet (USD)
        """
        pricing = MODEL_PRICING.get("gpt-4o", {"input": 2.50, "output": 10.00})
        input_tokens = total_tokens // 2
        output_tokens = total_tokens // 2

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    @staticmethod
    def _calculate_efficiency_grade(
        cost_per_word: float,
        tokens_per_word: float,
        model_routing_savings: float,
        baseline_cost: float,
    ) -> str:
        """
        Çoklu faktörden verimlilik notu hesapla.

        Faktörler:
        1. Kelime başına maliyet (%50 ağırlık)
        2. Token verimliliği (%20 ağırlık)
        3. Model yönlendirme tasarrufu (%30 ağırlık)

        Döndürür:
            str: Verimlilik notu (A+, A, B, C, D, F)
        """
        score = 0.0

        # Faktör 1: Kelime başına maliyet (%50)
        if cost_per_word <= COST_PER_WORD_THRESHOLDS["A+"]:
            score += 5.0
        elif cost_per_word <= COST_PER_WORD_THRESHOLDS["A"]:
            score += 4.0
        elif cost_per_word <= COST_PER_WORD_THRESHOLDS["B"]:
            score += 3.0
        elif cost_per_word <= COST_PER_WORD_THRESHOLDS["C"]:
            score += 2.0
        elif cost_per_word <= COST_PER_WORD_THRESHOLDS["D"]:
            score += 1.0
        else:
            score += 0.0

        # Faktör 2: Token verimliliği (%20)
        if tokens_per_word <= TOKENS_PER_WORD_IDEAL:
            score += 2.0
        elif tokens_per_word <= TOKENS_PER_WORD_ACCEPTABLE:
            score += 1.0
        else:
            score += 0.0

        # Faktör 3: Model yönlendirme tasarrufu (%30)
        if baseline_cost > 0:
            savings_pct = (model_routing_savings / baseline_cost) * 100
            if savings_pct >= 50:
                score += 3.0
            elif savings_pct >= 30:
                score += 2.0
            elif savings_pct >= 10:
                score += 1.0

        # Notu belirle (toplam 0-10 arası)
        if score >= 9.0:
            return "A+"
        elif score >= 7.5:
            return "A"
        elif score >= 6.0:
            return "B"
        elif score >= 4.0:
            return "C"
        elif score >= 2.0:
            return "D"
        else:
            return "F"


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 CostEvaluator - Test")
    print("=" * 60)

    evaluator = CostEvaluator()

    # Test 1: Verimli pipeline
    print("\n--- Test 1: Verimli Pipeline ---")
    result1 = evaluator.evaluate(
        total_tokens=8500,
        total_cost=0.003,
        word_count=1200,
        reflection_improvement=1.5,
        num_reflection_loops=2,
    )
    print(f"Not: {result1.efficiency_grade}")
    print(f"Toplam maliyet: ${result1.total_cost:.6f}")
    print(f"Kelime başına: ${result1.cost_per_word:.8f}")
    print(f"Token/kelime: {result1.tokens_per_word}")
    print(f"Tasarruf: ${result1.model_routing_savings:.6f}")
    print(f"Reflection ROI: {result1.reflection_roi:+.2f} ({'Karlı' if result1.reflection_roi_positive else 'Zararlı'})")
    for s in result1.suggestions:
        print(f"  → {s}")

    # Test 2: Pahalı pipeline
    print("\n--- Test 2: Pahalı Pipeline ---")
    result2 = evaluator.evaluate(
        total_tokens=25000,
        total_cost=0.15,
        word_count=800,
        reflection_improvement=0.3,
        num_reflection_loops=3,
    )
    print(f"Not: {result2.efficiency_grade}")
    print(f"Toplam maliyet: ${result2.total_cost:.6f}")
    print(f"Kelime başına: ${result2.cost_per_word:.8f}")
    print(f"Token/kelime: {result2.tokens_per_word}")
    for s in result2.suggestions:
        print(f"  → {s}")

    # Test 3: Baseline karşılaştırma
    print("\n--- Test 3: Baseline Karşılaştırma ---")
    comparison = evaluator.compare_with_baseline(result1)
    print(f"Gerçek maliyet: ${comparison['actual_cost']:.6f}")
    print(f"Baseline (all gpt-4o): ${comparison['baseline_cost']:.6f}")
    print(f"Tasarruf: ${comparison['savings']:.6f} (%{comparison['savings_percent']:.0f})")
    print(f"Değerlendirme: {comparison['verdict']}")

    print("\n✅ Test tamamlandı!")
