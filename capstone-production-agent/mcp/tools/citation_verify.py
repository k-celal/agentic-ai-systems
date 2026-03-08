"""
Kaynak Doğrulama Aracı - Simüle Edilmiş Atıf Kontrolü
=========================================================
İçerikteki iddiaların sağlanan kaynaklarla desteklenip desteklenmediğini
kontrol eden simüle edilmiş bir doğrulama aracıdır.

Bu Araç Neden Gerekli?
------------------------
AI tarafından üretilen içeriklerde "halüsinasyon" riski her zaman vardır.
Bu araç, üretilen içeriğin sağlanan kaynaklara dayalı olup olmadığını
kontrol ederek güvenilirliği artırır.

Nasıl Çalışır? (Simülasyon)
-----------------------------
Bu araç gerçek NLP yerine basitleştirilmiş anahtar kelime eşleme
kullanır. Üretim ortamında semantic similarity veya NLI (Natural
Language Inference) modelleri kullanılmalıdır.

Doğrulama Adımları:
    1. İçerik cümlelerine ayrılır
    2. Her cümle anahtar kelimelere dönüştürülür
    3. Kaynakların anahtar kelimeleri ile karşılaştırılır
    4. Eşleşme oranına göre "doğrulanmış" veya "doğrulanmamış" belirlenir
    5. Genel kapsama puanı (coverage_score) hesaplanır

Kullanım:
    from mcp.tools.citation_verify import verify_citations
    
    sonuc = verify_citations(
        content="Yapay zeka ajanları otonom kararlar alabilir...",
        sources=[
            {"title": "AI Agents Guide", "content": "Agents can make autonomous decisions..."},
        ],
    )
    
    print(f"Kapsama: %{sonuc['coverage_score']}")
"""

import sys
import os
import re
from typing import Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema
from shared.telemetry.logger import get_logger

logger = get_logger("mcp.tools.citation_verify")


# ═══════════════════════════════════════════════════════════════════
#  DURMA KELİMELERİ (Stop Words)
# ═══════════════════════════════════════════════════════════════════

STOP_WORDS: set[str] = {
    # Türkçe
    "bir", "bu", "ve", "ile", "için", "de", "da", "mi", "mu", "mı",
    "ne", "olan", "olarak", "daha", "çok", "en", "ise", "her", "gibi",
    "ya", "hem", "kadar", "sonra", "önce", "ancak", "ama", "fakat",
    "veya", "ki", "den", "dan", "ten", "tan", "dir", "dır", "tir",
    "tır", "nin", "nın", "nun", "nün", "ler", "lar",
    # İngilizce
    "the", "is", "are", "was", "were", "and", "or", "for", "with",
    "how", "what", "a", "an", "in", "on", "at", "to", "of", "that",
    "this", "can", "will", "has", "have", "had", "be", "been",
}


# ═══════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════

def _anahtar_kelimeleri_cikar(text: str) -> set[str]:
    """
    Metinden anlamlı anahtar kelimeleri çıkar.
    
    Durma kelimelerini filtreler, küçük harfe dönüştürür
    ve 2 karakterden kısa kelimeleri atar.
    
    Parametreler:
        text: İşlenecek metin
    
    Döndürür:
        set[str]: Anahtar kelimeler kümesi
    """
    kelimeler = re.findall(r'\b\w+\b', text.lower())
    return {
        k for k in kelimeler
        if k not in STOP_WORDS and len(k) > 2
    }


def _cumlelere_ayir(text: str) -> list[str]:
    """
    Metni cümlelerine ayır.
    
    Parametreler:
        text: Ayrıştırılacak metin
    
    Döndürür:
        list[str]: Cümle listesi (en az 5 kelimelik)
    """
    cumleler = re.split(r'[.!?]+', text)
    return [
        c.strip() for c in cumleler
        if c.strip() and len(c.strip().split()) >= 5
    ]


def _eslesme_orani(cumle_kelimeleri: set[str], kaynak_kelimeleri: set[str]) -> float:
    """
    İki anahtar kelime kümesi arasındaki eşleşme oranını hesapla.
    
    Jaccard benzerliği kullanır: kesişim / birleşim
    Ayrıca cümledeki kelimelerin kaçının kaynakta bulunduğunu da
    hesaplar ve ağırlıklı ortalama döndürür.
    
    Parametreler:
        cumle_kelimeleri: Cümleden çıkarılan anahtar kelimeler
        kaynak_kelimeleri: Kaynaktan çıkarılan anahtar kelimeler
    
    Döndürür:
        float: Eşleşme oranı (0.0 - 1.0)
    """
    if not cumle_kelimeleri or not kaynak_kelimeleri:
        return 0.0
    
    # Kesişim
    ortak = cumle_kelimeleri & kaynak_kelimeleri
    
    if not ortak:
        return 0.0
    
    # Kapsama oranı (cümle kelimelerinin kaçı kaynakta?)
    kapsama = len(ortak) / len(cumle_kelimeleri)
    
    # Jaccard benzerliği
    birlesim = cumle_kelimeleri | kaynak_kelimeleri
    jaccard = len(ortak) / len(birlesim)
    
    # Ağırlıklı ortalama (%70 kapsama, %30 Jaccard)
    return kapsama * 0.7 + jaccard * 0.3


# ═══════════════════════════════════════════════════════════════════
#  ANA DOĞRULAMA FONKSİYONU
# ═══════════════════════════════════════════════════════════════════

def verify_citations(content: str, sources: list) -> dict:
    """
    İçerikteki iddiaların kaynaklarla desteklenip desteklenmediğini doğrula.
    
    Her kaynak şu alanları içermelidir:
        - title (str): Kaynak başlığı
        - content (str): Kaynak içeriği/özeti
    
    Opsiyonel:
        - url (str): Kaynak URL'si
        - author (str): Yazar
    
    Parametreler:
        content: Doğrulanacak içerik metni
        sources: Referans kaynaklar listesi
    
    Döndürür:
        dict: Doğrulama sonucu
            - coverage_score (int): Kapsama puanı (0-100)
            - total_claims (int): Toplam iddia (cümle) sayısı
            - verified_claims (list[dict]): Doğrulanan iddialar
            - unverified_claims (list[dict]): Doğrulanmayan iddialar
            - source_usage (dict): Kaynak kullanım istatistikleri
            - verification_summary (str): Özet rapor
    
    Örnek:
        >>> sonuc = verify_citations(
        ...     content="LLM'ler transformer mimarisini kullanır.",
        ...     sources=[{"title": "LLM Rehberi", "content": "Transformer tabanlı..."}],
        ... )
        >>> print(f"Kapsama: %{sonuc['coverage_score']}")
    """
    logger.info(
        f"Kaynak doğrulaması başlatıldı: "
        f"{len(content)} karakter içerik, {len(sources)} kaynak"
    )
    
    if not sources:
        logger.warning("Kaynak listesi boş!")
        return {
            "coverage_score": 0,
            "total_claims": 0,
            "verified_claims": [],
            "unverified_claims": [],
            "source_usage": {},
            "verification_summary": "Doğrulama yapılamadı: kaynak listesi boş.",
        }
    
    # ─── Kaynakları İşle ───
    kaynak_verileri: list[dict] = []
    for i, kaynak in enumerate(sources):
        title = kaynak.get("title", f"Kaynak-{i+1}")
        kaynak_content = kaynak.get("content", "")
        url = kaynak.get("url", "")
        
        kaynak_verileri.append({
            "title": title,
            "url": url,
            "keywords": _anahtar_kelimeleri_cikar(
                f"{title} {kaynak_content}"
            ),
            "used_count": 0,
        })
    
    # Tüm kaynak anahtar kelimelerini birleştir (her kaynak ayrı ayrı da kontrol edilir)
    tum_kaynak_kelimeleri: set[str] = set()
    for kv in kaynak_verileri:
        tum_kaynak_kelimeleri.update(kv["keywords"])
    
    # ─── İçeriği Cümlelere Ayır ───
    cumleler = _cumlelere_ayir(content)
    
    if not cumleler:
        logger.warning("İçerikte yeterli cümle bulunamadı")
        return {
            "coverage_score": 0,
            "total_claims": 0,
            "verified_claims": [],
            "unverified_claims": [],
            "source_usage": {},
            "verification_summary": "İçerikte doğrulanabilir cümle bulunamadı.",
        }
    
    # ─── Her Cümleyi Doğrula ───
    dogrulanan: list[dict] = []
    dogrulanmayan: list[dict] = []
    
    DOGRULAMA_ESIGI = 0.25  # Eşleşme oranı eşiği
    
    for cumle in cumleler:
        cumle_kelimeleri = _anahtar_kelimeleri_cikar(cumle)
        
        if len(cumle_kelimeleri) < 2:
            continue  # Çok kısa cümleler atla
        
        # Her kaynakla eşleşme oranı
        en_iyi_eslesme = 0.0
        en_iyi_kaynak = None
        
        for kv in kaynak_verileri:
            oran = _eslesme_orani(cumle_kelimeleri, kv["keywords"])
            
            if oran > en_iyi_eslesme:
                en_iyi_eslesme = oran
                en_iyi_kaynak = kv
        
        if en_iyi_eslesme >= DOGRULAMA_ESIGI and en_iyi_kaynak is not None:
            dogrulanan.append({
                "claim": cumle[:150],
                "match_score": round(en_iyi_eslesme, 3),
                "matched_source": en_iyi_kaynak["title"],
                "matched_keywords": list(
                    cumle_kelimeleri & en_iyi_kaynak["keywords"]
                )[:10],
            })
            en_iyi_kaynak["used_count"] += 1
        else:
            dogrulanmayan.append({
                "claim": cumle[:150],
                "best_match_score": round(en_iyi_eslesme, 3),
                "closest_source": en_iyi_kaynak["title"] if en_iyi_kaynak else "yok",
            })
    
    # ─── Kapsama Puanı ───
    toplam_iddia = len(dogrulanan) + len(dogrulanmayan)
    if toplam_iddia > 0:
        coverage_score = round((len(dogrulanan) / toplam_iddia) * 100)
    else:
        coverage_score = 0
    
    # ─── Kaynak Kullanım İstatistikleri ───
    kaynak_kullanimi = {}
    for kv in kaynak_verileri:
        kaynak_kullanimi[kv["title"]] = {
            "used_count": kv["used_count"],
            "keyword_count": len(kv["keywords"]),
            "url": kv["url"],
        }
    
    # ─── Özet Rapor ───
    ozet = _generate_verification_summary(
        coverage_score=coverage_score,
        toplam_iddia=toplam_iddia,
        dogrulanan_sayisi=len(dogrulanan),
        dogrulanmayan_sayisi=len(dogrulanmayan),
        kaynak_sayisi=len(sources),
        kaynak_kullanimi=kaynak_kullanimi,
    )
    
    logger.info(
        f"Kaynak doğrulama tamamlandı: %{coverage_score} kapsama | "
        f"{len(dogrulanan)} doğrulanmış, {len(dogrulanmayan)} doğrulanmamış"
    )
    
    return {
        "coverage_score": coverage_score,
        "total_claims": toplam_iddia,
        "verified_claims": dogrulanan,
        "unverified_claims": dogrulanmayan,
        "source_usage": kaynak_kullanimi,
        "verification_summary": ozet,
        "verified_at": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
#  ÖZET RAPOR OLUŞTURMA
# ═══════════════════════════════════════════════════════════════════

def _generate_verification_summary(
    coverage_score: int,
    toplam_iddia: int,
    dogrulanan_sayisi: int,
    dogrulanmayan_sayisi: int,
    kaynak_sayisi: int,
    kaynak_kullanimi: dict,
) -> str:
    """
    Doğrulama özet raporu oluştur.
    
    Döndürür:
        str: Formatlanmış özet rapor
    """
    # Kapsama seviyesi değerlendirmesi
    if coverage_score >= 80:
        seviye = "Yüksek"
        yorum = "İçerik büyük ölçüde kaynaklarla desteklenmektedir."
    elif coverage_score >= 50:
        seviye = "Orta"
        yorum = "İçeriğin bir kısmı kaynaklarla desteklenmektedir, ek kaynaklar önerilir."
    elif coverage_score >= 25:
        seviye = "Düşük"
        yorum = "İçeriğin çoğu kaynaklarla desteklenmiyor. Daha fazla kaynak ekleyin."
    else:
        seviye = "Çok Düşük"
        yorum = "İçerik kaynaklarla yeterince desteklenmiyor. Ciddi revizyon gerekli."
    
    lines = [
        "",
        f"{'═' * 55}",
        f"  Kaynak Doğrulama Raporu",
        f"{'═' * 55}",
        f"  Kapsama Puanı:     %{coverage_score} ({seviye})",
        f"  Toplam İddia:      {toplam_iddia}",
        f"  Doğrulanan:        {dogrulanan_sayisi}",
        f"  Doğrulanmayan:     {dogrulanmayan_sayisi}",
        f"  Kullanılan Kaynak: {kaynak_sayisi}",
        f"{'─' * 55}",
        f"  Değerlendirme: {yorum}",
        f"{'─' * 55}",
        f"  Kaynak Kullanımı:",
    ]
    
    for kaynak, kullanim in kaynak_kullanimi.items():
        durum = "Kullanıldı" if kullanim["used_count"] > 0 else "Kullanılmadı"
        lines.append(
            f"    {kaynak[:35]:35s} | {kullanim['used_count']:2d} eşleşme | {durum}"
        )
    
    lines.append(f"{'═' * 55}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  ARAÇ ŞEMASI
# ═══════════════════════════════════════════════════════════════════

CITATION_VERIFY_SCHEMA = create_tool_schema(
    name="verify_citations",
    description=(
        "İçerikteki iddiaların sağlanan kaynaklarla desteklenip desteklenmediğini "
        "doğrular. Anahtar kelime eşleme ile kapsama puanı hesaplar. "
        "Doğrulanan ve doğrulanmayan iddiaları ayrı ayrı raporlar."
    ),
    parameters={
        "content": {
            "type": "string",
            "description": "Doğrulanacak içerik metni",
        },
        "sources": {
            "type": "array",
            "description": (
                "Referans kaynak listesi. Her kaynak: "
                "{'title': str, 'content': str, 'url': str (opsiyonel)}"
            ),
        },
    },
    required=["content", "sources"],
)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 60)
    print("  Kaynak Doğrulama Aracı - Test")
    print("=" * 60)
    
    # Test içeriği
    test_icerik = """
    Yapay zeka ajanları, belirli görevleri tamamlamak için otonom kararlar alabilen
    yazılım sistemleridir. LLM tabanlı ajanlar, algılama-düşünme-eylem döngüsünde
    çalışır ve araç kullanımı yeteneklerine sahiptir.
    
    MCP protokolü, Anthropic tarafından geliştirilmiş bir standart olup LLM'lerin
    dış dünyayla etkileşimini düzenler. USB-C gibi tek bir standart sağlar.
    
    Büyük dil modelleri transformer mimarisini kullanır ve milyarlarca parametre
    ile eğitilir. Token ekonomisi ve bağlam penceresi önemli kavramlardır.
    
    Quantum bilgisayarlar yakın gelecekte tüm şifreleme yöntemlerini kırabilir.
    Mars'ta yapay zeka destekli koloni kurulması 2030'dan önce gerçekleşecektir.
    """
    
    # Test kaynakları
    test_kaynaklar = [
        {
            "title": "Yapay Zeka Ajanları Rehberi",
            "content": (
                "Yapay zeka ajanları otonom kararlar alabilen yazılım sistemleridir. "
                "LLM tabanlı ajanlar algılama düşünme eylem döngüsünde çalışır. "
                "Araç kullanımı modern ajanların temel yeteneklerinden biridir."
            ),
            "url": "https://ornek.com/ai-agents",
        },
        {
            "title": "MCP Protokolü Dokümantasyonu",
            "content": (
                "Model Context Protocol Anthropic tarafından geliştirilmiştir. "
                "LLM araç etkileşimini standartlaştırır. "
                "Sunucu istemci mimarisi ile çalışır."
            ),
            "url": "https://ornek.com/mcp",
        },
        {
            "title": "LLM Temelleri",
            "content": (
                "Büyük dil modelleri transformer mimarisini kullanır. "
                "Milyarlarca parametre ile eğitilir. Token ekonomisi "
                "ve bağlam penceresi temel kavramlardır."
            ),
            "url": "https://ornek.com/llm",
        },
    ]
    
    sonuc = verify_citations(content=test_icerik, sources=test_kaynaklar)
    
    print(f"\nKapsama Puanı: %{sonuc['coverage_score']}")
    print(f"Toplam İddia: {sonuc['total_claims']}")
    
    print(f"\nDoğrulanan İddialar ({len(sonuc['verified_claims'])}):")
    for d in sonuc["verified_claims"][:5]:
        print(f"  [{d['match_score']:.3f}] {d['claim'][:80]}...")
        print(f"          Kaynak: {d['matched_source']}")
    
    print(f"\nDoğrulanmayan İddialar ({len(sonuc['unverified_claims'])}):")
    for d in sonuc["unverified_claims"][:3]:
        print(f"  [{d['best_match_score']:.3f}] {d['claim'][:80]}...")
    
    # Kaynak kullanımı
    print(f"\nKaynak Kullanımı:")
    for kaynak, kullanim in sonuc["source_usage"].items():
        print(f"  {kaynak}: {kullanim['used_count']} eşleşme")
    
    # Özet rapor
    print(sonuc["verification_summary"])
    
    # Boş kaynak testi
    print("\n--- Boş Kaynak Testi ---")
    bos_sonuc = verify_citations("Test içerik.", [])
    print(f"  Kapsama: %{bos_sonuc['coverage_score']}")
    print(f"  Özet: {bos_sonuc['verification_summary']}")
    
    print("\nTest tamamlandı!")
