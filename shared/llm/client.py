"""
LLM Client - Model İstemcisi
==============================
OpenAI API ile iletişim kuran ana istemci sınıfı.

Bu dosya ne yapar?
-----------------
1. OpenAI API'ye bağlanır
2. Mesaj gönderir ve cevap alır
3. Tool çağrılarını destekler
4. Token kullanımını takip eder

Kullanım:
    from shared.llm.client import LLMClient
    
    client = LLMClient()
    
    # Basit sohbet
    response = await client.chat("Merhaba, nasılsın?")
    print(response.content)
    
    # Tool'larla birlikte
    response = await client.chat(
        message="İstanbul'da hava nasıl?",
        tools=[weather_tool_schema]
    )
"""

import os
import json
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env dosyasından API key'i yükle
load_dotenv()

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


# ============================================================
# Veri Sınıfları (Data Classes)
# ============================================================
# Bu sınıflar, LLM'den dönen cevapları düzenli tutmamızı sağlar

@dataclass
class ToolCall:
    """
    LLM'in çağırmak istediği bir tool'u temsil eder.
    
    Örnek:
        tool_call = ToolCall(
            id="call_123",
            name="get_weather",
            arguments={"city": "Istanbul"}
        )
    """
    id: str                    # Tool çağrısının benzersiz kimliği
    name: str                  # Tool'un adı (örn: "get_weather")
    arguments: dict            # Tool'a gönderilecek parametreler


@dataclass
class TokenUsage:
    """
    Bir LLM çağrısında kullanılan token miktarı.
    
    Token nedir?
    - LLM'lerin metni işlediği en küçük birim
    - Yaklaşık 1 token ≈ 4 karakter (İngilizce)
    - Her çağrı para! Bu yüzden takip etmek önemli
    """
    input_tokens: int = 0      # Gönderdiğimiz metin (prompt)
    output_tokens: int = 0     # LLM'in ürettiği metin (cevap)
    
    @property
    def total_tokens(self) -> int:
        """Toplam token sayısı"""
        return self.input_tokens + self.output_tokens
    
    def estimate_cost(self, model: str = "gpt-4o-mini") -> float:
        """
        Tahmini maliyet hesapla (USD).
        
        Not: Fiyatlar değişebilir, güncel fiyatlar için OpenAI'ı kontrol edin.
        """
        # Yaklaşık fiyatlar (USD per 1M token)
        pricing = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        }
        
        prices = pricing.get(model, pricing["gpt-4o-mini"])
        
        input_cost = (self.input_tokens / 1_000_000) * prices["input"]
        output_cost = (self.output_tokens / 1_000_000) * prices["output"]
        
        return input_cost + output_cost


@dataclass
class LLMResponse:
    """
    LLM'den dönen cevabı temsil eder.
    
    İki tür cevap olabilir:
    1. content: Normal metin cevabı ("Hava güneşli")
    2. tool_calls: Tool çağrısı isteği (get_weather çağır)
    """
    content: Optional[str] = None          # Metin cevabı
    tool_calls: list[ToolCall] = field(default_factory=list)  # Tool çağrıları
    usage: TokenUsage = field(default_factory=TokenUsage)     # Token kullanımı
    model: str = ""                        # Kullanılan model
    
    @property
    def has_tool_calls(self) -> bool:
        """Tool çağrısı var mı?"""
        return len(self.tool_calls) > 0


# ============================================================
# Ana LLM Client Sınıfı
# ============================================================

class LLMClient:
    """
    OpenAI API ile iletişim kuran ana istemci.
    
    Bu sınıf ne yapar?
    1. API bağlantısını yönetir
    2. Mesaj geçmişini tutar (isteğe bağlı)
    3. Token kullanımını takip eder
    4. Tool çağrılarını destekler
    
    Kullanım:
        client = LLMClient(model="gpt-4o-mini")
        
        # Basit kullanım
        response = await client.chat("Merhaba!")
        print(response.content)
        
        # Mesaj geçmişi ile
        messages = [
            {"role": "system", "content": "Sen yardımcı bir asistansın."},
            {"role": "user", "content": "Python nedir?"},
        ]
        response = await client.chat_with_messages(messages)
    """
    
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        temperature: float = 0.7,
    ):
        """
        LLMClient'ı başlat.
        
        Parametreler:
            model: Kullanılacak model (varsayılan: .env'den veya gpt-4o-mini)
            api_key: OpenAI API key (varsayılan: .env'den)
            temperature: Yaratıcılık seviyesi (0=deterministik, 1=yaratıcı)
        """
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        
        # Toplam token kullanımını takip et
        self.total_usage = TokenUsage()
        
        # API istemcisini oluştur
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if AsyncOpenAI is None:
            print("⚠️  openai paketi yüklü değil. 'pip install openai' çalıştırın.")
            self._client = None
        elif not resolved_key or resolved_key == "sk-your-api-key-here":
            print("⚠️  OPENAI_API_KEY ayarlanmamış. .env dosyanızı kontrol edin.")
            self._client = None
        else:
            self._client = AsyncOpenAI(api_key=resolved_key)
    
    async def chat(
        self,
        message: str,
        system_prompt: str = None,
        tools: list[dict] = None,
    ) -> LLMResponse:
        """
        Basit bir mesaj gönder ve cevap al.
        
        Parametreler:
            message: Kullanıcı mesajı
            system_prompt: Sistem talimatı (isteğe bağlı)
            tools: Kullanılabilir tool şemaları (isteğe bağlı)
        
        Döndürür:
            LLMResponse: Model cevabı
        
        Örnek:
            response = await client.chat("Python nedir?")
            print(response.content)
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        return await self.chat_with_messages(messages, tools=tools)
    
    async def chat_with_messages(
        self,
        messages: list[dict],
        tools: list[dict] = None,
    ) -> LLMResponse:
        """
        Mesaj listesi ile LLM'e istek gönder.
        
        Bu method daha gelişmiş kullanım içindir.
        Mesaj geçmişini kontrol etmek istediğinizde kullanın.
        
        Parametreler:
            messages: Mesaj listesi [{"role": "...", "content": "..."}]
            tools: Kullanılabilir tool şemaları
        
        Döndürür:
            LLMResponse: Model cevabı
        """
        # API istemcisi yoksa demo mod
        if self._client is None:
            return self._demo_response(messages, tools)
        
        # API çağrısı için parametreler
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        # Tool'lar varsa ekle
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"  # Model tool kullanıp kullanmamaya karar verir
        
        # API çağrısı yap
        response = await self._client.chat.completions.create(**params)
        
        # Cevabı parse et
        return self._parse_response(response)
    
    def _parse_response(self, response) -> LLMResponse:
        """API cevabını LLMResponse'a dönüştür."""
        message = response.choices[0].message
        
        # Token kullanımı
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        
        # Toplam kullanımı güncelle
        self.total_usage.input_tokens += usage.input_tokens
        self.total_usage.output_tokens += usage.output_tokens
        
        # Tool çağrıları
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
        )
    
    def _demo_response(self, messages: list[dict], tools: list[dict] = None) -> LLMResponse:
        """
        API key yoksa demo cevap döndür.
        Bu sayede API key olmadan da kodu test edebilirsiniz.
        """
        last_message = messages[-1]["content"] if messages else ""
        
        # Tool varsa demo tool çağrısı yap
        if tools and len(tools) > 0:
            first_tool = tools[0]
            tool_name = first_tool["function"]["name"]
            
            return LLMResponse(
                content=None,
                tool_calls=[ToolCall(
                    id="demo_call_001",
                    name=tool_name,
                    arguments={"input": last_message},
                )],
                usage=TokenUsage(input_tokens=50, output_tokens=20),
                model="demo-mode",
            )
        
        # Tool yoksa metin cevabı ver
        return LLMResponse(
            content=f"[DEMO MOD] Mesajınız alındı: '{last_message[:50]}...' "
                    f"(Gerçek cevap için OPENAI_API_KEY ayarlayın)",
            usage=TokenUsage(input_tokens=50, output_tokens=30),
            model="demo-mode",
        )
    
    def get_usage_report(self) -> str:
        """
        Toplam token kullanım raporu döndür.
        
        Örnek çıktı:
            📊 Token Kullanım Raporu
            Model: gpt-4o-mini
            Input:  1500 tokens
            Output:  500 tokens
            Toplam: 2000 tokens
            Tahmini Maliyet: $0.000525
        """
        cost = self.total_usage.estimate_cost(self.model)
        return (
            f"📊 Token Kullanım Raporu\n"
            f"   Model:  {self.model}\n"
            f"   Input:  {self.total_usage.input_tokens:,} tokens\n"
            f"   Output: {self.total_usage.output_tokens:,} tokens\n"
            f"   Toplam: {self.total_usage.total_tokens:,} tokens\n"
            f"   Tahmini Maliyet: ${cost:.6f}"
        )
