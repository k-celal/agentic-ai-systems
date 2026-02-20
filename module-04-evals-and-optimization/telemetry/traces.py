"""
İzleme Toplayıcı (Trace Collector)
=====================================
Agent'ın her adımını detaylı olarak izler: zamanlama, maliyet, sonuç.

Neden İzleme (Tracing) Gerekli?
---------------------------------
Agent'lar birçok adım atar ve her adımın:
  - Ne kadar sürdüğünü
  - Ne kadar maliyet oluşturduğunu
  - Ne sonuç ürettiğini
bilmek, debugging ve optimizasyon için kritiktir.

shared/telemetry/logger.py'deki AgentTracer ile Farkı:
  AgentTracer → Basit loglama (sadece ne oldu?)
  TraceCollector → Detaylı izleme (ne oldu + ne kadar sürdü + ne kadar tuttu)

Kullanım senaryoları:
  1. Production debugging: "Bu görev neden 10 saniye sürdü?"
  2. Maliyet analizi: "Hangi adım en pahalı?"
  3. Performans optimizasyonu: "Darboğaz nerede?"
  4. Eval entegrasyonu: Her eval'in detaylı izini sakla

Kullanım:
    from telemetry.traces import TraceCollector

    tracer = TraceCollector(task_name="hava_durumu")

    tracer.start()
    tracer.add_step("düşünme", content="Hava durumunu sormalıyım", tokens=300, cost=0.002)
    tracer.add_step("tool_çağrısı", content="get_weather(Istanbul)", duration=1.2)
    tracer.add_step("cevap", content="İstanbul'da hava 15°C", tokens=100, cost=0.001)
    tracer.end(success=True)

    print(tracer.get_report())
"""

import sys
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

# shared/ modülünü import edebilmek için path ayarı
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger

logger = get_logger("telemetry.traces")


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class TraceStep:
    """
    İzleme kaydındaki tek bir adım.

    Agent'ın yaptığı her işlem bir TraceStep olarak kaydedilir.
    Bu, görevin tüm yaşam döngüsünü adım adım görmemizi sağlar.

    Adım türleri:
        - "düşünme" (think): LLM'in düşünce/planlama adımı
        - "tool_çağrısı" (tool_call): Tool çağrısı
        - "tool_sonucu" (tool_result): Tool'dan dönen sonuç
        - "cevap" (response): Kullanıcıya verilen cevap
        - "hata" (error): Oluşan bir hata

    Alanlar:
        step_type: Adım türü
        content: Adımın içeriği (düşünce, tool adı, cevap vs.)
        timestamp: Adımın zamanı
        duration: Adımın süresi (saniye, biliniyorsa)
        tokens: Kullanılan token sayısı (LLM adımları için)
        cost: Maliyet (USD, LLM adımları için)
        metadata: Ek bilgiler (tool parametreleri, hata detayı vs.)
    """
    step_type: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    tokens: int = 0
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    """
    Bir görevin tüm izleme kaydı.

    Görevin başından sonuna kadar tüm adımları,
    toplu istatistikleri ve sonucu içerir.

    Alanlar:
        task_name: Görev adı/açıklaması
        steps: Adımların listesi
        start_time: Başlangıç zamanı
        end_time: Bitiş zamanı
        success: Görev başarılı mı?
        total_duration: Toplam süre (saniye)
        total_tokens: Toplam kullanılan token
        total_cost: Toplam maliyet (USD)
    """
    task_name: str
    steps: list[TraceStep] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    total_duration: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0


# ============================================================
# Ana TraceCollector Sınıfı
# ============================================================

class TraceCollector:
    """
    Agent adımlarını detaylı olarak izleyen toplayıcı.

    Bu sınıf ne yapar?
    1. Görev başlangıcını kaydeder
    2. Her adımı zaman damgası, süre ve maliyetiyle birlikte saklar
    3. Görev bitişini kaydeder
    4. Detaylı rapor ve istatistik üretir

    Kullanım:
        tracer = TraceCollector(task_name="hava_durumu_görevi")

        tracer.start()

        # Düşünme adımı
        tracer.add_step(
            step_type="düşünme",
            content="Hava durumunu sormalıyım",
            tokens=300,
            cost=0.002,
        )

        # Tool çağrısı
        tracer.add_step(
            step_type="tool_çağrısı",
            content="get_weather(city='Istanbul')",
            duration=1.2,
            metadata={"tool": "get_weather", "args": {"city": "Istanbul"}},
        )

        # Cevap
        tracer.add_step(
            step_type="cevap",
            content="İstanbul'da hava 15°C ve güneşli.",
            tokens=100,
            cost=0.001,
        )

        tracer.end(success=True)
        print(tracer.get_report())

    Birden fazla görevi izleme:
        collector = TraceCollector("görev_1")
        collector.start()
        # ... adımlar ...
        collector.end(success=True)
        record1 = collector.get_record()

        collector.reset("görev_2")
        collector.start()
        # ... adımlar ...
        collector.end(success=True)
        record2 = collector.get_record()
    """

    def __init__(self, task_name: str = ""):
        """
        TraceCollector oluştur.

        Parametreler:
            task_name: Görev adı/açıklaması
        """
        self.task_name = task_name
        self._steps: list[TraceStep] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._start_datetime: Optional[datetime] = None
        self._success: Optional[bool] = None
        self.logger = get_logger("trace_collector")

    def start(self):
        """
        İzlemeyi başlat.

        Zamanlayıcıyı başlatır ve başlangıcı loglar.
        Her görev için bir kez çağrılmalı.
        """
        self._start_time = time.time()
        self._start_datetime = datetime.now()
        self._steps = []
        self._success = None
        self.logger.info(f"📍 İzleme başlatıldı: {self.task_name}")

    def add_step(
        self,
        step_type: str,
        content: str,
        duration: float = 0.0,
        tokens: int = 0,
        cost: float = 0.0,
        metadata: dict = None,
    ):
        """
        Yeni bir adım kaydet.

        Parametreler:
            step_type: Adım türü ("düşünme", "tool_çağrısı", "cevap", "hata" vb.)
            content: Adımın içeriği
            duration: Adımın süresi (saniye)
            tokens: Kullanılan token sayısı
            cost: Maliyet (USD)
            metadata: Ek bilgiler (dict)
        """
        step = TraceStep(
            step_type=step_type,
            content=content,
            timestamp=datetime.now(),
            duration=duration,
            tokens=tokens,
            cost=cost,
            metadata=metadata or {},
        )
        self._steps.append(step)

        # Adım türüne göre ikon seç
        icons = {
            "düşünme": "🧠",
            "tool_çağrısı": "🔧",
            "tool_sonucu": "📥",
            "cevap": "💬",
            "hata": "❌",
        }
        icon = icons.get(step_type, "▸")

        # Geçen süreyi hesapla (başlangıçtan itibaren)
        elapsed = time.time() - self._start_time if self._start_time else 0

        self.logger.info(
            f"  {icon} [{elapsed:.1f}s] {step_type}: {content[:80]}"
            + (f" (${cost:.4f})" if cost > 0 else "")
        )

    def end(self, success: bool = True):
        """
        İzlemeyi sonlandır.

        Parametreler:
            success: Görev başarılı mı?
        """
        self._end_time = time.time()
        self._success = success

        duration = self._end_time - self._start_time if self._start_time else 0
        total_cost = sum(s.cost for s in self._steps)
        total_tokens = sum(s.tokens for s in self._steps)

        status = "✅ Başarılı" if success else "❌ Başarısız"
        self.logger.info(
            f"📍 İzleme tamamlandı: {self.task_name} — {status} | "
            f"{duration:.2f}s | ${total_cost:.4f} | {total_tokens} token"
        )

    def get_record(self) -> TraceRecord:
        """
        İzleme kaydını döndür.

        Döndürür:
            TraceRecord: Görevin tüm izleme bilgileri
        """
        total_duration = (self._end_time - self._start_time) if self._start_time and self._end_time else 0

        return TraceRecord(
            task_name=self.task_name,
            steps=self._steps.copy(),
            start_time=self._start_datetime,
            end_time=datetime.now() if self._end_time else None,
            success=self._success,
            total_duration=round(total_duration, 3),
            total_tokens=sum(s.tokens for s in self._steps),
            total_cost=sum(s.cost for s in self._steps),
        )

    def get_report(self) -> str:
        """
        Detaylı izleme raporunu metin olarak döndür.

        Rapor şunları içerir:
        - Her adımın detayı (tür, süre, maliyet)
        - Toplu istatistikler
        - Adım bazlı maliyet dağılımı

        Döndürür:
            str: Formatlı izleme raporu
        """
        record = self.get_record()

        lines = []
        lines.append("")
        lines.append("═" * 55)
        lines.append(f"📍 İZLEME RAPORU: {record.task_name}")
        lines.append("═" * 55)

        # Adım detayları
        for i, step in enumerate(record.steps, 1):
            # Geçen süre hesapla
            if record.start_time and step.timestamp:
                elapsed = (step.timestamp - record.start_time).total_seconds()
            else:
                elapsed = 0

            icons = {
                "düşünme": "🧠",
                "tool_çağrısı": "🔧",
                "tool_sonucu": "📥",
                "cevap": "💬",
                "hata": "❌",
            }
            icon = icons.get(step.step_type, "▸")

            lines.append(f"\n  Adım {i} [{elapsed:.1f}s] {icon} {step.step_type.upper()}")
            lines.append(f"    İçerik:  {step.content[:100]}")

            if step.duration > 0:
                lines.append(f"    Süre:    {step.duration:.2f}s")
            if step.tokens > 0:
                lines.append(f"    Token:   {step.tokens}")
            if step.cost > 0:
                lines.append(f"    Maliyet: ${step.cost:.4f}")
            if step.metadata:
                lines.append(f"    Meta:    {step.metadata}")

        # Toplu istatistikler
        lines.append("\n" + "─" * 55)
        status = "✅ Başarılı" if record.success else "❌ Başarısız" if record.success is False else "⏳ Devam ediyor"
        lines.append(f"  Durum:        {status}")
        lines.append(f"  Toplam Süre:  {record.total_duration:.2f}s")
        lines.append(f"  Toplam Token: {record.total_tokens}")
        lines.append(f"  Toplam Maliyet: ${record.total_cost:.4f}")
        lines.append(f"  Adım Sayısı: {len(record.steps)}")

        # Adım türü dağılımı
        type_counts: dict[str, int] = {}
        type_costs: dict[str, float] = {}
        for step in record.steps:
            type_counts[step.step_type] = type_counts.get(step.step_type, 0) + 1
            type_costs[step.step_type] = type_costs.get(step.step_type, 0) + step.cost

        lines.append("\n  Adım Dağılımı:")
        for stype, count in type_counts.items():
            cost = type_costs.get(stype, 0)
            lines.append(f"    {stype:<16} {count} adım  ${cost:.4f}")

        lines.append("═" * 55)

        return "\n".join(lines)

    def reset(self, task_name: str = ""):
        """
        İzleyiciyi sıfırla (yeni görev için).

        Parametreler:
            task_name: Yeni görev adı
        """
        self.task_name = task_name
        self._steps = []
        self._start_time = None
        self._end_time = None
        self._start_datetime = None
        self._success = None


# ============================================================
# Ana çalıştırma bloğu — Demo
# ============================================================

if __name__ == "__main__":
    print("📍 İzleme Toplayıcı (Trace Collector) — Demo")
    print("=" * 55)
    print()
    print("Bu demo, bir agent görevinin adım adım izlenmesini simüle eder.")
    print()

    # Senaryo: "Hava durumunu öğren ve dosyaya kaydet"
    tracer = TraceCollector(task_name="Hava durumunu öğren ve dosyaya kaydet")

    tracer.start()

    # Adım 1: Düşünme
    time.sleep(0.1)  # Simüle edilmiş gecikme
    tracer.add_step(
        step_type="düşünme",
        content="Hava durumunu öğrenmek için get_weather tool'unu çağırmalıyım",
        tokens=300,
        cost=0.002,
    )

    # Adım 2: Tool çağrısı
    time.sleep(0.2)
    tracer.add_step(
        step_type="tool_çağrısı",
        content="get_weather(city='Istanbul')",
        duration=1.2,
        metadata={"tool": "get_weather", "args": {"city": "Istanbul"}},
    )

    # Adım 3: Tool sonucu
    time.sleep(0.05)
    tracer.add_step(
        step_type="tool_sonucu",
        content='{"temp": 15, "condition": "güneşli", "wind": "10 km/s"}',
        metadata={"tool": "get_weather"},
    )

    # Adım 4: Düşünme
    time.sleep(0.1)
    tracer.add_step(
        step_type="düşünme",
        content="Sonucu dosyaya kaydetmem gerekiyor",
        tokens=200,
        cost=0.001,
    )

    # Adım 5: Tool çağrısı
    time.sleep(0.1)
    tracer.add_step(
        step_type="tool_çağrısı",
        content="file_write(path='hava.txt', content='İstanbul: 15°C, güneşli')",
        duration=0.1,
        metadata={"tool": "file_write", "args": {"path": "hava.txt"}},
    )

    # Adım 6: Cevap
    time.sleep(0.1)
    tracer.add_step(
        step_type="cevap",
        content="İstanbul'da hava 15°C ve güneşli. Sonuç hava.txt dosyasına kaydedildi.",
        tokens=100,
        cost=0.001,
    )

    tracer.end(success=True)

    # Raporu yazdır
    print(tracer.get_report())
