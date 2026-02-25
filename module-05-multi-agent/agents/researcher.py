"""
Researcher Agent - Araştırmacı Agent
======================================
Planner'ın oluşturduğu plan doğrultusunda bilgi toplar.

Bu dosya ne yapar?
------------------
ResearcherAgent, Multi-Agent sisteminin "elleri"dir.
Planner'ın belirlediği her adım için bilgi toplar,
araştırma yapar ve bulgularını yapılandırılmış şekilde sunar.

Neden Researcher Gerekli?
--------------------------
Düşünün ki bir araştırma asistanısınız:
- Proje yöneticisi (Planner) size "AI'ın eğitimdeki kullanımlarını araştır" diyor
- Siz gidip kütüphaneye, internete bakıyorsunuz
- Bulduğunuz bilgileri düzenli şekilde raporluyorsunuz

Araştırma uzmanlık gerektirir — herkes her konuyu bilemez.
Bu yüzden Researcher'ın system prompt'u araştırma odaklıdır.

Kullanım:
    researcher = ResearcherAgent()
    result = await researcher.process(plan_content)
    print(result.content)  # Araştırma bulguları
"""

import sys
import os
import asyncio

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base_agent import BaseAgent, AgentResult


class ResearcherAgent(BaseAgent):
    """
    Araştırmacı Agent.
    
    Bu agent:
    1. Planner'ın oluşturduğu planı alır
    2. Her adım için detaylı bilgi toplar
    3. Bulguları yapılandırılmış formatta sunar
    4. Kaynak ve örnekler ekler
    
    Neden ayrı bir agent?
    - Araştırma, derinlemesine bilgi gerektirir
    - Researcher'ın system prompt'u "bilgi toplama" odaklıdır
    - Orta-yüksek temperature (0.7) ile çeşitli bilgiler üretir
    - İleride gerçek arama tool'ları bağlanabilir (web search, database vb.)
    
    Kullanım:
        researcher = ResearcherAgent()
        result = await researcher.process(planner_plan)
        print(result.content)  # Detaylı araştırma bulguları
    """
    
    def __init__(self, model: str = None):
        """
        ResearcherAgent'ı başlat.
        
        Parametreler:
            model: Kullanılacak LLM modeli
        
        Not:
            Temperature 0.7 olarak ayarlanır çünkü araştırma
            çeşitli ve geniş kapsamlı bilgi üretmeli.
        """
        super().__init__(
            name="researcher",
            role="Araştırmacı",
            model=model,
            temperature=0.7,  # Orta temperature = Çeşitli bilgiler
        )
    
    def _build_system_prompt(self) -> str:
        """
        Researcher'a özel system prompt oluştur.
        
        Bu prompt, LLM'e şunları söyler:
        - Sen bir araştırmacısın
        - Verilen plan doğrultusunda bilgi topla
        - Her başlık için detaylı açıklama yap
        - Örnekler ve veriler ekle
        
        Döndürür:
            str: Researcher system prompt
        """
        return (
            "Sen uzman bir araştırmacısın. Sana verilen plan doğrultusunda "
            "her konu hakkında kapsamlı ve detaylı bilgi toplaman gerekiyor.\n\n"
            "Kurallar:\n"
            "1. Her başlık için detaylı açıklama yap\n"
            "2. Somut örnekler ve veriler ekle\n"
            "3. Güncel bilgiler kullan\n"
            "4. Her bulguyu açık ve anlaşılır yaz\n"
            "5. Bilgi eksikliği varsa bunu belirt\n"
            "6. Türkçe yaz\n\n"
            "Çıktı formatı:\n"
            "ARAŞTIRMA BULGULARI:\n\n"
            "## [Başlık 1]\n"
            "[Detaylı bilgi, örnekler, veriler]\n\n"
            "## [Başlık 2]\n"
            "[Detaylı bilgi, örnekler, veriler]\n"
            "...\n\n"
            "Her başlık için en az 3-4 cümle yaz."
        )
    
    async def process(self, input_data: str) -> AgentResult:
        """
        Plan doğrultusunda araştırma yap.
        
        Bu metot:
        1. Planner'ın planını alır
        2. Her adım için LLM'den bilgi ister
        3. Bulguları derler ve döndürür
        
        Parametreler:
            input_data: Planner'ın ürettiği plan (veya araştırma konusu)
        
        Döndürür:
            AgentResult: Araştırma bulguları
        
        Örnek:
            result = await researcher.process(plan_metni)
            print(result.content)
            # ARAŞTIRMA BULGULARI:
            # ## AI'ın Eğitimdeki Mevcut Uygulamaları
            # Yapay zeka, eğitim sektöründe birçok alanda kullanılmaktadır...
        """
        self.logger.info(f"🔍 Araştırma başlıyor...")
        
        # LLM'e araştırma yaptır
        prompt = (
            f"Aşağıdaki plan doğrultusunda her başlık için detaylı araştırma yap. "
            f"Her konu için somut örnekler, güncel veriler ve açıklamalar ekle.\n\n"
            f"PLAN:\n{input_data}"
        )
        
        response = await self._call_llm(prompt)
        
        return AgentResult(
            agent_name=self.name,
            agent_role=self.role,
            content=response,
            success=bool(response and "[HATA]" not in response),
            metadata={"plan_input": input_data[:200]},
        )


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m agents.researcher
# ─────────────────────────────────────────

if __name__ == "__main__":
    async def main():
        print("🔍 ResearcherAgent Test")
        print("=" * 50)
        
        researcher = ResearcherAgent()
        print(f"Agent: {researcher}")
        
        # Örnek plan ile araştırma yap
        örnek_plan = (
            "PLAN:\n"
            "1. Yapay zekanın eğitimdeki mevcut kullanımları - Gerekli bilgi: Güncel örnekler\n"
            "2. Kişiselleştirilmiş öğrenme sistemleri - Gerekli bilgi: Teknoloji detayları\n"
            "3. Gelecek trendleri ve zorluklar - Gerekli bilgi: Uzman görüşleri"
        )
        
        print(f"\nPlan:\n{örnek_plan}")
        print("-" * 50)
        
        result = await researcher.process(örnek_plan)
        
        print(f"\nSonuç (başarılı: {result.success}):")
        print(result.content)
        
        print("\n✅ ResearcherAgent testi tamamlandı!")
    
    asyncio.run(main())
