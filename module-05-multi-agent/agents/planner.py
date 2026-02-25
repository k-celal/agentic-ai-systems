"""
Planner Agent - Planlayıcı Agent
==================================
Büyük görevleri küçük, yönetilebilir adımlara böler.

Bu dosya ne yapar?
------------------
PlannerAgent, Multi-Agent sisteminin "beyni"dir.
Kullanıcıdan gelen karmaşık bir görevi alır ve onu
diğer agent'ların (Researcher, Critic, Synthesizer)
işleyebileceği adımlara böler.

Neden Planner Gerekli?
-----------------------
Düşünün ki bir proje yöneticisisiniz:
- Size "AI ve eğitim hakkında rapor yaz" deniyor
- Bunu direkt yazmak yerine, ÖNCE plan yaparsınız:
  1. Hangi konular araştırılacak?
  2. Her konu için ne tür bilgi lazım?
  3. Hangi sırayla ele alınacak?

İyi bir plan → İyi bir sonuç!

Kullanım:
    planner = PlannerAgent()
    result = await planner.process("AI ve eğitim hakkında rapor yaz")
    print(result.content)  # "1. Mevcut AI uygulamaları..."
"""

import sys
import os
import asyncio

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base_agent import BaseAgent, AgentResult


class PlannerAgent(BaseAgent):
    """
    Görev Planlayıcı Agent.
    
    Bu agent:
    1. Kullanıcının görevini analiz eder
    2. Görevi mantıksal alt görevlere böler
    3. Her alt görev için hangi agent'ın çalışacağını belirtir
    4. Adımları sıralı bir plan olarak döndürür
    
    Neden ayrı bir agent?
    - Planlama, ayrı bir uzmanlık alanıdır
    - Planner'ın system prompt'u planlama odaklıdır
    - Düşük temperature (0.3) ile daha tutarlı planlar üretir
    
    Kullanım:
        planner = PlannerAgent()
        
        # Karmaşık bir görev planla
        result = await planner.process(
            "Yapay zeka ve eğitim hakkında kapsamlı bir rapor hazırla"
        )
        
        print(result.content)
        # Çıktı: Adımlara bölünmüş bir plan
    """
    
    def __init__(self, model: str = None):
        """
        PlannerAgent'ı başlat.
        
        Parametreler:
            model: Kullanılacak LLM modeli
        
        Not:
            Temperature 0.3 olarak ayarlanır çünkü planlama
            TUTARLI ve DETERMİNİSTİK olmalıdır. Yaratıcılık
            burada istenmeyen bir şeydir.
        """
        super().__init__(
            name="planner",
            role="Görev Planlayıcı",
            model=model,
            temperature=0.3,  # Düşük temperature = Tutarlı planlar
        )
    
    def _build_system_prompt(self) -> str:
        """
        Planner'a özel system prompt oluştur.
        
        Bu prompt, LLM'e şunları söyler:
        - Sen bir planlayıcısın
        - Görevi adımlara böl
        - Her adım net ve uygulanabilir olsun
        - Araştırma yapılacak alt başlıkları belirle
        
        Döndürür:
            str: Planner system prompt
        """
        return (
            "Sen uzman bir görev planlayıcısısın. Sana verilen karmaşık görevleri "
            "küçük, net ve uygulanabilir adımlara bölmelisin.\n\n"
            "Kurallar:\n"
            "1. Her adım açık ve anlaşılır olmalı\n"
            "2. Adımlar mantıksal bir sıra izlemeli\n"
            "3. Her adım için hangi tür bilgi gerektiğini belirt\n"
            "4. Araştırma yapılacak konuları alt başlıklar halinde listele\n"
            "5. Adımlar numaralı olmalı (1, 2, 3, ...)\n"
            "6. Türkçe yaz\n\n"
            "Çıktı formatı:\n"
            "PLAN:\n"
            "1. [Adım açıklaması] - Gerekli bilgi: [bilgi türü]\n"
            "2. [Adım açıklaması] - Gerekli bilgi: [bilgi türü]\n"
            "...\n\n"
            "Sadece planı yaz, başka açıklama ekleme."
        )
    
    async def process(self, input_data: str) -> AgentResult:
        """
        Verilen görevi adımlara böl.
        
        Bu metot:
        1. Kullanıcının görevini LLM'e gönderir
        2. LLM bir plan üretir
        3. Plan, AgentResult olarak döndürülür
        
        Parametreler:
            input_data: Planlanacak görev açıklaması
        
        Döndürür:
            AgentResult: Adımlara bölünmüş plan
        
        Örnek:
            result = await planner.process("AI ve eğitim raporu hazırla")
            print(result.content)
            # PLAN:
            # 1. AI'ın eğitimdeki mevcut uygulamaları - Gerekli bilgi: Güncel örnekler
            # 2. Kişiselleştirilmiş öğrenme - Gerekli bilgi: Teknoloji detayları
            # 3. Zorluklar ve etik konular - Gerekli bilgi: Araştırma makaleleri
        """
        self.logger.info(f"📋 Görev planlanıyor: {input_data[:80]}...")
        
        # LLM'e planı oluşturmasını söyle
        prompt = (
            f"Aşağıdaki görevi adımlara böl ve her adım için "
            f"araştırılacak konuları belirt:\n\n"
            f"GÖREV: {input_data}"
        )
        
        response = await self._call_llm(prompt)
        
        # Sonucu AgentResult olarak döndür
        return AgentResult(
            agent_name=self.name,
            agent_role=self.role,
            content=response,
            success=bool(response and "[HATA]" not in response),
            metadata={"original_task": input_data},
        )


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m agents.planner
# ─────────────────────────────────────────

if __name__ == "__main__":
    async def main():
        print("📋 PlannerAgent Test")
        print("=" * 50)
        
        # Planner oluştur
        planner = PlannerAgent()
        print(f"Agent: {planner}")
        print(f"System Prompt uzunluğu: {len(planner.system_prompt)} karakter")
        
        # Örnek görevi planla
        görev = "Yapay zeka ve eğitim hakkında kapsamlı bir araştırma raporu hazırla"
        print(f"\nGörev: {görev}")
        print("-" * 50)
        
        result = await planner.process(görev)
        
        print(f"\nSonuç (başarılı: {result.success}):")
        print(result.content)
        
        print("\n✅ PlannerAgent testi tamamlandı!")
    
    asyncio.run(main())
