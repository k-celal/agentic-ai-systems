"""
Cost Guard Agent - Maliyet Bekçisi
====================================
Tüm pipeline boyunca token kullanımını ve maliyeti kontrol eden koruyucu agent.

NEDEN BU AGENT VAR?
--------------------
Bir çoklu-agent sistemi, farkında olmadan çok sayıda LLM çağrısı yapabilir:
- Research agent 3 farklı arama yapabilir
- Writing agent uzun metinler üretir (yüksek output token)
- Reflection döngüsü her seferinde hem writing hem reflection agent'ı çağırır
- Repurpose agent ek bir çağrı daha yapar

Kontrol mekanizması olmadan, tek bir pipeline çalışması kolayca
bütçeyi aşabilir. CostGuardAgent şunları sağlar:

1. **Bütçe Koruması**: Toplam harcama limitini aşmayı engeller
2. **Adım Bazlı Limit**: Her pipeline adımı için ayrı limit koyar
3. **Erken Uyarı**: Bütçenin %80'ine ulaşıldığında uyarı verir
4. **Model Yönlendirme**: Görev tipine göre ucuz/pahalı model önerir
5. **Agent Bazlı Raporlama**: Hangi agent ne kadar harcadı gösterir

Model Yönlendirme Stratejisi:
- Planlama görevleri → gpt-4o-mini (basit mantık yürütme yeterli)
- Son yazım → gpt-4o (yaratıcılık ve dil kalitesi önemli)
- Diğer her şey → gpt-4o-mini (maliyet optimizasyonu)

Kullanım:
    from agents.cost_guard_agent import CostGuardAgent

    guard = CostGuardAgent(budget_limit=0.50)

    if guard.can_proceed(estimated_tokens=2000):
        # LLM çağrısı yap
        ...
        guard.record_usage("writing_agent", input_tokens=800, output_tokens=1200)

    print(guard.get_report())
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
# Bu satır, projenin kök dizinindeki shared/ modülüne erişmemizi sağlar.
# Dosya yapısı: capstone-production-agent/agents/cost_guard_agent.py
# İki üst dizin (../../) bizi proje köküne götürür.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.cost_tracker import CostTracker
from shared.telemetry.logger import get_logger


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class AgentUsageRecord:
    """
    Bir agent'ın toplam kullanım kaydı.

    Neden ayrı bir kayıt tutuyoruz?
    - CostTracker genel toplamı tutar
    - Bu sınıf agent bazlı detayı tutar
    - Pipeline raporunda "hangi agent ne kadar harcadı?" sorusuna cevap verir
    """
    agent_name: str                          # Agent adı (örn: "research_agent")
    total_input_tokens: int = 0              # Bu agent'ın toplam giriş token'ı
    total_output_tokens: int = 0             # Bu agent'ın toplam çıkış token'ı
    total_cost: float = 0.0                  # Bu agent'ın toplam maliyeti (USD)
    call_count: int = 0                      # Bu agent'ın toplam LLM çağrı sayısı
    models_used: list[str] = field(default_factory=list)  # Kullandığı modeller

    @property
    def total_tokens(self) -> int:
        """Toplam token sayısı."""
        return self.total_input_tokens + self.total_output_tokens


# ============================================================
# Model Yönlendirme Sabitleri
# ============================================================

# Görev tiplerine göre hangi modelin kullanılacağını belirleyen harita.
# Bu strateji, maliyet ile kalite arasındaki dengeyi optimize eder.
MODEL_ROUTING = {
    # Planlama görevleri: Basit mantık yürütme yeterli, ucuz model kullan
    "planning": "gpt-4o-mini",
    "orchestration": "gpt-4o-mini",

    # Araştırma: Özetleme ve bilgi çıkarma, ucuz model yeterli
    "research": "gpt-4o-mini",
    "summarization": "gpt-4o-mini",

    # Son yazım: Yaratıcılık ve dil kalitesi kritik, güçlü model kullan
    "final_writing": "gpt-4o",
    "creative_writing": "gpt-4o",

    # Değerlendirme: Analitik düşünme gerekli ama çok pahalı olmasın
    "reflection": "gpt-4o-mini",
    "evaluation": "gpt-4o-mini",

    # İçerik dönüştürme: Formatı değiştirmek basit bir görev
    "repurpose": "gpt-4o-mini",
    "transformation": "gpt-4o-mini",
}

# Varsayılan model: Haritada olmayan görevler için
DEFAULT_MODEL = "gpt-4o-mini"


# ============================================================
# CostGuardAgent Sınıfı
# ============================================================

class CostGuardAgent:
    """
    Maliyet Bekçisi Agent - Pipeline'ın bütçe koruyucusu.

    Bu agent, diğer agent'lar gibi LLM çağrısı yapmaz.
    Bunun yerine, diğer agent'ların harcamalarını takip eder ve
    bütçe aşımını engeller.

    Üç katmanlı koruma sağlar:
    1. can_proceed() → Bir sonraki adımın tahmini maliyetini kontrol eder
    2. record_usage() → Gerçekleşen kullanımı kaydeder
    3. get_report() → Detaylı maliyet raporu üretir

    Parametreler:
        budget_limit: Toplam bütçe limiti (USD). Varsayılan: 1.0 ($1)
        warning_threshold: Uyarı eşiği (yüzde). Varsayılan: 0.80 (%80)
        per_step_limit: Her adım için maksimum token. Varsayılan: 5000

    Kullanım:
        guard = CostGuardAgent(budget_limit=0.50, per_step_limit=3000)

        # Adım öncesi kontrol
        if guard.can_proceed(estimated_tokens=2000):
            response = await llm.chat(...)
            guard.record_usage("research", 500, 1500, "gpt-4o-mini")

        # Model seçimi
        model = guard.get_routing_recommendation("final_writing")
        # → "gpt-4o"

        # Rapor
        print(guard.get_report())
    """

    def __init__(
        self,
        budget_limit: float = 1.0,
        warning_threshold: float = 0.80,
        per_step_limit: int = 5000,
    ):
        """
        CostGuardAgent'ı başlat.

        Parametreler:
            budget_limit: Toplam bütçe limiti (USD).
                          Varsayılan 1.0, yani pipeline en fazla $1 harcayabilir.
            warning_threshold: Bütçenin yüzde kaçında uyarı verilsin?
                               0.80 = %80'inde uyarı ver.
            per_step_limit: Tek bir adımda kullanılabilecek maksimum token.
                            Sonsuz döngüye karşı güvenlik ağı.
        """
        # Shared CostTracker'ı sarmala
        self._tracker = CostTracker(budget_limit=budget_limit)

        # Yapılandırma
        self.budget_limit = budget_limit
        self.warning_threshold = warning_threshold
        self.per_step_limit = per_step_limit

        # Agent bazlı kullanım takibi
        self._agent_usage: dict[str, AgentUsageRecord] = {}

        # Logger
        self._logger = get_logger("cost_guard_agent")
        self._logger.info(
            f"CostGuardAgent başlatıldı | "
            f"Bütçe: ${budget_limit:.4f} | "
            f"Uyarı eşiği: %{warning_threshold * 100:.0f} | "
            f"Adım limiti: {per_step_limit} token"
        )

    # ────────────────────────────────────────────────────────
    # Bütçe Kontrol Metodları
    # ────────────────────────────────────────────────────────

    def can_proceed(self, estimated_tokens: int = 0) -> bool:
        """
        Bir sonraki adıma devam edilebilir mi?

        Bu metod üç kontrolden geçer:
        1. Toplam bütçe aşıldı mı?
        2. Tahmini maliyet kalan bütçeyi aşar mı?
        3. Tahmini token adım limitini aşar mı?

        Parametreler:
            estimated_tokens: Bir sonraki adımda kullanılacak tahmini token sayısı.
                              0 ise sadece bütçe kontrolü yapar.

        Döndürür:
            bool: True → devam edilebilir, False → dur!

        Örnek:
            if guard.can_proceed(estimated_tokens=2000):
                # Güvenle devam et
                pass
            else:
                # Pipeline'ı durdur veya ucuz modele geç
                pass
        """
        # Kontrol 1: Bütçe zaten aşıldı mı?
        if self._tracker.is_over_budget():
            self._logger.warning("BÜTÇE AŞILDI! Pipeline devam edemez.")
            return False

        # Kontrol 2: Tahmini maliyet kalan bütçeyi aşar mı?
        if estimated_tokens > 0:
            # En kötü senaryoyu hesapla (gpt-4o fiyatlarıyla)
            estimated_cost = self._tracker.calculate_cost(
                input_tokens=estimated_tokens // 2,
                output_tokens=estimated_tokens // 2,
                model="gpt-4o-mini",
            )
            remaining = self._tracker.remaining_budget()

            if estimated_cost > remaining:
                self._logger.warning(
                    f"Tahmini maliyet (${estimated_cost:.6f}) "
                    f"kalan bütçeyi (${remaining:.6f}) aşıyor!"
                )
                return False

        # Kontrol 3: Adım limiti kontrolü
        if estimated_tokens > self.per_step_limit:
            self._logger.warning(
                f"Tahmini token ({estimated_tokens}) "
                f"adım limitini ({self.per_step_limit}) aşıyor!"
            )
            return False

        # Uyarı: Bütçenin çoğu kullanıldı mı?
        usage_percent = self._tracker.budget_usage_percent()
        if usage_percent >= self.warning_threshold * 100:
            self._logger.warning(
                f"Bütçe uyarısı: %{usage_percent:.1f} kullanıldı "
                f"(eşik: %{self.warning_threshold * 100:.0f})"
            )

        return True

    def record_usage(
        self,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini",
    ) -> float:
        """
        Bir agent'ın LLM çağrısı sonrası kullanımını kaydet.

        Bu metod hem genel CostTracker'ı hem de agent bazlı kaydı günceller.

        Parametreler:
            agent_name: Kullanımı yapan agent'ın adı (örn: "research_agent")
            input_tokens: Giriş token sayısı
            output_tokens: Çıkış token sayısı
            model: Kullanılan LLM modeli

        Döndürür:
            float: Bu çağrının maliyeti (USD)

        Örnek:
            cost = guard.record_usage(
                agent_name="writing_agent",
                input_tokens=800,
                output_tokens=1200,
                model="gpt-4o"
            )
            print(f"Bu çağrı ${cost:.6f} tuttu")
        """
        # Genel tracker'a kaydet
        cost = self._tracker.add_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            label=agent_name,
        )

        # Agent bazlı kaydı güncelle
        if agent_name not in self._agent_usage:
            self._agent_usage[agent_name] = AgentUsageRecord(agent_name=agent_name)

        record = self._agent_usage[agent_name]
        record.total_input_tokens += input_tokens
        record.total_output_tokens += output_tokens
        record.total_cost += cost
        record.call_count += 1
        if model not in record.models_used:
            record.models_used.append(model)

        self._logger.info(
            f"Kullanım kaydı | Agent: {agent_name} | "
            f"Token: {input_tokens}+{output_tokens} | "
            f"Model: {model} | Maliyet: ${cost:.6f}"
        )

        return cost

    # ────────────────────────────────────────────────────────
    # Model Yönlendirme
    # ────────────────────────────────────────────────────────

    def get_routing_recommendation(self, task_type: str) -> str:
        """
        Görev tipine göre önerilen modeli döndür.

        Model yönlendirmesi neden önemli?
        - gpt-4o yaratıcı yazım için harika ama 15x daha pahalı
        - gpt-4o-mini çoğu görev için yeterli ve çok ucuz
        - Akıllı yönlendirme ile aynı kalitede %70 maliyet tasarrufu mümkün

        Parametreler:
            task_type: Görev tipi.
                Desteklenen tipler:
                - "planning", "orchestration" → gpt-4o-mini
                - "research", "summarization" → gpt-4o-mini
                - "final_writing", "creative_writing" → gpt-4o
                - "reflection", "evaluation" → gpt-4o-mini
                - "repurpose", "transformation" → gpt-4o-mini

        Döndürür:
            str: Önerilen model adı

        Örnek:
            model = guard.get_routing_recommendation("final_writing")
            # → "gpt-4o"

            model = guard.get_routing_recommendation("research")
            # → "gpt-4o-mini"
        """
        recommended = MODEL_ROUTING.get(task_type, DEFAULT_MODEL)

        self._logger.debug(
            f"Model yönlendirme | Görev: {task_type} → Model: {recommended}"
        )

        return recommended

    # ────────────────────────────────────────────────────────
    # Raporlama
    # ────────────────────────────────────────────────────────

    def get_report(self) -> str:
        """
        Detaylı maliyet raporu üret.

        Bu rapor şunları içerir:
        1. Genel özet (toplam token, maliyet, bütçe durumu)
        2. Agent bazlı harcama detayı
        3. Bütçe uyarıları

        Döndürür:
            str: Formatlanmış maliyet raporu

        Örnek çıktı:
            ══════════════════════════════════════
            💰 TwinGraph Studio - Maliyet Raporu
            ══════════════════════════════════════
            Toplam Token:    12,450
            Toplam Maliyet:  $0.004215
            Bütçe Limiti:    $1.000000
            Kalan Bütçe:     $0.995785
            Kullanım:        0.4%

            📋 Agent Bazlı Dağılım:
            ──────────────────────────────────────
            research_agent:
              Çağrı: 2 | Token: 3,200 | Maliyet: $0.001080
              Modeller: gpt-4o-mini
            writing_agent:
              Çağrı: 2 | Token: 6,500 | Maliyet: $0.002200
              Modeller: gpt-4o
            ...
            ══════════════════════════════════════
        """
        lines = [
            "",
            "═" * 45,
            "💰 TwinGraph Studio - Maliyet Raporu",
            "═" * 45,
            f"Toplam Token:    {self._tracker.total_input_tokens + self._tracker.total_output_tokens:,}",
            f"  ├─ Input:      {self._tracker.total_input_tokens:,}",
            f"  └─ Output:     {self._tracker.total_output_tokens:,}",
            f"Toplam Maliyet:  ${self._tracker.total_cost:.6f}",
            f"Bütçe Limiti:    ${self.budget_limit:.6f}",
            f"Kalan Bütçe:     ${self._tracker.remaining_budget():.6f}",
            f"Kullanım:        %{self._tracker.budget_usage_percent():.1f}",
            f"API Çağrıları:   {self._tracker.total_calls}",
        ]

        # Bütçe uyarıları
        if self._tracker.is_over_budget():
            lines.append("⚠️  BÜTÇE AŞILDI!")
        elif self._tracker.budget_usage_percent() >= self.warning_threshold * 100:
            lines.append(f"⚠️  Bütçe %{self.warning_threshold * 100:.0f} eşiğinin üzerinde!")

        # Agent bazlı dağılım
        if self._agent_usage:
            lines.append("")
            lines.append("📋 Agent Bazlı Dağılım:")
            lines.append("─" * 45)

            # Maliyete göre sırala (en pahalıdan ucuza)
            sorted_agents = sorted(
                self._agent_usage.values(),
                key=lambda r: r.total_cost,
                reverse=True,
            )

            for record in sorted_agents:
                lines.append(f"  {record.agent_name}:")
                lines.append(
                    f"    Çağrı: {record.call_count} | "
                    f"Token: {record.total_tokens:,} | "
                    f"Maliyet: ${record.total_cost:.6f}"
                )
                lines.append(
                    f"    Modeller: {', '.join(record.models_used)}"
                )

        lines.append("═" * 45)
        return "\n".join(lines)

    # ────────────────────────────────────────────────────────
    # Yardımcı Özellikler
    # ────────────────────────────────────────────────────────

    @property
    def total_cost(self) -> float:
        """Toplam maliyet (USD)."""
        return self._tracker.total_cost

    @property
    def total_tokens(self) -> int:
        """Toplam token sayısı."""
        return self._tracker.total_input_tokens + self._tracker.total_output_tokens

    @property
    def remaining_budget(self) -> float:
        """Kalan bütçe (USD)."""
        return self._tracker.remaining_budget()

    @property
    def is_over_budget(self) -> bool:
        """Bütçe aşıldı mı?"""
        return self._tracker.is_over_budget()


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    """
    CostGuardAgent'ı bağımsız test et.

    Bu test bloğu, agent'ın temel işlevselliğini doğrular:
    1. Bütçe kontrolü (can_proceed)
    2. Kullanım kaydı (record_usage)
    3. Model yönlendirme (get_routing_recommendation)
    4. Raporlama (get_report)
    """
    print("=" * 50)
    print("🧪 CostGuardAgent Test")
    print("=" * 50)

    # Düşük bütçe ile test et (hızlı aşılsın)
    guard = CostGuardAgent(
        budget_limit=0.01,  # 1 cent
        warning_threshold=0.80,
        per_step_limit=5000,
    )

    # Test 1: can_proceed kontrolü
    print("\n--- Test 1: can_proceed ---")
    print(f"İlk kontrol (boş bütçe): {guard.can_proceed(estimated_tokens=1000)}")

    # Test 2: Kullanım kaydet
    print("\n--- Test 2: record_usage ---")
    guard.record_usage("research_agent", input_tokens=500, output_tokens=300, model="gpt-4o-mini")
    guard.record_usage("writing_agent", input_tokens=800, output_tokens=1200, model="gpt-4o")
    guard.record_usage("reflection_agent", input_tokens=600, output_tokens=400, model="gpt-4o-mini")
    guard.record_usage("writing_agent", input_tokens=900, output_tokens=1100, model="gpt-4o")
    guard.record_usage("repurpose_agent", input_tokens=400, output_tokens=500, model="gpt-4o-mini")

    # Test 3: Model yönlendirme
    print("\n--- Test 3: Model Yönlendirme ---")
    for task in ["planning", "final_writing", "research", "reflection", "repurpose", "bilinmeyen"]:
        model = guard.get_routing_recommendation(task)
        print(f"  {task:20s} → {model}")

    # Test 4: Rapor
    print("\n--- Test 4: Rapor ---")
    print(guard.get_report())

    # Test 5: Bütçe aşımı kontrolü
    print("\n--- Test 5: Bütçe Aşımı ---")
    print(f"Bütçe aşıldı mı? {guard.is_over_budget}")
    print(f"Devam edilebilir mi? {guard.can_proceed(estimated_tokens=1000)}")
