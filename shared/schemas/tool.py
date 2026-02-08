"""
Tool Schema - Araç Şema Tanımları
===================================
MCP tool'larının şemalarını tanımlar.

Tool Şeması Nedir?
------------------
Bir tool'un "kimlik kartı"dır:
- Adı ne?
- Ne işe yarar?
- Hangi parametreleri alır?
- Hangi parametreler zorunlu?

LLM bu şemaya bakarak tool'u doğru şekilde çağırır.

Kullanım:
    schema = create_tool_schema(
        name="get_weather",
        description="Hava durumunu getirir",
        parameters={
            "city": {
                "type": "string",
                "description": "Şehir adı"
            }
        },
        required=["city"]
    )
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """
    Bir tool'un şema tanımı.
    
    Bu sınıf, OpenAI'ın tool calling formatına uygun
    JSON şeması oluşturur.
    
    Örnek:
        schema = ToolSchema(
            name="get_weather",
            description="Belirtilen şehrin hava durumunu getirir",
            parameters={
                "city": {
                    "type": "string",
                    "description": "Şehir adı (örn: Istanbul)"
                }
            },
            required=["city"]
        )
        
        # OpenAI formatına çevir
        openai_format = schema.to_openai_format()
    """
    name: str                                      # Tool adı
    description: str                               # Açıklama
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)  # Parametreler
    required: list[str] = field(default_factory=list)  # Zorunlu parametreler
    version: str = "1.0"                           # Versiyon
    
    def to_openai_format(self) -> dict:
        """
        OpenAI tool calling formatına çevir.
        
        Bu format, LLM'in tool'u tanıması ve doğru
        parametrelerle çağırması için gereklidir.
        
        Döndürür:
            dict: OpenAI uyumlu tool şeması
        
        Örnek çıktı:
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Hava durumunu getirir",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string", ...}},
                        "required": ["city"]
                    }
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }
    
    def to_mcp_format(self) -> dict:
        """
        MCP tool tanımı formatına çevir.
        
        Döndürür:
            dict: MCP uyumlu tool şeması
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }
    
    def validate_args(self, args: dict) -> tuple[bool, str]:
        """
        Tool çağrısı parametrelerini doğrula.
        
        Parametreler:
            args: Doğrulanacak parametreler
        
        Döndürür:
            (bool, str): (geçerli_mi, hata_mesajı)
        
        Örnek:
            valid, error = schema.validate_args({"city": "Istanbul"})
            if not valid:
                print(f"Hata: {error}")
        """
        # Zorunlu parametreler var mı?
        for req in self.required:
            if req not in args:
                return False, f"Zorunlu parametre eksik: '{req}'"
        
        # Bilinmeyen parametre var mı?
        known_params = set(self.parameters.keys())
        for key in args:
            if key not in known_params:
                return False, f"Bilinmeyen parametre: '{key}'"
        
        # Tip kontrolü (basit)
        for key, value in args.items():
            if key in self.parameters:
                expected_type = self.parameters[key].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"'{key}' string olmalı, {type(value).__name__} geldi"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"'{key}' number olmalı, {type(value).__name__} geldi"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"'{key}' boolean olmalı, {type(value).__name__} geldi"
        
        return True, ""


def create_tool_schema(
    name: str,
    description: str,
    parameters: dict[str, dict[str, Any]] = None,
    required: list[str] = None,
    version: str = "1.0",
) -> ToolSchema:
    """
    Kolayca tool şeması oluşturan yardımcı fonksiyon.
    
    Parametreler:
        name: Tool adı
        description: Tool açıklaması
        parameters: Parametre tanımları
        required: Zorunlu parametre adları
        version: Versiyon numarası
    
    Döndürür:
        ToolSchema: Oluşturulan şema
    
    Örnek:
        schema = create_tool_schema(
            name="search",
            description="Web araması yapar",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Arama sorgusu"
                },
                "max_results": {
                    "type": "number",
                    "description": "Maksimum sonuç sayısı"
                }
            },
            required=["query"]
        )
    """
    return ToolSchema(
        name=name,
        description=description,
        parameters=parameters or {},
        required=required or [],
        version=version,
    )
