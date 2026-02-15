"""
Tool Router - Akıllı Tool Yönlendirici
=========================================
Agent'ın hangi tool'u kullanacağına karar veren bileşen.

Tool Router Nedir?
-----------------
50 tane tool varsa, LLM her seferinde hepsini görmek zorunda değil.
Tool Router, görev bağlamına göre en uygun tool'ları filtreler.

Kullanım:
    from agent.tool_router import ToolRouter
    
    router = ToolRouter(registry=my_registry)
    
    # Görev için uygun tool'ları bul
    relevant_tools = router.get_relevant_tools("Python ile dosya yaz")
    # → [file_write, execute_code]  (search değil!)
"""

import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mcp_server.registry import ToolRegistry
from shared.telemetry.logger import get_logger


class ToolRouter:
    """
    Akıllı tool yönlendirici.
    
    Görev bağlamına göre en uygun tool'ları seçer.
    Bu sayede LLM'e gereksiz tool bilgisi göndermeyiz
    → Daha az token → Daha az maliyet!
    
    Kullanım:
        router = ToolRouter(registry)
        
        # Arama görevi
        tools = router.get_relevant_tools("Python hakkında bilgi bul")
        # → search tool döner
        
        # Kod görevi
        tools = router.get_relevant_tools("Fibonacci hesapla")
        # → execute_code tool döner
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.logger = get_logger("agent.tool_router")
        
        # Tool-anahtar kelime eşlemeleri
        self.tool_keywords = {
            "search": ["ara", "bul", "search", "sorgula", "listele"],
            "file_write": ["yaz", "kaydet", "oluştur", "dosya", "write", "save"],
            "file_read": ["oku", "göster", "read", "dosya", "içerik"],
            "execute_code": ["hesapla", "çalıştır", "kod", "python", "execute", "run", "compute"],
        }
    
    def get_relevant_tools(self, task: str, max_tools: int = 3) -> list[dict]:
        """
        Görev için en uygun tool'ları bul.
        
        Parametreler:
            task: Görev açıklaması
            max_tools: Maksimum tool sayısı
        
        Döndürür:
            list[dict]: Uygun tool şemaları
        """
        task_lower = task.lower()
        tool_scores = {}
        
        for tool_name, keywords in self.tool_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                tool_scores[tool_name] = score
        
        # Score'a göre sırala
        sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
        
        # En uygun tool'ları döndür
        relevant = []
        for tool_name, score in sorted_tools[:max_tools]:
            entry = self.registry.get_tool(tool_name)
            if entry:
                relevant.append(entry.schema.to_openai_format())
                self.logger.info(f"🎯 Uygun tool: {tool_name} (skor: {score})")
        
        # Hiç uygun tool bulunamadıysa, tümünü döndür
        if not relevant:
            self.logger.info("🔄 Spesifik tool bulunamadı, tümü döndürülüyor")
            for tool_list in self.registry.list_tools():
                entry = self.registry.get_tool(tool_list["name"])
                if entry:
                    relevant.append(entry.schema.to_openai_format())
        
        return relevant[:max_tools]
    
    def route(self, task: str) -> Optional[str]:
        """
        Görev için en uygun tek tool'u seç.
        
        Parametreler:
            task: Görev açıklaması
        
        Döndürür:
            str: Tool adı veya None
        """
        task_lower = task.lower()
        best_tool = None
        best_score = 0
        
        for tool_name, keywords in self.tool_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > best_score:
                best_score = score
                best_tool = tool_name
        
        return best_tool


if __name__ == "__main__":
    import asyncio
    
    async def demo():
        from mcp_server.server import create_server
        
        print("🎯 Tool Router Demo")
        print("=" * 40)
        
        registry = create_server()
        router = ToolRouter(registry)
        
        # Test görevleri
        tasks = [
            "Python hakkında bilgi ara",
            "Fibonacci hesaplama kodu çalıştır",
            "Sonuçları bir dosyaya kaydet",
            "Dosyadaki veriyi oku ve analiz et",
        ]
        
        for task in tasks:
            print(f"\n📋 Görev: {task}")
            best = router.route(task)
            print(f"   En uygun tool: {best}")
            
            relevant = router.get_relevant_tools(task)
            print(f"   Tüm uygun tool'lar: {[t['function']['name'] for t in relevant]}")
    
    asyncio.run(demo())
