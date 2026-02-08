"""
Cost Tracker - Maliyet Takibi
===============================
Her LLM çağrısının maliyetini takip eder ve bütçe limiti koyar.

Neden önemli?
-------------
Her LLM çağrısı para! Bir agent döngüde çalıştığında,
farkında olmadan yüzlerce çağrı yapabilir. CostTracker:
- Her çağrının maliyetini hesaplar
- Toplam maliyeti takip eder
- Bütçe limitini aştığında uyarır

Kullanım:
    from shared.telemetry.cost_tracker import CostTracker
    
    tracker = CostTracker(budget_limit=0.10)  # Maksimum 10 cent
    
    tracker.add_usage(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
    
    print(tracker.get_report())
    
    if tracker.is_over_budget():
        print("⚠️ Bütçe aşıldı! Agent durduruluyor.")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# Model fiyatları (USD per 1M token)
# Not: Bu fiyatlar değişebilir! Güncel fiyatlar için OpenAI'ı kontrol edin.
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


@dataclass
class UsageRecord:
    """Tek bir API çağrısının kullanım kaydı."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    label: str = ""  # Ne için kullanıldı? (opsiyonel)


class CostTracker:
    """
    LLM API maliyet takipçisi.
    
    Kullanım:
        # Tracker oluştur, bütçe limiti: 1 USD
        tracker = CostTracker(budget_limit=1.0)
        
        # Her LLM çağrısından sonra kullanımı kaydet
        tracker.add_usage(
            input_tokens=500,
            output_tokens=200,
            model="gpt-4o-mini",
            label="planner_call"
        )
        
        # Maliyet kontrolü
        if tracker.is_over_budget():
            print("Dur! Bütçe aşıldı!")
        
        # Rapor al
        print(tracker.get_report())
    """
    
    def __init__(self, budget_limit: float = 1.0):
        """
        CostTracker oluştur.
        
        Parametreler:
            budget_limit: Maksimum harcama limiti (USD)
        """
        self.budget_limit = budget_limit    # USD cinsinden bütçe limiti
        self.records: list[UsageRecord] = []  # Tüm kullanım kayıtları
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini",
    ) -> float:
        """
        Token kullanımından maliyet hesapla.
        
        Parametreler:
            input_tokens: Giriş token sayısı
            output_tokens: Çıkış token sayısı
            model: Kullanılan model
        
        Döndürür:
            float: Maliyet (USD)
        
        Örnek:
            cost = tracker.calculate_cost(1000, 500, "gpt-4o-mini")
            print(f"Maliyet: ${cost:.6f}")
            # Maliyet: $0.000450
        """
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def add_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini",
        label: str = "",
    ) -> float:
        """
        Yeni bir kullanım kaydı ekle.
        
        Parametreler:
            input_tokens: Giriş token sayısı
            output_tokens: Çıkış token sayısı
            model: Kullanılan model
            label: Açıklama (ne için kullanıldı?)
        
        Döndürür:
            float: Bu çağrının maliyeti (USD)
        """
        cost = self.calculate_cost(input_tokens, output_tokens, model)
        
        record = UsageRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            label=label,
        )
        self.records.append(record)
        
        return cost
    
    @property
    def total_cost(self) -> float:
        """Toplam maliyet (USD)."""
        return sum(r.cost for r in self.records)
    
    @property
    def total_input_tokens(self) -> int:
        """Toplam giriş token sayısı."""
        return sum(r.input_tokens for r in self.records)
    
    @property
    def total_output_tokens(self) -> int:
        """Toplam çıkış token sayısı."""
        return sum(r.output_tokens for r in self.records)
    
    @property
    def total_calls(self) -> int:
        """Toplam API çağrı sayısı."""
        return len(self.records)
    
    def is_over_budget(self) -> bool:
        """Bütçe aşıldı mı?"""
        return self.total_cost >= self.budget_limit
    
    def remaining_budget(self) -> float:
        """Kalan bütçe (USD)."""
        return max(0, self.budget_limit - self.total_cost)
    
    def budget_usage_percent(self) -> float:
        """Bütçe kullanım yüzdesi."""
        if self.budget_limit <= 0:
            return 100.0
        return (self.total_cost / self.budget_limit) * 100
    
    def get_report(self) -> str:
        """
        Detaylı maliyet raporu döndür.
        
        Örnek çıktı:
            💰 Maliyet Raporu
            ════════════════════════════
            Toplam Çağrı:   5
            Input Tokens:   2,500
            Output Tokens:  1,200
            Toplam Maliyet: $0.001095
            Bütçe Limiti:   $1.000000
            Kalan Bütçe:    $0.998905
            Kullanım:       0.1%
            ════════════════════════════
        """
        lines = [
            "",
            "💰 Maliyet Raporu",
            "═" * 35,
            f"Toplam Çağrı:   {self.total_calls}",
            f"Input Tokens:   {self.total_input_tokens:,}",
            f"Output Tokens:  {self.total_output_tokens:,}",
            f"Toplam Maliyet: ${self.total_cost:.6f}",
            f"Bütçe Limiti:   ${self.budget_limit:.6f}",
            f"Kalan Bütçe:    ${self.remaining_budget():.6f}",
            f"Kullanım:       {self.budget_usage_percent():.1f}%",
        ]
        
        if self.is_over_budget():
            lines.append("⚠️  BÜTÇE AŞILDI!")
        elif self.budget_usage_percent() > 80:
            lines.append("⚠️  Bütçe %80'in üzerinde!")
        
        lines.append("═" * 35)
        
        # En pahalı çağrıları göster
        if self.records:
            sorted_records = sorted(self.records, key=lambda r: r.cost, reverse=True)
            lines.append("\nEn Pahalı 3 Çağrı:")
            for r in sorted_records[:3]:
                label = f" ({r.label})" if r.label else ""
                lines.append(
                    f"  ${r.cost:.6f} | {r.model} | "
                    f"in:{r.input_tokens} out:{r.output_tokens}{label}"
                )
        
        return "\n".join(lines)
