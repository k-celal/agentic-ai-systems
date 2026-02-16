"""
Logging Middleware - Loglama Ara Katmanı
==========================================
Her tool çağrısını otomatik olarak loglar.

Middleware Nedir?
-----------------
Tool çağrısından ÖNCE ve SONRA çalışan ek işlemdir.
Tool'un kendisini değiştirmeden ek davranış ekler.

Kullanım:
    from mcp_server.middleware.logging_mw import LoggingMiddleware
    
    mw = LoggingMiddleware()
    
    # Tool çağrısından önce
    mw.before_call("search", {"query": "Python"})
    
    # Tool çağrısından sonra
    mw.after_call("search", result, duration=1.5)
"""

import sys
import os
from datetime import datetime
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.telemetry.logger import get_logger


@dataclass
class CallLog:
    """Tek bir tool çağrısının logu."""
    tool_name: str
    arguments: dict
    result: dict = None
    error: str = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True


class LoggingMiddleware:
    """
    Tool çağrılarını loglayan middleware.
    
    Her tool çağrısı için:
    1. Çağrı başlangıcını loglar
    2. Parametreleri kaydeder
    3. Sonucu ve süreyi loglar
    4. Hataları kaydeder
    
    Kullanım:
        mw = LoggingMiddleware()
        
        mw.before_call("search", {"query": "test"})
        result = tool.execute(...)
        mw.after_call("search", result, duration=1.5)
        
        # Logları görüntüle
        for log in mw.get_logs():
            print(f"{log.tool_name}: {log.duration_ms}ms")
    """
    
    def __init__(self, max_logs: int = 100):
        self.logger = get_logger("middleware.logging")
        self.logs: list[CallLog] = []
        self.max_logs = max_logs
    
    def before_call(self, tool_name: str, arguments: dict) -> None:
        """Tool çağrısı başlamadan önce."""
        self.logger.info(f"📞 Tool çağrısı: {tool_name}")
        self.logger.debug(f"   Parametreler: {arguments}")
    
    def after_call(
        self,
        tool_name: str,
        result: dict,
        duration_ms: float,
        arguments: dict = None,
    ) -> None:
        """Tool çağrısı tamamlandıktan sonra."""
        success = result.get("success", True) if isinstance(result, dict) else True
        
        log = CallLog(
            tool_name=tool_name,
            arguments=arguments or {},
            result=result if success else None,
            error=result.get("error") if isinstance(result, dict) and not success else None,
            duration_ms=duration_ms,
            success=success,
        )
        
        self.logs.append(log)
        
        # Max log sayısını aşarsa eskileri sil
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        status = "✅" if success else "❌"
        self.logger.info(f"{status} {tool_name}: {duration_ms:.0f}ms")
    
    def get_logs(self, tool_name: str = None) -> list[CallLog]:
        """Logları getir (isteğe bağlı tool filtresı ile)."""
        if tool_name:
            return [l for l in self.logs if l.tool_name == tool_name]
        return self.logs
    
    def get_summary(self) -> str:
        """Log özet raporu."""
        if not self.logs:
            return "📊 Henüz log kaydı yok."
        
        total = len(self.logs)
        success = sum(1 for l in self.logs if l.success)
        avg_duration = sum(l.duration_ms for l in self.logs) / total
        
        return (
            f"📊 Logging Özeti\n"
            f"   Toplam: {total} çağrı\n"
            f"   Başarılı: {success} ({success/total*100:.0f}%)\n"
            f"   Ort. Süre: {avg_duration:.0f}ms"
        )
