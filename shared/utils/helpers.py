"""
Helpers - Yardımcı Fonksiyonlar
================================
Projede sıkça kullanılan küçük ama faydalı fonksiyonlar.

Kullanım:
    from shared.utils.helpers import retry_async, truncate_text, load_env
"""

import os
import asyncio
import json
from typing import Callable, Any
from dotenv import load_dotenv


def load_env():
    """
    .env dosyasını yükle.
    
    Bu fonksiyon, projenin kök dizinindeki .env dosyasını okur
    ve ortam değişkenlerini ayarlar.
    
    Kullanım:
        load_env()
        api_key = os.getenv("OPENAI_API_KEY")
    """
    # Proje kök dizinini bul
    current = os.path.dirname(os.path.abspath(__file__))
    # shared/utils/ → shared/ → proje kökü
    root = os.path.dirname(os.path.dirname(current))
    
    env_path = os.path.join(root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()  # Mevcut dizinde veya üst dizinlerde ara


async def retry_async(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """
    Başarısız olan async fonksiyonu otomatik tekrar dener.
    
    Neden gerekli?
    - API çağrıları geçici hatalar verebilir (rate limit, timeout)
    - Her seferinde manuel tekrar denemek yerine otomatik deneriz
    - "Exponential backoff" kullanırız: her denemede bekleme süresi artar
    
    Parametreler:
        func: Çalıştırılacak async fonksiyon
        max_retries: Maksimum deneme sayısı
        delay: İlk deneme arası bekleme süresi (saniye)
        backoff: Her denemede bekleme süresinin çarpanı
        exceptions: Yakalanacak hata tipleri
    
    Döndürür:
        Fonksiyonun döndürdüğü değer
    
    Fırlatır:
        Son deneme de başarısız olursa, hatayı fırlatır
    
    Örnek:
        async def unreliable_api_call():
            # Bazen başarısız olan API çağrısı
            response = await api.get_data()
            return response
        
        # 3 denemeye kadar otomatik tekrar dener
        result = await retry_async(unreliable_api_call, max_retries=3)
    
    Bekleme süresi örneği (delay=1, backoff=2):
        Deneme 1: Hemen çalıştır
        Deneme 2: 1 saniye bekle
        Deneme 3: 2 saniye bekle
        Deneme 4: 4 saniye bekle (exponential backoff)
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                print(f"⚠️ Deneme {attempt + 1}/{max_retries} başarısız: {e}")
                print(f"   {current_delay:.1f}s sonra tekrar denenecek...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                print(f"❌ Tüm denemeler ({max_retries}) başarısız!")
    
    raise last_exception


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Uzun metni kırp.
    
    Context window'u verimli kullanmak için çok uzun metinleri kısaltırız.
    
    Parametreler:
        text: Kırpılacak metin
        max_length: Maksimum karakter sayısı
        suffix: Kırpılmış metnin sonuna eklenecek
    
    Döndürür:
        str: Kırpılmış (veya orijinal) metin
    
    Örnek:
        long_text = "A" * 1000
        short = truncate_text(long_text, max_length=100)
        print(len(short))  # 103 ("..." dahil)
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def format_tool_result(result: Any) -> str:
    """
    Tool sonucunu string'e çevir.
    
    Tool'lar farklı tipler döndürebilir (dict, list, string, int...).
    Hepsini LLM'in anlayacağı string formatına çeviririz.
    
    Parametreler:
        result: Tool sonucu (herhangi bir tip)
    
    Döndürür:
        str: String formatında sonuç
    """
    if isinstance(result, str):
        return result
    elif isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        return str(result)


def parse_json_safely(text: str) -> dict | None:
    """
    JSON string'i güvenli şekilde parse et.
    
    LLM bazen JSON formatında cevap verir ama formatı bozuk olabilir.
    Bu fonksiyon hata vermek yerine None döndürür.
    
    Parametreler:
        text: JSON string
    
    Döndürür:
        dict | None: Parse edilmiş JSON veya None
    
    Örnek:
        result = parse_json_safely('{"name": "test"}')
        # → {"name": "test"}
        
        result = parse_json_safely('bozuk json')
        # → None
    """
    try:
        # Bazen LLM markdown code block içinde JSON verir
        # ```json\n{...}\n``` formatını temizle
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # İlk ve son satırı (```) kaldır
            cleaned = "\n".join(lines[1:-1])
        
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, IndexError):
        return None
