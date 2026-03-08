"""
Yazı Değerlendirme Aracı - Kural Tabanlı Kalite Analizi
==========================================================
Üretilen metinlerin kalitesini kural tabanlı (LLM kullanmadan)
değerlendiren araçtır.

Neden Kural Tabanlı?
----------------------
Bu araç bilinçli olarak LLM kullanmaz. Nedenleri:
1. Maliyet: Değerlendirme için ek API çağrısı gerekmez
2. Deterministik: Aynı metin her seferinde aynı puanı alır
3. Hız: Milisaniyeler içinde sonuç verir
4. Bağımsızlık: İnternet bağlantısı gerektirmez

Değerlendirme Boyutları:
    1. Kelime Sayısı: Minimum kelime eşiği kontrolü
    2. Cümle Çeşitliliği: Cümle uzunluk dağılımı
    3. Paragraf Yapısı: Paragraf sayısı ve ortalama uzunluk
    4. Anahtar Kelime Yoğunluğu: Tekrarlanan kelimelerin oranı
    5. Okunabilirlik: Ortalama kelime/cümle oranı

Kullanım:
    from mcp.tools.eval_tool import evaluate_writing
    
    sonuc = evaluate_writing(content="Uzun bir metin...", min_words=500)
    print(f"Puan: {sonuc['score']}/10")
    for sorun in sonuc["issues"]:
        print(f"  - {sorun}")
"""

import sys
import os
import re
from typing import Any
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema
from shared.telemetry.logger import get_logger

logger = get_logger("mcp.tools.eval_tool")


# ═══════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════

def _cumlelerine_ayir(text: str) -> list[str]:
    """
    Metni cümlelerine ayır.
    
    Nokta, soru işareti ve ünlem işaretine göre böler.
    Boş cümleleri filtreler.
    
    Parametreler:
        text: Ayrıştırılacak metin
    
    Döndürür:
        list[str]: Cümle listesi
    """
    # Kısaltmaları koru (Dr., vb.)
    cumleler = re.split(r'[.!?]+', text)
    cumleler = [c.strip() for c in cumleler if c.strip() and len(c.strip()) > 3]
    return cumleler


def _paragraflarina_ayir(text: str) -> list[str]:
    """
    Metni paragraflarına ayır.
    
    Çift satır sonuna göre böler. Boş paragrafları filtreler.
    
    Parametreler:
        text: Ayrıştırılacak metin
    
    Döndürür:
        list[str]: Paragraf listesi
    """
    paragraflar = re.split(r'\n\s*\n', text)
    paragraflar = [p.strip() for p in paragraflar if p.strip() and len(p.strip()) > 10]
    return paragraflar


def _kelime_frekansi(text: str) -> Counter:
    """
    Metindeki kelime frekanslarını hesapla.
    
    Durma kelimelerini (stop words) hariç tutar.
    
    Parametreler:
        text: Analiz edilecek metin
    
    Döndürür:
        Counter: Kelime frekans sayacı
    """
    stop_words = {
        "bir", "bu", "ve", "ile", "için", "de", "da", "mi", "mu",
        "ne", "olan", "olarak", "daha", "çok", "en", "ise", "her",
        "gibi", "ya", "hem", "kadar", "sonra", "önce", "ancak",
        "ama", "fakat", "veya", "the", "is", "are", "and", "or",
        "a", "an", "in", "on", "at", "to", "of", "that", "this",
    }
    
    kelimeler = re.findall(r'\b\w+\b', text.lower())
    filtrelenmis = [k for k in kelimeler if k not in stop_words and len(k) > 2]
    
    return Counter(filtrelenmis)


# ═══════════════════════════════════════════════════════════════════
#  ANA DEĞERLENDİRME FONKSİYONU
# ═══════════════════════════════════════════════════════════════════

def evaluate_writing(content: str, min_words: int = 500) -> dict:
    """
    Metin kalitesini kural tabanlı olarak değerlendir.
    
    5 farklı boyutta puanlama yapılır ve genel bir skor hesaplanır.
    Her boyut 0-10 arası puan alır, genel skor bunların ağırlıklı
    ortalamasıdır.
    
    Boyutlar ve Ağırlıklar:
        1. Kelime Sayısı (ağırlık: %20): Minimum eşik kontrolü
        2. Cümle Çeşitliliği (ağırlık: %25): Uzunluk dağılımı
        3. Paragraf Yapısı (ağırlık: %20): Sayı ve denge
        4. Anahtar Kelime Yoğunluğu (ağırlık: %15): Tekrar oranı
        5. Okunabilirlik (ağırlık: %20): Kelime/cümle oranı
    
    Parametreler:
        content: Değerlendirilecek metin içeriği
        min_words: Minimum kelime sayısı eşiği (varsayılan: 500)
    
    Döndürür:
        dict: Değerlendirme sonucu
            - score (float): Genel puan (1.0 - 10.0)
            - grade (str): Harf notu (A, B, C, D, F)
            - dimensions (dict): Boyut bazında puanlar
            - stats (dict): Metin istatistikleri
            - issues (list[str]): Tespit edilen sorunlar
            - suggestions (list[str]): İyileştirme önerileri
    
    Örnek:
        >>> sonuc = evaluate_writing("Uzun bir makale metni...", min_words=300)
        >>> print(f"Puan: {sonuc['score']}/10 ({sonuc['grade']})")
        >>> for s in sonuc["suggestions"]:
        ...     print(f"  Öneri: {s}")
    """
    logger.info(f"Yazı değerlendirmesi başlatıldı (min_words={min_words})")
    
    issues: list[str] = []
    suggestions: list[str] = []
    
    # ─── Temel İstatistikler ───
    kelimeler = content.split()
    kelime_sayisi = len(kelimeler)
    karakter_sayisi = len(content)
    cumleler = _cumlelerine_ayir(content)
    cumle_sayisi = len(cumleler)
    paragraflar = _paragraflarina_ayir(content)
    paragraf_sayisi = len(paragraflar)
    
    stats = {
        "word_count": kelime_sayisi,
        "character_count": karakter_sayisi,
        "sentence_count": cumle_sayisi,
        "paragraph_count": paragraf_sayisi,
        "avg_words_per_sentence": round(kelime_sayisi / max(cumle_sayisi, 1), 1),
        "avg_words_per_paragraph": round(kelime_sayisi / max(paragraf_sayisi, 1), 1),
    }
    
    # ═══════════════════════════════════════════════════════════════
    #  BOYUT 1: Kelime Sayısı (%20)
    # ═══════════════════════════════════════════════════════════════
    
    if kelime_sayisi >= min_words:
        kelime_puani = min(10.0, 7.0 + (kelime_sayisi - min_words) / min_words * 3.0)
    elif kelime_sayisi >= min_words * 0.7:
        kelime_puani = 5.0 + (kelime_sayisi / min_words) * 2.0
        issues.append(
            f"Kelime sayısı hedefin altında: {kelime_sayisi}/{min_words} "
            f"(%{kelime_sayisi/min_words*100:.0f})"
        )
    elif kelime_sayisi >= min_words * 0.4:
        kelime_puani = 3.0 + (kelime_sayisi / min_words) * 2.0
        issues.append(
            f"Kelime sayısı yetersiz: {kelime_sayisi}/{min_words} "
            f"(%{kelime_sayisi/min_words*100:.0f})"
        )
        suggestions.append(
            f"İçeriği en az {min_words - kelime_sayisi} kelime daha "
            f"genişletmeyi deneyin."
        )
    else:
        kelime_puani = max(1.0, (kelime_sayisi / min_words) * 4.0)
        issues.append(
            f"Kelime sayısı çok yetersiz: {kelime_sayisi}/{min_words}"
        )
        suggestions.append(
            "İçerik önemli ölçüde genişletilmeli. Alt başlıklar, "
            "örnekler ve açıklamalar ekleyin."
        )
    
    # ═══════════════════════════════════════════════════════════════
    #  BOYUT 2: Cümle Çeşitliliği (%25)
    # ═══════════════════════════════════════════════════════════════
    
    if cumle_sayisi >= 3:
        cumle_uzunluklari = [len(c.split()) for c in cumleler]
        ort_uzunluk = sum(cumle_uzunluklari) / len(cumle_uzunluklari)
        
        # Standart sapma hesapla
        varyans = sum((x - ort_uzunluk) ** 2 for x in cumle_uzunluklari) / len(cumle_uzunluklari)
        std_sapma = varyans ** 0.5
        
        # İdeal: ortalama 10-20 kelime, std sapma 3-8
        if 10 <= ort_uzunluk <= 20 and 3 <= std_sapma <= 10:
            cesitlilik_puani = 9.0
        elif 8 <= ort_uzunluk <= 25 and 2 <= std_sapma <= 12:
            cesitlilik_puani = 7.0
        elif ort_uzunluk < 8:
            cesitlilik_puani = 4.0
            issues.append("Cümleler çok kısa. Daha detaylı ifadeler kullanın.")
            suggestions.append(
                "Bazı kısa cümleleri birleştirerek veya detay ekleyerek "
                "daha akıcı bir anlatım elde edebilirsiniz."
            )
        elif ort_uzunluk > 30:
            cesitlilik_puani = 4.0
            issues.append("Cümleler çok uzun. Bölmeyi deneyin.")
            suggestions.append(
                "Uzun cümleleri nokta veya noktalı virgülle bölerek "
                "okunabilirliği artırabilirsiniz."
            )
        else:
            cesitlilik_puani = 6.0
        
        # Çeşitlilik bonusu: kısa ve uzun cümleler karışık olmalı
        if std_sapma < 2:
            cesitlilik_puani -= 1.0
            issues.append("Cümle uzunlukları çok tekdüze.")
            suggestions.append(
                "Kısa ve uzun cümleleri karıştırarak daha dinamik "
                "bir yazı ritmi oluşturun."
            )
        
        stats["avg_sentence_length"] = round(ort_uzunluk, 1)
        stats["sentence_length_std"] = round(std_sapma, 1)
    else:
        cesitlilik_puani = 2.0
        issues.append(f"Çok az cümle: {cumle_sayisi}")
        suggestions.append("Daha fazla cümle içeren detaylı bir metin yazın.")
    
    # ═══════════════════════════════════════════════════════════════
    #  BOYUT 3: Paragraf Yapısı (%20)
    # ═══════════════════════════════════════════════════════════════
    
    if paragraf_sayisi >= 3:
        paragraf_uzunluklari = [len(p.split()) for p in paragraflar]
        ort_paragraf = sum(paragraf_uzunluklari) / len(paragraf_uzunluklari)
        
        # İdeal: 3-8 paragraf, ortalama 50-150 kelime
        if 3 <= paragraf_sayisi <= 10 and 40 <= ort_paragraf <= 200:
            paragraf_puani = 9.0
        elif 2 <= paragraf_sayisi <= 15 and 20 <= ort_paragraf <= 300:
            paragraf_puani = 7.0
        else:
            paragraf_puani = 5.0
            if ort_paragraf > 300:
                issues.append("Paragraflar çok uzun. Bölmeyi düşünün.")
                suggestions.append(
                    "Uzun paragrafları alt konulara göre bölmek "
                    "okunabilirliği artırır."
                )
        
        stats["avg_paragraph_length"] = round(ort_paragraf, 1)
    elif paragraf_sayisi >= 1:
        paragraf_puani = 4.0
        issues.append(f"Çok az paragraf: {paragraf_sayisi}")
        suggestions.append(
            "Metni mantıksal bölümlere ayırarak paragraflar oluşturun."
        )
    else:
        paragraf_puani = 1.0
        issues.append("Paragraf yapısı bulunamadı.")
        suggestions.append("Metni paragraflara bölmek okunabilirliği büyük ölçüde artırır.")
    
    # ═══════════════════════════════════════════════════════════════
    #  BOYUT 4: Anahtar Kelime Yoğunluğu (%15)
    # ═══════════════════════════════════════════════════════════════
    
    frekans = _kelime_frekansi(content)
    toplam_kelime = sum(frekans.values())
    
    if toplam_kelime > 10:
        # En sık 5 kelime
        en_sik = frekans.most_common(5)
        
        # En sık kelimenin yoğunluğu
        if en_sik:
            max_yogunluk = en_sik[0][1] / toplam_kelime
        else:
            max_yogunluk = 0
        
        # Benzersiz kelime oranı
        benzersiz_oran = len(frekans) / toplam_kelime
        
        # İdeal: yoğunluk < %5, benzersiz oran > %40
        if max_yogunluk < 0.05 and benzersiz_oran > 0.4:
            yogunluk_puani = 9.0
        elif max_yogunluk < 0.08 and benzersiz_oran > 0.3:
            yogunluk_puani = 7.0
        elif max_yogunluk > 0.10:
            yogunluk_puani = 4.0
            tekrar_kelime = en_sik[0][0] if en_sik else "?"
            issues.append(
                f"Anahtar kelime tekrarı yüksek: "
                f"'{tekrar_kelime}' %{max_yogunluk*100:.1f} yoğunlukta"
            )
            suggestions.append(
                f"'{tekrar_kelime}' kelimesini eşanlamlılarıyla "
                f"değiştirerek çeşitliliği artırın."
            )
        else:
            yogunluk_puani = 6.0
        
        stats["unique_word_ratio"] = round(benzersiz_oran, 3)
        stats["top_keywords"] = [{"word": w, "count": c} for w, c in en_sik]
    else:
        yogunluk_puani = 2.0
        issues.append("Yeterli kelime yok, kelime yoğunluğu analizi yapılamadı.")
    
    # ═══════════════════════════════════════════════════════════════
    #  BOYUT 5: Okunabilirlik (%20)
    # ═══════════════════════════════════════════════════════════════
    
    ort_kelime_cumle = kelime_sayisi / max(cumle_sayisi, 1)
    
    # Ortalama kelime uzunluğu
    if kelimeler:
        ort_kelime_uzunlugu = sum(len(k) for k in kelimeler) / len(kelimeler)
    else:
        ort_kelime_uzunlugu = 0
    
    # İdeal: cümle başına 12-18 kelime, ortalama kelime uzunluğu 4-7 harf
    if 10 <= ort_kelime_cumle <= 22 and 4 <= ort_kelime_uzunlugu <= 8:
        okunabilirlik_puani = 9.0
    elif 8 <= ort_kelime_cumle <= 28 and 3 <= ort_kelime_uzunlugu <= 10:
        okunabilirlik_puani = 7.0
    elif ort_kelime_cumle > 30:
        okunabilirlik_puani = 4.0
        issues.append(
            f"Okunabilirlik düşük: cümle başına {ort_kelime_cumle:.0f} kelime "
            f"(ideal: 12-18)"
        )
        suggestions.append(
            "Cümleleri kısaltarak ve basit yapılar kullanarak "
            "okunabilirliği artırabilirsiniz."
        )
    elif ort_kelime_cumle < 6:
        okunabilirlik_puani = 5.0
        issues.append("Cümleler çok basit ve kısa.")
        suggestions.append(
            "Bazı cümleleri birleştirerek ve bağlaçlar kullanarak "
            "daha akıcı bir anlatım sağlayabilirsiniz."
        )
    else:
        okunabilirlik_puani = 6.0
    
    stats["avg_word_length"] = round(ort_kelime_uzunlugu, 1)
    
    # ═══════════════════════════════════════════════════════════════
    #  GENEL SKOR HESAPLAMA
    # ═══════════════════════════════════════════════════════════════
    
    dimensions = {
        "word_count": {
            "score": round(kelime_puani, 1),
            "weight": 0.20,
            "label": "Kelime Sayısı",
        },
        "sentence_variety": {
            "score": round(cesitlilik_puani, 1),
            "weight": 0.25,
            "label": "Cümle Çeşitliliği",
        },
        "paragraph_structure": {
            "score": round(paragraf_puani, 1),
            "weight": 0.20,
            "label": "Paragraf Yapısı",
        },
        "keyword_density": {
            "score": round(yogunluk_puani, 1),
            "weight": 0.15,
            "label": "Anahtar Kelime Yoğunluğu",
        },
        "readability": {
            "score": round(okunabilirlik_puani, 1),
            "weight": 0.20,
            "label": "Okunabilirlik",
        },
    }
    
    # Ağırlıklı ortalama
    genel_skor = sum(
        d["score"] * d["weight"] for d in dimensions.values()
    )
    genel_skor = round(max(1.0, min(10.0, genel_skor)), 1)
    
    # Harf notu
    if genel_skor >= 9.0:
        grade = "A+"
    elif genel_skor >= 8.0:
        grade = "A"
    elif genel_skor >= 7.0:
        grade = "B"
    elif genel_skor >= 6.0:
        grade = "C"
    elif genel_skor >= 5.0:
        grade = "D"
    else:
        grade = "F"
    
    # Sorun yoksa olumlu geri bildirim
    if not issues:
        suggestions.append("İçerik genel olarak iyi durumda. Küçük ince ayarlar yapılabilir.")
    
    logger.info(
        f"Değerlendirme tamamlandı: {genel_skor}/10 ({grade}) | "
        f"{kelime_sayisi} kelime, {cumle_sayisi} cümle, "
        f"{len(issues)} sorun, {len(suggestions)} öneri"
    )
    
    return {
        "score": genel_skor,
        "grade": grade,
        "dimensions": dimensions,
        "stats": stats,
        "issues": issues,
        "suggestions": suggestions,
        "min_words_target": min_words,
    }


# ═══════════════════════════════════════════════════════════════════
#  ARAÇ ŞEMASI
# ═══════════════════════════════════════════════════════════════════

EVALUATE_WRITING_SCHEMA = create_tool_schema(
    name="evaluate_writing",
    description=(
        "Metin kalitesini kural tabanlı olarak değerlendirir. LLM kullanmaz! "
        "Kelime sayısı, cümle çeşitliliği, paragraf yapısı, anahtar kelime "
        "yoğunluğu ve okunabilirlik boyutlarında puanlama yapar. "
        "1-10 arası genel skor, sorunlar ve iyileştirme önerileri döndürür."
    ),
    parameters={
        "content": {
            "type": "string",
            "description": "Değerlendirilecek metin içeriği",
        },
        "min_words": {
            "type": "number",
            "description": (
                "Minimum kelime sayısı eşiği (varsayılan: 500). "
                "Bu eşiğin altındaki metinler düşük puan alır."
            ),
        },
    },
    required=["content"],
)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 60)
    print("  Yazı Değerlendirme Aracı - Test")
    print("=" * 60)
    
    # Test 1: Kısa metin
    print("\n--- Test 1: Kısa Metin ---")
    sonuc = evaluate_writing("Bu çok kısa bir metin.", min_words=100)
    print(f"  Puan: {sonuc['score']}/10 ({sonuc['grade']})")
    print(f"  Sorunlar: {len(sonuc['issues'])}")
    for s in sonuc["issues"][:3]:
        print(f"    - {s}")
    
    # Test 2: Orta uzunlukta metin
    print("\n--- Test 2: Orta Uzunlukta Metin ---")
    orta_metin = """
    Yapay zeka ajanları, modern yazılım dünyasının en heyecan verici gelişmelerinden biridir.
    Bu ajanlar, belirli görevleri tamamlamak için otonom kararlar alabilir. LLM tabanlı ajanlar
    özellikle güçlüdür çünkü doğal dil anlama ve üretme yeteneklerine sahiptirler.
    
    Bir ajanın temel bileşenleri şunlardır: algılama, düşünme ve eylem. Algılama aşamasında
    ajan kullanıcı girdisini ve çevre bilgisini alır. Düşünme aşamasında bu bilgiyi işler
    ve bir plan oluşturur. Eylem aşamasında ise planı uygulamaya koyar.
    
    Araç kullanımı, ajanların yeteneklerini büyük ölçüde genişletir. Bir ajan, web araması
    yapabilir, dosya okuyabilir, kod çalıştırabilir ve API'leri çağırabilir. MCP protokolü
    bu araç kullanımını standartlaştırarak farklı ajan çerçevelerinin aynı araçları kullanmasını
    sağlar.
    
    Çok ajanlı sistemlerde ise birden fazla uzman ajan koordineli çalışır. Bir yönetici ajan
    görevleri alt ajanlara dağıtır ve sonuçları birleştirir. Bu yaklaşım, karmaşık görevlerin
    daha verimli bir şekilde tamamlanmasını sağlar. Örneğin, bir araştırma ajanı bilgi toplar,
    bir yazma ajanı metni oluşturur ve bir editör ajanı kaliteyi kontrol eder.
    """
    sonuc = evaluate_writing(orta_metin, min_words=100)
    print(f"  Puan: {sonuc['score']}/10 ({sonuc['grade']})")
    print(f"  Kelime: {sonuc['stats']['word_count']}")
    print(f"  Cümle: {sonuc['stats']['sentence_count']}")
    print(f"  Paragraf: {sonuc['stats']['paragraph_count']}")
    print(f"  Boyutlar:")
    for key, dim in sonuc["dimensions"].items():
        print(f"    {dim['label']:30s}: {dim['score']}/10")
    if sonuc["suggestions"]:
        print(f"  Öneriler:")
        for s in sonuc["suggestions"][:3]:
            print(f"    - {s}")
    
    # Test 3: İstatistikler
    print("\n--- Test 3: Detaylı İstatistikler ---")
    print(f"  Ort. Cümle Uzunluğu: {sonuc['stats'].get('avg_words_per_sentence', 'N/A')} kelime")
    print(f"  Ort. Paragraf Uzunluğu: {sonuc['stats'].get('avg_words_per_paragraph', 'N/A')} kelime")
    if "top_keywords" in sonuc["stats"]:
        print(f"  En Sık Kelimeler:")
        for kw in sonuc["stats"]["top_keywords"][:5]:
            print(f"    '{kw['word']}': {kw['count']} kez")
    
    print("\nTest tamamlandı!")
