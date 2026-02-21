"""
Bağlam Sıkıştırıcı (Context Compressor)
==========================================
Konuşma geçmişini özetleyerek/kırparak token tasarrufu yapar.

Problem: Bağlam Penceresi Dolması
----------------------------------
Her LLM çağrısında tüm konuşma geçmişini gönderirsiniz.
Konuşma uzadıkça:
  - Token sayısı artar → Maliyet artar
  - Bağlam penceresi (context window) dolar → Hata alırsınız
  - İlk mesajlar "unutulur" (pencereden çıkar)

Çözüm: Context Compression
  - Eski mesajları özetle
  - Gereksiz detayları kırp
  - Sistem mesajını ve son mesajları koru

Sıkıştırma Stratejileri:
  1. Kırpma (Truncation): En eski mesajları sil
  2. Özetleme (Summarization): Eski mesajları tek bir özete dönüştür
  3. Seçici Sıkıştırma: Önemli mesajları koru, önemsizleri kaldır

Bu dosyada 1 ve 2 numaralı stratejiler uygulanmıştır.
3 numaralı strateji alıştırma olarak bırakılmıştır.

Kullanım:
    from optimization.context_compress import ContextCompressor

    compressor = ContextCompressor(max_tokens=2000)

    # Mesajları sıkıştır
    compressed = compressor.compress_messages(messages)
    print(f"Önce: {len(messages)} mesaj, Sonra: {len(compressed)} mesaj")
"""

import sys
import os
from typing import Optional

# shared/ modülünü import edebilmek için path ayarı
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger

logger = get_logger("optimization.context_compress")


class ContextCompressor:
    """
    Konuşma geçmişini sıkıştırarak token tasarrufu yapar.

    Nasıl çalışır?
    ─────────────
    1. Mesaj listesinin tahmini token sayısını hesaplar
    2. max_tokens'ı aşıyorsa sıkıştırma uygular
    3. Sıkıştırma stratejisine göre mesajları kırpar veya özetler

    Korunan mesajlar (asla silinmez):
    - Sistem mesajı (system) → Agent'ın talimatları
    - Son N mesaj (preserve_last) → Aktif konuşma bağlamı

    Sıkıştırma sırası:
    ┌─────────────────────────────────────────────┐
    │ system mesajı     → HER ZAMAN KORUNUR       │
    │ eski mesajlar     → ÖZETLENIR / KESİLİR     │
    │ son N mesaj       → HER ZAMAN KORUNUR       │
    └─────────────────────────────────────────────┘

    Kullanım:
        compressor = ContextCompressor(max_tokens=2000)

        messages = [
            {"role": "system", "content": "Sen bir asistansın."},
            {"role": "user", "content": "Python nedir?"},
            {"role": "assistant", "content": "Python yüksek seviyeli..."},
            {"role": "user", "content": "Değişken nasıl tanımlanır?"},
            {"role": "assistant", "content": "Python'da x = 5 şeklinde..."},
            {"role": "user", "content": "Şimdi bir sınıf yaz"},
        ]

        compressed = compressor.compress_messages(messages)
        # → system + özet + son mesaj = daha az token
    """

    # Token tahmini için ortalama karakter/token oranı
    # Türkçe metinler için yaklaşık değer (İngilizce'den biraz farklı)
    CHARS_PER_TOKEN = 3.5

    def __init__(
        self,
        max_tokens: int = 4000,
        preserve_last: int = 4,
        summary_prefix: str = "[Önceki konuşma özeti]",
    ):
        """
        ContextCompressor oluştur.

        Parametreler:
            max_tokens: Maksimum token limiti.
                        Bu limiti aşan mesajlar sıkıştırılır.
            preserve_last: Korunacak son mesaj sayısı.
                           Bu mesajlar asla silinmez/özetlenmez.
            summary_prefix: Özet mesajının başına eklenecek etiket.
        """
        self.max_tokens = max_tokens
        self.preserve_last = preserve_last
        self.summary_prefix = summary_prefix
        self.logger = get_logger("context_compressor")

    def estimate_tokens(self, text: str) -> int:
        """
        Bir metnin yaklaşık token sayısını hesapla.

        Bu basit bir tahmin yöntemidir. Gerçek projede
        tiktoken kütüphanesini kullanmanız önerilir:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4o-mini")
            tokens = len(enc.encode(text))

        Parametreler:
            text: Token sayısı hesaplanacak metin

        Döndürür:
            int: Tahmini token sayısı
        """
        if not text:
            return 0
        return int(len(text) / self.CHARS_PER_TOKEN)

    def estimate_messages_tokens(self, messages: list[dict]) -> int:
        """
        Mesaj listesinin toplam tahmini token sayısını hesapla.

        Her mesaj için:
        - content'in token sayısı
        - role ve metadata için +4 token (OpenAI overhead)

        Parametreler:
            messages: Mesaj listesi [{"role": "...", "content": "..."}]

        Döndürür:
            int: Toplam tahmini token sayısı
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.estimate_tokens(content) + 4  # +4 role/metadata overhead
        return total

    def _extract_system_message(self, messages: list[dict]) -> Optional[dict]:
        """
        Sistem mesajını bul ve döndür.

        Sistem mesajı genellikle ilk mesajdır ve
        agent'ın talimatlarını içerir.

        Parametreler:
            messages: Mesaj listesi

        Döndürür:
            dict | None: Sistem mesajı veya None
        """
        for msg in messages:
            if msg.get("role") == "system":
                return msg
        return None

    def _create_summary(self, messages: list[dict]) -> str:
        """
        Mesaj listesinin basit bir özetini oluştur.

        Bu basit bir kural tabanlı özetleyicidir.
        Gerçek projede LLM ile özet üretebilirsiniz:
            summary = await llm.chat(
                f"Şu konuşmayı 2-3 cümleyle özetle: {messages}"
            )

        Parametreler:
            messages: Özetlenecek mesajlar

        Döndürür:
            str: Özet metni
        """
        if not messages:
            return ""

        # Her mesajdan ilk cümleyi al
        # Bu basit bir stratejidir — LLM özetlemesi daha iyi sonuç verir
        summary_parts = []

        # Konuşulan konuları topla
        topics = set()
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if role == "user":
                # Kullanıcı ne sordu?
                first_sentence = content.split(".")[0].split("?")[0].strip()
                if first_sentence and len(first_sentence) > 5:
                    topics.add(first_sentence[:80])
            elif role == "assistant":
                # Assistant ne cevap verdi? (kısa versiyon)
                first_sentence = content.split(".")[0].strip()
                if first_sentence and len(first_sentence) > 10:
                    summary_parts.append(first_sentence[:100])

        # Özet oluştur
        summary = f"{self.summary_prefix}\n"

        if topics:
            summary += "Konuşulan konular: " + "; ".join(list(topics)[:5]) + ".\n"

        if summary_parts:
            summary += "Önceki cevaplardan özetler: " + ". ".join(summary_parts[:3]) + "."

        return summary.strip()

    def compress_messages(
        self,
        messages: list[dict],
        strategy: str = "summarize",
    ) -> list[dict]:
        """
        Mesaj listesini sıkıştır.

        Sıkıştırma adımları:
        1. Mevcut token sayısını hesapla
        2. Limit aşılmıyorsa mesajları olduğu gibi döndür
        3. Limit aşılıyorsa seçilen stratejiye göre sıkıştır

        Parametreler:
            messages: Sıkıştırılacak mesaj listesi
            strategy: Sıkıştırma stratejisi
                      "truncate" → Eski mesajları sil
                      "summarize" → Eski mesajları özetle (varsayılan)

        Döndürür:
            list[dict]: Sıkıştırılmış mesaj listesi
        """
        current_tokens = self.estimate_messages_tokens(messages)

        # Limit aşılmıyorsa sıkıştırmaya gerek yok
        if current_tokens <= self.max_tokens:
            self.logger.info(
                f"Sıkıştırma gerekmiyor: {current_tokens} token ≤ {self.max_tokens} limit"
            )
            return messages

        self.logger.info(
            f"Sıkıştırma başlatılıyor: {current_tokens} token > {self.max_tokens} limit "
            f"(strateji: {strategy})"
        )

        # Sistem mesajını ayır (korunacak)
        system_msg = self._extract_system_message(messages)
        non_system = [m for m in messages if m.get("role") != "system"]

        # Son N mesajı koru (aktif konuşma)
        preserved = non_system[-self.preserve_last:] if len(non_system) > self.preserve_last else non_system
        to_compress = non_system[:-self.preserve_last] if len(non_system) > self.preserve_last else []

        if strategy == "truncate":
            # Strateji 1: Basitçe eski mesajları sil
            compressed = self._truncate(system_msg, preserved)
        else:
            # Strateji 2: Eski mesajları özetle
            compressed = self._summarize(system_msg, to_compress, preserved)

        new_tokens = self.estimate_messages_tokens(compressed)
        saved = current_tokens - new_tokens
        self.logger.info(
            f"Sıkıştırma tamamlandı: {current_tokens} → {new_tokens} token "
            f"(tasarruf: {saved} token, %{saved/current_tokens*100:.0f})"
        )

        return compressed

    def _truncate(
        self,
        system_msg: Optional[dict],
        preserved: list[dict],
    ) -> list[dict]:
        """
        Kırpma stratejisi: Eski mesajları tamamen sil.

        En basit strateji. Hızlı ama bilgi kaybı yaşanır.

        Parametreler:
            system_msg: Sistem mesajı (korunacak)
            preserved: Korunacak son mesajlar

        Döndürür:
            list[dict]: Kırpılmış mesaj listesi
        """
        result = []

        if system_msg:
            result.append(system_msg)

        # Kırpma notu ekle
        result.append({
            "role": "system",
            "content": f"{self.summary_prefix} Önceki mesajlar uzunluk nedeniyle kırpıldı.",
        })

        result.extend(preserved)
        return result

    def _summarize(
        self,
        system_msg: Optional[dict],
        to_compress: list[dict],
        preserved: list[dict],
    ) -> list[dict]:
        """
        Özetleme stratejisi: Eski mesajları tek bir özete dönüştür.

        Kırpmadan daha iyi: Bilgi tamamen kaybolmaz,
        önemli noktalar korunur.

        Parametreler:
            system_msg: Sistem mesajı (korunacak)
            to_compress: Özetlenecek eski mesajlar
            preserved: Korunacak son mesajlar

        Döndürür:
            list[dict]: Özetlenmiş mesaj listesi
        """
        result = []

        if system_msg:
            result.append(system_msg)

        # Eski mesajları özetle
        if to_compress:
            summary_text = self._create_summary(to_compress)
            result.append({
                "role": "system",
                "content": summary_text,
            })

        result.extend(preserved)
        return result

    def get_compression_stats(
        self,
        original: list[dict],
        compressed: list[dict],
    ) -> dict:
        """
        Sıkıştırma istatistiklerini döndür.

        Parametreler:
            original: Orijinal mesajlar
            compressed: Sıkıştırılmış mesajlar

        Döndürür:
            dict: İstatistikler
        """
        orig_tokens = self.estimate_messages_tokens(original)
        comp_tokens = self.estimate_messages_tokens(compressed)
        saved = orig_tokens - comp_tokens

        return {
            "original_messages": len(original),
            "compressed_messages": len(compressed),
            "original_tokens": orig_tokens,
            "compressed_tokens": comp_tokens,
            "tokens_saved": saved,
            "compression_ratio": round(saved / orig_tokens * 100, 1) if orig_tokens > 0 else 0,
        }


# ============================================================
# Ana çalıştırma bloğu — Demo
# ============================================================

if __name__ == "__main__":
    print("🗜️ Bağlam Sıkıştırıcı (Context Compressor) — Demo")
    print("=" * 55)
    print()

    # Uzun bir konuşma geçmişi simüle et
    messages = [
        {"role": "system", "content": "Sen yardımcı bir Python asistanısın. Kullanıcıya Türkçe cevap ver."},
        {"role": "user", "content": "Python nedir?"},
        {"role": "assistant", "content": "Python, 1991 yılında Guido van Rossum tarafından oluşturulmuş yüksek seviyeli bir programlama dilidir. Okunabilirliği ve basit sözdizimi ile bilinir. Web geliştirme, veri bilimi, yapay zeka ve otomasyon gibi birçok alanda kullanılır."},
        {"role": "user", "content": "Değişken nasıl tanımlanır?"},
        {"role": "assistant", "content": "Python'da değişken tanımlamak çok kolaydır. Herhangi bir tür belirtmenize gerek yoktur. Örneğin: x = 5 bir tam sayı değişkeni, name = 'Ali' bir metin değişkeni oluşturur. Python dinamik tipli olduğu için tür otomatik algılanır."},
        {"role": "user", "content": "Liste ve tuple arasındaki fark nedir?"},
        {"role": "assistant", "content": "Liste (list) değiştirilebilir (mutable) bir veri yapısıdır ve köşeli parantez ile tanımlanır: [1, 2, 3]. Tuple ise değiştirilemez (immutable) ve normal parantez ile tanımlanır: (1, 2, 3). Tuple daha hızlıdır çünkü değiştirilemez. Sözlük anahtarı olarak tuple kullanılabilir ama liste kullanılamaz."},
        {"role": "user", "content": "For döngüsü nasıl kullanılır?"},
        {"role": "assistant", "content": "Python'da for döngüsü, bir iterable üzerinde gezinmek için kullanılır. Örnek: for i in range(10): print(i) — bu 0'dan 9'a kadar sayıları yazdırır. Listeler, stringler, sözlükler ve diğer iterable nesneler üzerinde de gezinebilirsiniz."},
        {"role": "user", "content": "Fonksiyon nasıl yazılır?"},
        {"role": "assistant", "content": "Python'da fonksiyon def anahtar kelimesi ile tanımlanır. Örnek: def topla(a, b): return a + b. Fonksiyonlar varsayılan parametreler, *args ve **kwargs destekler. Type hint ile parametrelerin ve dönüş değerinin tipini belirtebilirsiniz: def topla(a: int, b: int) -> int."},
        {"role": "user", "content": "Şimdi bir sınıf yazalım. Araba sınıfı oluştur."},
    ]

    # Sıkıştırıcı oluştur (düşük limit ile demo için)
    compressor = ContextCompressor(
        max_tokens=300,      # Düşük limit (demo için)
        preserve_last=2,     # Son 2 mesajı koru
    )

    # Orijinal durumu göster
    orig_tokens = compressor.estimate_messages_tokens(messages)
    print(f"📝 Orijinal: {len(messages)} mesaj, ~{orig_tokens} token")
    print()

    # Kırpma stratejisi
    print("─" * 55)
    print("📌 Strateji 1: Kırpma (Truncation)")
    print("─" * 55)
    truncated = compressor.compress_messages(messages, strategy="truncate")
    stats_t = compressor.get_compression_stats(messages, truncated)
    print(f"  Sonuç: {stats_t['compressed_messages']} mesaj, ~{stats_t['compressed_tokens']} token")
    print(f"  Tasarruf: {stats_t['tokens_saved']} token (%{stats_t['compression_ratio']})")
    print(f"  Mesajlar:")
    for m in truncated:
        content_preview = m['content'][:60] + "..." if len(m['content']) > 60 else m['content']
        print(f"    [{m['role']}] {content_preview}")

    # Özetleme stratejisi
    print()
    print("─" * 55)
    print("📌 Strateji 2: Özetleme (Summarization)")
    print("─" * 55)
    summarized = compressor.compress_messages(messages, strategy="summarize")
    stats_s = compressor.get_compression_stats(messages, summarized)
    print(f"  Sonuç: {stats_s['compressed_messages']} mesaj, ~{stats_s['compressed_tokens']} token")
    print(f"  Tasarruf: {stats_s['tokens_saved']} token (%{stats_s['compression_ratio']})")
    print(f"  Mesajlar:")
    for m in summarized:
        content_preview = m['content'][:80] + "..." if len(m['content']) > 80 else m['content']
        print(f"    [{m['role']}] {content_preview}")

    print()
    print("✅ Demo tamamlandı!")
