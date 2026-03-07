"""
Repurpose Agent - İçerik Dönüştürme Agent'ı
==============================================
Uzun formatlı makaleyi farklı platformlara uygun formatlara dönüştüren agent.

NEDEN BU AGENT VAR?
--------------------
Tek bir araştırma ve makale sürecinden birden fazla içerik çıkarmak,
içerik üretiminin en verimli stratejisidir. "Bir yaz, birden fazla yayınla"
prensibi ile:

- Medium makalesi → LinkedIn postu
- (gelecekte: Twitter thread, newsletter, podcast scripti vb.)

LinkedIn Post Anatomisi:
    Etkili bir LinkedIn postu 3 temel bileşenden oluşur:

    1. **Hook (Kanca)**: İlk 1-2 satır.
       LinkedIn'de "...daha fazla" butonundan önce görünen kısım.
       Dikkat çekici, merak uyandırıcı olmalı.
       Örnek: "Geçen ay 5 farklı AI agent framework'ü denedim. Sonuçlar şaşırtıcıydı."

    2. **Body (Gövde)**: Değer sunan kısım.
       Madde işaretleriyle yapılandırılmış, okunması kolay.
       Her madde somut bir değer veya öğrenme sunmalı.

    3. **CTA (Call to Action)**: Eylem çağrısı.
       Okuyucuyu etkileşime davet eden son bölüm.
       Örnek: "Siz hangi framework'ü tercih ediyorsunuz? Yorumlarda tartışalım."

    Bonus: Hashtag'ler
       Konuyla ilgili 3-5 hashtag, keşfedilebilirliği artırır.

Kullanım:
    from agents.repurpose_agent import RepurposeAgent

    agent = RepurposeAgent()
    post = await agent.repurpose_to_linkedin(article_content, topic)

    print(post.full_text)
    print(f"Kelime sayısı: {post.word_count}")
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# Shared modül import yolu
# ============================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient
from shared.telemetry.logger import get_logger, AgentTracer
from shared.schemas.message import build_messages
from shared.utils.helpers import truncate_text


# ============================================================
# Veri Sınıfları
# ============================================================

@dataclass
class LinkedInPost:
    """
    LinkedIn postu temsil eden veri sınıfı.

    LinkedIn'de etkili bir postun 3 temel bölümü vardır:
    - Hook: Dikkat çekici açılış
    - Body: Değer sunan gövde
    - CTA: Eylem çağrısı

    Alanlar:
        hook: Dikkat çekici ilk cümle(ler)
        body: Postun ana gövdesi (değer maddeleri)
        cta: Eylem çağrısı (Call to Action)
        hashtags: İlgili hashtag listesi
        full_text: Tam post metni (hepsi birleştirilmiş)
        word_count: Kelime sayısı
        token_count: Bu postu üretmek için kullanılan token
    """
    hook: str = ""                                          # Dikkat çekici açılış
    body: str = ""                                          # Ana gövde
    cta: str = ""                                           # Eylem çağrısı
    hashtags: list[str] = field(default_factory=list)       # Hashtag listesi
    full_text: str = ""                                     # Tam post metni
    word_count: int = 0                                     # Kelime sayısı
    token_count: int = 0                                    # Kullanılan token


# ============================================================
# Sistem Prompt'u
# ============================================================

LINKEDIN_SYSTEM_PROMPT = """Sen LinkedIn içerik stratejistisin.
Görevin: Verilen Medium makalesini etkili bir LinkedIn postuna dönüştürmek.

LinkedIn Post Yapısı:
1. **HOOK** (İlk 1-2 satır): Dikkat çekici açılış.
   - Şaşırtıcı bir istatistik, soru veya cesur bir iddia
   - "...daha fazla" butonundan ÖNCE görünecek kısım
   - Merak uyandırmalı

2. **GÖVDE**: Değer sunan bölüm.
   - Madde işaretleriyle (•) yapılandır
   - Her madde somut bir öğrenme veya değer sunmalı
   - Kısa cümleler, net ifadeler
   - 5-7 madde ideal

3. **CTA** (Call to Action): Eylem çağrısı.
   - Okuyucuyu etkileşime davet et
   - Soru sor veya görüş iste
   - Paylaşmaya teşvik et

4. **HASHTAG'LER**: 3-5 ilgili hashtag

Cevabını aşağıdaki JSON formatında ver:
{
    "hook": "Dikkat çekici açılış cümlesi...",
    "body": "• Madde 1\\n• Madde 2\\n• Madde 3...",
    "cta": "Eylem çağrısı cümlesi...",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
}

Kurallar:
- Dil: Türkçe
- Ton: Profesyonel ama samimi
- Toplam 150-300 kelime
- Kısa paragraflar (LinkedIn mobilde okunur!)
- Emoji kullanımı ÖLÇÜLÜ (sadece vurgu için)
- Cevabını SADECE JSON formatında ver
"""


# ============================================================
# RepurposeAgent Sınıfı
# ============================================================

class RepurposeAgent:
    """
    İçerik Dönüştürme Agent'ı.

    Bu agent, WritingAgent'ın ürettiği uzun formatlı makaleyi
    LinkedIn postu formatına dönüştürür.

    Neden ayrı bir agent?
    - Her platform farklı format ve ton gerektirir
    - LinkedIn postu, makale özetlemekten fazlasıdır
    - Kanca (hook) ve CTA gibi platform-spesifik bileşenler gerekir
    - Gelecekte Twitter, newsletter gibi formatlar eklenebilir

    Parametreler:
        model: Dönüştürme modeli (varsayılan: gpt-4o-mini)
               Format dönüştürme basit bir görev, ucuz model yeterli.
        temperature: Yaratıcılık seviyesi (varsayılan: 0.7)
                    Hook için yaratıcılık gerekli ama kontrollü.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ):
        """
        RepurposeAgent'ı başlat.

        Parametreler:
            model: gpt-4o-mini yeterlidir çünkü format dönüştürme
                   derin anlama gerektirmez, mevcut içeriği yeniden
                   yapılandırma yeterli.
            temperature: Orta seviye (0.7). Hook için yaratıcılık lazım
                        ama çok sapma da istemeyiz.
        """
        self._client = LLMClient(model=model, temperature=temperature)
        self._logger = get_logger("repurpose_agent")
        self._tracer = AgentTracer("repurpose_agent")

    async def repurpose_to_linkedin(
        self,
        article_content: str,
        topic: str,
    ) -> LinkedInPost:
        """
        Medium makalesini LinkedIn postuna dönüştür.

        Bu metod, uzun formatlı bir makaleyi alır ve
        LinkedIn'e uygun kısa, etkileyici bir posta çevirir.

        Parametreler:
            article_content: WritingAgent'ın ürettiği makale metni
            topic: Orijinal konu (hashtag üretimi için)

        Döndürür:
            LinkedInPost: Yapılandırılmış LinkedIn postu

        Örnek:
            agent = RepurposeAgent()
            post = await agent.repurpose_to_linkedin(
                article_content="# Agentic AI...makale metni...",
                topic="Agentic AI ve MCP"
            )
            print(post.hook)     # Dikkat çekici açılış
            print(post.body)     # Değer maddeleri
            print(post.cta)      # Eylem çağrısı
            print(post.full_text)  # Tam post
        """
        self._tracer.start_task(f"LinkedIn'e dönüştürme: {topic}")
        self._logger.info(
            f"LinkedIn dönüştürme başlatılıyor | "
            f"Konu: {topic} | Makale uzunluğu: {len(article_content)} karakter"
        )

        # ────────────────────────────────────
        # Prompt hazırlama
        # ────────────────────────────────────
        user_message = (
            f"Konu: {topic}\n\n"
            f"Aşağıdaki Medium makalesini LinkedIn postuna dönüştür:\n\n"
            f"{'─' * 40}\n"
            f"{truncate_text(article_content, max_length=3000)}\n"
            f"{'─' * 40}"
        )

        self._tracer.log_think("Makaleyi LinkedIn formatına dönüştüreceğim")

        # ────────────────────────────────────
        # LLM çağrısı
        # ────────────────────────────────────
        messages = build_messages(
            system_prompt=LINKEDIN_SYSTEM_PROMPT,
            user_message=user_message,
        )

        response = await self._client.chat_with_messages(messages)
        content = response.content or ""

        # ────────────────────────────────────
        # Cevabı parse et
        # ────────────────────────────────────
        if response.model == "demo-mode":
            self._logger.info("Demo mod algılandı, mock LinkedIn postu üretiliyor")
            post = self._mock_linkedin_post(topic)
        else:
            post = self._parse_linkedin_response(content, topic, response.usage.total_tokens)

        self._tracer.log_response(
            f"LinkedIn postu oluşturuldu | "
            f"Kelime: {post.word_count} | Token: {post.token_count}"
        )
        self._tracer.end_task(success=True)

        self._logger.info(
            f"LinkedIn postu hazır | {post.word_count} kelime | {post.token_count} token"
        )

        return post

    # ────────────────────────────────────────────────────────
    # Yardımcı Metodlar
    # ────────────────────────────────────────────────────────

    def _parse_linkedin_response(
        self,
        content: str,
        topic: str,
        token_count: int,
    ) -> LinkedInPost:
        """
        LLM cevabını LinkedInPost'a dönüştür.

        JSON parse başarısız olursa ham metni gövde olarak kullanır
        ve varsayılan hook/CTA ekler.
        """
        from shared.utils.helpers import parse_json_safely

        parsed = parse_json_safely(content)

        if parsed:
            hook = parsed.get("hook", "")
            body = parsed.get("body", "")
            cta = parsed.get("cta", "")
            hashtags = parsed.get("hashtags", [])

            # Hashtag'lerin # ile başlamasını garanti et
            hashtags = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in hashtags
            ]

            # Tam metni birleştir
            full_text = self._compose_full_text(hook, body, cta, hashtags)
            word_count = len(full_text.split())

            return LinkedInPost(
                hook=hook,
                body=body,
                cta=cta,
                hashtags=hashtags,
                full_text=full_text,
                word_count=word_count,
                token_count=token_count,
            )
        else:
            # JSON parse başarısız, ham metni kullan
            self._logger.warning(
                "LinkedIn cevabı JSON olarak parse edilemedi, ham metin kullanılıyor"
            )
            return LinkedInPost(
                hook="",
                body=content,
                cta="",
                hashtags=[f"#{topic.replace(' ', '')}"],
                full_text=content,
                word_count=len(content.split()),
                token_count=token_count,
            )

    def _compose_full_text(
        self,
        hook: str,
        body: str,
        cta: str,
        hashtags: list[str],
    ) -> str:
        """
        Post bileşenlerini tam metne birleştir.

        LinkedIn formatına uygun boşluk ve satır araları ekler.
        """
        parts = []

        if hook:
            parts.append(hook)
            parts.append("")  # Boş satır

        if body:
            parts.append(body)
            parts.append("")

        if cta:
            parts.append(cta)
            parts.append("")

        if hashtags:
            parts.append(" ".join(hashtags))

        return "\n".join(parts)

    def _mock_linkedin_post(self, topic: str) -> LinkedInPost:
        """
        Demo mod için mock LinkedIn postu üret.

        Gerçekçi bir LinkedIn postu yapısı sunar.
        """
        self._logger.info(f"Mock LinkedIn postu üretiliyor | Konu: {topic}")

        hook = (
            f"Son 3 ayda {topic} konusunda yoğun bir araştırma yaptım.\n"
            f"Öğrendiklerim beklentilerimin çok ötesindeydi."
        )

        body = (
            f"İşte {topic} hakkında öğrendiğim 5 kritik nokta:\n\n"
            f"• Agent sistemleri artık prototip aşamasını geçti, production'a hazır\n"
            f"• MCP protokolü, agent-tool iletişiminde standart haline geliyor\n"
            f"• Maliyet kontrolü olmadan agent sistemi çalıştırmak çok riskli\n"
            f"• Reflection (yansıma) kalıbı, çıktı kalitesini %40'a kadar artırıyor\n"
            f"• Çoklu agent sistemleri, tek agent'a göre çok daha güçlü sonuçlar veriyor\n\n"
            f"En çok şaşırtan bulgu: Akıllı model yönlendirme ile "
            f"aynı kalitede %70 maliyet tasarrufu mümkün."
        )

        cta = (
            f"Siz {topic} konusunda ne düşünüyorsunuz?\n"
            f"Kendi projelerinizde deneyimleriniz neler?\n"
            f"Yorumlarda tartışalım! 👇"
        )

        hashtags = [
            "#AgenticAI",
            "#YapayZeka",
            "#MCP",
            "#AIEngineering",
            "#TechTrends",
        ]

        full_text = self._compose_full_text(hook, body, cta, hashtags)

        return LinkedInPost(
            hook=hook,
            body=body,
            cta=cta,
            hashtags=hashtags,
            full_text=full_text,
            word_count=len(full_text.split()),
            token_count=60,  # Demo mod token tahmini
        )


# ============================================================
# Test Bloğu
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_repurpose():
        """
        RepurposeAgent'ı bağımsız test et.

        Bu test:
        1. Mock makale metni hazırlar
        2. LinkedIn postuna dönüştürür
        3. Postun bileşenlerini gösterir
        """
        print("=" * 50)
        print("🧪 RepurposeAgent Test")
        print("=" * 50)

        mock_article = """
# Agentic AI: Yapay Zekanın Yeni Sınırları

## Giriş
Yapay zeka, basit chatbot'lardan otonom agent'lara evrilmekte.
Bu makalede agentic AI'ın temellerini inceliyoruz.

## Agent Döngüsü
Her agent, Düşün → Plan → Çalıştır → Gözlemle döngüsünü takip eder.

## MCP Protokolü
Model Context Protocol, agent-tool iletişimini standardize eder.

## Sonuç
Agentic AI, yazılım geliştirmenin geleceğini şekillendirecek.
"""

        agent = RepurposeAgent()
        post = await agent.repurpose_to_linkedin(mock_article, "Agentic AI ve MCP")

        print(f"\n🎣 Hook:")
        print(f"  {post.hook}")
        print(f"\n📝 Body:")
        print(f"  {post.body}")
        print(f"\n📣 CTA:")
        print(f"  {post.cta}")
        print(f"\n#️⃣  Hashtag'ler: {' '.join(post.hashtags)}")
        print(f"\n📊 İstatistikler:")
        print(f"  Kelime: {post.word_count}")
        print(f"  Token: {post.token_count}")
        print(f"\n{'─' * 40}")
        print("TAM POST:")
        print(f"{'─' * 40}")
        print(post.full_text)

    asyncio.run(test_repurpose())
