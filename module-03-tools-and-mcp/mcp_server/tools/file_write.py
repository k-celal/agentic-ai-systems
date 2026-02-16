"""
File Write Tool - Dosya Yazma Aracı
======================================
Dosya oluşturma ve yazma işlemleri.

⚠️ Non-Idempotent Tool Örneği!
Bu tool idempotent DEĞİLDİR: Aynı çağrıyı 2 kez yapmak
dosyayı 2 kez yazdırır (overwrite). Retry dikkatli yapılmalı!

Kullanım:
    result = file_write(
        filename="output.txt",
        content="Merhaba Dünya!",
    )
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema

# Simüle edilmiş dosya sistemi (gerçek dosya yazmıyoruz, güvenlik!)
VIRTUAL_FILESYSTEM: dict[str, dict] = {}


def file_write(filename: str, content: str, append: bool = False) -> dict:
    """
    Sanal dosya sistemine dosya yaz.
    
    ⚠️ Bu tool gerçek dosya yazmaz, güvenlik için sanal dosya sistemi kullanır.
    Production'da sandbox içinde gerçek dosya yazabilirsiniz.
    
    Parametreler:
        filename: Dosya adı
        content: Yazılacak içerik
        append: True ise mevcut dosyaya ekle, False ise üzerine yaz
    
    Döndürür:
        dict: {"status": "written", "filename": "...", "size": N}
    """
    if append and filename in VIRTUAL_FILESYSTEM:
        existing = VIRTUAL_FILESYSTEM[filename]["content"]
        content = existing + "\n" + content
    
    VIRTUAL_FILESYSTEM[filename] = {
        "content": content,
        "size": len(content),
        "created_at": datetime.now().isoformat(),
        "modified_at": datetime.now().isoformat(),
    }
    
    return {
        "status": "written",
        "filename": filename,
        "size": len(content),
        "append": append,
    }


def file_read(filename: str) -> dict:
    """
    Sanal dosya sisteminden dosya oku.
    
    Parametreler:
        filename: Dosya adı
    
    Döndürür:
        dict: {"content": "...", "size": N} veya {"error": "..."}
    """
    if filename not in VIRTUAL_FILESYSTEM:
        return {"error": f"Dosya bulunamadı: {filename}"}
    
    file_data = VIRTUAL_FILESYSTEM[filename]
    return {
        "content": file_data["content"],
        "size": file_data["size"],
        "modified_at": file_data["modified_at"],
    }


FILE_WRITE_SCHEMA = create_tool_schema(
    name="file_write",
    description="Sanal dosya sistemine dosya yazar. Güvenli sandbox ortamında çalışır.",
    parameters={
        "filename": {
            "type": "string",
            "description": "Dosya adı (örn: output.txt)",
        },
        "content": {
            "type": "string",
            "description": "Dosyaya yazılacak içerik",
        },
        "append": {
            "type": "boolean",
            "description": "True ise mevcut dosyaya ekler, False ise üzerine yazar",
        },
    },
    required=["filename", "content"],
)

FILE_READ_SCHEMA = create_tool_schema(
    name="file_read",
    description="Sanal dosya sisteminden dosya okur.",
    parameters={
        "filename": {
            "type": "string",
            "description": "Okunacak dosya adı",
        },
    },
    required=["filename"],
)


if __name__ == "__main__":
    print("📁 File Tool Test")
    print("=" * 40)
    
    # Yazma testi
    result = file_write("test.txt", "Merhaba Dünya!")
    print(f"Yazma: {result}")
    
    # Okuma testi
    result = file_read("test.txt")
    print(f"Okuma: {result}")
    
    # Append testi
    result = file_write("test.txt", "İkinci satır", append=True)
    result = file_read("test.txt")
    print(f"Append sonrası: {result}")
    
    # Olmayan dosya
    result = file_read("yok.txt")
    print(f"Olmayan dosya: {result}")
    
    print("\n✅ Testler tamamlandı!")
