"""
Time Tool - Zaman Aracı
=========================
Şu anki saati ve tarihi döndürür.

Bu tool neden önemli?
--------------------
1. LLM'in bilmediği bir bilgiyi sağlar (güncel saat!)
2. "Tool calling" mantığını somutlaştırır
3. Parametreli tool örneği (timezone)

LLM kendi başına saati bilemez çünkü:
- Eğitim verisi eski olabilir
- Gerçek zamanlı bilgiye erişimi yoktur
- AMA bir tool çağırarak saati öğrenebilir!

Kullanım:
    result = get_time()
    # → {"time": "14:30:45", "date": "2025-01-15", "timezone": "UTC"}
    
    result = get_time(timezone="Europe/Istanbul")
    # → {"time": "17:30:45", "date": "2025-01-15", "timezone": "Europe/Istanbul"}
"""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema


# Basit timezone offset tablosu
# (Gerçek projede 'pytz' veya 'zoneinfo' kullanılır)
TIMEZONE_OFFSETS = {
    "UTC": 0,
    "Europe/Istanbul": 3,
    "Europe/London": 0,
    "Europe/Berlin": 1,
    "Europe/Paris": 1,
    "US/Eastern": -5,
    "US/Pacific": -8,
    "Asia/Tokyo": 9,
    "Asia/Dubai": 4,
}


def get_time(timezone_name: str = "UTC") -> dict:
    """
    Şu anki saat ve tarihi döndür.
    
    Parametreler:
        timezone_name: Zaman dilimi (varsayılan: UTC)
                      Desteklenen: UTC, Europe/Istanbul, US/Eastern, vb.
    
    Döndürür:
        dict: {
            "time": "14:30:45",
            "date": "2025-01-15",
            "day_of_week": "Çarşamba",
            "timezone": "Europe/Istanbul",
            "utc_offset": "+03:00"
        }
    
    Örnekler:
        >>> get_time()
        {"time": "12:00:00", "date": "2025-01-15", "timezone": "UTC", ...}
        
        >>> get_time("Europe/Istanbul")
        {"time": "15:00:00", "date": "2025-01-15", "timezone": "Europe/Istanbul", ...}
    """
    # UTC saatini al
    utc_now = datetime.now(timezone.utc)
    
    # Timezone offset'i bul
    offset_hours = TIMEZONE_OFFSETS.get(timezone_name)
    
    if offset_hours is None:
        return {
            "error": f"Bilinmeyen zaman dilimi: '{timezone_name}'",
            "supported_timezones": list(TIMEZONE_OFFSETS.keys()),
        }
    
    # Offset'i uygula
    local_time = utc_now + timedelta(hours=offset_hours)
    
    # Gün adını Türkçe olarak döndür
    day_names_tr = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }
    
    offset_str = f"{'+' if offset_hours >= 0 else ''}{offset_hours:02d}:00"
    
    return {
        "time": local_time.strftime("%H:%M:%S"),
        "date": local_time.strftime("%Y-%m-%d"),
        "day_of_week": day_names_tr.get(local_time.weekday(), "Bilinmiyor"),
        "timezone": timezone_name,
        "utc_offset": offset_str,
    }


# Tool Şeması
GET_TIME_SCHEMA = create_tool_schema(
    name="get_time",
    description=(
        "Belirtilen zaman diliminde şu anki saat ve tarihi döndürür. "
        "LLM saati bilemez, bu tool ile öğrenebilir."
    ),
    parameters={
        "timezone_name": {
            "type": "string",
            "description": (
                "Zaman dilimi adı. Desteklenen değerler: "
                "UTC, Europe/Istanbul, Europe/London, Europe/Berlin, "
                "US/Eastern, US/Pacific, Asia/Tokyo, Asia/Dubai. "
                "Varsayılan: UTC"
            ),
        }
    },
    required=[],  # timezone_name isteğe bağlı, varsayılan UTC
)

GET_TIME_OPENAI_SCHEMA = GET_TIME_SCHEMA.to_openai_format()


# ─────────────────────────────────────────
# Test
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🕐 Time Tool Test")
    print("=" * 40)
    
    # Test 1: UTC
    result = get_time()
    print(f"UTC:      {result['time']} ({result['date']}, {result['day_of_week']})")
    
    # Test 2: İstanbul
    result = get_time("Europe/Istanbul")
    print(f"İstanbul: {result['time']} ({result['date']}, {result['day_of_week']})")
    
    # Test 3: Tokyo
    result = get_time("Asia/Tokyo")
    print(f"Tokyo:    {result['time']} ({result['date']}, {result['day_of_week']})")
    
    # Test 4: Geçersiz timezone
    result = get_time("Mars/Olympus")
    print(f"Hatalı:   {result}")
    assert "error" in result, "Hatalı timezone error döndürmeli!"
    
    print("\n✅ Tüm testler başarılı!")
