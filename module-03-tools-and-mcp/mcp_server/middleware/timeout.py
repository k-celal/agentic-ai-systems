"""
Timeout Middleware - Zaman Aşımı Kontrolü
===========================================
Tool çağrılarına zaman limiti koyar ve retry mantığı ekler.

Neden Timeout Gerekli?
---------------------
Bir tool sonsuza dek çalışabilir (API yanıt vermiyordur, ağ sorunu var).
Timeout olmadan agent sonsuz beklemeye girebilir.

Retry Neden Gerekli?
-------------------
Geçici hatalar (network timeout, rate limit) genellikle tekrar denenince düzelir.
Ama SADECE idempotent tool'lar güvenle tekrar denenebilir!

Kullanım:
    from mcp_server.middleware.timeout import TimeoutMiddleware
    
    mw = TimeoutMiddleware(default_timeout=30, max_retries=3)
    
    result = await mw.execute_with_timeout(tool_func, args, timeout=10)
    result = await mw.execute_with_retry(tool_func, args, max_retries=3)
"""

import sys
import os
import asyncio
from typing import Callable, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.telemetry.logger import get_logger


class TimeoutMiddleware:
    """
    Zaman aşımı ve tekrar deneme middleware'i.
    
    Kullanım:
        mw = TimeoutMiddleware(default_timeout=30)
        
        # Timeout ile çağır
        result = await mw.execute_with_timeout(
            func=my_tool,
            kwargs={"query": "test"},
            timeout=10
        )
        
        # Retry ile çağır
        result = await mw.execute_with_retry(
            func=my_tool,
            kwargs={"query": "test"},
            max_retries=3,
            is_idempotent=True
        )
    """
    
    def __init__(self, default_timeout: float = 30.0, max_retries: int = 3):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.logger = get_logger("middleware.timeout")
    
    async def execute_with_timeout(
        self,
        func: Callable,
        kwargs: dict = None,
        timeout: float = None,
    ) -> dict:
        """
        Tool'u timeout ile çalıştır.
        
        Parametreler:
            func: Çalıştırılacak fonksiyon
            kwargs: Fonksiyon parametreleri
            timeout: Zaman aşımı süresi (saniye)
        
        Döndürür:
            dict: {"success": True/False, "result": ..., "error": ...}
        """
        timeout = timeout or self.default_timeout
        kwargs = kwargs or {}
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(**kwargs),
                    timeout=timeout,
                )
            else:
                # Sync fonksiyonu thread'de çalıştır
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(**kwargs)),
                    timeout=timeout,
                )
            
            return {"success": True, "result": result}
        
        except asyncio.TimeoutError:
            self.logger.warning(f"⏱️ Timeout: {timeout}s aşıldı")
            return {"success": False, "error": f"Timeout: {timeout}s aşıldı"}
        except Exception as e:
            self.logger.error(f"❌ Hata: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_with_retry(
        self,
        func: Callable,
        kwargs: dict = None,
        max_retries: int = None,
        timeout: float = None,
        backoff: float = 2.0,
        is_idempotent: bool = True,
    ) -> dict:
        """
        Tool'u retry mantığı ile çalıştır.
        
        ⚠️ DİKKAT: Sadece idempotent tool'ları retry edin!
        Non-idempotent tool'ları retry etmek tehlikelidir.
        (örn: send_email → 3 retry = 3 email!)
        
        Parametreler:
            func: Çalıştırılacak fonksiyon
            kwargs: Parametreler
            max_retries: Maksimum deneme sayısı
            timeout: Her deneme için timeout
            backoff: Bekleme çarpanı (exponential backoff)
            is_idempotent: Tool idempotent mi?
        
        Döndürür:
            dict: Sonuç
        """
        max_retries = max_retries or self.max_retries
        
        if not is_idempotent and max_retries > 1:
            self.logger.warning(
                "⚠️ Non-idempotent tool için retry tehlikeli! "
                "max_retries=1'e düşürüldü."
            )
            max_retries = 1
        
        last_error = None
        delay = 1.0  # İlk bekleme süresi
        
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"🔄 Deneme {attempt}/{max_retries}")
            
            result = await self.execute_with_timeout(func, kwargs, timeout)
            
            if result["success"]:
                if attempt > 1:
                    self.logger.info(f"✅ Deneme {attempt}'de başarılı!")
                return result
            
            last_error = result["error"]
            
            if attempt < max_retries:
                self.logger.info(f"   ⏳ {delay:.1f}s bekleniyor...")
                await asyncio.sleep(delay)
                delay *= backoff  # Exponential backoff
        
        return {
            "success": False,
            "error": f"Tüm denemeler ({max_retries}) başarısız. Son hata: {last_error}",
        }
