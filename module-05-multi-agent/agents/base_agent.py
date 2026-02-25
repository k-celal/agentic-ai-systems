"""
Base Agent - Temel Agent Soyut Sınıfı
=======================================
Tüm agent'ların miras aldığı (inherit) temel sınıf.

Bu dosya ne yapar?
------------------
Multi-Agent sisteminde her agent'ın ortak özellikleri vardır:
- Bir adı (name) → Kim bu agent?
- Bir rolü (role) → Ne iş yapar?
- Bir system prompt'u → LLM'e talimat
- Bir process() metodu → Görevi işle

Bu ortak özellikleri tek bir yerde tanımlamak için
**soyut sınıf (abstract class)** kullanıyoruz.

Neden Soyut Sınıf?
-------------------
Soyut sınıf, bir "şablon" gibidir:
- Ortak davranışları tanımlar (ör: LLM çağrısı)
- Alt sınıfların MUTLAKA uygulaması gereken metotları belirler
- Kod tekrarını önler (DRY - Don't Repeat Yourself)

Soyut sınıftan doğrudan nesne oluşturulamaz. Mutlaka
bir alt sınıf (PlannerAgent, ResearcherAgent vb.) oluşturulmalıdır.

Kullanım:
    # Doğrudan kullanılamaz (soyut sınıf):
    # agent = BaseAgent(...)  ← HATA!
    
    # Alt sınıf oluşturup kullanılır:
    class MyAgent(BaseAgent):
        def _build_system_prompt(self):
            return "Sen bir asistansın."
        
        async def process(self, input_data):
            return await self._call_llm(input_data)
"""

import sys
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass, field

# Proje kök dizinini Python path'ine ekle
# Bu sayede 'shared' modülünü import edebiliriz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient, LLMResponse
from shared.telemetry.logger import get_logger


# ============================================================
# Agent Sonuç Sınıfı
# ============================================================

@dataclass
class AgentResult:
    """
    Bir agent'ın process() çağrısından döndüğü sonuç.
    
    Neden ayrı bir sınıf?
    - Agent çıktısını standartlaştırır
    - Hangi agent'ın ne ürettiğini takip etmek kolaylaşır
    - Orkestratör, agent sonuçlarını bu format üzerinden işler
    
    Örnek:
        result = AgentResult(
            agent_name="planner",
            agent_role="Planlayıcı",
            content="Görev 3 adıma bölündü...",
            success=True,
        )
    """
    agent_name: str                     # Agent'ın adı
    agent_role: str                     # Agent'ın rolü
    content: str                        # Üretilen içerik
    success: bool = True                # İşlem başarılı mı?
    error: Optional[str] = None         # Hata mesajı (varsa)
    metadata: dict[str, Any] = field(default_factory=dict)  # Ek bilgiler


# ============================================================
# Base Agent Soyut Sınıfı
# ============================================================

class BaseAgent(ABC):
    """
    Tüm agent'ların temel sınıfı.
    
    Bu sınıf, Multi-Agent sistemindeki her agent'ın
    sahip olması gereken ortak işlevselliği tanımlar.
    
    Alt sınıflar MUTLAKA şunları tanımlamalı:
    1. _build_system_prompt() → Agent'a özel system prompt
    2. process() → Görevi işleme mantığı
    
    Ortak işlevler (hepsi otomatik gelir):
    - LLM çağrısı yapma (_call_llm)
    - Loglama
    - Hata yönetimi
    
    Kullanım:
        class PlannerAgent(BaseAgent):
            def _build_system_prompt(self):
                return "Sen bir planlayıcısın..."
            
            async def process(self, input_data):
                return await self._call_llm(input_data)
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        model: str = None,
        temperature: float = 0.7,
    ):
        """
        BaseAgent'ı başlat.
        
        Parametreler:
            name: Agent'ın benzersiz adı (örn: "planner", "researcher")
            role: Agent'ın rolünün açıklaması (örn: "Planlayıcı")
            model: Kullanılacak LLM modeli (varsayılan: .env'den)
            temperature: Yaratıcılık seviyesi (0=deterministik, 1=yaratıcı)
        
        Örnek:
            agent = PlannerAgent(
                name="planner",
                role="Görev Planlayıcı",
                temperature=0.3,  # Planlama deterministik olmalı
            )
        """
        self.name = name
        self.role = role
        self.temperature = temperature
        
        # LLM istemcisini oluştur
        # Her agent kendi LLM bağlantısına sahiptir
        self.llm = LLMClient(model=model, temperature=temperature)
        
        # System prompt'u oluştur
        # Alt sınıflar _build_system_prompt() ile bunu belirler
        self.system_prompt = self._build_system_prompt()
        
        # Loglama
        self.logger = get_logger(f"agent.{name}")
        
        self.logger.info(f"🤖 {self.role} agent'ı oluşturuldu: {self.name}")
    
    # ─────────────────────────────────────────
    # Soyut Metotlar (Alt sınıflar MUTLAKA tanımlamalı)
    # ─────────────────────────────────────────
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """
        Agent'a özel system prompt oluştur.
        
        Bu metot her alt sınıfta farklıdır:
        - PlannerAgent: "Sen bir görev planlayıcısısın..."
        - ResearcherAgent: "Sen bir araştırmacısın..."
        - CriticAgent: "Sen bir eleştirmensın..."
        - SynthesizerAgent: "Sen bir sentezcisin..."
        
        Döndürür:
            str: System prompt metni
        """
        pass
    
    @abstractmethod
    async def process(self, input_data: str) -> AgentResult:
        """
        Verilen girdiyi işle ve sonuç üret.
        
        Bu metot, agent'ın ANA İŞİDİR. Her alt sınıf
        kendi görevine uygun şekilde implement eder.
        
        Parametreler:
            input_data: İşlenecek girdi (önceki agent'ın çıktısı veya kullanıcı görevi)
        
        Döndürür:
            AgentResult: İşlem sonucu
        
        Örnek (PlannerAgent):
            async def process(self, input_data):
                # LLM'den plan iste
                response = await self._call_llm(
                    f"Bu görevi adımlara böl: {input_data}"
                )
                return AgentResult(
                    agent_name=self.name,
                    agent_role=self.role,
                    content=response,
                )
        """
        pass
    
    # ─────────────────────────────────────────
    # Ortak Metotlar (Tüm agent'lar kullanabilir)
    # ─────────────────────────────────────────
    
    async def _call_llm(self, user_message: str) -> str:
        """
        LLM'e mesaj gönder ve cevap al.
        
        Bu metot, tüm agent'ların ortak kullandığı LLM çağrısıdır.
        System prompt otomatik olarak eklenir.
        
        Parametreler:
            user_message: LLM'e gönderilecek mesaj
        
        Döndürür:
            str: LLM'in cevabı
        
        Neden ortak metot?
        - Her agent LLM çağrısı yapar
        - System prompt ekleme, hata yönetimi, loglama hep aynı
        - Kod tekrarını önler
        """
        self.logger.info(f"🧠 {self.name} düşünüyor...")
        
        try:
            response = await self.llm.chat(
                message=user_message,
                system_prompt=self.system_prompt,
            )
            
            content = response.content or ""
            self.logger.info(f"💬 {self.name} cevap verdi ({len(content)} karakter)")
            
            return content
            
        except Exception as e:
            error_msg = f"{self.name} agent'ı hata verdi: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            return f"[HATA] {error_msg}"
    
    def __repr__(self) -> str:
        """Agent'ın string gösterimi."""
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role}')>"
    
    def get_info(self) -> dict:
        """
        Agent hakkında bilgi döndür.
        
        Orkestratör, agent'ları tanımak için bu metodu kullanabilir.
        
        Döndürür:
            dict: Agent bilgileri
        """
        return {
            "name": self.name,
            "role": self.role,
            "class": self.__class__.__name__,
            "system_prompt_length": len(self.system_prompt),
        }


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m agents.base_agent
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🧪 BaseAgent Test")
    print("=" * 40)
    
    # BaseAgent soyut sınıf olduğu için doğrudan oluşturulamaz.
    # Test için basit bir alt sınıf oluşturuyoruz.
    
    class TestAgent(BaseAgent):
        """Test için basit bir agent."""
        
        def _build_system_prompt(self) -> str:
            return "Sen bir test agent'ısın. Kısaca cevap ver."
        
        async def process(self, input_data: str) -> AgentResult:
            response = await self._call_llm(input_data)
            return AgentResult(
                agent_name=self.name,
                agent_role=self.role,
                content=response,
            )
    
    async def test():
        # Test agent oluştur
        agent = TestAgent(name="test_agent", role="Test Agent")
        print(f"Agent: {agent}")
        print(f"Bilgi: {agent.get_info()}")
        
        # Process çağır
        result = await agent.process("Merhaba, bu bir test!")
        print(f"\nSonuç:")
        print(f"  Agent: {result.agent_name}")
        print(f"  Rol: {result.agent_role}")
        print(f"  Başarılı: {result.success}")
        print(f"  İçerik: {result.content[:200]}")
        
        print("\n✅ BaseAgent testi tamamlandı!")
    
    asyncio.run(test())
