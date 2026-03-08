"""
İçerik Kaydetme Aracı - Bellek İçi Dosya Yönetimi
=====================================================
Üretilen içerikleri bellek içi bir depolama alanında kaydeder,
listeler ve okur.

Bu Araç Neden Gerekli?
------------------------
TwinGraph Studio'da yazma ajanı içerik ürettiğinde, bu içeriğin
güvenli bir şekilde saklanması ve daha sonra erişilebilir olması gerekir.
Bu araç, dosya sistemi yerine bellek içi depolama kullanarak:
- Hızlı okuma/yazma sağlar
- Dosya sistemi yan etkilerinden kaçınır
- Test ve geliştirme ortamında güvenli çalışır

Desteklenen İşlemler:
    - save_content: İçerik kaydet (oluştur veya güncelle)
    - list_saved: Kayıtlı dosyaları listele
    - read_content: Kayıtlı içeriği oku

Kullanım:
    from mcp.tools.content_save import save_content, list_saved, read_content
    
    # İçerik kaydet
    sonuc = save_content("makale.md", "# Başlık\nİçerik...", "markdown")
    
    # Kayıtlı dosyaları listele
    dosyalar = list_saved()
    
    # İçerik oku
    icerik = read_content("makale.md")
"""

import sys
import os
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema
from shared.telemetry.logger import get_logger

logger = get_logger("mcp.tools.content_save")


# ═══════════════════════════════════════════════════════════════════
#  BELLEK İÇİ DEPOLAMA
# ═══════════════════════════════════════════════════════════════════
# Her kayıt: {"content": str, "content_type": str, "size": int,
#             "created_at": str, "updated_at": str, "version": int}

SAVED_CONTENTS: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════════
#  İÇERİK KAYDETME
# ═══════════════════════════════════════════════════════════════════

def save_content(
    filename: str,
    content: str,
    content_type: str = "text",
) -> dict:
    """
    İçeriği bellek içi depoya kaydet.
    
    Eğer aynı dosya adıyla daha önce kayıt varsa, içerik güncellenir
    ve versiyon numarası artırılır.
    
    Parametreler:
        filename: Dosya adı (benzersiz tanımlayıcı, örn: "makale.md")
        content: Kaydedilecek metin içeriği
        content_type: İçerik türü ("text", "markdown", "json", "html", "code")
    
    Döndürür:
        dict: Kayıt durumu
            - status (str): "created" veya "updated"
            - filename (str): Dosya adı
            - size (int): İçerik boyutu (karakter)
            - content_type (str): İçerik türü
            - version (int): Versiyon numarası
            - timestamp (str): Kayıt zamanı (ISO format)
            - word_count (int): Kelime sayısı
    
    Örnek:
        >>> sonuc = save_content("makale.md", "# Yapay Zeka\\nİçerik...", "markdown")
        >>> print(f"Durum: {sonuc['status']}, Boyut: {sonuc['size']} karakter")
    """
    now = datetime.now().isoformat()
    word_count = len(content.split())
    
    if filename in SAVED_CONTENTS:
        # Güncelleme
        mevcut = SAVED_CONTENTS[filename]
        eski_versiyon = mevcut["version"]
        
        SAVED_CONTENTS[filename] = {
            "content": content,
            "content_type": content_type,
            "size": len(content),
            "word_count": word_count,
            "created_at": mevcut["created_at"],
            "updated_at": now,
            "version": eski_versiyon + 1,
        }
        
        status = "updated"
        logger.info(
            f"İçerik güncellendi: {filename} "
            f"(v{eski_versiyon} → v{eski_versiyon + 1}, "
            f"{len(content)} karakter)"
        )
    else:
        # Yeni kayıt
        SAVED_CONTENTS[filename] = {
            "content": content,
            "content_type": content_type,
            "size": len(content),
            "word_count": word_count,
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }
        
        status = "created"
        logger.info(
            f"İçerik kaydedildi: {filename} "
            f"({len(content)} karakter, {word_count} kelime)"
        )
    
    entry = SAVED_CONTENTS[filename]
    
    return {
        "status": status,
        "filename": filename,
        "size": entry["size"],
        "content_type": entry["content_type"],
        "version": entry["version"],
        "timestamp": entry["updated_at"],
        "word_count": entry["word_count"],
    }


# ═══════════════════════════════════════════════════════════════════
#  KAYITLI DOSYALARI LİSTELEME
# ═══════════════════════════════════════════════════════════════════

def list_saved() -> dict:
    """
    Kayıtlı tüm dosyaları listele.
    
    Her dosya için ad, boyut, tür, versiyon ve zaman bilgisi döner.
    Dosya içerikleri bu listeye dahil DEĞİLDİR (boyut nedeniyle).
    
    Döndürür:
        dict: Dosya listesi
            - total_files (int): Toplam dosya sayısı
            - total_size (int): Toplam boyut (karakter)
            - total_words (int): Toplam kelime sayısı
            - files (list[dict]): Dosya bilgileri listesi, her biri:
                - filename (str): Dosya adı
                - content_type (str): İçerik türü
                - size (int): Boyut (karakter)
                - word_count (int): Kelime sayısı
                - version (int): Versiyon
                - created_at (str): Oluşturulma zamanı
                - updated_at (str): Güncellenme zamanı
    
    Örnek:
        >>> sonuc = list_saved()
        >>> print(f"Toplam: {sonuc['total_files']} dosya")
        >>> for f in sonuc["files"]:
        ...     print(f"  {f['filename']} ({f['size']} karakter)")
    """
    files = []
    total_size = 0
    total_words = 0
    
    for filename, entry in SAVED_CONTENTS.items():
        total_size += entry["size"]
        total_words += entry["word_count"]
        
        files.append({
            "filename": filename,
            "content_type": entry["content_type"],
            "size": entry["size"],
            "word_count": entry["word_count"],
            "version": entry["version"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
        })
    
    # Güncelleme zamanına göre sırala (en yeni önce)
    files.sort(key=lambda f: f["updated_at"], reverse=True)
    
    logger.info(f"Dosya listesi: {len(files)} dosya, toplam {total_size} karakter")
    
    return {
        "total_files": len(files),
        "total_size": total_size,
        "total_words": total_words,
        "files": files,
    }


# ═══════════════════════════════════════════════════════════════════
#  İÇERİK OKUMA
# ═══════════════════════════════════════════════════════════════════

def read_content(filename: str) -> dict:
    """
    Kayıtlı bir dosyanın içeriğini oku.
    
    Parametreler:
        filename: Okunacak dosyanın adı
    
    Döndürür:
        dict: Dosya içeriği ve meta veriler
            - found (bool): Dosya bulundu mu?
            - filename (str): Dosya adı
            - content (str): Dosya içeriği (bulunduysa)
            - content_type (str): İçerik türü
            - size (int): Boyut (karakter)
            - word_count (int): Kelime sayısı
            - version (int): Versiyon
            - error (str): Hata mesajı (bulunamadıysa)
    
    Örnek:
        >>> sonuc = read_content("makale.md")
        >>> if sonuc["found"]:
        ...     print(sonuc["content"][:100])
        ... else:
        ...     print(f"Hata: {sonuc['error']}")
    """
    if filename not in SAVED_CONTENTS:
        mevcut = list(SAVED_CONTENTS.keys())
        logger.warning(f"Dosya bulunamadı: {filename} (mevcut: {mevcut})")
        
        return {
            "found": False,
            "filename": filename,
            "error": f"Dosya bulunamadı: '{filename}'",
            "available_files": mevcut,
        }
    
    entry = SAVED_CONTENTS[filename]
    
    logger.info(f"Dosya okundu: {filename} ({entry['size']} karakter)")
    
    return {
        "found": True,
        "filename": filename,
        "content": entry["content"],
        "content_type": entry["content_type"],
        "size": entry["size"],
        "word_count": entry["word_count"],
        "version": entry["version"],
        "created_at": entry["created_at"],
        "updated_at": entry["updated_at"],
    }


# ═══════════════════════════════════════════════════════════════════
#  ARAÇ ŞEMALARI
# ═══════════════════════════════════════════════════════════════════

SAVE_CONTENT_SCHEMA = create_tool_schema(
    name="save_content",
    description=(
        "Üretilen içeriği bellek içi depoya kaydeder. Dosya adı, içerik metni "
        "ve içerik türü belirtilir. Aynı dosya adı ile tekrar çağrıldığında "
        "içerik güncellenir ve versiyon numarası artırılır."
    ),
    parameters={
        "filename": {
            "type": "string",
            "description": (
                "Dosya adı (benzersiz tanımlayıcı). "
                "Örnek: 'makale.md', 'rapor.txt', 'veri.json'"
            ),
        },
        "content": {
            "type": "string",
            "description": "Kaydedilecek metin içeriği",
        },
        "content_type": {
            "type": "string",
            "description": (
                "İçerik türü: 'text', 'markdown', 'json', 'html', 'code' "
                "(varsayılan: 'text')"
            ),
        },
    },
    required=["filename", "content"],
)

LIST_SAVED_SCHEMA = create_tool_schema(
    name="list_saved",
    description=(
        "Kayıtlı tüm dosyaları listeler. Her dosya için ad, boyut, tür, "
        "versiyon ve zaman bilgisi döner. Dosya içerikleri dahil değildir."
    ),
    parameters={},
    required=[],
)

READ_CONTENT_SCHEMA = create_tool_schema(
    name="read_content",
    description=(
        "Daha önce kaydedilmiş bir dosyanın içeriğini okur. Dosya adı ile "
        "çağrılır, içerik ve meta veriler döndürülür."
    ),
    parameters={
        "filename": {
            "type": "string",
            "description": "Okunacak dosyanın adı (örn: 'makale.md')",
        },
    },
    required=["filename"],
)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 55)
    print("  İçerik Kaydetme Aracı - Test")
    print("=" * 55)
    
    # Test 1: İçerik kaydet
    print("\n--- Test 1: İçerik Kaydetme ---")
    sonuc = save_content(
        filename="ai-makale.md",
        content="# Yapay Zeka Ajanları\n\nBu makale, yapay zeka ajanlarının "
                "temellerini ve uygulama alanlarını incelemektedir.\n\n"
                "## Giriş\n\nYapay zeka ajanları, otonom kararlar alabilen "
                "yazılım sistemleridir.",
        content_type="markdown",
    )
    print(f"  Durum: {sonuc['status']}")
    print(f"  Boyut: {sonuc['size']} karakter, {sonuc['word_count']} kelime")
    print(f"  Versiyon: {sonuc['version']}")
    
    # Test 2: İkinci dosya kaydet
    print("\n--- Test 2: İkinci Dosya ---")
    sonuc = save_content(
        filename="notlar.txt",
        content="Toplantı notları:\n- MCP sunucusu tasarımı\n- Araç testleri\n- Yol haritası",
        content_type="text",
    )
    print(f"  Durum: {sonuc['status']}, Dosya: {sonuc['filename']}")
    
    # Test 3: İçerik güncelle
    print("\n--- Test 3: İçerik Güncelleme ---")
    sonuc = save_content(
        filename="ai-makale.md",
        content="# Yapay Zeka Ajanları (Güncellenmiş)\n\nGenişletilmiş içerik...",
        content_type="markdown",
    )
    print(f"  Durum: {sonuc['status']}, Versiyon: {sonuc['version']}")
    
    # Test 4: Dosyaları listele
    print("\n--- Test 4: Dosya Listesi ---")
    sonuc = list_saved()
    print(f"  Toplam: {sonuc['total_files']} dosya, {sonuc['total_size']} karakter")
    for f in sonuc["files"]:
        print(f"    {f['filename']} ({f['content_type']}, v{f['version']})")
    
    # Test 5: İçerik oku
    print("\n--- Test 5: İçerik Okuma ---")
    sonuc = read_content("ai-makale.md")
    if sonuc["found"]:
        print(f"  Dosya: {sonuc['filename']} (v{sonuc['version']})")
        print(f"  İçerik: {sonuc['content'][:80]}...")
    
    # Test 6: Var olmayan dosya
    print("\n--- Test 6: Var Olmayan Dosya ---")
    sonuc = read_content("yok.txt")
    print(f"  Bulundu: {sonuc['found']}")
    print(f"  Hata: {sonuc['error']}")
    
    print("\nTest tamamlandı!")
