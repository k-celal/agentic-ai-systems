"""
Synthesizer Agent - Sentezci Agent
====================================
Tüm bulguları ve eleştirileri birleştirip tutarlı bir son çıktı üretir.

Bu dosya ne yapar?
------------------
SynthesizerAgent, Multi-Agent sisteminin "son noktası"dır.
Planner'ın planını, Researcher'ın bulgularını ve Critic'in
eleştirilerini alır ve hepsini birleştirerek tutarlı,
kapsamlı ve kaliteli bir son çıktı üretir.

Neden Synthesizer Gerekli?
---------------------------
Düşünün ki bir kitabın baş editörüsünüz:
- Araştırmacılar size ham veriler getirdi
- Eleştirmenler neyin eksik olduğunu söyledi
- SİZİN göreviniz: Her şeyi birleştirip tutarlı bir kitap yazmak

Sentez yapmak zor bir iştir çünkü:
1. Farklı kaynaklardan gelen bilgileri uyumlu hale getirmek gerekir
2. Eleştirileri dikkate alarak eksikleri gidermek gerekir
3. Tutarlı bir anlatım dili ve akış sağlamak gerekir

Kullanım:
    synthesizer = SynthesizerAgent()
    result = await synthesizer.process(tüm_bilgiler)
    print(result.content)  # Son rapor
"""

import sys
import os
import asyncio

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base_agent import BaseAgent, AgentResult


class SynthesizerAgent(BaseAgent):
    """
    Sentezci Agent.
    
    Bu agent:
    1. Planner'ın planını, Researcher'ın bulgularını ve Critic'in eleştirilerini alır
    2. Eleştirileri dikkate alarak bulguları iyileştirir
    3. Tüm bilgileri tutarlı bir yapıda birleştirir
    4. Kaliteli ve kapsamlı bir son çıktı üretir
    
    Neden ayrı bir agent?
    - Sentez, farklı bilgi parçalarını bir araya getirme uzmanlığıdır
    - Synthesizer'ın system prompt'u "birleştirme ve yazım" odaklıdır
    - Orta temperature (0.5) ile hem tutarlı hem akıcı çıktı üretir
    - Pipeline'ın son halkası olarak kaliteyi belirler
    
    Kullanım:
        synthesizer = SynthesizerAgent()
        
        tüm_veriler = f"PLAN:\\n{plan}\\nBULGULAR:\\n{bulgular}\\nELEŞTİRİ:\\n{eleştiri}"
        result = await synthesizer.process(tüm_veriler)
        print(result.content)  # Son rapor
    """
    
    def __init__(self, model: str = None):
        """
        SynthesizerAgent'ı başlat.
        
        Parametreler:
            model: Kullanılacak LLM modeli
        
        Not:
            Temperature 0.5 olarak ayarlanır çünkü sentez
            hem TUTARLI hem de AKICI olmalıdır. Çok düşük
            temperature mekanik olur, çok yüksek tutarsız olur.
        """
        super().__init__(
            name="synthesizer",
            role="Sentezci",
            model=model,
            temperature=0.5,  # Orta temperature = Tutarlı ama akıcı
        )
    
    def _build_system_prompt(self) -> str:
        """
        Synthesizer'a özel system prompt oluştur.
        
        Bu prompt, LLM'e şunları söyler:
        - Sen bir sentezcisin
        - Farklı kaynaklardan gelen bilgileri birleştir
        - Eleştirileri dikkate al
        - Tutarlı ve akıcı bir çıktı üret
        
        Döndürür:
            str: Synthesizer system prompt
        """
        return (
            "Sen uzman bir sentezci ve rapor yazarısın. Sana farklı kaynaklardan gelen "
            "bilgiler (plan, araştırma bulguları, eleştiriler) verilecek. "
            "Görevin bunları birleştirip tutarlı, kapsamlı ve kaliteli bir son rapor yazmak.\n\n"
            "Kurallar:\n"
            "1. Eleştirileri dikkate al ve eksikleri gider\n"
            "2. Bilgileri mantıksal bir sırayla düzenle\n"
            "3. Tutarlı bir anlatım dili kullan\n"
            "4. Giriş, gelişme, sonuç yapısına uy\n"
            "5. Somut örnekler ve veriler ekle\n"
            "6. Tekrarlardan kaçın\n"
            "7. Türkçe yaz\n\n"
            "Çıktı formatı:\n"
            "# [Rapor Başlığı]\n\n"
            "## Giriş\n"
            "[Konuya giriş]\n\n"
            "## [Ana Başlık 1]\n"
            "[İçerik]\n\n"
            "## [Ana Başlık 2]\n"
            "[İçerik]\n\n"
            "## Sonuç ve Değerlendirme\n"
            "[Özet ve gelecek öneriler]"
        )
    
    async def process(self, input_data: str) -> AgentResult:
        """
        Tüm bilgileri birleştirip son raporu oluştur.
        
        Bu metot:
        1. Plan, bulgular ve eleştirileri alır
        2. Eleştirileri dikkate alarak içeriği iyileştirir
        3. Her şeyi tutarlı bir rapor halinde birleştirir
        
        Parametreler:
            input_data: Birleştirilecek tüm bilgiler (plan + bulgular + eleştiri)
        
        Döndürür:
            AgentResult: Son rapor
        
        Örnek:
            combined = f"PLAN:\\n{plan}\\nBULGULAR:\\n{bulgular}\\nELEŞTİRİ:\\n{eleştiri}"
            result = await synthesizer.process(combined)
            print(result.content)
            # # Yapay Zeka ve Eğitim Raporu
            # ## Giriş
            # Yapay zeka, eğitim sektöründe devrim yaratıyor...
        """
        self.logger.info(f"📝 Sentez başlıyor...")
        
        # LLM'e son raporu yazdır
        prompt = (
            f"Aşağıda bir araştırma sürecinin tüm çıktıları var: "
            f"Plan, araştırma bulguları ve eleştiri raporu. "
            f"Bunları birleştirerek tutarlı, kapsamlı ve kaliteli bir son rapor yaz. "
            f"Eleştirilerdeki önerileri dikkate al ve eksikleri gider.\n\n"
            f"{input_data}"
        )
        
        response = await self._call_llm(prompt)
        
        return AgentResult(
            agent_name=self.name,
            agent_role=self.role,
            content=response,
            success=bool(response and "[HATA]" not in response),
            metadata={"input_length": len(input_data)},
        )


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m agents.synthesizer
# ─────────────────────────────────────────

if __name__ == "__main__":
    async def main():
        print("📝 SynthesizerAgent Test")
        print("=" * 50)
        
        synthesizer = SynthesizerAgent()
        print(f"Agent: {synthesizer}")
        
        # Tüm verileri birleştir
        örnek_veriler = (
            "=== PLAN ===\n"
            "1. AI'ın eğitimdeki mevcut uygulamaları\n"
            "2. Kişiselleştirilmiş öğrenme\n"
            "3. Gelecek trendleri\n\n"
            "=== ARAŞTIRMA BULGULARI ===\n"
            "## AI'ın Eğitimdeki Mevcut Uygulamaları\n"
            "Adaptif öğrenme platformları öğrencilerin bireysel hızlarına göre "
            "içerik sunar. Otomatik değerlendirme sistemleri öğretmen yükünü azaltır.\n\n"
            "## Kişiselleştirilmiş Öğrenme\n"
            "AI destekli sistemler her öğrencinin güçlü ve zayıf yönlerini analiz eder.\n\n"
            "## Gelecek Trendleri\n"
            "AI eğitimde daha da yaygınlaşacak.\n\n"
            "=== ELEŞTİRİ ===\n"
            "## Güçlü Yönler\n"
            "- Konu çeşitliliği iyi\n"
            "## Zayıf Yönler\n"
            "- Gelecek trendleri bölümü çok kısa\n"
            "- İstatistiksel veri eksik\n"
            "## Öneriler\n"
            "- Somut sayısal veriler ekle\n"
            "- Gelecek trendleri bölümünü genişlet"
        )
        
        print(f"\nToplam girdi uzunluğu: {len(örnek_veriler)} karakter")
        print("-" * 50)
        
        result = await synthesizer.process(örnek_veriler)
        
        print(f"\nSonuç (başarılı: {result.success}):")
        print(result.content)
        
        print("\n✅ SynthesizerAgent testi tamamlandı!")
    
    asyncio.run(main())
