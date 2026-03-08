"""
Writing Evaluator - Makale Kalite Değerlendirici
==================================================
Üretilen makale içeriğini kural tabanlı puanlama ile değerlendirir.

NEDEN BU MODÜL VAR?
--------------------
ReflectionAgent, LLM kullanarak makaleyi değerlendirir. Bu modül ise
LLM KULLANMADAN, tamamen kural tabanlı bir değerlendirme yapar.

Farklar:
- ReflectionAgent → LLM tabanlı, sübjektif, her seferinde farklı puanlama
- WritingEvaluator → Kural tabanlı, objektif, tekrarlanabilir puanlama

Bu önemli çünkü:
1. Evaluation maliyeti sıfır (LLM çağrısı yok)
2. Tekrarlanabilir sonuçlar (aynı girdi → aynı puan)
3. CI/CD'de otomatik kalite kontrolü yapılabilir
4. ReflectionAgent'ın puanlamasını doğrulamak için referans noktası

Değerlendirme Boyutları (5 boyut, ağırlıklı):
    1. Tutarlılık (coherence)   → %20 — Paragraf geçişleri, mantıksal akış
    2. Derinlik (depth)         → %25 — Kelime sayısı, detay seviyesi
    3. Özgünlük (originality)   → %15 — Kelime çeşitliliği
    4. Yapı (structure)         → %20 — Giriş/gövde/sonuç, başlıklar
    5. Kaynakça (citations)     → %20 — Kaynak referansları

Not Sistemi:
    A+ (9+), A (8+), B (7+), C (6+), D (5+), F (<5)

Kullanım:
    from evals.writing_eval import WritingEvaluator

    evaluator = WritingEvaluator()
    result = evaluator.evaluate(article_content, sources_used=5)

    print(f"Puan: {result.overall_score}/10 | Not: {result.grade}")
    for dim, score in result.dimension_scores.items():
        print(f"  {dim}: {score}/10")
"""

import os
import sys
import re
import math
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class WritingEvalResult:
    """
    Yazı değerlendirme sonucu.

    Bu sınıf, WritingEvaluator'ın çıktısıdır.
    Pipeline raporunda ve karşılaştırmalarda kullanılır.

    Alanlar:
        overall_score: Genel puan (1-10, ağırlıklı ortalama)
        dimension_scores: Her boyutun ayrı puanı
        grade: Harf notu (A+, A, B, C, D, F)
        issues: Tespit edilen sorunlar
        suggestions: İyileştirme önerileri
        word_count: Makale kelime sayısı
        paragraph_count: Paragraf sayısı
    """
    overall_score: float = 0.0                                      # Genel puan (1-10)
    dimension_scores: dict[str, float] = field(default_factory=dict)  # Boyut puanları
    grade: str = "F"                                                 # Harf notu
    issues: list[str] = field(default_factory=list)                  # Sorunlar
    suggestions: list[str] = field(default_factory=list)             # Öneriler
    word_count: int = 0                                              # Kelime sayısı
    paragraph_count: int = 0                                         # Paragraf sayısı


# ============================================================
# Boyut Ağırlıkları
# ============================================================

DIMENSION_WEIGHTS = {
    "coherence":   0.20,   # Tutarlılık
    "depth":       0.25,   # Derinlik
    "originality": 0.15,   # Özgünlük
    "structure":   0.20,   # Yapı
    "citations":   0.20,   # Kaynakça
}

# Not eşikleri
GRADE_THRESHOLDS = [
    (9.0, "A+"),
    (8.0, "A"),
    (7.0, "B"),
    (6.0, "C"),
    (5.0, "D"),
    (0.0, "F"),
]


# ============================================================
# WritingEvaluator Sınıfı
# ============================================================

class WritingEvaluator:
    """
    Kural Tabanlı Makale Kalite Değerlendirici.

    Bu sınıf, bir makale metnini 5 boyutta analiz eder ve
    LLM kullanmadan, tamamen kural tabanlı puanlama yapar.

    Neden LLM yerine kural tabanlı?
    - Maliyet: Sıfır (API çağrısı yok)
    - Hız: Milisaniye seviyesinde
    - Tekrarlanabilirlik: Aynı girdi → aynı çıktı
    - Test edilebilirlik: CI/CD'de kullanılabilir
    - Referans: LLM tabanlı değerlendirmeyle karşılaştırma imkanı

    Kullanım:
        evaluator = WritingEvaluator()

        # Tek makale değerlendir
        result = evaluator.evaluate(article_text, sources_used=5)
        print(f"Puan: {result.overall_score}/10 | Not: {result.grade}")

        # İki versiyonu karşılaştır
        delta = evaluator.compare_versions(v1_text, v2_text)
        print(f"İyileşme: {delta['score_delta']:+.1f} puan")
    """

    def __init__(self):
        """WritingEvaluator'ı başlat."""
        self._logger = get_logger("writing_evaluator")

    def evaluate(
        self,
        content: str,
        sources_used: int = 0,
    ) -> WritingEvalResult:
        """
        Makale içeriğini 5 boyutta değerlendir.

        Her boyut 1-10 arası puanlanır ve ağırlıklı ortalamayla
        genel puan hesaplanır.

        Parametreler:
            content: Makale metni (markdown formatında)
            sources_used: Makalede kullanılan kaynak sayısı
                          (ResearchOutput'tan alınır)

        Döndürür:
            WritingEvalResult: Değerlendirme sonucu

        Örnek:
            result = evaluator.evaluate(article_text, sources_used=5)
            print(f"Puan: {result.overall_score}/10")
            print(f"Not: {result.grade}")
        """
        self._logger.info(f"Makale değerlendirmesi başlıyor | {len(content)} karakter")

        # Temel metrikleri hesapla
        words = content.split()
        word_count = len(words)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs)

        issues: list[str] = []
        suggestions: list[str] = []

        # ── 1. Tutarlılık (Coherence) — %20 ──
        coherence_score = self._evaluate_coherence(
            content, paragraphs, issues, suggestions
        )

        # ── 2. Derinlik (Depth) — %25 ──
        depth_score = self._evaluate_depth(
            content, word_count, paragraphs, issues, suggestions
        )

        # ── 3. Özgünlük (Originality) — %15 ──
        originality_score = self._evaluate_originality(
            content, words, issues, suggestions
        )

        # ── 4. Yapı (Structure) — %20 ──
        structure_score = self._evaluate_structure(
            content, word_count, issues, suggestions
        )

        # ── 5. Kaynakça (Citations) — %20 ──
        citations_score = self._evaluate_citations(
            content, sources_used, issues, suggestions
        )

        # ── Boyut puanlarını birleştir ──
        dimension_scores = {
            "coherence":   round(coherence_score, 1),
            "depth":       round(depth_score, 1),
            "originality": round(originality_score, 1),
            "structure":   round(structure_score, 1),
            "citations":   round(citations_score, 1),
        }

        # ── Ağırlıklı ortalama ──
        overall = sum(
            dimension_scores[dim] * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )
        overall = round(min(10.0, max(1.0, overall)), 1)

        # ── Not hesapla ──
        grade = self._calculate_grade(overall)

        result = WritingEvalResult(
            overall_score=overall,
            dimension_scores=dimension_scores,
            grade=grade,
            issues=issues,
            suggestions=suggestions,
            word_count=word_count,
            paragraph_count=paragraph_count,
        )

        self._logger.info(
            f"Değerlendirme tamamlandı | Puan: {overall}/10 | Not: {grade} | "
            f"Kelime: {word_count} | Paragraf: {paragraph_count}"
        )

        return result

    def compare_versions(
        self,
        v1_content: str,
        v2_content: str,
        sources_used: int = 0,
    ) -> dict:
        """
        İki makale versiyonunu karşılaştır.

        Her iki versiyonu değerlendirir ve aralarındaki farkı hesaplar.
        Reflection döngüsünün etkisini ölçmek için kullanılır.

        Parametreler:
            v1_content: İlk versiyon metni
            v2_content: İkinci versiyon metni
            sources_used: Kaynak sayısı

        Döndürür:
            dict: Karşılaştırma sonucu
                - v1_score: İlk versiyon puanı
                - v2_score: İkinci versiyon puanı
                - score_delta: Puan farkı (v2 - v1)
                - improved: İyileşme oldu mu?
                - improved_dimensions: İyileşen boyutlar
                - degraded_dimensions: Kötüleşen boyutlar
                - v1_grade: İlk versiyon notu
                - v2_grade: İkinci versiyon notu

        Örnek:
            delta = evaluator.compare_versions(draft_v1, draft_v2)
            print(f"İyileşme: {delta['score_delta']:+.1f} puan")
            if delta['improved']:
                print("Reflection etkili oldu!")
        """
        v1_result = self.evaluate(v1_content, sources_used)
        v2_result = self.evaluate(v2_content, sources_used)

        # Boyut bazlı karşılaştırma
        improved_dims = []
        degraded_dims = []
        for dim in DIMENSION_WEIGHTS:
            delta = v2_result.dimension_scores[dim] - v1_result.dimension_scores[dim]
            if delta > 0.5:
                improved_dims.append(dim)
            elif delta < -0.5:
                degraded_dims.append(dim)

        score_delta = v2_result.overall_score - v1_result.overall_score

        self._logger.info(
            f"Versiyon karşılaştırma | "
            f"v1: {v1_result.overall_score}/10 ({v1_result.grade}) → "
            f"v2: {v2_result.overall_score}/10 ({v2_result.grade}) | "
            f"Fark: {score_delta:+.1f}"
        )

        return {
            "v1_score": v1_result.overall_score,
            "v2_score": v2_result.overall_score,
            "score_delta": round(score_delta, 1),
            "improved": score_delta > 0,
            "improved_dimensions": improved_dims,
            "degraded_dimensions": degraded_dims,
            "v1_grade": v1_result.grade,
            "v2_grade": v2_result.grade,
            "v1_result": v1_result,
            "v2_result": v2_result,
        }

    # ────────────────────────────────────────────────────────
    # Boyut Değerlendirme Yardımcıları
    # ────────────────────────────────────────────────────────

    def _evaluate_coherence(
        self,
        content: str,
        paragraphs: list[str],
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        """
        Tutarlılık (Coherence) puanı hesapla — %20 ağırlık.

        Kontrol edilen kriterler:
        - Paragraf geçiş kelimeleri (bağlaçlar)
        - Paragraf uzunluk dengesi
        - Mantıksal akış göstergeleri
        """
        score = 5.0  # Başlangıç: orta

        # Geçiş kelimeleri / bağlaçlar
        transition_words = [
            "ancak", "bununla birlikte", "ayrıca", "dahası", "öte yandan",
            "sonuç olarak", "bu nedenle", "dolayısıyla", "ilk olarak",
            "ikinci olarak", "son olarak", "bunun yanı sıra", "örneğin",
            "özellikle", "kısacası", "diğer taraftan", "üstelik",
            "böylece", "bu bağlamda", "buna ek olarak",
        ]
        content_lower = content.lower()
        transition_count = sum(
            1 for tw in transition_words if tw in content_lower
        )

        if transition_count >= 8:
            score += 2.5
        elif transition_count >= 5:
            score += 1.5
        elif transition_count >= 3:
            score += 0.5
        else:
            issues.append("Paragraflar arası geçiş kelimeleri yetersiz")
            suggestions.append("Bağlaçlar ekle: 'ancak', 'ayrıca', 'bu nedenle' gibi")
            score -= 1.0

        # Paragraf uzunluk dengesi
        if len(paragraphs) >= 3:
            lengths = [len(p.split()) for p in paragraphs]
            avg_len = sum(lengths) / len(lengths)
            if avg_len > 0:
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                cv = math.sqrt(variance) / avg_len  # Değişim katsayısı
                if cv < 0.5:
                    score += 1.0  # Dengeli paragraflar
                elif cv > 1.5:
                    score -= 0.5
                    issues.append("Paragraf uzunlukları çok dengesiz")

        # Skor sınırlama
        return max(1.0, min(10.0, score))

    def _evaluate_depth(
        self,
        content: str,
        word_count: int,
        paragraphs: list[str],
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        """
        Derinlik (Depth) puanı hesapla — %25 ağırlık.

        Kontrol edilen kriterler:
        - Kelime sayısı (minimum 800 beklenir)
        - Somut örnekler
        - Teknik terimler
        - Detay düzeyi
        """
        score = 5.0

        # Kelime sayısı
        if word_count >= 1500:
            score += 2.0
        elif word_count >= 1000:
            score += 1.5
        elif word_count >= 800:
            score += 1.0
        elif word_count >= 500:
            score += 0.0
        else:
            score -= 2.0
            issues.append(f"Kelime sayısı çok düşük: {word_count} (minimum 800 önerilir)")
            suggestions.append("Daha fazla açıklama, örnek ve detay ekle")

        # Somut örnekler
        content_lower = content.lower()
        example_markers = [
            "örneğin", "örnek olarak", "mesela", "somut olarak",
            "bir örnek", "şöyle bir örnek", "kod parçası",
            "```", "pratikte", "uygulamada",
        ]
        example_count = sum(1 for em in example_markers if em in content_lower)

        if example_count >= 4:
            score += 1.5
        elif example_count >= 2:
            score += 0.5
        else:
            issues.append("Somut örnek sayısı yetersiz")
            suggestions.append("En az 2-3 somut örnek veya kod parçası ekle")
            score -= 0.5

        # Teknik terim çeşitliliği
        tech_terms = [
            "agent", "llm", "mcp", "api", "token", "embedding", "rag",
            "pipeline", "prompt", "tool", "reflection", "graph",
            "orchestr", "multi-agent", "protocol", "vector", "framework",
        ]
        tech_count = sum(1 for t in tech_terms if t in content_lower)
        if tech_count >= 8:
            score += 1.0
        elif tech_count >= 5:
            score += 0.5

        return max(1.0, min(10.0, score))

    def _evaluate_originality(
        self,
        content: str,
        words: list[str],
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        """
        Özgünlük (Originality) puanı hesapla — %15 ağırlık.

        Kontrol edilen kriterler:
        - Kelime çeşitliliği (Type-Token Ratio)
        - Tekrarlayan kalıplar
        - Özgün ifadeler
        """
        score = 5.0

        if not words:
            return 3.0

        # Type-Token Ratio (TTR) — kelime çeşitliliği
        # Büyük metinlerde TTR doğal olarak düşer, normalize et
        sample_size = min(len(words), 500)
        sample_words = [w.lower().strip(".,;:!?\"'()") for w in words[:sample_size]]
        sample_words = [w for w in sample_words if len(w) > 2]

        if sample_words:
            unique_count = len(set(sample_words))
            ttr = unique_count / len(sample_words)

            if ttr >= 0.65:
                score += 2.5
            elif ttr >= 0.55:
                score += 1.5
            elif ttr >= 0.45:
                score += 0.5
            else:
                score -= 1.0
                issues.append(f"Kelime çeşitliliği düşük (TTR: {ttr:.2f})")
                suggestions.append("Eş anlamlı kelimeler kullanarak tekrarları azalt")

        # Klişe ifadeler
        cliches = [
            "günümüzde", "bu bağlamda", "sonuç olarak bakıldığında",
            "yadsınamaz bir gerçek", "şüphesiz ki",
        ]
        cliche_count = sum(1 for c in cliches if c in content.lower())
        if cliche_count >= 3:
            score -= 1.0
            issues.append("Çok fazla klişe ifade kullanılmış")
            suggestions.append("Klişe ifadeleri özgün cümlelerle değiştir")

        return max(1.0, min(10.0, score))

    def _evaluate_structure(
        self,
        content: str,
        word_count: int,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        """
        Yapı (Structure) puanı hesapla — %20 ağırlık.

        Kontrol edilen kriterler:
        - Başlık varlığı (# veya ##)
        - Giriş / gövde / sonuç yapısı
        - Alt başlık sayısı
        - Markdown formatı
        """
        score = 5.0
        lines = content.split("\n")

        # Ana başlık (h1 veya h2)
        has_title = any(
            line.strip().startswith("# ") or line.strip().startswith("## ")
            for line in lines
        )
        if has_title:
            score += 1.0
        else:
            issues.append("Makale başlığı (# Başlık) eksik")
            suggestions.append("Markdown formatında başlık ekle: # Başlık")
            score -= 1.0

        # Alt başlıklar
        subheadings = [
            line for line in lines
            if line.strip().startswith("### ") or
            (line.strip().startswith("## ") and not line.strip().startswith("# "))
        ]
        subheading_count = len(subheadings)

        if subheading_count >= 4:
            score += 1.5
        elif subheading_count >= 2:
            score += 0.5
        else:
            issues.append(f"Alt başlık sayısı yetersiz ({subheading_count})")
            suggestions.append("En az 3-4 alt başlık ile bölümlendir")
            score -= 0.5

        # Giriş bölümü kontrolü
        content_lower = content.lower()
        has_intro_marker = any(
            marker in content_lower
            for marker in ["giriş", "neden önemli", "bu makalede", "bu yazıda"]
        )
        if has_intro_marker:
            score += 0.5

        # Sonuç bölümü kontrolü
        has_conclusion_marker = any(
            marker in content_lower
            for marker in ["sonuç", "özet", "sonuç olarak", "özetlemek gerekirse"]
        )
        if has_conclusion_marker:
            score += 0.5
        else:
            issues.append("Sonuç bölümü tespit edilemedi")
            suggestions.append("'### Sonuç' başlığı ile bir sonuç bölümü ekle")

        # Kaynakça bölümü varlığı (yapısal olarak)
        has_references_section = any(
            marker in content_lower
            for marker in ["kaynakça", "kaynaklar", "referanslar", "references"]
        )
        if has_references_section:
            score += 0.5

        return max(1.0, min(10.0, score))

    def _evaluate_citations(
        self,
        content: str,
        sources_used: int,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        """
        Kaynakça (Citations) puanı hesapla — %20 ağırlık.

        Kontrol edilen kriterler:
        - İçerikte kaynak referansları
        - Kaynakça bölümünün varlığı
        - Linklerin varlığı
        - sources_used ile tutarlılık
        """
        score = 5.0

        # İçerikteki kaynak referansları
        # [kaynak adı](url) veya (kaynak: ...) formatları
        link_pattern = r'\[.+?\]\(.+?\)'
        links = re.findall(link_pattern, content)
        link_count = len(links)

        # Numaralı referanslar [1], [2] vb.
        numbered_refs = re.findall(r'\[\d+\]', content)
        numbered_ref_count = len(set(numbered_refs))

        # URL'ler
        url_pattern = r'https?://[^\s\)\]>]+'
        urls = re.findall(url_pattern, content)
        url_count = len(urls)

        total_refs = link_count + numbered_ref_count + url_count

        if total_refs >= 5:
            score += 2.5
        elif total_refs >= 3:
            score += 1.5
        elif total_refs >= 1:
            score += 0.5
        else:
            issues.append("İçerikte hiç kaynak referansı bulunamadı")
            suggestions.append("Araştırma kaynaklarına metin içinde atıf yap")
            score -= 1.5

        # Kaynakça bölümü
        content_lower = content.lower()
        has_references = any(
            marker in content_lower
            for marker in ["kaynakça", "kaynaklar", "referanslar"]
        )
        if has_references:
            score += 1.0
        else:
            issues.append("Ayrı bir kaynakça bölümü yok")
            suggestions.append("Makalenin sonuna '### Kaynakça' bölümü ekle")
            score -= 0.5

        # Kaynak kullanım tutarlılığı
        if sources_used > 0:
            if total_refs >= sources_used * 0.6:
                score += 0.5  # Kaynakların çoğuna atıf yapılmış
            else:
                issues.append(
                    f"Araştırmada {sources_used} kaynak var ama "
                    f"makalede sadece {total_refs} referans bulundu"
                )

        return max(1.0, min(10.0, score))

    # ────────────────────────────────────────────────────────
    # Yardımcı Metodlar
    # ────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_grade(score: float) -> str:
        """
        Puandan harf notu hesapla.

        Not sistemi:
            A+ → 9.0 ve üzeri
            A  → 8.0 - 8.9
            B  → 7.0 - 7.9
            C  → 6.0 - 6.9
            D  → 5.0 - 5.9
            F  → 5.0 altı
        """
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 WritingEvaluator - Test")
    print("=" * 60)

    evaluator = WritingEvaluator()

    # Test içeriği: yapılandırılmış makale
    test_article = """
# Agentic AI: Yapay Zekanın Yeni Sınırları

## Giriş

Bu makalede, agentic AI kavramını derinlemesine inceleyeceğiz. Günümüzde
yapay zeka sistemleri hızla evrilmekte ve otonom karar verme yeteneğine
sahip agent'lar önem kazanmaktadır.

Örneğin, bir AI agent araştırma yapabilir, makale yazabilir ve sonuçları
değerlendirebilir — tüm bunları insan müdahalesi olmadan gerçekleştirir.

### 1. Agent Mimarisi

Agent'lar, Think-Act-Observe döngüsünde çalışır. Önce durumu analiz eder,
ardından bir araç çağırır ve sonucu gözlemler. Bu döngü, görev tamamlanana
kadar tekrar eder. Ayrıca, reflection mekanizması ile kendi çıktısını
eleştirip iyileştirebilir.

Somut bir örnek olarak, TwinGraph Studio pipeline'ını düşünebiliriz.
Bu sistemde research agent araştırma yapar, writing agent makale yazar
ve reflection agent kalite kontrolü gerçekleştirir.

### 2. MCP Protokolü

Model Context Protocol (MCP), agent-tool iletişimini standardize eden
bir protokoldür [1]. Ancak, MCP'nin gerçek gücü tool discovery
mekanizmasında yatmaktadır. Bununla birlikte, güvenlik katmanları da
kritik öneme sahiptir.

Dahası, MCP JSON Schema tabanlı parametre doğrulaması yapar ve bu
sayede tool çağrılarının güvenliği sağlanır.

### 3. Multi-Agent Sistemleri

Çoklu agent sistemlerinde, orchestrator pattern merkezi bir rol oynar.
Özellikle, görev dağıtımı ve koordinasyon bu pattern ile yönetilir.
Pratikte, her agent belirli bir sorumluluğa sahiptir.

### Sonuç

Agentic AI, yazılım mühendisliğinin geleceğini şekillendirmektedir.
Özetlemek gerekirse, agent mimarisi, MCP standardı ve multi-agent
koordinasyonu bu alanın üç temel direğidir.

### Kaynakça

1. MCP Protokolü Resmi Dokümantasyonu (https://example.com/mcp)
2. Agentic AI Kapsamlı Rehber (https://example.com/guide)
3. Multi-Agent Sistemleri (https://example.com/multi-agent)
"""

    # Test 1: Tam makale
    print("\n--- Test 1: Yapılandırılmış Makale ---")
    result = evaluator.evaluate(test_article, sources_used=5)
    print(f"Puan: {result.overall_score}/10 | Not: {result.grade}")
    print(f"Kelime: {result.word_count} | Paragraf: {result.paragraph_count}")
    print(f"\nBoyut Puanları:")
    for dim, score in result.dimension_scores.items():
        weight = DIMENSION_WEIGHTS[dim]
        print(f"  {dim:15s}: {score:4.1f}/10 (ağırlık: %{weight*100:.0f})")
    if result.issues:
        print(f"\nSorunlar:")
        for issue in result.issues:
            print(f"  ❌ {issue}")
    if result.suggestions:
        print(f"\nÖneriler:")
        for suggestion in result.suggestions:
            print(f"  💡 {suggestion}")

    # Test 2: Kısa içerik
    print("\n--- Test 2: Kısa İçerik ---")
    short_content = "Bu kısa bir metin. Yeterli detay yok."
    result2 = evaluator.evaluate(short_content, sources_used=0)
    print(f"Puan: {result2.overall_score}/10 | Not: {result2.grade}")
    print(f"Sorun sayısı: {len(result2.issues)}")

    # Test 3: Versiyon karşılaştırma
    print("\n--- Test 3: Versiyon Karşılaştırma ---")
    short_v1 = "Bu kısa bir metin. Detay yok. Başlık yok."
    delta = evaluator.compare_versions(short_v1, test_article, sources_used=5)
    print(f"v1: {delta['v1_score']}/10 ({delta['v1_grade']})")
    print(f"v2: {delta['v2_score']}/10 ({delta['v2_grade']})")
    print(f"Fark: {delta['score_delta']:+.1f} puan")
    print(f"İyileşme: {'Evet' if delta['improved'] else 'Hayır'}")
    if delta['improved_dimensions']:
        print(f"İyileşen: {', '.join(delta['improved_dimensions'])}")

    print("\n✅ Test tamamlandı!")
