"""
Agent Runner - Agent Çalıştırıcı
==================================
Bu dosya, Module 1 agent'ını başlatır ve çalıştırır.

Çalıştırma:
    cd module-01-agent-fundamentals
    python -m agent.run

Bu dosya ne yapar?
1. MCP Server'ı oluşturur (tool'lar ile)
2. Agent Loop'u oluşturur
3. Örnek görevleri çalıştırır
4. Sonuçları gösterir
"""

import sys
import os
import asyncio

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.loop import AgentLoop
from mcp.server import create_server
from shared.telemetry.logger import get_logger

logger = get_logger("agent.run")


async def main():
    """
    Ana çalıştırma fonksiyonu.
    
    Adım adım:
    1. MCP Server oluştur (tool'ları barındırır)
    2. Agent Loop oluştur (tool'ları ve şemaları bağla)
    3. Örnek görevleri çalıştır
    """
    
    print("=" * 60)
    print("🤖 Module 1: Hello Agent + Hello MCP")
    print("=" * 60)
    
    # ─── Adım 1: MCP Server oluştur ───
    print("\n📡 MCP Server oluşturuluyor...")
    server = create_server()
    
    # Tool fonksiyonlarını ve şemalarını al
    # Agent, bu bilgileri kullanarak tool çağrısı yapar
    tools = {
        "echo": server.tools["echo"],
        "get_time": server.tools["get_time"],
    }
    tool_schemas = server.get_openai_tools()
    
    print(f"   Tool'lar hazır: {list(tools.keys())}")
    
    # ─── Adım 2: Agent oluştur ───
    print("\n🤖 Agent oluşturuluyor...")
    agent = AgentLoop(
        tools=tools,
        tool_schemas=tool_schemas,
        max_loops=5,  # Maksimum 5 döngü (sonsuz döngü koruması)
    )
    print("   Agent hazır!")
    
    # ─── Adım 3: Görevleri çalıştır ───
    
    # Görev 1: Basit echo testi
    print("\n" + "─" * 60)
    print("📋 Görev 1: Echo testi")
    print("─" * 60)
    result = await agent.run("'Merhaba Dünya' mesajını echo aracı ile tekrarla")
    print(f"\n📊 Sonuç: {result.status}")
    if result.final_answer:
        print(f"💬 Cevap: {result.final_answer}")
    
    # Görev 2: Saat sorgulama
    print("\n" + "─" * 60)
    print("📋 Görev 2: Saat sorgulama")
    print("─" * 60)
    
    # Yeni agent (temiz mesaj geçmişi için)
    agent2 = AgentLoop(
        tools=tools,
        tool_schemas=tool_schemas,
        max_loops=5,
    )
    result = await agent2.run("İstanbul'da şu an saat kaç? get_time aracını kullan.")
    print(f"\n📊 Sonuç: {result.status}")
    if result.final_answer:
        print(f"💬 Cevap: {result.final_answer}")
    
    # ─── Sonuç Raporu ───
    print("\n" + "=" * 60)
    print("📊 GENEL RAPOR")
    print("=" * 60)
    print(agent.cost_tracker.get_report())
    print(agent2.cost_tracker.get_report())
    
    print("\n🎉 Module 1 tamamlandı!")
    print("   Sonraki: module-02-reflection")


if __name__ == "__main__":
    asyncio.run(main())
