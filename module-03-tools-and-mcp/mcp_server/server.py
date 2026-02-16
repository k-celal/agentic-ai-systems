"""
Module 3 MCP Server - Gelişmiş MCP Sunucusu
==============================================
Registry, middleware ve gelişmiş tool'lar ile tam donanımlı MCP server.

Çalıştırma:
    cd module-03-tools-and-mcp
    python -m mcp_server.server
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mcp_server.registry import ToolRegistry
from mcp_server.middleware.logging_mw import LoggingMiddleware
from mcp_server.middleware.timeout import TimeoutMiddleware
from mcp_server.tools.search import (
    search_v1, SEARCH_V1_SCHEMA,
    search_v2, SEARCH_V2_SCHEMA,
)
from mcp_server.tools.file_write import (
    file_write, FILE_WRITE_SCHEMA,
    file_read, FILE_READ_SCHEMA,
)
from mcp_server.tools.code_exec import execute_code, CODE_EXEC_SCHEMA

from shared.telemetry.logger import get_logger

logger = get_logger("mcp.server")


def create_server() -> ToolRegistry:
    """
    Module 3 MCP Server'ını oluştur.
    
    Tüm tool'ları registry'ye kaydeder.
    """
    registry = ToolRegistry()
    
    # Search tool v1 ve v2
    registry.register(
        name="search", version="1.0",
        func=search_v1, schema=SEARCH_V1_SCHEMA,
        metadata={"timeout": 10, "idempotent": True},
        is_default=False,
    )
    registry.register(
        name="search", version="2.0",
        func=search_v2, schema=SEARCH_V2_SCHEMA,
        metadata={"timeout": 15, "idempotent": True},
        is_default=True,  # v2 varsayılan
    )
    
    # File tools
    registry.register(
        name="file_write", version="1.0",
        func=file_write, schema=FILE_WRITE_SCHEMA,
        metadata={"timeout": 5, "idempotent": False},  # ⚠️ Non-idempotent!
    )
    registry.register(
        name="file_read", version="1.0",
        func=file_read, schema=FILE_READ_SCHEMA,
        metadata={"timeout": 5, "idempotent": True},
    )
    
    # Code execution
    registry.register(
        name="execute_code", version="1.0",
        func=execute_code, schema=CODE_EXEC_SCHEMA,
        metadata={"timeout": 10, "idempotent": True},
    )
    
    return registry


async def demo():
    """Server demo."""
    print("=" * 60)
    print("🛠️ Module 3: MCP Server Demo")
    print("=" * 60)
    
    server = create_server()
    
    # Tool listesi
    tools = server.list_tools(include_versions=True)
    print(f"\n📋 Kayıtlı Tool'lar ({len(tools)}):")
    for t in tools:
        print(f"   {t['name']}: {t['description'][:50]}...")
    
    # Search v1
    print(f"\n{'─'*40}")
    print("🔍 Search v1: Basit arama")
    result = await server.call("search", {"query": "Python"}, version="1.0")
    if result["success"]:
        print(f"   {len(result['result'])} sonuç bulundu")
    
    # Search v2
    print(f"\n🔍 Search v2: Gelişmiş arama")
    result = await server.call("search", {
        "query": "Python",
        "category": "tutorial",
        "max_results": 2,
    })
    if result["success"]:
        print(f"   {result['result']['returned']}/{result['result']['total']} sonuç")
    
    # File write + read
    print(f"\n📁 File Write & Read")
    await server.call("file_write", {
        "filename": "test.txt",
        "content": "Merhaba MCP!",
    })
    result = await server.call("file_read", {"filename": "test.txt"})
    if result["success"]:
        print(f"   Dosya içeriği: {result['result']['content']}")
    
    # Code execution
    print(f"\n💻 Code Execution")
    result = await server.call("execute_code", {
        "code": "print(f'Fibonacci: {[1,1,2,3,5,8,13]}')"
    })
    if result["success"]:
        print(f"   Çıktı: {result['result']['output']}")
    
    # İstatistikler
    print(server.get_stats())
    
    print("\n✅ Demo tamamlandı!")


if __name__ == "__main__":
    asyncio.run(demo())
