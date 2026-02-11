"""
Module 2 Runner - Reflection Agent Çalıştırıcı
================================================
Reflection döngüsünü gösteren ana çalıştırma dosyası.

Çalıştırma:
    cd module-02-reflection
    python -m agent.run
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.improve import ReflectiveAgent
from mcp.tools.validate import validate_content
from shared.telemetry.logger import get_logger

logger = get_logger("agent.run")


async def main():
    """Reflection döngüsünü göster."""
    
    print("=" * 60)
    print("🪞 Module 2: Reflective Agent + Validation Tool")
    print("=" * 60)
    
    # ─── Demo 1: Basit Reflection (Validation Tool'suz) ───
    print("\n" + "─" * 60)
    print("📋 Demo 1: Basit Self-Reflection")
    print("─" * 60)
    
    agent = ReflectiveAgent(
        max_reflections=2,
        quality_threshold=7,
    )
    
    result = await agent.run(
        "Python'da bir liste sıralama fonksiyonu yaz. "
        "Fonksiyon docstring, type hint ve hata yönetimi içermeli."
    )
    
    print(f"\n📝 Son Versiyon:")
    print(result.final_content[:500] if result.final_content else "[Boş]")
    
    # ─── Demo 2: Validation Tool ile Reflection ───
    print("\n" + "─" * 60)
    print("📋 Demo 2: Reflection + Validation Tool (MCP)")
    print("─" * 60)
    
    async def validate_fn(content: str) -> dict:
        """Validation tool wrapper."""
        return validate_content(
            content=content,
            min_length=100,
            required_keywords=["def", "return"],
            forbidden_words=["TODO", "FIXME", "HACK"],
        )
    
    agent2 = ReflectiveAgent(
        max_reflections=3,
        quality_threshold=8,
        validate_fn=validate_fn,
    )
    
    result2 = await agent2.run(
        "Python'da Fibonacci dizisini hesaplayan bir fonksiyon yaz. "
        "Hem recursive hem iterative versiyonları olsun. "
        "Docstring ve örnekler ekle."
    )
    
    print(f"\n📝 Son Versiyon:")
    print(result2.final_content[:500] if result2.final_content else "[Boş]")
    
    # ─── Demo 3: Maliyet Karşılaştırması ───
    print("\n" + "─" * 60)
    print("📊 Maliyet Karşılaştırması: Reflection vs No-Reflection")
    print("─" * 60)
    
    print(f"\nDemo 1 (Self-Reflection):")
    print(f"  İterasyon: {result.iterations}")
    print(f"  Token: {result.total_tokens:,}")
    print(f"  Puan: {result.final_score}/10")
    
    print(f"\nDemo 2 (Reflection + Validation):")
    print(f"  İterasyon: {result2.iterations}")
    print(f"  Token: {result2.total_tokens:,}")
    print(f"  Puan: {result2.final_score}/10")
    
    print(f"\n💡 Reflection ekstra maliyet ekler ama kaliteyi artırır.")
    print(f"   Karar sizin: Görev kritik mi? Evet → Reflection kullan.")
    
    print("\n🎉 Module 2 tamamlandı!")
    print("   Sonraki: module-03-tools-and-mcp")


if __name__ == "__main__":
    asyncio.run(main())
