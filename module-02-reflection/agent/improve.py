"""
Improve - İyileştirme Modülü
===============================
Reflection döngüsünün üçüncü adımı: Eleştiriyi dikkate alarak geliştir.

Bu modül tüm reflection döngüsünü orkestra eder:
Generate → Critique → Improve → (Tekrar?)

Kullanım:
    from agent.improve import ReflectiveAgent
    
    agent = ReflectiveAgent(max_reflections=3, quality_threshold=7)
    result = await agent.run("Python sıralama fonksiyonu yaz")
    
    print(f"Son versiyon: {result.final_content}")
    print(f"İterasyon sayısı: {result.iterations}")
    print(f"Kalite puanı: {result.final_score}")
"""

import sys
import os
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.generate import Generator, GeneratedContent
from agent.critique import Critic, CritiqueResult
from shared.telemetry.logger import get_logger
from shared.telemetry.cost_tracker import CostTracker


@dataclass
class ReflectionResult:
    """
    Reflection döngüsünün sonucu.
    
    Tüm iterasyonların geçmişini ve son durumu tutar.
    """
    task: str                                   # Orijinal görev
    final_content: str = ""                     # Son geliştirilmiş içerik
    final_score: int = 0                        # Son kalite puanı
    iterations: int = 0                         # Toplam iterasyon sayısı
    history: list[dict] = field(default_factory=list)  # Tüm iterasyonların geçmişi
    total_tokens: int = 0                       # Toplam token kullanımı
    total_cost: float = 0.0                     # Toplam maliyet
    status: str = "pending"                     # pending, completed, max_iterations


@dataclass
class IterationRecord:
    """Tek bir iterasyonun kaydı."""
    iteration: int
    content: str
    score: int
    issues: list[str]
    suggestions: list[str]
    tokens_used: int


class ReflectiveAgent:
    """
    Reflection döngüsünü çalıştıran ana agent.
    
    Bu agent:
    1. İçerik üretir (Generate)
    2. İçeriği eleştirir (Critique)
    3. Eleştirilere göre iyileştirir (Improve)
    4. Kalite eşiği aşılana veya max iterasyona ulaşana kadar tekrarlar
    
    Kullanım:
        agent = ReflectiveAgent(
            max_reflections=3,      # Maksimum 3 iyileştirme
            quality_threshold=7,     # 7+ puan "yeterli"
        )
        
        result = await agent.run("Python'da Fibonacci fonksiyonu yaz")
        
        print(f"Sonuç: {result.status}")
        print(f"Puan: {result.final_score}/10")
        print(f"İterasyon: {result.iterations}")
        print(f"Maliyet: ${result.total_cost:.6f}")
        
        # Geçmişi göster
        for h in result.history:
            print(f"  İterasyon {h['iteration']}: Puan {h['score']}/10")
    """
    
    def __init__(
        self,
        max_reflections: int = 3,
        quality_threshold: int = 7,
        model: str = None,
        validate_fn=None,
    ):
        """
        ReflectiveAgent oluştur.
        
        Parametreler:
            max_reflections: Maksimum iyileştirme sayısı
            quality_threshold: Kabul edilebilir kalite eşiği (1-10)
            model: Kullanılacak LLM modeli
            validate_fn: Dış doğrulama fonksiyonu (isteğe bağlı)
        """
        self.max_reflections = max_reflections
        self.quality_threshold = quality_threshold
        self.validate_fn = validate_fn
        
        # Alt bileşenler
        self.generator = Generator(model=model)
        self.critic = Critic(threshold=quality_threshold, model=model)
        self.logger = get_logger("agent.reflective")
        self.cost_tracker = CostTracker(budget_limit=0.50)
    
    async def run(self, task: str) -> ReflectionResult:
        """
        Reflection döngüsünü çalıştır.
        
        Parametreler:
            task: Yapılacak görev
        
        Döndürür:
            ReflectionResult: Döngünün sonucu
        """
        result = ReflectionResult(task=task)
        
        self.logger.info(f"{'='*50}")
        self.logger.info(f"🪞 Reflection Döngüsü Başlatılıyor")
        self.logger.info(f"   Görev: {task}")
        self.logger.info(f"   Max iterasyon: {self.max_reflections}")
        self.logger.info(f"   Kalite eşiği: {self.quality_threshold}/10")
        self.logger.info(f"{'='*50}")
        
        # ─── Adım 1: İlk üretim ───
        self.logger.info(f"\n{'─'*40}")
        self.logger.info("📝 İterasyon 1: İlk Üretim")
        
        generated = await self.generator.generate(task)
        current_content = generated.content
        result.total_tokens += generated.token_count
        
        self.logger.info(f"   Üretilen: {current_content[:100]}...")
        
        # ─── Reflection Döngüsü ───
        for i in range(self.max_reflections):
            iteration_num = i + 1
            self.logger.info(f"\n{'─'*40}")
            self.logger.info(f"🔄 İterasyon {iteration_num}: Eleştiri ve İyileştirme")
            
            # ─── Adım 2: Eleştir ───
            if self.validate_fn:
                # Dış doğrulama varsa, önce onu çalıştır
                self.logger.info("🔧 Dış doğrulama çalıştırılıyor...")
                validation = await self.validate_fn(current_content)
                critique = await self.critic.critique_with_validation(
                    content=current_content,
                    task=task,
                    validation_result=validation,
                )
            else:
                critique = await self.critic.critique(
                    content=current_content,
                    task=task,
                )
            
            result.total_tokens += critique.token_count
            
            # Geçmişe kaydet
            result.history.append({
                "iteration": iteration_num,
                "content_preview": current_content[:200],
                "score": critique.score,
                "issues": critique.issues,
                "suggestions": critique.suggestions,
            })
            
            self.logger.info(f"   📊 Puan: {critique.score}/10")
            for issue in critique.issues[:3]:
                self.logger.info(f"   ❌ {issue}")
            for suggestion in critique.suggestions[:3]:
                self.logger.info(f"   💡 {suggestion}")
            
            # ─── Yeterli mi? ───
            if critique.is_acceptable:
                self.logger.info(f"\n✅ Kalite eşiği aşıldı! ({critique.score}/{self.quality_threshold})")
                result.final_content = current_content
                result.final_score = critique.score
                result.iterations = iteration_num
                result.status = "completed"
                break
            
            # ─── Adım 3: İyileştir ───
            feedback = self._format_feedback(critique)
            
            improved = await self.generator.regenerate(
                task=task,
                previous_content=current_content,
                feedback=feedback,
                iteration=iteration_num + 1,
            )
            
            current_content = improved.content
            result.total_tokens += improved.token_count
            
            self.logger.info(f"   ✏️ İçerik güncellendi ({len(current_content)} karakter)")
        
        else:
            # Max iterasyona ulaşıldı
            self.logger.info(f"\n⚠️ Maksimum iterasyona ulaşıldı ({self.max_reflections})")
            result.final_content = current_content
            result.final_score = critique.score if 'critique' in dir() else 0
            result.iterations = self.max_reflections
            result.status = "max_iterations"
        
        # Maliyet hesapla
        result.total_cost = self.cost_tracker.calculate_cost(
            result.total_tokens, 0
        )
        
        # Sonuç raporu
        self._print_summary(result)
        
        return result
    
    def _format_feedback(self, critique: CritiqueResult) -> str:
        """Eleştiriyi iyileştirme için formatlı geri bildirime dönüştür."""
        lines = [f"Kalite Puanı: {critique.score}/10\n"]
        
        if critique.issues:
            lines.append("Sorunlar:")
            for issue in critique.issues:
                lines.append(f"  - {issue}")
        
        if critique.suggestions:
            lines.append("\nÖneriler:")
            for suggestion in critique.suggestions:
                lines.append(f"  - {suggestion}")
        
        return "\n".join(lines)
    
    def _print_summary(self, result: ReflectionResult):
        """Döngü özet raporu yazdır."""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"📊 Reflection Özet Raporu")
        self.logger.info(f"{'='*50}")
        self.logger.info(f"Görev:       {result.task}")
        self.logger.info(f"Durum:       {result.status}")
        self.logger.info(f"Son Puan:    {result.final_score}/10")
        self.logger.info(f"İterasyon:   {result.iterations}")
        self.logger.info(f"Token:       {result.total_tokens:,}")
        self.logger.info(f"Tahmini Maliyet: ${result.total_cost:.6f}")
        
        if result.history:
            self.logger.info(f"\nPuan Geçmişi:")
            for h in result.history:
                self.logger.info(f"  İterasyon {h['iteration']}: {h['score']}/10")
        
        self.logger.info(f"{'='*50}")
