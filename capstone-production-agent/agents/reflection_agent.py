"""
Reflection Agent - Kalite Eleştirmeni Agent
=============================================
Makale taslağını eleştirel olarak değerlendiren ve iyileştirme önerileri sunan agent.

NEDEN BU AGENT VAR?
--------------------
LLM'ler çoğu zaman ilk denemede mükemmel çıktı üretmez. Reflection (yansıma)
kalıbı, bir agent'ın kendi çıktısını eleştirel olarak değerlendirmesini sağlar.

Bu agent, WritingAgent'ın ürettiği makaleyi 5 boyutta değerlendirir:

1. **Tutarlılık (Coherence)**: Makale mantıksal olarak tutarlı mı?
   - Paragraflar arası geçişler akıcı mı?
   - Argümanlar birbiriyle çelişiyor mu?
   - Konu bütünlüğü korunuyor mu?

2. **Derinlik (Depth)**: Konu yeterince derin ele alınmış mı?
   - Yüzeysel mi yoksa derinlemesine mi?
   - Somut örnekler var mı?
   - Teknik detaylar yeterli mi?

3. **Özgünlük (Originality)**: İçerik özgün mü?
   - Farklı bir bakış açısı sunuyor mu?
   - Klişe ifadelerden kaçınılmış mı?
   - Okuyucuya yeni bir şey öğretiyor mu?

4. **Yapı (Structure)**: Makale iyi yapılandırılmış mı?
   - Başlık, giriş, gövde, sonuç var mı?
   - Alt başlıklar mantıklı mı?
   - Kelime sayısı yeterli mi?

5. **Kaynakça (Citations)**: Kaynaklar doğru kullanılmış mı?
   - Araştırma kaynaklarına atıf yapılmış mı?
   - Kaynakça listesi var mı?
   - İddialar desteklenmiş mi?

Puanlama:
    Her boyut 1-10 arası puan alır.
    Genel puan = 5 boyutun ortalaması.
    Eşik değer (varsayılan 7.0) üzerindeyse "kabul" edilir.

Kullanım:
    from agents.reflection_agent import ReflectionAgent

    agent = ReflectionAgent()
    result = await agent.reflect(draft, research_output, threshold=7.0)

    if result.is_acceptable:
        print("Makale yayınlanabilir!")
    else:
        print(f"İyileştirme gerekli: {result.suggestions}")
"""

import os
import sys
import json
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger, AgentTracer
from shared.schemas.message import build_messages
from shared.utils.helpers import parse_json_safely, truncate_text


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class ReflectionResult:
    """
    Reflection (değerlendirme) sonucunu temsil eder.

    Bu sınıf, ReflectionAgent'ın çıktısıdır.
    Orchestrator bu sonuca göre:
    - is_acceptable=True → Pipeline devam eder (repurpose adımına)
    - is_acceptable=False → WritingAgent'a geri bildirim gönderilir

    Alanlar:
        overall_score: Genel puan (1-10, 5 boyutun ortalaması)
        dimension_scores: Her boyutun ayrı puanı
        issues: Tespit edilen sorunların listesi
        suggestions: İyileştirme önerilerinin listesi
        is_acceptable: Eşik değerin üzerinde mi?
        token_count: Bu değerlendirmede kullanılan token sayısı
    """
    overall_score: float = 0.0                              # Genel puan (1-10)
    dimension_scores: dict[str, float] = field(default_factory=dict)  # Boyut puanları
    issues: list[str] = field(default_factory=list)         # Tespit edilen sorunlar
    suggestions: list[str] = field(default_factory=list)    # İyileştirme önerileri
    is_acceptable: bool = False                             # Eşik üzerinde mi?
    token_count: int = 0                                    # Kullanılan token


# ============================================================
# Değerlendirme Boyutları (Türkçe)
# ============================================================

DIMENSIONS = {
    "tutarlilik": {
        "name": "Tutarlılık (Coherence)",
        "description": "Makale mantıksal olarak tutarlı mı? Paragraflar arası geçişler akıcı mı?",
    },
    "derinlik": {
        "name": "Derinlik (Depth)",
        "description": "Konu yeterince derin ele alınmış mı? Somut örnekler ve teknik detaylar var mı?",
    },
    "ozgunluk": {
        "name": "Özgünlük (Originality)",
        "description": "İçerik özgün mü? Farklı bir bakış açısı sunuyor mu?",
    },
    "yapi": {
        "name": "Yapı (Structure)",
        "description": "Makale iyi yapılandırılmış mı? Başlık, giriş, gövde, sonuç düzeni var mı?",
    },
    "kaynakca": {
        "name": "Kaynakça (Citations)",
        "description": "Araştırma kaynaklarına atıf yapılmış mı? İddialar desteklenmiş mi?",
    },
}


# ============================================================
# Sistem Prompt'u
# ============================================================

REFLECTION_SYSTEM_PROMPT = """Sen titiz ve deneyimli bir makale editörüsün.
Görevin: Verilen makale taslağını eleştirel olarak değerlendirmek.

Değerlendirme Boyutları (her biri 1-10 puan):
1. tutarlilik: Mantıksal tutarlılık, paragraf geçişleri, argüman bütünlüğü
2. derinlik: Konunun derinliği, somut örnekler, teknik detay
3. ozgunluk: İçeriğin özgünlüğü, farklı bakış açısı, klişelerden kaçınma
4. yapi: Makale yapısı (başlık, giriş, gövde, sonuç), alt başlıklar, kelime sayısı
5. kaynakca: Kaynak kullanımı, atıf yapılması, kaynakça listesi

Cevabını KESİNLİKLE aşağıdaki JSON formatında ver:
{
    "dimension_scores": {
        "tutarlilik": 7,
        "derinlik": 6,
        "ozgunluk": 5,
        "yapi": 8,
        "kaynakca": 4
    },
    "issues": [
        "Sorun 1: ...",
        "Sorun 2: ..."
    ],
    "suggestions": [
        "Öneri 1: ...",
        "Öneri 2: ..."
    ]
}

Kurallar:
1. Puanlar 1-10 arası TAM SAYI olmalı
2. En az 2 sorun ve 2 öneri belirt
3. Sorunlar SOMUT olmalı (hangi bölümde, ne eksik?)
4. Öneriler UYGULANABILIR olmalı (ne yapılmalı?)
5. Cevabını SADECE JSON formatında ver, başka metin ekleme
6. Türkçe yaz
"""


# ============================================================
# ReflectionAgent Sınıfı
# ============================================================

class ReflectionAgent:
    """
    Kalite Eleştirmeni Agent.

    Bu agent, WritingAgent'ın ürettiği makaleyi 5 boyutta değerlendirir
    ve iyileştirme önerileri sunar. Pipeline'daki kalite kontrol mekanizmasıdır.

    Neden ayrı bir agent?
    - "Bir kişi hem yazar hem editör olamaz" prensibi
    - Ayrı agent, farklı system prompt ve farklı perspektif demek
    - LLM'in kendi çıktısını eleştirmesi yerine, bağımsız değerlendirme

    Parametreler:
        model: Değerlendirme modeli (varsayılan: gpt-4o-mini)
               Analitik değerlendirme için güçlü model şart değil.
        temperature: Düşük tutulur (0.2) çünkü tutarlı ve tekrarlanabilir
                    değerlendirmeler istiyoruz.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ):
        """
        ReflectionAgent'ı başlat.

        Parametreler:
            model: Değerlendirme modeli. gpt-4o-mini yeterlidir çünkü
                   analitik değerlendirme, yaratıcı yazım kadar güçlü
                   model gerektirmez.
            temperature: Çok düşük tutulur (0.2) çünkü:
                        - Her seferinde tutarlı puanlama istiyoruz
                        - Subjektif değerlendirmeler minimize edilmeli
                        - Tekrarlanabilir sonuçlar önemli
        """
        self._client = LLMClient(model=model, temperature=temperature)
        self._logger = get_logger("reflection_agent")
        self._tracer = AgentTracer("reflection_agent")

    async def reflect(
        self,
        draft: any,
        research_output: any,
        threshold: float = 7.0,
    ) -> ReflectionResult:
        """
        Makale taslağını değerlendir.

        Bu metod, verilen taslağı orijinal araştırmayla karşılaştırarak
        5 boyutta puanlar ve iyileştirme önerileri sunar.

        Parametreler:
            draft: WritingAgent'ın ürettiği ArticleDraft.
                   .content ve .title alanlarını kullanır.
            research_output: ResearchAgent'ın çıktısı.
                            Makalenin araştırma ile uyumunu kontrol etmek için.
            threshold: Kabul eşiği (varsayılan: 7.0).
                      Genel puan bu değerin altındaysa makale reddedilir.

        Döndürür:
            ReflectionResult: Değerlendirme sonucu

        Örnek:
            result = await agent.reflect(draft_v1, research_output, threshold=7.0)

            if result.is_acceptable:
                print("Makale kabul edildi!")
            else:
                print(f"Puan: {result.overall_score}/10")
                for issue in result.issues:
                    print(f"  Sorun: {issue}")
                for suggestion in result.suggestions:
                    print(f"  Öneri: {suggestion}")
        """
        self._tracer.start_task(
            f"Değerlendirme: v{getattr(draft, 'version', '?')} | Eşik: {threshold}"
        )
        self._logger.info(
            f"Makale değerlendirmesi başlatılıyor | "
            f"Versiyon: v{getattr(draft, 'version', '?')} | Eşik: {threshold}"
        )

        # ────────────────────────────────────
        # Prompt hazırlama
        # ────────────────────────────────────
        user_message = self._build_reflection_prompt(draft, research_output)

        self._tracer.log_think("Makaleyi 5 boyutta değerlendireceğim")

        # ────────────────────────────────────
        # LLM çağrısı
        # ────────────────────────────────────
        messages = build_messages(
            system_prompt=REFLECTION_SYSTEM_PROMPT,
            user_message=user_message,
        )

        response = await self._client.chat_with_messages(messages)
        content = response.content or ""

        # ────────────────────────────────────
        # Cevabı parse et
        # ────────────────────────────────────
        if response.model == "demo-mode":
            self._logger.info("Demo mod algılandı, mock değerlendirme üretiliyor")
            result = self._mock_reflection(draft, threshold)
        else:
            result = self._parse_reflection_response(
                content, threshold, response.usage.total_tokens
            )

        self._tracer.log_response(
            f"Değerlendirme tamamlandı | "
            f"Puan: {result.overall_score:.1f}/10 | "
            f"Kabul: {'Evet' if result.is_acceptable else 'Hayır'} | "
            f"Sorun: {len(result.issues)} | Öneri: {len(result.suggestions)}"
        )
        self._tracer.end_task(success=True)

        self._logger.info(
            f"Değerlendirme sonucu | Puan: {result.overall_score:.1f}/10 | "
            f"Kabul: {'✅' if result.is_acceptable else '❌'}"
        )

        # Boyut puanlarını logla
        for dim_key, score in result.dimension_scores.items():
            dim_name = DIMENSIONS.get(dim_key, {}).get("name", dim_key)
            self._logger.info(f"  {dim_name}: {score}/10")

        return result

    # ────────────────────────────────────────────────────────
    # Yardımcı Metodlar
    # ────────────────────────────────────────────────────────

    def _build_reflection_prompt(self, draft: any, research_output: any) -> str:
        """
        Değerlendirme prompt'u oluştur.

        Makale taslağını ve orijinal araştırmayı birleştirerek
        karşılaştırmalı değerlendirme yapılmasını sağlar.
        """
        draft_content = getattr(draft, "content", str(draft))
        draft_title = getattr(draft, "title", "Başlıksız")
        draft_word_count = getattr(draft, "word_count", len(str(draft).split()))

        research_summary = getattr(research_output, "summary", str(research_output))
        research_citations = getattr(research_output, "citations", [])

        parts = [
            "DEĞERLENDİRİLECEK MAKALE:",
            f"Başlık: {draft_title}",
            f"Kelime Sayısı: {draft_word_count}",
            "─" * 40,
            truncate_text(draft_content, max_length=3000),
            "─" * 40,
            "",
            "ORİJİNAL ARAŞTIRMA ÖZETİ:",
            truncate_text(research_summary, max_length=1000),
            "",
        ]

        if research_citations:
            parts.append(f"Araştırmada {len(research_citations)} kaynak var. "
                        "Makalede bu kaynaklara atıf yapılmış mı kontrol et.")

        parts.append(
            "\nBu makaleyi 5 boyutta (tutarlilik, derinlik, ozgunluk, yapi, kaynakca) "
            "değerlendir ve JSON formatında cevap ver."
        )

        return "\n".join(parts)

    def _parse_reflection_response(
        self,
        content: str,
        threshold: float,
        token_count: int,
    ) -> ReflectionResult:
        """
        LLM cevabını ReflectionResult'a dönüştür.

        JSON parse başarısız olursa varsayılan düşük puanlar döndürür
        (güvenli tarafta kalmak için - makale yeniden değerlendirilir).
        """
        parsed = parse_json_safely(content)

        if parsed:
            dimension_scores = parsed.get("dimension_scores", {})

            # Puanları 1-10 arasında sınırla
            for key in dimension_scores:
                score = dimension_scores[key]
                if isinstance(score, (int, float)):
                    dimension_scores[key] = max(1, min(10, float(score)))
                else:
                    dimension_scores[key] = 5.0  # Geçersiz değer için varsayılan

            # Eksik boyutları varsayılan puanla doldur
            for dim_key in DIMENSIONS:
                if dim_key not in dimension_scores:
                    dimension_scores[dim_key] = 5.0

            # Genel puanı hesapla (ortalama)
            if dimension_scores:
                overall = sum(dimension_scores.values()) / len(dimension_scores)
            else:
                overall = 5.0

            return ReflectionResult(
                overall_score=round(overall, 1),
                dimension_scores=dimension_scores,
                issues=parsed.get("issues", ["Sorun bilgisi alınamadı"]),
                suggestions=parsed.get("suggestions", ["Öneri bilgisi alınamadı"]),
                is_acceptable=overall >= threshold,
                token_count=token_count,
            )
        else:
            # JSON parse başarısız - güvenli tarafta kal
            self._logger.warning(
                "Reflection cevabı JSON olarak parse edilemedi, düşük puan atanıyor"
            )
            return ReflectionResult(
                overall_score=4.0,
                dimension_scores={dim: 4.0 for dim in DIMENSIONS},
                issues=["Değerlendirme cevabı parse edilemedi", content[:200]],
                suggestions=["Değerlendirme tekrar yapılmalı"],
                is_acceptable=False,
                token_count=token_count,
            )

    def _mock_reflection(self, draft: any, threshold: float) -> ReflectionResult:
        """
        Demo mod için mock değerlendirme üret.

        İlk taslak (v1) düşük puan, sonraki taslaklar yüksek puan alır.
        Bu sayede pipeline'ın reflection döngüsü test edilebilir.
        """
        version = getattr(draft, "version", 1)

        if version <= 1:
            # İlk taslak: Düşük puan (iyileştirme gerekli)
            scores = {
                "tutarlilik": 6.0,
                "derinlik": 5.0,
                "ozgunluk": 5.0,
                "yapi": 7.0,
                "kaynakca": 4.0,
            }
            issues = [
                "Giriş bölümü okuyucuyu yeterince çekemiyor, daha güçlü bir kanca (hook) gerekli",
                "Derinlik eksik: Bazı kavramlar sadece yüzeysel olarak ele alınmış",
                "Kaynakça kullanımı zayıf: Araştırma kaynaklarının çoğuna atıf yapılmamış",
                "Özgünlük düşük: Konuya farklı bir bakış açısı getirilmemiş",
            ]
            suggestions = [
                "Girişe dikkat çekici bir istatistik veya soru ile başla",
                "Her bölüme en az bir somut örnek veya kod parçası ekle",
                "Araştırmada bulunan 5 kaynağın en az 3'üne makale içinde atıf yap",
                "Sonuç bölümünde okuyucuya somut bir eylem planı sun",
            ]
        else:
            # İyileştirilmiş taslak: Yüksek puan
            scores = {
                "tutarlilik": 8.0,
                "derinlik": 8.0,
                "ozgunluk": 7.0,
                "yapi": 9.0,
                "kaynakca": 7.0,
            }
            issues = [
                "Bazı teknik terimlerin Türkçe açıklaması eksik",
                "Sonuç bölümü biraz daha genişletilebilir",
            ]
            suggestions = [
                "Teknik terimleri ilk kullanıldığında parantez içinde açıkla",
                "Sonuç bölümüne gelecek trendler hakkında 1-2 cümle ekle",
            ]

        overall = sum(scores.values()) / len(scores)

        return ReflectionResult(
            overall_score=round(overall, 1),
            dimension_scores=scores,
            issues=issues,
            suggestions=suggestions,
            is_acceptable=overall >= threshold,
            token_count=80,  # Demo mod token tahmini
        )

    def format_feedback(self, result: ReflectionResult) -> str:
        """
        ReflectionResult'ı WritingAgent'a gönderilecek geri bildirim metnine çevir.

        Bu metod, Orchestrator tarafından çağrılır ve
        sonucu insan tarafından okunabilir formata dönüştürür.

        Parametreler:
            result: Değerlendirme sonucu

        Döndürür:
            str: Formatlanmış geri bildirim metni
        """
        lines = [
            f"Genel Puan: {result.overall_score:.1f}/10",
            "",
            "Boyut Puanları:",
        ]

        for dim_key, score in result.dimension_scores.items():
            dim_name = DIMENSIONS.get(dim_key, {}).get("name", dim_key)
            bar = "█" * int(score) + "░" * (10 - int(score))
            lines.append(f"  {dim_name}: {bar} {score:.0f}/10")

        if result.issues:
            lines.append("")
            lines.append("Tespit Edilen Sorunlar:")
            for issue in result.issues:
                lines.append(f"  ❌ {issue}")

        if result.suggestions:
            lines.append("")
            lines.append("İyileştirme Önerileri:")
            for suggestion in result.suggestions:
                lines.append(f"  💡 {suggestion}")

        return "\n".join(lines)


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_reflection():
        """
        ReflectionAgent'ı bağımsız test et.

        Bu test:
        1. Mock draft oluşturur
        2. Değerlendirme yapar
        3. Sonuçları ve geri bildirim formatını gösterir
        """
        print("=" * 50)
        print("🧪 ReflectionAgent Test")
        print("=" * 50)

        # Basit mock nesneler
        class MockDraft:
            title = "Test Makale"
            content = "Bu bir test makalesidir. " * 100
            word_count = 600
            version = 1

        class MockResearch:
            summary = "Araştırma özeti burada."
            citations = [{"source": "test.com", "title": "Test", "key_point": "Nokta"}]
            topic = "Test Konu"

        agent = ReflectionAgent()

        # Test 1: İlk taslak değerlendirmesi (düşük puan beklenir)
        print("\n--- Test 1: İlk Taslak (v1) ---")
        result = await agent.reflect(MockDraft(), MockResearch(), threshold=7.0)
        print(f"Puan: {result.overall_score}/10")
        print(f"Kabul: {'✅' if result.is_acceptable else '❌'}")
        print(f"\nGeri Bildirim:")
        print(agent.format_feedback(result))

        # Test 2: İyileştirilmiş taslak (yüksek puan beklenir)
        print("\n--- Test 2: İyileştirilmiş Taslak (v2) ---")
        mock_v2 = MockDraft()
        mock_v2.version = 2
        result_v2 = await agent.reflect(mock_v2, MockResearch(), threshold=7.0)
        print(f"Puan: {result_v2.overall_score}/10")
        print(f"Kabul: {'✅' if result_v2.is_acceptable else '❌'}")

    asyncio.run(test_reflection())
