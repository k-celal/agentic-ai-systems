"""
Shared Memory Tool - Ortak Bellek Aracı
==========================================
Agent'lar arası veri paylaşımını sağlayan MCP aracı.

Bu dosya ne yapar?
------------------
Multi-Agent sisteminde agent'lar birbirlerine veri aktarabilmeli.
SharedMemory, basit bir key-value (anahtar-değer) deposu sağlar:
- Bir agent veri yazar → store("plan", "3 adımlı plan")
- Başka bir agent okur → retrieve("plan") → "3 adımlı plan"

Neden Shared Memory Gerekli?
-----------------------------
Düşünün ki bir ofiste çalışıyorsunuz:
- Bir beyaz tahta var (shared memory)
- Proje yöneticisi tahtaya planı yazar
- Araştırmacı tahtadan planı okur ve bulgularını yazar
- Eleştirmen tahtadaki bulguları okur
- Herkes aynı tahtayı kullanır → bilgi kaybolmaz!

Bu pattern'e "Blackboard Pattern" (Kara Tahta) denir.

MCP Aracı Olarak Neden?
------------------------
Shared Memory'yi MCP aracı olarak tanımlamak şu avantajları sağlar:
1. Standart tool arayüzü ile erişilebilir
2. Agent'lar tool çağrısı yaparak veri paylaşabilir
3. İleride gerçek bir veritabanına geçiş kolaylaşır
4. Tool şeması sayesinde LLM doğrudan kullanabilir

Kullanım:
    from mcp.tools.shared_memory import SharedMemoryTool
    
    memory = SharedMemoryTool()
    
    # Veri kaydet
    memory.store("plan", "3 adımlı plan...")
    
    # Veri oku
    plan = memory.retrieve("plan")
    print(plan)  # "3 adımlı plan..."
    
    # Tüm anahtarları listele
    keys = memory.list_keys()
    print(keys)  # ["plan"]
    
    # Belleği temizle
    memory.clear()
"""

import sys
import os
import json
from typing import Optional, Any

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema


# ============================================================
# Shared Memory Tool Sınıfı
# ============================================================

class SharedMemoryTool:
    """
    Agent'lar arası ortak bellek aracı.
    
    Bu sınıf, basit bir in-memory (bellek içi) key-value deposu sağlar.
    Agent'lar bu aracı kullanarak birbirleriyle veri paylaşabilir.
    
    Veri Yapısı:
        {
            "plan": "3 adımlı plan...",
            "research": "araştırma bulguları...",
            "critique": "eleştiri raporu...",
        }
    
    Neden in-memory?
    - Eğitim amaçlı: Basit ve anlaşılır
    - Hızlı: Dosya veya veritabanı erişimi yok
    - Yeterli: Pipeline sırasında veri kaybolmaz
    
    Gerçek dünyada ne kullanılır?
    - Redis: Hızlı key-value deposu
    - SQLite/PostgreSQL: Kalıcı depolama
    - Message Queue (RabbitMQ, Kafka): Mesaj tabanlı paylaşım
    
    Kullanım:
        memory = SharedMemoryTool()
        
        # Agent 1 (Planner) veri yazar
        memory.store("plan", "1. Konu analizi 2. Araştırma 3. Rapor")
        
        # Agent 2 (Researcher) veri okur
        plan = memory.retrieve("plan")
        print(plan)  # "1. Konu analizi 2. Araştırma 3. Rapor"
    """
    
    def __init__(self):
        """
        SharedMemoryTool'u başlat.
        
        Boş bir sözlük (dictionary) ile başlar.
        Bu sözlük, tüm agent'ların paylaştığı ortak bellektir.
        """
        # Ana veri deposu
        # Key: string (anahtar adı, ör: "plan")
        # Value: any (herhangi bir değer)
        self._storage: dict[str, Any] = {}
        
        # Erişim geçmişi (denetim için)
        # Kim ne zaman ne yazdı/okudu?
        self._access_log: list[dict] = []
    
    def store(self, key: str, value: Any) -> dict:
        """
        Ortak belleğe veri kaydet.
        
        Bu metot, belirtilen anahtar altına bir değer kaydeder.
        Aynı anahtar varsa üzerine yazılır (güncellenir).
        
        Parametreler:
            key: Veri anahtarı (örn: "plan", "research", "critique")
            value: Kaydedilecek değer (string, dict, list vb.)
        
        Döndürür:
            dict: İşlem sonucu
        
        Örnek:
            result = memory.store("plan", "3 adımlı plan...")
            # → {"success": True, "key": "plan", "action": "stored"}
            
            result = memory.store("data", {"name": "test", "value": 42})
            # → {"success": True, "key": "data", "action": "stored"}
        """
        # Değeri string'e çevir (LLM'lerin işleyebilmesi için)
        if isinstance(value, (dict, list)):
            stored_value = json.dumps(value, ensure_ascii=False)
        else:
            stored_value = str(value)
        
        self._storage[key] = stored_value
        
        # Erişim logunu güncelle
        self._access_log.append({
            "action": "store",
            "key": key,
            "value_length": len(stored_value),
        })
        
        return {
            "success": True,
            "key": key,
            "action": "stored",
            "value_length": len(stored_value),
        }
    
    def retrieve(self, key: str) -> dict:
        """
        Ortak bellekten veri oku.
        
        Belirtilen anahtardaki veriyi döndürür.
        Anahtar yoksa hata mesajı döndürür.
        
        Parametreler:
            key: Okunacak veri anahtarı
        
        Döndürür:
            dict: Okunan veri veya hata mesajı
        
        Örnek:
            result = memory.retrieve("plan")
            # Anahtar varsa:
            # → {"success": True, "key": "plan", "value": "3 adımlı plan..."}
            # Anahtar yoksa:
            # → {"success": False, "error": "'plan' anahtarı bulunamadı"}
        """
        if key not in self._storage:
            return {
                "success": False,
                "error": f"'{key}' anahtarı bulunamadı",
                "available_keys": list(self._storage.keys()),
            }
        
        value = self._storage[key]
        
        # Erişim logunu güncelle
        self._access_log.append({
            "action": "retrieve",
            "key": key,
        })
        
        return {
            "success": True,
            "key": key,
            "value": value,
        }
    
    def list_keys(self) -> dict:
        """
        Bellekteki tüm anahtarları listele.
        
        Hangi verilerin mevcut olduğunu görmek için kullanılır.
        
        Döndürür:
            dict: Mevcut anahtarlar ve bilgileri
        
        Örnek:
            result = memory.list_keys()
            # → {
            #     "success": True,
            #     "keys": ["plan", "research", "critique"],
            #     "count": 3
            # }
        """
        keys = list(self._storage.keys())
        
        # Her anahtar için değer uzunluğu bilgisi
        key_info = {}
        for key in keys:
            value = self._storage[key]
            key_info[key] = {
                "value_length": len(str(value)),
                "value_preview": str(value)[:100],
            }
        
        return {
            "success": True,
            "keys": keys,
            "count": len(keys),
            "key_details": key_info,
        }
    
    def clear(self) -> dict:
        """
        Tüm belleği temizle.
        
        Yeni bir pipeline çalıştırmadan önce belleği
        temizlemek iyi bir pratiktir.
        
        Döndürür:
            dict: İşlem sonucu
        
        Örnek:
            result = memory.clear()
            # → {"success": True, "cleared_keys": 3}
        """
        cleared_count = len(self._storage)
        self._storage.clear()
        
        self._access_log.append({
            "action": "clear",
            "cleared_keys": cleared_count,
        })
        
        return {
            "success": True,
            "cleared_keys": cleared_count,
        }
    
    def get_access_log(self) -> list[dict]:
        """
        Erişim geçmişini döndür.
        
        Hata ayıklama ve denetim için hangi agent'ın
        ne zaman ne okuduğunu/yazdığını görmek için kullanılır.
        
        Döndürür:
            list[dict]: Erişim geçmişi
        """
        return list(self._access_log)


# ============================================================
# Tool Şemaları
# ============================================================
# Bu şemalar, LLM'e tool'ların ne yaptığını anlatır.
# LLM bu bilgiyi kullanarak tool'u doğru parametrelerle çağırır.

STORE_SCHEMA = create_tool_schema(
    name="shared_memory_store",
    description="Ortak belleğe veri kaydeder. Agent'lar arası veri paylaşımı için kullanılır.",
    parameters={
        "key": {
            "type": "string",
            "description": "Veri anahtarı (örn: 'plan', 'research', 'critique')",
        },
        "value": {
            "type": "string",
            "description": "Kaydedilecek değer",
        },
    },
    required=["key", "value"],
)

RETRIEVE_SCHEMA = create_tool_schema(
    name="shared_memory_retrieve",
    description="Ortak bellekten veri okur. Belirtilen anahtardaki veriyi döndürür.",
    parameters={
        "key": {
            "type": "string",
            "description": "Okunacak veri anahtarı (örn: 'plan', 'research')",
        },
    },
    required=["key"],
)

LIST_KEYS_SCHEMA = create_tool_schema(
    name="shared_memory_list_keys",
    description="Ortak bellekteki tüm anahtarları listeler.",
    parameters={},
    required=[],
)

CLEAR_SCHEMA = create_tool_schema(
    name="shared_memory_clear",
    description="Ortak belleği tamamen temizler.",
    parameters={},
    required=[],
)

# Tüm şemaları bir arada tut
ALL_SCHEMAS = [STORE_SCHEMA, RETRIEVE_SCHEMA, LIST_KEYS_SCHEMA, CLEAR_SCHEMA]

# OpenAI formatında şemalar
ALL_OPENAI_SCHEMAS = [schema.to_openai_format() for schema in ALL_SCHEMAS]


# ─────────────────────────────────────────
# Bu dosyayı doğrudan çalıştırarak test edebilirsiniz:
# cd module-05-multi-agent
# python -m mcp.tools.shared_memory
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Shared Memory Tool Test")
    print("=" * 40)
    
    # SharedMemoryTool oluştur
    memory = SharedMemoryTool()
    
    # Test 1: Veri kaydetme
    print("\n📝 Test 1: Veri Kaydetme")
    result = memory.store("plan", "1. AI araştır 2. Rapor yaz 3. Değerlendir")
    print(f"   Sonuç: {result}")
    assert result["success"] is True, "Store başarısız!"
    
    # Test 2: Veri okuma
    print("\n📖 Test 2: Veri Okuma")
    result = memory.retrieve("plan")
    print(f"   Sonuç: {result}")
    assert result["success"] is True, "Retrieve başarısız!"
    assert "AI araştır" in result["value"], "Değer yanlış!"
    
    # Test 3: Olmayan anahtar
    print("\n🔍 Test 3: Olmayan Anahtar")
    result = memory.retrieve("nonexistent")
    print(f"   Sonuç: {result}")
    assert result["success"] is False, "Olmayan anahtar başarılı döndü!"
    
    # Test 4: Birden fazla veri
    print("\n📝 Test 4: Birden Fazla Veri")
    memory.store("research", "AI eğitimde yaygın kullanılıyor...")
    memory.store("critique", "Araştırma yeterli değil, kaynak eksik")
    
    result = memory.list_keys()
    print(f"   Anahtarlar: {result['keys']}")
    print(f"   Toplam: {result['count']}")
    assert result["count"] == 3, f"Beklenen 3, gelen {result['count']}"
    
    # Test 5: Dict kaydetme
    print("\n📝 Test 5: Dict Kaydetme")
    memory.store("metadata", {"author": "planner", "steps": 3})
    result = memory.retrieve("metadata")
    print(f"   Sonuç: {result}")
    assert result["success"] is True, "Dict store başarısız!"
    
    # Test 6: Temizleme
    print("\n🗑️ Test 6: Bellek Temizleme")
    result = memory.clear()
    print(f"   Sonuç: {result}")
    assert result["cleared_keys"] == 4, f"Beklenen 4, temizlenen {result['cleared_keys']}"
    
    # Temizleme sonrası kontrol
    result = memory.list_keys()
    assert result["count"] == 0, "Bellek temizlenemedi!"
    print(f"   Bellek boş: ✅")
    
    # Test 7: Erişim logu
    print("\n📊 Test 7: Erişim Logu")
    log = memory.get_access_log()
    print(f"   Toplam erişim: {len(log)}")
    for entry in log:
        print(f"   - {entry['action']}: {entry.get('key', 'N/A')}")
    
    # Şema testi
    print("\n📋 Tool Şemaları:")
    for schema in ALL_SCHEMAS:
        print(f"   - {schema.name}: {schema.description[:50]}...")
    
    print(f"\n   OpenAI formatında şema sayısı: {len(ALL_OPENAI_SCHEMAS)}")
    print(f"   Örnek şema:")
    print(f"   {json.dumps(ALL_OPENAI_SCHEMAS[0], indent=2, ensure_ascii=False)[:300]}...")
    
    print("\n✅ Tüm Shared Memory testleri başarılı!")
