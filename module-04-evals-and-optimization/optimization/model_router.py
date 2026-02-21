"""
Akıllı Model Yönlendirici (Model Router)
==========================================
Basit görevleri ucuz modele (gpt-4o-mini), karmaşık görevleri
güçlü modele (gpt-4o) yönlendirir.

Neden Model Routing?
--------------------
Tüm görevler için aynı modeli kullanmak verimsizdir:

  "Merhaba, nasılsın?" → GPT-4o gereksiz! GPT-4o-mini yeterli ($0.0001)
  "Karmaşık bir refactoring planı yap" → GPT-4o-mini yetersiz! GPT-4o gerekli ($0.01)

Model routing ile:
  - Basit görevler → Ucuz model (hızlı + ucuz)
  - Orta görevler  → Ucuz model (genellikle yeterli)
  - Karmaşık görevler → Güçlü model (kalite önemli)

Maliyet etkisi (günde 10,000 çağrı senaryosu):
  Hep GPT-4o:    ~$300/gün
  Hep GPT-4o-mini: ~$18/gün (ama kalite düşer)
  Akıllı routing:  ~$25/gün (kalite + tasarruf!)

Karmaşıklık Skoru Nasıl Hesaplanır?
------------------------------------
Birden fazla sinyal kullanılır:
  - Metin uzunluğu (uzun = karmaşık)
  - Anahtar kelimeler (analiz, refactoring, plan = karmaşık)
  - Çok adımlı görev göstergeleri (ve, sonra, ardından)
  - Teknik terminoloji yoğunluğu

Kullanım:
    from optimization.model_router import ModelRouter

    router = ModelRouter()
    model = router.route("Merhaba, nasılsın?")
    # → "gpt-4o-mini"

    model = router.route("Bu kodu refactor et ve performans analizi yap")
    # → "gpt-4o"
"""

import sys
import os
from dataclasses import dataclass
from typing import Optional

# shared/ modülünü import edebilmek için path ayarı
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from shared.telemetry.cost_tracker import MODEL_PRICING

logger = get_logger("optimization.model_router")


# ============================================================
# Yapılandırma
# ============================================================

@dataclass
class RoutingConfig:
    """
    Model yönlendirme yapılandırması.

    Eşik değerlerini değiştirerek yönlendirme davranışını
    ayarlayabilirsiniz.

    Alanlar:
        cheap_model: Ucuz/hızlı model adı
        expensive_model: Güçlü/pahalı model adı
        complexity_threshold_low: Bu skorun altı → ucuz model
        complexity_threshold_high: Bu skorun üstü → güçlü model
        fallback_model: Hata durumunda kullanılacak model
    """
    cheap_model: str = "gpt-4o-mini"
    expensive_model: str = "gpt-4o"
    complexity_threshold_low: int = 4    # 0-3: ucuz model
    complexity_threshold_high: int = 7   # 7+: pahalı model
    fallback_model: str = "gpt-4o-mini"  # Hata durumunda


# ============================================================
# Ana Model Router Sınıfı
# ============================================================

class ModelRouter:
    """
    Görev karmaşıklığına göre model seçen yönlendirici.

    Çalışma mantığı:
    ────────────────
    1. Görev metnini analiz et
    2. Karmaşıklık skoru hesapla (0-15 arası)
    3. Skora göre model seç:
       - 0-3:  gpt-4o-mini (basit görevler)
       - 4-6:  gpt-4o-mini (orta görevler, genellikle yeterli)
       - 7+:   gpt-4o (karmaşık görevler)

    Karmaşıklık sinyalleri:
    ───────────────────────
    Sinyal                           Puan
    ─────────────────────────────────────
    Uzun metin (>200 karakter)        +2
    Çok uzun metin (>500 karakter)    +2 (ek)
    Çok adımlı görev göstergeleri     +3
    Teknik/analitik anahtar kelimeler +2
    Kod içerme                        +2
    Yaratıcı/açık uçlu görevler       +1
    Basit soru-cevap göstergeleri     -1

    Kullanım:
        router = ModelRouter()

        # Basit görev → ucuz model
        model = router.route("Merhaba!")
        assert model == "gpt-4o-mini"

        # Karmaşık görev → güçlü model
        model = router.route("Bu kodu refactor et, performans analizi yap ve test yaz")
        assert model == "gpt-4o"
    """

    def __init__(self, config: Optional[RoutingConfig] = None):
        """
        ModelRouter oluştur.

        Parametreler:
            config: Yönlendirme yapılandırması.
                    None ise varsayılan değerler kullanılır.
        """
        self.config = config or RoutingConfig()
        self.logger = get_logger("model_router")

        # Yönlendirme istatistikleri
        self._route_counts = {
            self.config.cheap_model: 0,
            self.config.expensive_model: 0,
        }
        self._total_routes = 0

    def calculate_complexity(self, task: str) -> int:
        """
        Görevin karmaşıklık skorunu hesapla.

        Birden fazla sinyal kullanarak toplam skor oluşturur.
        Her sinyal bağımsız olarak kontrol edilir ve puanlar toplanır.

        Parametreler:
            task: Görev açıklaması

        Döndürür:
            int: Karmaşıklık skoru (0-15 arası)
        """
        score = 0
        task_lower = task.lower()

        # ── Sinyal 1: Metin uzunluğu ──────────────────────
        # Uzun görevler genellikle daha karmaşıktır
        if len(task) > 200:
            score += 2
            self.logger.debug(f"  +2 uzun metin ({len(task)} karakter)")
        if len(task) > 500:
            score += 2
            self.logger.debug(f"  +2 çok uzun metin ({len(task)} karakter)")

        # ── Sinyal 2: Çok adımlı görev göstergeleri ──────
        # "ve", "sonra", "ardından" gibi bağlaçlar çok adımlı görevi işaret eder
        multi_step_keywords = [
            "ve sonra", "ardından", "daha sonra", "ilk önce",
            "adım adım", "sırasıyla", "aşama", "adım",
            "hem ... hem", "önce ... sonra",
        ]
        multi_step_count = sum(1 for kw in multi_step_keywords if kw in task_lower)
        if multi_step_count > 0:
            score += min(multi_step_count * 2, 3)  # Maksimum +3
            self.logger.debug(f"  +{min(multi_step_count * 2, 3)} çok adımlı görev")

        # ── Sinyal 3: Teknik/analitik anahtar kelimeler ──
        technical_keywords = [
            "analiz", "refactor", "optimize", "mimari", "tasarım",
            "karşılaştır", "değerlendir", "strateji", "algoritma",
            "performans", "ölçeklendir", "güvenlik", "architecture",
            "debug", "profil", "benchmark",
        ]
        tech_count = sum(1 for kw in technical_keywords if kw in task_lower)
        if tech_count > 0:
            score += min(tech_count, 2)  # Maksimum +2
            self.logger.debug(f"  +{min(tech_count, 2)} teknik anahtar kelimeler")

        # ── Sinyal 4: Kod içeriyor mu? ──────────────────
        code_indicators = [
            "```", "def ", "class ", "import ", "function",
            "kod yaz", "kod çalıştır", "implement", "uygula",
        ]
        has_code = any(ind in task_lower or ind in task for ind in code_indicators)
        if has_code:
            score += 2
            self.logger.debug("  +2 kod içeriyor")

        # ── Sinyal 5: Yaratıcı/açık uçlu görevler ───────
        creative_keywords = [
            "yaz", "oluştur", "tasarla", "hayal et", "öner",
            "hikaye", "senaryo", "plan yap",
        ]
        creative_count = sum(1 for kw in creative_keywords if kw in task_lower)
        if creative_count > 0:
            score += 1
            self.logger.debug("  +1 yaratıcı/açık uçlu görev")

        # ── Sinyal 6: Basit soru-cevap göstergeleri ──────
        # Basit sorular skoru düşürür
        simple_indicators = [
            "merhaba", "nedir", "ne demek", "nasılsın",
            "teşekkür", "tamam", "evet", "hayır", "selam",
        ]
        is_simple = any(ind in task_lower for ind in simple_indicators) and len(task) < 50
        if is_simple:
            score -= 1
            self.logger.debug("  -1 basit soru-cevap")

        # Skor negatif olamaz
        score = max(0, score)

        self.logger.debug(f"  Toplam karmaşıklık skoru: {score}")
        return score

    def route(self, task: str) -> str:
        """
        Görev için en uygun modeli seç.

        Parametreler:
            task: Görev açıklaması

        Döndürür:
            str: Model adı (örn: "gpt-4o-mini" veya "gpt-4o")
        """
        complexity = self.calculate_complexity(task)

        # Skora göre model seç
        if complexity >= self.config.complexity_threshold_high:
            model = self.config.expensive_model
            reason = "karmaşık görev"
        else:
            model = self.config.cheap_model
            reason = "basit/orta görev"

        # İstatistikleri güncelle
        self._total_routes += 1
        if model in self._route_counts:
            self._route_counts[model] += 1

        self.logger.info(
            f"🔀 Yönlendirme: {model} (skor={complexity}, sebep={reason})"
        )

        return model

    def route_with_details(self, task: str) -> dict:
        """
        Görev için model seç ve detaylı bilgi döndür.

        route() ile aynı mantık, ama ek bilgiler de verir.
        Debug ve eval için kullanışlı.

        Parametreler:
            task: Görev açıklaması

        Döndürür:
            dict: {
                "model": str,            # Seçilen model
                "complexity_score": int,  # Karmaşıklık skoru
                "reason": str,           # Seçim sebebi
                "estimated_cost_ratio": float,  # Maliyet oranı (ucuz/pahalı)
            }
        """
        complexity = self.calculate_complexity(task)

        if complexity >= self.config.complexity_threshold_high:
            model = self.config.expensive_model
            reason = "Yüksek karmaşıklık: güçlü model gerekli"
        elif complexity >= self.config.complexity_threshold_low:
            model = self.config.cheap_model
            reason = "Orta karmaşıklık: ucuz model yeterli"
        else:
            model = self.config.cheap_model
            reason = "Düşük karmaşıklık: ucuz model yeterli"

        # Maliyet oranını hesapla
        cheap_price = MODEL_PRICING.get(self.config.cheap_model, {}).get("input", 0.15)
        expensive_price = MODEL_PRICING.get(self.config.expensive_model, {}).get("input", 2.50)
        cost_ratio = cheap_price / expensive_price if expensive_price > 0 else 0

        # İstatistikleri güncelle
        self._total_routes += 1
        if model in self._route_counts:
            self._route_counts[model] += 1

        return {
            "model": model,
            "complexity_score": complexity,
            "reason": reason,
            "estimated_cost_ratio": round(cost_ratio, 3),
        }

    def get_stats(self) -> str:
        """
        Yönlendirme istatistiklerini döndür.

        Döndürür:
            str: İstatistik raporu
        """
        if self._total_routes == 0:
            return "Henüz yönlendirme yapılmadı."

        cheap_count = self._route_counts.get(self.config.cheap_model, 0)
        expensive_count = self._route_counts.get(self.config.expensive_model, 0)

        cheap_pct = cheap_count / self._total_routes * 100
        expensive_pct = expensive_count / self._total_routes * 100

        return (
            f"\n{'='*50}\n"
            f"🔀 Model Yönlendirme İstatistikleri\n"
            f"{'='*50}\n"
            f"  Toplam Yönlendirme:    {self._total_routes}\n"
            f"  {self.config.cheap_model:<20} {cheap_count:>5} ({cheap_pct:.0f}%)\n"
            f"  {self.config.expensive_model:<20} {expensive_count:>5} ({expensive_pct:.0f}%)\n"
            f"{'='*50}"
        )


# ============================================================
# Ana çalıştırma bloğu — Demo
# ============================================================

if __name__ == "__main__":
    print("🔀 Akıllı Model Yönlendirici — Demo")
    print("=" * 55)
    print()

    router = ModelRouter()

    # Farklı karmaşıklık seviyelerinde görevler
    tasks = [
        # Basit görevler → gpt-4o-mini bekleniyor
        "Merhaba, nasılsın?",
        "Python nedir?",
        "Teşekkürler!",

        # Orta görevler → gpt-4o-mini hâlâ yeterli
        "Python'da liste ve tuple arasındaki farkı açıkla",
        "Bir for döngüsü ile FizzBuzz çözümü yaz",

        # Karmaşık görevler → gpt-4o bekleniyor
        "Bu kodu refactor et, performans analizi yap ve sonra birim testlerini yaz",
        "Mikroservis mimarisini tasarla, adım adım API endpointlerini planla ve güvenlik stratejisini belirle",
        "Mevcut veritabanı şemasını analiz et, optimizasyon önerileri sun ve migration planı oluştur",
    ]

    print(f"{'Görev':<65} {'Model':<15} {'Skor':<6}")
    print("-" * 90)

    for task in tasks:
        details = router.route_with_details(task)
        # Görev metnini kısalt (görüntü için)
        task_short = task[:62] + "..." if len(task) > 62 else task
        print(
            f"{task_short:<65} {details['model']:<15} {details['complexity_score']:<6}"
        )

    # İstatistikler
    print(router.get_stats())

    # Maliyet tasarrufu hesabı
    print()
    print("💰 Maliyet Tasarrufu Hesabı (10,000 çağrı/gün senaryosu):")
    print("-" * 55)
    cheap = router._route_counts.get("gpt-4o-mini", 0)
    expensive = router._route_counts.get("gpt-4o", 0)
    total = cheap + expensive
    if total > 0:
        cheap_ratio = cheap / total
        expensive_ratio = expensive / total
        # 1000 token ortalama varsayımı
        all_expensive = 10000 * 0.01  # $100/gün
        all_cheap = 10000 * 0.0006    # $6/gün
        mixed = 10000 * (cheap_ratio * 0.0006 + expensive_ratio * 0.01)

        print(f"  Hep GPT-4o:      ${all_expensive:.0f}/gün")
        print(f"  Hep GPT-4o-mini: ${all_cheap:.0f}/gün")
        print(f"  Akıllı Routing:  ${mixed:.0f}/gün (model dağılımı: %{cheap_ratio*100:.0f} ucuz, %{expensive_ratio*100:.0f} pahalı)")
        savings = all_expensive - mixed
        print(f"  Tasarruf:        ${savings:.0f}/gün (%{savings/all_expensive*100:.0f})")
