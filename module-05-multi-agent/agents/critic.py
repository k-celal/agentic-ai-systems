"""
Critic Agent - Eleştirmen Agent
================================
Diğer agent'ların çıktılarını inceler, eleştirir ve iyileştirme önerir.

Bu dosya ne yapar?
------------------
CriticAgent, Multi-Agent sisteminin "kalite kontrol" birimidir.
Researcher'ın topladığı bilgileri eleştirel gözle inceler ve
eksikleri, hataları, iyileştirme alanlarını belirler.

Neden Critic Gerekli?
----------------------
Module 2'de öğrendiğimiz "Reflection" (yansıma) kavramını hatırlayın:
- Bir agent kendi çıktısını eleştirmekte zorlanır
- FARKLI bir agent (farklı system prompt ile) aynı çıktıyı
  çok daha etkili bir şekilde eleştirebilir

Bu, gerçek hayattaki "peer review" (meslektaş değerlendirmesi) sürecine benzer:
- Bir yazar kendi makalesindeki hataları göremez
- Başka bir editör bu hataları kolayca bulur

Kullanım:
    critic = CriticAgent()
    result = await critic.process(researcher_output)
    print(result.content)  # Eleştiri ve öneriler
"""

import sys
import os
import asyncio

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base_agent import BaseAgent, AgentResult


class CriticAgent(BaseAgent):
    """
    Eleştirmen Agent.
    
    Bu agent:
    1. Researcher'ın bulgularını alır
    2. İçeriği kalite, doğruluk ve kapsamlılık açısından değerlendirir
    3. Güçlü yönleri ve zayıf yönleri belirler
    4. İyileştirme önerileri sunar
    
    Neden ayrı bir agent?
    - Eleştiri, farklı bir bakış açısı gerektirir
    - Critic'in system prompt'u "eleştirel düşünme" odaklıdır
    - Düşük temperature (0.3) ile tutarlı ve objektif eleştiri üretir
    - Module 2'deki Reflection kavramını Multi-Agent'a taşır
    
    Kullanım:
        critic = CriticAgent()
        result = await critic.process(researcher_bulgulari)
        print(result.content)  # Eleştiri raporu
    """
    
    def __init__(self, model: str = None):
        """
        CriticAgent'ı başlat.
        
        Parametreler:
            model: Kullanılacak LLM modeli
        
        Not:
            Temperature 0.3 olarak ayarlanır çünkü eleştiri
            OBJEKTİF ve TUTARLI olmalıdır. Subjektif yorumlar
            kalite kontrolde istenmeyen bir durumdur.
        """
        super().__init__(
            name="critic",
            role="Eleştirmen",
            model=model,
            temperature=0.3,  # Düşük temperature = Objektif eleştiri
        )
    
    def _build_system_prompt(self) -> str:
        """
        Critic'e özel system prompt oluştur.
        
        Bu prompt, LLM'e şunları söyler:
        - Sen bir eleştirmensin
        - Çıktıyı kalite, doğruluk, kapsam açısından değerlendir
        - Güçlü ve zayıf yönleri belirle
        - Yapıcı eleştiri yap (sadece sorun değil, çözüm de öner)
        
        Döndürür:
            str: Critic system prompt
        """
        return (
            "Sen uzman bir eleştirmen ve kalite kontrol uzmanısın. "
            "Sana verilen içeriği dikkatli bir şekilde incele ve eleştir.\n\n"
            "Değerlendirme kriterlerin:\n"
            "1. DOĞRULUK: Bilgiler doğru mu? Yanlış veya yanıltıcı bilgi var mı?\n"
            "2. KAPSAM: Konu yeterince kapsamlı mı? Eksik kalan alan var mı?\n"
            "3. DERİNLİK: Bilgiler yeterince detaylı mı? Yüzeysel mi kalınmış?\n"
            "4. TUTARLILIK: İçerik kendi içinde tutarlı mı? Çelişki var mı?\n"
            "5. KAYNAK: Somut örnekler ve veriler var mı?\n\n"
            "Kurallar:\n"
            "- YAPICI eleştiri yap (sadece sorun değil, çözüm de öner)\n"
            "- Güçlü yönleri de belirt (sadece olumsuz değil)\n"
            "- Her eleştiri için somut iyileştirme önerisi sun\n"
            "- Türkçe yaz\n\n"
            "Çıktı formatı:\n"
            "ELEŞTİRİ RAPORU:\n\n"
            "## Güçlü Yönler\n"
            "- [güçlü yön 1]\n"
            "- [güçlü yön 2]\n\n"
            "## Zayıf Yönler ve İyileştirme Önerileri\n"
            "- [zayıf yön 1] → Öneri: [iyileştirme]\n"
            "- [zayıf yön 2] → Öneri: [iyileştirme]\n\n"
            "## Genel Değerlendirme\n"
            "[Kısa özet ve puan: 1-10]"
        )
    
    async def process(self, input_data: str) -> AgentResult:
        """
        Verilen içeriği eleştir.
        
        Bu metot:
        1. Researcher'ın bulgularını alır
        2. LLM'den eleştirel değerlendirme ister
        3. Eleştiri raporunu döndürür
        
        Parametreler:
            input_data: Eleştirilecek içerik (genellikle Researcher çıktısı)
        
        Döndürür:
            AgentResult: Eleştiri raporu
        
        Örnek:
            result = await critic.process(researcher_bulgulari)
            print(result.content)
            # ELEŞTİRİ RAPORU:
            # ## Güçlü Yönler
            # - Konu çeşitliliği iyi...
            # ## Zayıf Yönler ve İyileştirme Önerileri
            # - Kaynak eksikliği → Öneri: İstatistiksel veri ekle
        """
        self.logger.info(f"🔎 İçerik eleştiriliyor...")
        
        # LLM'e eleştiri yaptır
        prompt = (
            f"Aşağıdaki araştırma bulgularını eleştirel bir gözle değerlendir. "
            f"Güçlü ve zayıf yönlerini belirle, iyileştirme önerileri sun.\n\n"
            f"DEĞERLENDİRİLECEK İÇERİK:\n{input_data}"
        )
        
        response = await self._call_llm(prompt)
        
        return AgentResult(
            agent_name=self.name,
            agent_role=self.role,
            content=response,
            success=bool(response and "[HATA]" not in response),
            metadata={"reviewed_content_length": len(input_data)},
        )


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m agents.critic
# ─────────────────────────────────────────

if __name__ == "__main__":
    async def main():
        print("🔎 CriticAgent Test")
        print("=" * 50)
        
        critic = CriticAgent()
        print(f"Agent: {critic}")
        
        # Örnek araştırma bulguları ile eleştiri yap
        örnek_bulgular = (
            "ARAŞTIRMA BULGULARI:\n\n"
            "## AI'ın Eğitimdeki Mevcut Uygulamaları\n"
            "Yapay zeka, eğitim sektöründe birçok alanda kullanılmaktadır. "
            "Adaptif öğrenme platformları, öğrencilerin bireysel hızlarına göre "
            "içerik sunar.\n\n"
            "## Kişiselleştirilmiş Öğrenme\n"
            "AI destekli sistemler, her öğrencinin güçlü ve zayıf yönlerini "
            "analiz ederek kişiye özel müfredat oluşturabilir.\n\n"
            "## Gelecek Trendleri\n"
            "AI eğitimde daha da yaygınlaşacak."
        )
        
        print(f"\nDeğerlendirilecek içerik uzunluğu: {len(örnek_bulgular)} karakter")
        print("-" * 50)
        
        result = await critic.process(örnek_bulgular)
        
        print(f"\nSonuç (başarılı: {result.success}):")
        print(result.content)
        
        print("\n✅ CriticAgent testi tamamlandı!")
    
    asyncio.run(main())
