"""
Generate - İçerik Üretici
===========================
Reflection döngüsünün ilk adımı: İlk çıktıyı üret.

Bu modül ne yapar?
-----------------
Verilen bir görev için ilk taslak çıktıyı üretir.
Bu çıktı mükemmel olmak zorunda değil — eleştiri ve
iyileştirme aşamalarında geliştirilecek.

Kullanım:
    from agent.generate import Generator
    
    gen = Generator()
    draft = await gen.generate("Python'da fibonacci fonksiyonu yaz")
    print(draft.content)
"""

import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger


@dataclass
class GeneratedContent:
    """
    Üretilen içeriği temsil eder.
    
    Attributes:
        content: Üretilen metin
        task: Orijinal görev
        iteration: Kaçıncı iterasyon (1 = ilk üretim)
        token_count: Kullanılan token sayısı
    """
    content: str
    task: str
    iteration: int = 1
    token_count: int = 0


class Generator:
    """
    İçerik üretici.
    
    Verilen görev için LLM kullanarak içerik üretir.
    Reflection döngüsünün "Generate" aşamasıdır.
    
    Kullanım:
        gen = Generator()
        
        # İlk üretim
        draft = await gen.generate("Python sıralama fonksiyonu yaz")
        
        # Eleştiriden sonra yeniden üretim (feedback ile)
        improved = await gen.regenerate(
            task="Python sıralama fonksiyonu yaz",
            previous_content=draft.content,
            feedback="Docstring ekle ve type hint kullan"
        )
    """
    
    def __init__(self, model: str = None):
        self.llm = LLMClient(model=model)
        self.logger = get_logger("agent.generate")
    
    async def generate(self, task: str) -> GeneratedContent:
        """
        Görev için ilk içeriği üret.
        
        Parametreler:
            task: Yapılacak görev
        
        Döndürür:
            GeneratedContent: Üretilen içerik
        
        Örnek:
            draft = await gen.generate("E-posta taslağı yaz")
            print(draft.content)
        """
        self.logger.info(f"📝 İçerik üretiliyor: {task}")
        
        response = await self.llm.chat(
            message=task,
            system_prompt=(
                "Sen bir içerik üreticisisin. Verilen görevi en iyi şekilde tamamla.\n"
                "Açık, anlaşılır ve kaliteli içerik üret.\n"
                "Türkçe yanıt ver."
            ),
        )
        
        content = response.content or "[Üretim başarısız]"
        
        self.logger.info(f"✅ İçerik üretildi ({len(content)} karakter)")
        
        return GeneratedContent(
            content=content,
            task=task,
            iteration=1,
            token_count=response.usage.total_tokens,
        )
    
    async def regenerate(
        self,
        task: str,
        previous_content: str,
        feedback: str,
        iteration: int = 2,
    ) -> GeneratedContent:
        """
        Eleştiriden sonra içeriği yeniden üret.
        
        Bu fonksiyon, önceki üretimi ve eleştiriyi dikkate alarak
        geliştirilmiş bir versiyon üretir.
        
        Parametreler:
            task: Orijinal görev
            previous_content: Önceki üretilen içerik
            feedback: Eleştiri/geri bildirim
            iteration: Kaçıncı iterasyon
        
        Döndürür:
            GeneratedContent: Geliştirilmiş içerik
        """
        self.logger.info(f"🔄 İçerik yeniden üretiliyor (iterasyon {iteration})")
        
        response = await self.llm.chat(
            message=(
                f"## Orijinal Görev\n{task}\n\n"
                f"## Önceki Üretim\n{previous_content}\n\n"
                f"## Eleştiri ve Geri Bildirim\n{feedback}\n\n"
                f"Yukarıdaki eleştirileri dikkate alarak içeriği geliştir. "
                f"Sadece geliştirilmiş versiyonu yaz."
            ),
            system_prompt=(
                "Sen bir içerik geliştirme uzmanısın. "
                "Verilen eleştirileri dikkate alarak içeriği iyileştir.\n"
                "Eleştirilerdeki her noktayı adresle.\n"
                "Türkçe yanıt ver."
            ),
        )
        
        content = response.content or previous_content
        
        self.logger.info(f"✅ İçerik geliştirildi ({len(content)} karakter)")
        
        return GeneratedContent(
            content=content,
            task=task,
            iteration=iteration,
            token_count=response.usage.total_tokens,
        )
