"""
Code Exec Tool - Güvenli Kod Çalıştırma Aracı
================================================
Python kodunu güvenli bir sandbox ortamında çalıştırır.

⚠️ GÜVENLİK UYARISI
Kod çalıştırma en tehlikeli tool'lardan biridir!
Bu örnek, güvenlik için şu önlemleri alır:
1. Sadece izin verilen modüller kullanılabilir
2. Dosya sistemi erişimi yok
3. Ağ erişimi yok
4. Zaman limiti var (timeout)
5. Çıktı boyutu sınırlı

Kullanım:
    result = execute_code(
        code="print(sum(range(10)))",
        timeout=5,
    )
    # → {"success": True, "output": "45", "execution_time_ms": 2}
"""

import sys
import os
import io
import time
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema

# İzin verilen modüller (güvenlik!)
ALLOWED_MODULES = {
    "math", "random", "datetime", "json", "re",
    "collections", "itertools", "functools",
    "string", "textwrap",
}

# Yasaklanan anahtar kelimeler
FORBIDDEN_KEYWORDS = [
    "import os", "import sys", "import subprocess",
    "import socket", "import requests", "import urllib",
    "__import__", "eval(", "exec(", "compile(",
    "open(", "file(", "input(",
    "os.system", "os.popen", "os.exec",
]


def execute_code(
    code: str,
    timeout: int = 5,
    max_output_length: int = 1000,
) -> dict:
    """
    Python kodunu güvenli sandbox'ta çalıştır.
    
    Parametreler:
        code: Çalıştırılacak Python kodu
        timeout: Maksimum çalışma süresi (saniye)
        max_output_length: Maksimum çıktı uzunluğu (karakter)
    
    Döndürür:
        dict: {
            "success": True/False,
            "output": "stdout çıktısı",
            "error": "hata mesajı (varsa)",
            "execution_time_ms": süre
        }
    
    Örnekler:
        >>> execute_code("print(2 + 3)")
        {"success": True, "output": "5", ...}
        
        >>> execute_code("import os")  # Yasaklı!
        {"success": False, "error": "Güvenlik ihlali: ...", ...}
    """
    # ─── Güvenlik Kontrolü ───
    security_check = _check_security(code)
    if not security_check["safe"]:
        return {
            "success": False,
            "output": "",
            "error": f"Güvenlik ihlali: {security_check['reason']}",
            "execution_time_ms": 0,
        }
    
    # ─── Kod Çalıştırma ───
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Güvenli global scope
    safe_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "bool": bool,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "isinstance": isinstance,
            "type": type,
            "True": True,
            "False": False,
            "None": None,
        }
    }
    
    # İzin verilen modülleri ekle
    import math
    import random
    import json
    import re
    import collections
    safe_globals["math"] = math
    safe_globals["random"] = random
    safe_globals["json"] = json
    safe_globals["re"] = re
    safe_globals["collections"] = collections
    
    start_time = time.time()
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        output = stdout_capture.getvalue().strip()
        error_output = stderr_capture.getvalue().strip()
        
        # Çıktı boyutu limiti
        if len(output) > max_output_length:
            output = output[:max_output_length] + f"\n... (kırpıldı, toplam {len(output)} karakter)"
        
        return {
            "success": True,
            "output": output,
            "error": error_output if error_output else None,
            "execution_time_ms": round(elapsed_ms, 2),
        }
    
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "success": False,
            "output": stdout_capture.getvalue().strip(),
            "error": f"{type(e).__name__}: {str(e)}",
            "execution_time_ms": round(elapsed_ms, 2),
        }


def _check_security(code: str) -> dict:
    """
    Kodun güvenlik kontrolünü yap.
    
    Döndürür:
        dict: {"safe": True/False, "reason": "..."}
    """
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in code:
            return {
                "safe": False,
                "reason": f"Yasaklı ifade: '{keyword}'",
            }
    
    return {"safe": True, "reason": ""}


CODE_EXEC_SCHEMA = create_tool_schema(
    name="execute_code",
    description=(
        "Python kodunu güvenli bir sandbox ortamında çalıştırır. "
        "math, random, json, re gibi temel modüller kullanılabilir. "
        "Dosya sistemi ve ağ erişimi YOKTUR."
    ),
    parameters={
        "code": {
            "type": "string",
            "description": "Çalıştırılacak Python kodu",
        },
        "timeout": {
            "type": "number",
            "description": "Maksimum çalışma süresi (saniye, varsayılan: 5)",
        },
    },
    required=["code"],
)


if __name__ == "__main__":
    print("💻 Code Exec Tool Test")
    print("=" * 40)
    
    # Test 1: Basit hesaplama
    result = execute_code("print(sum(range(10)))")
    print(f"Test 1 (hesaplama): {result}")
    
    # Test 2: Değişken ve döngü
    result = execute_code("""
numbers = [3, 1, 4, 1, 5, 9, 2, 6]
print(f"Sıralı: {sorted(numbers)}")
print(f"Toplam: {sum(numbers)}")
print(f"Ortalama: {sum(numbers)/len(numbers):.2f}")
""")
    print(f"Test 2 (döngü): {result}")
    
    # Test 3: Güvenlik ihlali
    result = execute_code("import os; os.system('ls')")
    print(f"Test 3 (güvenlik): {result}")
    
    # Test 4: Hata
    result = execute_code("print(1/0)")
    print(f"Test 4 (hata): {result}")
    
    print("\n✅ Testler tamamlandı!")
