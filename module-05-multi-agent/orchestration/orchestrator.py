"""
Orchestrator - Orkestratör (Agent Yöneticisi)
===============================================
Multi-Agent sistemindeki tüm agent'ların akışını yönetir.

Bu dosya ne yapar?
------------------
Orkestratör, bir "orkestra şefi" gibi çalışır:
1. Hangi agent'ın ne zaman çağrılacağını belirler
2. Agent'lar arası mesaj akışını yönetir
3. Pipeline'ı (Planner → Researcher → Critic → Synthesizer) çalıştırır
4. Hata yönetimi ve loglama yapar

Neden Orkestratör Gerekli?
--------------------------
Birden fazla agent varsa, birinin çıktısını diğerine iletmek,
sırayı yönetmek ve hataları ele almak gerekir.
Bu karmaşık koordinasyonu tek bir yerde (orkestratör) toplamak:
- Kodu daha okunabilir yapar
- Değişiklikleri kolaylaştırır (yeni agent eklemek vb.)
- Hata ayıklamayı basitleştirir

Kullanım:
    from orchestration.orchestrator import Orchestrator
    
    orchestrator = Orchestrator(agents=[planner, researcher, critic, synthesizer])
    result = await orchestrator.run_pipeline("AI ve eğitim hakkında rapor yaz")
    print(result)

Mesaj Akışı:
    Kullanıcı → Planner → Researcher → Critic → Synthesizer → Son Rapor
"""

import sys
import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from agents.base_agent import BaseAgent, AgentResult


# ============================================================
# Agent Mesaj Sınıfı
# ============================================================

@dataclass
class AgentMessage:
    """
    Agent'lar arası iletişimde kullanılan mesaj formatı.
    
    Neden standart bir mesaj formatı gerekli?
    - Agent'lar farklı roller ve çıktılar üretir
    - Orkestratör, mesajları takip edebilmeli
    - Hata ayıklama sırasında "kim ne söyledi?" sorusu kolayca cevaplanabilmeli
    - Mesaj geçmişi tutmak sistemi denetlenebilir yapar
    
    Mesaj tipleri:
    - "task": Kullanıcıdan gelen başlangıç görevi
    - "plan": Planner'ın ürettiği plan
    - "research": Researcher'ın bulguları
    - "critique": Critic'in eleştirileri
    - "synthesis": Synthesizer'ın son raporu
    - "error": Hata mesajı
    
    Örnek:
        msg = AgentMessage(
            sender="planner",
            receiver="researcher",
            content="PLAN: 1. AI uygulamaları 2. Kişisel öğrenme",
            message_type="plan",
        )
    """
    sender: str                         # Mesajı gönderen agent adı
    receiver: str                       # Mesajı alan agent adı
    content: str                        # Mesaj içeriği
    message_type: str = "info"          # Mesaj tipi (task, plan, research, critique, synthesis, error)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """İnsan tarafından okunabilir format."""
        return (
            f"[{self.timestamp}] {self.sender} → {self.receiver} "
            f"({self.message_type}): {self.content[:100]}..."
        )
    
    def to_dict(self) -> dict:
        """Sözlük formatına çevir."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ============================================================
# Pipeline Sonuç Sınıfı
# ============================================================

@dataclass
class PipelineResult:
    """
    Pipeline çalışmasının toplam sonucu.
    
    Bu sınıf, tüm pipeline'ın durumunu özetler:
    - Hangi agent'lar çalıştı?
    - Mesaj geçmişi nedir?
    - Son çıktı ne?
    - Ne kadar sürdü?
    
    Örnek:
        result = PipelineResult(
            task="AI raporu yaz",
            final_output="# Rapor...",
            success=True,
        )
    """
    task: str                                       # Başlangıç görevi
    final_output: str = ""                          # Son çıktı
    success: bool = False                           # Pipeline başarılı mı?
    messages: list[AgentMessage] = field(default_factory=list)  # Mesaj geçmişi
    agent_results: dict[str, AgentResult] = field(default_factory=dict)  # Agent sonuçları
    error: Optional[str] = None                     # Hata mesajı (varsa)
    duration_seconds: float = 0.0                   # Toplam süre


# ============================================================
# Orkestratör Sınıfı
# ============================================================

class Orchestrator:
    """
    Multi-Agent pipeline'ını yöneten orkestratör.
    
    Bu sınıf:
    1. Agent'ları kayıt altına alır
    2. Pipeline sırasını belirler
    3. Agent'ları sırayla çağırır
    4. Mesaj akışını yönetir
    5. Hata yönetimi yapar
    
    Pipeline Akışı:
        Planner → Researcher → Critic → Synthesizer
    
    Mesaj Veriyolu (Message Bus):
        Tüm mesajlar bir listeye kaydedilir.
        Bu sayede pipeline tamamlandıktan sonra
        tüm agent'lar arası iletişim incelenebilir.
    
    Kullanım:
        orchestrator = Orchestrator(
            agents=[planner, researcher, critic, synthesizer]
        )
        result = await orchestrator.run_pipeline("Görev açıklaması")
        
        # Mesaj geçmişini incele
        for msg in result.messages:
            print(msg)
    """
    
    def __init__(self, agents: list[BaseAgent]):
        """
        Orkestratörü başlat.
        
        Parametreler:
            agents: Pipeline sırasına göre sıralı agent listesi
                    [planner, researcher, critic, synthesizer]
        
        Neden sıralı liste?
        - Pipeline'da her agent, bir öncekinin çıktısını alır
        - Sıra önemlidir: Planner ÖNCE çalışmalı ki plan oluşsun
        - Bu sıra Orchestrator'a dışarıdan verilir (esneklik!)
        """
        self.agents = {agent.name: agent for agent in agents}
        self.pipeline_order = [agent.name for agent in agents]
        
        # Mesaj veriyolu (message bus)
        # Tüm agent mesajları bu listeye kaydedilir
        # Bu basit bir liste tabanlı mesaj sistemidir
        self.message_bus: list[AgentMessage] = []
        
        # Loglama
        self.logger = get_logger("orchestrator")
        
        self.logger.info(
            f"🎼 Orkestratör oluşturuldu. "
            f"Agent'lar: {self.pipeline_order}"
        )
    
    def _add_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "info",
    ) -> AgentMessage:
        """
        Mesaj veriyoluna yeni mesaj ekle.
        
        Bu metot, agent'lar arası her iletişimi kayıt altına alır.
        
        Parametreler:
            sender: Gönderen agent adı
            receiver: Alan agent adı
            content: Mesaj içeriği
            message_type: Mesaj tipi
        
        Döndürür:
            AgentMessage: Oluşturulan mesaj
        """
        msg = AgentMessage(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
        )
        self.message_bus.append(msg)
        self.logger.info(f"📨 {msg}")
        return msg
    
    async def run_pipeline(self, task: str) -> PipelineResult:
        """
        Multi-Agent pipeline'ını çalıştır.
        
        Bu metot ana çalıştırma metodudur:
        1. Kullanıcının görevini alır
        2. İlk agent'a (Planner) gönderir
        3. Her agent'ın çıktısını bir sonraki agent'a iletir
        4. Son agent'ın (Synthesizer) çıktısı son rapor olur
        
        Pipeline:
            task → Planner → Researcher → Critic → Synthesizer → final_output
        
        Parametreler:
            task: Kullanıcının görevi
        
        Döndürür:
            PipelineResult: Pipeline'ın toplam sonucu
        
        Örnek:
            result = await orchestrator.run_pipeline(
                "Yapay zeka ve eğitim hakkında rapor hazırla"
            )
            
            if result.success:
                print(result.final_output)
            else:
                print(f"Hata: {result.error}")
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"\n{'═' * 60}")
        self.logger.info(f"🚀 Pipeline başlatılıyor: {task[:80]}...")
        self.logger.info(f"{'═' * 60}")
        
        # Sonuç nesnesi
        result = PipelineResult(task=task)
        
        # Mesaj veriyolunu temizle (yeni pipeline için)
        self.message_bus.clear()
        
        # Başlangıç mesajı
        self._add_message(
            sender="kullanıcı",
            receiver=self.pipeline_order[0],
            content=task,
            message_type="task",
        )
        
        # Her agent'ı sırayla çalıştır
        current_input = task
        
        for i, agent_name in enumerate(self.pipeline_order):
            agent = self.agents[agent_name]
            
            self.logger.info(f"\n{'─' * 50}")
            self.logger.info(
                f"📍 Adım {i + 1}/{len(self.pipeline_order)}: "
                f"{agent.role} ({agent.name})"
            )
            self.logger.info(f"{'─' * 50}")
            
            try:
                # Agent'ı çalıştır
                agent_result = await agent.process(current_input)
                
                # Sonucu kaydet
                result.agent_results[agent_name] = agent_result
                
                if not agent_result.success:
                    # Agent başarısız olduysa pipeline'ı durdur
                    error_msg = (
                        f"{agent.role} ({agent_name}) başarısız oldu: "
                        f"{agent_result.error or 'Bilinmeyen hata'}"
                    )
                    self.logger.error(f"❌ {error_msg}")
                    
                    self._add_message(
                        sender=agent_name,
                        receiver="orkestratör",
                        content=error_msg,
                        message_type="error",
                    )
                    
                    result.error = error_msg
                    result.success = False
                    break
                
                # Bir sonraki agent'ın girdi bilgisini hazırla
                # Son agent değilse, çıktıyı mesaj olarak gönder
                next_agent = (
                    self.pipeline_order[i + 1]
                    if i + 1 < len(self.pipeline_order)
                    else "son_çıktı"
                )
                
                # Mesaj tipini agent rolüne göre belirle
                message_types = {
                    "planner": "plan",
                    "researcher": "research",
                    "critic": "critique",
                    "synthesizer": "synthesis",
                }
                msg_type = message_types.get(agent_name, "info")
                
                self._add_message(
                    sender=agent_name,
                    receiver=next_agent,
                    content=agent_result.content,
                    message_type=msg_type,
                )
                
                # Synthesizer için özel durum:
                # Tüm önceki agent çıktılarını birleştirerek gönder
                if next_agent != "son_çıktı" and next_agent == "synthesizer":
                    # Synthesizer'a tüm verileri birleştirip gönder
                    combined_input = self._build_synthesis_input(result)
                    current_input = combined_input
                else:
                    # Diğer agent'lar için sadece mevcut çıktıyı gönder
                    current_input = agent_result.content
                
                self.logger.info(
                    f"✅ {agent.role} tamamlandı "
                    f"({len(agent_result.content)} karakter)"
                )
                
            except Exception as e:
                error_msg = f"{agent.role} ({agent_name}) hatası: {str(e)}"
                self.logger.error(f"❌ {error_msg}")
                
                self._add_message(
                    sender=agent_name,
                    receiver="orkestratör",
                    content=error_msg,
                    message_type="error",
                )
                
                result.error = error_msg
                result.success = False
                break
        
        else:
            # Tüm agent'lar başarıyla tamamlandı
            result.success = True
            # Son agent'ın çıktısı, pipeline'ın son çıktısıdır
            last_agent = self.pipeline_order[-1]
            if last_agent in result.agent_results:
                result.final_output = result.agent_results[last_agent].content
        
        # Süreyi hesapla
        result.duration_seconds = time.time() - start_time
        
        # Mesaj geçmişini sonuca ekle
        result.messages = list(self.message_bus)
        
        # Özet raporu yazdır
        self._print_summary(result)
        
        return result
    
    def _build_synthesis_input(self, result: PipelineResult) -> str:
        """
        Synthesizer için tüm agent çıktılarını birleştir.
        
        Synthesizer, sadece Critic'in çıktısını değil,
        TÜM agent'ların çıktılarını görmeli ki
        eksiksiz bir sentez yapabilsin.
        
        Parametreler:
            result: Şu ana kadarki pipeline sonucu
        
        Döndürür:
            str: Birleştirilmiş girdi metni
        """
        parts = []
        
        if "planner" in result.agent_results:
            parts.append(
                f"=== PLAN (Planlayıcı Agent Çıktısı) ===\n"
                f"{result.agent_results['planner'].content}"
            )
        
        if "researcher" in result.agent_results:
            parts.append(
                f"=== ARAŞTIRMA BULGULARI (Araştırmacı Agent Çıktısı) ===\n"
                f"{result.agent_results['researcher'].content}"
            )
        
        if "critic" in result.agent_results:
            parts.append(
                f"=== ELEŞTİRİ RAPORU (Eleştirmen Agent Çıktısı) ===\n"
                f"{result.agent_results['critic'].content}"
            )
        
        return "\n\n".join(parts)
    
    def _print_summary(self, result: PipelineResult):
        """Pipeline sonuç özetini yazdır."""
        self.logger.info(f"\n{'═' * 60}")
        self.logger.info(f"📊 PİPELINE SONUCU")
        self.logger.info(f"{'═' * 60}")
        self.logger.info(f"   Görev: {result.task[:60]}...")
        self.logger.info(f"   Başarılı: {'✅ Evet' if result.success else '❌ Hayır'}")
        self.logger.info(f"   Süre: {result.duration_seconds:.2f} saniye")
        self.logger.info(f"   Toplam mesaj: {len(result.messages)}")
        self.logger.info(f"   Çalışan agent'lar: {list(result.agent_results.keys())}")
        
        if result.error:
            self.logger.info(f"   Hata: {result.error}")
        
        if result.final_output:
            self.logger.info(f"   Çıktı uzunluğu: {len(result.final_output)} karakter")
        
        self.logger.info(f"{'═' * 60}")
    
    def get_message_history(self) -> list[dict]:
        """
        Tüm mesaj geçmişini döndür.
        
        Bu metot, pipeline'ın nasıl çalıştığını
        incelemek ve hata ayıklamak için kullanılır.
        
        Döndürür:
            list[dict]: Mesaj listesi
        """
        return [msg.to_dict() for msg in self.message_bus]


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m orchestration.orchestrator
# ─────────────────────────────────────────

if __name__ == "__main__":
    from agents.planner import PlannerAgent
    from agents.researcher import ResearcherAgent
    from agents.critic import CriticAgent
    from agents.synthesizer import SynthesizerAgent
    
    async def main():
        print("🎼 Orchestrator Test")
        print("=" * 50)
        
        # Agent'ları oluştur
        agents = [
            PlannerAgent(),
            ResearcherAgent(),
            CriticAgent(),
            SynthesizerAgent(),
        ]
        
        # Orkestratörü oluştur
        orchestrator = Orchestrator(agents=agents)
        
        # Pipeline'ı çalıştır
        result = await orchestrator.run_pipeline(
            "Yapay zeka ve eğitim hakkında kısa bir araştırma raporu hazırla"
        )
        
        print(f"\n{'=' * 50}")
        print(f"Pipeline Başarılı: {result.success}")
        print(f"Mesaj Sayısı: {len(result.messages)}")
        
        if result.final_output:
            print(f"\n📄 Son Rapor:")
            print(result.final_output[:500])
        
        print("\n✅ Orchestrator testi tamamlandı!")
    
    asyncio.run(main())
