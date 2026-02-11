"""
Critique - Eleştiri Modülü
============================
Reflection döngüsünün ikinci adımı: Üretilen içeriği eleştir.

Eleştiri neden önemli?
---------------------
İlk üretim genellikle "yeterli" ama "mükemmel" değildir.
Eleştiri aşaması, eksiklikleri ve hataları tespit eder.

İki tür eleştiri:
1. Self-Critique (Öz Eleştiri): LLM kendi çıktısını eleştirir
2. External Validation: Dış bir araç/sistem ile doğrulama

Kullanım:
    from agent.critique import Critic
    
    critic = Critic()
    feedback = await critic.critique(content, task)
    print(feedback.issues)     # Bulunan sorunlar
    print(feedback.score)      # Kalite puanı (1-10)
    print(feedback.suggestions) # İyileştirme önerileri
"""

import sys
import os
import json
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger
from shared.utils.helpers import parse_json_safely


@dataclass
class CritiqueResult:
    """
    Eleştiri sonucunu temsil eder.
    
    Attributes:
        score: Kalite puanı (1-10, 10=mükemmel)
        issues: Tespit edilen sorunlar listesi
        suggestions: İyileştirme önerileri
        is_acceptable: Kabul edilebilir mi? (score >= threshold)
        token_count: Kullanılan token sayısı
    """
    score: int = 5
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    is_acceptable: bool = False
    raw_feedback: str = ""
    token_count: int = 0


class Critic:
    """
    İçerik eleştirmeni.
    
    Üretilen içeriği analiz eder ve geri bildirim verir.
    
    Kullanım:
        critic = Critic(threshold=7)
        
        feedback = await critic.critique(
            content="def sort(lst): return sorted(lst)",
            task="Python sıralama fonksiyonu yaz"
        )
        
        if feedback.is_acceptable:
            print("İçerik kabul edildi!")
        else:
            print(f"Sorunlar: {feedback.issues}")
            print(f"Öneriler: {feedback.suggestions}")
    """
    
    def __init__(self, threshold: int = 7, model: str = None):
        """
        Critic oluştur.
        
        Parametreler:
            threshold: Kabul eşiği (bu puan ve üzeri "kabul edilir")
            model: Kullanılacak LLM modeli
        """
        self.threshold = threshold
        self.llm = LLMClient(model=model)
        self.logger = get_logger("agent.critique")
    
    async def critique(
        self,
        content: str,
        task: str,
        criteria: list[str] = None,
    ) -> CritiqueResult:
        """
        İçeriği eleştir.
        
        Parametreler:
            content: Eleştirilecek içerik
            task: Orijinal görev (bağlam için)
            criteria: Değerlendirme kriterleri (isteğe bağlı)
        
        Döndürür:
            CritiqueResult: Eleştiri sonucu
        
        Örnek:
            result = await critic.critique(
                content="print('hello')",
                task="Python'da merhaba dünya programı yaz",
                criteria=["Okunabilirlik", "Doğruluk", "Tamlık"]
            )
        """
        self.logger.info("🔍 İçerik eleştiriliyor...")
        
        # Varsayılan kriterler
        if criteria is None:
            criteria = [
                "Doğruluk (içerik faktüel olarak doğru mu?)",
                "Tamlık (görevin tüm gereksinimleri karşılanmış mı?)",
                "Açıklık (anlaşılır mı?)",
                "Kalite (iyi yazılmış mı?)",
            ]
        
        criteria_text = "\n".join(f"- {c}" for c in criteria)
        
        response = await self.llm.chat(
            message=(
                f"## Görev\n{task}\n\n"
                f"## Üretilen İçerik\n{content}\n\n"
                f"## Değerlendirme Kriterleri\n{criteria_text}\n\n"
                "Yukarıdaki içeriği değerlendir."
            ),
            system_prompt=(
                "Sen sıkı bir içerik eleştirmenisin. Verilen içeriği objektif değerlendir.\n\n"
                "MUTLAKA aşağıdaki JSON formatında yanıt ver:\n"
                '{\n'
                '  "score": 1-10 arası puan,\n'
                '  "issues": ["sorun 1", "sorun 2", ...],\n'
                '  "suggestions": ["öneri 1", "öneri 2", ...]\n'
                '}\n\n'
                "Kurallar:\n"
                "- 1-3: Çok kötü, ciddi sorunlar var\n"
                "- 4-6: Orta, iyileştirme gerekli\n"
                "- 7-8: İyi, küçük düzeltmeler yeterli\n"
                "- 9-10: Mükemmel, değişiklik gerekmez\n"
                "- Dürüst ve yapıcı ol\n"
                "- Her sorun için somut öneri ver"
            ),
        )
        
        # Cevabı parse et
        result = self._parse_critique(response.content or "")
        result.token_count = response.usage.total_tokens
        result.is_acceptable = result.score >= self.threshold
        
        self.logger.info(f"📊 Puan: {result.score}/10 | Kabul: {'✅' if result.is_acceptable else '❌'}")
        self.logger.info(f"   Sorunlar: {len(result.issues)} | Öneriler: {len(result.suggestions)}")
        
        return result
    
    async def critique_with_validation(
        self,
        content: str,
        task: str,
        validation_result: dict,
    ) -> CritiqueResult:
        """
        Dış doğrulama sonucu ile birlikte eleştir.
        
        MCP validation tool'unun sonucunu da dikkate alır.
        
        Parametreler:
            content: Eleştirilecek içerik
            task: Orijinal görev
            validation_result: Validation tool sonucu
        
        Döndürür:
            CritiqueResult: Eleştiri sonucu
        """
        self.logger.info("🔍 İçerik eleştiriliyor (validation sonucu ile)...")
        
        response = await self.llm.chat(
            message=(
                f"## Görev\n{task}\n\n"
                f"## Üretilen İçerik\n{content}\n\n"
                f"## Doğrulama Sonucu\n{json.dumps(validation_result, ensure_ascii=False, indent=2)}\n\n"
                "Hem içeriği hem de doğrulama sonuçlarını değerlendir."
            ),
            system_prompt=(
                "Sen bir kalite kontrol uzmanısın. İçeriği ve doğrulama sonuçlarını değerlendir.\n\n"
                "MUTLAKA aşağıdaki JSON formatında yanıt ver:\n"
                '{\n'
                '  "score": 1-10 arası puan,\n'
                '  "issues": ["sorun 1", "sorun 2", ...],\n'
                '  "suggestions": ["öneri 1", "öneri 2", ...]\n'
                '}'
            ),
        )
        
        result = self._parse_critique(response.content or "")
        result.token_count = response.usage.total_tokens
        result.is_acceptable = result.score >= self.threshold
        
        return result
    
    def _parse_critique(self, text: str) -> CritiqueResult:
        """LLM cevabını CritiqueResult'a dönüştür."""
        parsed = parse_json_safely(text)
        
        if parsed:
            return CritiqueResult(
                score=min(10, max(1, int(parsed.get("score", 5)))),
                issues=parsed.get("issues", []),
                suggestions=parsed.get("suggestions", []),
                raw_feedback=text,
            )
        
        # JSON parse edilemezse, ham metni kullan
        return CritiqueResult(
            score=5,
            issues=["Eleştiri JSON formatında değil"],
            suggestions=["İçeriği tekrar değerlendir"],
            raw_feedback=text,
        )
