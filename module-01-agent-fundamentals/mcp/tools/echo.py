"""
Echo Tool - Yankı Aracı
=========================
Gelen mesajı aynen geri döndürür.

Neden böyle basit bir tool var?
------------------------------
1. Tool çağrı mekanizmasını test etmek için idealdir
2. "Agent gerçekten tool çağırabiliyor mu?" sorusunu cevaplar
3. En basit MCP tool örneğidir — buradan başlayıp karmaşık tool'lara gideriz

Kullanım:
    result = echo(message="Merhaba Dünya!")
    # → "Yankı: Merhaba Dünya!"
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema


def echo(message: str) -> str:
    """
    Gelen mesajı geri döndür.
    
    Parametreler:
        message: Geri döndürülecek mesaj
    
    Döndürür:
        str: "Yankı: {mesaj}"
    
    Örnekler:
        >>> echo("Merhaba!")
        'Yankı: Merhaba!'
        
        >>> echo("Test 123")
        'Yankı: Test 123'
    """
    return f"Yankı: {message}"


# Tool Şeması
# ─────────────────────────────────────────
# Bu şema, LLM'e tool'un ne yaptığını anlatır.
# LLM bu bilgiyi kullanarak tool'u doğru parametrelerle çağırır.

ECHO_SCHEMA = create_tool_schema(
    name="echo",
    description="Gelen mesajı aynen geri döndürür. Test ve doğrulama için kullanılır.",
    parameters={
        "message": {
            "type": "string",
            "description": "Geri döndürülecek mesaj metni",
        }
    },
    required=["message"],
)

# OpenAI formatında şema (agent/loop.py bunu kullanır)
ECHO_OPENAI_SCHEMA = ECHO_SCHEMA.to_openai_format()


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# python -m mcp.tools.echo
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🔧 Echo Tool Test")
    print("=" * 30)
    
    # Test 1: Basit mesaj
    result = echo("Merhaba Dünya!")
    print(f"Test 1: {result}")
    assert result == "Yankı: Merhaba Dünya!", "Test 1 başarısız!"
    
    # Test 2: Boş mesaj
    result = echo("")
    print(f"Test 2: {result}")
    assert result == "Yankı: ", "Test 2 başarısız!"
    
    # Test 3: Türkçe karakterler
    result = echo("Şükrü Öztürk'ün çığlığı")
    print(f"Test 3: {result}")
    
    # Şema testi
    print(f"\nTool Şeması:")
    import json
    print(json.dumps(ECHO_OPENAI_SCHEMA, indent=2, ensure_ascii=False))
    
    print("\n✅ Tüm testler başarılı!")
