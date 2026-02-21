"""
Maliyet Koruyucu (Cost Guard)
===============================
Token harcamasını izler, bütçe limiti koyar ve aşımları engeller.

Neden CostGuard Gerekli?
-------------------------
Agent'lar döngüde çalışır. Bir bug veya kötü prompt yüzünden
sonsuz döngüye giren agent, kısa sürede yüzlerce API çağrısı yapabilir.
CostGuard olmadan bu durum:
  - Sonsuz döngü × GPT-4o = felaket maliyeti 💸
  - Farkına varana kadar yüzlerce dolar harcanabilir

CostGuard 3 seviyede koruma sağlar:
  1. per_call_limit: Tek bir çağrının maliyetini sınırlar
     → Yanlışlıkla dev bir prompt göndermeyi engeller
  2. warning_threshold: Toplam bütçenin %X'ine ulaşınca uyarır
     → "Dikkat, bütçenin %80'i kullanıldı!"
  3. budget_limit: Toplam bütçe aşılınca durdurur
     → "DURDUR! Bütçe aşıldı, daha fazla çağrı yapılamaz"

shared/telemetry/cost_tracker.py ile Farkı:
  CostTracker sadece takip eder (pasif).
  CostGuard hem takip eder hem de ENGELLER (aktif).

Kullanım:
    from optimization.cost_guard import CostGuard

    guard = CostGuard(budget_limit=1.0, per_call_limit=0.10)

    # Her LLM çağrısından ÖNCE kontrol et
    if guard.can_proceed():
        response = await llm.chat(message)
        guard.record_call(input_tokens=500, output_tokens=200, model="gpt-4o-mini")
    else:
        print("Bütçe aşıldı, çağrı engellendi!")

    print(guard.get_status())
"""

import sys
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# shared/ modülünü import edebilmek için path ayarı
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from shared.telemetry.cost_tracker import CostTracker, MODEL_PRICING

logger = get_logger("optimization.cost_guard")


# ============================================================
# Uyarı Seviyeleri
# ============================================================

@dataclass
class AlertEvent:
    """
    Bir uyarı olayını temsil eder.

    Bütçe eşikleri aşıldığında AlertEvent oluşturulur.
    Bu olaylar loglanır ve geçmişte tutulur.

    Alanlar:
        timestamp: Uyarı zamanı
        level: Uyarı seviyesi ("WARNING" veya "CRITICAL")
        message: Uyarı mesajı
        usage_percent: Bütçe kullanım yüzdesi
    """
    timestamp: datetime
    level: str           # "WARNING" veya "CRITICAL"
    message: str
    usage_percent: float


# ============================================================
# Ana CostGuard Sınıfı
# ============================================================

class CostGuard:
    """
    Agent maliyet koruyucu — token harcamasını izler ve engeller.

    3 Katmanlı Koruma:
    ──────────────────
    Katman 1: Çağrı Bazlı Limit (per_call_limit)
        → Tek bir çağrı bu limiti aşarsa uyarı verir
        → Örn: Yanlışlıkla 100K token'lık prompt göndermeyi yakalar

    Katman 2: Uyarı Eşiği (warning_threshold)
        → Toplam bütçenin belirli %'sine ulaşılınca uyarı
        → Varsayılan: %80'de uyar
        → Agent çalışmaya devam eder ama logda uyarı görürsünüz

    Katman 3: Durdurma Eşiği (budget_limit)
        → Toplam bütçe aşıldığında can_proceed() False döner
        → Agent durdurulmalı!

    Kullanım:
        guard = CostGuard(
            budget_limit=1.0,       # Toplam: $1.00
            per_call_limit=0.10,    # Tek çağrı: max $0.10
            warning_threshold=0.80, # %80'de uyar
        )

        # Agent döngüsünde:
        while guard.can_proceed():
            response = await llm.chat(message)
            guard.record_call(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model="gpt-4o-mini",
            )
    """

    def __init__(
        self,
        budget_limit: float = 1.0,
        per_call_limit: float = 0.10,
        warning_threshold: float = 0.80,
    ):
        """
        CostGuard oluştur.

        Parametreler:
            budget_limit: Toplam bütçe limiti (USD)
                          Aşıldığında can_proceed() False döner
            per_call_limit: Tek çağrı maliyet limiti (USD)
                            Aşılırsa uyarı verilir (ama engellenmez)
            warning_threshold: Uyarı eşiği (0.0 - 1.0 arası)
                               Örn: 0.80 = bütçenin %80'inde uyar
        """
        self.budget_limit = budget_limit
        self.per_call_limit = per_call_limit
        self.warning_threshold = warning_threshold

        # İç maliyet takipçisi (shared modülünden)
        self._tracker = CostTracker(budget_limit=budget_limit)

        # Uyarı geçmişi
        self.alerts: list[AlertEvent] = []

        # İstatistikler
        self._calls_blocked = 0  # Engellenen çağrı sayısı
        self._warnings_issued = 0  # Verilen uyarı sayısı

        self.logger = get_logger("cost_guard")
        self.logger.info(
            f"💰 CostGuard başlatıldı: bütçe=${budget_limit:.2f}, "
            f"çağrı_limiti=${per_call_limit:.2f}, "
            f"uyarı_eşiği=%{warning_threshold*100:.0f}"
        )

    def can_proceed(self) -> bool:
        """
        Yeni bir LLM çağrısı yapılabilir mi?

        Bu method her çağrıdan ÖNCE kontrol edilmelidir.
        Bütçe aşılmışsa False döner → Agent durmalı!

        Döndürür:
            bool: True ise çağrı yapılabilir, False ise bütçe aşıldı

        Örnek:
            if guard.can_proceed():
                response = await llm.chat(message)
            else:
                print("Bütçe aşıldı!")
                break  # Agent döngüsünden çık
        """
        if self._tracker.is_over_budget():
            self._calls_blocked += 1
            self.logger.error(
                f"🛑 Çağrı engellendi! Bütçe aşıldı: "
                f"${self._tracker.total_cost:.6f} >= ${self.budget_limit:.6f}"
            )
            return False
        return True

    def record_call(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini",
        label: str = "",
    ) -> dict:
        """
        Bir LLM çağrısının maliyetini kaydet ve kontrol et.

        Bu method her çağrıdan SONRA çağrılmalıdır.
        Maliyeti kaydeder ve gerekirse uyarı verir.

        Parametreler:
            input_tokens: Giriş token sayısı
            output_tokens: Çıkış token sayısı
            model: Kullanılan model
            label: Açıklama (ne için kullanıldı?)

        Döndürür:
            dict: {
                "cost": float,           # Bu çağrının maliyeti
                "total_cost": float,      # Toplam maliyet
                "budget_remaining": float, # Kalan bütçe
                "usage_percent": float,   # Kullanım yüzdesi
                "alert": str | None,      # Uyarı mesajı (varsa)
            }
        """
        # Maliyeti hesapla ve kaydet
        cost = self._tracker.add_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            label=label,
        )

        alert_message = None
        usage_pct = self._tracker.budget_usage_percent()

        # Kontrol 1: Tek çağrı limiti aşıldı mı?
        if cost > self.per_call_limit:
            alert_message = (
                f"⚠️ Tek çağrı limiti aşıldı! "
                f"${cost:.6f} > ${self.per_call_limit:.6f} "
                f"(model={model}, in={input_tokens}, out={output_tokens})"
            )
            self._add_alert("WARNING", alert_message, usage_pct)
            self.logger.warning(alert_message)

        # Kontrol 2: Uyarı eşiği aşıldı mı?
        elif usage_pct >= self.warning_threshold * 100:
            # Bütçe aşıldıysa kritik, yoksa uyarı
            if self._tracker.is_over_budget():
                alert_message = (
                    f"🛑 BÜTÇE AŞILDI! "
                    f"${self._tracker.total_cost:.6f} >= ${self.budget_limit:.6f}"
                )
                self._add_alert("CRITICAL", alert_message, usage_pct)
                self.logger.error(alert_message)
            else:
                alert_message = (
                    f"⚠️ Bütçe uyarısı: %{usage_pct:.1f} kullanıldı "
                    f"(${self._tracker.total_cost:.6f} / ${self.budget_limit:.6f})"
                )
                self._add_alert("WARNING", alert_message, usage_pct)
                self.logger.warning(alert_message)

        return {
            "cost": cost,
            "total_cost": self._tracker.total_cost,
            "budget_remaining": self._tracker.remaining_budget(),
            "usage_percent": usage_pct,
            "alert": alert_message,
        }

    def _add_alert(self, level: str, message: str, usage_pct: float):
        """Uyarı geçmişine ekle."""
        self.alerts.append(AlertEvent(
            timestamp=datetime.now(),
            level=level,
            message=message,
            usage_percent=usage_pct,
        ))
        self._warnings_issued += 1

    def get_status(self) -> str:
        """
        Mevcut durumu özetleyen metin döndür.

        Döndürür:
            str: Durum raporu
        """
        usage_pct = self._tracker.budget_usage_percent()

        # Durum göstergesi
        if self._tracker.is_over_budget():
            status_icon = "🛑"
            status_text = "BÜTÇE AŞILDI"
        elif usage_pct >= self.warning_threshold * 100:
            status_icon = "⚠️"
            status_text = "UYARI BÖLGESİ"
        else:
            status_icon = "✅"
            status_text = "NORMAL"

        # İlerleme çubuğu
        bar_length = 20
        filled = int(min(usage_pct / 100, 1.0) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        return (
            f"\n{'='*45}\n"
            f"{status_icon} CostGuard Durumu: {status_text}\n"
            f"{'='*45}\n"
            f"  Bütçe:     ${self.budget_limit:.2f}\n"
            f"  Harcanan:  ${self._tracker.total_cost:.6f}\n"
            f"  Kalan:     ${self._tracker.remaining_budget():.6f}\n"
            f"  Kullanım:  [{bar}] {usage_pct:.1f}%\n"
            f"  Çağrı:     {self._tracker.total_calls}\n"
            f"  Engellenen:{self._calls_blocked}\n"
            f"  Uyarılar:  {self._warnings_issued}\n"
            f"{'='*45}"
        )

    def get_detailed_report(self) -> str:
        """
        Detaylı maliyet raporu döndür.

        CostTracker'ın raporunu + CostGuard uyarılarını içerir.

        Döndürür:
            str: Detaylı rapor
        """
        report = self.get_status()
        report += "\n" + self._tracker.get_report()

        # Uyarı geçmişi
        if self.alerts:
            report += "\n\n📢 Uyarı Geçmişi:\n"
            for alert in self.alerts[-5:]:  # Son 5 uyarı
                report += (
                    f"  [{alert.level}] {alert.timestamp.strftime('%H:%M:%S')} "
                    f"— {alert.message}\n"
                )

        return report

    def reset(self):
        """
        CostGuard'ı sıfırla.

        Yeni bir görev/oturum başlatırken kullanışlı.
        Tüm kayıtlar ve uyarılar sıfırlanır.
        """
        self._tracker = CostTracker(budget_limit=self.budget_limit)
        self.alerts = []
        self._calls_blocked = 0
        self._warnings_issued = 0
        self.logger.info("🔄 CostGuard sıfırlandı")


# ============================================================
# Ana çalıştırma bloğu — Demo
# ============================================================

if __name__ == "__main__":
    print("💰 CostGuard Demo")
    print("=" * 50)
    print()
    print("Bu demo, bir agent'ın 20 API çağrısı yapmasını simüle eder.")
    print("Bütçe limiti $0.005 olarak ayarlanmıştır.")
    print()

    # Düşük bütçe limiti koy (demo için)
    guard = CostGuard(
        budget_limit=0.005,       # Toplam: 0.5 cent
        per_call_limit=0.002,     # Tek çağrı: 0.2 cent
        warning_threshold=0.70,   # %70'te uyar
    )

    # Simüle edilmiş API çağrıları
    for i in range(1, 21):
        if not guard.can_proceed():
            print(f"\n🛑 Çağrı #{i}: ENGELLENDİ — Bütçe aşıldı!")
            break

        # Farklı boyutlarda çağrılar simüle et
        input_tokens = 200 + (i * 50)
        output_tokens = 100 + (i * 30)

        result = guard.record_call(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model="gpt-4o-mini",
            label=f"çağrı_{i}",
        )

        print(
            f"  Çağrı #{i:2d}: maliyet=${result['cost']:.6f} | "
            f"toplam=${result['total_cost']:.6f} | "
            f"kalan=${result['budget_remaining']:.6f} | "
            f"%{result['usage_percent']:.1f}"
        )

        if result["alert"]:
            print(f"           → {result['alert']}")

    # Son durum
    print(guard.get_detailed_report())
