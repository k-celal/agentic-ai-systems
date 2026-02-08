"""
Simple Planner - Basit Görev Planlayıcı
=========================================
Büyük bir görevi küçük adımlara bölen basit planlayıcı.

Task Decomposition Nedir?
-------------------------
Bir görevi küçük, yönetilebilir adımlara bölme işlemi.

Örnek:
    Görev: "İstanbul ve Ankara'nın hava durumunu karşılaştır"
    
    Adımlar:
    1. İstanbul hava durumunu al
    2. Ankara hava durumunu al
    3. İkisini karşılaştır ve özet yaz

Kullanım:
    from agent.planner import SimplePlanner
    
    planner = SimplePlanner()
    steps = await planner.decompose("İstanbul ve Ankara hava durumunu karşılaştır")
    
    for step in steps:
        print(f"Adım {step['step']}: {step['description']}")
"""

import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger


@dataclass
class PlanStep:
    """
    Bir plan adımını temsil eder.
    
    Örnek:
        step = PlanStep(
            step_number=1,
            description="İstanbul hava durumunu al",
            tool_needed="get_weather",
            tool_args={"city": "Istanbul"}
        )
    """
    step_number: int              # Adım numarası
    description: str              # Adımın açıklaması
    tool_needed: str = None       # Gerekli tool (varsa)
    tool_args: dict = None        # Tool parametreleri (varsa)
    completed: bool = False       # Tamamlandı mı?


class SimplePlanner:
    """
    Basit görev planlayıcı.
    
    Bu planlayıcı, LLM kullanarak bir görevi adımlara böler.
    Module 1 için basit tutulmuştur — daha gelişmiş versiyonlar
    sonraki modüllerde olacak.
    
    Kullanım:
        planner = SimplePlanner(available_tools=["get_weather", "echo", "get_time"])
        steps = await planner.decompose("İstanbul hava durumunu öğren")
        
        for step in steps:
            print(f"  {step.step_number}. {step.description}")
            if step.tool_needed:
                print(f"     Tool: {step.tool_needed}")
    """
    
    def __init__(self, available_tools: list[str] = None, model: str = None):
        """
        Planner oluştur.
        
        Parametreler:
            available_tools: Kullanılabilir tool isimleri
            model: Kullanılacak LLM modeli
        """
        self.available_tools = available_tools or []
        self.llm = LLMClient(model=model)
        self.logger = get_logger("agent.planner")
    
    async def decompose(self, task: str) -> list[PlanStep]:
        """
        Görevi adımlara böl.
        
        Parametreler:
            task: Bölünecek görev
        
        Döndürür:
            list[PlanStep]: Plan adımları
        
        Örnek:
            steps = await planner.decompose(
                "İstanbul ve Ankara hava durumunu karşılaştır"
            )
            # [
            #   PlanStep(1, "İstanbul hava durumunu al", "get_weather", {"city": "Istanbul"}),
            #   PlanStep(2, "Ankara hava durumunu al", "get_weather", {"city": "Ankara"}),
            #   PlanStep(3, "İki şehri karşılaştır ve özet yaz"),
            # ]
        """
        self.logger.info(f"📋 Görev planlanıyor: {task}")
        
        # LLM'e plan yapmasını iste
        tools_info = f"Kullanılabilir tool'lar: {', '.join(self.available_tools)}" if self.available_tools else "Hiç tool yok."
        
        response = await self.llm.chat(
            message=f"Görev: {task}",
            system_prompt=(
                "Sen bir görev planlayıcısın. Verilen görevi basit adımlara böl.\n\n"
                f"{tools_info}\n\n"
                "Her adımı şu formatta yaz:\n"
                "1. [Adım açıklaması] (tool: tool_adı)\n"
                "2. [Adım açıklaması] (tool: tool_adı)\n"
                "...\n\n"
                "Tool gerekmiyorsa (tool: yok) yaz.\n"
                "Maksimum 5 adım olsun."
            ),
        )
        
        # Cevabı parse et (basit parsing)
        steps = self._parse_steps(response.content or "")
        
        self.logger.info(f"✅ {len(steps)} adım planlandı")
        for step in steps:
            self.logger.info(f"   {step.step_number}. {step.description}")
        
        return steps
    
    def _parse_steps(self, text: str) -> list[PlanStep]:
        """
        LLM cevabını plan adımlarına dönüştür.
        
        Bu basit bir parser — LLM'in cevap formatı her zaman
        aynı olmayabilir, bu yüzden esnek tutuyoruz.
        """
        steps = []
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Numara ile başlayan satırları bul
            # Örnek: "1. İstanbul hava durumunu al (tool: get_weather)"
            for i in range(1, 10):
                prefix = f"{i}."
                if line.startswith(prefix):
                    description = line[len(prefix):].strip()
                    
                    # Tool bilgisini çıkar
                    tool_needed = None
                    if "(tool:" in description:
                        parts = description.split("(tool:")
                        description = parts[0].strip()
                        tool_part = parts[1].replace(")", "").strip()
                        if tool_part.lower() != "yok":
                            tool_needed = tool_part
                    
                    steps.append(PlanStep(
                        step_number=i,
                        description=description,
                        tool_needed=tool_needed,
                    ))
                    break
        
        # Hiç adım bulunamadıysa, tüm metni tek adım olarak al
        if not steps:
            steps.append(PlanStep(
                step_number=1,
                description=text[:200],
            ))
        
        return steps
    
    def decompose_simple(self, task: str) -> list[PlanStep]:
        """
        LLM kullanmadan basit kural tabanlı planlama.
        
        LLM çağrısı yapmak istemiyorsanız veya test ederken
        bu fonksiyonu kullanabilirsiniz.
        
        Parametreler:
            task: Görev
        
        Döndürür:
            list[PlanStep]: Plan adımları
        
        Örnek:
            steps = planner.decompose_simple("Saati öğren")
            # [PlanStep(1, "Saati öğren", tool_needed=None)]
        """
        # Basit kural: "ve", "sonra", "ardından" kelimeleri ile böl
        separators = [" ve ", " sonra ", " ardından ", ", "]
        
        parts = [task]
        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts
        
        # Boş parçaları filtrele
        parts = [p.strip() for p in parts if p.strip()]
        
        steps = []
        for i, part in enumerate(parts, 1):
            # Hangi tool gerekli olabilir?
            tool = self._guess_tool(part)
            steps.append(PlanStep(
                step_number=i,
                description=part,
                tool_needed=tool,
            ))
        
        return steps
    
    def _guess_tool(self, description: str) -> str | None:
        """Açıklamadan hangi tool gerektiğini tahmin et."""
        description_lower = description.lower()
        
        tool_keywords = {
            "get_time": ["saat", "zaman", "tarih", "time"],
            "echo": ["tekrarla", "echo", "söyle"],
            "get_weather": ["hava", "sıcaklık", "derece"],
            "search": ["ara", "bul", "search"],
        }
        
        for tool_name, keywords in tool_keywords.items():
            if tool_name in self.available_tools:
                if any(kw in description_lower for kw in keywords):
                    return tool_name
        
        return None
