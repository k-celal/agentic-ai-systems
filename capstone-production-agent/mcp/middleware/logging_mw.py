"""
CallLogger - Araç Çağrı Loglama Ara Katmanı
===============================================
Her araç çağrısını yapılandırılmış şekilde loglar ve özet rapor üretir.

Ara Katman Nedir?
------------------
Araç çağrısından ÖNCE ve SONRA çalışan ek işlem katmanıdır.
Aracın kendisini değiştirmeden izleme, loglama ve metrik toplama sağlar.

CallLogger Ne İşe Yarar?
--------------------------
1. Çağrı öncesi: Araç adı ve parametreleri loglanır
2. Çağrı sonrası: Sonuç, süre ve başarı durumu loglanır
3. Özet rapor: Tüm çağrıların istatistiksel özeti

Kullanım:
    from mcp.middleware.logging_mw import CallLogger
    
    logger = CallLogger()
    
    # Çağrı öncesi
    logger.before_call("deep_research", {"query": "yapay zeka"})
    
    # Aracı çalıştır...
    
    # Çağrı sonrası
    logger.after_call("deep_research", sonuc, duration_ms=125.3)
    
    # Özet rapor
    print(logger.get_summary())
"""

import sys
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.telemetry.logger import get_logger


# ─── Çağrı Kaydı Yapısı ───

@dataclass
class CallRecord:
    """
    Tek bir araç çağrısının kaydı.
    
    Her before_call + after_call çifti bir CallRecord oluşturur.
    Bu kayıtlar daha sonra özet raporda kullanılır.
    
    Öznitelikler:
        tool_name: Çağrılan aracın adı
        args: Çağrı parametreleri
        result: Araç sonucu (başarılıysa)
        error: Hata mesajı (başarısızsa)
        duration_ms: Çalışma süresi (milisaniye)
        timestamp: Çağrı zamanı
        success: Çağrı başarılı mı?
    """
    tool_name: str
    args: dict = field(default_factory=dict)
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True


# ─── Ana CallLogger Sınıfı ───

class CallLogger:
    """
    Araç çağrılarını loglayan ve izleyen ara katman bileşeni.
    
    Her çağrı için:
    1. Başlangıcı loglar (before_call)
    2. Parametreleri kaydeder
    3. Sonucu, süreyi ve başarı durumunu loglar (after_call)
    4. Hataları özel olarak kaydeder
    
    Kullanım:
        logger = CallLogger(max_records=200)
        
        logger.before_call("deep_research", {"query": "LLM nedir?"})
        sonuc = arac.calistir(...)
        logger.after_call("deep_research", sonuc, duration_ms=150.5)
        
        # Logları filtrele
        arama_loglari = logger.get_records(tool_name="deep_research")
        
        # Özet rapor
        print(logger.get_summary())
    """
    
    def __init__(self, max_records: int = 200):
        """
        CallLogger oluştur.
        
        Parametreler:
            max_records: Saklanacak maksimum kayıt sayısı.
                         Aşıldığında en eski kayıtlar silinir.
        """
        self.logger = get_logger("mcp.middleware.logging")
        self.records: list[CallRecord] = []
        self.max_records: int = max_records
        self._active_calls: dict[str, datetime] = {}
    
    def before_call(self, tool_name: str, args: dict) -> None:
        """
        Araç çağrısı başlamadan önce çağrılır.
        
        Çağrıyı loglar ve aktif çağrı olarak işaretler.
        
        Parametreler:
            tool_name: Çağrılacak aracın adı
            args: Araç parametreleri
        
        Örnek:
            logger.before_call("deep_research", {"query": "Python"})
        """
        self._active_calls[tool_name] = datetime.now()
        
        # Parametreleri güvenli şekilde kısalt (çok uzun değerler için)
        safe_args = {}
        for key, value in args.items():
            str_val = str(value)
            safe_args[key] = str_val[:100] + "..." if len(str_val) > 100 else str_val
        
        self.logger.info(f"[ÇAĞRI BAŞLADI] {tool_name}")
        self.logger.debug(f"  Parametreler: {safe_args}")
    
    def after_call(
        self,
        tool_name: str,
        result: Any,
        duration_ms: float,
    ) -> None:
        """
        Araç çağrısı tamamlandıktan sonra çağrılır.
        
        Sonucu ve süreyi loglar, kayıt oluşturur.
        
        Parametreler:
            tool_name: Çağrılan aracın adı
            result: Araç sonucu (dict beklenir)
            duration_ms: Çalışma süresi (milisaniye)
        
        Örnek:
            logger.after_call("deep_research", sonuc_dict, duration_ms=125.3)
        """
        # Başarı durumunu belirle
        success = True
        error = None
        if isinstance(result, dict):
            success = result.get("success", True)
            if not success:
                error = result.get("error", "Bilinmeyen hata")
        
        # Kayıt oluştur
        record = CallRecord(
            tool_name=tool_name,
            args={},  # Gizlilik için parametreler burada saklanmaz
            result=result if success else None,
            error=error,
            duration_ms=duration_ms,
            success=success,
        )
        
        self.records.append(record)
        
        # Maksimum kayıt sayısını kontrol et
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
        
        # Aktif çağrıdan kaldır
        self._active_calls.pop(tool_name, None)
        
        # Logla
        if success:
            self.logger.info(
                f"[ÇAĞRI TAMAMLANDI] {tool_name} | "
                f"süre: {duration_ms:.1f}ms | durum: BAŞARILI"
            )
        else:
            self.logger.warning(
                f"[ÇAĞRI BAŞARISIZ] {tool_name} | "
                f"süre: {duration_ms:.1f}ms | hata: {error}"
            )
    
    def get_records(self, tool_name: str = None) -> list[CallRecord]:
        """
        Kayıtları getir, isteğe bağlı olarak araç adına göre filtrele.
        
        Parametreler:
            tool_name: Filtrelenecek araç adı (None ise tümü)
        
        Döndürür:
            list[CallRecord]: Filtrelenmiş kayıt listesi
        """
        if tool_name:
            return [r for r in self.records if r.tool_name == tool_name]
        return self.records
    
    def get_summary(self) -> str:
        """
        Tüm çağrıların özet raporunu döndür.
        
        Rapor içeriği:
        - Toplam çağrı sayısı
        - Başarılı / Başarısız oranı
        - Ortalama süre
        - Araç bazında kırılım
        
        Döndürür:
            str: Formatlanmış özet rapor
        
        Örnek:
            print(logger.get_summary())
        """
        if not self.records:
            return "Henüz araç çağrı kaydı bulunmuyor."
        
        toplam = len(self.records)
        basarili = sum(1 for r in self.records if r.success)
        basarisiz = toplam - basarili
        ort_sure = sum(r.duration_ms for r in self.records) / toplam
        
        # Araç bazında kırılım
        tool_stats: dict[str, dict] = {}
        for r in self.records:
            if r.tool_name not in tool_stats:
                tool_stats[r.tool_name] = {
                    "count": 0, "success": 0, "total_ms": 0.0
                }
            stats = tool_stats[r.tool_name]
            stats["count"] += 1
            if r.success:
                stats["success"] += 1
            stats["total_ms"] += r.duration_ms
        
        lines = [
            "",
            f"{'═' * 55}",
            f"  CallLogger Özet Raporu",
            f"{'═' * 55}",
            f"  Toplam Çağrı:       {toplam}",
            f"  Başarılı:           {basarili} ({basarili/toplam*100:.0f}%)",
            f"  Başarısız:          {basarisiz} ({basarisiz/toplam*100:.0f}%)",
            f"  Ortalama Süre:      {ort_sure:.1f}ms",
            f"{'─' * 55}",
            f"  Araç Bazında Kırılım:",
        ]
        
        for name, stats in tool_stats.items():
            ort = stats["total_ms"] / stats["count"]
            rate = (stats["success"] / stats["count"]) * 100
            lines.append(
                f"    {name:22s} | "
                f"{stats['count']:3d} çağrı | "
                f"{rate:5.0f}% başarı | "
                f"ort. {ort:.1f}ms"
            )
        
        lines.append(f"{'═' * 55}")
        return "\n".join(lines)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 55)
    print("  CallLogger - Ara Katman Test")
    print("=" * 55)
    
    cl = CallLogger()
    
    # Simüle edilmiş çağrılar
    test_calls = [
        ("deep_research", {"query": "yapay zeka"}, True, 125.3),
        ("save_content", {"filename": "test.md"}, True, 45.8),
        ("deep_research", {"query": "MCP"}, True, 98.7),
        ("evaluate_writing", {"content": "test metin"}, True, 210.5),
        ("deep_research", {"query": "hatalı"}, False, 500.1),
    ]
    
    for tool_name, args, success, duration in test_calls:
        cl.before_call(tool_name, args)
        # Simüle edilmiş sonuç
        if success:
            result = {"success": True, "result": {"data": "test"}}
        else:
            result = {"success": False, "error": "Simüle edilmiş hata"}
        cl.after_call(tool_name, result, duration)
    
    # Kayıtları listele
    print(f"\nToplam Kayıt: {len(cl.records)}")
    print(f"deep_research Kayıtları: {len(cl.get_records('deep_research'))}")
    
    # Özet rapor
    print(cl.get_summary())
    
    print("\nTest tamamlandı!")
