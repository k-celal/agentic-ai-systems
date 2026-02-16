"""
Tool Registry - Araç Kayıt Sistemi
=====================================
Tüm tool'ları merkezi olarak yöneten kayıt sistemi.

Tool Registry Nedir?
-------------------
Bir "telefon rehberi" gibi düşünün:
- Her tool'un adı, versiyonu ve şeması kayıtlıdır
- Agent, registry'ye bakarak hangi tool'ları kullanabileceğini öğrenir
- Tool versiyonları yönetilir (search@v1, search@v2)
- Tool metadata'sı tutulur (timeout, idempotent mi?)

Kullanım:
    from mcp_server.registry import ToolRegistry
    
    registry = ToolRegistry()
    
    # Tool kaydet
    registry.register(
        name="search",
        version="1.0",
        func=search_fn,
        schema=search_schema,
        metadata={"timeout": 30, "idempotent": True}
    )
    
    # Tool çağır
    result = await registry.call("search", {"query": "Python"})
"""

import sys
import os
import asyncio
import json
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.schemas.tool import ToolSchema
from shared.telemetry.logger import get_logger


@dataclass
class ToolEntry:
    """
    Registry'deki bir tool kaydı.
    
    Attributes:
        name: Tool adı
        version: Versiyon (örn: "1.0", "2.0")
        func: Tool fonksiyonu
        schema: Tool şeması
        metadata: Ek bilgiler (timeout, idempotent, vb.)
        registered_at: Kayıt zamanı
        call_count: Çağrılma sayısı
        error_count: Hata sayısı
    """
    name: str
    version: str
    func: Callable
    schema: ToolSchema
    metadata: dict = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    call_count: int = 0
    error_count: int = 0
    
    @property
    def full_name(self) -> str:
        """Tam isim: name@version (örn: search@v2.0)"""
        return f"{self.name}@v{self.version}"
    
    @property
    def timeout(self) -> float:
        """Tool timeout süresi (saniye)."""
        return self.metadata.get("timeout", 30.0)
    
    @property
    def is_idempotent(self) -> bool:
        """Tool idempotent mi?"""
        return self.metadata.get("idempotent", False)
    
    @property
    def success_rate(self) -> float:
        """Başarı oranı (%)."""
        if self.call_count == 0:
            return 100.0
        return ((self.call_count - self.error_count) / self.call_count) * 100


class ToolRegistry:
    """
    Merkezi tool kayıt ve yönetim sistemi.
    
    Bu sınıf:
    1. Tool'ları kaydeder
    2. Versiyonları yönetir
    3. Tool çağrılarını yürütür (middleware'ler ile)
    4. İstatistik tutar
    
    Kullanım:
        registry = ToolRegistry()
        
        # Tool kaydet
        registry.register("echo", "1.0", echo_fn, echo_schema)
        
        # Tool listele
        tools = registry.list_tools()
        
        # Tool çağır
        result = await registry.call("echo", {"message": "test"})
        
        # İstatistik
        print(registry.get_stats())
    """
    
    def __init__(self):
        self._tools: dict[str, dict[str, ToolEntry]] = {}  # name -> {version -> entry}
        self._default_versions: dict[str, str] = {}  # name -> default version
        self._middlewares: list[Callable] = []
        self.logger = get_logger("mcp.registry")
    
    def register(
        self,
        name: str,
        version: str,
        func: Callable,
        schema: ToolSchema,
        metadata: dict = None,
        is_default: bool = True,
    ) -> None:
        """
        Yeni bir tool kaydet.
        
        Parametreler:
            name: Tool adı
            version: Versiyon numarası (örn: "1.0")
            func: Tool fonksiyonu
            schema: Tool şeması
            metadata: Ek bilgiler {"timeout": 30, "idempotent": True}
            is_default: Varsayılan versiyon mu?
        """
        entry = ToolEntry(
            name=name,
            version=version,
            func=func,
            schema=schema,
            metadata=metadata or {},
        )
        
        if name not in self._tools:
            self._tools[name] = {}
        
        self._tools[name][version] = entry
        
        if is_default:
            self._default_versions[name] = version
        
        self.logger.info(f"✅ Tool kaydedildi: {entry.full_name}")
    
    def get_tool(self, name: str, version: str = None) -> Optional[ToolEntry]:
        """
        Tool'u getir.
        
        Parametreler:
            name: Tool adı
            version: İstenen versiyon (None ise varsayılan)
        
        Döndürür:
            ToolEntry veya None
        """
        if name not in self._tools:
            return None
        
        if version is None:
            version = self._default_versions.get(name)
        
        return self._tools[name].get(version)
    
    def list_tools(self, include_versions: bool = False) -> list[dict]:
        """
        Kayıtlı tool'ların listesini döndür.
        
        Parametreler:
            include_versions: Tüm versiyonları göster mi?
        """
        tools = []
        for name, versions in self._tools.items():
            if include_versions:
                for ver, entry in versions.items():
                    tools.append({
                        "name": entry.full_name,
                        "description": entry.schema.description,
                        "version": ver,
                        "calls": entry.call_count,
                        "success_rate": f"{entry.success_rate:.1f}%",
                    })
            else:
                default_ver = self._default_versions.get(name)
                entry = versions.get(default_ver, list(versions.values())[0])
                tools.append({
                    "name": name,
                    "description": entry.schema.description,
                    "version": default_ver,
                    "versions_available": list(versions.keys()),
                })
        return tools
    
    async def call(
        self,
        name: str,
        arguments: dict,
        version: str = None,
    ) -> dict:
        """
        Bir tool'u çağır.
        
        Bu fonksiyon:
        1. Tool'u registry'den bulur
        2. Parametreleri doğrular
        3. Middleware'leri çalıştırır
        4. Tool'u yürütür
        5. Sonucu döndürür
        
        Parametreler:
            name: Tool adı
            arguments: Tool parametreleri
            version: İstenen versiyon
        
        Döndürür:
            dict: {"success": True/False, "result": ..., "error": ...}
        """
        # Tool'u bul
        entry = self.get_tool(name, version)
        if entry is None:
            available = list(self._tools.keys())
            return {
                "success": False,
                "error": f"Tool bulunamadı: '{name}'",
                "available": available,
            }
        
        # Parametre doğrulama
        valid, error_msg = entry.schema.validate_args(arguments)
        if not valid:
            entry.error_count += 1
            return {
                "success": False,
                "error": f"Parametre hatası: {error_msg}",
            }
        
        # Tool'u çağır
        entry.call_count += 1
        
        try:
            # Timeout kontrolü
            if asyncio.iscoroutinefunction(entry.func):
                result = await asyncio.wait_for(
                    entry.func(**arguments),
                    timeout=entry.timeout,
                )
            else:
                result = entry.func(**arguments)
            
            return {
                "success": True,
                "result": result,
                "tool": entry.full_name,
            }
        
        except asyncio.TimeoutError:
            entry.error_count += 1
            return {
                "success": False,
                "error": f"Timeout: {name} {entry.timeout}s içinde tamamlanamadı",
            }
        except Exception as e:
            entry.error_count += 1
            return {
                "success": False,
                "error": f"Tool hatası ({name}): {str(e)}",
            }
    
    def get_stats(self) -> str:
        """Registry istatistik raporu."""
        total_tools = sum(len(v) for v in self._tools.values())
        total_calls = sum(
            e.call_count
            for versions in self._tools.values()
            for e in versions.values()
        )
        total_errors = sum(
            e.error_count
            for versions in self._tools.values()
            for e in versions.values()
        )
        
        lines = [
            f"\n📊 Tool Registry İstatistikleri",
            f"{'═'*35}",
            f"Toplam Tool:    {total_tools}",
            f"Toplam Çağrı:   {total_calls}",
            f"Toplam Hata:    {total_errors}",
            f"Başarı Oranı:   {((total_calls-total_errors)/max(total_calls,1))*100:.1f}%",
            f"{'═'*35}",
        ]
        
        # Tool bazında detay
        for name, versions in self._tools.items():
            for ver, entry in versions.items():
                lines.append(
                    f"  {entry.full_name}: "
                    f"{entry.call_count} çağrı, "
                    f"{entry.success_rate:.0f}% başarı"
                )
        
        return "\n".join(lines)
