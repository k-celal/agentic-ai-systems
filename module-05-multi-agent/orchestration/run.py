"""
Multi-Agent Runner - Çoklu Agent Çalıştırıcı
===============================================
Multi-Agent pipeline'ını başlatır ve demo görev çalıştırır.

Çalıştırma:
    cd module-05-multi-agent
    python -m orchestration.run

Bu dosya ne yapar?
------------------
1. Tüm agent'ları oluşturur (Planner, Researcher, Critic, Synthesizer)
2. Orkestratörü oluşturur
3. Demo görevi çalıştırır: "Yapay zeka ve eğitim hakkında bir araştırma raporu hazırla"
4. Agent'lar arası mesaj akışını gösterir
5. Son raporu ekrana basar

Bu dosya, Module 5'in "ana giriş noktası"dır.
Tüm parçaların nasıl bir araya geldiğini burada göreceksiniz.
"""

import sys
import os
import asyncio

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
# Module dizinini de ekle (agents, mcp vb. için)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.critic import CriticAgent
from agents.synthesizer import SynthesizerAgent
from orchestration.orchestrator import Orchestrator
from shared.telemetry.logger import get_logger

logger = get_logger("multi_agent.run")


async def main():
    """
    Ana çalıştırma fonksiyonu.
    
    Adım adım:
    1. Agent'ları oluştur
    2. Orkestratörü oluştur
    3. Demo görevi çalıştır
    4. Mesaj akışını göster
    5. Son raporu yazdır
    """
    
    print("=" * 60)
    print("🤝 Module 5: Multi-Agent Sistemi")
    print("=" * 60)
    
    # ─── Adım 1: Agent'ları Oluştur ───
    print("\n🤖 Agent'lar oluşturuluyor...")
    
    planner = PlannerAgent()
    researcher = ResearcherAgent()
    critic = CriticAgent()
    synthesizer = SynthesizerAgent()
    
    agents = [planner, researcher, critic, synthesizer]
    
    print(f"   Agent'lar hazır:")
    for agent in agents:
        print(f"   - {agent.role} ({agent.name})")
    
    # ─── Adım 2: Orkestratörü Oluştur ───
    print("\n🎼 Orkestratör oluşturuluyor...")
    orchestrator = Orchestrator(agents=agents)
    print("   Orkestratör hazır!")
    
    # ─── Adım 3: Demo Görevi Çalıştır ───
    demo_task = "Yapay zeka ve eğitim hakkında bir araştırma raporu hazırla"
    
    print(f"\n{'─' * 60}")
    print(f"📋 Demo Görev: {demo_task}")
    print(f"{'─' * 60}")
    print()
    print("Pipeline: Planner → Researcher → Critic → Synthesizer")
    print()
    
    # Pipeline'ı çalıştır
    result = await orchestrator.run_pipeline(demo_task)
    
    # ─── Adım 4: Mesaj Akışını Göster ───
    print(f"\n{'═' * 60}")
    print("📨 AGENT MESAJ GEÇMİŞİ")
    print(f"{'═' * 60}")
    
    for i, msg in enumerate(result.messages, 1):
        # Mesaj tipine göre emoji
        type_emojis = {
            "task": "📋",
            "plan": "📝",
            "research": "🔍",
            "critique": "🔎",
            "synthesis": "📄",
            "error": "❌",
            "info": "ℹ️",
        }
        emoji = type_emojis.get(msg.message_type, "📨")
        
        print(f"\n{emoji} Mesaj {i}:")
        print(f"   Gönderen: {msg.sender}")
        print(f"   Alan:     {msg.receiver}")
        print(f"   Tip:      {msg.message_type}")
        print(f"   Zaman:    {msg.timestamp}")
        print(f"   İçerik:   {msg.content[:150]}...")
    
    # ─── Adım 5: Son Raporu Göster ───
    print(f"\n{'═' * 60}")
    print("📄 SON RAPOR")
    print(f"{'═' * 60}")
    
    if result.success and result.final_output:
        print(result.final_output)
    elif result.error:
        print(f"❌ Pipeline hatası: {result.error}")
    else:
        print("⚠️ Rapor oluşturulamadı.")
    
    # ─── Sonuç Raporu ───
    print(f"\n{'═' * 60}")
    print("📊 GENEL RAPOR")
    print(f"{'═' * 60}")
    print(f"   Görev:             {result.task}")
    print(f"   Başarılı:          {'✅ Evet' if result.success else '❌ Hayır'}")
    print(f"   Toplam süre:       {result.duration_seconds:.2f} saniye")
    print(f"   Toplam mesaj:      {len(result.messages)}")
    print(f"   Çalışan agent'lar: {list(result.agent_results.keys())}")
    
    if result.final_output:
        print(f"   Çıktı uzunluğu:   {len(result.final_output)} karakter")
    
    # Her agent'ın ürettiği çıktı uzunluğu
    print(f"\n   Agent Çıktı Boyutları:")
    for name, agent_result in result.agent_results.items():
        print(f"   - {name}: {len(agent_result.content)} karakter")
    
    print(f"\n{'═' * 60}")
    print("🎉 Module 5 demo tamamlandı!")
    print("   Alıştırmalar için: exercises/exercises.md")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
