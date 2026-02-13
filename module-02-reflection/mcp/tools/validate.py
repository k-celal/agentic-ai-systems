"""
Validate Tool - Doğrulama Aracı
==================================
Üretilen içeriği çeşitli kurallara göre doğrular.

Bu Tool Neden Var?
-----------------
Agent kendi çıktısını eleştirirken "kendi hatalarını göremeyebilir".
Dış bir doğrulama aracı, objektif kurallar uygular:
- Minimum uzunluk kontrolü
- Zorunlu bölüm kontrolü
- Format kontrolü
- Yasak kelime kontrolü

Kullanım:
    result = validate_content(
        content="Kısa metin",
        rules={
            "min_length": 100,
            "required_sections": ["Giriş", "Sonuç"],
        }
    )
    
    if result["is_valid"]:
        print("İçerik geçerli!")
    else:
        for violation in result["violations"]:
            print(f"İhlal: {violation}")
"""

import sys
import os
import re
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema


def validate_content(
    content: str,
    min_length: int = 50,
    max_length: int = 5000,
    required_keywords: list[str] = None,
    forbidden_words: list[str] = None,
    required_sections: list[str] = None,
    check_grammar_basics: bool = True,
) -> dict:
    """
    İçeriği çeşitli kurallara göre doğrula.
    
    Bu fonksiyon, bir MCP tool olarak agent tarafından çağrılır.
    Üretilen içeriğin kalite standartlarını karşılayıp karşılamadığını kontrol eder.
    
    Parametreler:
        content: Doğrulanacak içerik
        min_length: Minimum karakter sayısı
        max_length: Maksimum karakter sayısı
        required_keywords: İçerikte olması gereken kelimeler
        forbidden_words: İçerikte olmaması gereken kelimeler
        required_sections: Olması gereken bölüm başlıkları
        check_grammar_basics: Basit gramer kontrolü yap mı?
    
    Döndürür:
        dict: {
            "is_valid": True/False,
            "score": 1-10 arası puan,
            "violations": [...ihlaller...],
            "warnings": [...uyarılar...],
            "stats": {...istatistikler...}
        }
    
    Örnek:
        >>> validate_content("Kısa", min_length=100)
        {
            "is_valid": False,
            "score": 3,
            "violations": ["İçerik çok kısa: 5 karakter (minimum: 100)"],
            ...
        }
    """
    violations = []    # Kuralları ihlal eden durumlar
    warnings = []      # Uyarılar (ihlal değil ama dikkat)
    score = 10         # 10'dan başla, her ihlalde düş
    
    # ─── 1. Uzunluk Kontrolü ───
    content_length = len(content.strip())
    
    if content_length < min_length:
        violations.append(
            f"İçerik çok kısa: {content_length} karakter (minimum: {min_length})"
        )
        score -= 3
    
    if content_length > max_length:
        violations.append(
            f"İçerik çok uzun: {content_length} karakter (maksimum: {max_length})"
        )
        score -= 1
    
    # ─── 2. Zorunlu Kelime Kontrolü ───
    if required_keywords:
        content_lower = content.lower()
        missing_keywords = []
        for keyword in required_keywords:
            if keyword.lower() not in content_lower:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            violations.append(
                f"Eksik anahtar kelimeler: {', '.join(missing_keywords)}"
            )
            score -= min(3, len(missing_keywords))
    
    # ─── 3. Yasak Kelime Kontrolü ───
    if forbidden_words:
        content_lower = content.lower()
        found_forbidden = []
        for word in forbidden_words:
            if word.lower() in content_lower:
                found_forbidden.append(word)
        
        if found_forbidden:
            violations.append(
                f"Yasak kelimeler bulundu: {', '.join(found_forbidden)}"
            )
            score -= min(3, len(found_forbidden))
    
    # ─── 4. Zorunlu Bölüm Kontrolü ───
    if required_sections:
        missing_sections = []
        for section in required_sections:
            # Başlık formatlarını kontrol et: "# Bölüm", "## Bölüm", "Bölüm:"
            patterns = [
                f"#{1,3}\\s*{re.escape(section)}",
                f"{re.escape(section)}\\s*:",
                f"\\*\\*{re.escape(section)}\\*\\*",
            ]
            found = any(re.search(p, content, re.IGNORECASE) for p in patterns)
            if not found:
                missing_sections.append(section)
        
        if missing_sections:
            violations.append(
                f"Eksik bölümler: {', '.join(missing_sections)}"
            )
            score -= min(3, len(missing_sections))
    
    # ─── 5. Basit Gramer Kontrolü ───
    if check_grammar_basics:
        # Cümle büyük harfle başlıyor mu?
        sentences = re.split(r'[.!?]\s+', content.strip())
        if sentences and sentences[0] and not sentences[0][0].isupper():
            warnings.append("İlk cümle büyük harfle başlamıyor")
            score -= 1
        
        # Çok fazla tekrar var mı?
        words = content.lower().split()
        if len(words) > 10:
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            
            repetitive_words = [
                w for w, c in word_freq.items()
                if c > len(words) * 0.1 and len(w) > 3
            ]
            if repetitive_words:
                warnings.append(
                    f"Tekrarlayan kelimeler: {', '.join(repetitive_words[:3])}"
                )
    
    # ─── İstatistikler ───
    words = content.split()
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    stats = {
        "character_count": content_length,
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
        "avg_sentence_length": len(words) / max(len(sentences), 1),
    }
    
    # Score'u 1-10 arasında tut
    score = max(1, min(10, score))
    
    return {
        "is_valid": len(violations) == 0,
        "score": score,
        "violations": violations,
        "warnings": warnings,
        "stats": stats,
    }


# Tool Şeması
VALIDATE_SCHEMA = create_tool_schema(
    name="validate_content",
    description=(
        "Üretilen içeriği çeşitli kurallara göre doğrular. "
        "Uzunluk, anahtar kelime, yasak kelime ve format kontrolü yapar."
    ),
    parameters={
        "content": {
            "type": "string",
            "description": "Doğrulanacak içerik metni",
        },
        "min_length": {
            "type": "number",
            "description": "Minimum karakter sayısı (varsayılan: 50)",
        },
        "required_keywords": {
            "type": "string",
            "description": "Zorunlu anahtar kelimeler (virgülle ayrılmış)",
        },
    },
    required=["content"],
)


# ─────────────────────────────────────────
# Test
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Validation Tool Test")
    print("=" * 40)
    
    # Test 1: Geçerli içerik
    result = validate_content(
        content="Bu bir test içeriğidir. Python programlama dili hakkında bilgi vermektedir. "
                "Python, kolay öğrenilen ve güçlü bir programlama dilidir.",
        min_length=50,
        required_keywords=["Python", "programlama"],
    )
    print(f"Test 1 (Geçerli): {result['is_valid']} | Puan: {result['score']}/10")
    
    # Test 2: Çok kısa içerik
    result = validate_content(
        content="Kısa",
        min_length=100,
    )
    print(f"Test 2 (Kısa):    {result['is_valid']} | Puan: {result['score']}/10")
    print(f"   İhlaller: {result['violations']}")
    
    # Test 3: Eksik kelimeler
    result = validate_content(
        content="Bu bir uzun metin örneğidir. " * 5,
        required_keywords=["Python", "AI"],
    )
    print(f"Test 3 (Eksik):   {result['is_valid']} | Puan: {result['score']}/10")
    print(f"   İhlaller: {result['violations']}")
    
    # Test 4: Yasak kelimeler
    result = validate_content(
        content="Bu çok güzel bir PLACEHOLDER metindir. TODO: düzelt.",
        min_length=10,
        forbidden_words=["PLACEHOLDER", "TODO"],
    )
    print(f"Test 4 (Yasak):   {result['is_valid']} | Puan: {result['score']}/10")
    print(f"   İhlaller: {result['violations']}")
    
    print("\n✅ Tüm testler tamamlandı!")
