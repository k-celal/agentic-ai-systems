"""
Model Router - Akıllı Model Yönlendirici
==========================================
Görev karmaşıklığına göre en uygun LLM modelini seçen yönlendirici.

NEDEN BU MODÜL VAR?
--------------------
CostGuardAgent basit bir görev→model haritası kullanır. Bu modül ise
daha akıllı bir yönlendirme yapar: içerik uzunluğu, görev tipi ve
bütçe durumuna göre dinamik model seçimi.

Varsayılan Yönlendirme Tablosu:
    planning    → gpt-4o-mini    (basit planlama, ucuz model yeterli)
    research    → gpt-4o-mini    (özetleme, güçlü model şart değil)
    writing     → gpt-4o         (yaratıcı yazım, kalite önemli)
    reflection  → gpt-4o-mini    (analitik değerlendirme, ucuz yeterli)
    repurpose   → gpt-4o-mini    (format dönüştürme, basit görev)

Dinamik Kurallar (Writing için):
    - content_length > 2000 → gpt-4o (uzun, kaliteli yazım gerekir)
    - content_length < 500  → gpt-4o-mini (kısa metin, pahalı model gereksiz)
    - 500 ≤ content_length ≤ 2000 → gpt-4o (varsayılan, kalite öncelikli)

Kullanım:
    from routing.model_router import TwinGraphModelRouter

    router = TwinGraphModelRouter()

    # Basit yönlendirme
    choice = router.route("research")
    print(f"Model: {choice.model}")

    # İçerik uzunluğu ile yönlendirme
    choice = router.route("writing", content_length=1500)
    print(f"Model: {choice.model} | Neden: {choice.reason}")

    # Tasarruf raporu
    report = router.get_savings_report(usage_log)
    print(report)
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
class ModelChoice:
    """
    Model yönlendirme kararını temsil eder.

    Bu sınıf, TwinGraphModelRouter'ın çıktısıdır.
    Her route() çağrısında bir ModelChoice döndürülür.

    Alanlar:
        model: Seçilen model adı (örn: "gpt-4o-mini")
        reason: Seçim nedeni (Türkçe açıklama)
        estimated_cost_per_1k: Tahmini maliyet / 1000 token (USD)
        task_type: Yönlendirilen görev tipi
    """
    model: str = "gpt-4o-mini"                          # Seçilen model
    reason: str = ""                                     # Seçim nedeni
    estimated_cost_per_1k: float = 0.0                   # Tahmini maliyet / 1K token
    task_type: str = ""                                  # Görev tipi


# ============================================================
# Yönlendirme Tablosu
# ============================================================

# Görev tiplerine göre varsayılan model haritası
DEFAULT_ROUTING_TABLE: dict[str, str] = {
    "planning":    "gpt-4o-mini",
    "research":    "gpt-4o-mini",
    "writing":     "gpt-4o",
    "reflection":  "gpt-4o-mini",
    "repurpose":   "gpt-4o-mini",
}

# Görev açıklamaları (Türkçe)
TASK_DESCRIPTIONS: dict[str, str] = {
    "planning":    "Planlama ve koordinasyon — basit mantık yürütme yeterli",
    "research":    "Araştırma ve özetleme — güçlü model şart değil",
    "writing":     "Yaratıcı yazım — dil kalitesi ve yaratıcılık önemli",
    "reflection":  "Kalite değerlendirme — analitik düşünme, ucuz model yeterli",
    "repurpose":   "Format dönüştürme — basit görev, ucuz model yeterli",
}


# ============================================================
# TwinGraphModelRouter Sınıfı
# ============================================================

class TwinGraphModelRouter:
    """
    Akıllı Model Yönlendirici.

    Görev tipine ve içerik uzunluğuna göre en uygun LLM modelini seçer.
    Temel strateji: kalite gereken yerde güçlü model, basit görevlerde
    ucuz model kullan.

    Bu yaklaşım, aynı kalitede %40-70 maliyet tasarrufu sağlar.

    Neden bu sınıf var?
    - CostGuardAgent'ın model yönlendirmesi statik
    - Bu sınıf, içerik uzunluğuna göre dinamik karar verir
    - Tasarruf raporlaması yapar
    - Kullanım logu tutar

    Kullanım:
        router = TwinGraphModelRouter()

        # Görev tipine göre model seç
        choice = router.route("writing", content_length=1500)
        print(f"Model: {choice.model} | Neden: {choice.reason}")

        # Tasarruf raporu
        usage_log = [
            {"task": "research", "tokens": 2000, "model": "gpt-4o-mini"},
            {"task": "writing", "tokens": 5000, "model": "gpt-4o"},
            {"task": "reflection", "tokens": 1500, "model": "gpt-4o-mini"},
        ]
        print(router.get_savings_report(usage_log))
    """

    def __init__(
        self,
        routing_table: Optional[dict[str, str]] = None,
    ):
        """
        TwinGraphModelRouter'ı başlat.

        Parametreler:
            routing_table: Özel yönlendirme tablosu (isteğe bağlı).
                          Verilmezse varsayılan tablo kullanılır.
        """
        self._routing_table = routing_table or DEFAULT_ROUTING_TABLE.copy()
        self._logger = get_logger("model_router")
        self._decisions: list[ModelChoice] = []  # Karar geçmişi

        self._logger.info(
            f"TwinGraphModelRouter başlatıldı | "
            f"{len(self._routing_table)} görev tipi tanımlı"
        )

    def route(
        self,
        task_type: str,
        content_length: Optional[int] = None,
    ) -> ModelChoice:
        """
        Görev tipine ve içerik uzunluğuna göre model seç.

        Yönlendirme kuralları:
        1. task_type → varsayılan model tablosundan al
        2. writing görevi için içerik uzunluğuna göre override:
           - content_length > 2000 → gpt-4o (kalite kritik)
           - content_length < 500  → gpt-4o-mini (kısa metin, ucuz yeterli)
        3. Bilinmeyen görev tipi → gpt-4o-mini (güvenli varsayılan)

        Parametreler:
            task_type: Görev tipi
                       Desteklenen: "planning", "research", "writing",
                                    "reflection", "repurpose"
            content_length: Beklenen içerik uzunluğu (kelime sayısı, isteğe bağlı)
                           Writing görevi için model seçimini etkiler.

        Döndürür:
            ModelChoice: Model seçim kararı

        Örnek:
            choice = router.route("writing", content_length=1500)
            print(f"Model: {choice.model}")
            print(f"Neden: {choice.reason}")
            print(f"Tahmini maliyet/1K: ${choice.estimated_cost_per_1k:.6f}")
        """
        # Varsayılan modeli al
        default_model = self._routing_table.get(task_type, "gpt-4o-mini")
        model = default_model
        reason = TASK_DESCRIPTIONS.get(
            task_type,
            "Bilinmeyen görev tipi — güvenli varsayılan (gpt-4o-mini)"
        )

        # ── Writing için dinamik yönlendirme ──
        if task_type == "writing" and content_length is not None:
            if content_length > 2000:
                model = "gpt-4o"
                reason = (
                    f"Uzun içerik ({content_length} kelime) — "
                    f"kalite için gpt-4o gerekli"
                )
            elif content_length < 500:
                model = "gpt-4o-mini"
                reason = (
                    f"Kısa içerik ({content_length} kelime) — "
                    f"gpt-4o-mini yeterli, maliyet tasarrufu"
                )
            else:
                model = "gpt-4o"
                reason = (
                    f"Orta uzunlukta içerik ({content_length} kelime) — "
                    f"kalite öncelikli, gpt-4o tercih ediliyor"
                )

        # Tahmini maliyet hesapla (1K token başına, ortalama input+output)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
        estimated_cost_per_1k = (pricing["input"] + pricing["output"]) / 2 / 1000

        choice = ModelChoice(
            model=model,
            reason=reason,
            estimated_cost_per_1k=estimated_cost_per_1k,
            task_type=task_type,
        )

        # Karar geçmişine ekle
        self._decisions.append(choice)

        self._logger.info(
            f"Model yönlendirme | {task_type} → {model} | "
            f"Neden: {reason[:60]}..."
        )

        return choice

    def get_savings_report(self, usage_log: list[dict]) -> str:
        """
        Kullanım loguna göre tasarruf raporu üret.

        Bu rapor, akıllı yönlendirme ile tüm çağrıları gpt-4o ile
        yapsaydık ne kadar harcardık sorusuna cevap verir.

        Parametreler:
            usage_log: Kullanım kaydı listesi. Her kayıt:
                       {"task": str, "tokens": int, "model": str}

        Döndürür:
            str: Formatlanmış tasarruf raporu

        Örnek:
            log = [
                {"task": "research", "tokens": 2000, "model": "gpt-4o-mini"},
                {"task": "writing", "tokens": 5000, "model": "gpt-4o"},
            ]
            print(router.get_savings_report(log))
        """
        if not usage_log:
            return "Kullanım logu boş — rapor üretilemiyor."

        actual_cost = 0.0
        gpt4o_cost = 0.0

        gpt4o_pricing = MODEL_PRICING.get("gpt-4o", {"input": 2.50, "output": 10.00})

        for entry in usage_log:
            tokens = entry.get("tokens", 0)
            model = entry.get("model", "gpt-4o-mini")
            task = entry.get("task", "bilinmeyen")

            input_tokens = tokens // 2
            output_tokens = tokens // 2

            # Gerçek maliyet
            pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
            actual = (input_tokens / 1_000_000) * pricing["input"] + \
                     (output_tokens / 1_000_000) * pricing["output"]
            actual_cost += actual

            # gpt-4o ile olsaydı
            baseline = (input_tokens / 1_000_000) * gpt4o_pricing["input"] + \
                       (output_tokens / 1_000_000) * gpt4o_pricing["output"]
            gpt4o_cost += baseline

        savings = max(0, gpt4o_cost - actual_cost)
        savings_pct = (savings / max(gpt4o_cost, 0.000001)) * 100

        lines = [
            "",
            "═" * 50,
            "📊 TwinGraph Model Yönlendirme — Tasarruf Raporu",
            "═" * 50,
            f"  Toplam çağrı sayısı:     {len(usage_log)}",
            f"  Gerçek maliyet:          ${actual_cost:.6f}",
            f"  All-GPT-4o maliyeti:     ${gpt4o_cost:.6f}",
            f"  Tasarruf:                ${savings:.6f}",
            f"  Tasarruf oranı:          %{savings_pct:.1f}",
            "",
            "  📋 Görev Bazlı Dağılım:",
            "  " + "─" * 46,
        ]

        # Görev bazlı özet
        task_summary: dict[str, dict] = {}
        for entry in usage_log:
            task = entry.get("task", "bilinmeyen")
            model = entry.get("model", "?")
            tokens = entry.get("tokens", 0)

            if task not in task_summary:
                task_summary[task] = {"tokens": 0, "model": model, "count": 0}
            task_summary[task]["tokens"] += tokens
            task_summary[task]["count"] += 1

        for task, info in task_summary.items():
            lines.append(
                f"    {task:15s} | {info['model']:15s} | "
                f"{info['tokens']:,} token | {info['count']} çağrı"
            )

        # Sonuç
        if savings_pct >= 50:
            verdict = "Mükemmel! Akıllı yönlendirme çok etkili."
        elif savings_pct >= 30:
            verdict = "İyi tasarruf sağlanıyor."
        elif savings_pct >= 10:
            verdict = "Orta düzey tasarruf. Daha fazla optimizasyon mümkün."
        else:
            verdict = "Tasarruf düşük. Yönlendirme stratejisi gözden geçirilmeli."

        lines.extend([
            "",
            f"  💡 Değerlendirme: {verdict}",
            "═" * 50,
        ])

        return "\n".join(lines)

    @property
    def decision_history(self) -> list[ModelChoice]:
        """Tüm yönlendirme kararlarının geçmişi."""
        return self._decisions.copy()


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TwinGraphModelRouter - Test")
    print("=" * 60)

    router = TwinGraphModelRouter()

    # Test 1: Her görev tipi için yönlendirme
    print("\n--- Test 1: Görev Tipi Yönlendirme ---")
    for task in ["planning", "research", "writing", "reflection", "repurpose", "bilinmeyen"]:
        choice = router.route(task)
        print(f"  {task:15s} → {choice.model:15s} | ${choice.estimated_cost_per_1k:.6f}/1K")

    # Test 2: Writing için dinamik yönlendirme
    print("\n--- Test 2: Writing — İçerik Uzunluğu ---")
    for length in [200, 500, 1000, 1500, 2500, 5000]:
        choice = router.route("writing", content_length=length)
        print(f"  {length:5d} kelime → {choice.model:15s} | {choice.reason[:50]}...")

    # Test 3: Tasarruf raporu
    print("\n--- Test 3: Tasarruf Raporu ---")
    usage_log = [
        {"task": "research",   "tokens": 2000, "model": "gpt-4o-mini"},
        {"task": "writing",    "tokens": 5000, "model": "gpt-4o"},
        {"task": "reflection", "tokens": 1500, "model": "gpt-4o-mini"},
        {"task": "writing",    "tokens": 4000, "model": "gpt-4o"},
        {"task": "repurpose",  "tokens": 1200, "model": "gpt-4o-mini"},
    ]
    print(router.get_savings_report(usage_log))

    # Test 4: Karar geçmişi
    print("\n--- Test 4: Karar Geçmişi ---")
    print(f"Toplam karar: {len(router.decision_history)}")

    print("\n✅ Test tamamlandı!")
