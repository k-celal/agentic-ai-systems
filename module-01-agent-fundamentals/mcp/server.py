"""
MCP Server - Module 1 MCP Sunucusu
=====================================
Bu dosya, basit bir MCP sunucusu oluşturur.

MCP Server Nedir?
-----------------
Agent'ın (client) tool'lara erişmesini sağlayan sunucu.
- Tool'ları barındırır
- Agent'tan gelen istekleri alır
- Tool'u çalıştırır ve sonucu döndürür

Bu Sunucudaki Tool'lar:
- echo: Mesajı geri döndürür
- get_time: Saati döndürür

Çalıştırma:
    python -m mcp.server

Not: Bu basit bir MCP sunucusu implementasyonudur.
     Gerçek MCP SDK kullanımı Module 3'te detaylı işlenecek.
"""

import json
import asyncio
from typing import Callable

# Tool'ları import et
from mcp.tools.echo import echo, ECHO_SCHEMA
from mcp.tools.time_tool import get_time, GET_TIME_SCHEMA


class SimpleMCPServer:
    """
    Basit MCP Server implementasyonu.
    
    Bu, MCP protokolünün basitleştirilmiş bir versiyonudur.
    Gerçek MCP SDK implementasyonu Module 3'te işlenecek.
    
    Ne yapar?
    1. Tool'ları kayıt eder (register)
    2. "tools/list" isteğine tool listesini döndürür
    3. "tools/call" isteğine tool'u çalıştırır ve sonucu döndürür
    
    Kullanım:
        server = SimpleMCPServer()
        
        # Tool kaydet
        server.register_tool("echo", echo, ECHO_SCHEMA)
        server.register_tool("get_time", get_time, GET_TIME_SCHEMA)
        
        # Tool listesi
        tools = server.list_tools()
        
        # Tool çağır
        result = await server.call_tool("echo", {"message": "test"})
    """
    
    def __init__(self, name: str = "module-01-server"):
        """
        MCP Server oluştur.
        
        Parametreler:
            name: Sunucu adı
        """
        self.name = name
        self.tools: dict[str, Callable] = {}        # Tool fonksiyonları
        self.tool_schemas: dict[str, dict] = {}      # Tool şemaları
        
        print(f"🖥️  MCP Server başlatılıyor: {name}")
    
    def register_tool(self, name: str, func: Callable, schema) -> None:
        """
        Yeni bir tool kaydet.
        
        Parametreler:
            name: Tool adı
            func: Tool fonksiyonu
            schema: Tool şeması (ToolSchema nesnesi)
        """
        self.tools[name] = func
        self.tool_schemas[name] = schema.to_mcp_format() if hasattr(schema, 'to_mcp_format') else schema
        print(f"   ✅ Tool kaydedildi: {name}")
    
    def list_tools(self) -> list[dict]:
        """
        Kayıtlı tool'ların listesini döndür.
        
        Bu, MCP protokolündeki "tools/list" isteğine karşılık gelir.
        Agent, bu listeye bakarak hangi tool'ları kullanabileceğini öğrenir.
        
        Döndürür:
            list[dict]: Tool şemalarının listesi
        """
        return list(self.tool_schemas.values())
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """
        Bir tool'u çağır.
        
        Bu, MCP protokolündeki "tools/call" isteğine karşılık gelir.
        
        Parametreler:
            name: Tool adı
            arguments: Tool parametreleri
        
        Döndürür:
            dict: {"success": True/False, "result": ..., "error": ...}
        """
        # Tool var mı?
        if name not in self.tools:
            return {
                "success": False,
                "error": f"Tool bulunamadı: '{name}'",
                "available_tools": list(self.tools.keys()),
            }
        
        try:
            # Tool fonksiyonunu çağır
            func = self.tools[name]
            
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            
            return {
                "success": True,
                "result": result,
            }
        
        except TypeError as e:
            return {
                "success": False,
                "error": f"Parametre hatası: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool hatası: {str(e)}",
            }
    
    def get_openai_tools(self) -> list[dict]:
        """
        Tool şemalarını OpenAI formatında döndür.
        
        Agent'ın LLM'e tool bilgilerini göndermesi için
        OpenAI formatında şemalar gerekir.
        
        Döndürür:
            list[dict]: OpenAI tool formatında şemalar
        """
        openai_tools = []
        for name, schema in self.tool_schemas.items():
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["inputSchema"],
                },
            })
        return openai_tools


def create_server() -> SimpleMCPServer:
    """
    Module 1 MCP Server'ını oluştur ve tool'ları kaydet.
    
    Döndürür:
        SimpleMCPServer: Hazır sunucu
    """
    server = SimpleMCPServer("module-01-server")
    
    # Tool'ları kaydet
    server.register_tool("echo", echo, ECHO_SCHEMA)
    server.register_tool("get_time", get_time, GET_TIME_SCHEMA)
    
    return server


# ─────────────────────────────────────────
# Doğrudan çalıştırma testi
# ─────────────────────────────────────────

if __name__ == "__main__":
    async def test_server():
        print("\n🖥️  MCP Server Testi")
        print("=" * 40)
        
        # Server oluştur
        server = create_server()
        
        # Tool listesi
        tools = server.list_tools()
        print(f"\n📋 Kayıtlı Tool'lar ({len(tools)}):")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        
        # Echo test
        print("\n🔧 Echo Tool Testi:")
        result = await server.call_tool("echo", {"message": "Merhaba MCP!"})
        print(f"   Sonuç: {result}")
        
        # Time test
        print("\n🕐 Time Tool Testi:")
        result = await server.call_tool("get_time", {"timezone_name": "Europe/Istanbul"})
        print(f"   Sonuç: {result}")
        
        # Hata testi: olmayan tool
        print("\n❌ Hata Testi (olmayan tool):")
        result = await server.call_tool("nonexistent", {})
        print(f"   Sonuç: {result}")
        
        # Hata testi: yanlış parametre
        print("\n❌ Hata Testi (yanlış parametre):")
        result = await server.call_tool("echo", {"wrong_param": "test"})
        print(f"   Sonuç: {result}")
        
        print("\n✅ Server testi tamamlandı!")
    
    asyncio.run(test_server())
